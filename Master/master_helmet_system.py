#!/usr/bin/env python3
"""
Master Helmet Camera System

Generates GPIO pulses and sends MQTT commands to slave helmet cameras.
Collects and logs responses from all connected slaves.
Includes web interface for monitoring and control.
Master also captures photos as cam1 and saves IMU data.
Supports automatic capture triggers: timer, IMU movement, GPIO pin 20.
"""

import time
import logging
import signal
import sys
import json
import threading
import datetime
import math
from pathlib import Path
from typing import Dict, List
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
from camera.factories import ConfigLoader
from camera.utils import setup_logging
from camera.services import MasterIMUSensor, HelmetCamera, JsonLogger, MasterOLEDDisplay
from web_master_server import setup_master_web_server, run_master_web_server


logger = logging.getLogger(__name__)


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
        
        # Enhanced statistics tracking per board
        self.stats = {
            "total_commands": 0,
            "successful_responses": 0,
            "failed_responses": 0,
            "timeout_responses": 0,
            "master_captures": 0,
            "master_capture_failures": 0
        }
        
        # Individual board statistics
        self.board_stats = {}
        for slave in self.slaves:
            self.board_stats[slave] = {
                "total_commands": 0,
                "successful_responses": 0,
                "failed_responses": 0,
                "timeout_responses": 0,
                "last_seen": None,
                "last_response_time_ms": 0,
                "avg_response_time_ms": 0,
                "response_count": 0,
                "status": "unknown"  # unknown, online, offline, timeout
            }
        
        # Timeout tracking
        self.timeout_check_interval = 30  # seconds
        self.command_timeout = config.get("timeout_ms", 5000) / 1000.0  # convert to seconds
        self._start_timeout_checker()
        
        # Polling/heartbeat
        self.polling_interval = 60  # seconds
        self.last_poll_time = time.time()
        
    def _start_timeout_checker(self):
        """Start background thread to check for timeouts"""
        def timeout_checker():
            while True:
                try:
                    self._check_timeouts()
                    time.sleep(self.timeout_check_interval)
                except Exception as e:
                    logger.error(f"Error in timeout checker: {e}")
                    
        timeout_thread = threading.Thread(target=timeout_checker, daemon=True)
        timeout_thread.start()
        logger.info("Timeout checker started")
    
    def _check_timeouts(self):
        """Check for timed out commands and update statistics"""
        current_time = time.time()
        timed_out_commands = []
        
        with self.response_lock:
            for command_id, command_data in self.pending_commands.items():
                if current_time - command_data["timestamp"] > self.command_timeout:
                    timed_out_commands.append(command_id)
                    
                    # Update stats for slaves that didn't respond
                    for slave_id in command_data["slaves_waiting"]:
                        if slave_id in self.board_stats:
                            self.board_stats[slave_id]["timeout_responses"] += 1
                            self.board_stats[slave_id]["status"] = "timeout"
                            self.stats["timeout_responses"] += 1
                            logger.warning(f"Timeout detected for slave {slave_id} on command {command_id}")
            
            # Remove timed out commands
            for command_id in timed_out_commands:
                if command_id in self.pending_commands:
                    del self.pending_commands[command_id]
                    logger.error(f"Command {command_id} timed out and removed")
    
    def send_poll_message(self):
        """Send polling/heartbeat message to check slave status"""
        if not self.connected:
            return
            
        current_time = time.time()
        if current_time - self.last_poll_time < self.polling_interval:
            return
            
        self.command_counter += 1
        poll_command = {
            "id": self.command_counter,
            "type": "poll",
            "t_utc_ns": time.time_ns(),
            "notes": "heartbeat_poll"
        }
        
        # Track as pending command for timeout detection
        with self.response_lock:
            self.pending_commands[self.command_counter] = {
                "slaves_waiting": set(self.slaves),
                "responses": {},
                "timestamp": current_time,
                "type": "poll"
            }
        
        try:
            topic = self.mqtt_config["topic_commands"]
            command_str = json.dumps(poll_command)
            result = self.client.publish(topic, command_str, qos=self.mqtt_config["qos"])
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Poll message {self.command_counter} sent to all slaves")
                self.last_poll_time = current_time
            else:
                logger.error(f"Failed to send poll message {self.command_counter}")
                
        except Exception as e:
            logger.error(f"Error sending poll message: {e}")
    
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
            command_start_time = command_data["timestamp"]
            response_time_ms = (time.time() - command_start_time) * 1000
            
            # Record response
            command_data["responses"][client_id] = response
            
            # Update board-specific statistics
            if client_id in self.board_stats:
                board_stat = self.board_stats[client_id]
                board_stat["total_commands"] += 1
                board_stat["last_seen"] = datetime.datetime.now().isoformat()
                board_stat["last_response_time_ms"] = response_time_ms
                board_stat["response_count"] += 1
                
                # Update average response time
                if board_stat["response_count"] > 1:
                    board_stat["avg_response_time_ms"] = (
                        (board_stat["avg_response_time_ms"] * (board_stat["response_count"] - 1) + response_time_ms) / 
                        board_stat["response_count"]
                    )
                else:
                    board_stat["avg_response_time_ms"] = response_time_ms
                
                # Update status and statistics
                if status == "ok":
                    board_stat["successful_responses"] += 1
                    board_stat["status"] = "online"
                    self.stats["successful_responses"] += 1
                elif status == "timeout":
                    board_stat["timeout_responses"] += 1
                    board_stat["status"] = "timeout"
                    self.stats["timeout_responses"] += 1
                else:
                    board_stat["failed_responses"] += 1
                    board_stat["status"] = "error"
                    self.stats["failed_responses"] += 1
            
            # Remove from waiting list
            if client_id in command_data["slaves_waiting"]:
                command_data["slaves_waiting"].remove(client_id)
            
            logger.info(f"Command {command_id}: {client_id} responded with {status} (response time: {response_time_ms:.1f}ms)")
            
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
    
    def get_board_stats(self):
        """Get individual board statistics"""
        return self.board_stats.copy()
    
    def get_detailed_status(self):
        """Get comprehensive system status"""
        return {
            "global_stats": self.stats.copy(),
            "board_stats": self.board_stats.copy(),
            "pending_commands": len(self.pending_commands),
            "connected": self.connected,
            "session_name": self.session_name
        }
    
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


