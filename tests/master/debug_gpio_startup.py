#!/usr/bin/env python3
"""
Debug script to check GPIO monitoring startup and configuration
"""

import json
import logging
import time
import sys
from pathlib import Path

# Setup logging to see what's happening
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def check_config():
    """Check the configuration file"""
    print("=" * 50)
    print("CHECKING CONFIGURATION")
    print("=" * 50)
    
    try:
        with open('master_config.json', 'r') as f:
            config = json.load(f)
        
        triggers = config.get("capture_triggers", {})
        
        print(f"✓ Configuration loaded successfully")
        print(f"✓ GPIO pin 20 enabled: {triggers.get('gpio_pin20_enabled', False)}")
        print(f"✓ GPIO pin 20 pin: {triggers.get('gpio_pin20_pin', 'NOT SET')}")
        print(f"✓ Timer enabled: {triggers.get('timer_enabled', False)}")
        print(f"✓ IMU enabled: {triggers.get('imu_movement_enabled', False)}")
        print(f"✓ Buzzer pin: {config.get('buzzer_pin', 'NOT SET')}")
        
        return config
        
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None

def test_gpio_import():
    """Test if GPIO import works"""
    print("\n" + "=" * 50)
    print("TESTING GPIO IMPORT")
    print("=" * 50)
    
    try:
        import RPi.GPIO as GPIO
        print("✓ RPi.GPIO imported successfully")
        
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        print("✓ GPIO mode set to BCM")
        
        return True
        
    except Exception as e:
        print(f"❌ GPIO import failed: {e}")
        return False

def test_classes_import():
    """Test if our custom classes import correctly"""
    print("\n" + "=" * 50)
    print("TESTING CLASS IMPORTS")
    print("=" * 50)
    
    try:
        from master_helmet_system import MasterHelmetSystem, AutoCaptureManager, PassiveBuzzer
        print("✓ MasterHelmetSystem imported")
        print("✓ AutoCaptureManager imported")
        print("✓ PassiveBuzzer imported")
        
        # Test other required imports
        from camera.factories import ConfigLoader
        print("✓ ConfigLoader imported")
        
        from camera.services import MasterIMUSensor, HelmetCamera, JsonLogger, MasterOLEDDisplay
        print("✓ Camera services imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Class import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_auto_capture_creation(config):
    """Test creating AutoCaptureManager"""
    print("\n" + "=" * 50)
    print("TESTING AUTOCAPTURE CREATION")
    print("=" * 50)
    
    try:
        # Create a minimal mock master system
        class MockMasterSystem:
            def __init__(self):
                self.running = True
                
            def capture_single_photo(self, trigger_source):
                print(f"🎯 MOCK PHOTO CAPTURE: {trigger_source}")
                return "mock_command_id", True
        
        mock_master = MockMasterSystem()
        
        from master_helmet_system import AutoCaptureManager
        auto_capture = AutoCaptureManager(config, mock_master)
        
        print(f"✓ AutoCaptureManager created")
        print(f"✓ GPIO trigger pin: {auto_capture.gpio_trigger_pin}")
        print(f"✓ GPIO trigger enabled: {config.get('capture_triggers', {}).get('gpio_pin20_enabled', False)}")
        
        # Try to start GPIO monitoring
        if config.get('capture_triggers', {}).get('gpio_pin20_enabled', False):
            print("\n🚀 Starting GPIO trigger monitoring...")
            auto_capture.start_gpio_trigger_monitoring()
            
            print(f"✓ GPIO trigger monitoring state: {auto_capture.gpio_trigger_monitoring}")
            print(f"✓ GPIO trigger initialized: {auto_capture.gpio_trigger_initialized}")
            
            # Test for 10 seconds
            print("\n⏱️  Testing GPIO monitoring for 10 seconds...")
            print("   Connect GPIO 16 to GND to trigger")
            
            import RPi.GPIO as GPIO
            for i in range(100):  # 10 seconds at 0.1s intervals
                try:
                    state = GPIO.input(auto_capture.gpio_trigger_pin)
                    state_text = "LOW (triggered)" if state == GPIO.LOW else "HIGH (idle)"
                    print(f"\r   GPIO {auto_capture.gpio_trigger_pin}: {state_text} | Time: {i/10:.1f}s", end="", flush=True)
                    time.sleep(0.1)
                except Exception as e:
                    print(f"\n❌ Error reading GPIO: {e}")
                    break
            
            print("\n")
            auto_capture.stop_gpio_trigger_monitoring()
            GPIO.cleanup()
        else:
            print("⚠️  GPIO trigger not enabled in config")
        
        return True
        
    except Exception as e:
        print(f"❌ AutoCapture creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main debug function"""
    print("🔍 GPIO MONITORING DEBUG SCRIPT")
    print("This script will check why GPIO monitoring isn't working")
    
    # Check if running as root (may be needed for GPIO)
    import os
    if os.geteuid() != 0:
        print("\n⚠️  Not running as root - GPIO access might fail")
        print("   Try: sudo python3 debug_gpio_startup.py")
    
    # Step 1: Check configuration
    config = check_config()
    if not config:
        print("\n❌ Cannot continue without valid config")
        return
    
    # Step 2: Test GPIO import
    if not test_gpio_import():
        print("\n❌ Cannot continue without GPIO access")
        return
    
    # Step 3: Test class imports
    if not test_classes_import():
        print("\n❌ Cannot continue without class imports")
        return
    
    # Step 4: Test AutoCapture creation and GPIO monitoring
    if not test_auto_capture_creation(config):
        print("\n❌ AutoCapture testing failed")
        return
    
    print("\n" + "=" * 50)
    print("DEBUG COMPLETE")
    print("=" * 50)
    print("✅ All tests passed!")
    print("\nIf GPIO monitoring still doesn't work in the main system:")
    print("1. Check that master_config.json has 'gpio_pin20_enabled': true")
    print("2. Verify GPIO 16 hardware connections")
    print("3. Run main system with: sudo python3 run_master.py")
    print("4. Check logs for GPIO monitoring messages")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Debug interrupted by user")
    except Exception as e:
        print(f"\n❌ Debug script error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
        except:
            pass
        print("\n🧹 GPIO cleaned up") 