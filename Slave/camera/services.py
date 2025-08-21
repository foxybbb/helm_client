import os
import time
import json
import datetime
import subprocess
import logging
import threading
import atexit
from pathlib import Path
import RPi.GPIO as GPIO
from picamera2 import Picamera2
import paho.mqtt.client as mqtt

# IMU sensor support removed - only master board has IMU access
# IMU functionality has been moved to master-only architecture

logger = logging.getLogger(__name__)

# IMU sensor class removed - only master board has IMU access
# All IMU functionality moved to master system

class MQTTCameraService:
    """MQTT service for handling camera commands from master"""
    
    def __init__(self, config, camera_service):
        self.config = config
        self.client_id = config["client_id"]
        self.camera_service = camera_service
        self.mqtt_config = config["mqtt"]
        
        # MQTT client setup
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # Capture state tracking
        self.last_command_id = None
        self.last_capture_status = {
            "timestamp": None,
            "status": "idle",
            "command_id": None,
            "filename": None,
            "imu_data": None
        }
        
        # Session management for grouping photos
        self.current_session_dir = None
        self.current_session_date = None
        self.session_timeout = 1800  # 30 minutes timeout for session
        self.last_capture_time = 0
        self.photos_in_session = 0
        
        # Response tracking
        self.last_response_time = time.time()
        
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
                if hasattr(self, 'connected') and self.connected:
                    break
                time.sleep(0.5)
            
            logger.info("Slave MQTT service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start slave MQTT service: {e}")
            raise
        
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when MQTT client connects"""
        if rc == 0:
            self.connected = True
            logger.info(f"Slave MQTT connected successfully as {self.client_id}")
            # Subscribe to command topic
            topic = self.mqtt_config["topic_commands"]
            client.subscribe(topic, qos=self.mqtt_config["qos"])
            logger.info(f"Subscribed to command topic: {topic}")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when MQTT client disconnects"""
        self.connected = False
        logger.warning(f"Slave MQTT disconnected with code {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Handle incoming command messages from master"""
        try:
            command_str = msg.payload.decode('utf-8')
            command = json.loads(command_str)
            
            logger.info(f"Received command: {command}")
            self._process_command(command)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse command JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _get_session_directory(self):
        """Get or create appropriate session directory for grouping photos"""
        current_time = time.time()
        current_date = datetime.datetime.now().strftime('%Y%m%d')
        
        # Check if we need a new session (new day or timeout exceeded)
        need_new_session = (
            self.current_session_dir is None or
            self.current_session_date != current_date or
            (current_time - self.last_capture_time) > self.session_timeout
        )
        
        if need_new_session:
            # Create new session directory
            cam_number = self.client_id[-1]  # Extract camera number from client_id
            base_dir = Path(self.config["photo_base_dir"]) / f"helmet-cam{cam_number}"
            
            # Create daily session directory
            session_name = f"session_{current_date}"
            
            # If multiple sessions in same day, add sequence number
            session_dir = base_dir / session_name
            counter = 1
            while session_dir.exists() and self.photos_in_session > 100:  # Start new session after 100 photos
                session_name = f"session_{current_date}_{counter:03d}"
                session_dir = base_dir / session_name
                counter += 1
            
            session_dir.mkdir(parents=True, exist_ok=True)
            
            self.current_session_dir = session_dir
            self.current_session_date = current_date
            self.photos_in_session = 0
            
            logger.info(f"Created new session directory: {session_dir}")
        
        return self.current_session_dir
    
    def _clean_notes_for_filename(self, notes):
        """Clean up notes field to remove web sequences and unwanted suffixes"""
        if not notes:
            return "capture"
        
        # Remove web sequence patterns
        import re
        notes = re.sub(r'_web_sequence_\d+', '', notes)
        notes = re.sub(r'_web_single_\d+', '', notes)
        notes = re.sub(r'_web_\w+', '', notes)
        
        # Remove timestamp suffixes that are too specific
        notes = re.sub(r'_\d{6}$', '', notes)  # Remove HHMMSS
        notes = re.sub(r'_\d{8}_\d{6}$', '', notes)  # Remove YYYYMMDD_HHMMSS
        
        # Clean up multiple underscores
        notes = re.sub(r'_+', '_', notes)
        notes = notes.strip('_')
        
        # Default if nothing left
        if not notes or notes == "session":
            return "capture"
        
        return notes
    
    def _process_command(self, command):
        """Process camera capture command"""
        command_id = command["id"]
        command_type = command.get("type", "capture")
        start_time_ns = time.time_ns()
        
        # Handle polling/heartbeat messages
        if command_type == "poll":
            self._handle_poll_command(command_id, start_time_ns)
            return
        
        # Update status
        self.last_capture_status.update({
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "processing",
            "command_id": command_id,
            "filename": None,
            "imu_data": None
        })
        
        try:
            # Store command ID to avoid duplicates
            if self.last_command_id == command_id:
                logger.warning(f"Duplicate command ID {command_id}, ignoring")
                return
            self.last_command_id = command_id
            
            logger.info(f"Processing capture command {command_id}")
            
            # Get session directory (groups photos properly)
            session_dir = self._get_session_directory()
            
            # Clean up the notes for filename
            notes = command.get("notes", "capture")
            clean_notes = self._clean_notes_for_filename(notes)
            
            # Create meaningful filename
            cam_number = self.client_id[-1]
            timestamp = datetime.datetime.now().strftime('%H%M%S')
            filename = f"cam{cam_number}_{timestamp}_{command_id:06d}.jpg"
            
            # Capture photo
            photo_path = self.camera_service.capture_with_filename(session_dir, filename)
            
            end_time_ns = time.time_ns()
            jitter_us = (start_time_ns - command["t_utc_ns"]) // 1000  # Convert to microseconds
            
            if photo_path:
                # Update session tracking
                self.last_capture_time = time.time()
                self.photos_in_session += 1
                
                # Send success response
                response = {
                    "id": command_id,
                    "client": self.client_id,
                    "status": "ok",
                    "started_ns": start_time_ns,
                    "finished_ns": end_time_ns,
                    "file": filename,
                    "jitter_us": jitter_us,
                    "session_dir": str(session_dir.name),
                    "photos_in_session": self.photos_in_session,
                    "error": ""
                }
                
                self.last_capture_status.update({
                    "status": "success",
                    "filename": filename
                })
                
                logger.info(f"Photo captured successfully: {filename} (Session: {session_dir.name}, Photo #{self.photos_in_session})")
                
            else:
                # Send failure response
                response = {
                    "id": command_id,
                    "client": self.client_id,
                    "status": "error",
                    "started_ns": start_time_ns,
                    "finished_ns": end_time_ns,
                    "file": "",
                    "jitter_us": jitter_us,
                    "error": "Photo capture failed"
                }
                
                self.last_capture_status.update({
                    "status": "failed",
                    "filename": None
                })
                
                logger.error(f"Photo capture failed for command {command_id}")
            
            # Send response to master
            self._send_response(response)
                
        except Exception as e:
            logger.error(f"Error processing command {command_id}: {e}")
            
            # Send error response
            error_response = {
                "id": command_id,
                "client": self.client_id,
                "status": "error",
                "started_ns": start_time_ns,
                "finished_ns": time.time_ns(),
                "file": "",
                "jitter_us": 0,
                "error": str(e)
            }
            
            self._send_response(error_response)
    
    def _handle_poll_command(self, command_id, start_time_ns):
        """Handle polling/heartbeat command from master"""
        logger.debug(f"Handling poll command {command_id}")
        
        response = {
            "id": command_id,
            "client": self.client_id,
            "status": "online",
            "started_ns": start_time_ns,
            "finished_ns": time.time_ns(),
            "file": "",
            "jitter_us": 0,
            "last_capture": self.last_capture_status,
            "current_session": str(self.current_session_dir.name) if self.current_session_dir else None,
            "photos_in_session": self.photos_in_session,
            "error": ""
        }
        
        self._send_response(response)
    
    def _send_response(self, response):
        """Send response back to master"""
        try:
            topic = self.mqtt_config["topic_responses"]
            response_str = json.dumps(response)
            result = self.client.publish(topic, response_str, qos=self.mqtt_config["qos"])
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Response sent for command {response['id']}")
                self.last_response_time = time.time()
            else:
                logger.error(f"Failed to send response for command {response['id']}")
                
        except Exception as e:
            logger.error(f"Error sending response: {e}")
    
    def get_status(self):
        """Get current service status"""
        return {
            "client_id": self.client_id,
            "connected": getattr(self, 'connected', False),
            "last_capture": self.last_capture_status,
            "last_response_time": self.last_response_time,
            "current_session": str(self.current_session_dir.name) if self.current_session_dir else None,
            "photos_in_session": self.photos_in_session
        }
    
    def cleanup(self):
        """Cleanup MQTT service"""
        try:
            if hasattr(self.client, 'loop_stop'):
                self.client.loop_stop()
            if hasattr(self.client, 'disconnect'):
                self.client.disconnect()
            logger.info("Slave MQTT service cleanup completed")
        except Exception as e:
            logger.error(f"Error during slave MQTT cleanup: {e}")


class HelmetCamera:
    def __init__(self, cam_number):
        self.cam_number = cam_number
        self.camera = None
        self._camera_initialized = False
        self._setup_camera()
        
        # Register cleanup function
        atexit.register(self.cleanup)
        
    def _setup_camera(self):
        """Initialize the picamera2 instance"""
        try:
            logger.debug("Initializing picamera2...")
            
            # Create and configure camera
            self.camera = Picamera2()
            
            # Configure camera for still image capture
            # Use a reasonable resolution for helmet camera use
            config = self.camera.create_still_configuration(
                main={"size": (1920, 1080)},  # Full HD resolution
                lores={"size": (640, 480)},   # Lower resolution for preview
                display="lores"
            )
            self.camera.configure(config)
            
            # Start the camera
            self.camera.start()
            
            # Allow camera to warm up
            time.sleep(2)
            
            self._camera_initialized = True
            logger.info(f"Camera {self.cam_number} initialized successfully with picamera2")
            
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            self._camera_initialized = False
            raise
        
    def capture(self, session_dir, photo_count):
        """Capture a photo using picamera2 and return the file path"""
        try:
            if not self._camera_initialized or not self.camera:
                logger.error("Camera not initialized, attempting to reinitialize...")
                self._setup_camera()
                if not self._camera_initialized:
                    return None
            
            # Create timestamp for filename
            timestamp = datetime.datetime.now().strftime('%H%M%S')
            filename = f"cam{self.cam_number}_{timestamp}_{photo_count}.jpg"
            photo_path = session_dir / filename
            
            logger.debug(f"Attempting to capture photo: {photo_path}")
            
            # Capture photo using picamera2
            self.camera.capture_file(str(photo_path))
            
            # Verify file was created and has reasonable size
            if photo_path.exists() and photo_path.stat().st_size > 1000:  # At least 1KB
                logger.info(f"Photo captured successfully: {photo_path} ({photo_path.stat().st_size} bytes)")
                return str(photo_path)
            else:
                logger.error(f"Photo file not created or too small: {photo_path}")
                return None
                
        except Exception as e:
            logger.error(f"Photo capture error: {e}")
            # Try to reinitialize camera on error
            try:
                logger.info("Attempting camera reinitialization after error...")
                self.cleanup()
                self._setup_camera()
            except Exception as reinit_error:
                logger.error(f"Camera reinitialization failed: {reinit_error}")
            return None
    
    def capture_with_filename(self, session_dir, filename):
        """Capture a photo with specific filename"""
        if not self._camera_initialized:
            logger.error("Camera not initialized")
            return None
            
        try:
            # Ensure session directory exists
            session_dir = Path(session_dir)
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # Create full file path
            photo_path = session_dir / filename
            
            logger.debug(f"Capturing photo to: {photo_path}")
            
            # Capture the image
            self.camera.capture_file(str(photo_path))
            
            # Verify file was created and has reasonable size
            if photo_path.exists() and photo_path.stat().st_size > 1000:  # At least 1KB
                logger.info(f"Photo captured successfully: {photo_path}")
                return str(photo_path)
            else:
                logger.error("Photo file was not created or is too small")
                return None
                
        except Exception as e:
            logger.error(f"Failed to capture photo: {e}")
            return None

    
    def cleanup(self):
        """Cleanup camera resources"""
        try:
            if self.camera and self._camera_initialized:
                logger.debug("Stopping camera...")
                self.camera.stop()
                self.camera.close()
                self._camera_initialized = False
                logger.info("Camera cleanup completed")
        except Exception as e:
            logger.error(f"Error during camera cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        return self

    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()

class JsonLogger:
    def __init__(self, cam_number, config):
        self.cam_number = cam_number
        self.photo_count = 0
        self.config = config
        self.session = {
            "camera": cam_number,
            "start_time": None,
            "end_time": None,
            "photos": [],
            "failures": []
        }
        self.session_dir = None
        self.log_path = None

    def start_session(self):
        now = datetime.datetime.now()
        self.session["start_time"] = now.isoformat()
        date_folder = now.strftime('%Y%m%d')  # Only date
        base_dir = Path(self.config["photo_base_dir"]) / f"helmet-cam{self.cam_number}"
        self.session_dir = base_dir / f"session_{date_folder}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.session_dir / "session_log.json"
        logger.info(f"Session started for camera {self.cam_number}: {self.session_dir}")

    def log_success(self, photo_path):
        """Log a successful photo capture"""
        if photo_path:
            self.session["photos"].append({
                "index": self.photo_count,
                "path": photo_path,
                "timestamp": datetime.datetime.now().isoformat()
            })
            logger.info(f"Photo {self.photo_count} logged successfully: {photo_path}")
        else:
            self.session["failures"].append({
                "index": self.photo_count,
                "reason": "capture_failed",
                "timestamp": datetime.datetime.now().isoformat()
            })
            logger.warning(f"Photo {self.photo_count} capture failed")
        
        self.photo_count += 1
        self._save_log()

    def log_failure(self, reason):
        """Log a failed photo capture"""
        self.session["failures"].append({
            "index": self.photo_count,
            "reason": reason,
            "timestamp": datetime.datetime.now().isoformat()
        })
        logger.error(f"Photo {self.photo_count} failed: {reason}")
        self.photo_count += 1
        self._save_log()

    def end_session(self):
        """End the current session and save final log"""
        self.session["end_time"] = datetime.datetime.now().isoformat()
        self._save_log()
        logger.info(f"Session ended for camera {self.cam_number}. "
                   f"Total photos: {len(self.session['photos'])}, "
                   f"Failures: {len(self.session['failures'])}")

    def _save_log(self):
        """Save current session state to log file"""
        if self.log_path:
            try:
                with open(self.log_path, 'w') as f:
                    json.dump(self.session, f, indent=2)
                logger.debug(f"Session log saved to {self.log_path}")
            except Exception as e:
                logger.error(f"Failed to save session log: {e}")

class GPIOWatcher:
    def __init__(self, config):
        self.pin = config["gpio_pin"]
        self.config = config
        self.last_high_time = None
        self.wifi_scan_triggered = False
        self.wifi_timer = None
        self.capture_callback = None
        self._gpio_initialized = False
        
        # Initialize GPIO
        self._setup_gpio()
        
        # Register cleanup function to run on exit
        atexit.register(self.cleanup)
        
    def _setup_gpio(self):
        """Initialize GPIO settings and interrupts"""
        try:
            # Clean up any existing GPIO state first
            try:
                GPIO.cleanup(self.pin)
            except:
                pass  # Ignore cleanup errors
            
            # Set GPIO mode and disable warnings
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            
            logger.debug(f"Setting up GPIO pin {self.pin} as input")
            
            # Configure pin as input with pull-down resistor
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            
            # Small delay to ensure pin is ready
            time.sleep(0.1)
            
            # Check if pin can be read
            initial_state = GPIO.input(self.pin)
            logger.debug(f"GPIO pin {self.pin} initial state: {initial_state}")
            
            # Add interrupt handlers for both edges
            logger.debug(f"Adding edge detection to GPIO pin {self.pin}")
            GPIO.add_event_detect(self.pin, GPIO.BOTH, 
                                callback=self._gpio_interrupt_handler, 
                                bouncetime=50)  # 50ms debounce
            
            self._gpio_initialized = True
            logger.info(f"GPIO pin {self.pin} initialized successfully with hardware interrupts")
            
        except RuntimeError as e:
            if "already been added" in str(e):
                logger.warning(f"GPIO pin {self.pin} edge detection already exists, cleaning up and retrying...")
                try:
                    GPIO.remove_event_detect(self.pin)
                    time.sleep(0.1)
                    GPIO.add_event_detect(self.pin, GPIO.BOTH, 
                                        callback=self._gpio_interrupt_handler, 
                                        bouncetime=50)
                    self._gpio_initialized = True
                    logger.info(f"GPIO pin {self.pin} initialized successfully after cleanup")
                except Exception as retry_e:
                    logger.error(f"Failed to initialize GPIO after cleanup: {retry_e}")
                    raise
            else:
                logger.error(f"GPIO RuntimeError: {e}")
                raise
        except PermissionError as e:
            logger.error(f"Permission denied accessing GPIO. Try running with sudo or add user to gpio group: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize GPIO pin {self.pin}: {e}")
            logger.debug(f"GPIO error details: {type(e).__name__}: {e}")
            raise
    
    def _gpio_interrupt_handler(self, channel):
        """Hardware interrupt handler for GPIO state changes"""
        try:
            current_state = GPIO.input(channel)
            current_time = time.time()
            
            if current_state == GPIO.HIGH:  # Rising edge
                self.last_high_time = current_time
                self.wifi_scan_triggered = False
                logger.debug(f"GPIO pin {channel} RISING edge detected")
                
                # Cancel any existing WiFi timer
                if self.wifi_timer:
                    self.wifi_timer.cancel()
                
                # Schedule WiFi scan after minimum high duration
                self.wifi_timer = threading.Timer(
                    self.config["min_high_duration"], 
                    self._trigger_wifi_scan
                )
                self.wifi_timer.start()
                
                # Trigger photo capture callback if set
                if self.capture_callback:
                    threading.Thread(target=self.capture_callback, daemon=True).start()
                    
            else:  # Falling edge
                self.last_high_time = None
                logger.debug(f"GPIO pin {channel} FALLING edge detected")
                
                # Cancel WiFi timer if running
                if self.wifi_timer:
                    self.wifi_timer.cancel()
                    self.wifi_timer = None
                
        except Exception as e:
            logger.error(f"Error in GPIO interrupt handler: {e}")
    
    def _trigger_wifi_scan(self):
        """Timer callback to trigger WiFi scan"""
        if not self.wifi_scan_triggered and self._gpio_initialized and GPIO.input(self.pin) == GPIO.HIGH:
            self.wifi_scan_triggered = True
            logger.info("WiFi scan triggered by prolonged GPIO HIGH signal")
            threading.Thread(target=self.scan_and_connect_wifi, daemon=True).start()
    
    def set_capture_callback(self, callback):
        """Set callback function to be called on rising edge"""
        self.capture_callback = callback
        logger.debug("Photo capture callback registered")
    
    def get_current_state(self):
        """Get current GPIO pin state"""
        if self._gpio_initialized:
            return GPIO.input(self.pin)
        return GPIO.LOW
    
    def is_high_duration_exceeded(self):
        """Check if GPIO has been high for minimum duration"""
        return (self.last_high_time and 
                time.time() - self.last_high_time > self.config["min_high_duration"])
    
    def scan_and_connect_wifi(self):
        """Scan for WiFi and connect if target network is found"""
        if self.wifi_scan_triggered:
            return
            
        self.wifi_scan_triggered = True
        logger.info("Starting WiFi scan after prolonged GPIO HIGH signal")
        
        try:
            # Scan for available networks
            result = subprocess.run(['iwlist', 'wlan0', 'scan'], 
                                  capture_output=True, text=True, timeout=30)
            
            if self.config["wifi_ssid"] in result.stdout:
                logger.info(f"Target WiFi network '{self.config['wifi_ssid']}' found. Attempting connection...")
                
                # Attempt to connect
                connect_result = subprocess.run([
                    'nmcli', 'device', 'wifi', 'connect', self.config["wifi_ssid"],
                    'password', self.config["wifi_password"], 'ifname', 'wlan0'
                ], capture_output=True, text=True, timeout=30)
                
                if connect_result.returncode == 0:
                    logger.info("WiFi connection successful")
                else:
                    logger.warning(f"WiFi connection failed: {connect_result.stderr}")
            else:
                logger.warning(f"Target WiFi network '{self.config['wifi_ssid']}' not found in scan results")
                
        except subprocess.TimeoutExpired:
            logger.error("WiFi scan/connect operation timed out")
        except Exception as e:
            logger.error(f"WiFi scan/connect error: {e}")
    
    def cleanup(self):
        """Clean up GPIO resources"""
        try:
            if self.wifi_timer:
                self.wifi_timer.cancel()
                self.wifi_timer = None
            
            if self._gpio_initialized:
                try:
                    GPIO.remove_event_detect(self.pin)
                    logger.debug(f"Removed edge detection from GPIO pin {self.pin}")
                except Exception as e:
                    logger.debug(f"Error removing edge detection: {e}")
                
                try:
                    GPIO.cleanup(self.pin)
                    logger.debug(f"Cleaned up GPIO pin {self.pin}")
                except Exception as e:
                    logger.debug(f"Error cleaning up GPIO pin: {e}")
                
                self._gpio_initialized = False
                logger.info("GPIO cleanup completed")
                
        except Exception as e:
            logger.error(f"Error during GPIO cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup() 