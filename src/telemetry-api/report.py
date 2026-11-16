"""Fleet & ESG report rendered as a PDF (reportlab, pure Python - no system libraries needed).

build_fleet_report_pdf() is a pure function of the data it is given, so the PDF always matches what the
dashboard shows and is easy to test. Data that came from the built-in sample set is clearly labelled.
"""

import io
import time
from typing import List, Optional
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INDIGO = colors.HexColor("#4f46e5")
SLATE = colors.HexColor("#334155")
LIGHT = colors.HexColor("#f1f5f9")
RED = colors.HexColor("#dc2626")
AMBER = colors.HexColor("#d97706")
GREEN = colors.HexColor("#059669")
GRID = colors.HexColor("#cbd5e1")

MODE_LABELS = {
    "EV_MODE": "Pure Electric",
    "HYBRID_MODE": "Parallel Hybrid",
    "ICE_MODE": "ICE Drive",
    "REGEN_BRAKING": "Regen Braking",
}

_styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=_styles["Title"], fontSize=21, textColor=INDIGO, spaceAfter=2, alignment=0)
SUB = ParagraphStyle("Sub", parent=_styles["Normal"], fontSize=9, textColor=SLATE, spaceAfter=8)
H2 = ParagraphStyle("H2", parent=_styles["Heading2"], fontSize=13, textColor=SLATE, spaceBefore=12, spaceAfter=5)
BODY = ParagraphStyle("Body", parent=_styles["Normal"], fontSize=9, leading=12)
CELL = ParagraphStyle("Cell", parent=_styles["Normal"], fontSize=8, leading=10)
CELL_B = ParagraphStyle("CellB", parent=CELL, fontName="Helvetica-Bold")
NOTE = ParagraphStyle("Note", parent=_styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#64748b"))
BANNER = ParagraphStyle("Banner", parent=_styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#92400e"))
KPI_V = ParagraphStyle("KpiV", parent=_styles["Normal"], fontName="Helvetica-Bold", fontSize=15, leading=18, alignment=TA_CENTER, textColor=INDIGO)
KPI_L = ParagraphStyle("KpiL", parent=_styles["Normal"], fontSize=7.5, leading=9, alignment=TA_CENTER, textColor=SLATE)


def _p(text, style=CELL):
    return Paragraph(escape(str(text)), style)


def _num(value, digits=0, suffix=""):
    if value is None:
        return "n/a"
    return f"{value:,.{digits}f}{suffix}"


def _kpi_row(items):
    """items: list of (value, label). Renders a single row of KPI tiles."""
    cells = [[Paragraph(escape(v), KPI_V), Paragraph(escape(label), KPI_L)] for v, label in items]
    table = Table([[c[0] for c in cells], [c[1] for c in cells]], colWidths=[7.0 * inch / len(items)] * len(items))
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, GRID),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, GRID),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _data_table(header, rows, col_widths, zebra=True):
    # Header cells arrive already rendered by _white_header(); never str() a Paragraph (prints its repr).
    table = Table([list(header)] + rows, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), INDIGO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if zebra:
        style.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]))
    table.setStyle(TableStyle(style))
    return table


def _white_header(text):
    return Paragraph(f'<font color="white"><b>{escape(text)}</b></font>', CELL)


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(0.75 * inch, 0.5 * inch, "FleetPulse - Fleet & ESG Report")
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _summary_section(esg: dict, fleet: list, open_alerts: int) -> list:
    offsets = esg["esg_carbon_offsets"]
    split = esg["mode_split"]
    critical = len([v for v in fleet if v.get("status") == "Critical"])
    return [
        Paragraph("Executive summary", H2),
        _kpi_row([
            (str(esg["fleet_size"]), "Vehicles"),
            (f"{split['ev_share_percent']}%", "Electric miles share"),
            (_num(offsets["scope_1_co2_offset_kg"] / 1000.0, 2, " t"), "CO2 avoided (Scope 1)"),
            (f"${_num(offsets['carbon_credit_value_usd'], 2)}", "Carbon credit value"),
            (str(open_alerts), "Open alerts"),
        ]),
        Spacer(1, 5),
        Paragraph(
            f"{esg['fleet_size']} vehicles reporting; {critical} in critical condition and {esg['obd_diagnostics']['total_active_dtc_units']} "
            f"with active diagnostic trouble codes. Electric traction covers {split['ev_share_percent']}% of "
            f"{_num(split['total_miles'])} lifetime miles.",
            BODY,
        ),
    ]


