#!/usr/bin/env python3
"""
Master Helmet Camera System

Generates GPIO pulses and sends MQTT commands to slave helmet cameras.
Collects and logs responses from all connected slaves.
Includes web interface for monitoring and control.
"""

import time
import logging
import signal
import sys
import json
import threading
import datetime
from pathlib import Path
from typing import Dict, List
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
from camera.factories import ConfigLoader
from camera.utils import setup_logging
from camera.services import MasterIMUSensor
from web_master_server import setup_master_web_server, run_master_web_server


class MQTTMasterService:
    """MQTT service for master to communicate with slaves"""
    
    def __init__(self, config, imu_sensor=None):
        self.config = config
        self.master_id = config["master_id"]
        self.mqtt_config = config["mqtt"]
        self.slaves = config["slaves"]
        self.imu_sensor = imu_sensor  # Master's IMU sensor reference
        
        # MQTT client
        self.client = mqtt.Client(client_id=self.master_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # Connection status
        self.connected = False
        
        # Response tracking
        self.pending_commands = {}  # command_id -> {slaves_waiting: set, responses: dict, timestamp: float}
        self.response_lock = threading.Lock()
        
        # Session data
        self.command_counter = 0
        self.session_name = None
        
        # Statistics tracking
        self.stats = {
            "total_commands": 0,
            "successful_responses": 0,
            "failed_responses": 0,
            "timeout_responses": 0
        }
        
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when MQTT client connects"""
        if rc == 0:
            self.connected = True
            logger.info(f"Master MQTT connected successfully as {self.master_id}")
            # Subscribe to response topic
            topic = self.mqtt_config["topic_responses"]
            client.subscribe(topic, qos=self.mqtt_config["qos"])
            logger.info(f"Subscribed to response topic: {topic}")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when MQTT client disconnects"""
        self.connected = False
        logger.warning(f"Master MQTT disconnected with code {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Handle incoming response messages from slaves"""
        try:
            response_str = msg.payload.decode('utf-8')
            response = json.loads(response_str)
            
            logger.info(f"Received response: {response}")
            self._process_response(response)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT response: {e}")
    
    def _process_response(self, response):
        """Process response from slave"""
        with self.response_lock:
            command_id = response.get("id")
            client_id = response.get("client")
            status = response.get("status")
            
            if command_id not in self.pending_commands:
                logger.warning(f"Received response for unknown command {command_id}")
                return
            
            command_data = self.pending_commands[command_id]
            
            # Record response
            command_data["responses"][client_id] = response
            
            # Update statistics
            if status == "ok":
                self.stats["successful_responses"] += 1
            elif status == "timeout":
                self.stats["timeout_responses"] += 1
            else:
                self.stats["failed_responses"] += 1
            
            # Remove from waiting list
            if client_id in command_data["slaves_waiting"]:
                command_data["slaves_waiting"].remove(client_id)
            
            logger.info(f"Command {command_id}: {client_id} responded with {status}")
            
            # Note: IMU data is no longer expected from slaves (master-only IMU access)
            
            # Check if all slaves have responded
            if not command_data["slaves_waiting"]:
                self._command_completed(command_id)
    
    def _command_completed(self, command_id):
        """Handle command completion when all slaves have responded"""
        command_data = self.pending_commands[command_id]
        duration = time.time() - command_data["timestamp"]
        
        # Log summary
        responses = command_data["responses"]
        success_count = len([r for r in responses.values() if r["status"] == "ok"])
        total_count = len(responses)
        
        logger.info(f"Command {command_id} completed in {duration:.2f}s: {success_count}/{total_count} successful")
        
        # Log individual responses
        for client_id, response in responses.items():
            if response["status"] == "ok":
                logger.info(f"  {client_id}: SUCCESS - {response['file']} (jitter: {response['jitter_us']}μs)")
            else:
                logger.error(f"  {client_id}: FAILED - {response.get('error', 'Unknown error')}")
        
        # Clean up
        del self.pending_commands[command_id]
    
    def start(self):
        """Start MQTT service"""
        try:
            broker_host = self.mqtt_config["broker_host"]
            broker_port = self.mqtt_config["broker_port"]
            keepalive = self.mqtt_config["keepalive"]
            
            logger.info(f"Connecting to MQTT broker at {broker_host}:{broker_port}")
            self.client.connect(broker_host, broker_port, keepalive)
            
            # Start network loop in separate thread
            self.client.loop_start()
            
            # Wait for connection
            for _ in range(10):
                if self.connected:
                    break
                time.sleep(0.5)
            
            if not self.connected:
                raise Exception("Failed to connect to MQTT broker within timeout")
                
            logger.info("Master MQTT service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start master MQTT service: {e}")
            raise
    
    def send_capture_command(self, exposure_us, timeout_ms, notes):
        """Send capture command to all slaves"""
        if not self.connected:
            logger.error("MQTT not connected, cannot send command")
            return None
        
        # Generate command
        self.command_counter += 1
        command_id = self.command_counter
        current_time_ns = time.time_ns()
        
        command = {
            "id": command_id,
            "t_utc_ns": current_time_ns,
            "exposure_us": exposure_us,
            "timeout_ms": timeout_ms,
            "notes": notes
        }
        
        # Add master's IMU data to command (master-only IMU access)
        if self.imu_sensor and self.imu_sensor.available:
            master_imu_data = self.imu_sensor.read_data()
            command["master_imu"] = master_imu_data
            logger.info(f"Including master IMU data in command {command_id}")
        else:
            command["master_imu"] = {"available": False, "error": "Master IMU not available"}
            logger.warning(f"Master IMU not available for command {command_id}")
        
        # Track pending command
        with self.response_lock:
            self.pending_commands[command_id] = {
                "slaves_waiting": set(self.slaves),
                "responses": {},
                "timestamp": time.time()
            }
        
        # Send command
        topic = self.mqtt_config["topic_commands"]
        command_str = json.dumps(command)
        
        try:
            result = self.client.publish(topic, command_str, qos=self.mqtt_config["qos"])
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.stats["total_commands"] += 1
                logger.info(f"Command {command_id} sent to all slaves")
                return command_id
            else:
                logger.error(f"Failed to send command {command_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending MQTT command: {e}")
            return None
    
    def get_stats(self):
        """Get current statistics"""
        return self.stats.copy()
    
    def cleanup(self):
        """Cleanup MQTT service"""
        try:
            if hasattr(self.client, 'loop_stop'):
                self.client.loop_stop()
            if hasattr(self.client, 'disconnect'):
                self.client.disconnect()
            logger.info("Master MQTT service cleanup completed")
        except Exception as e:
            logger.error(f"Error during master MQTT cleanup: {e}")


class GPIOPulseGenerator:
    """Generates GPIO pulses for camera synchronization"""
    
    def __init__(self, config):
        self.pin = config["gpio_pin"]
        self.pulse_duration_ms = config["pulse_duration_ms"]
        self.pulse_interval_ms = config["pulse_interval_ms"]
        self._gpio_initialized = False
        
        self._setup_gpio()
        
    def _setup_gpio(self):
        """Initialize GPIO for pulse generation"""
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)
            
            self._gpio_initialized = True
            logger.info(f"GPIO pin {self.pin} initialized for pulse generation")
            
        except Exception as e:
            logger.error(f"Failed to initialize GPIO: {e}")
            raise
    
    def generate_pulse(self):
        """Generate a single pulse"""
        if not self._gpio_initialized:
            logger.error("GPIO not initialized")
            return False
        
        try:
            # Generate pulse
            GPIO.output(self.pin, GPIO.HIGH)
            time.sleep(self.pulse_duration_ms / 1000.0)  # Convert to seconds
            GPIO.output(self.pin, GPIO.LOW)
            
            logger.debug(f"Pulse generated on pin {self.pin} for {self.pulse_duration_ms}ms")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate pulse: {e}")
            return False
    
    def cleanup(self):
        """Cleanup GPIO"""
        try:
            if self._gpio_initialized:
                GPIO.cleanup(self.pin)
                logger.info("GPIO pulse generator cleanup completed")
        except Exception as e:
            logger.error(f"Error during GPIO cleanup: {e}")


class MasterHelmetSystem:
    """Main master system coordinator"""
    
    def __init__(self, config):
        self.config = config
        self.imu_sensor = MasterIMUSensor()  # Master-only IMU access
        self.mqtt_service = MQTTMasterService(config, self.imu_sensor)
        self.gpio_generator = GPIOPulseGenerator(config)
        self.running = False
        
    def start(self):
        """Start master system"""
        logger.info("Starting Master Helmet System...")
        
        # Start MQTT service
        self.mqtt_service.start()
        
        # Generate session name
        now = datetime.datetime.now()
        session_name = f"session_{now.strftime('%Y%m%d_%H')}"
        self.mqtt_service.session_name = session_name
        
        logger.info(f"Master system started - Session: {session_name}")
        self.running = True
    
    def capture_sequence(self, count=1, interval_seconds=5):
        """Execute a sequence of synchronized captures"""
        logger.info(f"Starting capture sequence: {count} captures, {interval_seconds}s interval")
        
        for i in range(count):
            logger.info(f"Capture {i+1}/{count}")
            
            # Generate GPIO pulse for hardware synchronization
            pulse_success = self.gpio_generator.generate_pulse()
            if not pulse_success:
                logger.error(f"Failed to generate pulse for capture {i+1}")
            
            # Send MQTT command
            command_id = self.mqtt_service.send_capture_command(
                exposure_us=self.config["exposure_us"],
                timeout_ms=self.config["timeout_ms"],
                notes=self.mqtt_service.session_name
            )
            
            if command_id:
                logger.info(f"Capture command {command_id} sent")
            else:
                logger.error(f"Failed to send capture command for capture {i+1}")
            
            # Wait between captures (except for last one)
            if i < count - 1:
                logger.info(f"Waiting {interval_seconds}s before next capture...")
                time.sleep(interval_seconds)
        
        logger.info("Capture sequence completed")
    
    def cleanup(self):
        """Cleanup master system"""
        self.running = False
        self.gpio_generator.cleanup()
        self.mqtt_service.cleanup()
        logger.info("Master system cleanup completed")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.info(f"Received signal {signum}, initiating shutdown...")
    sys.exit(0)


def main():
    """Main application entry point for master"""
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    master_system = None
    web_thread = None
    
    try:
        # Load master configuration
        config = ConfigLoader.load_config("master_config.json")
        
        # Initialize logging
        log_dir = config.get("log_dir")
        if log_dir and log_dir.startswith("~"):
            log_dir = str(Path(log_dir).expanduser())
        setup_logging(log_dir=log_dir)
        logger.info(f"Master Helmet System Starting - Master ID: {config['master_id']}")
        
        # Startup delay
        startup_delay = config["startup_delay"]
        logger.info(f"Waiting {startup_delay} seconds before starting...")
        time.sleep(startup_delay)
        
        # Create and start master system
        master_system = MasterHelmetSystem(config)
        master_system.start()
        
        # Setup and start web server
        web_port = config.get("web_port", 8081)
        setup_master_web_server(master_system, config)
        
        web_thread = threading.Thread(
            target=run_master_web_server,
            kwargs={"host": "0.0.0.0", "port": web_port, "debug": False},
            daemon=True
        )
        web_thread.start()
        logger.info(f"Master web interface started on port {web_port}")
        logger.info(f"Open http://<master-ip>:{web_port} in your browser to control the system")
        
        logger.info("Master system ready. Starting interactive mode...")
        logger.info("Commands: 'capture [count] [interval]', 'stats', or 'quit'")
        
        # Interactive command loop
        try:
            while master_system.running:
                try:
                    user_input = input("master> ").strip().lower()
                    
                    if user_input == "quit" or user_input == "exit":
                        break
                    elif user_input.startswith("capture"):
                        parts = user_input.split()
                        count = int(parts[1]) if len(parts) > 1 else 1
                        interval = float(parts[2]) if len(parts) > 2 else 5.0
                        master_system.capture_sequence(count, interval)
                    elif user_input == "stats":
                        stats = master_system.mqtt_service.get_stats()
                        print(f"Statistics:")
                        print(f"  Total commands sent: {stats['total_commands']}")
                        print(f"  Successful responses: {stats['successful_responses']}")
                        print(f"  Failed responses: {stats['failed_responses']}")
                        print(f"  Timeout responses: {stats['timeout_responses']}")
                        print(f"  Pending commands: {len(master_system.mqtt_service.pending_commands)}")
                    elif user_input == "help":
                        print("Available commands:")
                        print("  capture [count] [interval] - Take photos (default: 1 photo, 5s interval)")
                        print("  stats - Show system statistics")
                        print("  quit/exit - Shutdown system")
                        print("  help - Show this help")
                    else:
                        print("Unknown command. Type 'help' for available commands.")
                        
                except EOFError:
                    # Handle Ctrl+D
                    break
                except ValueError as e:
                    print(f"Invalid input: {e}")
                except Exception as e:
                    logger.error(f"Error processing command: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            raise
        finally:
            if master_system:
                master_system.cleanup()
            logger.info("Master Helmet System Shutdown Complete")
            
    except Exception as e:
        logger.error(f"Fatal error during startup: {e}")
        if master_system:
            master_system.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    # Setup basic logging for startup
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    main() 