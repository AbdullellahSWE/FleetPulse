"""LLM access through OpenRouter (OpenAI-compatible chat completions API).

Every call returns an AiResult. When the model cannot be used the result carries
engine="Simulated" plus a machine-readable fallback_code and a human readable
fallback_reason, so the UI shows *why* instead of silently pretending a model answered.

Configuration (environment):
  OPENROUTER_API_KEY          required for live answers
  OPENROUTER_MODEL            primary model            (default openai/gpt-4o-mini)
  OPENROUTER_FALLBACK_MODELS  comma-separated, tried when the primary is retired/unavailable
"""

import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

import httpx

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
PRIMARY_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
FALLBACK_MODELS = [m.strip() for m in os.getenv("OPENROUTER_FALLBACK_MODELS", "meta-llama/llama-3.3-70b-instruct").split(",") if m.strip()]

ENGINE_LIVE = "OpenRouter"
ENGINE_SIMULATED = "Simulated"

# CloudFront gives the origin 30 s to answer, so the model call must finish well inside that.
HTTP_TIMEOUT = httpx.Timeout(22.0, connect=5.0)


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


def classify_http_error(status: int, message: str, model: str) -> Tuple[str, str, bool]:
    """Map an OpenRouter HTTP error to (code, human-readable reason, try_next_model)."""
    message = (message or "")[:160]
    if status == 401:
        return "InvalidApiKey", "OpenRouter rejected the API key (invalid or revoked). Update the openrouter-secret.", False
    if status == 402:
        return "InsufficientCredits", "The OpenRouter account is out of credits or over its key limit.", False
    if status == 403:
        return "Forbidden", f"OpenRouter refused the request: {message}", False
    if status == 404:
        return "ModelUnavailable", f"Model '{model}' is no longer available on OpenRouter; set OPENROUTER_MODEL.", True
    if status == 429:
        return "RateLimited", "OpenRouter is rate limiting requests; retry shortly.", True
    if status >= 500:
        return "ProviderError", f"OpenRouter/provider error (HTTP {status}); retry shortly.", True
    return f"HTTP{status}", f"OpenRouter returned HTTP {status}: {message}", False


def _error_message(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        err = body.get("error", body)
        return err.get("message", str(err)) if isinstance(err, dict) else str(err)
    except ValueError:
        return resp.text[:160]


def _call_model(api_key: str, model: str, system: str, messages: List[dict], max_tokens: int, temperature: float):
    """Returns (text, None) on success or (None, (code, reason, try_next)) on failure."""
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "system", "content": system}, *[{"role": m["role"], "content": m["content"]} for m in messages]],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://fleetpulse.local",
        "X-Title": "FleetPulse",
    }
    try:
        resp = httpx.post(f"{OPENROUTER_BASE_URL}/chat/completions", json=payload, headers=headers, timeout=HTTP_TIMEOUT)
    except httpx.TimeoutException:
        return None, ("Timeout", f"Model '{model}' did not answer in time.", True)
    except httpx.HTTPError as exc:
        return None, ("NetworkError", f"Could not reach OpenRouter: {type(exc).__name__}", True)

    if resp.status_code != 200:
        return None, classify_http_error(resp.status_code, _error_message(resp), model)
    try:
        text = (resp.json()["choices"][0]["message"]["content"] or "").strip()
    except (ValueError, KeyError, IndexError, TypeError):
        text = ""
    if not text:
        return None, ("EmptyResponse", f"Model '{model}' returned an empty answer.", True)
    return text, None


def converse(system: str, messages: List[dict], max_tokens: int = 1000, temperature: float = 0.3) -> AiResult:
    """Ask the model. `messages` is [{"role": "user"|"assistant", "content": "text"}, ...].

    Tries the primary model, then each fallback model when the failure is model-specific
    (retired, rate limited, provider error). Auth and credit errors stop immediately."""
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return AiResult(None, ENGINE_SIMULATED, PRIMARY_MODEL, "MissingApiKey", "OPENROUTER_API_KEY is not configured on the server.")

    last = ("Unknown", "No model could be reached.")
    for model in [PRIMARY_MODEL, *[m for m in FALLBACK_MODELS if m != PRIMARY_MODEL]]:
        text, err = _call_model(api_key, model, system, messages, max_tokens, temperature)
        if text is not None:
            return AiResult(text, ENGINE_LIVE, model)
        code, reason, try_next = err
        print(f"OpenRouter call failed [{code}] model={model}")  # never log the key or the prompt
        last = (code, reason)
        if not try_next:
            break
    return AiResult(None, ENGINE_SIMULATED, PRIMARY_MODEL, last[0], last[1])


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
    """Deterministic, data-driven answer used only when the language model is unavailable."""
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
        "Ask about faults, LEZ status, battery levels or alerts. (Live AI answers are unavailable right now.)"
    )
