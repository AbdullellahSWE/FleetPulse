import json
import random
import time
import boto3

# Initialize Kinesis client (ensure AWS credentials and region us-east-1 are configured)
kinesis_client = boto3.client('kinesis', region_name='us-east-1')
STREAM_NAME = 'FleetPulse-TelemetryStream'

FLEET_VEHICLES = ['EV-9402', 'EV-1088', 'EV-3310', 'EV-7721']

def generate_telemetry_payload():
    vehicle_id = random.choice(FLEET_VEHICLES)
    battery = round(random.uniform(10.0, 95.0), 2)
    temp = round(random.uniform(28.0, 50.0), 2)
    
    status = 'Optimal'
    if battery < 20 or temp > 45:
        status = 'Critical'
    elif battery < 45 or temp > 36:
        status = 'Warning'

    return {
        "vehicle_id": vehicle_id,
        "battery_level": battery,
        "temperature_celsius": temp,
        "status": status,
        "timestamp": time.time(),
        "diagnostics": f"Live telemetry sync from {vehicle_id}."
    }

def stream_telemetry():
    print(f"Starting FleetPulse Kinesis Telemetry Producer -> Stream: {STREAM_NAME}")
    while True:
        payload = generate_telemetry_payload()
        try:
            response = kinesis_client.put_record(
                StreamName=STREAM_NAME,
                Data=json.dumps(payload),
                PartitionKey=payload['vehicle_id']
            )
            print(f"[KINESIS SENT] Vehicle: {payload['vehicle_id']} | Battery: {payload['battery_level']}% | Temp: {payload['temperature_celsius']}°C | ShardID: {response['ShardId']}")
        except Exception as e:
            print(f"[ERROR pushing to Kinesis]: {e}")
        
        time.sleep(2) # Send records every 2 seconds

if __name__ == '__main__':
    stream_telemetry()