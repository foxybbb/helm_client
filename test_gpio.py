#!/usr/bin/env python3
"""
GPIO Interrupt Test Script

Simple test to verify that GPIO hardware interrupts are working correctly.
This script can be used for testing without the full camera application.
"""

import time
import logging
import signal
import sys
from camera.utils import setup_logging
from camera.factories import ConfigLoader, GPIOWatcherFactory

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.info(f"Received signal {signum}, shutting down test...")
    sys.exit(0)

def test_gpio_interrupts():
    """Test GPIO interrupt functionality"""
    
    # Setup basic logging
    setup_logging(log_level=logging.DEBUG)
    logging.info("GPIO Interrupt Test Starting...")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    gpio = None
    
    try:
        # Load configuration
        config = ConfigLoader.load_config()
        logging.info(f"Testing GPIO pin {config['gpio_pin']}")
        
        # Create GPIO watcher
        gpio = GPIOWatcherFactory.create(config)
        
        # Define test callbacks
        def test_capture_callback():
            """Test callback for photo capture"""
            logging.info("🔥 CAPTURE TRIGGERED! Photo would be taken now.")
        
        # Register callback
        gpio.set_capture_callback(test_capture_callback)
        
        logging.info("GPIO interrupts active. Test ready!")
        logging.info("Instructions:")
        logging.info("- Connect GPIO pin to HIGH to trigger photo capture")
        logging.info("- Keep HIGH for 60+ seconds to trigger WiFi scan")
        logging.info("- Connect to LOW to reset")
        logging.info("- Press Ctrl+C to exit")
        
        # Keep alive and monitor
        test_count = 0
        while True:
            time.sleep(30)  # 30 second intervals
            test_count += 1
            current_state = "HIGH" if gpio.get_current_state() else "LOW"
            logging.info(f"Test heartbeat #{test_count} - GPIO state: {current_state}")
            
    except KeyboardInterrupt:
        logging.info("Test interrupted by user")
    except Exception as e:
        logging.error(f"Test error: {e}")
    finally:
        if gpio:
            gpio.cleanup()
        logging.info("GPIO test completed")

if __name__ == "__main__":
    test_gpio_interrupts() 