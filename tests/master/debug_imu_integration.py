#!/usr/bin/env python3
"""
IMU Integration Debug - Test IMU trigger with Master system components
"""

import time
import logging
import json
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_imu_integration():
    """Test IMU integration with Master system"""
    print("🔗 IMU Integration Debug")
    print("=" * 40)
    
    try:
        # Import Master system components
        from camera.factories import ConfigLoader
        from master_helmet_system import MasterHelmetSystem, AutoCaptureManager
        
        # Load configuration
        config = ConfigLoader.load_config("master_config.json")
        print("✓ Configuration loaded")
        
        # Check IMU configuration
        triggers = config.get("capture_triggers", {})
        print(f"\n📋 IMU Configuration:")
        print(f"   - Enabled: {triggers.get('imu_movement_enabled', False)}")
        print(f"   - Threshold: {triggers.get('imu_movement_threshold', 2.0)} m/s²")
        print(f"   - Cooldown: {triggers.get('imu_movement_cooldown_seconds', 1800.0)} seconds")
        
        # Create minimal master system for IMU testing
        print(f"\n🚀 Creating Master system components...")
        
        # Test IMU sensor creation
        try:
            from camera.services import MasterIMUSensor
            imu_sensor = MasterIMUSensor()
            print(f"✓ IMU sensor created, available: {imu_sensor.available}")
            
            if imu_sensor.available:
                # Test IMU data reading
                imu_data = imu_sensor.read_data()
                print(f"✓ IMU data read: {imu_data.get('available', False)}")
                
                if imu_data.get('available'):
                    accel = imu_data.get('acceleration', {})
                    print(f"   - Acceleration: X:{accel.get('x', 0):.2f} Y:{accel.get('y', 0):.2f} Z:{accel.get('z', 0):.2f}")
                    print(f"   - Temperature: {imu_data.get('temperature', 'N/A')}°C")
                    print(f"   - Calibration: {imu_data.get('calibration_status', 'N/A')}")
            
        except Exception as e:
            print(f"❌ IMU sensor creation failed: {e}")
            return False
        
        # Test AutoCaptureManager with IMU
        print(f"\n🎯 Testing AutoCaptureManager with IMU...")
        
        # Create mock master system
        class MockMasterSystem:
            def __init__(self):
                self.running = True
                self.imu_sensor = imu_sensor
                
            def capture_single_photo(self, trigger_source):
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"\n🎯 [{timestamp}] MOCK PHOTO CAPTURE!")
                print(f"     - Trigger: {trigger_source}")
                print(f"     - Would capture photo now")
                return "mock_command_id", True
        
        mock_master = MockMasterSystem()
        
        # Create AutoCaptureManager
        auto_capture = AutoCaptureManager(config, mock_master)
        print(f"✓ AutoCaptureManager created")
        print(f"   - IMU monitoring available: {hasattr(auto_capture, 'imu_monitoring')}")
        
        # Test IMU monitoring if enabled
        if triggers.get('imu_movement_enabled', False) and imu_sensor.available:
            print(f"\n🔄 Testing IMU monitoring for 30 seconds...")
            print(f"   Move the sensor sharply to trigger captures")
            print(f"   Threshold: {triggers.get('imu_movement_threshold', 2.0)} m/s²")
            
            # Start IMU monitoring
            auto_capture.start_imu_monitoring()
            
            # Monitor for 30 seconds
            start_time = time.time()
            while time.time() - start_time < 30:
                elapsed = time.time() - start_time
                remaining = 30 - elapsed
                
                # Show current IMU data
                try:
                    imu_data = imu_sensor.read_data()
                    if imu_data.get('available'):
                        accel = imu_data.get('acceleration', {})
                        magnitude = (accel.get('x', 0)**2 + accel.get('y', 0)**2 + accel.get('z', 0)**2)**0.5
                        
                        cooldown_remaining = max(0, triggers.get('imu_movement_cooldown_seconds', 1800.0) - 
                                               (time.time() - auto_capture.last_imu_capture))
                        
                        status = "🟢 READY" if cooldown_remaining == 0 else f"⏳ COOLDOWN ({cooldown_remaining/60:.1f}min)"
                        
                        print(f"\r⏱️  {elapsed:.1f}s | Remaining: {remaining:.1f}s | Accel: {magnitude:.2f} m/s² | {status}        ", end="", flush=True)
                
                except Exception as e:
                    print(f"\r❌ IMU read error: {e}", end="", flush=True)
                
                time.sleep(0.1)
            
            print(f"\n")
            
            # Stop monitoring
            auto_capture.stop_imu_monitoring()
            print(f"✓ IMU monitoring test completed")
            
        else:
            print(f"⚠️  IMU monitoring not enabled or sensor not available")
        
        print(f"\n✅ IMU integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ IMU integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_imu_trigger_simulation():
    """Simulate IMU trigger behavior"""
    print(f"\n🎮 IMU Trigger Simulation")
    print("=" * 30)
    
    try:
        # Load config
        with open('master_config.json', 'r') as f:
            config = json.load(f)
        
        triggers = config.get("capture_triggers", {})
        threshold = triggers.get("imu_movement_threshold", 2.0)
        cooldown = triggers.get("imu_movement_cooldown_seconds", 1800.0)
        
        print(f"📋 Simulating trigger behavior:")
        print(f"   - Threshold: {threshold} m/s²")
        print(f"   - Cooldown: {cooldown} seconds ({cooldown/60:.1f} minutes)")
        
        # Simulate different acceleration changes
        test_values = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 5.0, 10.0]
        last_trigger_time = 0
        
        print(f"\n🧪 Testing different acceleration changes:")
        
        for accel_change in test_values:
            current_time = time.time()
            cooldown_passed = (current_time - last_trigger_time) >= cooldown
            would_trigger = accel_change > threshold
            
            if would_trigger and cooldown_passed:
                result = "🔥 WOULD TRIGGER"
                last_trigger_time = current_time
            elif would_trigger and not cooldown_passed:
                cooldown_remaining = cooldown - (current_time - last_trigger_time)
                result = f"⏳ BLOCKED (cooldown: {cooldown_remaining:.1f}s)"
            else:
                result = "📊 No trigger"
            
            print(f"   - Accel change: {accel_change:4.1f} m/s² → {result}")
            
            # Small delay to show progression
            time.sleep(0.1)
        
        print(f"\n✅ Trigger simulation completed")
        return True
        
    except Exception as e:
        print(f"❌ Trigger simulation failed: {e}")
        return False

def main():
    """Main debug function"""
    print("🔍 IMU Trigger Debug Suite")
    print("=" * 50)
    
    while True:
        print("\n📋 Debug Menu:")
        print("1. Test IMU integration with Master system")
        print("2. Simulate IMU trigger behavior")
        print("3. Run both tests")
        print("4. Exit")
        print()
        
        try:
            choice = input("Select option (1-4): ").strip()
            
            if choice == "1":
                test_imu_integration()
                
            elif choice == "2":
                test_imu_trigger_simulation()
                
            elif choice == "3":
                test_imu_integration()
                test_imu_trigger_simulation()
                
            elif choice == "4":
                print("👋 Exiting IMU debug suite")
                break
                
            else:
                print("❌ Invalid choice, please select 1-4")
        
        except KeyboardInterrupt:
            print("\n🛑 Debug interrupted by user")
            break
        except Exception as e:
            print(f"❌ Debug error: {e}")

if __name__ == "__main__":
    main() 