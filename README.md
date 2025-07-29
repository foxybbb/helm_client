# Smart Helmet Camera Project

A distributed Raspberry Pi-based smart helmet camera system with MQTT communication between master and slave devices.

## Architecture

### Master-Slave System
- **Master**: Generates GPIO pulses and sends MQTT commands to coordinate photo capture
- **Slaves**: Receive MQTT commands and capture photos using picamera2

### Communication Protocol
Master sends JSON commands:
```json
{
  "id": 321,
  "t_utc_ns": 1753828805123456789,
  "exposure_us": 8000,
  "timeout_ms": 5000,
  "notes": "session_20250729_01"
}
```

Slaves respond with:
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

## Project Structure

```
helmet_camera/
├── master_helmet_system.py   # Master application
├── config.json              # Master configuration
├── requirements.txt         # Dependencies (includes paho-mqtt)
├── Slave/                   # Slave device files
│   ├── slave_helmet_camera.py  # Slave application
│   ├── slave_config.json      # Slave configuration
│   ├── camera/                 # Camera services and factories
│   └── test_*.py              # Test scripts
└── camera/                  # Original camera code (for reference)
```

## Features

### Master Features
- GPIO pulse generation for hardware synchronization
- MQTT command broadcasting to multiple slaves
- Response collection and logging
- Interactive command interface
- Session management

### Slave Features
- MQTT command processing with threading
- Picamera2-based photo capture
- Precise timestamp tracking and jitter calculation
- Automatic response generation
- Error handling and reporting

## Configuration

### Master Configuration (`config.json`)
```json
{
  "master_id": "helm_master",
  "gpio_pin": 17,
  "startup_delay": 5,
  "pulse_duration_ms": 100,
  "pulse_interval_ms": 1000,
  "exposure_us": 8000,
  "timeout_ms": 5000,
  "photo_base_dir": "/home/rpi",
  "log_dir": "~/helmet_camera_logs",
  "mqtt": {
    "broker_host": "192.168.1.100",
    "broker_port": 1883,
    "topic_commands": "helmet/commands",
    "topic_responses": "helmet/responses",
    "keepalive": 60,
    "qos": 1
  },
  "slaves": ["rpihelmet1", "rpihelmet2", "rpihelmet3"]
}
```

### Slave Configuration (`Slave/slave_config.json`)
```json
{
  "client_id": "rpihelmet3",
  "gpio_pin": 17,
  "startup_delay": 5,
  "photo_base_dir": "/home/rpi",
  "log_dir": "~/helmet_camera_logs",
  "mqtt": {
    "broker_host": "192.168.1.100",
    "broker_port": 1883,
    "topic_commands": "helmet/commands",
    "topic_responses": "helmet/responses",
    "keepalive": 60,
    "qos": 1
  }
}
```

## Installation

1. **Install dependencies**: `pip install -r requirements.txt`
2. **MQTT Broker**: Setup an MQTT broker (e.g., Mosquitto) on your network
3. **Configure hostnames**: Use format `rpihelmet{number}` (e.g., `rpihelmet1`, `rpihelmet2`)
4. **GPIO permissions**: `sudo usermod -a -G gpio $USER` (then logout/login)
5. **Test components**:
   - Master: `python master_helmet_system.py`
   - Slave: `cd Slave && python slave_helmet_camera.py`

## Usage

### Master System
```bash
python master_helmet_system.py
```
Interactive commands:
- `capture [count] [interval]` - Take synchronized photos
- `help` - Show available commands
- `quit` - Shutdown system

### Slave System
```bash
cd Slave
python slave_helmet_camera.py
```
Slaves automatically connect to MQTT broker and wait for commands.

## Output Structure

Photos are saved to:
```
/home/rpi/helmet-cam{N}/{session_name}/
├── cam{N}_{session}_{id}.jpg
└── ...
```

Logs are saved to:
```
~/helmet_camera_logs/
├── helmet_camera_{YYYYMMDD}.log
└── ...
```

## Testing

- **Camera functionality**: `cd Slave && python test_camera.py`
- **GPIO functionality**: `cd Slave && python test_gpio.py`
- **GPIO diagnostics**: `cd Slave && python check_gpio.py`

## Technical Details

### Threading Implementation
- **Master**: Uses threading for MQTT response handling and command processing
- **Slaves**: Uses threading for MQTT message processing to avoid blocking camera operations

### Synchronization
1. Master generates GPIO pulse for hardware-level synchronization
2. Master sends MQTT command with precise timestamp
3. Slaves process commands in separate threads
4. Slaves calculate jitter and respond with timing information

### Error Handling
- Connection resilience with automatic MQTT reconnection
- Comprehensive error reporting in slave responses
- Timeout handling for unresponsive slaves
- Graceful cleanup on shutdown signals 