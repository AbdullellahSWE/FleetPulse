"""Alert rules engine.

Evaluates each vehicle against a set of rules on every fleet read, keeps an
in-memory alert log with de-duplication (one alert per vehicle+rule until the
condition clears and re-triggers, or the cooldown elapses) and publishes
critical alerts to SNS.
"""

import os
import time
import uuid
import threading
from typing import Callable, Dict, List, Optional

import boto3

from geo import is_strict_zone

COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", "900"))
MAX_ALERTS = 200
LOW_SOC_FOR_LEZ_PERCENT = 15.0  # matches the "SoC > 15% required for zone entry" rule shown in the UI


RULES: List[dict] = [
    {
        "id": "dtc_critical_oil",
        "severity": "CRITICAL",
        "title": "Critical oil pressure DTC (P0524)",
        "when": lambda v: "P0524" in (v.get("active_dtc_codes") or "") or (
            v.get("powertrain_mode") != "EV_MODE" and 0 < float(v.get("oil_pressure_psi", 99)) < 28.0
        ),
        "detail": lambda v: f"Oil pressure {v.get('oil_pressure_psi')} PSI, codes {v.get('active_dtc_codes')}. Shut down ICE and continue on EV.",
    },
    {
        "id": "dtc_catalyst",
        "severity": "WARNING",
        "title": "Catalytic converter degradation (P0420)",
        "when": lambda v: "P0420" in (v.get("active_dtc_codes") or ""),
        "detail": lambda v: f"Codes {v.get('active_dtc_codes')}. Lock out ICE in urban corridors and schedule catalyst service.",
    },
    {
        "id": "battery_overtemp",
        "severity": "CRITICAL",
        "title": "HV battery over-temperature",
        "when": lambda v: float(v.get("temp", 0)) >= 45.0,
        "detail": lambda v: f"Battery temperature {v.get('temp')} C (limit 45 C).",
    },
    {
        "id": "lez_low_soc",
        "severity": "WARNING",
        "title": "In LEZ with low state of charge",
        "when": lambda v: bool(v.get("in_lez_zone")) and float(v.get("battery", 100)) < LOW_SOC_FOR_LEZ_PERCENT + 5.0,
        "detail": lambda v: f"Battery {v.get('battery')}% inside {v.get('lez_zone_name')}; zone requires > {LOW_SOC_FOR_LEZ_PERCENT:.0f}%.",
    },
    {
        "id": "lez_ice_violation",
        "severity": "CRITICAL",
        "title": "ICE running inside a zero-emission zone",
        "when": lambda v: bool(v.get("in_lez_zone")) and is_strict_zone(v.get("lez_zone_id")) and float(v.get("fuel_rate_lph", 0)) > 0.1,
        "detail": lambda v: f"Fuel rate {v.get('fuel_rate_lph')} L/h inside {v.get('lez_zone_name')} (EV mode enforced).",
    },
    {
        "id": "coolant_overtemp",
        "severity": "WARNING",
        "title": "Engine coolant over-temperature",
        "when": lambda v: float(v.get("engine_coolant_temp", 0)) >= 105.0,
        "detail": lambda v: f"Coolant {v.get('engine_coolant_temp')} C (limit 105 C).",
    },
]

_lock = threading.Lock()
_alerts: List[dict] = []
_active: Dict[str, float] = {}  # "vehicle|rule" -> last fired epoch seconds


def _publish_sns(alert: dict) -> Optional[str]:
    topic = os.getenv("SNS_ALERT_TOPIC_ARN")
    if not topic:
        return None
    try:
        resp = boto3.client("sns", region_name=os.getenv("AWS_REGION", "us-east-1")).publish(
            TopicArn=topic,
            Subject=f"FleetPulse {alert['severity']}: {alert['vehicle_id']} - {alert['title']}"[:100],
            Message=(
                f"[FleetPulse Automated Alert]\nVehicle: {alert['vehicle_id']}\nRule: {alert['title']}\n"
                f"Severity: {alert['severity']}\nDetail: {alert['detail']}\nLocation: {alert.get('location_name', '')}\n"
            ),
        )
        return resp["MessageId"]
    except Exception as exc:  # alerting must never break telemetry reads
        print(f"SNS publish failed for {alert['id']}: {exc}")
        return None


def evaluate_fleet(fleet: List[dict], notify: Callable[[dict], Optional[str]] = _publish_sns) -> List[dict]:
    """Run all rules over the fleet. Returns the alerts newly fired by this evaluation."""
    now = time.time()
    fired: List[dict] = []
    with _lock:
        triggered_keys = set()
        for vehicle in fleet:
            for rule in RULES:
                try:
                    hit = bool(rule["when"](vehicle))
                except (TypeError, ValueError):
                    hit = False
                if not hit:
                    continue
                key = f"{vehicle['id']}|{rule['id']}"
                triggered_keys.add(key)
                last = _active.get(key)
                if last is not None and (now - last) < COOLDOWN_SECONDS:
                    continue
                alert = {
                    "id": str(uuid.uuid4()),
                    "vehicle_id": vehicle["id"],
                    "rule_id": rule["id"],
                    "severity": rule["severity"],
                    "title": rule["title"],
                    "detail": rule["detail"](vehicle),
                    "location_name": vehicle.get("location_name", ""),
                    "latitude": vehicle.get("latitude"),
                    "longitude": vehicle.get("longitude"),
                    "created_at": now,
                    "acknowledged": False,
                    "sns_message_id": None,
                }
                _active[key] = now
                fired.append(alert)
                _alerts.insert(0, alert)
        # conditions that cleared may fire again on their next occurrence
        for key in list(_active):
            if key not in triggered_keys:
                del _active[key]
        del _alerts[MAX_ALERTS:]

    for alert in fired:  # network I/O outside the lock
        if alert["severity"] == "CRITICAL":
            alert["sns_message_id"] = notify(alert)
    return fired


def list_alerts(limit: int = 50) -> List[dict]:
    with _lock:
        return [dict(a) for a in _alerts[:limit]]


def acknowledge(alert_id: str) -> Optional[dict]:
    with _lock:
        for a in _alerts:
            if a["id"] == alert_id:
                a["acknowledged"] = True
                return dict(a)
    return None


def reset() -> None:
    """Clear all state (used by tests)."""
    with _lock:
        _alerts.clear()
        _active.clear()
