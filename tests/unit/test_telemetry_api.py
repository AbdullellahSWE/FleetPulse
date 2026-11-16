"""Unit tests for the telemetry API: geofencing, alert rules, ESG maths, validation, auth and AI fallback."""

import os
import sys
import time
from pathlib import Path
from unittest import mock

import pytest

API_DIR = Path(__file__).resolve().parents[2] / "src" / "telemetry-api"
sys.path.insert(0, str(API_DIR))

# Configure auth before importing the app modules
os.environ.setdefault("COGNITO_USER_POOL_ID", "us-east-1_TESTPOOL")
os.environ.setdefault("COGNITO_CLIENT_ID", "test-client-id")
os.environ.pop("SNS_ALERT_TOPIC_ARN", None)

import ai  # noqa: E402
import alerts  # noqa: E402
import auth  # noqa: E402
import geo  # noqa: E402
from fallback_data import FALLBACK_PHEV_FLEET  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_alerts():
    alerts.reset()
    yield
    alerts.reset()


@pytest.fixture
def client(monkeypatch):
    """Client with auth dependency replaced by a fixed user (JWT crypto is tested separately)."""
    main.app.dependency_overrides[auth.verify_cognito_token] = lambda: {"email": "tester@fleetpulse.io", "cognito:groups": ["FleetAdmins"]}
    monkeypatch.setattr(main, "load_fleet", lambda: ([geo.apply_geofence(v) for v in FALLBACK_PHEV_FLEET], "fallback"))
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


# â”€â”€ Server-side geofencing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_haversine_known_distance():
    # Chicago -> St. Louis is about 421 km great-circle
    assert 410 < geo.haversine_km(41.8781, -87.6298, 38.6270, -90.1994) < 435


def test_point_in_chicago_zone():
    zone = geo.find_lez_zone(41.8819, -87.6278)
    assert zone and zone["id"] == "lez-chi-01"


def test_point_outside_all_zones():
    assert geo.find_lez_zone(39.7684, -86.1581) is None  # Indianapolis


def test_apply_geofence_overrides_stale_flag():
    stale = dict(FALLBACK_PHEV_FLEET[1])  # Joliet, stored as not in LEZ
    stale.update(in_lez_zone=True, lez_zone_name="Bogus Zone")
    out = geo.apply_geofence(stale)
    assert out["in_lez_zone"] is False and out["lez_zone_name"] == "None"


# â”€â”€ Alert rules engine â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _fleet():
    return [geo.apply_geofence(v) for v in FALLBACK_PHEV_FLEET]


def test_critical_dtc_fires_alert_and_notifies():
    notify = mock.Mock(return_value="msg-1")
    fired = alerts.evaluate_fleet(_fleet(), notify=notify)
    rule_ids = {(a["vehicle_id"], a["rule_id"]) for a in fired}
    assert ("PHEV-3310", "dtc_critical_oil") in rule_ids
    assert ("PHEV-3310", "dtc_catalyst") in rule_ids
    assert notify.call_count == len([a for a in fired if a["severity"] == "CRITICAL"])


def test_alerts_are_deduplicated():
    notify = mock.Mock(return_value=None)
    first = alerts.evaluate_fleet(_fleet(), notify=notify)
    second = alerts.evaluate_fleet(_fleet(), notify=notify)
    assert first and second == []


def test_alert_refires_after_condition_clears():
    notify = mock.Mock(return_value=None)
    fleet = _fleet()
    assert alerts.evaluate_fleet(fleet, notify=notify)
    healthy = [dict(v, active_dtc_codes="NONE", oil_pressure_psi=45.0, temp=30.0, engine_coolant_temp=80.0, battery=80.0, fuel_rate_lph=0.0) for v in fleet]
    assert alerts.evaluate_fleet(healthy, notify=notify) == []
    assert alerts.evaluate_fleet(fleet, notify=notify)  # same problem again -> fires again


def test_acknowledge_alert():
    alerts.evaluate_fleet(_fleet(), notify=mock.Mock(return_value=None))
    first = alerts.list_alerts()[0]
    assert alerts.acknowledge(first["id"])["acknowledged"] is True
    assert alerts.acknowledge("nope") is None


def test_battery_overtemp_rule():
    fleet = _fleet()
    assert fleet[0]["temp"] >= 45.0  # PHEV-9402 seeded at 47.8C
    fired = alerts.evaluate_fleet(fleet, notify=mock.Mock(return_value=None))
    assert ("PHEV-9402", "battery_overtemp") in {(a["vehicle_id"], a["rule_id"]) for a in fired}