def _fleet_section(fleet: list) -> list:
    header = [_white_header(h) for h in ("Vehicle", "Driver", "Mode", "Battery", "Fuel rate", "DTC codes", "Zone", "Status")]
    rows = []
    for v in fleet:
        status = v.get("status", "")
        color = {"Critical": "#dc2626", "Warning": "#d97706"}.get(status, "#059669")
        rows.append([
            _p(v["id"], CELL_B),
            _p(v.get("driver", "")),
            _p(MODE_LABELS.get(v.get("powertrain_mode"), v.get("powertrain_mode", ""))),
            _p(f"{v.get('battery', 0):.0f}% / {v.get('temp', 0):.0f} C"),
            _p(f"{v.get('fuel_rate_lph', 0):.1f} L/h"),
            _p(v.get("active_dtc_codes", "NONE")),
            _p(v.get("lez_zone_name") if v.get("in_lez_zone") else "-"),
            Paragraph(f'<font color="{color}"><b>{escape(status)}</b></font>', CELL),
        ])
    widths = [0.8, 0.8, 0.95, 0.95, 0.75, 0.9, 1.15, 0.7]
    return [Paragraph("Fleet status", H2), _data_table(header, rows, [w * inch for w in widths])]


def _mode_split_section(esg: dict) -> list:
    split = esg["mode_split"]
    eff = esg["efficiency_metrics"]
    obd = esg["obd_diagnostics"]
    header = [_white_header(h) for h in ("Metric", "Value")]
    rows = [
        [_p("Electric miles"), _p(f"{_num(split['ev_miles'])} ({split['ev_share_percent']}%)")],
        [_p("Combustion miles"), _p(f"{_num(split['ice_miles'])} ({split['ice_share_percent']}%)")],
        [_p("Fleet average economy"), _p(f"{eff['fleet_avg_mpg']} MPG (diesel baseline {eff['ice_baseline_mpg']} MPG)")],
        [_p("Instantaneous fleet fuel burn"), _p(f"{obd['fleet_instant_fuel_burn_lph']} L/h")],
        [_p("Average engine load / throttle"), _p(f"{obd['avg_engine_load_percent']}% / {obd['avg_throttle_position_percent']}%")],
    ]
    modes = ", ".join(f"{MODE_LABELS.get(k, k)}: {n}" for k, n in split["current_mode_counts"].items())
    return [
        Paragraph("Powertrain mode split", H2),
        _data_table(header, rows, [2.6 * inch, 4.4 * inch]),
        Spacer(1, 4),
        Paragraph(f"Vehicles by current mode - {escape(modes)}", NOTE),
    ]


def _esg_section(esg: dict) -> list:
    o = esg["esg_carbon_offsets"]
    header = [_white_header(h) for h in ("Carbon accounting", "Value")]
    rows = [
        [_p("Scope 1 emissions (fleet)"), _p(f"{_num(o['scope_1_co2_emissions_kg'])} kg CO2")],
        [_p("Scope 1 emissions avoided (recorded offset)"), _p(f"{_num(o['scope_1_co2_offset_kg'])} kg CO2")],
        [_p("Diesel CO2 avoided (modeled, EV miles vs diesel baseline)"), _p(f"{_num(o['modeled_diesel_co2_avoided_kg'])} kg CO2")],
        [_p("Scope 2 grid emissions (EV charging, modeled)"), _p(f"{_num(o['scope_2_grid_co2_kg'])} kg CO2")],
        [_p("Net CO2 avoided (modeled)"), Paragraph(f"<b>{_num(o['net_co2_avoided_kg'])} kg CO2</b>", CELL)],
        [_p("Diesel saved"), _p(f"{_num(o['diesel_gallons_saved'])} gallons")],
        [_p("Tree-year equivalent"), _p(f"{_num(o['trees_planted_offset_equivalent'])} trees")],
        [_p("Carbon credit value"), _p(f"${_num(o['carbon_credit_value_usd'], 2)} at ${o['carbon_credit_usd_per_tonne']:.2f} per tonne")],
    ]
    return [
        Paragraph("ESG carbon offsets", H2),
        _data_table(header, rows, [2.6 * inch, 4.4 * inch]),
        Spacer(1, 4),
        Paragraph(
            "Modeled values use lifetime electric miles, a US-average grid factor, an estimated electric consumption per km and the diesel "
            "baseline economy shown above; all are configurable on the server. The recorded Scope 1 offset comes from vehicle telemetry "
            "and is reported separately.", NOTE),
    ]


