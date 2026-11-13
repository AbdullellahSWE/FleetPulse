CREATE TABLE IF NOT EXISTS telemetry_logs (
    id SERIAL PRIMARY KEY,
    vehicle_id VARCHAR(50) NOT NULL,
    battery_level FLOAT NOT NULL,
    temperature_celsius FLOAT NOT NULL,
    status VARCHAR(50) NOT NULL,
    timestamp DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_telemetry_vehicle_id ON telemetry_logs(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry_logs(timestamp);
