import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="FleetPulse Telemetry API")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

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
async def dispatch_assistant(request: TelemetryAnalysisRequest):
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