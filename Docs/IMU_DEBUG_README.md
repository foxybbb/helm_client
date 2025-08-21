# IMU Trigger Debug Tools

Comprehensive debugging tools for the BNO055 IMU sensor and movement trigger functionality.

## 🔧 Debug Tools Available

### 1. **`test_imu_simple.py`** - Basic IMU Verification
**Purpose**: Quick check if IMU sensor is working
**Duration**: ~10 seconds
**Features**:
- Tests IMU library imports
- Verifies I2C connection
- Reads temperature and calibration status
- Shows real-time acceleration data

**Usage**:
```bash
cd tests
python3 test_imu_simple.py
```

### 2. **`debug_imu_trigger.py`** - Comprehensive IMU Debug Suite
**Purpose**: Full-featured IMU trigger debugging with multiple test modes
**Features**:
- Configuration analysis
- Basic readings test (10s)
- Movement detection test (30s)
- Continuous monitoring test (60s)
- Calibration helper
- Debug report generation

**Usage**:
```bash
cd tests
python3 debug_imu_trigger.py
```

### 3. **`debug_imu_integration.py`** - Master System Integration Test
**Purpose**: Test IMU trigger integration with actual Master system components
**Features**:
- Tests IMU with AutoCaptureManager
- Simulates photo capture triggers
- Tests cooldown functionality
- Integration with Master system

**Usage**:
```bash
cd tests
python3 debug_imu_integration.py
```

## 🔍 Troubleshooting Guide

### **Issue: IMU Libraries Not Found**
```
❌ IMU libraries missing: No module named 'adafruit_bno055'
```

**Solution**:
```bash
# Install IMU libraries
pip3 install adafruit-circuitpython-bno055
pip3 install adafruit-blinka

# Or with sudo if needed
sudo pip3 install adafruit-circuitpython-bno055 adafruit-blinka
```

### **Issue: I2C Connection Failed**
```
❌ I2C connection failed: Remote I/O error
```

**Solutions**:
1. **Check I2C Enable**:
   ```bash
   sudo raspi-config
   # Interface Options → I2C → Enable
   sudo reboot
   ```

2. **Check Wiring**:
   ```
   BNO055 → Raspberry Pi
   VCC → 3.3V (Pin 1)
   GND → GND (Pin 6)
   SDA → GPIO 2 (Pin 3)
   SCL → GPIO 3 (Pin 5)
   ```

3. **Check I2C Address**:
   ```bash
   sudo i2cdetect -y 1
   # Should show device at 0x28 or 0x29
   ```

### **Issue: Sensor Not Calibrated**
```
⚠️ System not fully calibrated. Move sensor in figure-8 patterns.
```

**Solution**:
1. Run calibration helper: `python3 debug_imu_trigger.py` → Option 4
2. Follow calibration steps:
   - **Gyroscope**: Keep sensor stationary
   - **Accelerometer**: Place in 6 different orientations
   - **Magnetometer**: Move in figure-8 patterns
   - **System**: Combines all sensors (automatic)

### **Issue: No Movement Detection**
```
📊 Monitoring - No triggers detected despite movement
```

**Solutions**:
1. **Check Threshold**: Default 2.0 m/s² might be too high
   ```json
   "imu_movement_threshold": 1.5  // Lower threshold
   ```

2. **Test Movement Patterns**:
   - Sharp, quick movements work better
   - Gentle movements may not exceed threshold
   - Test with different orientations

3. **Check Calibration**: Uncalibrated sensors give poor readings

### **Issue: Too Many Triggers**
```
🔥 Multiple triggers in short time
```

**Solutions**:
1. **Increase Threshold**:
   ```json
   "imu_movement_threshold": 3.0  // Higher threshold
   ```

2. **Check Cooldown**: Should be 30 minutes (1800 seconds)
   ```json
   "imu_movement_cooldown_seconds": 1800.0
   ```

## 📊 Understanding Debug Output

### **Basic Readings Output**
```
⏱️ 5.2s | Accel: 9.81 m/s² (X:0.1 Y:0.2 Z:9.8) | Temp: 28°C | Readings: 52
```
- **Accel**: Total acceleration magnitude
- **X,Y,Z**: Individual axis readings
- **Temp**: Sensor temperature (should be ~20-40°C)
- **Readings**: Number of successful readings

