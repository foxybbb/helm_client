#!/usr/bin/env python3
"""
Diagnostic script for GPIO 16 photo capture issues
Helps troubleshoot why Master system might not be taking photos
"""

import json
import logging
import RPi.GPIO as GPIO
import time
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_configuration():
    """Check Master configuration file"""
    print("🔍 Checking Master Configuration...")
    print("=" * 50)
    
    try:
        with open('master_config.json', 'r') as f:
            config = json.load(f)
        
        triggers = config.get("capture_triggers", {})
        
        print(f"✅ Configuration file loaded successfully")
        print(f"📌 GPIO Trigger Settings:")
        print(f"   - Enabled: {triggers.get('gpio_pin20_enabled', 'NOT SET')}")
        print(f"   - Pin: {triggers.get('gpio_pin20_pin', 'NOT SET')}")
        print(f"   - Buzzer Pin: {config.get('buzzer_pin', 'NOT SET')}")
        print()
        
        # Check if GPIO trigger is enabled
        if not triggers.get('gpio_pin20_enabled', False):
            print("❌ GPIO trigger is DISABLED in config!")
            print("   Fix: Set 'gpio_pin20_enabled': true")
            return False
        
        gpio_pin = triggers.get('gpio_pin20_pin')
        if gpio_pin is None:
            print("❌ GPIO pin is NOT SET in config!")
            return False
        
        print(f"✅ GPIO trigger is properly configured for pin {gpio_pin}")
        return True, gpio_pin
        
    except FileNotFoundError:
        print("❌ master_config.json not found!")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False

def check_gpio_hardware(gpio_pin):
    """Check GPIO hardware functionality"""
    print(f"🔌 Testing GPIO {gpio_pin} Hardware...")
    print("=" * 50)
    
    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        print(f"✅ GPIO {gpio_pin} initialized successfully")
        
        # Test pin states
        print(f"📊 Testing pin states for 10 seconds...")
        print(f"🔧 Connect GPIO {gpio_pin} to GND to test LOW state")
        print()
        
        for i in range(50):  # 10 seconds at 0.2s intervals
            state = GPIO.input(gpio_pin)
            state_text = "LOW (triggered)" if state == GPIO.LOW else "HIGH (idle)"
            timestamp = time.strftime('%H:%M:%S.%f')[:-3]
            print(f"\r{timestamp} - GPIO {gpio_pin}: {state_text}    ", end="", flush=True)
            time.sleep(0.2)
        
        print("\n✅ GPIO hardware test completed")
        return True
        
    except Exception as e:
        print(f"❌ GPIO hardware error: {e}")
        return False
    finally:
        GPIO.cleanup()

def check_master_system_files():
    """Check if Master system files exist and are accessible"""
    print("📁 Checking Master System Files...")
    print("=" * 50)
    
    required_files = [
        'master_helmet_system.py',
        'run_master.py',
        'master_config.json',
        'camera/__init__.py',
        'camera/services.py'
    ]
    
    all_good = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING!")
            all_good = False
    
    return all_good

def check_import_dependencies():
    """Check if all required Python modules can be imported"""
    print("📦 Checking Python Dependencies...")
    print("=" * 50)
    
    modules = [
        ('RPi.GPIO', 'Raspberry Pi GPIO control'),
        ('paho.mqtt.client', 'MQTT communication'),
        ('picamera2', 'Camera control'),
        ('threading', 'Multi-threading support'),
        ('json', 'JSON configuration'),
        ('logging', 'Logging system')
    ]
    
    all_good = True
    for module, description in modules:
        try:
            __import__(module)
            print(f"✅ {module:<20} - {description}")
        except ImportError as e:
            print(f"❌ {module:<20} - MISSING! ({e})")
            all_good = False
    
    return all_good

def simulate_master_trigger():
    """Simulate how the Master system would handle GPIO trigger"""
    print("🎯 Simulating Master System GPIO Trigger Logic...")
    print("=" * 50)
    
    try:
        # Load config like Master system does
        with open('master_config.json', 'r') as f:
            config = json.load(f)
        
        triggers_config = config.get("capture_triggers", {})
        gpio_pin = triggers_config.get("gpio_pin20_pin", 16)
        
        # Setup GPIO like AutoCaptureManager does
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        print(f"📌 Monitoring GPIO {gpio_pin} like Master system...")
        print(f"🔧 Connect pin to GND to trigger simulation")
        print(f"⏱️  Will simulate photo capture every 5 seconds when LOW")
        print("⏹️  Press Ctrl+C to stop")
        print()
        
        last_capture_time = 0
        capture_interval = 5.0
        capture_count = 0
        
        while True:
            current_state = GPIO.input(gpio_pin)
            current_time = time.time()
            
            if current_state == GPIO.LOW:
                if current_time - last_capture_time >= capture_interval:
                    capture_count += 1
                    timestamp = time.strftime('%H:%M:%S')
                    print(f"📸 SIMULATED CAPTURE #{capture_count} at {timestamp}")
                    print(f"   - Would call: master_system.capture_single_photo('gpio{gpio_pin}_continuous')")
                    print(f"   - Would generate GPIO pulse for slaves")
                    print(f"   - Would send MQTT command")
                    print(f"   - Would capture master photo")
                    print(f"   - Would play buzzer beep")
                    last_capture_time = current_time
                    
                status = f"🔴 TRIGGERED - Captures: {capture_count}"
            else:
                status = f"🟢 IDLE - Captures: {capture_count}"
            
            print(f"\rGPIO {gpio_pin}: {status}    ", end="", flush=True)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print(f"\n\n✅ Simulation completed!")
        print(f"📊 Total simulated captures: {capture_count}")
    except Exception as e:
        print(f"\n❌ Simulation error: {e}")
    finally:
        GPIO.cleanup()

def main():
    """Main diagnostic function"""
    print("🔧 Master Board GPIO 16 Diagnostic Tool")
    print("=" * 60)
    print()
    
    # Step 1: Check configuration
    config_result = check_configuration()
    if not config_result:
        return
    
    _, gpio_pin = config_result
    print()
    
    # Step 2: Check required files
    if not check_master_system_files():
        print("❌ Missing required files - check Master system installation")
        return
    print()
    
    # Step 3: Check Python dependencies
    if not check_import_dependencies():
        print("❌ Missing Python dependencies - install required packages")
        return
    print()
    
    # Step 4: Test GPIO hardware
    if not check_gpio_hardware(gpio_pin):
        print("❌ GPIO hardware issues - check wiring and permissions")
        return
    print()
    
    # Step 5: Simulate Master system behavior
    print("🎯 All checks passed! Running Master system simulation...")
    input("Press Enter to start GPIO trigger simulation...")
    simulate_master_trigger()

if __name__ == "__main__":
    main() 