import os
import psycopg2
from fastapi import HTTPException

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@aurora-cluster.cluster-c1234.us-east-1.rds.amazonaws.com:5432/fleetpulse",
)


def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


def save_telemetry_to_aurora(vehicle_id: str, battery: float, temp: float, status: str):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO vehicle_telemetry (vehicle_id, battery_level, temperature_celsius, status, recorded_at)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (vehicle_id, battery, temp, status),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Failed to insert record into Aurora: {e}")
        return False


def get_fleet_vehicles() -> list:
    """Fetch the current state of all active vehicles from Aurora.
    
    Returns a list of vehicle dicts compatible with the frontend fleet schema,
    or an empty list if the DB is unavailable.
    """
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT ON (vehicle_id)
                vehicle_id,
                driver_name,
                battery_level,
                temperature_celsius,
                status,
                route_diagnostics,
                recorded_at
            FROM vehicle_telemetry
            ORDER BY vehicle_id, recorded_at DESC
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        return [
            {
                "id": row[0],
                "driver": row[1] or "Unknown",
                "battery": float(row[2]),
                "temp": float(row[3]),
                "status": row[4] or "Optimal",
                "diagnostics": row[5] or "No diagnostics available.",
            }
            for row in rows
        ]
    except Exception as e:
        print(f"Failed to fetch fleet vehicles from Aurora: {e}")
        return []
