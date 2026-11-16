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


def get_phev_fleet() -> list:
    """Fetch live PHEV fleet with GPS coordinates and full OBD-II vitals from Aurora."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id, model_name, driver_name, powertrain_mode,
                latitude, longitude, location_name, speed_kph, heading_deg,
                battery_level, battery_temp_celsius, fuel_level_percent,
                engine_rpm, engine_coolant_temp, oil_pressure_psi,
                engine_load_percent, map_pressure_kpa, throttle_position_percent,
                fuel_rate_lph, high_res_odometer_km, active_dtc_codes, dtc_description, dtc_severity,
                current_mpg, ev_miles_total, ice_miles_total, in_lez_zone, lez_zone_name,
                co2_emissions_kg_total, co2_offset_kg_total, assigned_trailer_id,
                ice_failure_mode, hybrid_failure_mode, status
            FROM phev_vehicles
            ORDER BY id ASC
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        return [
            {
                "id": r[0],
                "model_name": r[1],
                "driver": r[2],
                "powertrain_mode": r[3],
                # Real-time Map Coordinates
                "latitude": float(r[4]) if r[4] is not None else 41.8781,
                "longitude": float(r[5]) if r[5] is not None else -87.6298,
                "location_name": r[6] or "Midwest Freight Corridor",
                "speed_kph": float(r[7]) if r[7] is not None else 65.0,
                "heading_deg": float(r[8]) if r[8] is not None else 90.0,
                # Dual-Powertrain
                "battery": float(r[9]),
                "temp": float(r[10]),
                "fuel_level": float(r[11]),
                "engine_rpm": int(r[12]),
                "engine_coolant_temp": float(r[13]),
                "oil_pressure_psi": float(r[14]),
                # OBD-II Standard Diagnostics
                "engine_load_percent": float(r[15]) if r[15] is not None else 45.0,
                "map_pressure_kpa": float(r[16]) if r[16] is not None else 101.3,
                "throttle_position_percent": float(r[17]) if r[17] is not None else 20.0,
                "fuel_rate_lph": float(r[18]) if r[18] is not None else 4.0,
                "high_res_odometer_km": float(r[19]) if r[19] is not None else 50000.0,
                "active_dtc_codes": r[20] or "NONE",
                "dtc_description": r[21] or "All emission & powertrain sensors nominal.",
                "dtc_severity": r[22] or "NONE",
                # Performance & ESG
                "current_mpg": float(r[23]),
                "ev_miles_total": float(r[24]),
                "ice_miles_total": float(r[25]),
                "in_lez_zone": bool(r[26]),
                "lez_zone_name": r[27],
                "co2_emissions_kg": float(r[28]),
                "co2_offset_kg": float(r[29]),
                "assigned_trailer": r[30],
                "ice_failure_mode": r[31],
                "hybrid_failure_mode": r[32],
                "status": r[33],
                "diagnostics": f"Map GPS ({r[4]:.4f}, {r[5]:.4f}) • RPM {r[12]} • Load {r[15]}% • DTC: {r[20]}.",
            }
            for r in rows
        ]
    except Exception as e:
        print(f"Failed to fetch PHEV fleet with GPS map from Aurora: {e}")
        return []


def get_trailers_from_db() -> list:
    """Fetch modular trailer suites with coordinates from Aurora."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id, name, trailer_type, hardware_suite, assigned_vehicle_id, assigned_driver,
                latitude, longitude,
                battery_level, solar_generation_watts, tire_psi_avg, tire_pressure_status,
                abs_fault_code, cargo_load_status, cargo_volume_percent, cargo_confidence_score,
                current_yard_location, dwell_time_hours, hub_odometer_miles, hub_rotation_needed,
                tpms_sensors_online, status
            FROM trailer_assets
            ORDER BY id ASC
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        return [
            {
                "id": r[0],
                "name": r[1],
                "trailer_type": r[2],
                "hardware_suite": r[3],
                "assigned_vehicle_id": r[4],
                "assigned_driver": r[5],
                "latitude": float(r[6]) if r[6] is not None else 41.8781,
                "longitude": float(r[7]) if r[7] is not None else -87.6298,
                "battery_level": float(r[8]),
                "solar_generation_watts": float(r[9]),
                "tire_psi_avg": float(r[10]),
                "tire_pressure_status": r[11],
                "abs_fault_code": r[12],
                "cargo_load_status": r[13],
                "cargo_volume_percent": int(r[14]),
                "cargo_confidence_score": float(r[15]),
                "current_yard_location": r[16],
                "dwell_time_hours": float(r[17]),
                "hub_odometer_miles": float(r[18]),
                "hub_rotation_needed": bool(r[19]),
                "tpms_sensors_online": int(r[20]),
                "status": r[21],
            }
            for r in rows
        ]
    except Exception as e:
        print(f"Failed to fetch trailers from Aurora: {e}")
        return []


