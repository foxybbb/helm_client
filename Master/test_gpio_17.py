import RPi.GPIO as GPIO
import time

# Set GPIO mode
GPIO.setmode(GPIO.BCM)

# Use GPIO 17
GPIO_PIN = 17

# Setup GPIO pin as output
GPIO.setup(GPIO_PIN, GPIO.OUT)

try:
    while True:
        # Set pin HIGH (impulse start)
        GPIO.output(GPIO_PIN, GPIO.HIGH)
        time.sleep(0.5)  # Pulse width: 0.5 sec

        # Set pin LOW (impulse end)
        GPIO.output(GPIO_PIN, GPIO.LOW)
        time.sleep(5)  # Wait before next impulse

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()
