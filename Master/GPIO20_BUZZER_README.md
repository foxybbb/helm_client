# GPIO 20 Continuous Triggering and Passive Buzzer Implementation

This document describes the implementation of the GPIO 20 continuous photo triggering and passive buzzer functionality for the Master board.

## Features Implemented

### 1. GPIO 20 Continuous Photo Triggering

**Previous Behavior:** GPIO 20 triggered photos on falling edge (when button was pressed)

**New Behavior:** GPIO 20 triggers photos every 5 seconds while the pin is LOW

#### How it Works:
- Uses pull-up resistor configuration (HIGH by default)
- When GPIO 20 is connected to GND (LOW), the system captures photos every 5 seconds
- When GPIO 20 is disconnected (HIGH), no photos are taken
- Eliminates the need for repeated button presses

#### Configuration:
```json
"capture_triggers": {
  "gpio_pin20_enabled": true,
  "gpio_pin20_pin": 20
}
```

### 2. Passive Buzzer System Feedback

**New Feature:** Comprehensive audio feedback system using a passive buzzer

#### Buzzer Events:
1. **System Startup**: Three-tone sequence (low-high-medium)
2. **Photo Finished**: Single high-pitched beep after each photo capture
3. **All Photos Finished**: Three rapid high-pitched beeps after photo sequences

#### Hardware Setup:
- **Default Pin**: GPIO 18 (configurable)
- **Type**: Passive buzzer (requires PWM signal)
- **Connection**: Buzzer positive to GPIO pin, negative to GND

#### Configuration:
```json
{
  "buzzer_pin": 18
}
```

## Implementation Details

### PassiveBuzzer Class

Located in `master_helmet_system.py`, the `PassiveBuzzer` class provides:

```python
class PassiveBuzzer:
    def __init__(self, config)           # Initialize with GPIO pin
    def beep(frequency, duration, duty)  # Generate custom beep
    def startup_sequence()               # System startup sound
    def photo_finished_beep()           # Single photo completion
    def all_photos_finished_beep()      # Photo sequence completion
    def cleanup()                       # GPIO cleanup
```

### Integration Points

1. **System Startup**: Plays startup sequence in `MasterHelmetSystem.start()`
2. **Photo Capture**: Plays beep in `capture_single_photo()` method
3. **Photo Sequences**: Plays completion sequence in `capture_photo_sequence()` method
4. **Web Interface**: Modified to use new sequence method with beep

### GPIO 20 Monitoring Changes

The `start_gpio20_monitoring()` method in `AutoCaptureManager` was modified:

- **Old**: Edge detection with debounce
- **New**: Continuous state monitoring with 5-second intervals
- **Polling Rate**: 100ms (10Hz) for responsive detection
- **Trigger Logic**: Only triggers when pin is LOW and 5 seconds have elapsed

## Configuration File Updates

Updated `master_config.json`:

```json
{
  "buzzer_pin": 18,
  "capture_triggers": {
    "gpio_pin20_enabled": true,
    "gpio_pin20_pin": 20
  }
}
```

## Testing

### Test Script: `test_buzzer_gpio20.py`

Provides comprehensive testing of both features:

```bash
cd Master
python3 test_buzzer_gpio20.py
```

**Test Functions:**
1. `test_buzzer()` - Tests all buzzer sequences
2. `test_gpio20_continuous()` - Simulates GPIO 20 monitoring

### Manual Testing

#### Buzzer Test:
1. Connect passive buzzer to GPIO 18 and GND
2. Run test script
3. Listen for startup, photo finished, and sequence completion sounds

#### GPIO 20 Test:
1. Connect a switch or jumper wire between GPIO 20 and GND
2. Enable GPIO 20 in config: `"gpio_pin20_enabled": true`
3. Start master system
4. Connect GPIO 20 to GND - photos should trigger every 5 seconds
5. Disconnect GPIO 20 - photo triggering should stop

## Usage Examples

### Enable GPIO 20 Continuous Triggering:
```json
"capture_triggers": {
  "gpio_pin20_enabled": true
}
```

### Hardware Setup:
```
Raspberry Pi GPIO:
- Pin 18: Buzzer positive (+)
- Pin 20: Switch/trigger input
- GND: Buzzer negative (-) and switch common
```

### Web Interface:
- Multi-photo sequences now automatically play completion beeps
- Single photos play individual completion beeps
- All audio feedback is threaded and non-blocking

## Troubleshooting

### No Buzzer Sound:
1. Check wiring: GPIO 18 → Buzzer(+), GND → Buzzer(-)
2. Verify buzzer type: Must be passive buzzer (requires PWM)
3. Check logs for "Passive buzzer initialized" message

### GPIO 20 Not Triggering:
1. Verify pull-up configuration in logs
2. Check pin connection: GPIO 20 to GND for trigger
3. Monitor logs for "GPIO pin 20 is LOW" messages
4. Ensure `gpio_pin20_enabled: true` in config

### Audio Conflicts:
- Buzzer uses hardware PWM on GPIO 18
- Avoid using other PWM-dependent features on same pin
- If conflicts occur, change `buzzer_pin` in config

## Technical Notes

- All buzzer operations run in separate threads to avoid blocking photo capture
- GPIO 20 uses 100ms polling for balance between responsiveness and CPU usage
- Buzzer cleanup is handled automatically on system shutdown
- Web interface sequences now include automatic completion beeps

## Compatibility

- **Requires**: RPi.GPIO library with PWM support
- **Compatible**: All Raspberry Pi models with GPIO access
- **Tested**: Raspberry Pi 4B (recommended for Master board)

This implementation maintains backward compatibility while adding the requested continuous triggering and audio feedback functionality. 