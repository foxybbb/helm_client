#!/usr/bin/env python3
"""
Master Helmet Camera System - Development Version

This version mocks GPIO functionality for testing on non-Raspberry Pi systems.
"""

import time
import logging
import signal
import sys
import json
import threading
import datetime
from pathlib import Path
from typing import Dict, List
import paho.mqtt.client as mqtt
from camera.factories import ConfigLoader
from camera.utils import setup_logging
from camera.services import MasterIMUSensor

# Mock GPIO for development
class MockGPIO:
    BCM = "BCM"
    OUT = "OUT"
    HIGH = True
    LOW = False
    
    @staticmethod
    def setmode(mode):
        print(f"Mock GPIO: setmode({mode})")
    
    @staticmethod
    def setup(pin, mode):
        print(f"Mock GPIO: setup(pin={pin}, mode={mode})")
    
    @staticmethod
    def output(pin, state):
        print(f"Mock GPIO: output(pin={pin}, state={state})")
    
    @staticmethod
    def cleanup():
        print("Mock GPIO: cleanup()")

# Mock IMU libraries for development
class MockBoard:
    @staticmethod
    def I2C():
        return "Mock I2C"
    
    @staticmethod
    def SCL():
        return "Mock SCL"
    
    @staticmethod
    def SDA():
        return "Mock SDA"

class MockBusio:
    @staticmethod
    def I2C(scl, sda):
        return "Mock I2C Bus"

class MockBNO055:
    def __init__(self, i2c):
        self.temperature = 24.5
        self.acceleration = (0.1, 0.2, 9.8)
        self.magnetic = (25.3, -15.7, 48.1)
        self.gyro = (0.01, -0.02, 0.0)
        self.euler = (45.2, 1.3, -2.1)
        self.quaternion = (0.999, 0.001, -0.002, 0.045)
        self.linear_acceleration = (0.05, 0.15, 0.1)
        self.gravity = (0.05, 0.05, 9.7)
        self.calibration_status = (3, 3, 3, 3)  # fully calibrated
        print("Mock BNO055 IMU sensor initialized")

class MockAdafruitBNO055:
    @staticmethod
    def BNO055_I2C(i2c):
        return MockBNO055(i2c)

# Use mock modules
sys.modules['RPi.GPIO'] = MockGPIO()
sys.modules['board'] = MockBoard()
sys.modules['busio'] = MockBusio()
sys.modules['adafruit_bno055'] = MockAdafruitBNO055()

# Now import the actual master system
from master_helmet_system import MasterHelmetSystem

logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    sys.exit(0)

def main():
    """Main application entry point for master - development version"""
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    master_system = None
    
    try:
        # Load master configuration
        config = ConfigLoader.load_config("master_config.json")
        
        # Initialize logging
        log_dir = config.get("log_dir")
        if log_dir and log_dir.startswith("~"):
            log_dir = str(Path(log_dir).expanduser())
        setup_logging(log_dir=log_dir)
        logger.info(f"Master Helmet System Starting (DEV MODE) - Master ID: {config['master_id']}")
        
        # Startup delay
        startup_delay = config["startup_delay"]
        logger.info(f"Waiting {startup_delay} seconds before starting...")
        time.sleep(startup_delay)
        
        # Create and start master system
        master_system = MasterHelmetSystem(config)
        master_system.start()
        
        logger.info("Master system ready (DEV MODE). IMU and GPIO are mocked.")
        logger.info("Starting interactive mode...")
        logger.info("Commands: 'capture [count] [interval]', 'stats', or 'quit'")
        
        # Interactive command loop
        try:
            while True:
                try:
                    user_input = input("\nmaster> ").strip().lower()
                    
                    if user_input == 'quit' or user_input == 'exit':
                        break
                    elif user_input == 'stats':
                        stats = master_system.mqtt_service.get_stats()
                        print(f"Statistics: {stats}")
                    elif user_input.startswith('capture'):
                        parts = user_input.split()
                        count = int(parts[1]) if len(parts) > 1 else 1
                        interval = int(parts[2]) if len(parts) > 2 else 5
                        
                        logger.info(f"Starting capture sequence: {count} captures, {interval}s interval")
                        master_system.capture_sequence(count, interval)
                    else:
                        print("Available commands: 'capture [count] [interval]', 'stats', 'quit'")
                        
                except EOFError:
                    break
                except KeyboardInterrupt:
                    break
                except ValueError as e:
                    print(f"Invalid command format: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            
    except Exception as e:
        logger.error(f"Fatal error during startup: {e}")
        if master_system:
            master_system.mqtt_service.cleanup()
        sys.exit(1)
    
    finally:
        if master_system:
            logger.info("Shutting down master system...")
            master_system.mqtt_service.cleanup()
            master_system.gpio_generator.cleanup()
        logger.info("Master Helmet System Shutdown Complete")

if __name__ == "__main__":
    main() 