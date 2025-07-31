# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import json
import os
from datetime import datetime
import board
import adafruit_bno055

CALIBRATION_FILE = "bno055_calibration.json"

def all_data_valid(data: dict) -> bool:
    for key, value in data.items():
        if key == "timestamp":
            continue
        if value is None:
            return False
        if isinstance(value, (tuple, list)) and all(v == 0 for v in value):
            return False
    return True

def load_calibration(sensor):
    if not os.path.exists(CALIBRATION_FILE):
        return False
    try:
        with open(CALIBRATION_FILE, "r") as f:
            calib = json.load(f)
        sensor.offsets_accelerometer = tuple(calib["offsets_accelerometer"])
        sensor.offsets_magnetometer = tuple(calib["offsets_magnetometer"])
        sensor.offsets_gyroscope = tuple(calib["offsets_gyroscope"])
        sensor.radius_accelerometer = calib["radius_accelerometer"]
        sensor.radius_magnetometer = calib["radius_magnetometer"]
        print("✅ Calibration loaded.")
        return True
    except Exception as e:
        print(f"⚠️ Error loading calibration: {e}")
        return False

def save_calibration(sensor):
    calib = {
        "offsets_accelerometer": sensor.offsets_accelerometer,
        "offsets_magnetometer": sensor.offsets_magnetometer,
        "offsets_gyroscope": sensor.offsets_gyroscope,
        "radius_accelerometer": sensor.radius_accelerometer,
        "radius_magnetometer": sensor.radius_magnetometer,
    }
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(calib, f, indent=4)
    print(f"💾 Calibration saved to: {CALIBRATION_FILE}")

# --- I2C and sensor initialization ---
i2c = board.I2C()
sensor = adafruit_bno055.BNO055_I2C(i2c)

# --- Calibration ---
if not load_calibration(sensor):
    print("🧭 Calibrating BNO055 sensor...")
    while sensor.calibration_status[3] < 3:
        print(f"Magnetometer calibration: {int(100 / 3 * sensor.calibration_status[3])}%")
        time.sleep(1)
    while sensor.calibration_status[2] < 3:
        print(f"Accelerometer calibration: {int(100 / 3 * sensor.calibration_status[2])}%")
        time.sleep(1)
    while sensor.calibration_status[1] < 3:
        print(f"Gyroscope calibration: {int(100 / 3 * sensor.calibration_status[1])}%")
        time.sleep(1)
    print("✅ All systems calibrated.")
    save_calibration(sensor)

# --- Waiting for valid data ---
print("📡 Waiting for valid data from BNO055...")
while True:
    data = {
        "timestamp": datetime.now().isoformat(),
        "temperature_C": sensor.temperature,
        "acceleration_m_s2": sensor.acceleration,
        "magnetic_uT": sensor.magnetic,
        "gyro_rad_s": sensor.gyro,
        "euler_deg": sensor.euler,
        "quaternion": sensor.quaternion,
        "linear_acceleration_m_s2": sensor.linear_acceleration,
        "gravity_m_s2": sensor.gravity,
    }

    if all_data_valid(data):
        break
    time.sleep(0.1)

# --- Save valid dataset ---
filename = f"bno055_record_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, "w") as f:
    json.dump(data, f, indent=4)

print(f"✅ First valid dataset saved to: {filename}")
