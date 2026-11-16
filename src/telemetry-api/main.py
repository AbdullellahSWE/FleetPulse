import os
import re
import uuid
import time
from typing import List, Literal, Optional

import boto3
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import ai
import alerts as alert_engine
from auth import require_group, verify_cognito_token
from fallback_data import FALLBACK_PHEV_FLEET, FALLBACK_TRAILERS
from geo import LEZ_GEOFENCES, apply_geofence, is_strict_zone

app = FastAPI(title="FleetPulse OBD-II Diagnostics, GPS Map & PHEV AI API", version="2.0.0")

# CORS: explicit origins only (comma-separated env). The dashboard is served same-origin through nginx,
# so no cross-origin access is needed in production. Bearer tokens are used, never cookies.
_origins = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

DTC_PATTERN = re.compile(r"^(NONE|P[0-3][0-9A-F]{3}(\s*,\s*P[0-3][0-9A-F]{3})*)$")
VEHICLE_ID_PATTERN = r"^[A-Za-z0-9_-]{1,40}$"


# ── Request models (validated; bad input returns 422 instead of a 500) ────────

class DispatchRequest(BaseModel):
    vehicle_id: str = Field("PHEV-9402", pattern=VEHICLE_ID_PATTERN)
    trailer_id: str = Field("TR-5011", pattern=VEHICLE_ID_PATTERN)
    powertrain_mode: Literal["EV_MODE", "HYBRID_MODE", "ICE_MODE", "REGEN_BRAKING"] = "HYBRID_MODE"
    battery_level: float = Field(50.0, ge=0, le=100)
    temperature_celsius: float = Field(35.0, ge=-60, le=150)
    fuel_level: float = Field(75.0, ge=0, le=100)
    latitude: float = Field(41.8819, ge=-90, le=90)
    longitude: float = Field(-87.6278, ge=-180, le=180)
    location_name: str = Field("Chicago Loop Hub", max_length=120)
    engine_rpm: int = Field(1400, ge=0, le=6000)
    engine_coolant_temp: float = Field(88.0, ge=-40, le=200)
    oil_pressure_psi: float = Field(44.0, ge=0, le=150)
    engine_load_percent: float = Field(50.0, ge=0, le=100)
    map_pressure_kpa: float = Field(101.3, ge=0, le=500)
    throttle_position_percent: float = Field(25.0, ge=0, le=100)
    fuel_rate_lph: float = Field(5.0, ge=0, le=200)
    high_res_odometer_km: float = Field(60000.0, ge=0)
    active_dtc_codes: str = Field("NONE", max_length=60)
    in_lez_zone: bool = False
    lez_zone_name: Optional[str] = Field(None, max_length=120)
    route_diagnostics: str = Field("Standard interstate linehaul route.", max_length=500)


class SnsAlertRequest(BaseModel):
    vehicle_id: str = Field("PHEV-UNKNOWN", pattern=VEHICLE_ID_PATTERN)
    trailer_id: str = Field("TR-UNKNOWN", pattern=VEHICLE_ID_PATTERN)
    powertrain_mode: str = Field("HYBRID_MODE", max_length=20)
    active_dtc_codes: str = Field("NONE", max_length=60)
    oil_pressure_psi: float = Field(40.0, ge=0, le=150)
    engine_load_percent: float = Field(50.0, ge=0, le=100)
    latitude: float = Field(41.8819, ge=-90, le=90)
    longitude: float = Field(-87.6298, ge=-180, le=180)


class TierChangeRequest(BaseModel):
    tier: Literal["Starter", "Professional", "Premium"] = "Professional"


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: List[ChatTurn] = Field(..., min_length=1, max_length=20)


# ── Data access: Aurora first, clearly-labelled fallback second ───────────────