# â”€â”€ ESG numbers are derived, not hard-coded â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_esg_is_computed_from_fleet():
    report = main.compute_esg(_fleet())
    total_offset = sum(v["co2_offset_kg"] for v in FALLBACK_PHEV_FLEET)
    assert report["esg_carbon_offsets"]["scope_1_co2_offset_kg"] == total_offset
    assert report["esg_carbon_offsets"]["carbon_credit_value_usd"] == round(total_offset / 1000 * 45.0, 2)
    assert report["esg_carbon_offsets"]["scope_2_grid_co2_kg"] > 0
    assert report["efficiency_metrics"]["efficiency_multiplier"] == round(92.4 / 6.8, 1)


def test_esg_changes_when_data_changes():
    base = main.compute_esg(_fleet())
    altered = _fleet()
    altered[0]["co2_offset_kg"] += 1000.0
    assert main.compute_esg(altered)["esg_carbon_offsets"]["scope_1_co2_offset_kg"] == base["esg_carbon_offsets"]["scope_1_co2_offset_kg"] + 1000.0


def test_lez_enforcement_rate_is_measured():
    fleet = _fleet()
    assert main.compute_esg(fleet)["lez_geo_compliance"]["lez_ev_enforcement_percent"] == 100.0
    fleet[0]["fuel_rate_lph"] = 5.0  # truck burning diesel inside Chicago LEZ
    report = main.compute_esg(fleet)
    assert report["lez_geo_compliance"]["lez_ev_enforcement_percent"] < 100.0
    assert report["lez_geo_compliance"]["violations"][0]["vehicle_id"] == "PHEV-9402"

# ── Endpoints, validation, AI fallback visibility ────────────────────────────

def test_fleet_endpoint_labels_data_source_and_runs_alerts(client):
    body = client.get("/telemetry/fleet", headers={"Authorization": "Bearer x"}).json()
    assert body["data_source"] == "fallback"
    assert body["open_alerts"] > 0
    assert all("lez_distance_km" in v for v in body["vehicles"])


def test_dispatch_validation_rejects_bad_input(client):
    r = client.post("/ai/dispatch-assistant", json={"latitude": 999})
    assert r.status_code == 422
    r = client.post("/ai/dispatch-assistant", json={"powertrain_mode": "WARP_DRIVE"})
    assert r.status_code == 422
    r = client.post("/ai/dispatch-assistant", json={"vehicle_id": "x; DROP TABLE"})
    assert r.status_code == 422


def test_dispatch_surfaces_ai_fallback_reason(client, monkeypatch):
    monkeypatch.setattr(ai, "converse", lambda *a, **k: ai.AiResult(None, ai.ENGINE_SIMULATED, "m", "InvalidApiKey", "OpenRouter rejected the API key"))
    body = client.post("/ai/dispatch-assistant", json={"vehicle_id": "PHEV-9402", "latitude": 41.8819, "longitude": -87.6278}).json()
    assert body["live"] is False and body["engine"] == "Simulated"
    assert body["fallback_code"] == "InvalidApiKey" and "API key" in body["fallback_reason"]
    assert "simulated" in body["recommendation"].lower()
    assert body["geofence"]["in_lez_zone"] is True  # derived from GPS, not the client flag


def test_dispatch_live_result(client, monkeypatch):
    monkeypatch.setattr(ai, "converse", lambda *a, **k: ai.AiResult("1. Do the thing", ai.ENGINE_LIVE, "model-x"))
    body = client.post("/ai/dispatch-assistant", json={}).json()
    assert body["live"] is True and body["recommendation"] == "1. Do the thing" and body["fallback_reason"] is None


def test_chat_requires_last_message_from_user(client):
    r = client.post("/ai/chat", json={"messages": [{"role": "assistant", "content": "hi"}]})
    assert r.status_code == 422


def test_chat_grounds_prompt_in_fleet_and_falls_back(client, monkeypatch):
    seen = {}

    def fake(system, messages, **kw):
        seen["system"] = system
        return ai.AiResult(None, ai.ENGINE_SIMULATED, "m", "ThrottlingException", "slow down")

    monkeypatch.setattr(ai, "converse", fake)
    body = client.post("/ai/chat", json={"messages": [{"role": "user", "content": "Which trucks have critical faults?"}]}).json()
    assert "PHEV-3310" in seen["system"]  # snapshot is in the system prompt
    assert "PHEV-3310" in body["reply"] and body["live"] is False and body["fallback_code"] == "ThrottlingException"


