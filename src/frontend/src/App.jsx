import React, { useState, useEffect } from 'react';
import {
  Battery,
  Thermometer,
  ShieldAlert,
  Cpu,
  Navigation,
  Zap,
  RefreshCw,
  Lock,
  LogOut,
  BellRing,
  ShieldCheck,
  WifiOff,
  Wifi,
  ChevronRight,
  Activity,
  Layers,
  Sun,
  Truck,
  Eye,
  Camera,
  AlertTriangle,
  Clock,
  Compass,
  CreditCard,
  CheckCircle2,
  Sliders,
  DollarSign,
  Gauge,
  Fuel,
  Leaf,
  Flame,
  Globe2,
  TreeDeciduous,
  Wind,
  MapPin,
  Sparkles,
  Binary,
  Wrench,
  Radio,
  LocateFixed,
  Maximize2
} from 'lucide-react';
import FleetMap from './FleetMap.jsx';
import Login from './Login.jsx';
import AlertsPanel from './AlertsPanel.jsx';
import ChatAssistant from './ChatAssistant.jsx';
import EngineBadge from './EngineBadge.jsx';
import { fetchAuthConfig, isExpiringSoon, loadSession, refreshSession, saveSession } from './auth.js';

// ── Initial PHEV Fleet with Precise Coordinates for Midwest Freight Corridor ──
const INITIAL_PHEV_FLEET = [
  {
    id: 'PHEV-9402',
    model_name: 'Freightliner Cascadia Hybrid',
    driver: 'Alex R.',
    powertrain_mode: 'EV_MODE',
    latitude: 41.8819,
    longitude: -87.6278,
    location_name: 'Chicago Loop Clean Air Zone (Downtown Hub)',
    speed_kph: 34.5,
    heading_deg: 88.0,
    battery: 18.5,
    temp: 47.8,
    fuel_level: 74.0,
    engine_rpm: 0,
    engine_coolant_temp: 42.0,
    oil_pressure_psi: 0.0,
    engine_load_percent: 0.0,
    map_pressure_kpa: 101.3,
    throttle_position_percent: 14.2,
    fuel_rate_lph: 0.0,
    high_res_odometer_km: 58914.8,
    active_dtc_codes: 'NONE',
    dtc_description: 'Pure electric traction active. Zero ICE emissions.',
    dtc_severity: 'NONE',
    current_mpg: 92.4,
    ev_miles_total: 22410.0,
    ice_miles_total: 14200.0,
    in_lez_zone: true,
    lez_zone_name: 'Chicago Clean Air LEZ Zone 1',
    co2_emissions_kg: 412.0,
    co2_offset_kg: 4820.0,
    assigned_trailer: 'TR-5011',
    status: 'Warning',
    diagnostics: 'GPS Map: Inside Chicago LEZ Zone 1. Pure electric zero-emission lock.',
  },
  {
    id: 'PHEV-1088',
    model_name: 'Volvo VNR Dual-Drive PHEV',
    driver: 'Jordan M.',
    powertrain_mode: 'HYBRID_MODE',
    latitude: 41.5250,
    longitude: -88.0817,
    location_name: 'Joliet Intermodal Freight Gateway (I-80 Corridor)',
    speed_kph: 88.5,
    heading_deg: 235.0,
    battery: 76.0,
    temp: 32.5,
    fuel_level: 88.0,
    engine_rpm: 1380,
    engine_coolant_temp: 89.5,
    oil_pressure_psi: 46.0,
    engine_load_percent: 44.0,
    map_pressure_kpa: 118.5,
    throttle_position_percent: 31.0,
    fuel_rate_lph: 4.6,
    high_res_odometer_km: 96810.4,
    active_dtc_codes: 'NONE',
    dtc_description: 'Closed-loop stoichiometric fuel control. Parallel hybrid cruising.',
    dtc_severity: 'NONE',
    current_mpg: 56.8,
    ev_miles_total: 31200.0,
    ice_miles_total: 28950.0,
    in_lez_zone: false,
    lez_zone_name: 'None',
    co2_emissions_kg: 1140.0,
    co2_offset_kg: 3940.0,
    assigned_trailer: 'TR-3088',
    status: 'Optimal',
    diagnostics: 'GPS Map: Cruising I-80 Southwest. High speed parallel hybrid.',
  },
  {
    id: 'PHEV-3310',
    model_name: 'Peterbilt 579 Hybrid',
    driver: 'Sam K.',
    powertrain_mode: 'ICE_MODE',
    latitude: 39.7684,
    longitude: -86.1581,
    location_name: 'Indianapolis Crossroads Logistics Depot',
    speed_kph: 72.0,
    heading_deg: 160.0,
    battery: 34.5,
    temp: 38.2,
    fuel_level: 38.0,
    engine_rpm: 1720,
    engine_coolant_temp: 96.5,
    oil_pressure_psi: 26.5,
    engine_load_percent: 78.0,
    map_pressure_kpa: 142.0,
    throttle_position_percent: 54.0,
    fuel_rate_lph: 11.4,
    high_res_odometer_km: 85620.1,
    active_dtc_codes: 'P0420, P0524',
    dtc_description: 'P0420 Catalyst Degradation; P0524 Low Oil Pressure (26.5 PSI).',
    dtc_severity: 'CRITICAL',
    current_mpg: 24.5,
    ev_miles_total: 14800.0,
    ice_miles_total: 38400.0,
    in_lez_zone: false,
    lez_zone_name: 'None',
    co2_emissions_kg: 2480.0,
    co2_offset_kg: 1920.0,
    assigned_trailer: 'TR-2204',
    status: 'Critical',
    diagnostics: 'GPS Map: Inbound Indianapolis. CRITICAL: P0420 & P0524 active.',
  },
  {
    id: 'PHEV-7721',
    model_name: 'Kenworth T680 PHEV EcoLine',
    driver: 'Taylor B.',
    powertrain_mode: 'REGEN_BRAKING',
    latitude: 38.6270,
    longitude: -90.1994,
    location_name: 'St. Louis Gateway Green Freight Corridor (I-64)',
    speed_kph: 56.0,
    heading_deg: 275.0,
    battery: 89.2,
    temp: 29.0,
    fuel_level: 92.0,
    engine_rpm: 850,
    engine_coolant_temp: 86.0,
    oil_pressure_psi: 45.0,
    engine_load_percent: 18.0,
    map_pressure_kpa: 98.4,
    throttle_position_percent: 8.0,
    fuel_rate_lph: 1.2,
    high_res_odometer_km: 76210.6,
    active_dtc_codes: 'NONE',
    dtc_description: 'Regen braking recovery. Deceleration fuel cut active.',
    dtc_severity: 'NONE',
    current_mpg: 78.5,
    ev_miles_total: 28900.0,
    ice_miles_total: 18450.0,
    in_lez_zone: true,
    lez_zone_name: 'St. Louis Metro Green Freight Corridor',
    co2_emissions_kg: 640.0,
    co2_offset_kg: 4410.0,
    assigned_trailer: 'TR-1049',
    status: 'Optimal',
    diagnostics: 'GPS Map: St. Louis Riverfront Bridge. Kinetic energy recovery.',
  },
];

