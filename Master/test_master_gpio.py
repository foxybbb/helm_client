#!/usr/bin/env python3
"""
Minimal test of Master system GPIO functionality
"""

import time
import logging
import sys
from pathlib import Path

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_master_gpio():
    """Test Master system GPIO functionality"""
    print("🔍 Testing Master System GPIO Functionality")
    print("=" * 60)
    
    try:
        # Import required classes
        from camera.factories import ConfigLoader
        from camera.utils import setup_logging
        from master_helmet_system import MasterHelmetSystem
        
        # Load configuration
        config = ConfigLoader.load_config("master_config.json")
        
        # Setup logging
        log_dir = config.get("log_dir")
        if log_dir and log_dir.startswith("~"):
            log_dir = str(Path(log_dir).expanduser())
        setup_logging(log_dir=log_dir)
        
        print(f"✓ Configuration loaded")
        print(f"✓ GPIO pin 20 enabled: {config.get('capture_triggers', {}).get('gpio_pin20_enabled', False)}")
        print(f"✓ GPIO pin: {config.get('capture_triggers', {}).get('gpio_pin20_pin', 'NOT SET')}")
        
        # Create master system (but don't start everything)
        print("\n🚀 Creating Master system...")
        master_system = MasterHelmetSystem(config)
        
        print("✓ Master system created")
        print(f"✓ Auto capture manager: {hasattr(master_system, 'auto_capture')}")
        
        if hasattr(master_system, 'auto_capture'):
            auto_capture = master_system.auto_capture
            print(f"✓ GPIO trigger pin: {auto_capture.gpio_trigger_pin}")
            print(f"✓ GPIO trigger enabled in config: {config.get('capture_triggers', {}).get('gpio_pin20_enabled', False)}")
            
            # Test starting GPIO monitoring directly
            print("\n📌 Testing GPIO monitoring directly...")
            if config.get('capture_triggers', {}).get('gpio_pin20_enabled', False):
                auto_capture.start_gpio_trigger_monitoring()
                print(f"✓ GPIO monitoring started: {auto_capture.gpio_trigger_monitoring}")
                print(f"✓ GPIO initialized: {auto_capture.gpio_trigger_initialized}")
                
                # Test GPIO state reading for 10 seconds
                print(f"\n⏱️  Monitoring GPIO {auto_capture.gpio_trigger_pin} for 10 seconds...")
                print("   Connect GPIO to GND to trigger")
                
                import RPi.GPIO as GPIO
                start_time = time.time()
                last_state = None
                
                while time.time() - start_time < 10:
                    try:
                        current_state = GPIO.input(auto_capture.gpio_trigger_pin)
                        
                        if current_state != last_state:
                            state_text = "LOW (triggered)" if current_state == GPIO.LOW else "HIGH (idle)"
                            elapsed = time.time() - start_time
                            print(f"   {elapsed:.1f}s: GPIO {auto_capture.gpio_trigger_pin} changed to {state_text}")
                            last_state = current_state
                        
                        time.sleep(0.1)
                        
                    except Exception as e:
                        print(f"   Error reading GPIO: {e}")
                        break
                
                # Stop monitoring
                auto_capture.stop_gpio_trigger_monitoring()
                GPIO.cleanup()
                print(f"✓ GPIO monitoring stopped")
            else:
                print("⚠️  GPIO trigger not enabled in config")
        
        print("\n✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    try:
        success = test_master_gpio()
        
        if success:
            print("\n🎯 RECOMMENDATIONS:")
            print("1. GPIO monitoring appears to work in isolation")
            print("2. Check if the full Master system is calling start_all_triggers()")
            print("3. Run with: sudo python3 run_master.py")
            print("4. Monitor logs for GPIO trigger messages")
            print("5. Verify GPIO 16 physical connections")
        else:
            print("\n❌ GPIO monitoring has issues")
            print("1. Check hardware connections")
            print("2. Verify GPIO permissions")
            print("3. Run with sudo if needed")
    
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
    
    finally:
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
        except:
            pass

if __name__ == "__main__":
    main() 