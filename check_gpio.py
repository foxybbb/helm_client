#!/usr/bin/env python3
"""
GPIO Diagnostic Script

Checks GPIO status, permissions, and pin availability.
Run this if you're having GPIO issues.
"""

import os
import stat
import grp
import pwd
from pathlib import Path

def check_gpio_permissions():
    """Check GPIO-related permissions and groups"""
    print("=== GPIO Permission Check ===")
    
    # Check if running as root
    if os.geteuid() == 0:
        print("✅ Running as root - GPIO access should work")
    else:
        print(f"ℹ️  Running as user: {pwd.getpwuid(os.getuid()).pw_name}")
        
        # Check gpio group membership
        try:
            gpio_group = grp.getgrnam('gpio')
            user_groups = [grp.getgrgid(gid).gr_name for gid in os.getgroups()]
            
            if 'gpio' in user_groups:
                print("✅ User is in 'gpio' group")
            else:
                print("❌ User is NOT in 'gpio' group")
                print("   Fix: sudo usermod -a -G gpio $USER")
                print("   Then logout and login again")
        except KeyError:
            print("⚠️  'gpio' group not found on this system")
    
    # Check /dev/gpiomem permissions
    gpiomem_path = Path("/dev/gpiomem")
    if gpiomem_path.exists():
        stat_info = gpiomem_path.stat()
        mode = stat.filemode(stat_info.st_mode)
        print(f"ℹ️  /dev/gpiomem permissions: {mode}")
        
        if stat_info.st_mode & 0o060:  # Group read/write
            print("✅ /dev/gpiomem has group access")
        else:
            print("❌ /dev/gpiomem lacks group access")
    else:
        print("❌ /dev/gpiomem not found")
    
    print()

def check_gpio_status():
    """Check current GPIO status"""
    print("=== GPIO Status Check ===")
    
    try:
        import RPi.GPIO as GPIO
        print("✅ RPi.GPIO module imported successfully")
        
        # Try to set BCM mode
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            print("✅ GPIO.setmode(BCM) successful")
            
            # Test a safe pin (usually safe to test)
            test_pin = 17
            print(f"ℹ️  Testing GPIO pin {test_pin}...")
            
            try:
                # Clean up first
                GPIO.cleanup(test_pin)
                
                # Setup as input
                GPIO.setup(test_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                
                # Read current state
                state = GPIO.input(test_pin)
                print(f"✅ GPIO pin {test_pin} read successful, state: {state}")
                
                # Test edge detection
                try:
                    GPIO.add_event_detect(test_pin, GPIO.BOTH, bouncetime=50)
                    print(f"✅ Edge detection added to pin {test_pin}")
                    
                    GPIO.remove_event_detect(test_pin)
                    print(f"✅ Edge detection removed from pin {test_pin}")
                    
                except Exception as e:
                    print(f"❌ Edge detection failed: {e}")
                
                # Cleanup
                GPIO.cleanup(test_pin)
                print(f"✅ GPIO pin {test_pin} cleanup successful")
                
            except Exception as e:
                print(f"❌ GPIO pin {test_pin} test failed: {e}")
                
        except Exception as e:
            print(f"❌ GPIO.setmode failed: {e}")
            
    except ImportError as e:
        print(f"❌ Failed to import RPi.GPIO: {e}")
        print("   Install with: pip install RPi.GPIO")
    except Exception as e:
        print(f"❌ GPIO test failed: {e}")
    
    print()

def check_system_info():
    """Check system information"""
    print("=== System Information ===")
    
    # Check if running on Raspberry Pi
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            if 'BCM' in cpuinfo or 'Raspberry Pi' in cpuinfo:
                print("✅ Running on Raspberry Pi")
            else:
                print("⚠️  Not running on Raspberry Pi - GPIO may not work")
    except:
        print("⚠️  Could not determine if running on Raspberry Pi")
    
    # Check kernel modules
    try:
        with open('/proc/modules', 'r') as f:
            modules = f.read()
            if 'gpio' in modules.lower():
                print("✅ GPIO kernel modules loaded")
            else:
                print("⚠️  No GPIO kernel modules found")
    except:
        print("⚠️  Could not check kernel modules")
    
    print()

def main():
    """Run all diagnostic checks"""
    print("GPIO Diagnostic Tool")
    print("===================")
    print()
    
    check_system_info()
    check_gpio_permissions()
    check_gpio_status()
    
    print("=== Recommendations ===")
    print("If you see errors above:")
    print("1. Ensure you're on a Raspberry Pi")
    print("2. Add user to gpio group: sudo usermod -a -G gpio $USER")
    print("3. Logout and login again")
    print("4. Or run with sudo (not recommended for production)")
    print("5. Check hardware connections")

if __name__ == "__main__":
    main() 