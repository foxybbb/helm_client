# IMU Trigger Debug Tools Summary

## 🔍 **Debug Tools Created**

### **3 Comprehensive Debug Scripts**

1. **`tests/test_imu_simple.py`** - Quick IMU Verification
   - Basic sensor connectivity test
   - Temperature and calibration readings
   - 10-second acceleration monitoring
   - **Usage**: `python3 test_imu_simple.py`

2. **`tests/debug_imu_trigger.py`** - Full Debug Suite
   - Interactive menu with 6 debug options
   - Configuration analysis
   - Movement detection testing
   - Continuous monitoring simulation
   - Calibration helper
   - Debug report generation
   - **Usage**: `python3 debug_imu_trigger.py`

3. **`tests/debug_imu_integration.py`** - System Integration Test
   - Tests IMU with Master system components
   - AutoCaptureManager integration testing
   - Mock photo capture simulation
   - Real-time trigger monitoring
   - **Usage**: `python3 debug_imu_integration.py`

## 🎯 **Key Debug Features**

### **Hardware Verification**
- ✅ **I2C Connection**: Tests communication with BNO055 sensor
- ✅ **Library Check**: Verifies required libraries are installed
- ✅ **Wiring Validation**: Checks if sensor responds correctly
- ✅ **Temperature Reading**: Confirms sensor is operational

### **Calibration Support**
- 🎯 **Real-time Status**: Shows calibration progress for all 4 systems
- 🎯 **Visual Feedback**: Progress bars for SYS/GYRO/ACCEL/MAG
- 🎯 **Calibration Guide**: Step-by-step instructions
- 🎯 **Target Validation**: Confirms when fully calibrated (3/3)

### **Movement Detection Testing**
- 📊 **Threshold Testing**: Test different sensitivity levels
- 📊 **Real-time Monitoring**: Live acceleration change tracking
- 📊 **Trigger Simulation**: Test what movements cause triggers
- 📊 **Cooldown Verification**: 30-minute cooldown testing

### **Integration Testing**
- 🔗 **AutoCaptureManager**: Tests with actual Master system components
- 🔗 **Photo Simulation**: Mock capture when triggers fire
- 🔗 **Configuration Loading**: Uses real master_config.json settings
- 🔗 **Logging Integration**: Full debug logging output

## 📋 **Debug Menu Options**

### **Main Debug Suite Menu** (`debug_imu_trigger.py`)
```
📋 Debug Menu:
1. Test basic IMU readings (10s)          - Hardware verification
2. Test movement detection (30s)          - Trigger algorithm testing  
3. Test continuous monitoring (60s)       - Real system simulation
4. Calibration helper                     - Interactive calibration
5. Save debug report                      - Generate JSON report
6. Exit
```

### **Integration Test Menu** (`debug_imu_integration.py`)
```
📋 Debug Menu:
1. Test IMU integration with Master system  - Full system test
2. Simulate IMU trigger behavior            - Algorithm simulation
3. Run both tests                          - Complete verification
4. Exit
```

## 🔧 **Troubleshooting Capabilities**

### **Common Issues Detected**
- ❌ **Missing Libraries**: `pip3 install adafruit-circuitpython-bno055`
- ❌ **I2C Not Enabled**: `sudo raspi-config` → Interface Options → I2C
- ❌ **Wiring Issues**: SDA/SCL connection problems
- ❌ **Calibration Problems**: Sensor not properly calibrated
- ❌ **Threshold Issues**: Sensitivity too high/low
- ❌ **Cooldown Problems**: Timer not working correctly

### **Debug Output Examples**
```bash
# Hardware Test
✓ IMU libraries available
✓ IMU sensor connected  
✓ Temperature: 28°C
✓ Calibration: SYS:3 GYRO:3 ACCEL:3 MAG:3

# Movement Detection
⏱️  15.3s | Accel: 10.5 | Change: 2.3 | Max: 4.7 | 🔥 TRIGGER #2!

# System Integration
🎯 [14:32:15] MOVEMENT TRIGGER #1!
     - Acceleration change: 3.45 m/s²
     - Would capture photo now
     - Next trigger possible in 30.0 minutes
```

## ⚙️ **Configuration Testing**

### **Current IMU Settings** (master_config.json)
```json
{
  "capture_triggers": {
    "imu_movement_enabled": false,           // ← Can be tested
    "imu_movement_threshold": 2.0,          // ← Adjustable
    "imu_movement_cooldown_seconds": 1800.0 // ← 30 minutes
  }
}
```

### **Debug Testing Validates**
- ✅ Configuration loading and parsing
- ✅ Threshold sensitivity (1.0 - 5.0 m/s²)
- ✅ Cooldown timer (30 minutes = 1800 seconds)
- ✅ Enable/disable functionality
- ✅ Integration with AutoCaptureManager

## 📊 **Generated Debug Reports**

### **JSON Debug Report** (`imu_debug_report_YYYYMMDD_HHMMSS.json`)
Contains:
- **Timestamp** and configuration snapshot
- **Sensor availability** and status
- **Debug data** from test sessions
- **Current readings** (temperature, calibration, acceleration)
- **Trigger history** and timing data

## 🚀 **Quick Start Guide**

### **Step 1: Basic Hardware Test**
```bash
cd Master/tests
python3 test_imu_simple.py
```
**Expected**: Sensor connects and shows acceleration data

### **Step 2: Movement Sensitivity Test**
```bash
python3 debug_imu_trigger.py
# Select option 2
# Move sensor sharply to test triggers
```
**Expected**: Sharp movements trigger, gentle movements don't

### **Step 3: System Integration Test**
```bash
python3 debug_imu_integration.py
# Select option 1
# Test with real Master system components
```
**Expected**: Mock photo captures when movement detected

### **Step 4: Enable in Production**
```bash
# Edit master_config.json
"imu_movement_enabled": true

# Start Master system
cd Master
sudo python3 run_master.py
```

## 📱 **OLED Display Integration**

The debug tools work alongside the enhanced OLED display:

**Screen 5: IMU Trigger Status**
```
IMU TRIGGER
STATUS: ON (RUN)
THRESH: 2.0 m/s²
COOLDOWN: 0/30min
```

This shows real-time IMU status that can be compared with debug tool output.

## 🏆 **Benefits of Debug Suite**

1. **Hardware Validation**: Quickly verify IMU sensor is working
2. **Sensitivity Tuning**: Test different threshold values easily  
3. **Calibration Assistance**: Interactive calibration with visual feedback
4. **Integration Testing**: Verify IMU works with Master system
5. **Troubleshooting**: Comprehensive error detection and solutions
6. **Documentation**: Detailed guides for common issues
7. **Reporting**: Detailed debug reports for analysis

The IMU debug suite provides everything needed to successfully deploy and troubleshoot IMU trigger functionality! 