class AutoCaptureManager:
    """Manages automatic photo capture triggers"""
    
    def __init__(self, config, master_system):
        self.config = config
        self.master_system = master_system
        self.triggers_config = config.get("capture_triggers", {})
        
        # Timer-based capture
        self.timer_thread = None
        self.timer_running = False
        
        # IMU movement detection
        self.imu_monitor_thread = None
        self.imu_monitoring = False
        self.last_imu_capture = 0
        self.last_acceleration = None
        
        # GPIO pin 20 monitoring
        self.gpio20_thread = None
        self.gpio20_monitoring = False
        self.gpio20_pin = self.triggers_config.get("gpio_pin20_pin", 20)
        self.gpio20_initialized = False
        
        logger.info(f"AutoCaptureManager initialized with config: {self.triggers_config}")
    
    def start_all_triggers(self):
        """Start all enabled capture triggers"""
        logger.info("Starting automatic capture triggers...")
        
        if self.triggers_config.get("timer_enabled", False):
            self.start_timer_capture()
        
        if self.triggers_config.get("imu_movement_enabled", False):
            self.start_imu_monitoring()
        
        if self.triggers_config.get("gpio_pin20_enabled", False):
            self.start_gpio20_monitoring()
    
    def stop_all_triggers(self):
        """Stop all capture triggers"""
        logger.info("Stopping automatic capture triggers...")
        
        self.stop_timer_capture()
        self.stop_imu_monitoring()
        self.stop_gpio20_monitoring()
    
    def start_timer_capture(self):
        """Start timer-based automatic capture"""
        if self.timer_running:
            return
            
        interval = self.triggers_config.get("timer_interval_seconds", 5)
        self.timer_running = True
        
        def timer_capture_loop():
            logger.info(f"Timer capture started - interval: {interval}s")
            while self.timer_running and self.master_system.running:
                try:
                    logger.info("Timer trigger - capturing photo")
                    self.master_system.capture_single_photo("timer_trigger")
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"Error in timer capture: {e}")
                    time.sleep(5)  # Wait before retrying
        
        self.timer_thread = threading.Thread(target=timer_capture_loop, daemon=True)
        self.timer_thread.start()
        logger.info("Timer-based capture trigger started")
    
    def stop_timer_capture(self):
        """Stop timer-based capture"""
        self.timer_running = False
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.join(timeout=2)
        logger.info("Timer capture stopped")
    
    def start_imu_monitoring(self):
        """Start IMU movement detection"""
        if not self.master_system.imu_sensor.available:
            logger.warning("IMU sensor not available - movement trigger disabled")
            return
            
        if self.imu_monitoring:
            return
            
        self.imu_monitoring = True
        
        def imu_monitor_loop():
            logger.info("IMU movement monitoring started")
            threshold = self.triggers_config.get("imu_movement_threshold", 2.0)
            cooldown = self.triggers_config.get("imu_movement_cooldown_seconds", 2.0)
            
            while self.imu_monitoring and self.master_system.running:
                try:
                    current_time = time.time()
                    if current_time - self.last_imu_capture < cooldown:
                        time.sleep(0.1)
                        continue
                    
                    imu_data = self.master_system.imu_sensor.read_data()
                    if not imu_data.get("available", False):
                        time.sleep(1)
                        continue
                    
                    # Calculate acceleration magnitude
                    accel = imu_data.get("acceleration", {})
                    current_acceleration = math.sqrt(
                        accel.get("x", 0)**2 + 
                        accel.get("y", 0)**2 + 
                        accel.get("z", 0)**2
                    )
                    
                    if self.last_acceleration is not None:
                        acceleration_change = abs(current_acceleration - self.last_acceleration)
                        
                        if acceleration_change > threshold:
                            logger.info(f"Movement detected - acceleration change: {acceleration_change:.2f} m/s²")
                            self.master_system.capture_single_photo("movement_trigger")
                            self.last_imu_capture = current_time
                    
                    self.last_acceleration = current_acceleration
                    time.sleep(0.1)  # 10Hz monitoring
                    
                except Exception as e:
                    logger.error(f"Error in IMU monitoring: {e}")
                    time.sleep(1)
        
        self.imu_monitor_thread = threading.Thread(target=imu_monitor_loop, daemon=True)
        self.imu_monitor_thread.start()
        logger.info("IMU movement detection started")
    
    def stop_imu_monitoring(self):
        """Stop IMU movement detection"""
        self.imu_monitoring = False
        if self.imu_monitor_thread and self.imu_monitor_thread.is_alive():
            self.imu_monitor_thread.join(timeout=2)
        logger.info("IMU movement monitoring stopped")
    
    def start_gpio20_monitoring(self):
        """Start GPIO pin 20 monitoring"""
        if self.gpio20_monitoring:
            return
            
        try:
            # Setup GPIO pin 20 with pull-up resistor
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio20_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.gpio20_initialized = True
            logger.info(f"GPIO pin {self.gpio20_pin} initialized with pull-up")
        except Exception as e:
            logger.error(f"Failed to initialize GPIO pin {self.gpio20_pin}: {e}")
            return
        
        self.gpio20_monitoring = True
        
        def gpio20_monitor_loop():
            logger.info(f"GPIO pin {self.gpio20_pin} monitoring started")
            last_state = GPIO.input(self.gpio20_pin)
            
            while self.gpio20_monitoring and self.master_system.running:
                try:
                    current_state = GPIO.input(self.gpio20_pin)
                    
                    # Trigger on falling edge (pull-up means LOW when pressed)
                    if last_state == GPIO.HIGH and current_state == GPIO.LOW:
                        logger.info(f"GPIO pin {self.gpio20_pin} trigger detected")
                        self.master_system.capture_single_photo("gpio20_trigger")
                        time.sleep(0.5)  # Debounce
                    
                    last_state = current_state
                    time.sleep(0.05)  # 20Hz polling
                    
                except Exception as e:
                    logger.error(f"Error in GPIO pin {self.gpio20_pin} monitoring: {e}")
                    time.sleep(1)
        
        self.gpio20_thread = threading.Thread(target=gpio20_monitor_loop, daemon=True)
        self.gpio20_thread.start()
        logger.info(f"GPIO pin {self.gpio20_pin} monitoring started")
    
    def stop_gpio20_monitoring(self):
        """Stop GPIO pin 20 monitoring"""
        self.gpio20_monitoring = False
        if self.gpio20_thread and self.gpio20_thread.is_alive():
            self.gpio20_thread.join(timeout=2)
        
        if self.gpio20_initialized:
            try:
                GPIO.cleanup(self.gpio20_pin)
                logger.info(f"GPIO pin {self.gpio20_pin} cleanup completed")
            except Exception as e:
                logger.error(f"Error cleaning up GPIO pin {self.gpio20_pin}: {e}")
        
        logger.info("GPIO pin 20 monitoring stopped")