def load_fleet() -> tuple:
    """Return (fleet, data_source). LEZ status is always derived from GPS, never trusted from storage."""
    source = "aurora"
    fleet = None
    try:
        from database import get_phev_fleet
        fleet = get_phev_fleet() or None
    except Exception as exc:
        print(f"Fleet DB read failed: {exc}")
    if not fleet:
        fleet, source = FALLBACK_PHEV_FLEET, "fallback"
    return [apply_geofence(v) for v in fleet], source


def refresh_alerts(fleet: list) -> None:
    """Evaluate the alert rules against the latest fleet snapshot (de-duplicated, SNS for critical)."""
    try:
        alert_engine.evaluate_fleet(fleet)
    except Exception as exc:  # alerting must never break a telemetry read
        print(f"Alert evaluation failed: {exc}")


@app.get("/health/liveness")
@app.get("/health/readiness")
def health_check():
    return {"status": "healthy", "service": "FleetPulse-GPS-OBD2-API"}


@app.get("/auth/config")
def auth_config():
    """Public, non-secret Cognito settings so the SPA can sign in without build-time configuration."""
    import auth as auth_module

    return {
        "region": auth_module.COGNITO_REGION,
        "user_pool_id": auth_module.COGNITO_USER_POOL_ID,
        "client_id": auth_module.COGNITO_CLIENT_ID,
        "configured": bool(auth_module.COGNITO_USER_POOL_ID and auth_module.COGNITO_CLIENT_ID),
        "dev_bypass": auth_module.AUTH_DEV_BYPASS,
    }


# ── Fleet & map ───────────────────────────────────────────────────────────────

@app.get("/telemetry/fleet")
@app.get("/fleet")
async def get_fleet(user: dict = Depends(verify_cognito_token)):
    """Live PHEV dual-powertrain, GPS and OBD-II vitals. LEZ flags are derived from GPS server-side."""
    fleet, source = load_fleet()
    refresh_alerts(fleet)
    return {
        "vehicles": fleet,
        "lez_geofences": LEZ_GEOFENCES,
        "data_source": source,
        "open_alerts": len([a for a in alert_engine.list_alerts(200) if not a["acknowledged"]]),
    }


@app.get("/api/v1/map/fleet-locations")
@app.get("/map/fleet-locations")
async def get_map_fleet_locations(user: dict = Depends(verify_cognito_token)):
    fleet, source = load_fleet()
    markers = [
        {
            "id": v["id"], "model_name": v["model_name"], "driver": v["driver"],
            "lat": v["latitude"], "lon": v["longitude"], "location_name": v["location_name"],
            "speed_kph": v["speed_kph"], "heading_deg": v["heading_deg"],
            "powertrain_mode": v["powertrain_mode"], "battery": v["battery"],
            "fuel_level": v["fuel_level"], "engine_rpm": v["engine_rpm"],
            "fuel_rate_lph": v["fuel_rate_lph"], "active_dtc": v["active_dtc_codes"],
            "in_lez": v["in_lez_zone"], "lez_name": v["lez_zone_name"], "status": v["status"],
        }
        for v in fleet
    ]
    return {"markers": markers, "geofences": LEZ_GEOFENCES, "data_source": source}


# ── Mode split & ESG (computed from fleet data; no hard-coded results) ────────

# Emission factors (documented assumptions, overridable via env)
DIESEL_KG_CO2_PER_LITRE = float(os.getenv("DIESEL_KG_CO2_PER_LITRE", "2.68"))
KG_CO2_PER_US_GALLON = DIESEL_KG_CO2_PER_LITRE * 3.78541  # ~10.15 kg per gallon
KG_CO2_PER_TREE_YEAR = 21.7
CARBON_CREDIT_USD_PER_TONNE = float(os.getenv("CARBON_CREDIT_USD_PER_TONNE", "45.0"))
ICE_BASELINE_MPG = float(os.getenv("ICE_BASELINE_MPG", "6.8"))
GRID_KG_CO2_PER_KWH = float(os.getenv("GRID_KG_CO2_PER_KWH", "0.386"))  # US average, scope 2
EV_KWH_PER_KM = float(os.getenv("EV_KWH_PER_KM", "1.6"))  # Class 8 electric traction estimate
KM_PER_MILE = 1.60934


