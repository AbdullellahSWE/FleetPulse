-- ── Database Schema Expansion: Live GPS Coordinates, LEZ Geofences, OBD-II & PHEV Telemetry ──

CREATE TABLE IF NOT EXISTS telemetry_logs (
    id SERIAL PRIMARY KEY,
    vehicle_id VARCHAR(50) NOT NULL,
    battery_level FLOAT NOT NULL,
    temperature_celsius FLOAT NOT NULL,
    status VARCHAR(50) NOT NULL,
    timestamp DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- GPS Coordinates & Speed
    latitude FLOAT DEFAULT 41.8781,
    longitude FLOAT DEFAULT -87.6298,
    speed_kph FLOAT DEFAULT 65.0,
    heading_deg FLOAT DEFAULT 90.0,
    -- PHEV Dual-Powertrain & OBD-II Diagnostic Fields
    powertrain_mode VARCHAR(20) DEFAULT 'EV_MODE',
    fuel_level_percent FLOAT DEFAULT 85.0,
    engine_rpm INT DEFAULT 0,
    engine_coolant_temp FLOAT DEFAULT 88.0,
    oil_pressure_psi FLOAT DEFAULT 42.0,
    current_mpg FLOAT DEFAULT 62.5,
    ev_kwh_per_mile FLOAT DEFAULT 0.38,
    -- OBD-II Standard PIDs
    engine_load_percent FLOAT DEFAULT 48.5,
    map_pressure_kpa FLOAT DEFAULT 101.3,
    throttle_position_percent FLOAT DEFAULT 22.0,
    fuel_rate_lph FLOAT DEFAULT 4.2,
    high_res_odometer_km FLOAT DEFAULT 42100.5,
    active_dtc_codes VARCHAR(255) DEFAULT 'NONE',
    dtc_severity VARCHAR(30) DEFAULT 'NONE',
    ice_failure_mode VARCHAR(50) DEFAULT 'NONE',
    hybrid_failure_mode VARCHAR(50) DEFAULT 'NONE',
    lez_zone_active BOOLEAN DEFAULT FALSE,
    lez_zone_name VARCHAR(100) DEFAULT 'None',
    co2_saved_kg FLOAT DEFAULT 14.2
);

