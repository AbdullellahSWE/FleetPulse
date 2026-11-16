"""Low-Emission Zone geofences and server-side geofence evaluation."""

import math
from typing import Optional

# Municipal LEZ geofences (circular) shown on the map and enforced server-side
LEZ_GEOFENCES = [
    {
        "id": "lez-chi-01",
        "name": "Chicago Clean Air LEZ Zone 1",
        "center_lat": 41.8781,
        "center_lon": -87.6298,
        "radius_km": 12.5,
        "mandate": "Zero-Emission EV Mode Enforced",
        "severity": "CRITICAL_EV_LOCK",
    },
    {
        "id": "lez-stl-01",
        "name": "St. Louis Metro Green Freight Corridor",
        "center_lat": 38.6270,
        "center_lon": -90.1994,
        "radius_km": 18.0,
        "mandate": "Regen & EV Preferred",
        "severity": "ECO_RESTRICTION",
    },
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

def find_lez_zone(latitude: float, longitude: float) -> Optional[dict]:
    """Return the geofence containing the point (nearest centre wins), or None."""
    best = None
    best_dist = None
    for zone in LEZ_GEOFENCES:
        dist = haversine_km(latitude, longitude, zone["center_lat"], zone["center_lon"])
        if dist <= zone["radius_km"] and (best_dist is None or dist < best_dist):
            best, best_dist = zone, dist
    return best


def apply_geofence(vehicle: dict) -> dict:
    """Derive in_lez_zone / lez_zone_name from GPS instead of trusting stored flags.

    Returns a copy of the vehicle with the derived values plus lez_distance_km
    (distance to the containing zone's centre, or None when outside every zone).
    """
    zone = find_lez_zone(vehicle["latitude"], vehicle["longitude"])
    out = dict(vehicle)
    if zone:
        out["in_lez_zone"] = True
        out["lez_zone_name"] = zone["name"]
        out["lez_zone_id"] = zone["id"]
        out["lez_distance_km"] = round(
            haversine_km(vehicle["latitude"], vehicle["longitude"], zone["center_lat"], zone["center_lon"]), 2
        )
    else:
        out["in_lez_zone"] = False
        out["lez_zone_name"] = "None"
        out["lez_zone_id"] = None
        out["lez_distance_km"] = None
    return out

def is_strict_zone(zone_id: Optional[str]) -> bool:
    """True when the zone mandates zero-emission operation (CRITICAL_EV_LOCK), not just a preference."""
    return any(z["id"] == zone_id and z["severity"] == "CRITICAL_EV_LOCK" for z in LEZ_GEOFENCES)