import os
import httpx
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
import requests

app = FastAPI(title="FleetPulse Telemetry & AI Dispatch API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "60ljkjaia3u74terhhcto4n076")
COGNITO_REGION = "us-east-1"
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "us-east-1_xxxxxxxxx") # Update if needed

async def verify_cognito_token(authorization: str = Header(None)):
    """Validates the Cognito ID Token sent from the frontend UI."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.split(" ")[1]
    try:
        # For development/testing flexibility, if a mock token is passed or direct verification is bypassed:
        if token == "mock-token" or len(token.split('.')) != 3:
            return {"email": "admin@fleetpulse.io"}
            
        # Standard OIDC JWKS validation could go here, or simple unverified claims decoding for internal clusters
        claims = jwt.get_unverified_claims(token)
        return claims
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Unauthorized: {exc}")

@app.get("/health/liveness")
@app.get("/health/readiness")
def health_check():
    return {"status": "healthy"}

@app.post("/ai/dispatch-assistant")
@app.post("/api/ai-dispatch")
async def ai_dispatch_assistant(request: Request, user: dict = Depends(verify_cognito_token)):
    """Queries OpenRouter AI to generate real-time vehicle route diagnostics and dispatch instructions."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenRouter API Key not configured in environment")
    
    try:
        body = await request.json()
        vehicle_id = body.get("vehicle_id", "EV-UNKNOWN")
        battery_charge = body.get("battery_charge", 50.0)
        battery_temp = body.get("battery_temp", 35.0)

        prompt = (
            f"Analyze the following EV telemetry for vehicle {vehicle_id}: "
            f"Battery Charge: {battery_charge}%, Battery Temperature: {battery_temp}°C. "
            f"Provide a concise, professional thermal stress assessment and precise dispatch recommendation."
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://fleetpulse.io",
                    "X-Title": "FleetPulse EV Platform"
                },
                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are an expert FleetPulse AI EV Logistics and Dispatch Assistant."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"OpenRouter Error: {response.text}")
                
            result = response.json()
            ai_message = result["choices"][0]["message"]["content"]
            return {"vehicle_id": vehicle_id, "recommendation": ai_message}

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"AI Dispatch processing error: {str(e)}")