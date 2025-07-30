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
            
            # Determine config type and validate accordingly
            is_master_config = 'master_id' in config or 'slaves' in config
            is_slave_config = 'client_id' in config or 'min_high_duration' in config
            
            if is_master_config:
                # Master configuration validation
                required_fields = [
                    'master_id', 'gpio_pin', 'startup_delay', 'pulse_duration_ms',
                    'pulse_interval_ms', 'exposure_us', 'timeout_ms', 'photo_base_dir',
                    'mqtt', 'slaves'
                ]
                optional_fields = {
                    'log_dir': '~/helmet_camera_logs',
                    'web_port': 8081
                }
                logger.info("Loading master configuration")
                
            elif is_slave_config:
                # Slave configuration validation
                required_fields = [
                    'client_id', 'gpio_pin', 'startup_delay', 'min_high_duration', 
                    'photo_base_dir', 'wifi_ssid', 'wifi_password', 'mqtt'
                ]
                optional_fields = {
                    'log_dir': '~/helmet_camera_logs'
                }
                logger.info("Loading slave configuration")
                
            else:
                # Fallback to generic validation
                required_fields = ['gpio_pin', 'startup_delay', 'photo_base_dir']
                optional_fields = {
                    'log_dir': '~/helmet_camera_logs'
                }
                logger.warning("Could not determine config type, using generic validation")
            
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