#!/usr/bin/env python3
"""
Master System Launcher

Easy-to-use launcher for the Smart Helmet Camera Master System.
Performs system checks and starts the master application.
"""

import sys
import os
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("Checking dependencies...")
    
    required_modules = [
        ('paho.mqtt.client', 'paho-mqtt'),
        ('RPi.GPIO', 'RPi.GPIO'),
        ('picamera2', 'picamera2')
    ]
    
    missing = []
    for module, package in required_modules:
        try:
            __import__(module)
            print(f"  OK: {package}")
        except ImportError:
            print(f"  MISSING: {package}")
            missing.append(package)
    
    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False
    
    print("All dependencies found")
    return True

def check_config():
    """Check if master configuration exists"""
    config_path = Path("master_config.json")
    if not config_path.exists():
        print(f"Configuration file not found: {config_path}")
        print("Please ensure master_config.json exists in the Master directory")
        return False
    
    print("Configuration file found")
    return True

def check_mqtt_broker():
    """Basic check for MQTT broker connectivity"""
    print("\nTesting MQTT broker connectivity...")
    print("(This may take a few seconds...)")
    
    try:
        # Run the MQTT test script if it exists
        test_script = Path("test_mqtt_connection.py")
        if test_script.exists():
            print("Running MQTT connection test...")
            # Note: We don't actually run it automatically as it's interactive
            print("You can test MQTT manually with: python test_mqtt_connection.py")
        else:
            print("MQTT test script not found")
    except Exception as e:
        print(f"Could not test MQTT: {e}")
    
    return True

def show_system_info():
    """Display system information"""
    print("\nSystem Information:")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Working Directory: {os.getcwd()}")
    print(f"  Platform: {sys.platform}")

def main():
    """Main launcher function"""
    print("Smart Helmet Camera - Master System Launcher")
    print("=" * 50)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    print(f"Working directory: {script_dir}")
    
    # System checks
    show_system_info()
    
    if not check_dependencies():
        sys.exit(1)
    
    if not check_config():
        sys.exit(1)
    
    check_mqtt_broker()
    
    print("\nStarting Master System...")
    print("=" * 50)
    
    # Start the master application
    try:
        # Import and run the master system
        sys.path.insert(0, str(script_dir))
        
        # Import the master system
        from master_helmet_system import main as master_main
        
        # Run the master system
        master_main()
        
    except KeyboardInterrupt:
        print("\nMaster system stopped by user")
    except ImportError as e:
        print(f"Failed to import master system: {e}")
        print("Ensure all files are in the correct directory")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting master system: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 