def compute_esg(fleet: list) -> dict:
    n = len(fleet)
    ev_miles = sum(v["ev_miles_total"] for v in fleet)
    ice_miles = sum(v["ice_miles_total"] for v in fleet)
    total_miles = ev_miles + ice_miles
    ev_share = round(ev_miles / total_miles * 100, 1) if total_miles else 0.0
    mode_counts = {m: sum(1 for v in fleet if v["powertrain_mode"] == m) for m in ("EV_MODE", "HYBRID_MODE", "ICE_MODE", "REGEN_BRAKING")}

    offset = sum(v["co2_offset_kg"] for v in fleet)
    emitted = sum(v["co2_emissions_kg"] for v in fleet)
    gallons_saved = round(offset / KG_CO2_PER_US_GALLON, 1)

    # Scope 2: grid electricity consumed for EV miles
    ev_kwh = ev_miles * KM_PER_MILE * EV_KWH_PER_KM
    scope2_kg = round(ev_kwh * GRID_KG_CO2_PER_KWH, 1)

    fleet_mpg = round(sum(v["current_mpg"] for v in fleet) / n, 1) if n else 0.0
    ev_mpgs = [v["current_mpg"] for v in fleet if v["powertrain_mode"] == "EV_MODE"]
    ev_equiv_mpg = round(sum(ev_mpgs) / len(ev_mpgs), 1) if ev_mpgs else None
    multiplier = round(ev_equiv_mpg / ICE_BASELINE_MPG, 1) if ev_equiv_mpg else None

    in_lez = [v for v in fleet if v["in_lez_zone"]]
    # Only zones that mandate zero-emission operation count toward the enforcement rate;
    # "preferred" corridors (e.g. St. Louis) are reported in vehicles_in_lez but not as violations.
    strict = [v for v in in_lez if is_strict_zone(v.get("lez_zone_id"))]
    compliant = [v for v in strict if v["fuel_rate_lph"] <= 0.1]
    enforcement = round(len(compliant) / len(strict) * 100, 1) if strict else None
    dtc_units = [v for v in fleet if v.get("active_dtc_codes") not in ("NONE", "", None)]

    return {
        "summary": "FleetPulse OBD-II Diagnostics, GPS Map & ESG Report",
        "fleet_size": n,
        "obd_diagnostics": {
            "total_active_dtc_units": len(dtc_units),
            "flagged_dtcs": [{"vehicle_id": v["id"], "codes": v["active_dtc_codes"], "severity": v.get("dtc_severity", "WARNING")} for v in dtc_units],
            "fleet_instant_fuel_burn_lph": round(sum(v.get("fuel_rate_lph", 0.0) for v in fleet), 2),
            "avg_engine_load_percent": round(sum(v.get("engine_load_percent", 0.0) for v in fleet) / n, 1) if n else 0.0,
            "avg_throttle_position_percent": round(sum(v.get("throttle_position_percent", 0.0) for v in fleet) / n, 1) if n else 0.0,
        },
        "mode_split": {
            "ev_miles": ev_miles, "ice_miles": ice_miles, "total_miles": total_miles,
            "ev_share_percent": ev_share, "ice_share_percent": round(100 - ev_share, 1) if total_miles else 0.0,
            "current_mode_counts": mode_counts,
        },
        "efficiency_metrics": {
            "fleet_avg_mpg": fleet_mpg, "ev_mode_equivalent_mpg": ev_equiv_mpg,
            "ice_baseline_mpg": ICE_BASELINE_MPG, "efficiency_multiplier": multiplier,
        },
        "esg_carbon_offsets": {
            "scope_1_co2_emissions_kg": emitted, "scope_1_co2_offset_kg": offset,
            "scope_2_grid_co2_kg": scope2_kg, "net_co2_avoided_kg": round(offset - scope2_kg, 1),
            "diesel_gallons_saved": gallons_saved,
            "trees_planted_offset_equivalent": int(offset / KG_CO2_PER_TREE_YEAR),
            "carbon_credit_value_usd": round(offset / 1000.0 * CARBON_CREDIT_USD_PER_TONNE, 2),
            "carbon_credit_usd_per_tonne": CARBON_CREDIT_USD_PER_TONNE,
        },
        "lez_geo_compliance": {
            "vehicles_in_lez": len(in_lez), "strict_zone_vehicles": len(strict),
            "compliant_vehicles": len(compliant), "lez_ev_enforcement_percent": enforcement,
            "violations": [{"vehicle_id": v["id"], "zone": v["lez_zone_name"], "fuel_rate_lph": v["fuel_rate_lph"]} for v in strict if v["fuel_rate_lph"] > 0.1],
        },
    }


