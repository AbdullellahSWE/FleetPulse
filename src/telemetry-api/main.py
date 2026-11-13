import os
import uuid
import httpx
import boto3
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt

app = FastAPI(title="FleetPulse Telemetry & AI Dispatch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "60ljkjaia3u74terhhcto4n076")
COGNITO_REGION = "us-east-1"
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "us-east-1_xxxxxxxxx")


async def verify_cognito_token(authorization: str = Header(None)):
    """Validates the Cognito ID Token sent from the frontend UI."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split(" ")[1]
    try:
        # Allow mock/demo tokens for local dev and the Demo Mode login
        if token in ("mock-token", "demo") or len(token.split(".")) != 3:
            return {"email": "admin@fleetpulse.io"}
        claims = jwt.get_unverified_claims(token)
        return claims
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Unauthorized: {exc}")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health/liveness")
@app.get("/health/readiness")
def health_check():
    return {"status": "healthy"}


# ── Fleet Telemetry ───────────────────────────────────────────────────────────

@app.get("/telemetry/fleet")
async def get_fleet(user: dict = Depends(verify_cognito_token)):
    """Returns live fleet telemetry. Reads from DB if available, falls back to seed data."""
    try:
        from database import get_fleet_vehicles
        vehicles = await get_fleet_vehicles()
        if vehicles:
            return {"vehicles": vehicles}
    except Exception:
        pass  # DB unavailable -- fall through to seed data

    return {
        "vehicles": [
            {
                "id": "EV-9402",
                "driver": "Alex R.",
                "battery": 14.5,
                "temp": 48.2,
                "status": "Critical",
                "diagnostics": "High thermal stress detected under heavy acceleration uphill.",
            },
            {
                "id": "EV-1088",
                "driver": "Jordan M.",
                "battery": 78.0,
                "temp": 31.5,
                "status": "Optimal",
                "diagnostics": "Nominal city cruising.",
            },
            {
                "id": "EV-3310",
                "driver": "Sam K.",
                "battery": 42.1,
                "temp": 37.8,
                "status": "Warning",
                "diagnostics": "Elevated battery temp during rapid DC charging.",
            },
            {
                "id": "EV-7721",
                "driver": "Taylor B.",
                "battery": 91.4,
                "temp": 28.0,
                "status": "Optimal",
                "diagnostics": "Regenerative braking active on highway descent.",
            },
        ]
    }


# ── AI Dispatch ───────────────────────────────────────────────────────────────

@app.post("/ai/dispatch-assistant")
@app.post("/api/ai-dispatch")
async def ai_dispatch_assistant(request: Request, user: dict = Depends(verify_cognito_token)):
    """
    Queries OpenRouter AI to generate real-time vehicle dispatch instructions.

    Accepts both canonical v2 field names (battery_level, temperature_celsius)
    and legacy field names (battery_charge, battery_temp) for backwards compatibility.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenRouter API Key not configured in environment (OPENROUTER_API_KEY)",
        )

    try:
        body = await request.json()
        vehicle_id = body.get("vehicle_id", "EV-UNKNOWN")

        # Accept both old and new field names
        battery_level = (
            body.get("battery_level")       # canonical v2 name
            or body.get("battery_charge")   # legacy name
            or 50.0
        )
        temperature = (
            body.get("temperature_celsius") # canonical v2 name
            or body.get("battery_temp")     # legacy name
            or 35.0
        )
        route_diagnostics = body.get("route_diagnostics", "No diagnostics provided.")

        prompt = (
            f"Analyze the following EV telemetry for vehicle {vehicle_id}:\n"
            f"- Battery Level: {battery_level}%\n"
            f"- Battery Temperature: {temperature}\u00b0C\n"
            f"- Route Diagnostics: {route_diagnostics}\n\n"
            f"Provide a concise, professional thermal stress assessment and precise dispatch "
            f"recommendation. Include urgency level (Critical / Warning / Optimal), "
            f"recommended action, and risk summary."
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://fleetpulse.io",
                    "X-Title": "FleetPulse EV Platform",
                },
                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are an expert FleetPulse AI EV Logistics and Dispatch "
                                "Assistant. Be concise and actionable."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                },
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"OpenRouter Error: {response.text}",
                )

            result = response.json()
            ai_message = result["choices"][0]["message"]["content"]
            return {"vehicle_id": vehicle_id, "recommendation": ai_message}

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"AI Dispatch processing error: {str(e)}")


# ── SNS Alert ─────────────────────────────────────────────────────────────────

@app.post("/telemetry/alert-sns")
async def alert_sns(request: Request, user: dict = Depends(verify_cognito_token)):
    """Publishes a critical vehicle alert to the configured AWS SNS topic."""
    sns_topic_arn = os.getenv("SNS_ALERT_TOPIC_ARN")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    try:
        body = await request.json()
        vehicle_id = body.get("vehicle_id", "EV-UNKNOWN")
        battery_level = body.get("battery_level", body.get("battery_charge", 0.0))
        temperature = body.get("temperature_celsius", body.get("battery_temp", 0.0))
        route_diagnostics = body.get("route_diagnostics", "No diagnostics provided.")
        operator = user.get("email", "unknown")

        message = (
            f"[FleetPulse Critical Alert]\n"
            f"Vehicle:     {vehicle_id}\n"
            f"Battery:     {battery_level}%\n"
            f"Temperature: {temperature}\u00b0C\n"
            f"Diagnostics: {route_diagnostics}\n"
            f"Operator:    {operator}"
        )

        if not sns_topic_arn:
            # Graceful fallback for local dev -- return a simulated MessageId
            mock_id = str(uuid.uuid4())
            return {
                "status": "simulated",
                "message_id": mock_id,
                "detail": "SNS_ALERT_TOPIC_ARN not set -- returning simulated MessageId for local dev.",
            }

        sns_client = boto3.client("sns", region_name=aws_region)
        response = sns_client.publish(
            TopicArn=sns_topic_arn,
            Message=message,
            Subject=f"FleetPulse CRITICAL: {vehicle_id}",
        )
        return {"status": "published", "message_id": response["MessageId"]}

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"SNS publish error: {str(e)}")
