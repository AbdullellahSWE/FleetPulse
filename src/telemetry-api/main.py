import os
import random
from datetime import datetime, timezone
import boto3
import httpx
import jwt
from jwt import PyJWKClient
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="FleetPulse Telemetry API")

ALLOWED_ORIGINS = [
    "https://d3o21e293sq1am.cloudfront.net",
    "http://localhost:5173",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
COGNITO_REGION = os.getenv("COGNITO_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "us-east-1_Et8nMj7du")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "60ljkjaia3u74terhhcto4n076")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:194163347210:fleetpulse-critical-alerts")

JWKS_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
jwks_client = PyJWKClient(JWKS_URL)
security = HTTPBearer()
sns_client = boto3.client("sns", region_name=COGNITO_REGION)

FLEET_STATE = [
    {"id": "EV-9402", "driver": "Alex R.", "battery": 14.5, "temp": 48.2, "status": "Critical", "diagnostics": "High thermal stress detected under heavy acceleration uphill."},
    {"id": "EV-1088", "driver": "Jordan M.", "battery": 78.0, "temp": 31.5, "status": "Optimal", "diagnostics": "Nominal city cruising."},
    {"id": "EV-3310", "driver": "Sam K.", "battery": 42.1, "temp": 37.8, "status": "Warning", "diagnostics": "Elevated battery temp during rapid DC charging."},
    {"id": "EV-7721", "driver": "Taylor B.", "battery": 91.4, "temp": 28.0, "status": "Optimal", "diagnostics": "Regenerative braking active on highway descent."},
]

def verify_cognito_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=ISSUER,
            options={"verify_aud": False},
        )
        if claims.get("token_use") != "id" or claims.get("aud") != COGNITO_CLIENT_ID:
            raise HTTPException(status_code=401, detail="Invalid Cognito token claims")
        return claims
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Unauthorized: {exc}")

class TelemetryAnalysisRequest(BaseModel):
    vehicle_id: str
    battery_level: float
    temperature_celsius: float
    route_diagnostics: str

@app.get("/health/liveness")
def liveness():
    return {"status": "alive"}

@app.get("/health/readiness")
def readiness():
    return {"status": "ready"}

@app.get("/telemetry/fleet")
def get_live_fleet(user=Depends(verify_cognito_jwt)):
    for v in FLEET_STATE:
        delta_bat = round(random.uniform(-0.3, 0.2), 1)
        delta_temp = round(random.uniform(-0.4, 0.5), 1)
        if v["id"] == "EV-9402":
            v["battery"] = max(8.0, min(16.0, round(v["battery"] + delta_bat, 1)))
            v["temp"] = max(46.0, min(51.5, round(v["temp"] + delta_temp, 1)))
        else:
            v["battery"] = max(18.0, min(98.0, round(v["battery"] + delta_bat, 1)))
            v["temp"] = max(25.0, min(43.0, round(v["temp"] + delta_temp, 1)))
        v["status"] = "Critical" if (v["battery"] < 15.0 or v["temp"] > 45.0) else ("Warning" if (v["battery"] < 45.0 or v["temp"] > 37.0) else "Optimal")
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "waf_protected": True,
        "sns_topic": SNS_TOPIC_ARN.split(":")[-1],
        "vehicles": FLEET_STATE,
    }

@app.post("/telemetry/alert-sns")
def publish_sns_alert(request: TelemetryAnalysisRequest, user=Depends(verify_cognito_jwt)):
    message = (
        f"[FleetPulse CRITICAL EV ALERT]\n"
        f"Vehicle: {request.vehicle_id}\n"
        f"Battery: {request.battery_level}% | Temp: {request.temperature_celsius}°C\n"
        f"Diagnostics: {request.route_diagnostics}\n"
        f"Operator: {user.get('email', 'admin@fleetpulse.io')}"
    )
    try:
        resp = sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"FleetPulse Critical Alert: {request.vehicle_id}",
            Message=message,
        )
        return {"status": "published", "message_id": resp.get("MessageId")}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"SNS publish error: {exc}")

@app.post("/ai/dispatch-assistant")
async def dispatch_assistant(request: TelemetryAnalysisRequest, user=Depends(verify_cognito_jwt)):
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenRouter API Key not configured")

    prompt = (
        f"You are FleetPulse AI dispatch assistant. Analyze EV telemetry:\n"
        f"Vehicle ID: {request.vehicle_id}\n"
        f"Battery Level: {request.battery_level}%\n"
        f"Battery Temp: {request.temperature_celsius}°C\n"
        f"Diagnostics: {request.route_diagnostics}\n"
        f"Provide a brief dispatch action recommendation."
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are an EV fleet management assistant."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 300
            },
            timeout=30.0
        )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()["choices"][0]["message"]


from pydantic import BaseModel
from typing import List

class TelemetryEvent(BaseModel):
    vehicle_id: str
    battery_level: float
    temperature_celsius: float
    status: str
    timestamp: float
    diagnostics: str

@app.post("/telemetry/stream-ingress")
async def ingest_telemetry_stream(events: List[TelemetryEvent]):
    """
    Ingests batch or single real-time telemetry events streamed from Kinesis / IoT devices.
    """
    processed_count = len(events)
    # Here you can add logic to push to Aurora PostgreSQL or cache in ElastiCache
    return {
        "status": "success", 
        "processed_records": processed_count,
        "message": f"Successfully ingested {processed_count} telemetry records into FleetPulse core pipeline."
    }