@app.get("/api/v1/analytics/mode-split-esg")
@app.get("/analytics/mode-split-esg")
async def get_mode_split_esg(user: dict = Depends(verify_cognito_token)):
    fleet, source = load_fleet()
    report = compute_esg(fleet)
    report["data_source"] = source
    return report


# ── AI: dispatch directive + conversational assistant (Amazon Bedrock) ───────

def _dispatch_prompt(r: DispatchRequest, zone_name: str, in_lez: bool) -> str:
    return (
        f"Analyze this PHEV Class 8 tractor + OBD-II telemetry:\n"
        f"- Unit: {r.vehicle_id} + {r.trailer_id}\n"
        f"- GPS: ({r.latitude:.4f}, {r.longitude:.4f}) - {r.location_name}\n"
        f"- Mode: {r.powertrain_mode} | LEZ geofence: {zone_name} (inside: {in_lez})\n"
        f"- OBD-II: RPM {r.engine_rpm}, coolant {r.engine_coolant_temp}C, oil {r.oil_pressure_psi} PSI, "
        f"load {r.engine_load_percent}%, MAP {r.map_pressure_kpa} kPa, throttle {r.throttle_position_percent}%, "
        f"fuel rate {r.fuel_rate_lph} L/h, odometer {r.high_res_odometer_km:.1f} km\n"
        f"- Active DTC codes: {r.active_dtc_codes}\n"
        f"- EV battery: {r.battery_level}%, {r.temperature_celsius}C\n"
        f"- Notes: {r.route_diagnostics}"
    )


def _simulated_dispatch(r: DispatchRequest, zone_name: str, in_lez: bool) -> str:
    dtc = "All OBD-II trouble codes clear (MIL off)."
    if "P0420" in r.active_dtc_codes and "P0524" in r.active_dtc_codes:
        dtc = "CRITICAL dual DTC [P0420 + P0524]: shut down ICE immediately, run EV only and route to the nearest heavy-vehicle depot."
    elif "P0420" in r.active_dtc_codes:
        dtc = "[P0420] catalyst efficiency below threshold: avoid ICE in urban corridors; schedule catalyst service within 500 km."
    elif "P0524" in r.active_dtc_codes or r.oil_pressure_psi < 28.0:
        dtc = "CRITICAL [P0524] oil pressure low (< 28 PSI): de-energize the combustion engine and continue on EV battery."
    lez = (
        f"{r.vehicle_id} is inside '{zone_name}'. Zero-emission EV lock: fuel rate must be 0.0 L/h."
        if in_lez else f"Outside all low-emission zones ({r.location_name}). Parallel hybrid is allowed for highway efficiency."
    )
    return (
        f"FLEETPULSE DISPATCH DIRECTIVE (simulated - not generated by a model)\n"
        f"Unit {r.vehicle_id} + {r.trailer_id} | ({r.latitude:.4f}, {r.longitude:.4f}) {r.location_name}\n\n"
        f"1. GPS Navigation & LEZ Compliance\n   {lez}\n\n"
        f"2. OBD-II DTC Mitigation\n   {dtc}\n\n"
        f"3. Dual-Powertrain Optimization\n   Load {r.engine_load_percent:.1f}%, throttle {r.throttle_position_percent:.1f}%, "
        f"MAP {r.map_pressure_kpa:.1f} kPa, fuel {r.fuel_rate_lph:.1f} L/h at {r.engine_rpm} RPM.\n\n"
        f"4. ESG Impact\n   Diesel avoided vs 14.2 L/h baseline: {max(0.0, 14.2 - r.fuel_rate_lph):.1f} L/h."
    )


