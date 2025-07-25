import logging
from camera.services import JsonLogger
from .camera_factory import get_cam_number

logger = logging.getLogger(__name__)

class LoggerFactory:
    """Factory for creating logger instances"""
    
    @staticmethod
    def create(config):
        """Create a JsonLogger instance"""
        try:
            cam_number = get_cam_number()
            json_logger = JsonLogger(cam_number, config)
            logger.info(f"Logger factory created logger instance for cam {cam_number}")
            return json_logger
            
        except Exception as e:
            logger.error(f"Error creating logger instance: {e}")
            raise 