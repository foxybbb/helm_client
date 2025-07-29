#!/usr/bin/env python3
"""
Slave Helmet Camera Application

A Raspberry Pi-based smart helmet camera system that receives MQTT commands
from master and captures photos using picamera2.
"""

import time
import logging
import signal
import sys
from camera.factories import CameraFactory, LoggerFactory, ConfigLoader
from camera.services import MQTTCameraService
from camera.utils import setup_logging
from pathlib import Path


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.info(f"Received signal {signum}, initiating shutdown...")
    sys.exit(0)

def main():
    """Main application entry point for slave"""
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    camera = None
    mqtt_service = None
    
    try:
        # Load slave configuration
        config = ConfigLoader.load_config("slave_config.json")
        
        # Initialize logging system with configured directory
        log_dir = config.get("log_dir")
        if log_dir and log_dir.startswith("~"):
            log_dir = str(Path(log_dir).expanduser())
        setup_logging(log_dir=log_dir)
        logging.info(f"Slave Helmet Camera System Starting - Client ID: {config['client_id']}")
        
        # Configuration already loaded for logging setup
        startup_delay = config["startup_delay"]
        
        logging.info(f"Waiting {startup_delay} seconds before starting...")
        time.sleep(startup_delay)
        
        # Create camera
        camera = CameraFactory.create(config)
        logging.info("Camera initialized successfully")
        
        # Create MQTT service
        mqtt_service = MQTTCameraService(config, camera)
        mqtt_service.start()
        logging.info("MQTT service started successfully")
        
        logging.info("All components initialized. Slave ready for MQTT commands.")
        
        # MQTT-driven main loop
        try:
            while True:
                # System is now MQTT-driven, so we just need to keep alive
                # Log heartbeat every 5 minutes
                time.sleep(300)  # 5 minutes
                logging.debug("Slave heartbeat - system running normally")
                if mqtt_service.connected:
                    logging.info("MQTT status: Connected")
                else:
                    logging.warning("MQTT status: Disconnected - attempting reconnect")
                    # Try to reconnect
                    try:
                        mqtt_service.start()
                    except Exception as e:
                        logging.error(f"Failed to reconnect MQTT: {e}")
                    
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt received, shutting down...")
        except Exception as e:
            logging.error(f"Unexpected error in main loop: {e}")
            raise
        finally:
            # Cleanup in reverse order
            if mqtt_service:
                mqtt_service.cleanup()
            if camera:
                camera.cleanup()
            logging.info("Slave Helmet Camera System Shutdown Complete")
            
    except Exception as e:
        logging.error(f"Fatal error during startup: {e}")
        # Ensure cleanup even on startup failure
        if mqtt_service:
            mqtt_service.cleanup()
        if camera:
            camera.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main() 
