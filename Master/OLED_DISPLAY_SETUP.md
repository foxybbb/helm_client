# OLED Display Setup Guide

## Overview
The Master Helmet System now includes support for a **SSD1306 128x32 OLED display** that shows real-time system statistics and status information at I2C address 0x3C.

## Hardware Requirements
- **SSD1306 OLED Display** (128x32 pixels)
- **I2C Interface** (4 pins: VCC, GND, SDA, SCL)
- **I2C Address**: 0x3C (default)

## Wiring Connections

| SSD1306 OLED | Raspberry Pi | Pin Number |
|--------------|--------------|------------|
| VCC          | 3.3V         | Pin 1      |
| GND          | Ground       | Pin 6      |
| SDA          | GPIO 2       | Pin 3      |
| SCL          | GPIO 3       | Pin 5      |

## Software Setup

### 1. Enable I2C on Raspberry Pi
```bash
sudo raspi-config
# Navigate to: Interface Options > I2C > Enable
# Reboot after enabling
sudo reboot
```

### 2. Install Required Libraries
```bash
# Install OLED display libraries
sudo pip3 install adafruit-circuitpython-ssd1306 pillow

# Or using pip without sudo
pip3 install adafruit-circuitpython-ssd1306 pillow
```

### 3. Verify I2C Connection
```bash
# Check if I2C device is detected
sudo i2cdetect -y 1

# Should show '3c' at address 0x3C if display is connected correctly
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:          -- -- -- -- -- -- -- -- -- -- -- -- --
# 10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 30: -- -- -- -- -- -- -- -- -- -- -- -- 3c -- -- --
```

### 4. Test Display
```bash
cd Master
python3 test_oled_display.py
```

## Display Features

### 📊 **Screen 1: System Status**
- Master system status (READY/STOP)
- MQTT connection status (ON/OFF)
- IMU sensor status (ON/OFF)
- Connected slaves count (online/total)

### 📈 **Screen 2: Statistics**
- Total commands sent
- Success rate percentage
- Master camera captures (CAM1)
- Failed responses count
- Timeout count

### ⏰ **Screen 3: Session Info**
- Current session name
- Current time (HH:MM:SS)
- Current date (MM/DD)
- Pending commands count

### 📷 **Screen 4: Capture Boards Status**
- How many boards respond correctly during captures
- Overall success rate across all boards
- Master camera (CAM1) capture count
- Total captures across all boards

### 🔄 **Screen 5: IMU Trigger Status**
- IMU sensor availability and monitoring status
- Movement threshold setting (m/s²)
- Cooldown timer (30 minutes) with remaining time
- Current trigger state (IDLE/RUN)

### 🎯 **Screen 6: Trigger Overview**
- Timer trigger status (OFF/ON/RUN)
- IMU movement trigger status (OFF/ON/RUN)
- GPIO trigger status with pin number (OFF/ON/RUN)
- Web interface availability

### 🔄 **Special Displays**
- **Extended Startup Sequence**: Multi-screen startup with system initialization steps
- **Capture Status**: Shows during individual photo capture operations
- **Sequence Progress**: Shows progress during multi-photo sequences
- **Error Messages**: Displays system errors and warnings
- **Shutdown Message**: Shows during system shutdown

## Display Behavior

### Auto-Cycling
- **Update Interval**: Every 3 seconds
- **Screen Rotation**: Cycles through 6 main screens automatically
- **Background Updates**: Runs in separate thread, non-blocking

### Event-Driven Updates
- **Capture Operations**: Temporarily shows capture status
- **Error Conditions**: Immediately displays error messages
- **System Events**: Shows startup/shutdown messages

## Configuration

### Custom I2C Address
If your display uses a different I2C address, modify in `camera/services.py`:
```python
# Default address is 0x3C
self.oled_display = MasterOLEDDisplay(i2c_address=0x3D)  # Custom address
```

### Update Timing
Modify display update intervals in `camera/services.py`:
```python
self.update_interval = 2.0  # Update every 2 seconds (default)
```

## Troubleshooting

### Display Not Working
1. **Check I2C Enable**: `sudo raspi-config` → Interface Options → I2C → Enable
2. **Check Connections**: Verify wiring matches the table above
3. **Check I2C Address**: Run `sudo i2cdetect -y 1` to confirm 0x3C
4. **Check Libraries**: Run the test script to verify installation

### Common Issues

#### Error: "No module named 'adafruit_ssd1306'"
```bash
# Install missing libraries
sudo pip3 install adafruit-circuitpython-ssd1306 pillow
```

#### Error: "Remote I/O error"
- Check physical connections
- Verify I2C is enabled
- Try different I2C address (0x3D)

#### Display Shows Garbled Text
- Check power supply (3.3V, not 5V)
- Verify SDA/SCL connections
- Check for loose connections

### Test Commands
```bash
# Test I2C detection
sudo i2cdetect -y 1

# Test display functionality
cd Master
python3 test_oled_display.py

# Check system logs for display errors
journalctl -f | grep -i oled
```

## Web Interface Integration

The OLED display status is also shown in the web interface at `http://master-ip:8081`:
- **Display Available**: Green indicator if OLED is working
- **Display Not Available**: Yellow warning if OLED is not detected

## Performance Impact

- **CPU Usage**: Minimal (~1% for display updates)
- **Memory Usage**: <10MB for display operations
- **I2C Bus**: Shared with IMU sensor (no conflicts)
- **Update Rate**: Limited to prevent flickering

## Advanced Usage

### Custom Display Content
You can extend the display functionality by adding new screen types in the `MasterOLEDDisplay` class.

### Integration with Other Systems
The display service can be extended to show data from external sources or custom monitoring systems.

## Support

If you encounter issues with the OLED display:
1. Run the test script: `python3 test_oled_display.py`
2. Check the troubleshooting section above
3. Verify all hardware connections
4. Check system logs for error messages

The OLED display enhances the master system by providing immediate visual feedback without requiring a separate monitor or web interface access. 