#!/usr/bin/env python3
"""
IMU Trigger Debug Tool
Comprehensive debugging for BNO055 IMU sensor and movement trigger functionality
"""

import time
import json
import logging
import math
import threading
from datetime import datetime
from pathlib import Path

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IMUTriggerDebugger:
    """Debug tool for IMU trigger system"""
    
    def __init__(self):
        self.config = None
        self.imu_sensor = None
        self.monitoring = False
        self.debug_data = []
        self.last_trigger_time = 0
        
        self._load_config()
        self._setup_imu()
    
    def _load_config(self):
        """Load configuration"""
        try:
            with open('master_config.json', 'r') as f:
                self.config = json.load(f)
            
            triggers = self.config.get("capture_triggers", {})
            
            print("📋 IMU Trigger Configuration:")
            print(f"   - Enabled: {triggers.get('imu_movement_enabled', False)}")
            print(f"   - Threshold: {triggers.get('imu_movement_threshold', 2.0)} m/s²")
            print(f"   - Cooldown: {triggers.get('imu_movement_cooldown_seconds', 1800.0)} seconds")
            print(f"   - Cooldown (minutes): {triggers.get('imu_movement_cooldown_seconds', 1800.0) / 60:.1f} min")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return False
    
    def _setup_imu(self):
        """Initialize IMU sensor"""
        print("\n🔍 IMU Sensor Initialization:")
        
        try:
            # Check if IMU libraries are available
            try:
                import board
                import busio
                import adafruit_bno055
                print("✓ IMU libraries available")
            except ImportError as e:
                print(f"❌ IMU libraries missing: {e}")
                print("   Install with: pip3 install adafruit-circuitpython-bno055")
                return False
            
            # Initialize I2C and sensor
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                self.imu_sensor = adafruit_bno055.BNO055_I2C(i2c)
                print("✓ I2C connection established")
            except Exception as e:
                print(f"❌ I2C connection failed: {e}")
                print("   Check wiring: SDA=GPIO2, SCL=GPIO3")
                return False
            
            # Test sensor communication
            try:
                temp = self.imu_sensor.temperature
                print(f"✓ Sensor communication OK (Temperature: {temp}°C)")
            except Exception as e:
                print(f"❌ Sensor communication failed: {e}")
                return False
            
            # Check calibration status
            try:
                cal_status = self.imu_sensor.calibration_status
                print(f"✓ Calibration status: SYS:{cal_status[0]} GYRO:{cal_status[1]} ACCEL:{cal_status[2]} MAG:{cal_status[3]}")
                
                if cal_status[0] < 3:
                    print("⚠️  System not fully calibrated. Move sensor in figure-8 patterns.")
                
            except Exception as e:
                print(f"⚠️  Could not read calibration: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ IMU setup failed: {e}")
            return False
    
    def test_basic_readings(self, duration=10):
        """Test basic IMU readings"""
        print(f"\n📊 Testing IMU Readings for {duration} seconds:")
        print("   Move the sensor to see acceleration changes")
        print()
        
        if not self.imu_sensor:
            print("❌ IMU sensor not available")
            return False
        
        try:
            start_time = time.time()
            reading_count = 0
            
            while time.time() - start_time < duration:
                try:
                    # Read acceleration data
                    accel = self.imu_sensor.acceleration
                    if accel:
                        x, y, z = accel
                        magnitude = math.sqrt(x*x + y*y + z*z)
                        
                        # Read other sensor data
                        gyro = self.imu_sensor.gyro
                        temp = self.imu_sensor.temperature
                        
                        elapsed = time.time() - start_time
                        reading_count += 1
                        
                        print(f"\r⏱️  {elapsed:.1f}s | Accel: {magnitude:.2f} m/s² (X:{x:.1f} Y:{y:.1f} Z:{z:.1f}) | Temp: {temp}°C | Readings: {reading_count}", end="", flush=True)
                    else:
                        print(f"\r⚠️  No acceleration data available", end="", flush=True)
                
                except Exception as e:
                    print(f"\r❌ Reading error: {e}", end="", flush=True)
                
                time.sleep(0.1)  # 10Hz readings
            
            print(f"\n✓ Test completed: {reading_count} readings in {duration} seconds")
            return True
            
        except Exception as e:
            print(f"❌ Basic readings test failed: {e}")
            return False
    
    def test_movement_detection(self, duration=30):
        """Test movement detection algorithm"""
        print(f"\n🎯 Testing Movement Detection for {duration} seconds:")
        
        if not self.imu_sensor:
            print("❌ IMU sensor not available")
            return False
        
        triggers = self.config.get("capture_triggers", {})
        threshold = triggers.get("imu_movement_threshold", 2.0)
        cooldown = triggers.get("imu_movement_cooldown_seconds", 1800.0)
        
        print(f"   - Threshold: {threshold} m/s²")
        print(f"   - Cooldown: {cooldown} seconds ({cooldown/60:.1f} minutes)")
        print("   - Move sensor sharply to trigger")
        print()
        
        last_acceleration = None
        trigger_count = 0
        max_change = 0
        
        try:
            start_time = time.time()
            
            while time.time() - start_time < duration:
                try:
                    current_time = time.time()
                    elapsed = current_time - start_time
                    
                    # Read acceleration
                    accel = self.imu_sensor.acceleration
                    if accel:
                        x, y, z = accel
                        current_acceleration = math.sqrt(x*x + y*y + z*z)
                        
                        if last_acceleration is not None:
                            acceleration_change = abs(current_acceleration - last_acceleration)
                            max_change = max(max_change, acceleration_change)
                            
                            # Check for trigger condition
                            trigger_ready = (current_time - self.last_trigger_time) >= cooldown
                            would_trigger = acceleration_change > threshold
                            
                            if would_trigger and trigger_ready:
                                trigger_count += 1
                                self.last_trigger_time = current_time
                                trigger_status = f"🔥 TRIGGER #{trigger_count}!"
                                
                                # Log trigger event
                                self.debug_data.append({
                                    'time': elapsed,
                                    'acceleration': current_acceleration,
                                    'change': acceleration_change,
                                    'triggered': True
                                })
                                
                            elif would_trigger and not trigger_ready:
                                cooldown_remaining = cooldown - (current_time - self.last_trigger_time)
                                trigger_status = f"⏳ WOULD TRIGGER (cooldown: {cooldown_remaining:.1f}s)"
                            else:
                                trigger_status = f"📊 Monitoring"
                            
                            print(f"\r⏱️  {elapsed:.1f}s | Accel: {current_acceleration:.2f} | Change: {acceleration_change:.2f} | Max: {max_change:.2f} | {trigger_status}        ", end="", flush=True)
                        
                        last_acceleration = current_acceleration
                
                except Exception as e:
                    print(f"\r❌ Movement detection error: {e}", end="", flush=True)
                
                time.sleep(0.1)  # 10Hz monitoring
            
            print(f"\n")
            print(f"✓ Movement detection test completed:")
            print(f"   - Triggers detected: {trigger_count}")
            print(f"   - Maximum change: {max_change:.2f} m/s²")
            print(f"   - Threshold: {threshold} m/s²")
            print(f"   - Status: {'SENSITIVE' if max_change > threshold else 'NEEDS MORE MOVEMENT'}")
            
            return True
            
        except Exception as e:
            print(f"❌ Movement detection test failed: {e}")
            return False
    
    def test_continuous_monitoring(self, duration=60):
        """Test continuous monitoring like the real system"""
        print(f"\n🔄 Testing Continuous Monitoring for {duration} seconds:")
        print("   This simulates the real AutoCaptureManager IMU monitoring")
        print()
        
        if not self.imu_sensor:
            print("❌ IMU sensor not available")
            return False
        
        # Use real system configuration
        triggers = self.config.get("capture_triggers", {})
        threshold = triggers.get("imu_movement_threshold", 2.0)
        cooldown = triggers.get("imu_movement_cooldown_seconds", 1800.0)
        
        self.monitoring = True
        trigger_count = 0
        last_acceleration = None
        
        def monitor_loop():
            nonlocal trigger_count, last_acceleration
            
            print(f"🔍 IMU monitoring started - threshold: {threshold} m/s², cooldown: {cooldown/60:.1f}min")
            
            while self.monitoring:
                try:
                    current_time = time.time()
                    
                    # Simulate the real system's IMU data reading
                    accel = self.imu_sensor.acceleration
                    if accel:
                        x, y, z = accel
                        current_acceleration = math.sqrt(x*x + y*y + z*z)
                        
                        if last_acceleration is not None:
                            acceleration_change = abs(current_acceleration - last_acceleration)
                            
                            # Check cooldown
                            if current_time - self.last_trigger_time < cooldown:
                                time.sleep(0.1)
                                continue
                            
                            # Check trigger condition (same as real system)
                            if acceleration_change > threshold:
                                trigger_count += 1
                                timestamp = datetime.now().strftime('%H:%M:%S')
                                print(f"🎯 [{timestamp}] MOVEMENT TRIGGER #{trigger_count}!")
                                print(f"     - Acceleration change: {acceleration_change:.2f} m/s²")
                                print(f"     - Would capture photo now")
                                print(f"     - Next trigger possible in {cooldown/60:.1f} minutes")
                                
                                self.last_trigger_time = current_time
                        
                        last_acceleration = current_acceleration
                    
                    time.sleep(0.1)  # Same as real system
                    
                except Exception as e:
                    print(f"❌ Monitoring error: {e}")
                    time.sleep(1)
        
        # Start monitoring in background
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        
        try:
            # Show live status
            start_time = time.time()
            
            while time.time() - start_time < duration:
                elapsed = time.time() - start_time
                remaining = duration - elapsed
                cooldown_remaining = max(0, cooldown - (time.time() - self.last_trigger_time))
                
                status = "🟢 READY" if cooldown_remaining == 0 else f"⏳ COOLDOWN ({cooldown_remaining/60:.1f}min)"
                
                print(f"\r⏱️  Time: {elapsed:.0f}s | Remaining: {remaining:.0f}s | Triggers: {trigger_count} | Status: {status}        ", end="", flush=True)
                time.sleep(1)
            
            print("\n")
            
        except KeyboardInterrupt:
            print("\n🛑 Monitoring interrupted by user")
        
        finally:
            self.monitoring = False
            monitor_thread.join(timeout=1)
        
        print(f"✓ Continuous monitoring test completed:")
        print(f"   - Total triggers: {trigger_count}")
        print(f"   - Test duration: {duration} seconds")
        print(f"   - Average triggers per minute: {(trigger_count / duration) * 60:.2f}")
        
        return True
    
    def calibration_helper(self):
        """Help user calibrate the IMU sensor"""
        print("\n🎯 IMU Calibration Helper:")
        print("   BNO055 sensor needs calibration for accurate readings")
        print()
        
        if not self.imu_sensor:
            print("❌ IMU sensor not available")
            return False
        
        try:
            print("📋 Calibration Instructions:")
            print("   1. Keep sensor stationary for gyroscope calibration")
            print("   2. Move sensor slowly in figure-8 patterns for magnetometer")
            print("   3. Place sensor in 6 different orientations for accelerometer")
            print("   4. Target: All values should reach 3 (fully calibrated)")
            print()
            
            for i in range(60):  # Monitor for 60 seconds
                try:
                    cal_status = self.imu_sensor.calibration_status
                    sys_cal, gyro_cal, accel_cal, mag_cal = cal_status
                    
                    # Visual calibration status
                    def cal_bar(value):
                        bars = "█" * value + "░" * (3 - value)
                        return f"{bars} ({value}/3)"
                    
                    print(f"\r🎯 Calibration Status:")
                    print(f"   SYS:   {cal_bar(sys_cal)}")
                    print(f"   GYRO:  {cal_bar(gyro_cal)}")
                    print(f"   ACCEL: {cal_bar(accel_cal)}")
                    print(f"   MAG:   {cal_bar(mag_cal)}")
                    
                    if all(cal >= 3 for cal in cal_status):
                        print("\n🎉 Sensor fully calibrated!")
                        break
                    
                    # Move cursor up to overwrite status
                    print("\033[5A", end="")
                    
                except Exception as e:
                    print(f"❌ Calibration read error: {e}")
                
                time.sleep(1)
            
            print("\n" * 5)  # Clear the overwritten lines
            print("✓ Calibration helper completed")
            return True
            
        except Exception as e:
            print(f"❌ Calibration helper failed: {e}")
            return False
    
    def save_debug_report(self):
        """Save debug information to file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"imu_debug_report_{timestamp}.json"
            
            report = {
                'timestamp': timestamp,
                'config': self.config.get('capture_triggers', {}),
                'sensor_available': self.imu_sensor is not None,
                'debug_data': self.debug_data,
                'last_trigger_time': self.last_trigger_time
            }
            
            # Add current sensor status if available
            if self.imu_sensor:
                try:
                    report['current_status'] = {
                        'temperature': self.imu_sensor.temperature,
                        'calibration': self.imu_sensor.calibration_status,
                        'acceleration': list(self.imu_sensor.acceleration) if self.imu_sensor.acceleration else None
                    }
                except:
                    report['current_status'] = 'error_reading_sensor'
            
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"✅ Debug report saved: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Failed to save debug report: {e}")
            return None

def main():
    """Main debug function"""
    print("🔍 IMU Trigger Debug Tool")
    print("=" * 50)
    
    debugger = IMUTriggerDebugger()
    
    if not debugger.config:
        print("❌ Cannot continue without configuration")
        return
    
    while True:
        print("\n📋 Debug Menu:")
        print("1. Test basic IMU readings (10s)")
        print("2. Test movement detection (30s)")
        print("3. Test continuous monitoring (60s)")
        print("4. Calibration helper")
        print("5. Save debug report")
        print("6. Exit")
        print()
        
        try:
            choice = input("Select option (1-6): ").strip()
            
            if choice == "1":
                debugger.test_basic_readings(10)
                
            elif choice == "2":
                debugger.test_movement_detection(30)
                
            elif choice == "3":
                debugger.test_continuous_monitoring(60)
                
            elif choice == "4":
                debugger.calibration_helper()
                
            elif choice == "5":
                debugger.save_debug_report()
                
            elif choice == "6":
                print("👋 Exiting IMU debug tool")
                break
                
            else:
                print("❌ Invalid choice, please select 1-6")
        
        except KeyboardInterrupt:
            print("\n🛑 Debug interrupted by user")
            break
        except Exception as e:
            print(f"❌ Debug error: {e}")

if __name__ == "__main__":
    main() 