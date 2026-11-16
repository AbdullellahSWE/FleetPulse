import json
import random
import time
import boto3

kinesis_client = boto3.client('kinesis', region_name='us-east-1')
STREAM_NAME = 'FleetPulse-TelemetryStream'

PHEV_FLEET = [
    {
        "vehicle_id": "PHEV-9402",
        "model": "Freightliner Cascadia Hybrid",
        "trailer_id": "TR-5011",
        "hardware_suite": "CargoView AI",
        "in_lez_zone": True,
        "lez_zone_name": "Chicago Clean Air LEZ Zone 1",
        "default_mode": "EV_MODE",
        "base_odometer_km": 58914.8,
    },
    {
        "vehicle_id": "PHEV-1088",
        "model": "Volvo VNR Dual-Drive PHEV",
        "trailer_id": "TR-3088",
        "hardware_suite": "Pro",
        "in_lez_zone": False,
        "lez_zone_name": "None",
        "default_mode": "HYBRID_MODE",
        "base_odometer_km": 96810.4,
    },
    {
        "vehicle_id": "PHEV-3310",
        "model": "Peterbilt 579 Hybrid",
        "trailer_id": "TR-2204",
        "hardware_suite": "Solar",
        "in_lez_zone": False,
        "lez_zone_name": "None",
        "default_mode": "ICE_MODE",
        "base_odometer_km": 85620.1,
    },
    {
        "vehicle_id": "PHEV-7721",
        "model": "Kenworth T680 PHEV EcoLine",
        "trailer_id": "TR-1049",
        "hardware_suite": "Track",
        "in_lez_zone": True,
        "lez_zone_name": "St. Louis Metro Green Freight Corridor",
        "default_mode": "REGEN_BRAKING",
        "base_odometer_km": 76210.6,
    }
]

