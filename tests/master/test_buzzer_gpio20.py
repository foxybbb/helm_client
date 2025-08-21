#!/usr/bin/env python3
"""
Test script for GPIO 20 continuous monitoring and passive buzzer functionality
"""

import time
import json
import logging
import RPi.GPIO as GPIO
from master_helmet_system import PassiveBuzzer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_buzzer():
    """Test the passive buzzer functionality"""
    print("Testing passive buzzer functionality...")
    
    # Load config
    with open('master_config.json', 'r') as f:
        config = json.load(f)
    
    buzzer = PassiveBuzzer(config)
    
    try:
        print("Testing startup sequence...")
        buzzer.startup_sequence()
        time.sleep(1)
        
        print("Testing photo finished beep...")
        buzzer.photo_finished_beep()
        time.sleep(1)
        
        print("Testing all photos finished sequence...")
        buzzer.all_photos_finished_beep()
        time.sleep(1)
        
        print("Testing custom beep...")
        buzzer.beep(500, 0.2)  # Low frequency, longer duration
        
    finally:
        buzzer.cleanup()
    
    print("Buzzer test completed!")

def test_gpio20_continuous():
    """Test GPIO 20 continuous monitoring (simulation)"""
    print("Testing GPIO 20 continuous monitoring...")
    
    # Load config
    with open('master_config.json', 'r') as f:
        config = json.load(f)
    
    gpio_pin = config["capture_triggers"]["gpio_pin20_pin"]
    
    try:
        # Setup GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        print(f"Monitoring GPIO pin {gpio_pin} for 30 seconds...")
        print("Connect pin to GND to simulate trigger")
        print("Will show capture triggers every 5 seconds when LOW")
        
        last_capture_time = 0
        capture_interval = 5.0
        
        start_time = time.time()
        while time.time() - start_time < 30:  # Run for 30 seconds
            current_state = GPIO.input(gpio_pin)
            current_time = time.time()
            
            if current_state == GPIO.LOW:
                if current_time - last_capture_time >= capture_interval:
                    print(f"GPIO {gpio_pin} is LOW - would trigger photo capture now!")
                    last_capture_time = current_time
                    
            time.sleep(0.1)
            
    finally:
        GPIO.cleanup(gpio_pin)
    
    print("GPIO 20 test completed!")

def main():
    """Main test function"""
    print("=== Master Board GPIO 20 and Buzzer Test ===\n")
    
    try:
        # Test buzzer first
        test_buzzer()
        print()
        
        # Test GPIO 20 monitoring
        test_gpio20_continuous()
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        GPIO.cleanup()
        print("\nTest completed - GPIO cleaned up")

if __name__ == "__main__":
    main() 