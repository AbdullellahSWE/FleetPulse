"""Tests for the PDF Fleet & ESG report."""

import io
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader

API_DIR = Path(__file__).resolve().parents[2] / "src" / "telemetry-api"
sys.path.insert(0, str(API_DIR))

import alerts as alert_engine  # noqa: E402
import auth  # noqa: E402
import geo  # noqa: E402
import main  # noqa: E402
import report  # noqa: E402
from fallback_data import FALLBACK_PHEV_FLEET  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _fleet():
    return [geo.apply_geofence(v) for v in FALLBACK_PHEV_FLEET]


def _text(pdf_bytes: bytes) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_bytes)).pages)


@pytest.fixture(autouse=True)
def _reset_alerts():
    alert_engine.reset()
    yield
    alert_engine.reset()


@pytest.fixture
def client(monkeypatch):
    main.app.dependency_overrides[auth.verify_cognito_token] = lambda: {"email": "tester@fleetpulse.io", "cognito:groups": ["FleetAdmins"]}
    monkeypatch.setattr(main, "load_fleet", lambda: (_fleet(), "fallback"))
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def _build(**kw):
    fleet = _fleet()
    alert_engine.evaluate_fleet(fleet, notify=lambda a: None)
    return report.build_fleet_report_pdf(fleet, main.compute_esg(fleet), alert_engine.list_alerts(), **kw)


def test_builds_a_valid_pdf():
    pdf = _build()
    assert pdf.startswith(b"%PDF-") and pdf.rstrip().endswith(b"%%EOF")
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) >= 1
    assert reader.metadata.title == "FleetPulse Fleet & ESG Report"


def test_contains_the_real_numbers_from_the_dashboard_data():
    fleet = _fleet()
    esg = main.compute_esg(fleet)
    text = _text(_build(generated_by="ops@fleetpulse.io"))
    for vehicle in FALLBACK_PHEV_FLEET:
        assert vehicle["id"] in text
    assert f"{esg['mode_split']['ev_share_percent']}%" in text
    assert f"{esg['esg_carbon_offsets']['carbon_credit_value_usd']:,.2f}" in text
    assert "P0420" in text and "P0524" in text           # active fault codes
    assert "ops@fleetpulse.io" in text                   # who generated it
    for section in ("Executive summary", "Fleet status", "Powertrain mode split", "ESG carbon offsets", "Low-emission zone compliance", "Open alerts"):
        assert section in text


def test_no_python_object_text_leaks_into_the_pdf():
    """Regression: table headers once rendered as "Paragraph('caseSensitive': 1 ..." (a Paragraph repr)."""
    text = _text(_build())
    for leaked in ("Paragraph(", "caseSensitive", "fontName", "ParaFrag", "<font", "<b>", "</b>"):
        assert leaked not in text, f"raw markup/object text leaked into the PDF: {leaked}"
    for header in ("Vehicle", "Driver", "Mode", "Battery", "Fuel rate", "DTC codes", "Zone", "Status", "Severity", "Metric", "Value"):
        assert header in text


def test_report_is_compact_for_a_small_fleet():
    assert len(PdfReader(io.BytesIO(_build())).pages) <= 2


def test_sample_data_is_clearly_labelled():
    assert "Sample data" in _text(_build(data_source="fallback"))
    assert "Sample data" not in _text(_build(data_source="aurora"))


def test_acknowledged_alerts_are_left_out():
    fleet = _fleet()
    alert_engine.evaluate_fleet(fleet, notify=lambda a: None)
    for a in alert_engine.list_alerts():
        alert_engine.acknowledge(a["id"])
    text = _text(report.build_fleet_report_pdf(fleet, main.compute_esg(fleet), alert_engine.list_alerts()))
    assert "No open alerts" in text


def test_many_alerts_and_odd_characters_do_not_break_the_layout():
    fleet = _fleet()
    fleet[0]["driver"] = "Zo\u00eb <b>&</b> O'Brien"
    many = [{"id": str(i), "vehicle_id": f"V-{i}", "severity": "WARNING", "title": "Title & <tag>", "detail": "d" * 300, "acknowledged": False} for i in range(40)]
    pdf = report.build_fleet_report_pdf(fleet, main.compute_esg(fleet), many)
    text = _text(pdf)
    assert "Showing 25 of 40" in text and PdfReader(io.BytesIO(pdf)).pages


def test_endpoint_returns_a_downloadable_pdf(client):
    r = client.get("/telemetry/reports/fleet.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"].startswith('attachment; filename="fleetpulse-report-') and r.headers["content-disposition"].endswith('.pdf"')
    assert r.headers["cache-control"] == "no-store"
    assert r.content.startswith(b"%PDF-")
    assert "tester@fleetpulse.io" in _text(r.content)
    assert "Sample data" in _text(r.content)  # the test client serves fallback data


def test_endpoint_requires_login():
    r = TestClient(main.app).get("/telemetry/reports/fleet.pdf")
    assert r.status_code == 401


def test_endpoint_uses_a_prefix_cloudfront_forwards():
    assert "/telemetry/reports/fleet.pdf" in {getattr(r, "path", "") for r in main.app.routes}


def test_endpoint_failure_is_a_clean_500(client, monkeypatch):
    monkeypatch.setattr(report, "build_fleet_report_pdf", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    r = client.get("/telemetry/reports/fleet.pdf")
    assert r.status_code == 500 and r.json()["detail"] == "The PDF report could not be generated."
    assert "boom" not in r.text