def generate_obd_phev_telemetry():
    v = random.choice(PHEV_FLEET)
    mode = v["default_mode"]

    # OBD-II standard parameters depending on operating state
    if mode == "EV_MODE":
        battery = round(random.uniform(15.0, 95.0), 1)
        batt_temp = round(random.uniform(28.0, 48.0), 1)
        rpm = 0
        coolant = round(random.uniform(35.0, 50.0), 1)
        oil_psi = 0.0
        engine_load = 0.0
        map_pressure = 101.3 # atmospheric
        throttle_pos = round(random.uniform(10.0, 35.0), 1) # accelerator pedal position sensor
        fuel_rate_lph = 0.0
        mpg = 95.0
        dtc_codes = "NONE"
        dtc_desc = "Zero-emission pure electric traction mode active."
        dtc_sev = "NONE"
        co2_saved = round(random.uniform(18.0, 26.0), 2)
    elif mode == "ICE_MODE":
        battery = round(random.uniform(20.0, 40.0), 1)
        batt_temp = round(random.uniform(30.0, 39.0), 1)
        rpm = random.randint(1450, 1850)
        coolant = round(random.uniform(88.0, 98.0), 1)
        oil_psi = round(random.uniform(25.0, 44.0), 1)
        engine_load = round(random.uniform(62.0, 88.0), 1)
        map_pressure = round(random.uniform(130.0, 165.0), 1) # turbo boost MAP
        throttle_pos = round(random.uniform(40.0, 75.0), 1)
        fuel_rate_lph = round(random.uniform(8.5, 16.0), 1)
        mpg = round(random.uniform(22.0, 28.0), 1)
        
        # Simulate active OBD-II DTC faults for high load units
        if v["vehicle_id"] == "PHEV-3310" or oil_psi < 28.0:
            dtc_codes = "P0420, P0524"
            dtc_desc = "P0420 Catalyst System Efficiency Below Threshold; P0524 Engine Oil Pressure Too Low."
            dtc_sev = "CRITICAL"
        else:
            dtc_codes = "NONE"
            dtc_desc = "Closed loop stoichiometric fuel control active."
            dtc_sev = "NONE"
        co2_saved = 0.0
    elif mode == "REGEN_BRAKING":
        battery = round(random.uniform(70.0, 98.0), 1)
        batt_temp = round(random.uniform(26.0, 33.0), 1)
        rpm = random.randint(600, 950)
        coolant = round(random.uniform(75.0, 85.0), 1)
        oil_psi = round(random.uniform(40.0, 45.0), 1)
        engine_load = round(random.uniform(5.0, 15.0), 1)
        map_pressure = 98.2
        throttle_pos = 0.0 # foot off accelerator, braking
        fuel_rate_lph = 0.8 # idle fuel cut
        mpg = round(random.uniform(70.0, 88.0), 1)
        dtc_codes = "NONE"
        dtc_desc = "Kinetic energy regenerative braking active."
        dtc_sev = "NONE"
        co2_saved = round(random.uniform(12.0, 18.0), 2)
    else: # HYBRID_MODE
        battery = round(random.uniform(45.0, 85.0), 1)
        batt_temp = round(random.uniform(31.0, 40.0), 1)
        rpm = random.randint(1100, 1550)
        coolant = round(random.uniform(85.0, 92.0), 1)
        oil_psi = round(random.uniform(42.0, 47.0), 1)
        engine_load = round(random.uniform(38.0, 58.0), 1)
        map_pressure = round(random.uniform(108.0, 128.0), 1)
        throttle_pos = round(random.uniform(22.0, 45.0), 1)
        fuel_rate_lph = round(random.uniform(3.5, 6.2), 1)
        mpg = round(random.uniform(52.0, 64.0), 1)
        dtc_codes = "NONE"
        dtc_desc = "Parallel hybrid torque split optimized."
        dtc_sev = "NONE"
        co2_saved = round(random.uniform(8.0, 15.0), 2)

    status = 'Optimal'
    if battery < 18 or batt_temp > 46 or dtc_sev == 'CRITICAL' or (rpm > 0 and (oil_psi < 30 or coolant > 102)):
        status = 'Critical'
    elif battery < 35 or batt_temp > 39 or (rpm > 0 and coolant > 94):
        status = 'Warning'

    return {
        "vehicle_id": v["vehicle_id"],
        "model_name": v["model"],
        "powertrain_mode": mode,
        "battery_level": battery,
        "battery_temp_celsius": batt_temp,
        "fuel_level_percent": round(random.uniform(35.0, 95.0), 1),
        # OBD-II PIDs
        "engine_rpm": rpm,
        "engine_coolant_temp": coolant,
        "oil_pressure_psi": oil_psi,
        "engine_load_percent": engine_load,
        "map_pressure_kpa": map_pressure,
        "throttle_position_percent": throttle_pos,
        "fuel_rate_lph": fuel_rate_lph,
        "high_res_odometer_km": round(v["base_odometer_km"] + random.uniform(0.1, 5.0), 2),
        "active_dtc_codes": dtc_codes,
        "dtc_description": dtc_desc,
        "dtc_severity": dtc_sev,
        # Performance & ESG
        "current_mpg": mpg,
        "in_lez_zone": v["in_lez_zone"],
        "lez_zone_name": v["lez_zone_name"],
        "co2_saved_kg": co2_saved,
        "trailer_id": v["trailer_id"],
        "hardware_suite": v["hardware_suite"],
        "status": status,
        "timestamp": time.time(),
        "diagnostics": f"OBD-II Telemetry live: Mode {mode}, RPM {rpm}, Load {engine_load}%, DTC: {dtc_codes}."
    }

def stream_telemetry():
    print(f"Starting FleetPulse OBD-II & PHEV Kinesis Streamer -> Stream: {STREAM_NAME}")
    while True:
        payload = generate_obd_phev_telemetry()
        try:
            response = kinesis_client.put_record(
                StreamName=STREAM_NAME,
                Data=json.dumps(payload),
                PartitionKey=payload['vehicle_id']
            )
            print(f"[OBD-II SENT] {payload['vehicle_id']} [{payload['powertrain_mode']}] | RPM: {payload['engine_rpm']} | Load: {payload['engine_load_percent']}% | DTC: {payload['active_dtc_codes']} | Shard: {response['ShardId']}")
        except Exception as e:
            print(f"[ERROR pushing OBD-II telemetry]: {e}")
        time.sleep(2)

if __name__ == '__main__':
    stream_telemetry()
