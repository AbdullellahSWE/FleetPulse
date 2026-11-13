import boto3
import json
import psycopg2
import os

kinesis_client = boto3.client('kinesis', region_name='us-east-1')
STREAM_NAME = 'FleetPulse-TelemetryStream'

# Connect to Aurora / PostgreSQL using secret configuration
conn = psycopg2.connect(os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/fleetpulse"))
cursor = conn.cursor()

def process_stream():
    response = kinesis_client.describe_stream(StreamName=STREAM_NAME)
    shard_id = response['StreamDescription']['Shards'][0]['ShardId']
    
    iterator = kinesis_client.get_shard_iterator(
        StreamName=STREAM_NAME,
        ShardId=shard_id,
        ShardIteratorType='LATEST'
    )['ShardIterator']

    print("Consuming telemetry events and writing to database...")
    while iterator:
        records = kinesis_client.get_records(ShardIterator=iterator, Limit=20)
        for record in records['Records']:
            payload = json.loads(record['Data'].decode('utf-8'))
            
            # Insert into database table
            cursor.execute(
                "INSERT INTO telemetry_logs (vehicle_id, battery_level, temperature_celsius, status, timestamp) VALUES (%s, %s, %s, %s, %s)",
                (payload['vehicle_id'], payload['battery_level'], payload['temperature_celsius'], payload['status'], payload['timestamp'])
            )
            conn.commit()
            print(f"[DB SAVED] Vehicle {payload['vehicle_id']} inserted.")
            
        iterator = records.get('NextShardIterator')

if __name__ == '__main__':
    process_stream()