def update_phev_obd_telemetry_in_db(vehicle_id: str, updates: dict) -> bool:
    """Update live PHEV dual-powertrain, GPS location & OBD-II vitals in Aurora."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE phev_vehicles
            SET
                powertrain_mode = COALESCE(%s, powertrain_mode),
                latitude = COALESCE(%s, latitude),
                longitude = COALESCE(%s, longitude),
                location_name = COALESCE(%s, location_name),
                speed_kph = COALESCE(%s, speed_kph),
                battery_level = COALESCE(%s, battery_level),
                battery_temp_celsius = COALESCE(%s, battery_temp_celsius),
                fuel_level_percent = COALESCE(%s, fuel_level_percent),
                engine_rpm = COALESCE(%s, engine_rpm),
                engine_coolant_temp = COALESCE(%s, engine_coolant_temp),
                oil_pressure_psi = COALESCE(%s, oil_pressure_psi),
                engine_load_percent = COALESCE(%s, engine_load_percent),
                map_pressure_kpa = COALESCE(%s, map_pressure_kpa),
                throttle_position_percent = COALESCE(%s, throttle_position_percent),
                fuel_rate_lph = COALESCE(%s, fuel_rate_lph),
                high_res_odometer_km = COALESCE(%s, high_res_odometer_km),
                active_dtc_codes = COALESCE(%s, active_dtc_codes),
                dtc_description = COALESCE(%s, dtc_description),
                dtc_severity = COALESCE(%s, dtc_severity),
                current_mpg = COALESCE(%s, current_mpg),
                in_lez_zone = COALESCE(%s, in_lez_zone),
                lez_zone_name = COALESCE(%s, lez_zone_name),
                ice_failure_mode = COALESCE(%s, ice_failure_mode),
                hybrid_failure_mode = COALESCE(%s, hybrid_failure_mode),
                status = COALESCE(%s, status),
                last_ping = NOW()
            WHERE id = %s
            """,
            (
                updates.get("powertrain_mode"),
                updates.get("latitude"),
                updates.get("longitude"),
                updates.get("location_name"),
                updates.get("speed_kph"),
                updates.get("battery_level"),
                updates.get("battery_temp_celsius"),
                updates.get("fuel_level_percent"),
                updates.get("engine_rpm"),
                updates.get("engine_coolant_temp"),
                updates.get("oil_pressure_psi"),
                updates.get("engine_load_percent"),
                updates.get("map_pressure_kpa"),
                updates.get("throttle_position_percent"),
                updates.get("fuel_rate_lph"),
                updates.get("high_res_odometer_km"),
                updates.get("active_dtc_codes"),
                updates.get("dtc_description"),
                updates.get("dtc_severity"),
                updates.get("current_mpg"),
                updates.get("in_lez_zone"),
                updates.get("lez_zone_name"),
                updates.get("ice_failure_mode"),
                updates.get("hybrid_failure_mode"),
                updates.get("status"),
                vehicle_id,
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Failed to update OBD-II telemetry in DB: {e}")
        return False


def get_subscription_account_from_db(account_id: str = "acc-sibley-trans") -> dict:
    conn = get_db_connection()
    if not conn:
        return {}
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                account_id, company_name, current_tier, price_per_vehicle_mo,
                active_vehicles_count, active_trailers_count, billing_status,
                digital_inspections_enabled, custom_rbac_enabled, api_access_enabled,
                monthly_estimate_usd, next_billing_cycle
            FROM subscription_accounts
            WHERE account_id = %s
            """,
            (account_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            return {}
        return {
            "account_id": row[0],
            "company_name": row[1],
            "current_tier": row[2],
            "price_per_vehicle_mo": float(row[3]),
            "active_vehicles_count": int(row[4]),
            "active_trailers_count": int(row[5]),
            "billing_status": row[6],
            "digital_inspections_enabled": bool(row[7]),
            "custom_rbac_enabled": bool(row[8]),
            "api_access_enabled": bool(row[9]),
            "monthly_estimate_usd": float(row[10]),
            "next_billing_cycle": str(row[11]),
        }
    except Exception as e:
        print(f"Failed to fetch subscription: {e}")
        return {}


def update_subscription_tier_in_db(account_id: str, tier: str) -> dict:
    rates = {"Starter": 3.00, "Professional": 6.00, "Premium": 9.00}
    rate = rates.get(tier, 6.00)
    inspections = tier in ("Professional", "Premium")
    custom_rbac = tier == "Premium"
    api_access = tier == "Premium"

    conn = get_db_connection()
    if not conn:
        return {}
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE subscription_accounts
            SET
                current_tier = %s,
                price_per_vehicle_mo = %s,
                digital_inspections_enabled = %s,
                custom_rbac_enabled = %s,
                api_access_enabled = %s,
                monthly_estimate_usd = (%s * (active_vehicles_count + active_trailers_count))
            WHERE account_id = %s
            RETURNING
                account_id, company_name, current_tier, price_per_vehicle_mo,
                active_vehicles_count, active_trailers_count, billing_status,
                digital_inspections_enabled, custom_rbac_enabled, api_access_enabled,
                monthly_estimate_usd, next_billing_cycle
            """,
            (tier, rate, inspections, custom_rbac, api_access, rate, account_id),
        )
        row = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        if not row:
            return {}
        return {
            "account_id": row[0],
            "company_name": row[1],
            "current_tier": row[2],
            "price_per_vehicle_mo": float(row[3]),
            "active_vehicles_count": int(row[4]),
            "active_trailers_count": int(row[5]),
            "billing_status": row[6],
            "digital_inspections_enabled": bool(row[7]),
            "custom_rbac_enabled": bool(row[8]),
            "api_access_enabled": bool(row[9]),
            "monthly_estimate_usd": float(row[10]),
            "next_billing_cycle": str(row[11]),
        }
    except Exception as e:
        print(f"Failed to update subscription in DB: {e}")
        return {}
