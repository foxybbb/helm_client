# Test Suite Organization

This directory contains all test files organized by system component.

## 📁 Directory Structure

```
tests/
├── master/          # Master board tests
├── slave/           # Slave board tests
└── README.md        # This file
```

## 🔧 Master Board Tests (`tests/master/`)

### GPIO & Hardware Tests
- **`test_gpio_17.py`** - Test GPIO 17 functionality
- **`quick_test_gpio16.py`** - Quick GPIO 16 trigger test
- **`test_gpio16_trigger.py`** - Comprehensive GPIO 16 test suite
- **`test_buzzer_gpio20.py`** - GPIO trigger and buzzer tests

### IMU Sensor Tests
- **`test_imu_simple.py`** - Simple IMU sensor verification
- **`debug_imu_trigger.py`** - Comprehensive IMU debug suite
- **`debug_imu_integration.py`** - IMU integration with Master system
- **`bno055_test.py`** - BNO055 IMU sensor specific tests

### System Integration Tests
- **`test_master_gpio.py`** - Master system GPIO integration
- **`debug_gpio_startup.py`** - GPIO startup debugging
- **`test_oled_display.py`** - OLED display functionality
- **`test_mqtt_connection.py`** - MQTT broker connection test
- **`test_mqtt_connection_root.py`** - Root-level MQTT test

## 📷 Slave Board Tests (`tests/slave/`)

### Camera Tests
- **`test_camera.py`** - Slave camera functionality
- **`test_camera_root.py`** - Root-level camera test

### GPIO Tests
- **`test_gpio.py`** - Slave GPIO functionality
- **`test_gpio_root.py`** - Root-level GPIO test

## 🚀 Quick Start

### Test Master Board:
```bash
# Quick GPIO test
cd tests/master
python3 quick_test_gpio16.py

# IMU sensor test
python3 test_imu_simple.py

# OLED display test
python3 test_oled_display.py
```

### Test Slave Board:
```bash
# Camera test
cd tests/slave
python3 test_camera.py

# GPIO test
python3 test_gpio.py
```

## 🔍 Debug Tools

### Master Debug Suite:
```bash
cd tests/master

# GPIO debugging
python3 debug_gpio_startup.py

# IMU debugging (interactive menu)
python3 debug_imu_trigger.py

# System integration
python3 debug_imu_integration.py
```

## 📋 Test Categories

### **Hardware Tests**
- GPIO pin functionality
- Camera operation
- IMU sensor communication
- OLED display output
- Buzzer operation

### **Integration Tests**
- MQTT communication
- Master-Slave coordination
- Trigger system integration
- System startup sequence

### **Debug Tools**
- Interactive debugging suites
- Comprehensive diagnostics
- Real-time monitoring
- Configuration validation

## ⚙️ Configuration

Tests use configuration files from their respective directories:
- **Master tests**: Use `Master/master_config.json`
- **Slave tests**: Use `Slave/slave_config.json`

## 🛠️ Prerequisites

### For Master Tests:
```bash
# IMU sensor libraries
pip3 install adafruit-circuitpython-bno055

# OLED display libraries  
pip3 install adafruit-circuitpython-ssd1306 pillow

# Camera libraries
pip3 install picamera2

# MQTT libraries
pip3 install paho-mqtt
```

### For Slave Tests:
```bash
# Camera libraries
pip3 install picamera2

# GPIO libraries (usually pre-installed)
python3 -c "import RPi.GPIO"
```

## 📊 Test Results

### Expected Outputs:
- **✅ Pass**: Test completed successfully
- **⚠️ Warning**: Test completed with warnings
- **❌ Fail**: Test failed, check hardware/configuration

### Common Issues:
- **Permission errors**: Run with `sudo` for GPIO access
- **Library missing**: Install required dependencies
- **Hardware not connected**: Check wiring and connections

## 🔗 Related Documentation

- **Master Documentation**: `Docs/` folder
- **GPIO Setup**: `Docs/GPIO16_TEST_README.md`
- **IMU Setup**: `Docs/IMU_DEBUG_README.md`
- **OLED Setup**: `Docs/OLED_DISPLAY_SETUP.md`

This organized structure makes it easy to find and run the appropriate tests for each system component!
