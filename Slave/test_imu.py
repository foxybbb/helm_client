#!/usr/bin/env python3
"""
IMU Sensor Test Script

Test script to verify that BNO055 IMU sensor is working correctly.
This script can be used for testing IMU functionality.
"""

import time
import logging
import signal
import sys
from camera.services import IMUSensor

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.info(f"Received signal {signum}, shutting down IMU test...")
    sys.exit(0)

def test_imu():
    """Test IMU sensor functionality"""
    
    # Setup basic logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("IMU Sensor Test Starting...")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    imu = None
    
    try:
        # Create IMU sensor
        imu = IMUSensor()
        
        if not imu.available:
            logging.error("IMU sensor not available")
            logging.error("Please check:")
            logging.error("1. BNO055 sensor is connected properly")
            logging.error("2. I2C is enabled: sudo raspi-config -> Interface Options -> I2C -> Enable")
            logging.error("3. Required libraries installed: pip install adafruit-circuitpython-bno055")
            return
        
        logging.info("IMU sensor initialized successfully")
        logging.info("Starting continuous reading test...")
        logging.info("Press Ctrl+C to exit")
        print()
        
        # Continuous reading test
        test_count = 0
        while True:
            test_count += 1
            
            # Read IMU data
            imu_data = imu.read_data()
            
            if imu_data["available"]:
                # Clear screen and display data
                print("\033[2J\033[H", end="")  # Clear screen and move cursor to top
                
                print(f"IMU Test Reading #{test_count}")
                print("=" * 60)
                print(f"Temperature: {imu_data['temperature']:.1f}°C")
                print()
                
                print("Acceleration (m/s²):")
                acc = imu_data['acceleration']
                print(f"   X: {acc['x']:8.2f}   Y: {acc['y']:8.2f}   Z: {acc['z']:8.2f}")
                print()
                
                print("Magnetometer (µT):")
                mag = imu_data['magnetic']
                print(f"   X: {mag['x']:8.2f}   Y: {mag['y']:8.2f}   Z: {mag['z']:8.2f}")
                print()
                
                print("Gyroscope (rad/s):")
                gyro = imu_data['gyroscope']
                print(f"   X: {gyro['x']:8.2f}   Y: {gyro['y']:8.2f}   Z: {gyro['z']:8.2f}")
                print()
                
                print("Euler Angles (degrees):")
                euler = imu_data['euler']
                print(f"   Heading: {euler['heading']:6.1f}°   Roll: {euler['roll']:6.1f}°   Pitch: {euler['pitch']:6.1f}°")
                print()
                
                print("Quaternion:")
                quat = imu_data['quaternion']
                print(f"   W: {quat['w']:6.3f}   X: {quat['x']:6.3f}   Y: {quat['y']:6.3f}   Z: {quat['z']:6.3f}")
                print()
                
                print("Linear Acceleration (m/s²):")
                lin_acc = imu_data['linear_acceleration']
                print(f"   X: {lin_acc['x']:8.2f}   Y: {lin_acc['y']:8.2f}   Z: {lin_acc['z']:8.2f}")
                print()
                
                print("Gravity (m/s²):")
                grav = imu_data['gravity']
                print(f"   X: {grav['x']:8.2f}   Y: {grav['y']:8.2f}   Z: {grav['z']:8.2f}")
                print()
                
                print("Calibration Status (0-3, 3=fully calibrated):")
                cal = imu_data['calibration_status']
                print(f"   System: {cal['system']}   Gyro: {cal['gyroscope']}   Accel: {cal['accelerometer']}   Mag: {cal['magnetometer']}")
                print()
                
                # Calibration advice
                cal_total = cal['system'] + cal['gyroscope'] + cal['accelerometer'] + cal['magnetometer']
                if cal_total < 10:
                    print("Calibration Tips:")
                    if cal['gyroscope'] < 3:
                        print("   - Place sensor on stable surface for gyro calibration")
                    if cal['accelerometer'] < 3:
                        print("   - Move sensor in figure-8 pattern for accelerometer")
                    if cal['magnetometer'] < 3:
                        print("   - Move sensor in figure-8 pattern away from metal objects")
                    if cal['system'] < 3:
                        print("   - Continue calibration motions until system is calibrated")
                    print()
                else:
                    print("Sensor well calibrated!")
                    print()
                
                print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                print("Press Ctrl+C to exit")
                
            else:
                print(f"Failed to read IMU data: {imu_data.get('error', 'Unknown error')}")
            
            # Wait before next reading
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nIMU test interrupted by user")
    except Exception as e:
        logging.error(f"IMU test error: {e}")
        logging.error("Common solutions:")
        logging.error("1. Check wiring: VIN->3.3V, GND->GND, SDA->GPIO2, SCL->GPIO3")
        logging.error("2. Enable I2C: sudo raspi-config -> Interface Options -> I2C")
        logging.error("3. Check I2C devices: sudo i2cdetect -y 1")
        logging.error("4. Install libraries: pip install adafruit-circuitpython-bno055")
    finally:
        logging.info("IMU test completed")

if __name__ == "__main__":
    test_imu() 