import os
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

JWKS_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
jwks_client = PyJWKClient(JWKS_URL)
security = HTTPBearer()

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
