# Helmet Camera Architecture

## 📁 Interrupt-Driven Project Structure

```
helmet_camera/
├── helmet_camera.py              # Main application with hardware interrupts & signal handling
├── config.json                  # Configuration settings
├── requirements.txt             # Updated dependencies with RPi.GPIO + picamera2
├── README.md                    # Basic usage documentation
├── ARCHITECTURE.md              # This file - detailed architecture
├── test_camera.py               # Test script for picamera2 functionality
├── test_gpio.py                 # Test script for GPIO interrupt functionality
└── camera/
    ├── __init__.py              # Package initialization
    ├── services.py              # Core services with picamera2 + RPi.GPIO interrupts
    ├── factories/               # 🆕 Separated factory modules
    │   ├── __init__.py          # Factory package exports
    │   ├── config_loader.py     # Configuration loading with validation
    │   ├── camera_factory.py    # Camera creation with error handling
    │   ├── logger_factory.py    # Logger creation
    │   └── gpio_factory.py      # GPIO watcher creation
    └── utils/                   # 🆕 Utility modules
        ├── __init__.py          # Utils package exports
        └── logging_config.py    # Comprehensive logging setup
```




### Systemd Service Integration
```ini
[Unit]
Description=Helmet Camera Service
After=network.target

[Service]
Type=simple
User=pi
ExecStart=/usr/bin/python3 /opt/helmet_camera/helmet_camera.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Log Monitoring
```bash
# View real-time logs
journalctl -u helmet-camera -f

# View specific date logs
journalctl -u helmet-camera --since "2025-01-25"

# View file logs
tail -f ~/helmet_camera_logs/helmet_camera_20250125.log
```

## ⚡ Hardware Interrupt Architecture

### Event-Driven Design
The system now uses **hardware interrupts** instead of polling:

- **Rising Edge Detection**: Photo capture triggered immediately on GPIO HIGH
- **Falling Edge Detection**: Cancels WiFi timer and resets state  
- **Timer-Based WiFi**: Automatic WiFi scan after prolonged HIGH signal
- **Zero CPU Polling**: Main loop only runs heartbeat every 10 minutes

### Interrupt Handling Flow
```
GPIO Rising Edge → Hardware Interrupt → Photo Capture + WiFi Timer Start
                      ↓
GPIO Falling Edge → Hardware Interrupt → Cancel WiFi Timer + Reset State
                      ↓
Timer Expires → WiFi Scan Thread → Network Connection Attempt
```

### Performance Benefits
- **Ultra-Low CPU Usage**: No continuous GPIO polling
- **Instant Response**: Hardware-level trigger detection
- **Battery Efficient**: CPU sleeps between events
- **Reliable Debouncing**: Built-in 50ms hardware debounce

## 📸 Modern Camera Implementation

### Picamera2 Integration
The system uses **picamera2** for optimal camera performance:

- **Native Python API**: Direct camera control without subprocess overhead
- **Fast Capture**: Sub-second photo capture times
- **Full HD Resolution**: 1920x1080 default resolution with configurable options
- **Memory Efficient**: Proper resource management with automatic cleanup
- **Error Recovery**: Automatic camera reinitialization on failures

### Camera Features
- **Auto-Initialization**: Camera starts and warms up during application startup
- **File Validation**: Checks photo file size to ensure successful capture
- **Context Manager Support**: Proper resource cleanup using `with` statements
- **Thread-Safe**: Safe to call from interrupt handlers
- **Configurable Quality**: Easy to adjust resolution and compression settings

### Capture Process
```
GPIO Interrupt → Background Thread → Camera.capture() → File Validation → Logging
```

## 🔧 Enhanced Main Application

### Signal Handling
Graceful shutdown on SIGINT and SIGTERM signals with proper GPIO cleanup

### Error Recovery
- Comprehensive exception handling
- Graceful degradation when components fail
- Automatic GPIO cleanup on exit
- Context manager support for resource management

### Monitoring
- Heartbeat logging every 10 minutes
- GPIO state monitoring
- Thread-safe callback execution
- Resource usage tracking

