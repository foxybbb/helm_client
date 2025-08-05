# Smart Helmet Automatic Capture System

The master helmet system now supports automatic photo capture triggers without requiring any terminal interaction. The system runs as a service and can be controlled via the web interface.

## Automatic Capture Triggers

The system supports four different capture trigger methods:

### 1. Web Interface Trigger
- **Manual control** via web browser
- Access: `http://<master-ip>:8081`
- Two capture options:
  - **Standard captures**: Multi-photo sequences with intervals
  - **Web Single Photo**: Special single captures with extra session information

### 2. Timer-Based Capture
- **Automatic periodic captures** at configurable intervals
- Configuration in `master_config.json`:
```json
"capture_triggers": {
  "timer_enabled": true,
  "timer_interval_seconds": 5
}
```

### 3. Movement Detection (IMU Sensor)
- **Motion-triggered captures** using the BNO055 IMU sensor
- Detects changes in acceleration above a threshold
- Configuration in `master_config.json`:
```json
"capture_triggers": {
  "imu_movement_enabled": true,
  "imu_movement_threshold": 2.0,
  "imu_movement_cooldown_seconds": 2.0
}
```

### 4. GPIO Pin 20 Physical Trigger
- **Physical button/switch trigger** on GPIO pin 20
- Uses pull-up resistor configuration (trigger on LOW/press)
- Configuration in `master_config.json`:
```json
"capture_triggers": {
  "gpio_pin20_enabled": true,
  "gpio_pin20_pin": 20
}
```

## Configuration Options

Edit `master_config.json` to enable/disable triggers:

```json
{
  "capture_triggers": {
    "timer_enabled": false,
    "timer_interval_seconds": 5,
    "imu_movement_enabled": false,
    "imu_movement_threshold": 2.0,
    "imu_movement_cooldown_seconds": 2.0,
    "gpio_pin20_enabled": true,
    "gpio_pin20_pin": 20
  }
}
```

## Service Management

The system runs automatically as a systemd service:

### Install Service
```bash
sudo cp master_startup_service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable master_startup_service
```

### Control Service
```bash
# Start service
sudo systemctl start master_startup_service

# Stop service  
sudo systemctl stop master_startup_service

# Check status
sudo systemctl status master_startup_service

# View logs
sudo journalctl -u master_startup_service -f
```

## Hardware Connections

### GPIO Pin 20 Trigger
- Connect a push button between GPIO pin 20 and GND
- Internal pull-up resistor is automatically configured
- Press button to trigger photo capture

### IMU Sensor (BNO055)
- Connected via I2C (SDA/SCL pins)
- Automatically detected if available
- Used for movement-based capture triggers

## Web Interface

Access the web dashboard at `http://<master-ip>:8081`:

- **System Status**: Shows MQTT, IMU, and display status
- **Capture Control**: Manual photo capture controls
- **Automatic Triggers Status**: Shows which triggers are enabled/running
- **Statistics**: Capture success rates and counts
- **Connected Slaves**: Status of all slave helmet cameras
- **System Logs**: Real-time system log monitoring

## Log Files

System logs are saved to:
- **Service logs**: `sudo journalctl -u master_startup_service`
- **Application logs**: `~/helmet_camera_logs/helmet_camera_YYYYMMDD.log`
- **Session data**: `/home/rpi/helmet-cam1/session_YYYYMMDD/`

## Troubleshooting

### Check System Status
```bash
# Check if service is running
sudo systemctl status master_startup_service

# Check for errors
sudo journalctl -u master_startup_service --since "1 hour ago"

# Check configuration
cat /home/ivan/Dev/TTI/SmartHelmet/repos/helm_client/Master/master_config.json
```

### Common Issues

1. **GPIO Permission Errors**: User must be in `gpio` group
2. **IMU Not Available**: Check I2C connections and libraries
3. **MQTT Connection Failed**: Verify broker IP and network connectivity
4. **Web Interface Not Accessible**: Check firewall settings and port 8081

### Reset Configuration
```bash
# Disable all triggers
vim master_config.json
# Set all *_enabled to false

# Restart service
sudo systemctl restart master_startup_service
```

## Example Configurations

### Security Camera Mode (Timer + Motion)
```json
"capture_triggers": {
  "timer_enabled": true,
  "timer_interval_seconds": 10,
  "imu_movement_enabled": true,
  "imu_movement_threshold": 1.5,
  "gpio_pin20_enabled": false
}
```

### Manual Only Mode (GPIO + Web)
```json
"capture_triggers": {
  "timer_enabled": false,
  "imu_movement_enabled": false,
  "gpio_pin20_enabled": true
}
```

### High Frequency Monitoring
```json
"capture_triggers": {
  "timer_enabled": true,
  "timer_interval_seconds": 2,
  "imu_movement_enabled": true,
  "imu_movement_threshold": 0.5,
  "gpio_pin20_enabled": true
}
``` 