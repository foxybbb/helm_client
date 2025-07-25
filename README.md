# Helmet Camera Project

A Raspberry Pi-based smart helmet camera system that captures photos based on GPIO input and manages WiFi connectivity.

## Project Structure

```
helmet_camera/
├── helmet_camera.py      # Main application entry point
├── config.json          # Configuration settings
├── requirements.txt     # Python dependencies
└── camera/
    ├── __init__.py      # Package initialization
    ├── factories.py     # Factory classes for component creation
    └── services.py      # Core service implementations
```

## Features
## Configuration

Edit `config.json` to customize:
- `gpio_pin`: GPIO pin number for trigger input
- `startup_delay`: Delay before starting main loop
- `min_high_duration`: Time (seconds) before WiFi scan triggers
- `photo_base_dir`: Base directory for photo storage
- `wifi_ssid` / `wifi_password`: Target WiFi network credentials
- `log_dir`: Directory for log files (default: `~/helmet_camera_logs`)

## Installation

1. Install dependencies: `pip install -r requirements.txt`
2. Ensure system tools are available: `iwlist`, `nmcli` (raspistill no longer needed)
3. Configure hostname format: `rpihelmet{number}` (e.g., `rpihelmet1`)
4. **Setup GPIO permissions**: `sudo usermod -a -G gpio $USER` (then logout/login)
5. **Test camera**: `python test_camera.py` (verify picamera2 works)
6. **Test GPIO interrupts**: `python test_gpio.py` (verify interrupt functionality)
7. **GPIO troubleshooting**: `python check_gpio.py` (if GPIO issues occur)

## Usage

Run the main application:
```bash
python helmet_camera.py
```

## Output Structure

Photos and logs are saved to:
```
/home/rpi/helmet-cam{N}/session_{YYYYMMDD}/
├── session_log.json
├── cam{N}_{YYYYMMDD_HHMMSS}_{index}.jpg
└── ...
```

Application logs are saved to:
```
~/helmet_camera_logs/
├── helmet_camera_{YYYYMMDD}.log
├── helmet_camera_{YYYYMMDD}.log.1
└── ...
``` 