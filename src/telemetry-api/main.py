from fastapi import FastAPI, Response, status
import os

app = FastAPI(title="FleetPulse Telemetry API")

@app.get("/health/liveness")
def liveness():
    return {"status": "alive"}

@app.get("/health/readiness")
def readiness(response: Response):
    # Perform operational readiness check (e.g. DB connection)
    db_host = os.getenv("DB_HOST")
    if not db_host:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not ready", "reason": "Database uninitialized"}
    return {"status": "ready"}

@app.get("/api/v1/telemetry")
def get_telemetry():
    return {"service": "telemetry-api", "version": "1.0.0"}