#!/usr/bin/env python3
"""
Test program for GPIO 16 photo capture trigger
Tests the continuous monitoring functionality where GPIO 16 triggers photos every 5 seconds when LOW
"""

import time
import json
import logging
import threading
import RPi.GPIO as GPIO
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GPIO16TriggerTest:
    """Test class for GPIO 16 continuous photo triggering"""
    
    def __init__(self):
        self.gpio_pin = 16
        self.monitoring = False
        self.monitor_thread = None
        self.capture_count = 0
        self.last_capture_time = 0
        self.capture_interval = 5.0  # 5 seconds between captures when LOW
        
        # Load config to verify pin setting
        try:
            with open('master_config.json', 'r') as f:
                config = json.load(f)
                configured_pin = config["capture_triggers"]["gpio_pin20_pin"]
                if configured_pin != self.gpio_pin:
                    logger.warning(f"Config shows pin {configured_pin}, but testing pin {self.gpio_pin}")
                    self.gpio_pin = configured_pin
        except Exception as e:
            logger.error(f"Could not load config: {e}")
        
        self._setup_gpio()
    
    def _setup_gpio(self):
        """Initialize GPIO pin for monitoring"""
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            logger.info(f"GPIO pin {self.gpio_pin} initialized with pull-up resistor")
            
            # Test initial state
            initial_state = GPIO.input(self.gpio_pin)
            state_text = "HIGH (not triggered)" if initial_state else "LOW (triggered)"
            logger.info(f"Initial GPIO {self.gpio_pin} state: {state_text}")
            
        except Exception as e:
            logger.error(f"Failed to initialize GPIO pin {self.gpio_pin}: {e}")
            raise
    
    def simulate_photo_capture(self, trigger_number):
        """Simulate photo capture process"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        logger.info(f"📸 PHOTO CAPTURE #{trigger_number} at {timestamp}")
        logger.info(f"   - Trigger source: gpio{self.gpio_pin}_continuous")
        logger.info(f"   - Would generate GPIO pulse for slave sync")
        logger.info(f"   - Would send MQTT command to slaves")
        logger.info(f"   - Would capture master photo (cam1)")
        logger.info(f"   - Would play photo finished beep")
        print(f"🔊 *BEEP* Photo {trigger_number} captured!")
        self.capture_count += 1
    
    def start_monitoring(self):
        """Start GPIO 16 continuous monitoring"""
        if self.monitoring:
            logger.warning("Monitoring already started")
            return
        
        self.monitoring = True
        self.capture_count = 0
        self.last_capture_time = 0
        
        def monitor_loop():
            logger.info(f"🔍 Starting GPIO {self.gpio_pin} continuous monitoring...")
            logger.info("📋 Monitoring behavior:")
            logger.info("   - When pin is HIGH: No photo capture")
            logger.info("   - When pin is LOW: Photo every 5 seconds")
            logger.info("   - Connect pin to GND to trigger")
            logger.info("   - Disconnect from GND to stop")
            
            trigger_number = 0
            
            while self.monitoring:
                try:
                    current_state = GPIO.input(self.gpio_pin)
                    current_time = time.time()
                    
                    if current_state == GPIO.LOW:
                        # Pin is triggered (connected to GND)
                        if current_time - self.last_capture_time >= self.capture_interval:
                            trigger_number += 1
                            self.simulate_photo_capture(trigger_number)
                            self.last_capture_time = current_time
                            
                            # Show next capture countdown
                            logger.info(f"⏱️  Next capture in {self.capture_interval} seconds (if pin stays LOW)")
                    else:
                        # Pin is not triggered (disconnected/HIGH)
                        if self.last_capture_time > 0:  # Was previously triggered
                            logger.info(f"🛑 GPIO {self.gpio_pin} is HIGH - photo triggering stopped")
                            self.last_capture_time = 0  # Reset timer
                    
                    time.sleep(0.1)  # Check every 100ms
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(1)
            
            logger.info("🏁 GPIO monitoring stopped")
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"✅ GPIO {self.gpio_pin} monitoring thread started")
    
    def stop_monitoring(self):
        """Stop GPIO monitoring"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        
        logger.info(f"📊 Test Summary:")
        logger.info(f"   - Total simulated captures: {self.capture_count}")
        logger.info(f"   - GPIO pin tested: {self.gpio_pin}")
        logger.info(f"   - Capture interval: {self.capture_interval} seconds")
    
    def run_interactive_test(self, duration=60):
        """Run interactive test for specified duration"""
        logger.info(f"🚀 Starting GPIO {self.gpio_pin} interactive test")
        logger.info(f"⏳ Test duration: {duration} seconds")
        logger.info("")
        logger.info("🔧 Hardware setup:")
        logger.info(f"   - Connect a wire from GPIO {self.gpio_pin} to GND to trigger")
        logger.info(f"   - Disconnect wire to stop triggering")
        logger.info("")
        
        self.start_monitoring()
        
        try:
            start_time = time.time()
            while time.time() - start_time < duration:
                current_state = GPIO.input(self.gpio_pin)
                elapsed = int(time.time() - start_time)
                remaining = duration - elapsed
                
                state_indicator = "🔴 TRIGGERED (LOW)" if current_state == GPIO.LOW else "🟢 IDLE (HIGH)"
                
                print(f"\r⏱️  Time: {elapsed:02d}s | Remaining: {remaining:02d}s | Pin {self.gpio_pin}: {state_indicator} | Captures: {self.capture_count}", end="", flush=True)
                time.sleep(1)
            
            print()  # New line after progress display
            
        except KeyboardInterrupt:
            print("\n🛑 Test interrupted by user")
        
        finally:
            self.stop_monitoring()
    
    def cleanup(self):
        """Cleanup GPIO resources"""
        try:
            self.stop_monitoring()
            GPIO.cleanup(self.gpio_pin)
            logger.info(f"🧹 GPIO {self.gpio_pin} cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def test_gpio_state():
    """Quick test to check current GPIO 16 state"""
    print("🔍 Quick GPIO 16 State Check")
    print("=" * 40)
    
    try:
        # Load config to get correct pin
        with open('master_config.json', 'r') as f:
            config = json.load(f)
            gpio_pin = config["capture_triggers"]["gpio_pin20_pin"]
        
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        for i in range(10):
            state = GPIO.input(gpio_pin)
            state_text = "LOW (triggered)" if state == GPIO.LOW else "HIGH (idle)"
            print(f"GPIO {gpio_pin} state: {state_text}")
            time.sleep(0.5)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        GPIO.cleanup()

def main():
    """Main test function"""
    print("=" * 60)
    print("🎯 GPIO 16 Photo Capture Trigger Test")
    print("=" * 60)
    print()
    
    # Show menu
    print("Test options:")
    print("1. Quick state check (10 readings)")
    print("2. Interactive test (60 seconds)")
    print("3. Extended test (5 minutes)")
    print("4. Custom duration test")
    print()
    
    try:
        choice = input("Select test option (1-4): ").strip()
        
        if choice == "1":
            test_gpio_state()
            
        elif choice in ["2", "3", "4"]:
            if choice == "2":
                duration = 60
            elif choice == "3":
                duration = 300
            else:  # choice == "4"
                duration = int(input("Enter test duration in seconds: "))
            
            tester = GPIO16TriggerTest()
            try:
                tester.run_interactive_test(duration)
            finally:
                tester.cleanup()
        else:
            print("Invalid choice")
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test error: {e}")
    finally:
        GPIO.cleanup()
        print("\n✅ Test completed - GPIO cleaned up")

if __name__ == "__main__":
    main() 