def _lez_section(esg: dict) -> list:
    z = esg["lez_geo_compliance"]
    rate = z["lez_ev_enforcement_percent"]
    line = (
        "No vehicles are currently inside a zero-emission zone."
        if rate is None
        else f"{rate}% of vehicles in zero-emission zones are running electric only ({z['compliant_vehicles']} of {z['strict_zone_vehicles']})."
    )
    out = [Paragraph("Low-emission zone compliance", H2), Paragraph(f"{escape(line)} Vehicles inside any zone: {z['vehicles_in_lez']}.", BODY)]
    for viol in z["violations"]:
        out.append(Paragraph(
            f'<font color="#dc2626"><b>Violation:</b></font> {escape(viol["vehicle_id"])} burning {viol["fuel_rate_lph"]} L/h in {escape(viol["zone"])}', BODY))
    return out


def _alerts_section(alerts: list) -> list:
    open_alerts = [a for a in alerts if not a.get("acknowledged")]
    out = [Paragraph("Open alerts", H2)]
    if not open_alerts:
        out.append(Paragraph("No open alerts. All monitored conditions are within limits.", BODY))
        return out
    header = [_white_header(h) for h in ("Severity", "Vehicle", "Alert", "Detail")]
    rows = []
    for a in open_alerts[:25]:
        color = "#dc2626" if a["severity"] == "CRITICAL" else "#d97706"
        rows.append([
            Paragraph(f'<font color="{color}"><b>{escape(a["severity"])}</b></font>', CELL),
            _p(a["vehicle_id"], CELL_B),
            _p(a["title"]),
            _p(a["detail"]),
        ])
    out.append(_data_table(header, rows, [0.8 * inch, 0.9 * inch, 2.0 * inch, 3.3 * inch]))
    if len(open_alerts) > 25:
        out.append(Paragraph(f"Showing 25 of {len(open_alerts)} open alerts.", NOTE))
    return out


def build_fleet_report_pdf(
    fleet: List[dict],
    esg: dict,
    alerts: List[dict],
    data_source: str = "aurora",
    generated_by: Optional[str] = None,
    generated_at: Optional[float] = None,
) -> bytes:
    """Render the Fleet & ESG report. Returns the PDF file content."""
    stamp = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(generated_at if generated_at is not None else time.time()))
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch, topMargin=0.7 * inch, bottomMargin=0.8 * inch,
        title="FleetPulse Fleet & ESG Report", author="FleetPulse", subject="PHEV fleet status, mode split and carbon offsets",
    )
    open_alerts = len([a for a in alerts if not a.get("acknowledged")])

    story = [
        Paragraph("FleetPulse Fleet &amp; ESG Report", H1),
        Paragraph(f"Generated {escape(stamp)}" + (f" by {escape(generated_by)}" if generated_by else ""), SUB),
    ]
    if data_source == "fallback":
        banner = Table([[Paragraph(
            "<b>Sample data.</b> The database was unreachable when this report was generated, so the figures below come from "
            "the built-in sample fleet and must not be used for compliance or billing.", BANNER)]], colWidths=[7.0 * inch])
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef3c7")), ("BOX", (0, 0), (-1, -1), 0.8, AMBER),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story += [banner, Spacer(1, 6)]

    story += _summary_section(esg, fleet, open_alerts)
    story += _fleet_section(fleet)
    story += [KeepTogether(_mode_split_section(esg))]
    story += [KeepTogether(_esg_section(esg))]
    story += _lez_section(esg)
    story += _alerts_section(alerts)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