@app.post("/ai/dispatch-assistant")
@app.post("/dispatch-assistant")
@app.post("/api/ai-dispatch")
async def ai_phev_obd_dispatch(req: DispatchRequest, user: dict = Depends(verify_cognito_token)):
    from geo import find_lez_zone

    zone = find_lez_zone(req.latitude, req.longitude)  # server-side geofence, ignores client flag
    in_lez = zone is not None
    zone_name = zone["name"] if zone else "None"

    result = ai.converse(ai.DISPATCH_SYSTEM, [{"role": "user", "content": _dispatch_prompt(req, zone_name, in_lez)}], max_tokens=1000)
    text = result.text if result.live else _simulated_dispatch(req, zone_name, in_lez)
    return {
        "vehicle_id": req.vehicle_id,
        "recommendation": text,
        "engine": result.engine,
        "model_id": result.model_id,
        "live": result.live,
        "fallback_code": result.fallback_code,
        "fallback_reason": result.fallback_reason,
        "geofence": {"in_lez_zone": in_lez, "zone": zone_name},
    }


@app.post("/ai/chat")
async def ai_chat(req: ChatRequest, user: dict = Depends(verify_cognito_token)):
    """Conversational dispatch assistant grounded in the live fleet snapshot and open alerts."""
    if req.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="The last message must come from the user.")
    fleet, source = load_fleet()
    snapshot = ai.fleet_snapshot(fleet, alert_engine.list_alerts(50))
    system = f"{ai.CHAT_SYSTEM}\n\n{snapshot}"
    history = [{"role": m.role, "content": m.content} for m in req.messages]

    result = ai.converse(system, history, max_tokens=700, temperature=0.2)
    reply = result.text if result.live else ai.simulated_chat_reply(req.messages[-1].content, fleet, alert_engine.list_alerts(50))
    return {
        "reply": reply,
        "engine": result.engine,
        "model_id": result.model_id,
        "live": result.live,
        "fallback_code": result.fallback_code,
        "fallback_reason": result.fallback_reason,
        "data_source": source,
    }


@app.get("/ai/status")
async def ai_status(user: dict = Depends(verify_cognito_token)):
    """Lightweight probe so the UI can show whether live Bedrock is usable (one tiny call)."""
    result = ai.converse("Reply with the single word OK.", [{"role": "user", "content": "ping"}], max_tokens=5, temperature=0.0)
    return {
        "live": result.live, "engine": result.engine, "model_id": result.model_id,
        "fallback_code": result.fallback_code, "fallback_reason": result.fallback_reason,
    }




# ── Alerts (rules engine) & manual SNS dispatch ──────────────────────────────

@app.get("/alerts")
@app.get("/api/v1/alerts")
async def get_alerts(user: dict = Depends(verify_cognito_token)):
    fleet, _ = load_fleet()
    refresh_alerts(fleet)  # evaluate on read so the list is current even without dashboard polling
    items = alert_engine.list_alerts(100)
    return {
        "alerts": items,
        "open": len([a for a in items if not a["acknowledged"]]),
        "rules": [{"id": r["id"], "severity": r["severity"], "title": r["title"]} for r in alert_engine.RULES],
    }


@app.post("/alerts/{alert_id}/ack")
@app.post("/api/v1/alerts/{alert_id}/ack")
async def ack_alert(alert_id: str, user: dict = Depends(verify_cognito_token)):
    updated = alert_engine.acknowledge(alert_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"alert": updated, "acknowledged_by": user.get("email", "unknown")}