const INITIAL_TRAILERS = [
  {
    id: 'TR-5011',
    name: '53ft Dry Van Aero',
    trailer_type: 'Dry Van',
    hardware_suite: 'CargoView AI',
    assigned_vehicle_id: 'PHEV-9402',
    assigned_driver: 'Alex R.',
    tire_psi_avg: 96.2,
    cargo_load_status: 'Loaded',
    current_yard_location: 'Sibley Central Yard (St. Louis)',
    dwell_time_hours: 8.5,
  },
  {
    id: 'TR-3088',
    name: '53ft Reefer Thermal',
    trailer_type: 'Reefer',
    hardware_suite: 'Pro',
    assigned_vehicle_id: 'PHEV-1088',
    assigned_driver: 'Jordan M.',
    tire_psi_avg: 103.5,
    cargo_load_status: 'Empty',
    current_yard_location: 'Chicago Distribution Hub',
    dwell_time_hours: 46.2,
  },
  {
    id: 'TR-2204',
    name: '48ft Solar Flatbed',
    trailer_type: 'Flatbed',
    hardware_suite: 'Solar',
    assigned_vehicle_id: 'PHEV-3310',
    assigned_driver: 'Sam K.',
    tire_psi_avg: 101.8,
    cargo_load_status: 'Partial',
    current_yard_location: 'Indianapolis Intermodal Gate',
    dwell_time_hours: 79.4,
  },
  {
    id: 'TR-1049',
    name: '53ft Dry Van Logistics',
    trailer_type: 'Dry Van',
    hardware_suite: 'Track',
    assigned_vehicle_id: 'PHEV-7721',
    assigned_driver: 'Taylor B.',
    tire_psi_avg: 102.1,
    cargo_load_status: 'Loaded',
    current_yard_location: 'In Transit - I-80 Westbound',
    dwell_time_hours: 1.2,
  },
];

// Map bounding box for Midwest Freight Network
const MAP_BOUNDS = {
  minLat: 38.0,
  maxLat: 42.5,
  minLon: -91.0,
  maxLon: -85.5,
};

function projectToMap(lat, lon) {
  // Projects lat/lon onto a 0-100% SVG/CSS space
  const x = ((lon - MAP_BOUNDS.minLon) / (MAP_BOUNDS.maxLon - MAP_BOUNDS.minLon)) * 100;
  const y = ((MAP_BOUNDS.maxLat - lat) / (MAP_BOUNDS.maxLat - MAP_BOUNDS.minLat)) * 100;
  return {
    x: Math.max(5, Math.min(95, x)),
    y: Math.max(5, Math.min(95, y)),
  };
}

