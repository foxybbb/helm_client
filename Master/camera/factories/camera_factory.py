import os
import logging
from camera.services import HelmetCamera

logger = logging.getLogger(__name__)

def get_cam_number():
    """Extract camera number from hostname"""
    try:
        hostname = os.uname()[1]
        if not hostname.startswith("rpihelmet"):
            logger.warning(f"Hostname {hostname} doesn't follow rpihelmet pattern, using default camera number 1")
            return 1
        
        cam_number = int(hostname.replace("rpihelmet", ""))
        logger.info(f"Detected camera number: {cam_number}")
        return cam_number
        
    except (ValueError, IndexError) as e:
        logger.error(f"Error extracting camera number from hostname: {e}, using default 1")
        return 1

class CameraFactory:
    """Factory for creating camera instances"""
    
    @staticmethod
    def create(config):
        """Create a HelmetCamera instance"""
        try:
            cam_number = get_cam_number()
            camera = HelmetCamera(cam_number)
            logger.info(f"Camera factory created camera instance for cam {cam_number}")
            return camera
            
        except Exception as e:
            logger.error(f"Error creating camera instance: {e}")
            raise 