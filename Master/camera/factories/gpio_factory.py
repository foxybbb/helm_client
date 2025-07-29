import logging
from camera.services import GPIOWatcher

logger = logging.getLogger(__name__)

class GPIOWatcherFactory:
    """Factory for creating GPIO watcher instances"""
    
    @staticmethod
    def create(config):
        """Create a GPIOWatcher instance"""
        try:
            gpio_watcher = GPIOWatcher(config)
            logger.info(f"GPIO factory created watcher for pin {config['gpio_pin']}")
            return gpio_watcher
            
        except Exception as e:
            logger.error(f"Error creating GPIO watcher instance: {e}")
            raise 