class MasterHelmetSystem:
    """Main master system coordinator"""
    
    def __init__(self, config):
        self.config = config
        self.imu_sensor = MasterIMUSensor()  # Master-only IMU access
        self.mqtt_service = MQTTMasterService(config, self.imu_sensor)
        self.gpio_generator = GPIOPulseGenerator(config)
        
        # Master camera functionality (cam1)
        self.master_camera = HelmetCamera(cam_number=1)
        self.session_logger = JsonLogger(cam_number=1, config=config)
        self.session_dir = None
        
        # OLED display functionality
        self.oled_display = MasterOLEDDisplay()
        
        # Display update thread
        self.display_thread = None
        self.display_running = False
        
        # Auto capture manager
        self.auto_capture = AutoCaptureManager(config, self)
        
        self.running = False
        
    def start(self):
        """Start master system"""
        logger.info("Starting Master Helmet System...")
        
        # Start MQTT service
        self.mqtt_service.start()
        
        # Generate session name
        now = datetime.datetime.now()
        session_name = f"session_{now.strftime('%Y%m%d_%H%M%S')}"
        self.mqtt_service.session_name = session_name
        
        # Start master camera session
        self.session_logger.start_session()
        self.session_dir = self.session_logger.session_dir
        
        # Create IMU data file in session directory
        self._setup_imu_logging()
        
        logger.info(f"Master system started - Session: {session_name}")
        logger.info(f"Master session directory: {self.session_dir}")
        
        # Start OLED display updates
        self._start_display_updates()
        
        # Start automatic capture triggers
        self.auto_capture.start_all_triggers()
        
        self.running = True
    
    def _setup_imu_logging(self):
        """Setup IMU data logging to session directory"""
        if self.session_dir:
            self.imu_log_path = self.session_dir / "master_imu_data.json"
            logger.info(f"IMU data will be saved to: {self.imu_log_path}")
    
    def _save_imu_data(self, command_id, imu_data):
        """Save IMU data to session file"""
        if not hasattr(self, 'imu_log_path') or not self.imu_log_path:
            return
            
        try:
            # Load existing data or create new
            imu_log = []
            if self.imu_log_path.exists():
                try:
                    with open(self.imu_log_path, 'r') as f:
                        imu_log = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    imu_log = []
            
            # Add new IMU reading
            imu_entry = {
                "command_id": command_id,
                "timestamp": datetime.datetime.now().isoformat(),
                "imu_data": imu_data
            }
            imu_log.append(imu_entry)
            
            # Save updated data
            with open(self.imu_log_path, 'w') as f:
                json.dump(imu_log, f, indent=2)
                
            logger.debug(f"IMU data saved for command {command_id}")
            
        except Exception as e:
            logger.error(f"Failed to save IMU data: {e}")
    
    def _start_display_updates(self):
        """Start background thread for OLED display updates"""
        if not self.oled_display.available:
            logger.info("OLED display not available, skipping display updates")
            return
            
        self.display_running = True
        
        def display_update_loop():
            """Background thread for updating OLED display"""
            while self.display_running and self.running:
                try:
                    self.oled_display.update_display(self)
                    time.sleep(1)  # Update every second, display manages its own timing
                except Exception as e:
                    logger.error(f"Error in display update loop: {e}")
                    time.sleep(5)  # Wait longer on error
        
        self.display_thread = threading.Thread(target=display_update_loop, daemon=True)
        self.display_thread.start()
        logger.info("OLED display update thread started")
    
    def capture_single_photo(self, trigger_source="manual"):
        """Capture a single photo from all cameras"""
        try:
            logger.info(f"Starting single photo capture - trigger: {trigger_source}")
            
            # Generate GPIO pulse for hardware synchronization
            pulse_success = self.gpio_generator.generate_pulse()
            if not pulse_success:
                logger.error("Failed to generate pulse for single capture")
            
            # Send MQTT command to slaves
            command_id = self.mqtt_service.send_capture_command(
                exposure_us=self.config["exposure_us"],
                timeout_ms=self.config["timeout_ms"],
                notes=f"{self.mqtt_service.session_name}_{trigger_source}"
            )
            
            # Capture master photo (cam1) simultaneously
            master_photo_success = False
            try:
                if self.session_dir:
                    master_photo_path = self.master_camera.capture(
                        self.session_dir, 
                        self.session_logger.photo_count
                    )
                    if master_photo_path:
                        self.session_logger.log_success(master_photo_path)
                        self.mqtt_service.stats["master_captures"] += 1
                        master_photo_success = True
                        logger.info(f"Master photo captured: {master_photo_path}")
                    else:
                        self.session_logger.log_failure("master_capture_failed")
                        self.mqtt_service.stats["master_capture_failures"] += 1
                        logger.error("Master photo capture failed")
                        
            except Exception as e:
                self.session_logger.log_failure(f"master_capture_error: {e}")
                self.mqtt_service.stats["master_capture_failures"] += 1
                logger.error(f"Master photo capture error: {e}")
            
            # Save IMU data if available
            if command_id and self.imu_sensor and self.imu_sensor.available:
                try:
                    imu_data = self.imu_sensor.read_data()
                    self._save_imu_data(command_id, imu_data)
                except Exception as e:
                    logger.error(f"Failed to save IMU data for command {command_id}: {e}")
            
            if command_id:
                logger.info(f"Capture command {command_id} sent to slaves ({trigger_source}), master capture: {'success' if master_photo_success else 'failed'}")
                
                # Show capture status on OLED display
                if self.oled_display.available:
                    self.oled_display.show_capture_status(command_id, master_photo_success)
            else:
                logger.error(f"Failed to send capture command ({trigger_source})")
                
                # Show error on OLED display
                if self.oled_display.available:
                    self.oled_display.show_error_message(f"Failed command {trigger_source}")
            
            # Send polling message periodically
            self.mqtt_service.send_poll_message()
            
            return command_id, master_photo_success
            
        except Exception as e:
            logger.error(f"Error in single photo capture ({trigger_source}): {e}")
            return None, False
    
    def web_capture_single_photo(self):
        """Web interface trigger for single photo with extra session info"""
        logger.info("Web interface single photo capture requested")
        
        # Create a special session note for web captures
        now = datetime.datetime.now()
        web_session_note = f"web_single_{now.strftime('%H%M%S')}"
        
        return self.capture_single_photo(f"web_{web_session_note}")
    
    def cleanup(self):
        """Cleanup master system"""
        self.running = False
        
        # Stop automatic capture triggers
        self.auto_capture.stop_all_triggers()
        
        # Stop display updates
        self.display_running = False
        if self.display_thread and self.display_thread.is_alive():
            self.display_thread.join(timeout=2)
        
        # Cleanup camera and session
        if hasattr(self, 'master_camera'):
            self.master_camera.cleanup()
        if hasattr(self, 'session_logger'):
            self.session_logger.end_session()
        
        # Cleanup OLED display
        if hasattr(self, 'oled_display'):
            self.oled_display.cleanup()
        
        # Cleanup other components
        self.gpio_generator.cleanup()
        self.mqtt_service.cleanup()
        logger.info("Master system cleanup completed")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.info(f"Received signal {signum}, initiating shutdown...")
    sys.exit(0)


def main():
    """Main application entry point for master - automatic operation"""
    
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
        
        logger.info("Master system running automatically with configured triggers:")
        triggers = config.get("capture_triggers", {})
        if triggers.get("timer_enabled", False):
            logger.info(f"  - Timer capture: every {triggers.get('timer_interval_seconds', 5)}s")
        if triggers.get("imu_movement_enabled", False):
            logger.info(f"  - Movement detection: threshold {triggers.get('imu_movement_threshold', 2.0)} m/s²")
        if triggers.get("gpio_pin20_enabled", False):
            logger.info(f"  - GPIO pin {triggers.get('gpio_pin20_pin', 20)} trigger enabled")
        logger.info("  - Web interface single capture available")
        
        # Keep the main thread alive
        try:
            while master_system.running:
                time.sleep(1)
                # Optional: Check system health, log status, etc.
                
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