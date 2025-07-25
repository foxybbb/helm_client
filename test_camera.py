#!/usr/bin/env python3
"""
Camera Test Script

Test script to verify that picamera2 is working correctly.
This script can be used for testing camera functionality without the full application.
"""

import time
import logging
import signal
import sys
from pathlib import Path
from camera.utils import setup_logging
from camera.factories import ConfigLoader, CameraFactory

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.info(f"Received signal {signum}, shutting down camera test...")
    sys.exit(0)

def test_camera():
    """Test camera functionality"""
    
    # Setup basic logging
    setup_logging(log_level=logging.DEBUG)
    logging.info("Camera Test Starting...")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    camera = None
    
    try:
        # Load configuration
        config = ConfigLoader.load_config()
        logging.info("Configuration loaded successfully")
        
        # Create camera
        camera = CameraFactory.create(config)
        logging.info("Camera factory created camera instance")
        
        # Create test directory
        test_dir = Path("/tmp/helmet_camera_test")
        test_dir.mkdir(exist_ok=True)
        logging.info(f"Test directory created: {test_dir}")
        
        # Take test photos
        logging.info("Taking test photos...")
        for i in range(3):
            logging.info(f"Capturing test photo {i+1}/3...")
            photo_path = camera.capture(test_dir, i)
            
            if photo_path:
                logging.info(f"✅ Test photo {i+1} captured successfully: {photo_path}")
                # Display file info
                photo_file = Path(photo_path)
                if photo_file.exists():
                    size_mb = photo_file.stat().st_size / (1024 * 1024)
                    logging.info(f"   File size: {size_mb:.2f} MB")
            else:
                logging.error(f"❌ Test photo {i+1} failed")
            
            # Wait between photos
            if i < 2:
                logging.info("Waiting 3 seconds before next photo...")
                time.sleep(3)
        
        logging.info("Camera test completed successfully!")
        logging.info(f"Test photos saved in: {test_dir}")
        logging.info("You can check the photos to verify camera is working correctly.")
        
    except KeyboardInterrupt:
        logging.info("Test interrupted by user")
    except Exception as e:
        logging.error(f"Camera test error: {e}")
        import traceback
        logging.debug(f"Full traceback: {traceback.format_exc()}")
    finally:
        if camera:
            camera.cleanup()
        logging.info("Camera test cleanup completed")

if __name__ == "__main__":
    test_camera() 