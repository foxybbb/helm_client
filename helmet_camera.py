#!/usr/bin/env python3
"""
Helmet Camera Main Application

A Raspberry Pi-based smart helmet camera system that captures photos 
based on GPIO input and manages WiFi connectivity.
"""

import time
import logging
import signal
import sys
from camera.factories import CameraFactory, LoggerFactory, GPIOWatcherFactory, ConfigLoader
from camera.utils import setup_logging
from pathlib import Path


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.info(f"Received signal {signum}, initiating shutdown...")
    sys.exit(0)

def main():
    """Main application entry point"""
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    camera = None
    session_logger = None
    gpio = None
    
    try:
        # Load configuration first for log directory
        config = ConfigLoader.load_config()
        
        # Initialize logging system with configured directory
        log_dir = config.get("log_dir")
        if log_dir and log_dir.startswith("~"):
            log_dir = str(Path(log_dir).expanduser())
        setup_logging(log_dir=log_dir)
        logging.info("Helmet Camera System Starting...")
        
        # Configuration already loaded for logging setup
        startup_delay = config["startup_delay"]
        
        logging.info(f"Waiting {startup_delay} seconds before starting main loop...")
        time.sleep(startup_delay)
        
        # Create components using factories
        camera = CameraFactory.create(config)
        session_logger = LoggerFactory.create(config)
        gpio = GPIOWatcherFactory.create(config)
        
        # Start session
        session_logger.start_session()
        
        # Define photo capture callback
        def capture_photo():
            """Callback function for photo capture triggered by GPIO interrupt"""
            try:
                photo_path = camera.capture(session_logger.session_dir, session_logger.photo_count)
                session_logger.log_success(photo_path)
            except Exception as e:
                logging.error(f"Error in photo capture callback: {e}")
                session_logger.log_failure(f"callback_error: {e}")
        
        # Register the callback with GPIO watcher
        gpio.set_capture_callback(capture_photo)
        
        logging.info("All components initialized, GPIO interrupts active. System ready.")
        
        # Event-driven main loop - much more efficient than polling
        try:
            while True:
                # System is now interrupt-driven, so we just need to keep alive
                # Log heartbeat every 10 minutes
                time.sleep(600)  # 10 minutes
                logging.debug("Application heartbeat - system running normally")
                logging.info(f"Current GPIO state: {'HIGH' if gpio.get_current_state() else 'LOW'}")
                    
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt received, shutting down...")
        except Exception as e:
            logging.error(f"Unexpected error in main loop: {e}")
            raise
        finally:
            # Cleanup in reverse order
            if camera:
                camera.cleanup()
            if gpio:
                gpio.cleanup()
            if session_logger:
                session_logger.end_session()
            logging.info("Helmet Camera System Shutdown Complete")
            
    except Exception as e:
        logging.error(f"Fatal error during startup: {e}")
        # Ensure cleanup even on startup failure
        if camera:
            camera.cleanup()
        if gpio:
            gpio.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main() 
