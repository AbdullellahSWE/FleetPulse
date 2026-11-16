import boto3
import json
import psycopg2
import os

kinesis_client = boto3.client('kinesis', region_name='us-east-1')
STREAM_NAME = 'FleetPulse-TelemetryStream'

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/fleetpulse")

def get_db():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"Error connecting to Aurora: {e}")
        return None

def process_stream():
    response = kinesis_client.describe_stream(StreamName=STREAM_NAME)
    shard_id = response['StreamDescription']['Shards'][0]['ShardId']
    
    iterator = kinesis_client.get_shard_iterator(
        StreamName=STREAM_NAME,
        ShardId=shard_id,
        ShardIteratorType='LATEST'
    )['ShardIterator']

    print("Consuming OBD-II and PHEV dual-powertrain telemetry events into Aurora PostgreSQL...")
    while iterator:
        records = kinesis_client.get_records(ShardIterator=iterator, Limit=20)
        conn = get_db()
        if conn:
            cursor = conn.cursor()
            for record in records['Records']:
                try:
                    payload = json.loads(record['Data'].decode('utf-8'))
                    
                    # 1. Insert into general telemetry_logs with full OBD-II fields
                    cursor.execute(
                        """
                        INSERT INTO telemetry_logs (
                            vehicle_id, battery_level, temperature_celsius, status, timestamp,
                            powertrain_mode, fuel_level_percent, engine_rpm, engine_coolant_temp,
                            oil_pressure_psi, current_mpg, engine_load_percent, map_pressure_kpa,
                            throttle_position_percent, fuel_rate_lph, high_res_odometer_km,
                            active_dtc_codes, dtc_severity, lez_zone_active, lez_zone_name, co2_saved_kg
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            payload['vehicle_id'], payload['battery_level'], payload['battery_temp_celsius'],
                            payload['status'], payload['timestamp'], payload['powertrain_mode'],
                            payload.get('fuel_level_percent', 80.0), payload.get('engine_rpm', 0),
                            payload.get('engine_coolant_temp', 88.0), payload.get('oil_pressure_psi', 42.0),
                            payload.get('current_mpg', 50.0), payload.get('engine_load_percent', 45.0),
                            payload.get('map_pressure_kpa', 101.3), payload.get('throttle_position_percent', 20.0),
                            payload.get('fuel_rate_lph', 4.0), payload.get('high_res_odometer_km', 50000.0),
                            payload.get('active_dtc_codes', 'NONE'), payload.get('dtc_severity', 'NONE'),
                            payload.get('in_lez_zone', False), payload.get('lez_zone_name', 'None'),
                            payload.get('co2_saved_kg', 10.0)
                        )
                    )
                    
                    # 2. Update phev_vehicles table with OBD-II parameters
                    cursor.execute(
                        """
                        UPDATE phev_vehicles
                        SET
                            powertrain_mode = %s,
                            battery_level = %s,
                            battery_temp_celsius = %s,
                            fuel_level_percent = %s,
                            engine_rpm = %s,
                            engine_coolant_temp = %s,
                            oil_pressure_psi = %s,
                            engine_load_percent = %s,
                            map_pressure_kpa = %s,
                            throttle_position_percent = %s,
                            fuel_rate_lph = %s,
                            high_res_odometer_km = %s,
                            active_dtc_codes = %s,
                            dtc_description = %s,
                            dtc_severity = %s,
                            current_mpg = %s,
                            in_lez_zone = %s,
                            lez_zone_name = %s,
                            status = %s,
                            last_ping = NOW()
                        WHERE id = %s
                        """,
                        (
                            payload['powertrain_mode'], payload['battery_level'], payload['battery_temp_celsius'],
                            payload.get('fuel_level_percent', 80.0), payload.get('engine_rpm', 0),
                            payload.get('engine_coolant_temp', 88.0), payload.get('oil_pressure_psi', 42.0),
                            payload.get('engine_load_percent', 45.0), payload.get('map_pressure_kpa', 101.3),
                            payload.get('throttle_position_percent', 20.0), payload.get('fuel_rate_lph', 4.0),
                            payload.get('high_res_odometer_km', 50000.0), payload.get('active_dtc_codes', 'NONE'),
                            payload.get('dtc_description', 'Nominal'), payload.get('dtc_severity', 'NONE'),
                            payload.get('current_mpg', 50.0), payload.get('in_lez_zone', False),
                            payload.get('lez_zone_name', 'None'), payload['status'], payload['vehicle_id']
                        )
                    )
                    conn.commit()
                    print(f"[DB SAVED] OBD-II Telemetry for {payload['vehicle_id']} [{payload['powertrain_mode']}] | DTC: {payload.get('active_dtc_codes')}")
                except Exception as ex:
                    print(f"[ERROR processing record]: {ex}")
            cursor.close()
            conn.close()
            
        iterator = records.get('NextShardIterator')

if __name__ == '__main__':
    process_stream()
