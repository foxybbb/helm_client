# Master Board Test Programs

This folder contains test programs and documentation for the Master board GPIO trigger and buzzer functionality.

## 📁 Test Programs

### GPIO 16 Trigger Tests
- **`quick_test_gpio16.py`** - Simple quick test for GPIO 16 functionality
- **`test_gpio16_trigger.py`** - Comprehensive test suite with multiple options

### Combined Tests  
- **`test_buzzer_gpio20.py`** - Tests both GPIO trigger and buzzer functionality

### IMU Trigger Tests
- **`test_imu_simple.py`** - Simple IMU sensor verification (10s)
- **`debug_imu_trigger.py`** - Comprehensive IMU debug suite with menu
- **`debug_imu_integration.py`** - Test IMU integration with Master system

## 📚 Documentation

- **`GPIO16_TEST_README.md`** - Complete documentation for GPIO 16 testing
- **`GPIO20_BUZZER_README.md`** - Implementation details for GPIO triggers and buzzer
- **`IMU_DEBUG_README.md`** - Comprehensive IMU troubleshooting and debug guide

## 🚀 Quick Start

### Test GPIO 16 Trigger (Simple):
```bash
cd tests
python3 quick_test_gpio16.py
```

### Test GPIO 16 Trigger (Full Suite):
```bash
cd tests  
python3 test_gpio16_trigger.py
```

### Test Both GPIO and Buzzer:
```bash
cd tests
python3 test_buzzer_gpio20.py
```

### Test IMU Sensor (Quick):
```bash
cd tests
python3 test_imu_simple.py
```

### Debug IMU Triggers (Comprehensive):
```bash
cd tests
python3 debug_imu_trigger.py
```

## 🔧 Hardware Setup

**GPIO 16 Trigger:**
- Connect GPIO 16 (Physical Pin 36) to GND to trigger
- System captures photos every 5 seconds when LOW

**Buzzer (Optional):**
- Connect passive buzzer to GPIO 18 and GND
- Provides audio feedback for system events

## ⚙️ Configuration

Current configuration (in `../master_config.json`):
```json
{
  "buzzer_pin": 18,
  "capture_triggers": {
    "gpio_pin20_enabled": true,
    "gpio_pin20_pin": 16
  }
}
```

## 🔍 Test Results

All test programs will show:
- Real-time GPIO state monitoring
- Photo capture simulation timing
- Hardware connection verification
- System integration validation

## 📋 Before Running Master System

1. **Test GPIO 16**: Run `quick_test_gpio16.py` to verify trigger works
2. **Check Hardware**: Ensure solid connections
3. **Verify Config**: Confirm pin 16 is configured correctly
4. **Test Buzzer**: Optional audio feedback verification

## 🛠️ Troubleshooting

- **No triggers**: Check GPIO 16 to GND connection
- **Wrong pin**: GPIO 16 = Physical Pin 36  
- **Permission errors**: Run with `sudo` if needed
- **Import errors**: Ensure RPi.GPIO is installed

See individual documentation files for detailed troubleshooting guides. 