CREATE INDEX IF NOT EXISTS idx_telemetry_vehicle_id ON telemetry_logs(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_telemetry_powertrain ON telemetry_logs(powertrain_mode);
CREATE INDEX IF NOT EXISTS idx_telemetry_dtc ON telemetry_logs(active_dtc_codes);

-- PHEV Vehicles Master with GPS Map Coordinates & OBD-II
CREATE TABLE IF NOT EXISTS phev_vehicles (
    id VARCHAR(50) PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    driver_name VARCHAR(100) NOT NULL,
    powertrain_mode VARCHAR(20) NOT NULL DEFAULT 'HYBRID_MODE',
    -- Real-time Map Location
    latitude FLOAT NOT NULL DEFAULT 41.8781,
    longitude FLOAT NOT NULL DEFAULT -87.6298,
    location_name VARCHAR(100) NOT NULL DEFAULT 'Chicago Downtown Logistics Center',
    speed_kph FLOAT NOT NULL DEFAULT 42.0,
    heading_deg FLOAT NOT NULL DEFAULT 120.0,
    -- Dual-Powertrain
    battery_level FLOAT NOT NULL DEFAULT 68.5,
    battery_temp_celsius FLOAT NOT NULL DEFAULT 34.0,
    fuel_level_percent FLOAT NOT NULL DEFAULT 82.0,
    fuel_tank_capacity_gal FLOAT NOT NULL DEFAULT 120.0,
    -- OBD-II Live Vitals
    engine_rpm INT NOT NULL DEFAULT 1450,
    engine_coolant_temp FLOAT NOT NULL DEFAULT 89.0,
    oil_pressure_psi FLOAT NOT NULL DEFAULT 44.0,
    engine_load_percent FLOAT NOT NULL DEFAULT 52.0,
    map_pressure_kpa FLOAT NOT NULL DEFAULT 104.2,
    throttle_position_percent FLOAT NOT NULL DEFAULT 28.5,
    fuel_rate_lph FLOAT NOT NULL DEFAULT 5.8,
    high_res_odometer_km FLOAT NOT NULL DEFAULT 58490.2,
    active_dtc_codes VARCHAR(255) NOT NULL DEFAULT 'NONE',
    dtc_description TEXT DEFAULT 'All emission & powertrain sensors nominal.',
    dtc_severity VARCHAR(30) NOT NULL DEFAULT 'NONE',
    current_mpg FLOAT NOT NULL DEFAULT 58.2,
    ev_kwh_per_mile FLOAT NOT NULL DEFAULT 0.39,
    ev_miles_total FLOAT NOT NULL DEFAULT 18450.0,
    ice_miles_total FLOAT NOT NULL DEFAULT 24680.0,
    in_lez_zone BOOLEAN NOT NULL DEFAULT FALSE,
    lez_zone_name VARCHAR(100) DEFAULT 'None',
    co2_emissions_kg_total FLOAT NOT NULL DEFAULT 1240.0,
    co2_offset_kg_total FLOAT NOT NULL DEFAULT 3850.0,
    assigned_trailer_id VARCHAR(50),
    ice_failure_mode VARCHAR(50) DEFAULT 'NONE',
    hybrid_failure_mode VARCHAR(50) DEFAULT 'NONE',
    status VARCHAR(30) NOT NULL DEFAULT 'Optimal',
    last_ping TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed initial PHEV Fleet with Precise Coordinates for the Midwest Corridor
INSERT INTO phev_vehicles (
    id, model_name, driver_name, powertrain_mode,
    latitude, longitude, location_name, speed_kph, heading_deg,
    battery_level, battery_temp_celsius, fuel_level_percent,
    engine_rpm, engine_coolant_temp, oil_pressure_psi,
    engine_load_percent, map_pressure_kpa, throttle_position_percent,
    fuel_rate_lph, high_res_odometer_km, active_dtc_codes, dtc_description, dtc_severity,
    current_mpg, ev_miles_total, ice_miles_total, in_lez_zone, lez_zone_name,
    co2_emissions_kg_total, co2_offset_kg_total, assigned_trailer_id,
    ice_failure_mode, hybrid_failure_mode, status
) VALUES
(
    'PHEV-9402', 'Freightliner Cascadia Hybrid', 'Alex R.', 'EV_MODE',
    41.8819, -87.6278, 'Chicago Loop Clean Air Zone (Downtown Hub)', 34.5, 88.0,
    18.5, 47.8, 74.0,
    0, 42.0, 0.0,
    0.0, 101.3, 14.2,
    0.0, 58914.8, 'NONE', 'Pure electric traction. Zero ICE emissions inside LEZ.', 'NONE',
    92.4, 22410.0, 14200.0, TRUE, 'Chicago Clean Air LEZ Zone 1',
    412.0, 4820.0, 'TR-5011',
    'NONE', 'NONE', 'Warning'
),
(
    'PHEV-1088', 'Volvo VNR Dual-Drive PHEV', 'Jordan M.', 'HYBRID_MODE',
    41.5250, -88.0817, 'Joliet Intermodal Freight Gateway (I-80 Corridor)', 88.5, 235.0,
    76.0, 32.5, 88.0,
    1380, 89.5, 46.0,
    44.0, 118.5, 31.0,
    4.6, 96810.4, 'NONE', 'Closed-loop stoichiometric fuel control. Parallel hybrid cruising.', 'NONE',
    56.8, 31200.0, 28950.0, FALSE, 'None',
    1140.0, 3940.0, 'TR-3088',
    'NONE', 'NONE', 'Optimal'
),
(
    'PHEV-3310', 'Peterbilt 579 Hybrid', 'Sam K.', 'ICE_MODE',
    39.7684, -86.1581, 'Indianapolis Crossroads Logistics Depot', 72.0, 160.0,
    34.5, 38.2, 38.0,
    1720, 96.5, 26.5,
    78.0, 142.0, 54.0,
    11.4, 85620.1, 'P0420, P0524', 'P0420 Catalyst Degradation; P0524 Low Oil Pressure (26.5 PSI).', 'CRITICAL',
    24.5, 14800.0, 38400.0, FALSE, 'None',
    2480.0, 1920.0, 'TR-2204',
    'CATALYTIC_DEGRADATION', 'NONE', 'Critical'
),
(
    'PHEV-7721', 'Kenworth T680 PHEV EcoLine', 'Taylor B.', 'REGEN_BRAKING',
    38.6270, -90.1994, 'St. Louis Gateway Green Freight Corridor (I-64)', 56.0, 275.0,
    89.2, 29.0, 92.0,
    850, 86.0, 45.0,
    18.0, 98.4, 8.0,
    1.2, 76210.6, 'NONE', 'Regen brake recovery active. Deceleration fuel cut on descent.', 'NONE',
    78.5, 28900.0, 18450.0, TRUE, 'St. Louis Metro Green Freight Corridor',
    640.0, 4410.0, 'TR-1049',
    'NONE', 'NONE', 'Optimal'
) ON CONFLICT (id) DO UPDATE SET
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    location_name = EXCLUDED.location_name,
    speed_kph = EXCLUDED.speed_kph,
    heading_deg = EXCLUDED.heading_deg,
    engine_load_percent = EXCLUDED.engine_load_percent,
    map_pressure_kpa = EXCLUDED.map_pressure_kpa,
    throttle_position_percent = EXCLUDED.throttle_position_percent,
    fuel_rate_lph = EXCLUDED.fuel_rate_lph,
    high_res_odometer_km = EXCLUDED.high_res_odometer_km,
    active_dtc_codes = EXCLUDED.active_dtc_codes,
    dtc_description = EXCLUDED.dtc_description,
    dtc_severity = EXCLUDED.dtc_severity;

-- Trailers / Sensor Suites Table
CREATE TABLE IF NOT EXISTS trailer_assets (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    trailer_type VARCHAR(50) NOT NULL,
    hardware_suite VARCHAR(50) NOT NULL,
    assigned_vehicle_id VARCHAR(50),
    assigned_driver VARCHAR(100),
    latitude FLOAT DEFAULT 41.8781,
    longitude FLOAT DEFAULT -87.6298,
    battery_level FLOAT NOT NULL DEFAULT 100.0,
    solar_generation_watts FLOAT NOT NULL DEFAULT 0.0,
    tire_psi_avg FLOAT NOT NULL DEFAULT 102.0,
    tire_pressure_status VARCHAR(20) NOT NULL DEFAULT 'Optimal',
    abs_fault_code VARCHAR(50) DEFAULT 'NONE',
    cargo_load_status VARCHAR(30) NOT NULL DEFAULT 'Empty',
    cargo_volume_percent INT NOT NULL DEFAULT 0,
    cargo_confidence_score FLOAT NOT NULL DEFAULT 0.95,
    current_yard_location VARCHAR(100) NOT NULL DEFAULT 'Yard Alpha (Chicago Hub)',
    dwell_time_hours FLOAT NOT NULL DEFAULT 0.0,
    hub_odometer_miles FLOAT NOT NULL DEFAULT 12450.0,
    hub_rotation_needed BOOLEAN NOT NULL DEFAULT FALSE,
    tpms_sensors_online INT NOT NULL DEFAULT 8,
    status VARCHAR(30) NOT NULL DEFAULT 'Optimal',
    last_ping TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trailer_hardware ON trailer_assets(hardware_suite);
CREATE INDEX IF NOT EXISTS idx_trailer_yard ON trailer_assets(current_yard_location);

-- Seed Trailer Assets with Sibley Transportation case study metrics
INSERT INTO trailer_assets (
    id, name, trailer_type, hardware_suite, assigned_vehicle_id, assigned_driver,
    latitude, longitude,
    battery_level, solar_generation_watts, tire_psi_avg, tire_pressure_status, abs_fault_code,
    cargo_load_status, cargo_volume_percent, cargo_confidence_score,
    current_yard_location, dwell_time_hours, hub_odometer_miles, hub_rotation_needed,
    tpms_sensors_online, status
) VALUES
(
    'TR-5011', '53ft Dry Van Aero', 'Dry Van', 'CargoView AI', 'PHEV-9402', 'Alex R.',
    41.8819, -87.6278,
    64.0, 18.5, 96.2, 'Warning', 'ABS-VALVE-ERR-04',
    'Loaded', 92, 0.98,
    'Sibley Central Yard (St. Louis)', 8.5, 34210.0, FALSE,
    8, 'Warning'
),
(
    'TR-3088', '53ft Reefer Thermal', 'Reefer', 'Pro', 'PHEV-1088', 'Jordan M.',
    41.5250, -88.0817,
    92.0, 42.0, 103.5, 'Optimal', 'NONE',
    'Empty', 0, 0.99,
    'Chicago Distribution Hub', 46.2, 58490.0, TRUE,
    8, 'Optimal'
),
(
    'TR-2204', '48ft Solar Flatbed', 'Flatbed', 'Solar', 'PHEV-3310', 'Sam K.',
    39.7684, -86.1581,
    98.5, 84.0, 101.8, 'Optimal', 'NONE',
    'Partial', 45, 0.91,
    'Indianapolis Intermodal Gate', 79.4, 19820.0, FALSE,
    4, 'Warning'
),
(
    'TR-1049', '53ft Dry Van Logistics', 'Dry Van', 'Track', 'PHEV-7721', 'Taylor B.',
    38.6270, -90.1994,
    88.0, 0.0, 102.1, 'Optimal', 'NONE',
    'Loaded', 100, 0.89,
    'In Transit - I-80 Westbound', 1.2, 12850.0, FALSE,
    4, 'Optimal'
) ON CONFLICT (id) DO NOTHING;