function modeBadge(mode) {
  switch (mode) {
    case 'EV_MODE':
      return { bg: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40', label: 'Pure Electric (EV)', icon: Zap };
    case 'HYBRID_MODE':
      return { bg: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40', label: 'Parallel Hybrid', icon: Activity };
    case 'ICE_MODE':
      return { bg: 'bg-amber-500/20 text-amber-400 border-amber-500/40', label: 'ICE Engine Drive', icon: Flame };
    case 'REGEN_BRAKING':
      return { bg: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40', label: 'Regenerative Recovery', icon: RefreshCw };
    default:
      return { bg: 'bg-slate-800 text-slate-300 border-slate-700', label: mode, icon: Activity };
  }
}

export default function FleetPulseDashboard() {
  const [activeTab, setActiveTab] = useState('map'); // 'map' | 'operations' | 'obd' | 'modesplit' | 'lez' | 'esg'

  const [fleet, setFleet] = useState(INITIAL_PHEV_FLEET);
  const [trailers, setTrailers] = useState(INITIAL_TRAILERS);
  const [selectedVehicleId, setSelectedVehicleId] = useState(INITIAL_PHEV_FLEET[0].id);

  const selectedVehicle = fleet.find((v) => v.id === selectedVehicleId) || fleet[0];
  const selectedTrailer = trailers.find((t) => t.assigned_vehicle_id === selectedVehicle.id) || trailers[0];

  // Editable fields for simulation & failure injection
  const [editPowertrainMode, setEditPowertrainMode] = useState(selectedVehicle.powertrain_mode);
  const [editBattery, setEditBattery] = useState(selectedVehicle.battery);
  const [editTemp, setEditTemp] = useState(selectedVehicle.temp);
  const [editFuelLevel, setEditFuelLevel] = useState(selectedVehicle.fuel_level);
  const [editEngineRpm, setEditEngineRpm] = useState(selectedVehicle.engine_rpm);
  const [editCoolantTemp, setEditCoolantTemp] = useState(selectedVehicle.engine_coolant_temp);
  const [editOilPsi, setEditOilPsi] = useState(selectedVehicle.oil_pressure_psi);
  const [editEngineLoad, setEditEngineLoad] = useState(selectedVehicle.engine_load_percent);
  const [editMapPressure, setEditMapPressure] = useState(selectedVehicle.map_pressure_kpa);
  const [editThrottlePos, setEditThrottlePos] = useState(selectedVehicle.throttle_position_percent);
  const [editFuelRate, setEditFuelRate] = useState(selectedVehicle.fuel_rate_lph);
  const [editHighResOdo, setEditHighResOdo] = useState(selectedVehicle.high_res_odometer_km);
  const [editActiveDtc, setEditActiveDtc] = useState(selectedVehicle.active_dtc_codes);
  const [editInLez, setEditInLez] = useState(selectedVehicle.in_lez_zone);
  const [editLezName, setEditLezName] = useState(selectedVehicle.lez_zone_name);
  const [editDiagnostics, setEditDiagnostics] = useState(selectedVehicle.diagnostics);

  // Connectivity & Bedrock AI State
  const [lastSync, setLastSync] = useState('Live');
  const [aiOutput, setAiOutput] = useState('');
  const [aiEngine, setAiEngine] = useState('Amazon Bedrock');
  const [snsStatus, setSnsStatus] = useState('');
  const [loading, setLoading] = useState(false);
  const [snsLoading, setSnsLoading] = useState(false);
  const [apiOnline, setApiOnline] = useState(true);

  const [apiEndpoint, setApiEndpoint] = useState(
    typeof window !== 'undefined' && window.location.hostname !== 'localhost'
      ? window.location.origin
      : 'http://localhost:8000'
  );

  // ── Authentication (Cognito) ──
  const [session, setSession] = useState(() => loadSession());
  const idToken = session?.idToken || '';
  const authHeader = () => (idToken ? { Authorization: `Bearer ${idToken}` } : {});

  const updateSession = (next) => {
    saveSession(next);
    setSession(next);
  };
  const signOut = () => updateSession(null);

  // Silently refresh the id token shortly before it expires
  useEffect(() => {
    if (!session || session.devBypass) return undefined;
    const timer = setInterval(async () => {
      if (!isExpiringSoon(session)) return;
      try {
        const config = await fetchAuthConfig(apiEndpoint);
        updateSession(await refreshSession(config, session));
      } catch (_) {
        signOut();
      }
    }, 30000);
    return () => clearInterval(timer);
  }, [session, apiEndpoint]);

  // Server-computed data: alerts rules engine, ESG analytics, data provenance
  const [alerts, setAlerts] = useState([]);
  const [alertRules, setAlertRules] = useState([]);
  const [esg, setEsg] = useState(null);
  const [analyticsError, setAnalyticsError] = useState('');
  const [dataSource, setDataSource] = useState('aurora');
  const [aiMeta, setAiMeta] = useState(null); // {live, reason, modelId}

  // Sync edits when vehicle switches
  useEffect(() => {
    const v = fleet.find((x) => x.id === selectedVehicleId) || fleet[0];
    setEditPowertrainMode(v.powertrain_mode);
    setEditBattery(v.battery);
    setEditTemp(v.temp);
    setEditFuelLevel(v.fuel_level);
    setEditEngineRpm(v.engine_rpm);
    setEditCoolantTemp(v.engine_coolant_temp);
    setEditOilPsi(v.oil_pressure_psi);
    setEditEngineLoad(v.engine_load_percent);
    setEditMapPressure(v.map_pressure_kpa);
    setEditThrottlePos(v.throttle_position_percent);
    setEditFuelRate(v.fuel_rate_lph);
    setEditHighResOdo(v.high_res_odometer_km);
    setEditActiveDtc(v.active_dtc_codes);
    setEditInLez(v.in_lez_zone);
    setEditLezName(v.lez_zone_name);
    setEditDiagnostics(v.diagnostics);
  }, [selectedVehicleId]);

  // Live polling
  useEffect(() => {
    if (!idToken) return;
    let active = true;

    const getJson = async (path) => {
      const res = await fetch(`${apiEndpoint}${path}`, { headers: { Authorization: `Bearer ${idToken}` } });
      if (res.status === 401) throw Object.assign(new Error('unauthorized'), { unauthorized: true });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    };

    const pollAll = async () => {
      try {
        const data = await getJson('/telemetry/fleet');
        if (!active) return;
        if (data.vehicles?.length) setFleet(data.vehicles);
        if (data.data_source) setDataSource(data.data_source);
        setLastSync(new Date().toLocaleTimeString());
        setApiOnline(true);

        // Alerts and ESG are secondary; a failure there must not flip the connection status
        // /telemetry/* is the path prefix CloudFront forwards to the API with the Authorization header
        const [alertData, esgData] = await Promise.allSettled([getJson('/telemetry/alerts'), getJson('/telemetry/analytics/mode-split-esg')]);
        if (!active) return;
        if (alertData.status === 'fulfilled') {
          setAlerts(alertData.value.alerts || []);
          setAlertRules(alertData.value.rules || []);
        }
        if (esgData.status === 'fulfilled') {
          setEsg(esgData.value);
          setAnalyticsError('');
        } else {
          setAnalyticsError(esgData.reason?.message || 'request failed');
        }
      } catch (err) {
        if (err.unauthorized) signOut();
        else setApiOnline(false);
      }
    };

    pollAll();
    const timer = setInterval(pollAll, 6000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [idToken, apiEndpoint]);

  const acknowledgeAlert = async (alertId) => {
    setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, acknowledged: true } : a))); // optimistic
    try {
      const res = await fetch(`${apiEndpoint}/telemetry/alerts/${alertId}/ack`, { method: 'POST', headers: authHeader() });
      if (res.status === 401) signOut();
    } catch (_) {
      /* the next poll restores the server state */
    }
  };

  const locateVehicle = (vehicleId) => {
    setSelectedVehicleId(vehicleId);
    setActiveTab('map');
  };

  const openAlertCount = alerts.filter((a) => !a.acknowledged).length;

  // Run Bedrock AI Dispatch Recommendation
  const runBedrockDispatch = async () => {
    setLoading(true);
    setAiOutput('');

    const payload = {
      vehicle_id: selectedVehicleId,
      trailer_id: selectedTrailer.id,
      powertrain_mode: editPowertrainMode,
      latitude: selectedVehicle.latitude,
      longitude: selectedVehicle.longitude,
      location_name: selectedVehicle.location_name,
      battery_level: parseFloat(editBattery),
      temperature_celsius: parseFloat(editTemp),
      fuel_level: parseFloat(editFuelLevel),
      engine_rpm: parseInt(editEngineRpm, 10),
      engine_coolant_temp: parseFloat(editCoolantTemp),
      oil_pressure_psi: parseFloat(editOilPsi),
      engine_load_percent: parseFloat(editEngineLoad),
      map_pressure_kpa: parseFloat(editMapPressure),
      throttle_position_percent: parseFloat(editThrottlePos),
      fuel_rate_lph: parseFloat(editFuelRate),
      high_res_odometer_km: parseFloat(editHighResOdo),
      active_dtc_codes: editActiveDtc,
      in_lez_zone: editInLez,
      lez_zone_name: editLezName,
      route_diagnostics: editDiagnostics,
    };

    try {
      const res = await fetch(`${apiEndpoint}/ai/dispatch-assistant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeader() },
        body: JSON.stringify(payload),
      });

      if (res.status === 401) {
        signOut();
        throw new Error('Your session has expired. Please sign in again.');
      }
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = Array.isArray(data.detail) ? data.detail.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join('; ') : data.detail;
        throw new Error(detail || `Request failed (HTTP ${res.status})`);
      }
      setAiOutput(data.recommendation || JSON.stringify(data, null, 2));
      setAiEngine(data.engine || 'Amazon Bedrock');
      setAiMeta({ live: !!data.live, reason: data.fallback_reason, modelId: data.model_id });
      setApiOnline(true);
    } catch (err) {
      // Never fabricate a model answer in the browser: show the real failure so it can be fixed.
      setAiEngine('Request failed');
      setAiMeta({ live: false, reason: err.message, modelId: null });
      setAiOutput(`Could not get a dispatch directive.\n\n${err.message}`);
      setApiOnline(err.message.startsWith('Your session') ? apiOnline : false);
    } finally {
      setLoading(false);
    }
  };

  // Dispatch SNS Alert
  const triggerSnsAlert = async () => {
    setSnsLoading(true);
    setSnsStatus('');
    try {
      const res = await fetch(`${apiEndpoint}/telemetry/alert-sns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeader() },
        body: JSON.stringify({
          vehicle_id: selectedVehicleId,
          trailer_id: selectedTrailer.id,
          powertrain_mode: editPowertrainMode,
          active_dtc_codes: editActiveDtc,
          oil_pressure_psi: parseFloat(editOilPsi),
          engine_load_percent: parseFloat(editEngineLoad),
          latitude: selectedVehicle.latitude,
          longitude: selectedVehicle.longitude,
        }),
      });

      if (res.status === 401) {
        signOut();
        throw new Error('Your session has expired. Please sign in again.');
      }
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = Array.isArray(data.detail) ? data.detail.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join('; ') : data.detail;
        throw new Error(detail || `Request failed (HTTP ${res.status})`);
      }
      const label = data.status === 'simulated' ? '[NOT SENT - SNS topic not configured]' : 'SNS alert published';
      setSnsStatus(`${label} • MessageId: ${String(data.message_id || '').slice(0, 14)}…`);
    } catch (err) {
      setSnsStatus(`✗ Alert not sent: ${err.message}`);
    } finally {
      setSnsLoading(false);
    }
  };

  const badge = modeBadge(editPowertrainMode);
  const ModeIcon = badge.icon;

  // Not signed in: show the Cognito login instead of the dashboard
  if (!session) {
    return <Login apiEndpoint={apiEndpoint} onSignedIn={updateSession} />;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans">
      {/* ── Top Header Command Bar ── */}
      <header className="sticky top-0 z-30 bg-slate-950/95 backdrop-blur border-b border-slate-800 px-6 py-3">
        <div className="flex flex-wrap justify-between items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/10 rounded-xl border border-indigo-500/20">
              <Compass className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
                FleetPulse GPS Map Operations
                <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 flex items-center gap-1">
                  <MapPin className="w-3 h-3 text-red-400" /> Live Telematics Map Online
                </span>
              </h1>
              <p className="text-xs text-slate-400">
                Real-Time GPS Tracking · LEZ Municipal Geofences · Dual-Powertrain OBD-II Telemetry
              </p>
            </div>
          </div>

          {/* Navigation Bar */}
          <nav className="flex items-center gap-1 bg-slate-900 border border-slate-800 p-1 rounded-xl">
            <button
              onClick={() => setActiveTab('map')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition ${
                activeTab === 'map' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Compass className="w-3.5 h-3.5" /> Live GPS Fleet Map
            </button>
            <button
              onClick={() => setActiveTab('operations')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition ${
                activeTab === 'operations' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" /> Operations &amp; AI
            </button>
            <button
              onClick={() => setActiveTab('obd')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition ${
                activeTab === 'obd' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Binary className="w-3.5 h-3.5" /> OBD-II Vitals
            </button>
            <button
              onClick={() => setActiveTab('modesplit')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition ${
                activeTab === 'modesplit' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Activity className="w-3.5 h-3.5" /> Mode Split
            </button>
            <button
              onClick={() => setActiveTab('lez')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition ${
                activeTab === 'lez' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <MapPin className="w-3.5 h-3.5" /> LEZ Geofences
            </button>
            <button
              onClick={() => setActiveTab('esg')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition ${
                activeTab === 'esg' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Leaf className="w-3.5 h-3.5" /> ESG Offsets
            </button>
            <button
              onClick={() => setActiveTab('alerts')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition ${
                activeTab === 'alerts' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <BellRing className="w-3.5 h-3.5" /> Alerts
              {openAlertCount > 0 && (
                <span className="min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
                  {openAlertCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('assistant')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition ${
                activeTab === 'assistant' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" /> Assistant
            </button>
          </nav>

          {/* Status */}
          <div className="flex items-center gap-2">
            {dataSource === 'fallback' && (
              <span
                title="The database is unreachable, so the API is serving built-in sample data."
                className="text-xs px-2.5 py-1 rounded-full border font-medium bg-amber-500/10 text-amber-400 border-amber-500/20"
              >
                Sample data
              </span>
            )}
            <span
              className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border font-medium ${
                apiOnline
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-red-500/10 text-red-400 border-red-500/20'
              }`}
            >
              {apiOnline ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
              {apiOnline ? 'API Connected' : 'API Unreachable'}
            </span>
            <span className="text-xs text-slate-400 hidden md:inline" title={(session.groups || []).join(', ') || 'no groups'}>
              {session.email}
            </span>
            <button
              onClick={signOut}
              className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border border-slate-700 text-slate-300 hover:bg-slate-800 transition"
            >
              <LogOut className="w-3 h-3" /> Sign out
            </button>
          </div>
        </div>
      </header>

      {/* ── Tab 1: Live Interactive GPS Fleet Map ── */}
      {activeTab === 'map' && (
        <div className="p-6 space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Compass className="w-5 h-5 text-indigo-400" />
                Live Fleet Telematics &amp; Geofenced Corridor Map
              </h2>
              <p className="text-xs text-slate-400">
                Interactive real-time map displaying tractor-trailer coordinates, heading vectors, speed, and municipal clean-air geofence zones
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-3 py-1 rounded-full font-medium flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                4 Vehicles Positioned Across Midwest Corridor
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 items-start">
            {/* Real Interactive Map View (Leaflet + OpenStreetMap) */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 relative overflow-hidden min-h-[560px] flex flex-col justify-between shadow-2xl">
              {/* Map Controls & Legend Overlay (click-through so the map stays draggable) */}
              <div className="flex justify-between items-start z-10 pointer-events-none">
                <div className="bg-slate-950/80 backdrop-blur p-3 rounded-xl border border-slate-800/80 space-y-1">
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Globe2 className="w-3.5 h-3.5 text-indigo-400" /> Midwest Regional Freight Corridor
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Live OpenStreetMap · scroll to zoom, drag to pan, click a truck for details
                  </div>
                </div>

                <div className="bg-slate-950/80 backdrop-blur p-3 rounded-xl border border-slate-800/80 text-[11px] space-y-1.5 mr-12">
                  <div className="flex items-center gap-2 text-emerald-400">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" /> Pure EV Mode
                  </div>
                  <div className="flex items-center gap-2 text-indigo-300">
                    <span className="w-2.5 h-2.5 rounded-full bg-indigo-400" /> Parallel Hybrid
                  </div>
                  <div className="flex items-center gap-2 text-amber-400">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-400" /> ICE Engine Drive
                  </div>
                  <div className="flex items-center gap-2 text-cyan-300">
                    <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" /> Regenerative Braking
                  </div>
                </div>
              </div>

              {/* Real interactive map (Leaflet + OpenStreetMap tiles) with live vehicle markers & LEZ geofences */}
              <div className="absolute inset-0 z-0">
                <FleetMap fleet={fleet} selectedVehicleId={selectedVehicleId} onSelect={setSelectedVehicleId} />
              </div>

              {/* Bottom Map Details Footer */}
              <div className="flex justify-between items-center z-10 pointer-events-none bg-slate-950/80 backdrop-blur p-3 rounded-xl border border-slate-800/80 text-xs text-slate-300">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1 font-semibold text-white">
                    <LocateFixed className="w-4 h-4 text-indigo-400" />
                    Selected Asset: {selectedVehicle.id}
                  </span>
                  <span className="text-slate-400 font-mono text-[11px]">
                    Lat: {Math.abs(selectedVehicle.latitude).toFixed(4)}°{selectedVehicle.latitude >= 0 ? 'N' : 'S'}, Lon:{' '}
                    {Math.abs(selectedVehicle.longitude).toFixed(4)}°{selectedVehicle.longitude >= 0 ? 'E' : 'W'}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Location: <span className="text-white font-medium">{selectedVehicle.location_name}</span>
                </div>
              </div>
            </div>

            {/* Selected Vehicle Map Telemetry Sidebar */}
            <aside className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-red-400" />
                  Waypoint Vitals
                </h3>
                <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold ${badge.bg}`}>
                  {badge.label}
                </span>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <span className="text-xs text-slate-400">Location Heading</span>
                <p className="text-sm font-bold text-white">{selectedVehicle.location_name}</p>
                <div className="flex justify-between text-xs text-slate-400 font-mono pt-1">
                  <span>Speed: {selectedVehicle.speed_kph} km/h</span>
                  <span>Heading: {selectedVehicle.heading_deg}°</span>
                </div>
              </div>

              {/* GPS OBD-II Snapshot */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-[11px] text-slate-500">Engine RPM</span>
                  <p className="text-lg font-bold text-white mt-0.5 font-mono">{selectedVehicle.engine_rpm}</p>
                  <span className="text-[10px] text-cyan-400">PID 0C</span>
                </div>

                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-[11px] text-slate-500">Fuel Burn Rate</span>
                  <p className="text-lg font-bold text-amber-400 mt-0.5 font-mono">{selectedVehicle.fuel_rate_lph} L/h</p>
                  <span className="text-[10px] text-amber-500">PID 5E</span>
                </div>

                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-[11px] text-slate-500">Battery SOC</span>
                  <p className="text-lg font-bold text-emerald-400 mt-0.5 font-mono">{selectedVehicle.battery}%</p>
                  <span className="text-[10px] text-emerald-500">{selectedVehicle.temp}°C</span>
                </div>

                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-[11px] text-slate-500">High-Res Odometer</span>
                  <p className="text-sm font-bold text-indigo-300 mt-1 font-mono">
                    {Number(selectedVehicle.high_res_odometer_km).toLocaleString()} km
                  </p>
                  <span className="text-[10px] text-slate-500">PID A6</span>
                </div>
              </div>

              {/* Active DTC Alert */}
              <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400">Diagnostic Trouble Code Status</span>
                <p className={`text-xs font-mono font-bold mt-1 ${selectedVehicle.active_dtc_codes !== 'NONE' ? 'text-red-400' : 'text-emerald-400'}`}>
                  {selectedVehicle.active_dtc_codes}
                </p>
                <p className="text-[11px] text-slate-400 mt-1">{selectedVehicle.dtc_description}</p>
              </div>

              {/* Bedrock Dispatch Action */}
              <button
                onClick={runBedrockDispatch}
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-500 active:scale-[0.99] text-white font-semibold py-3 px-4 rounded-xl transition flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/30 text-xs disabled:opacity-60"
              >
                {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4 text-amber-300" />}
                Analyze Location with Bedrock AI
              </button>

              {/* Bedrock AI Result (shown on the map tab so the analysis is visible right here) */}
              {(loading || aiOutput) && (
                <div className="bg-slate-950 border border-indigo-500/30 rounded-xl p-3.5 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-semibold text-indigo-300 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                      Bedrock Location Analysis
                    </span>
                    {aiMeta ? (
                      <EngineBadge live={aiMeta.live} engine={aiEngine} reason={aiMeta.reason} modelId={aiMeta.modelId} />
                    ) : (
                      <span className="text-[10px] text-slate-500">{aiEngine}</span>
                    )}
                  </div>
                  {aiMeta && !aiMeta.live && aiMeta.reason && (
                    <p className="text-[11px] text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded-lg px-2.5 py-1.5">
                      Why not live: {aiMeta.reason}
                    </p>
                  )}
                  {loading ? (
                    <div className="flex items-center gap-2 text-xs text-slate-400 py-4 justify-center">
                      <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                      Analyzing GPS position &amp; OBD-II diagnostics…
                    </div>
                  ) : (
                    <pre className="font-mono text-[10.5px] text-slate-200 whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto">
                      {aiOutput}
                    </pre>
                  )}
                </div>
              )}

            </aside>
          </div>
        </div>
      )}

      {/* ── Tab 2: Operations, Powertrain & Failure Controls ── */}
      {activeTab === 'operations' && (
        <div className="p-6 grid grid-cols-1 lg:grid-cols-[320px_1fr_420px] gap-6 items-start">
          <aside className="bg-slate-900/60 backdrop-blur border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Truck className="w-4 h-4 text-emerald-400" />
                Active PHEV Fleet ({fleet.length})
              </h2>
            </div>

            <div className="space-y-3">
              {fleet.map((v) => {
                const isSelected = v.id === selectedVehicleId;
                const mBadge = modeBadge(v.powertrain_mode);
                return (
                  <button
                    key={v.id}
                    onClick={() => setSelectedVehicleId(v.id)}
                    className={`w-full text-left p-4 rounded-xl border transition-all ${
                      isSelected
                        ? 'bg-indigo-950/60 border-indigo-500 shadow-lg shadow-indigo-950/40'
                        : 'bg-slate-900/70 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-1.5">
                      <div>
                        <span className="font-bold text-white text-sm font-mono">{v.id}</span>
                        <p className="text-[11px] text-slate-400">{v.model_name}</p>
                      </div>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold ${mBadge.bg}`}>
                        {mBadge.label}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 mt-2 truncate flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-red-400 shrink-0" />
                      {v.location_name}
                    </div>
                  </button>
                );
              })}
            </div>
          </aside>

          {/* Middle Controls */}
          <main className="bg-slate-900/60 backdrop-blur border border-slate-800 rounded-xl p-5 space-y-5">
            <div className="flex justify-between items-center">
              <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Binary className="w-4 h-4 text-emerald-400" />
                Live Vehicle Vitals &amp; OBD-II Diagnostics Inspector
              </h2>
              <span className={`text-xs px-3 py-1 rounded-full border font-semibold flex items-center gap-1.5 ${badge.bg}`}>
                <ModeIcon className="w-3.5 h-3.5" />
                {badge.label}
              </span>
            </div>

            <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider">Unit Identifier</p>
                <p className="text-2xl font-black text-white">{selectedVehicle.id}</p>
                <p className="text-xs text-slate-400">{selectedVehicle.model_name} • Driver: {selectedVehicle.driver}</p>
                <p className="text-xs text-indigo-400 font-mono mt-1">High-Res Odo: {Number(editHighResOdo).toLocaleString()} km</p>
              </div>

              <div className="border-t md:border-t-0 md:border-l border-slate-800 md:pl-4">
                <p className="text-xs text-slate-500 uppercase tracking-wider">OBD-II Diagnostic Trouble Codes (DTC)</p>
                <p className={`text-base font-bold mt-1 font-mono flex items-center gap-1.5 ${editActiveDtc !== 'NONE' ? 'text-red-400' : 'text-emerald-400'}`}>
                  {editActiveDtc !== 'NONE' ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
                  {editActiveDtc}
                </p>
                <p className="text-[11px] text-slate-400 mt-1">{selectedVehicle.dtc_description}</p>
              </div>
            </div>

            {/* Parameter Injection */}
            <div className="bg-slate-950/70 border border-indigo-500/20 rounded-xl p-4 space-y-4">
              <p className="text-xs font-semibold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5" />
                Live OBD-II Parameter &amp; Failure Injection
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Powertrain Mode</label>
                  <select
                    value={editPowertrainMode}
                    onChange={(e) => setEditPowertrainMode(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-lg p-2 font-mono"
                  >
                    <option value="EV_MODE">Pure Electric (EV Mode)</option>
                    <option value="HYBRID_MODE">Parallel Hybrid Mode</option>
                    <option value="ICE_MODE">Internal Combustion (ICE Mode)</option>
                    <option value="REGEN_BRAKING">Regenerative Braking Mode</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">Active OBD-II DTC Fault Code</label>
                  <select
                    value={editActiveDtc}
                    onChange={(e) => setEditActiveDtc(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-lg p-2 font-mono"
                  >
                    <option value="NONE">NONE (All Diagnostic Systems OK)</option>
                    <option value="P0420">P0420 - Catalytic Converter Degradation</option>
                    <option value="P0524">P0524 - Engine Oil Pressure Too Low</option>
                    <option value="P0420, P0524">P0420 + P0524 - Dual Critical Failure</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">Throttle Position ({editThrottlePos}%)</label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="1"
                    value={editThrottlePos}
                    onChange={(e) => setEditThrottlePos(parseFloat(e.target.value))}
                    className="w-full accent-indigo-500 mt-2"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Oil Pressure ({editOilPsi} PSI)</label>
                  <input
                    type="range"
                    min="15"
                    max="65"
                    step="0.5"
                    value={editOilPsi}
                    onChange={(e) => setEditOilPsi(e.target.value)}
                    className="w-full accent-amber-500"
                  />
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">Engine Coolant ({editCoolantTemp}°C)</label>
                  <input
                    type="range"
                    min="40"
                    max="115"
                    step="0.5"
                    value={editCoolantTemp}
                    onChange={(e) => setEditCoolantTemp(e.target.value)}
                    className="w-full accent-red-500"
                  />
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-3">
              <button
                onClick={runBedrockDispatch}
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-500 active:scale-[0.99] text-white font-semibold py-3 px-4 rounded-xl transition flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/30 disabled:opacity-60"
              >
                {loading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5 text-amber-300" />}
                Run Amazon Bedrock OBD-II &amp; Map AI
              </button>

              <button
                onClick={triggerSnsAlert}
                disabled={snsLoading}
                className="w-full bg-red-600/90 hover:bg-red-500 active:scale-[0.99] text-white font-semibold py-2.5 px-4 rounded-xl transition flex items-center justify-center gap-2 disabled:opacity-60"
              >
                <BellRing className="w-4 h-4" />
                {snsLoading ? 'Publishing to Amazon SNS…' : 'Dispatch Amazon SNS Critical Alert'}
              </button>

              {snsStatus && (
                <div className="text-xs text-emerald-300 bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-2.5 text-center font-mono">
                  {snsStatus}
                </div>
              )}
            </div>
          </main>

          {/* Right Console */}
          <aside className="bg-slate-900/60 backdrop-blur border border-slate-800 rounded-xl p-5 flex flex-col min-h-[620px]">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-400" />
                Bedrock Dispatch Console
              </h2>
              <span className="text-[10px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 px-2.5 py-0.5 rounded-full font-medium">
                {aiEngine}
              </span>
            </div>

            <div className="flex-1 bg-slate-950 border border-slate-800 rounded-lg p-4 font-mono text-xs overflow-y-auto">
              {loading ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-3">
                  <RefreshCw className="w-8 h-8 animate-spin text-indigo-400" />
                  <span>Synthesizing Bedrock GPS map position &amp; OBD-II diagnostics…</span>
                </div>
              ) : aiOutput ? (
                <pre className="text-slate-200 whitespace-pre-wrap leading-relaxed">{aiOutput}</pre>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-600 text-center gap-3">
                  <Compass className="w-10 h-10 text-slate-800" />
                  <p className="text-sm font-semibold text-slate-400">Amazon Bedrock Telematics Engine</p>
                  <p className="text-xs max-w-xs text-slate-500 leading-relaxed">
                    View fleet positions on the Live GPS Map tab or trigger an AI dispatch evaluation above.
                  </p>
                </div>
              )}
            </div>
          </aside>
        </div>
      )}

      {/* ── Tab 3: Dedicated OBD-II Stream ── */}
      {activeTab === 'obd' && (
        <div className="p-6 space-y-6">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Binary className="w-5 h-5 text-emerald-400" />
              Real-Time OBD-II CAN-Bus Parameter Stream
            </h2>
            <p className="text-xs text-slate-400">
              Live OBD-II standard PIDs across all 4 fleet power units
            </p>
          </div>

          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300 font-mono">
              <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="p-3">Vehicle</th>
                  <th className="p-3">GPS Location</th>
                  <th className="p-3">Active DTC</th>
                  <th className="p-3">RPM</th>
                  <th className="p-3">Load %</th>
                  <th className="p-3">MAP kPa</th>
                  <th className="p-3">Fuel Rate</th>
                  <th className="p-3">Odometer</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {fleet.map((v) => (
                  <tr key={v.id} className="hover:bg-slate-800/40">
                    <td className="p-3 font-bold text-white">{v.id}</td>
                    <td className="p-3 text-slate-400 font-sans">{v.location_name}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        v.active_dtc_codes && v.active_dtc_codes !== 'NONE'
                          ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                          : 'bg-emerald-500/20 text-emerald-300'
                      }`}>
                        {v.active_dtc_codes || 'NONE'}
                      </span>
                    </td>
                    <td className="p-3">{v.engine_rpm}</td>
                    <td className="p-3">{v.engine_load_percent}%</td>
                    <td className="p-3">{v.map_pressure_kpa}</td>
                    <td className="p-3 font-bold text-amber-400">{v.fuel_rate_lph} L/h</td>
                    <td className="p-3">{Number(v.high_res_odometer_km).toLocaleString()} km</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Tab 4: Mode Split (computed server-side from fleet data) ── */}
      {activeTab === 'modesplit' && (
        <div className="p-6 space-y-6">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-indigo-400" />
            PHEV Mode Split &amp; OBD-II Fuel Economy Analytics
          </h2>
          {!esg ? (
            analyticsError ? (
              <p className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                Could not load analytics: {analyticsError}
              </p>
            ) : (
              <p className="text-sm text-slate-400">Loading analytics…</p>
            )
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
                  <span className="text-xs text-slate-400">Blended Fleet Economy</span>
                  <p className="text-3xl font-extrabold text-emerald-400 mt-1">{esg.efficiency_metrics.fleet_avg_mpg} MPG</p>
                  <p className="text-[11px] text-slate-500 mt-1">vs. {esg.efficiency_metrics.ice_baseline_mpg} MPG diesel benchmark</p>
                </div>
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
                  <span className="text-xs text-slate-400">Electric Miles Share</span>
                  <p className="text-3xl font-extrabold text-indigo-400 mt-1">{esg.mode_split.ev_share_percent}%</p>
                  <p className="text-[11px] text-slate-400 mt-1">{Math.round(esg.mode_split.ev_miles).toLocaleString()} EV traction miles</p>
                </div>
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
                  <span className="text-xs text-slate-400">Internal Combustion Share</span>
                  <p className="text-3xl font-extrabold text-amber-400 mt-1">{esg.mode_split.ice_share_percent}%</p>
                  <p className="text-[11px] text-slate-400 mt-1">{Math.round(esg.mode_split.ice_miles).toLocaleString()} ICE miles</p>
                </div>
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
                  <span className="text-xs text-slate-400">Fleet Fuel Burn (now)</span>
                  <p className="text-3xl font-extrabold text-cyan-400 mt-1">{esg.obd_diagnostics.fleet_instant_fuel_burn_lph} L/h</p>
                  <p className="text-[11px] text-slate-400 mt-1">{esg.obd_diagnostics.total_active_dtc_units} unit(s) with active DTCs</p>
                </div>
              </div>
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
                <span className="text-xs text-slate-400">Vehicles by powertrain mode right now</span>
                <div className="flex flex-wrap gap-3 mt-2">
                  {Object.entries(esg.mode_split.current_mode_counts).map(([mode, count]) => (
                    <span key={mode} className="text-xs px-3 py-1 rounded-full border border-slate-700 text-slate-300">
                      {modeBadge(mode).label}: <b className="text-white">{count}</b>
                    </span>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Tab 5: LEZ Geofences ── */}
      {activeTab === 'lez' && (
        <div className="p-6 space-y-6">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <MapPin className="w-5 h-5 text-emerald-400" />
            AI-Driven Geo-Fenced Low-Emission Zone (LEZ) Routing
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Globe2 className="w-4 h-4 text-emerald-400" />
                Active Low-Emission Zones (Municipal Geofences)
              </h3>
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 flex justify-between items-center">
                <div>
                  <span className="font-bold text-white text-xs">Chicago Clean Air LEZ Zone 1</span>
                  <p className="text-[11px] text-slate-400">Downtown Loop &amp; Central Logistics Terminal</p>
                </div>
                <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded font-semibold">
                  100% Zero-Emission Enforced
                </span>
              </div>
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 flex justify-between items-center">
                <div>
                  <span className="font-bold text-white text-xs">St. Louis Metro Green Freight Corridor</span>
                  <p className="text-[11px] text-slate-400">Interstate 64 Urban Ring</p>
                </div>
                <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded font-semibold">
                  Regen &amp; EV Preferred
                </span>
              </div>
            </div>
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Cpu className="w-4 h-4 text-indigo-400" />
                Amazon Bedrock Geo-Route Logic
              </h3>
              <ul className="text-xs text-slate-400 space-y-2 list-disc pl-5">
                <li>Bedrock verifies state of charge (&gt;15% required for zone entry).</li>
                <li>Pre-charges high-voltage battery via hybrid generator if below threshold.</li>
                <li>Locks out ICE fuel injection (PID 5E = 0.0 L/h) upon crossing geofence.</li>
                <li>Transmits verified zero-emission telemetry to municipal audit logs.</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab 6: ESG Offsets (computed server-side from fleet data) ── */}
      {activeTab === 'esg' && (
        <div className="p-6 space-y-6">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Leaf className="w-5 h-5 text-emerald-400" />
            Automated ESG Carbon Offset Reporting
          </h2>
          {!esg ? (
            analyticsError ? (
              <p className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                Could not load the ESG report: {analyticsError}
              </p>
            ) : (
              <p className="text-sm text-slate-400">Loading ESG report…</p>
            )
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
                  <span className="text-xs text-slate-400">Scope 1 CO2 Avoided</span>
                  <p className="text-3xl font-extrabold text-emerald-400 mt-1">
                    {Math.round(esg.esg_carbon_offsets.scope_1_co2_offset_kg).toLocaleString()} kg
                  </p>
                  <p className="text-[11px] text-slate-400 mt-1">
                    {(esg.esg_carbon_offsets.scope_1_co2_offset_kg / 1000).toFixed(2)} metric tons CO2e
                  </p>
                </div>
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
                  <span className="text-xs text-slate-400">Diesel Gallons Saved</span>
                  <p className="text-3xl font-extrabold text-amber-400 mt-1">
                    {Math.round(esg.esg_carbon_offsets.diesel_gallons_saved).toLocaleString()} gal
                  </p>
                  <p className="text-[11px] text-slate-400 mt-1">Avoided fossil combustion</p>
                </div>
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
                  <span className="text-xs text-slate-400">Scope 2 Grid CO2 (EV charging)</span>
                  <p className="text-3xl font-extrabold text-rose-400 mt-1">
                    {Math.round(esg.esg_carbon_offsets.scope_2_grid_co2_kg).toLocaleString()} kg
                  </p>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Net avoided: {Math.round(esg.esg_carbon_offsets.net_co2_avoided_kg).toLocaleString()} kg
                  </p>
                </div>
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
                  <span className="text-xs text-slate-400">Carbon Credit Value</span>
                  <p className="text-3xl font-extrabold text-cyan-400 mt-1">
                    ${esg.esg_carbon_offsets.carbon_credit_value_usd.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-1">
                    At ${esg.esg_carbon_offsets.carbon_credit_usd_per_tonne.toFixed(2)}/metric ton voluntary credit
                  </p>
                </div>
              </div>
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-1">
                <span className="text-xs text-slate-400">Low-emission zone compliance (measured)</span>
                <p className="text-sm text-slate-200">
                  {esg.lez_geo_compliance.lez_ev_enforcement_percent === null
                    ? 'No vehicles are currently inside a zero-emission zone.'
                    : `${esg.lez_geo_compliance.lez_ev_enforcement_percent}% of vehicles in zero-emission zones are running EV-only (${esg.lez_geo_compliance.compliant_vehicles}/${esg.lez_geo_compliance.strict_zone_vehicles}).`}
                </p>
                {esg.lez_geo_compliance.violations.map((v) => (
                  <p key={v.vehicle_id} className="text-xs text-red-300">
                    Violation: {v.vehicle_id} burning {v.fuel_rate_lph} L/h in {v.zone}
                  </p>
                ))}
              </div>
              {esg.data_source === 'fallback' && (
                <p className="text-[11px] text-amber-400">Figures use built-in sample data because the database is unreachable.</p>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Tab 7: Alerts (server-side rules engine) ── */}
      {activeTab === 'alerts' && (
        <AlertsPanel alerts={alerts} rules={alertRules} onAck={acknowledgeAlert} onLocate={locateVehicle} />
      )}

      {/* ── Tab 8: Conversational dispatch assistant ── */}
      {activeTab === 'assistant' && (
        <div className="p-6 max-w-3xl mx-auto">
          <ChatAssistant apiEndpoint={apiEndpoint} authHeader={authHeader} onUnauthorized={signOut} />
        </div>
      )}
    </div>
  );
}
