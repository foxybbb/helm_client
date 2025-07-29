# Smart Helmet Camera - Master System

This is the master system that coordinates synchronized photo capture across multiple helmet-mounted cameras via MQTT communication.

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

## Features

- **GPIO Pulse Generation**: Hardware synchronization signals
- **MQTT Command Broadcasting**: Sends capture commands to all slaves
- **Response Collection**: Tracks and logs responses from all helmet cameras
- **Interactive Interface**: Easy-to-use command interface
- **Session Management**: Organized photo sessions with timestamps

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
  "notes": "session_20250729_01"
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