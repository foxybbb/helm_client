# Master Helmet Camera System

Coordinate multiple Raspberry Pi helmet cameras with synchronized capture commands via MQTT.
**Only the master board has access to the IMU sensor** - providing centralized orientation data for all captures.

## Features

- **GPIO Pulse Generation**: Hardware-level trigger for precise timing
- **MQTT Command Broadcasting**: Send synchronized commands to multiple slave cameras
- **Master-Only IMU Integration**: BNO055 sensor data included in all capture commands
- **Response Coordination**: Collect and track responses from all connected slaves
- **Web Interface**: Monitor status and control captures via web dashboard
- **Session Management**: Organized photo storage with session-based directories

## Architecture

### Master-Only IMU Design
- **Centralized IMU**: Only master board connects to BNO055 IMU sensor
- **IMU Data Broadcasting**: Master includes its IMU readings in every capture command
- **Consistent Reference Frame**: All photos captured with the same orientation data
- **Simplified Slaves**: Slave boards focus solely on camera operations

### Communication Flow
```
Master IMU Reading → Command with IMU Data → MQTT → All Slaves → Photo Capture
```

## Installation

### Hardware Requirements
- Raspberry Pi 4 (Master Board)
- BNO055 IMU sensor connected to master board I2C
- MQTT broker (can run on master or separate device)
- Network connection to slave helmet cameras

### Software Setup
```bash
# Clone the repository
git clone <repo_url>
cd helmet_client/Master

# Install dependencies
pip install -r requirements.txt

# Enable I2C for IMU sensor
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable

# Configure MQTT and slaves
cp master_config.json.example master_config.json
nano master_config.json
```

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure MQTT broker IP in `master_config.json`:**
   ```json
   "mqtt": {
     "broker_host": "192.168.1.100",  # Change to your MQTT broker IP
     ...
   }
   ```

3. **Test MQTT connection:**
   ```bash
   python test_mqtt_connection.py
   ```

4. **Run master system:**
   ```bash
   python run_master.py
   ```
   
   Or directly:
   ```bash
   python master_helmet_system.py
   ```

## Usage Commands

Once the master system is running, use these interactive commands:

- `capture` - Take 1 photo on all helmets
- `capture 5` - Take 5 photos with default 5-second intervals
- `capture 3 2` - Take 3 photos with 2-second intervals
- `help` - Show available commands
- `quit` or `exit` - Shutdown system

## Configuration

Edit `master_config.json` to configure:

```json
{
  "master_id": "helm_master",
  "gpio_pin": 17,                    # GPIO pin for pulse generation
  "pulse_duration_ms": 100,          # Pulse duration in milliseconds
  "exposure_us": 8000,               # Camera exposure time
  "timeout_ms": 5000,                # Command timeout
  "mqtt": {
    "broker_host": "192.168.1.100", # Your MQTT broker IP
    "broker_port": 1883,
    "topic_commands": "helmet/commands",
    "topic_responses": "helmet/responses"
  },
  "slaves": [                        # List of connected helmet cameras
    "rpihelmet1",
    "rpihelmet2", 
    "rpihelmet3"
  ]
}
```

## MQTT Protocol

### Commands Sent to Slaves
```json
{
  "id": 321,
  "t_utc_ns": 1753828805123456789,
  "exposure_us": 8000,
  "timeout_ms": 5000,
  "notes": "session_20250729_01",
  "master_imu": {
    "available": true,
    "timestamp_ns": 1753828805123456789,
    "temperature": 24.5,
    "acceleration": {"x": 0.1, "y": 0.2, "z": 9.8, "unit": "m/s²"},
    "magnetic": {"x": 25.3, "y": -15.7, "z": 48.1, "unit": "µT"},
    "gyroscope": {"x": 0.01, "y": -0.02, "z": 0.0, "unit": "rad/s"},
    "euler": {"heading": 45.2, "roll": 1.3, "pitch": -2.1, "unit": "degrees"},
    "quaternion": {"w": 0.999, "x": 0.001, "y": -0.002, "z": 0.045},
    "calibration_status": {"system": 3, "gyroscope": 3, "accelerometer": 3, "magnetometer": 3}
  }
}
```

### Responses from Slaves
```json
{
  "id": 321,
  "client": "rpihelmet3",
  "status": "ok",
  "started_ns": 1753828805123461000,
  "finished_ns": 1753828805131461000,
  "file": "cam3_20250729_000321.jpg",
  "jitter_us": 43,
  "error": ""
}
```

**Note**: Slaves no longer include IMU data in responses since only the master board has IMU access.

## Files

- `master_helmet_system.py` - Main master application
- `run_master.py` - Easy launcher with system checks
- `master_config.json` - Master configuration
- `test_mqtt_connection.py` - MQTT connectivity test
- `requirements.txt` - Python dependencies
- `camera/` - Shared camera utilities

## Troubleshooting

**MQTT Connection Issues:**
- Verify MQTT broker is running: `sudo systemctl status mosquitto`
- Test connectivity: `python test_mqtt_connection.py`
- Check firewall settings

**GPIO Permission Issues:**
```bash
sudo usermod -a -G gpio $USER
# Then logout and login
```

**No Slave Responses:**
- Ensure slaves are running and connected
- Check MQTT topics match between master and slaves
- Verify network connectivity 