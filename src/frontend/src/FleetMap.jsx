import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Municipal Low-Emission Zone geofences (mirrors LEZ_GEOFENCES in src/telemetry-api/main.py)
const LEZ_ZONES = [
  {
    id: 'lez-chi-01',
    name: 'Chicago Clean Air LEZ Zone 1',
    lat: 41.8781,
    lon: -87.6298,
    radiusKm: 12.5,
    color: '#10b981',
    mandate: 'Zero-Emission EV Mode Enforced',
  },
  {
    id: 'lez-stl-01',
    name: 'St. Louis Metro Green Freight Corridor',
    lat: 38.627,
    lon: -90.1994,
    radiusKm: 18.0,
    color: '#06b6d4',
    mandate: 'Regen & EV Preferred',
  },
];

const MODE_COLORS = {
  EV_MODE: '#34d399',
  HYBRID_MODE: '#818cf8',
  ICE_MODE: '#fbbf24',
  REGEN_BRAKING: '#22d3ee',
};

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[c]));
}

function buildIcon(vehicle, isSelected) {
  const color = MODE_COLORS[vehicle.powertrain_mode] || '#818cf8';
  const hasDtc = vehicle.active_dtc_codes && vehicle.active_dtc_codes !== 'NONE';
  const ring = isSelected ? `box-shadow:0 0 0 4px ${color}66, 0 0 18px ${color};` : 'box-shadow:0 2px 6px rgba(0,0,0,.6);';
  const size = isSelected ? 38 : 30;
  const html = `
    <div style="position:relative;width:${size}px;height:${size}px;">
      <div style="width:${size}px;height:${size}px;border-radius:50%;background:#0f172a;border:3px solid ${isSelected ? '#fff' : color};${ring}display:flex;align-items:center;justify-content:center;box-sizing:border-box;">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9"/>
          <path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14"/>
          <circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/>
        </svg>
      </div>
      ${hasDtc ? '<span style="position:absolute;top:-4px;right:-4px;width:12px;height:12px;border-radius:50%;background:#ef4444;border:2px solid #0f172a;"></span>' : ''}
    </div>`;
  return L.divIcon({
    html,
    className: 'fleetpulse-marker',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function buildPopup(v) {
  const hasDtc = v.active_dtc_codes && v.active_dtc_codes !== 'NONE';
  return `
    <div style="font-family:ui-monospace,monospace;font-size:11px;line-height:1.5;min-width:190px;">
      <div style="font-weight:700;font-size:13px;">${escapeHtml(v.id)}</div>
      <div>${escapeHtml(v.model_name)}</div>
      <div>${escapeHtml(v.location_name)}</div>
      <hr style="margin:4px 0;border:0;border-top:1px solid #cbd5e1;" />
      <div>Mode: <b>${escapeHtml(v.powertrain_mode)}</b></div>
      <div>Speed: ${escapeHtml(v.speed_kph)} km/h · Heading: ${escapeHtml(v.heading_deg)}°</div>
      <div>Battery: ${escapeHtml(v.battery)}%</div>
      <div style="color:${hasDtc ? '#dc2626' : '#059669'};">DTC: ${escapeHtml(v.active_dtc_codes)}</div>
    </div>`;
}

export default function FleetMap({ fleet, selectedVehicleId, onSelect }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef(new Map());
  const fittedRef = useRef(false);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  // Initialise the real map once (OpenStreetMap tiles + LEZ geofences)
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return undefined;

    const map = L.map(containerRef.current, {
      center: [40.5, -88.0],
      zoom: 6,
      zoomControl: true,
      attributionControl: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      className: 'leaflet-dark-tiles',
    }).addTo(map);

    LEZ_ZONES.forEach((z) => {
      L.circle([z.lat, z.lon], {
        radius: z.radiusKm * 1000,
        color: z.color,
        weight: 2,
        dashArray: '6 4',
        fillColor: z.color,
        fillOpacity: 0.12,
      })
        .bindTooltip(`${z.name} — ${z.mandate}`, { sticky: true })
        .addTo(map);
    });

    mapRef.current = map;
    const markers = markersRef.current;

    // The container is laid out after mount; make sure tiles fill it
    const resizeTimer = setTimeout(() => map.invalidateSize(), 150);
    const onResize = () => map.invalidateSize();
    window.addEventListener('resize', onResize);

    return () => {
      clearTimeout(resizeTimer);
      window.removeEventListener('resize', onResize);
      map.remove();
      mapRef.current = null;
      markers.clear();
      fittedRef.current = false;
    };
  }, []);

  // Sync vehicle markers with live fleet data
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const markers = markersRef.current;
    const seen = new Set();

    fleet.forEach((v) => {
      if (typeof v.latitude !== 'number' || typeof v.longitude !== 'number') return;
      seen.add(v.id);
      const isSelected = v.id === selectedVehicleId;
      let marker = markers.get(v.id);
      if (!marker) {
        marker = L.marker([v.latitude, v.longitude], { icon: buildIcon(v, isSelected) })
          .on('click', () => onSelectRef.current && onSelectRef.current(v.id))
          .bindPopup(buildPopup(v))
          .addTo(map);
        markers.set(v.id, marker);
      } else {
        marker.setLatLng([v.latitude, v.longitude]);
        marker.setIcon(buildIcon(v, isSelected));
        marker.setPopupContent(buildPopup(v));
      }
      marker.setZIndexOffset(isSelected ? 1000 : 0);
    });

    markers.forEach((marker, id) => {
      if (!seen.has(id)) {
        marker.remove();
        markers.delete(id);
      }
    });

    if (!fittedRef.current && seen.size > 0) {
      const bounds = L.latLngBounds(
        fleet.filter((v) => seen.has(v.id)).map((v) => [v.latitude, v.longitude])
      );
      map.fitBounds(bounds, { padding: [60, 60], maxZoom: 9 });
      fittedRef.current = true;
    }
  }, [fleet, selectedVehicleId]);

  // Pan to the selected vehicle
  useEffect(() => {
    const map = mapRef.current;
    const v = fleet.find((x) => x.id === selectedVehicleId);
    if (map && v && typeof v.latitude === 'number') {
      map.flyTo([v.latitude, v.longitude], Math.max(map.getZoom(), 8), { duration: 0.8 });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedVehicleId]);

  return <div ref={containerRef} className="w-full h-full" />;
}
