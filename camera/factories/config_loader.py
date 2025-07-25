import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Handles loading and validation of configuration files"""
    
    @staticmethod
    def load_config(path="config.json"):
        """Load configuration from JSON file with validation"""
        try:
            config_path = Path(path)
            if not config_path.exists():
                logger.error(f"Configuration file not found: {path}")
                raise FileNotFoundError(f"Configuration file not found: {path}")
            
            with open(config_path, "r") as f:
                config = json.load(f)
            
            # Validate required fields
            required_fields = [
                'gpio_pin', 'startup_delay', 'min_high_duration', 
                'photo_base_dir', 'wifi_ssid', 'wifi_password'
            ]
            
            # Optional fields with defaults
            optional_fields = {
                'log_dir': '~/helmet_camera_logs'
            }
            
            # Add default values for missing optional fields
            for field, default_value in optional_fields.items():
                if field not in config:
                    config[field] = default_value
            
            missing_fields = [field for field in required_fields if field not in config]
            if missing_fields:
                logger.error(f"Missing required configuration fields: {missing_fields}")
                raise ValueError(f"Missing required configuration fields: {missing_fields}")
            
            logger.info(f"Configuration loaded successfully from {path}")
            return config
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise 