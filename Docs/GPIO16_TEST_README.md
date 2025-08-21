# GPIO 16 Trigger Test Programs

Test programs for verifying GPIO 16 photo capture trigger functionality.

## Test Programs Available

### 1. `quick_test_gpio16.py` - Simple Quick Test
**Purpose**: Fast verification that GPIO 16 triggering works
**Duration**: Continuous (until Ctrl+C)
**Features**:
- Real-time GPIO state display
- 5-second interval photo trigger simulation
- Simple visual feedback
- Capture counting

**Usage**:
```bash
python3 quick_test_gpio16.py
```

### 2. `test_gpio16_trigger.py` - Comprehensive Test Suite
**Purpose**: Full featured testing with multiple options
**Features**:
- Interactive menu system
- Timed tests (60s, 5min, custom)
- Detailed logging
- State monitoring
- Statistics reporting

**Usage**:
```bash
python3 test_gpio16_trigger.py
```

## Hardware Setup

### Required Connections:
```
Raspberry Pi GPIO:
- Pin 16 (GPIO 16): Connect to switch/jumper wire
- GND: Connect to other side of switch/jumper wire
```

### Simple Test Setup:
1. **Jumper Wire Method**: Use a male-to-male jumper wire
   - One end to GPIO 16 (physical pin 36)
   - Other end to any GND pin (physical pins 6, 9, 14, 20, 25, 30, 34, 39)

2. **Button/Switch Method**: Connect a momentary or toggle switch
   - One terminal to GPIO 16
   - Other terminal to GND

### GPIO Pin Reference:
```
GPIO 16 = Physical Pin 36
GND pins = Physical pins 6, 9, 14, 20, 25, 30, 34, 39
```

## Test Behavior

### Expected Behavior:
- **GPIO 16 HIGH (default)**: No photo triggers
- **GPIO 16 LOW (connected to GND)**: Photo trigger every 5 seconds
- **Switching from HIGH to LOW**: Immediate first trigger, then 5-second intervals
- **Switching from LOW to HIGH**: Triggering stops immediately

### Visual Indicators:
- 🟢 **HIGH (idle)**: Pin not triggered, no photos
- 🔴 **LOW (triggered)**: Pin triggered, capturing photos every 5s
- 📸 **Photo trigger**: Simulated capture event
- ⏱️ **Countdown**: Time until next photo (when triggered)

## Running the Tests

### Quick Test (Immediate):
```bash
cd Master
python3 quick_test_gpio16.py
```
**Output Example**:
```
🔌 Quick GPIO 16 Trigger Test
===================================
📌 Testing GPIO pin 16 with pull-up resistor
🔧 Connect pin 16 to GND to trigger
📸 Will show capture trigger every 5 seconds when LOW
⏹️  Press Ctrl+C to stop

GPIO 16: 🟢 HIGH (idle) - Captures: 0
```

### Comprehensive Test:
```bash
cd Master
python3 test_gpio16_trigger.py
```
**Menu Options**:
1. Quick state check (10 readings)
2. Interactive test (60 seconds)
3. Extended test (5 minutes)
4. Custom duration test

## Test Scenarios

### Scenario 1: Basic Functionality
1. Run quick test: `python3 quick_test_gpio16.py`
2. Observe GPIO 16 shows HIGH (idle)
3. Connect GPIO 16 to GND
4. Observe immediate first photo trigger
5. Observe subsequent triggers every 5 seconds
6. Disconnect from GND
7. Observe triggering stops

### Scenario 2: Timing Verification
1. Run comprehensive test with 60-second duration
2. Connect GPIO 16 to GND at start
3. Count triggers: Should get ~12 triggers in 60 seconds
4. Verify 5-second intervals between triggers

### Scenario 3: Start/Stop Testing
1. Run test program
2. Connect and disconnect GPIO 16 multiple times
3. Verify triggering starts/stops immediately
4. Verify no spurious triggers when disconnected

## Troubleshooting

### No Triggers When Connected:
1. **Check wiring**: Ensure solid connection GPIO 16 to GND
2. **Verify pin**: GPIO 16 = Physical pin 36
3. **Check logs**: Look for "GPIO 16 is LOW" messages
4. **Test continuity**: Use multimeter to verify connection

### Continuous Triggering:
1. **Check connection**: May have loose/intermittent connection
2. **Verify pull-up**: Should show HIGH when disconnected
3. **Clean connections**: Ensure good contact points

### Wrong Pin:
- The test programs automatically read from `master_config.json`
- Current config shows pin 16 (updated from pin 20)
- Tests will use whatever pin is configured

## Integration with Master System

### Configuration Verification:
```json
"capture_triggers": {
  "gpio_pin20_enabled": true,
  "gpio_pin20_pin": 16
}
```

### Real System Testing:
1. Start master system: `python3 run_master.py`
2. Connect GPIO 16 to GND
3. Watch logs for actual photo captures every 5 seconds
4. Listen for buzzer beeps after each photo

## Test Results Interpretation

### Successful Test Results:
- GPIO state changes immediately when connected/disconnected
- Triggers occur exactly every 5 seconds when LOW
- No triggers when HIGH
- Clean start/stop behavior

### Failed Test Indicators:
- No state changes when connecting to GND
- Irregular timing between triggers
- Triggers when pin should be HIGH
- GPIO errors or exceptions

## Hardware Verification Commands

### Check GPIO State Manually:
```bash
# Read GPIO 16 state
echo 16 > /sys/class/gpio/export
cat /sys/class/gpio/gpio16/value
echo 16 > /sys/class/gpio/unexport
```

### Monitor with raspi-gpio:
```bash
# Show GPIO 16 status
raspi-gpio get 16
```

This test suite ensures GPIO 16 trigger functionality works correctly before deploying to the full Master helmet system. 