### **Movement Detection Output**
```
⏱️ 15.3s | Accel: 10.5 | Change: 2.3 | Max: 4.7 | 🔥 TRIGGER #2!
```
- **Accel**: Current acceleration magnitude
- **Change**: Difference from previous reading
- **Max**: Maximum change detected so far
- **Trigger**: Indicates when threshold is exceeded

### **Calibration Status**
```
SYS:   ███░ (3/3)    GYRO:  ████ (3/3)
ACCEL: ██░░ (2/3)    MAG:   █░░░ (1/3)
```
- **█ = Calibrated**, **░ = Not calibrated**
- **Target**: All should reach 3/3 for best accuracy

## ⚙️ Configuration Parameters

### **IMU Trigger Settings** (in `../master_config.json`)
```json
{
  "capture_triggers": {
    "imu_movement_enabled": true,          // Enable IMU triggering
    "imu_movement_threshold": 2.0,         // Sensitivity (m/s²)
    "imu_movement_cooldown_seconds": 1800.0  // 30-minute cooldown
  }
}
```

### **Threshold Guidelines**
- **1.0 m/s²**: Very sensitive (small movements)
- **2.0 m/s²**: Normal sensitivity (default)
- **3.0 m/s²**: Less sensitive (larger movements)
- **5.0 m/s²**: Very insensitive (sharp movements only)

### **Cooldown Guidelines**
- **30 seconds**: Testing purposes
- **300 seconds**: 5 minutes for frequent captures
- **1800 seconds**: 30 minutes (default, prevents spam)
- **3600 seconds**: 1 hour for rare events

## 🎯 Test Scenarios

### **Scenario 1: Verify IMU Hardware**
```bash
python3 test_imu_simple.py
```
**Expected**: Sensor connects, shows temperature, acceleration changes with movement

### **Scenario 2: Test Movement Sensitivity**
```bash
python3 debug_imu_trigger.py
# Select option 2 (Movement detection test)
```
**Actions**: 
- Try gentle movements (should not trigger)
- Try sharp movements (should trigger)
- Adjust threshold if needed

### **Scenario 3: Test Real System Integration**
```bash
python3 debug_imu_integration.py
# Select option 1 (Integration test)
```
**Expected**: IMU integrates with Master system, mock photo captures triggered

### **Scenario 4: Calibrate for Accuracy**
```bash
python3 debug_imu_trigger.py
# Select option 4 (Calibration helper)
```
**Goal**: Get all calibration values to 3/3

## 📋 Debug Report Analysis

### **Generated Debug Report** (`imu_debug_report_YYYYMMDD_HHMMSS.json`)
```json
{
  "timestamp": "20241201_143215",
  "config": {
    "imu_movement_enabled": true,
    "imu_movement_threshold": 2.0,
    "imu_movement_cooldown_seconds": 1800.0
  },
  "sensor_available": true,
  "debug_data": [...],
  "current_status": {
    "temperature": 28,
    "calibration": [3, 3, 3, 3],
    "acceleration": [0.1, 0.2, 9.8]
  }
}
```

### **Key Analysis Points**:
- **sensor_available**: Should be `true`
- **temperature**: Should be 20-40°C
- **calibration**: All values should be 3
- **acceleration**: Should show ~9.8 m/s² when stationary (gravity)

## 🚀 Integration with Master System

### **Enable IMU Triggering**:
1. Edit `master_config.json`:
   ```json
   "imu_movement_enabled": true
   ```

2. Test with debug tools first
3. Start Master system:
   ```bash
   sudo python3 run_master.py
   ```

4. Watch logs for IMU messages:
   ```
   INFO - IMU movement monitoring started
   INFO - Movement detected - acceleration change: 3.2 m/s²
   INFO - Starting single photo capture - trigger: movement_trigger
   ```

### **OLED Display Integration**
The IMU status is shown on OLED Screen 5:
```
IMU TRIGGER
STATUS: ON (RUN)
THRESH: 2.0 m/s²
COOLDOWN: 0/30min
```

This comprehensive debug suite helps identify and resolve IMU trigger issues quickly! 