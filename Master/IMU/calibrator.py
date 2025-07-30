# SPDX-FileCopyrightText: 2023 JG for Cedar Grove Maker Studios
# SPDX-License-Identifier: MIT

import time
import json
import board
import adafruit_bno055

CALIBRATION_FILE = "bno055_calibration.json"

class Mode:
    CONFIG_MODE = 0x00
    NDOF_MODE = 0x0C

# I2C подключение (используй board.I2C(), если не STEMMA)
i2c = board.I2C()
sensor = adafruit_bno055.BNO055_I2C(i2c)
sensor.mode = Mode.NDOF_MODE  # Полный режим со всеми сенсорами

def print_status(name, index):
    status = sensor.calibration_status[index]
    print(f"{name} Calib Status: {int(100 / 3 * status)}%")

print("🧭 Магнитометр: танец восьмёркой")
while sensor.calibration_status[3] < 3:
    print_status("Mag", 3)
    time.sleep(1)
print("✅ Магнитометр откалиброван\n")
time.sleep(1)

print("🪂 Акселерометр: шесть устойчивых положений")
while sensor.calibration_status[2] < 3:
    print_status("Accel", 2)
    time.sleep(1)
print("✅ Акселерометр откалиброван\n")
time.sleep(1)

print("🧍 Гироскоп: держать неподвижно")
while sensor.calibration_status[1] < 3:
    print_status("Gyro", 1)
    time.sleep(1)
print("✅ Гироскоп откалиброван\n")
time.sleep(1)

print("🎉 ВСЁ КАЛИБРОВАНО!")

# Сохраняем калибровочные значения
calib = {
    "offsets_accelerometer": sensor.offsets_accelerometer,
    "offsets_magnetometer": sensor.offsets_magnetometer,
    "offsets_gyroscope": sensor.offsets_gyroscope,
    "radius_accelerometer": sensor.radius_accelerometer,
    "radius_magnetometer": sensor.radius_magnetometer,
}

with open(CALIBRATION_FILE, "w") as f:
    json.dump(calib, f, indent=4)

print(f"💾 Калибровочные данные сохранены в: {CALIBRATION_FILE}")
print("\n🧩 Эти значения можно использовать в других скриптах для загрузки оффсетов.")
