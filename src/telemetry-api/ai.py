"""Amazon Bedrock access (Converse API) with an explicit, visible fallback.

Every call returns an AiResult. When Bedrock cannot be used the result carries
engine="Bedrock-Simulated" plus a machine-readable fallback_code and a human
readable fallback_reason so the UI can show *why* instead of silently
pretending the model answered.
"""

import os
from dataclasses import dataclass
from typing import List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
# claude-3-haiku reached end of life; use a current inference profile (override via env).
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")

ENGINE_LIVE = "Amazon Bedrock"
ENGINE_SIMULATED = "Bedrock-Simulated"

_client = None


@dataclass
class AiResult:
    text: Optional[str]
    engine: str
    model_id: str
    fallback_code: Optional[str] = None
    fallback_reason: Optional[str] = None

    @property
    def live(self) -> bool:
        return self.engine == ENGINE_LIVE


def _bedrock():
    global _client
    if _client is None:
        _client = boto3.client(
            "bedrock-runtime",
            region_name=AWS_REGION,
            config=Config(connect_timeout=5, read_timeout=45, retries={"max_attempts": 2, "mode": "standard"}),
        )
    return _client


def classify_error(exc: Exception) -> tuple:
    """Map an exception to (code, human-readable reason)."""
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "ClientError")
        message = exc.response.get("Error", {}).get("Message", str(exc))
        if code == "AccessDeniedException":
            return code, "The pod's IAM role is not allowed to call bedrock:InvokeModel (grant it in the EKS stack)."
        if code == "ResourceNotFoundException":
            return code, f"Model '{BEDROCK_MODEL_ID}' was not found or has reached end of life; set BEDROCK_MODEL_ID."
        if code == "ThrottlingException":
            return code, "Bedrock is throttling requests; retry shortly."
        if code == "ValidationException" and "not allowed for this account" in message:
            return code, "Bedrock model access is not enabled for this AWS account (enable model access in the Bedrock console)."
        if code == "ModelNotReadyException":
            return code, "The model is still warming up; retry shortly."
        return code, f"{code}: {message[:200]}"
    if isinstance(exc, BotoCoreError):
        return type(exc).__name__, f"Could not reach Bedrock: {str(exc)[:200]}"
    return type(exc).__name__, f"Unexpected error calling Bedrock: {str(exc)[:200]}"


def converse(system: str, messages: List[dict], max_tokens: int = 1000, temperature: float = 0.3) -> AiResult:
    """Call Bedrock. `messages` is [{"role": "user"|"assistant", "content": "text"}, ...]."""
    try:
        resp = _bedrock().converse(
            modelId=BEDROCK_MODEL_ID,
            system=[{"text": system}],
            messages=[{"role": m["role"], "content": [{"text": m["content"]}]} for m in messages],
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )
        text = "".join(block.get("text", "") for block in resp["output"]["message"]["content"])
        return AiResult(text=text, engine=ENGINE_LIVE, model_id=BEDROCK_MODEL_ID)
    except Exception as exc:  # classified, logged, and surfaced to the caller - never swallowed
        code, reason = classify_error(exc)
        print(f"Bedrock call failed [{code}]: {exc}")
        return AiResult(
            text=None,
            engine=ENGINE_SIMULATED,
            model_id=BEDROCK_MODEL_ID,
            fallback_code=code,
            fallback_reason=reason,
        )


DISPATCH_SYSTEM = (
    "You are the FleetPulse AI Diagnostics & Powertrain Dispatcher for a Class 8 PHEV freight fleet. "
    "Be concise, concrete and safety-first. Use exactly these four numbered sections: "
    "1. GPS Navigation & LEZ Compliance, 2. OBD-II DTC Mitigation, 3. Dual-Powertrain Optimization, "
    "4. ESG Impact (diesel litres saved, CO2 avoided)."
)

CHAT_SYSTEM = (
    "You are the FleetPulse conversational dispatch assistant. Answer questions about the fleet using ONLY the "
    "fleet snapshot provided. If something is not in the snapshot, say you do not have that data. "
    "Keep answers short; use bullet points for lists. Recommend concrete dispatch actions when relevant."
)


def fleet_snapshot(fleet: List[dict], alerts: List[dict]) -> str:
    lines = ["FLEET SNAPSHOT"]
    for v in fleet:
        lines.append(
            f"- {v['id']} ({v.get('model_name', '')}) driver {v.get('driver', '?')} | mode {v.get('powertrain_mode')} | "
            f"battery {v.get('battery')}% temp {v.get('temp')}C | fuel {v.get('fuel_level')}% rate {v.get('fuel_rate_lph')} L/h | "
            f"rpm {v.get('engine_rpm')} coolant {v.get('engine_coolant_temp')}C oil {v.get('oil_pressure_psi')} PSI | "
            f"DTC {v.get('active_dtc_codes')} | at {v.get('location_name')} "
            f"({v.get('latitude'):.4f}, {v.get('longitude'):.4f}) | in LEZ {v.get('in_lez_zone')} {v.get('lez_zone_name')} | "
            f"trailer {v.get('assigned_trailer')} | status {v.get('status')}"
        )
    open_alerts = [a for a in alerts if not a.get("acknowledged")][:10]
    lines.append("OPEN ALERTS: " + ("none" if not open_alerts else "; ".join(f"{a['vehicle_id']} {a['title']}" for a in open_alerts)))
    return "\n".join(lines)


def simulated_chat_reply(question: str, fleet: List[dict], alerts: List[dict]) -> str:
    """Deterministic, data-driven answer used only when Bedrock is unavailable."""
    q = question.lower()
    critical = [v for v in fleet if v.get("status") == "Critical" or v.get("dtc_severity") == "CRITICAL"]
    in_lez = [v for v in fleet if v.get("in_lez_zone")]
    low_batt = sorted(fleet, key=lambda v: v.get("battery", 100))[:2]
    if any(w in q for w in ("critical", "fault", "dtc", "problem", "attention", "urgent")):
        if not critical:
            return "No vehicles currently report critical faults."
        return "Vehicles needing attention:\n" + "\n".join(
            f"- {v['id']}: DTC {v.get('active_dtc_codes')} at {v.get('location_name')} (oil {v.get('oil_pressure_psi')} PSI)" for v in critical
        )
    if "lez" in q or "zone" in q or "emission" in q:
        if not in_lez:
            return "No vehicles are inside a low-emission zone right now."
        return "Inside a low-emission zone:\n" + "\n".join(f"- {v['id']} in {v.get('lez_zone_name')} (battery {v.get('battery')}%)" for v in in_lez)
    if "battery" in q or "charge" in q or "soc" in q:
        return "Lowest state of charge:\n" + "\n".join(f"- {v['id']}: {v.get('battery')}% ({v.get('powertrain_mode')})" for v in low_batt)
    if "alert" in q:
        open_alerts = [a for a in alerts if not a.get("acknowledged")]
        return f"{len(open_alerts)} open alert(s)." + ("".join(f"\n- {a['vehicle_id']}: {a['title']}" for a in open_alerts[:5]))
    return (
        f"Fleet of {len(fleet)} vehicles: {len(critical)} critical, {len(in_lez)} inside a low-emission zone. "
        "Ask about faults, LEZ status, battery levels or alerts. (Live Bedrock answers are unavailable right now.)"
    )
