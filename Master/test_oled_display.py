#!/usr/bin/env python3
"""
Test script for SSD1306 OLED display functionality

This script tests the OLED display without requiring the full master system.
Run this to verify your display is connected and working properly.
"""

import time
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_oled_display():
    """Test OLED display functionality"""
    try:
        # Import display libraries
        import board
        import busio
        import adafruit_ssd1306
        from PIL import Image, ImageDraw, ImageFont
        
        logger.info("OLED display libraries imported successfully")
        
        # Initialize I2C and display
        i2c = busio.I2C(board.SCL, board.SDA)
        display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, addr=0x3C)
        
        logger.info("OLED display initialized at address 0x3C")
        
        # Clear display
        display.fill(0)
        display.show()
        
        # Test basic text display
        for test_num in range(1, 4):
            logger.info(f"Running test {test_num}/3")
            
            # Create image for drawing
            image = Image.new("1", (128, 32))
            draw = ImageDraw.Draw(image)
            
            if test_num == 1:
                # Test 1: Basic text
                draw.text((0, 0), "OLED TEST 1/3", fill=255)
                draw.text((0, 10), "Basic Text", fill=255)
                draw.text((0, 20), "Display Working!", fill=255)
                
            elif test_num == 2:
                # Test 2: System info simulation
                draw.text((0, 0), "MASTER SYSTEM", fill=255)
                draw.text((0, 8), "MQTT:ON IMU:ON", fill=255)
                draw.text((0, 16), "SLAVES: 2/2", fill=255)
                draw.text((0, 24), "STATUS: READY", fill=255)
                
            elif test_num == 3:
                # Test 3: Statistics simulation
                draw.text((0, 0), "STATISTICS", fill=255)
                draw.text((0, 8), "CMD: 42", fill=255)
                draw.text((64, 8), "OK: 95%", fill=255)
                draw.text((0, 16), "CAM1: 42", fill=255)
                draw.text((64, 16), "FAIL: 2", fill=255)
                draw.text((0, 24), "TIMEOUT: 0", fill=255)
            
            # Display the image
            display.image(image)
            display.show()
            
            time.sleep(3)
        
        # Show completion message
        image = Image.new("1", (128, 32))
        draw = ImageDraw.Draw(image)
        draw.text((0, 0), "TEST COMPLETE", fill=255)
        draw.text((0, 10), "Display Working", fill=255)
        draw.text((0, 20), "Successfully!", fill=255)
        display.image(image)
        display.show()
        
        logger.info("✅ OLED display test completed successfully!")
        logger.info("Your SSD1306 display is working correctly.")
        
        time.sleep(2)
        
        # Clear display
        display.fill(0)
        display.show()
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ OLED display libraries not installed: {e}")
        logger.info("To install required libraries, run:")
        logger.info("  sudo pip3 install adafruit-circuitpython-ssd1306 pillow")
        logger.info("  or")
        logger.info("  pip3 install adafruit-circuitpython-ssd1306 pillow")
        return False
        
    except Exception as e:
        logger.error(f"❌ OLED display test failed: {e}")
        logger.info("Common issues:")
        logger.info("1. Check I2C is enabled: sudo raspi-config > Interface Options > I2C > Enable")
        logger.info("2. Check display connections:")
        logger.info("   - VCC to 3.3V")
        logger.info("   - GND to Ground")
        logger.info("   - SDA to GPIO 2 (Pin 3)")
        logger.info("   - SCL to GPIO 3 (Pin 5)")
        logger.info("3. Check I2C address: sudo i2cdetect -y 1")
        logger.info("   (Should show 3c if display is connected)")
        return False

def main():
    """Main test function"""
    print("=" * 50)
    print("SSD1306 OLED Display Test")
    print("=" * 50)
    print("Testing 128x32 OLED display at I2C address 0x3C")
    print()
    
    if test_oled_display():
        print("\n🎉 Success! Your OLED display is ready for the master system.")
    else:
        print("\n❌ Display test failed. Please check connections and libraries.")
    
    print("\nConnection Guide:")
    print("SSD1306 OLED  ->  Raspberry Pi")
    print("VCC           ->  3.3V (Pin 1)")
    print("GND           ->  Ground (Pin 6)")
    print("SDA           ->  GPIO 2 (Pin 3)")
    print("SCL           ->  GPIO 3 (Pin 5)")

if __name__ == "__main__":
    main() 