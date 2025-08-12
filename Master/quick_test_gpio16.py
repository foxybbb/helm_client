#!/usr/bin/env python3
"""
Quick test for GPIO 16 trigger functionality
Simple script to verify GPIO 16 is working as photo capture trigger
"""

import time
import RPi.GPIO as GPIO

def main():
    print("🔌 Quick GPIO 16 Trigger Test")
    print("=" * 35)
    
    gpio_pin = 16
    
    try:
        # Setup GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        print(f"📌 Testing GPIO pin {gpio_pin} with pull-up resistor")
        print(f"🔧 Connect pin {gpio_pin} to GND to trigger")
        print(f"📸 Will show capture trigger every 5 seconds when LOW")
        print("⏹️  Press Ctrl+C to stop")
        print()
        
        last_capture = 0
        capture_count = 0
        
        while True:
            state = GPIO.input(gpio_pin)
            current_time = time.time()
            
            if state == GPIO.LOW:
                # Pin is triggered (connected to GND)
                if current_time - last_capture >= 5.0:
                    capture_count += 1
                    timestamp = time.strftime('%H:%M:%S')
                    print(f"📸 TRIGGER {capture_count} at {timestamp} - GPIO {gpio_pin} is LOW")
                    print(f"    Would capture photo now!")
                    last_capture = current_time
                    
                    # Show countdown to next trigger
                    print(f"    ⏱️  Next capture in 5 seconds if pin stays LOW")
                
                status = f"🔴 LOW (triggered) - Captures: {capture_count}"
            else:
                status = f"🟢 HIGH (idle) - Captures: {capture_count}"
            
            print(f"\rGPIO {gpio_pin}: {status}", end="", flush=True)
            time.sleep(0.2)
            
    except KeyboardInterrupt:
        print(f"\n\n✅ Test completed!")
        print(f"📊 Total simulated captures: {capture_count}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
    finally:
        GPIO.cleanup()
        print("🧹 GPIO cleaned up")

if __name__ == "__main__":
    main() 