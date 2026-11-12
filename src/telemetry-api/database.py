import os
import psycopg2
from fastapi import HTTPException

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@aurora-cluster.cluster-c1234.us-east-1.rds.amazonaws.com:5432/fleetpulse")

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
            (vehicle_id, battery, temp, status)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Failed to insert record into Aurora: {e}")
        return False