def test_alert_endpoints_and_ack(client):
    data = client.get("/alerts").json()
    assert data["open"] > 0 and data["rules"]
    alert_id = data["alerts"][0]["id"]
    assert client.post(f"/alerts/{alert_id}/ack").json()["alert"]["acknowledged"] is True
    assert client.post("/alerts/does-not-exist/ack").status_code == 404


def test_dashboard_routes_use_prefixes_cloudfront_forwards(client):
    """CloudFront only forwards /telemetry/*, /ai/* and /health/* with the Authorization header.
    Every endpoint the dashboard calls must live under one of those prefixes (regression: ESG/alerts 401 via CDN)."""
    forwarded = ("/telemetry/", "/ai/", "/health/")
    dashboard_paths = [
        "/telemetry/fleet", "/telemetry/alerts", "/telemetry/analytics/mode-split-esg",
        "/telemetry/alert-sns", "/ai/dispatch-assistant", "/ai/chat",
    ]
    registered = {getattr(r, "path", "") for r in main.app.routes}
    for path in dashboard_paths:
        assert path in registered, f"{path} is not registered"
        assert path.startswith(forwarded), f"{path} would not be forwarded by CloudFront"
    assert client.get("/telemetry/alerts").status_code == 200
    assert client.get("/telemetry/analytics/mode-split-esg").status_code == 200
    first = client.get("/telemetry/alerts").json()["alerts"][0]["id"]
    assert client.post(f"/telemetry/alerts/{first}/ack").status_code == 200


def test_change_tier_validates_tier(client):
    assert client.post("/billing/change-tier", json={"tier": "Platinum"}).status_code == 422
    ok = client.post("/billing/change-tier", json={"tier": "Premium"})
    assert ok.status_code == 200 and ok.json()["subscription"]["api_access_enabled"] is True


# ── Auth ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def real_auth_client():
    return TestClient(main.app)


def test_missing_and_demo_tokens_are_rejected(real_auth_client):
    assert real_auth_client.get("/telemetry/fleet").status_code == 401
    assert real_auth_client.get("/telemetry/fleet", headers={"Authorization": "Bearer demo"}).status_code in (401, 503)
    assert real_auth_client.get("/telemetry/fleet", headers={"Authorization": "Bearer not.a.jwt"}).status_code in (401, 503)


def test_dev_bypass_only_when_enabled(monkeypatch, real_auth_client):
    monkeypatch.setattr(auth, "AUTH_DEV_BYPASS", True)
    monkeypatch.setattr(main, "load_fleet", lambda: ([geo.apply_geofence(v) for v in FALLBACK_PHEV_FLEET], "fallback"))
    assert real_auth_client.get("/telemetry/fleet", headers={"Authorization": "Bearer demo"}).status_code == 200


def _make_token(private_pem, kid="k1", **claims):
    from jose import jwt as jose_jwt
    base = {"iss": auth.issuer(), "aud": auth.COGNITO_CLIENT_ID, "token_use": "id", "exp": int(time.time()) + 600, "email": "u@x.io", "cognito:groups": ["DispatchManagers"]}
    base.update(claims)
    return jose_jwt.encode(base, private_pem, algorithm="RS256", headers={"kid": kid})


@pytest.fixture
def rsa_keys(monkeypatch):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from jose import jwk

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    public_pem = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    jwk_dict = jwk.construct(public_pem, "RS256").to_dict()
    jwk_dict.update(kid="k1", use="sig", alg="RS256")
    monkeypatch.setattr(auth, "_load_jwks", lambda force=False: [jwk_dict])
    return private_pem


def test_valid_jwt_is_accepted(rsa_keys):
    claims = auth.decode_and_verify(_make_token(rsa_keys))
    assert claims["email"] == "u@x.io"


@pytest.mark.parametrize("override", [
    {"exp": int(time.time()) - 10},
    {"iss": "https://evil.example.com/pool"},
    {"aud": "someone-else"},
    {"token_use": "refresh"},
])
def test_bad_claims_are_rejected(rsa_keys, override):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        auth.decode_and_verify(_make_token(rsa_keys, **override))
    assert exc.value.status_code == 401


def test_token_signed_by_wrong_key_is_rejected(rsa_keys):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from fastapi import HTTPException

    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    with pytest.raises(HTTPException) as exc:
        auth.decode_and_verify(_make_token(other_pem))
    assert exc.value.status_code == 401


def test_group_authorization(rsa_keys):
    c = TestClient(main.app)
    token = _make_token(rsa_keys, **{"cognito:groups": ["Viewers"]})
    r = c.post("/billing/change-tier", json={"tier": "Premium"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    token = _make_token(rsa_keys)
    r = c.post("/billing/change-tier", json={"tier": "Premium"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200