import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Factory for loading configuration with validation"""
    
    @staticmethod
    def load_config(config_file="config.json"):
        """Load and validate configuration from JSON file"""
        try:
            # Get the path relative to the script location
            script_dir = Path(__file__).parent.parent.parent  # Go up to project root
            config_path = script_dir / config_file
            
            # Fallback to current directory if not found
            if not config_path.exists():
                config_path = Path(config_file)
            
            if not config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_file}")
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Validate required fields
            ConfigLoader._validate_config(config)
            
            logger.debug(f"Configuration loaded from: {config_path}")
            return config
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    @staticmethod
    def _validate_config(config):
        """Validate configuration has required fields"""
        # Base required fields that both master and slave need
        base_required = ["log_dir"]
        
        # Check if this is a slave config (has client_id)
        if "client_id" in config:
            # Slave configuration
            required_fields = base_required + [
                "client_id", "gpio_pin", "startup_delay", "photo_base_dir", "mqtt"
            ]
            mqtt_required = ["broker_host", "broker_port", "topic_commands", "topic_responses"]
        else:
            # Master configuration  
            required_fields = base_required + [
                "master_id", "gpio_pin", "startup_delay", "exposure_us", "timeout_ms", "mqtt", "slaves"
            ]
            mqtt_required = ["broker_host", "broker_port", "topic_commands", "topic_responses"]
        
        # Check main fields
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required configuration field: {field}")
        
        # Check MQTT configuration
        mqtt_config = config.get("mqtt", {})
        for field in mqtt_required:
            if field not in mqtt_config:
                raise ValueError(f"Missing required MQTT configuration field: {field}")
        
        logger.debug("Configuration validation passed") 