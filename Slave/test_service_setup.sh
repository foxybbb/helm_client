#!/bin/bash

# Service Setup Validation Test
# Tests the service configuration before deployment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=============================================="
echo "Helmet Camera Slave Service Setup Validation"
echo "=============================================="
echo

# Test functions
test_passed() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
}

test_failed() {
    echo -e "${RED}✗ FAIL${NC}: $1"
}

test_warning() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
}

test_info() {
    echo -e "${BLUE}ℹ INFO${NC}: $1"
}

# Test 1: Check required files exist
echo "Test 1: Checking required files..."
if [ -f "helmet-camera-slave.service" ]; then
    test_passed "Service file exists"
else
    test_failed "Service file missing"
    exit 1
fi

if [ -f "install_service.sh" ] && [ -x "install_service.sh" ]; then
    test_passed "Install script exists and is executable"
else
    test_failed "Install script missing or not executable"
    exit 1
fi

if [ -f "manage_service.sh" ] && [ -x "manage_service.sh" ]; then
    test_passed "Management script exists and is executable"
else
    test_failed "Management script missing or not executable"
    exit 1
fi

if [ -f "slave_helmet_camera.py" ]; then
    test_passed "Main Python script exists"
else
    test_failed "Main Python script missing"
    exit 1
fi

if [ -f "slave_config.json" ]; then
    test_passed "Configuration file exists"
else
    test_failed "Configuration file missing"
    exit 1
fi

echo

# Test 2: Validate service file syntax
echo "Test 2: Validating service file syntax..."
if command -v systemd-analyze &> /dev/null; then
    if systemd-analyze verify helmet-camera-slave.service 2>/dev/null; then
        test_passed "Service file syntax is valid"
    else
        test_failed "Service file has syntax errors"
        systemd-analyze verify helmet-camera-slave.service
        exit 1
    fi
else
    test_warning "systemd-analyze not available, skipping syntax check"
fi

echo

# Test 3: Check Python dependencies
echo "Test 3: Checking Python dependencies..."
if [ -f "requirements.txt" ]; then
    test_passed "Requirements file exists"
    
    # Check if Python modules can be imported
    python3 -c "
import sys
missing_modules = []
required_modules = ['RPi.GPIO', 'picamera2', 'paho.mqtt.client', 'pathlib']

for module in required_modules:
    try:
        __import__(module)
        print(f'✓ {module} available')
    except ImportError:
        missing_modules.append(module)
        print(f'✗ {module} missing')

if missing_modules:
    print(f'Missing modules: {missing_modules}')
    sys.exit(1)
" 2>/dev/null && test_passed "Key Python modules available" || test_warning "Some Python modules missing (install with pip3 install -r requirements.txt)"
else
    test_warning "Requirements file missing"
fi

echo

# Test 4: Check configuration file
echo "Test 4: Validating configuration file..."
if python3 -c "
import json
try:
    with open('slave_config.json', 'r') as f:
        config = json.load(f)
    required_keys = ['client_id', 'mqtt', 'photo_base_dir']
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        print(f'Missing config keys: {missing_keys}')
        exit(1)
    print('Configuration file is valid JSON with required keys')
except Exception as e:
    print(f'Configuration error: {e}')
    exit(1)
" 2>/dev/null; then
    test_passed "Configuration file is valid"
else
    test_failed "Configuration file has issues"
    exit 1
fi

echo

# Test 5: Check system requirements
echo "Test 5: Checking system requirements..."

# Check systemctl
if command -v systemctl &> /dev/null; then
    test_passed "systemctl available"
else
    test_failed "systemctl not found - systemd required"
    exit 1
fi

# Check Python3
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
    test_passed "Python3 available (version $python_version)"
else
    test_failed "Python3 not found"
    exit 1
fi

# Check user permissions
if groups | grep -q "video\|gpio"; then
    test_passed "User has video/gpio group access"
else
    test_warning "User may need video/gpio group access (installer will fix this)"
fi

echo

# Test 6: Check service file content
echo "Test 6: Checking service file configuration..."

# Check if service file points to correct paths
if grep -q "/home/pi/helmet_camera/Slave/slave_helmet_camera.py" helmet-camera-slave.service; then
    test_passed "Service points to correct Python script path"
else
    test_warning "Service may need path adjustment for your system"
fi

if grep -q "User=pi" helmet-camera-slave.service; then
    if id "pi" &>/dev/null; then
        test_passed "Service configured for pi user (user exists)"
    else
        test_warning "Service configured for pi user (user doesn't exist - installer will adapt)"
    fi
fi

echo

# Test 7: Simulate service installation (dry run)
echo "Test 7: Service installation simulation..."

# Check if we can write to systemd directory (sudo required)
if sudo test -w /etc/systemd/system/; then
    test_passed "Can write to systemd directory"
else
    test_failed "Cannot write to systemd directory"
    exit 1
fi

# Check if service already exists
if systemctl list-unit-files | grep -q "helmet-camera-slave"; then
    test_warning "Service already installed"
else
    test_passed "Service not yet installed (ready for installation)"
fi

echo

# Summary
echo "=============================================="
echo "VALIDATION SUMMARY"
echo "=============================================="
echo

test_info "All basic validation tests passed!"
echo
echo "✅ Ready for installation with: ./install_service.sh"
echo "📋 Service management with: ./manage_service.sh"
echo "📖 Documentation available in: SERVICE_SETUP.md"
echo

echo "Next steps:"
echo "1. Run: ./install_service.sh"
echo "2. Check status: ./manage_service.sh status"
echo "3. View logs: ./manage_service.sh logs"
echo

echo "The service will:"
echo "• Start automatically on boot"
echo "• Restart automatically if it crashes"
echo "• Run in the background"
echo "• Log to systemd journal"
echo "• Connect to MQTT broker and wait for commands"

echo
test_info "Validation complete! 🎯" 