@app.post("/telemetry/alert-sns")
@app.post("/alert-sns")
async def alert_sns(req: SnsAlertRequest, user: dict = Depends(verify_cognito_token)):
    topic = os.getenv("SNS_ALERT_TOPIC_ARN")
    operator = user.get("email", "unknown")
    message = (
        f"[FleetPulse Manual Critical Alert]\n"
        f"Vehicle:      {req.vehicle_id} ({req.powertrain_mode})\n"
        f"Trailer:      {req.trailer_id}\n"
        f"GPS Location: ({req.latitude:.4f}, {req.longitude:.4f})\n"
        f"Active DTC:   {req.active_dtc_codes}\n"
        f"Oil Pressure: {req.oil_pressure_psi} PSI\n"
        f"Engine Load:  {req.engine_load_percent}%\n"
        f"Operator:     {operator}"
    )
    if not topic:
        return {"status": "simulated", "message_id": str(uuid.uuid4()), "detail": "SNS_ALERT_TOPIC_ARN not set."}
    try:
        response = boto3.client("sns", region_name=os.getenv("AWS_REGION", "us-east-1")).publish(
            TopicArn=topic, Message=message, Subject=f"FleetPulse CRITICAL: {req.vehicle_id} ({req.active_dtc_codes})"[:100]
        )
        return {"status": "published", "message_id": response["MessageId"]}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"SNS publish error: {exc}")


# ── Modular trailers & subscriptions ─────────────────────────────────────────

@app.get("/api/v1/trailers")
@app.get("/trailers")
async def get_trailers(user: dict = Depends(verify_cognito_token)):
    try:
        from database import get_trailers_from_db
        trailers = get_trailers_from_db()
        if trailers:
            return {"trailers": trailers, "data_source": "aurora"}
    except Exception as exc:
        print(f"Trailer DB read failed: {exc}")
    return {"trailers": FALLBACK_TRAILERS, "data_source": "fallback"}


TIER_RATES = {"Starter": 3.0, "Professional": 6.0, "Premium": 9.0}


@app.get("/api/v1/billing/subscription")
@app.get("/billing/subscription")
async def get_subscription(user: dict = Depends(verify_cognito_token)):
    try:
        from database import get_subscription_account_from_db
        sub = get_subscription_account_from_db("acc-sibley-trans")
        if sub:
            return {"subscription": sub, "data_source": "aurora"}
    except Exception as exc:
        print(f"Subscription DB read failed: {exc}")
    return {
        "data_source": "fallback",
        "subscription": {
            "account_id": "acc-sibley-trans", "company_name": "Sibley Transportation Corp",
            "current_tier": "Professional", "price_per_vehicle_mo": 6.0,
            "active_vehicles_count": 4, "active_trailers_count": 4, "billing_status": "Active",
            "digital_inspections_enabled": True, "custom_rbac_enabled": False, "api_access_enabled": False,
            "monthly_estimate_usd": 48.0, "next_billing_cycle": "2026-12-16",
        },
    }


@app.post("/api/v1/billing/change-tier")
@app.post("/billing/change-tier")
async def change_subscription_tier(req: TierChangeRequest, user: dict = Depends(require_group("FleetAdmins", "DispatchManagers"))):
    try:
        from database import update_subscription_tier_in_db
        updated = update_subscription_tier_in_db("acc-sibley-trans", req.tier)
        if updated:
            return {"status": "tier_updated", "subscription": updated, "data_source": "aurora"}
    except Exception as exc:
        print(f"Subscription DB update failed: {exc}")
    rate = TIER_RATES[req.tier]
    return {
        "status": "tier_updated", "data_source": "fallback",
        "subscription": {
            "account_id": "acc-sibley-trans", "company_name": "Sibley Transportation Corp",
            "current_tier": req.tier, "price_per_vehicle_mo": rate, "monthly_estimate_usd": rate * 8,
            "digital_inspections_enabled": req.tier != "Starter",
            "custom_rbac_enabled": req.tier == "Premium", "api_access_enabled": req.tier == "Premium",
        },
    }

