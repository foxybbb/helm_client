#!/usr/bin/env python3
"""
Simple IMU Test - Quick verification of BNO055 sensor
"""

import time
import math

def test_imu_basic():
    """Quick IMU sensor test"""
    print("🔍 Simple IMU Test")
    print("=" * 30)
    
    try:
        # Import IMU libraries
        import board
        import busio
        import adafruit_bno055
        print("✓ IMU libraries available")
        
        # Initialize sensor
        i2c = busio.I2C(board.SCL, board.SDA)
        sensor = adafruit_bno055.BNO055_I2C(i2c)
        print("✓ IMU sensor connected")
        
        # Test readings
        temp = sensor.temperature
        print(f"✓ Temperature: {temp}°C")
        
        # Calibration status
        cal = sensor.calibration_status
        print(f"✓ Calibration: SYS:{cal[0]} GYRO:{cal[1]} ACCEL:{cal[2]} MAG:{cal[3]}")
        
        # Test acceleration readings
        print("\n📊 Testing acceleration for 10 seconds:")
        print("   Move sensor to see changes...")
        
        for i in range(100):  # 10 seconds at 10Hz
            try:
                accel = sensor.acceleration
                if accel:
                    x, y, z = accel
                    magnitude = math.sqrt(x*x + y*y + z*z)
                    print(f"\r   Acceleration: {magnitude:.2f} m/s² (X:{x:.1f} Y:{y:.1f} Z:{z:.1f})", end="", flush=True)
                else:
                    print(f"\r   No acceleration data", end="", flush=True)
            except:
                print(f"\r   Read error", end="", flush=True)
            
            time.sleep(0.1)
        
        print("\n✅ IMU test completed successfully!")
        return True
        
    except ImportError:
        print("❌ IMU libraries not installed")
        print("   Install: pip3 install adafruit-circuitpython-bno055")
        return False
        
    except Exception as e:
        print(f"❌ IMU test failed: {e}")
        return False

if __name__ == "__main__":
    test_imu_basic() 