#!/bin/bash

# Helmet Camera Slave Service Installation Script
# This script installs and configures the helmet camera slave as a systemd service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="helmet-camera-slave"
SERVICE_FILE="helmet-camera-slave.service"
INSTALL_DIR="/home/pi/helmet_camera"
CURRENT_DIR="$(pwd)"

# Functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    print_status "Checking system requirements..."
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should NOT be run as root"
        print_status "Run as: ./install_service.sh"
        exit 1
    fi
    
    # Check if pi user exists
    if ! id "pi" &>/dev/null; then
        print_warning "User 'pi' does not exist. Service will run as current user: $(whoami)"
        read -p "Continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Check if systemd is available
    if ! command -v systemctl &> /dev/null; then
        print_error "systemctl not found. This system doesn't use systemd."
        exit 1
    fi
    
    # Check Python3
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 not found. Please install Python3."
        exit 1
    fi
    
    print_success "System requirements check passed"
}

install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if [ -f "requirements.txt" ]; then
        pip3 install --user -r requirements.txt
        print_success "Python dependencies installed"
    else
        print_warning "requirements.txt not found, skipping dependency installation"
    fi
}

setup_directories() {
    print_status "Setting up directories..."
    
    # Create installation directory
    sudo mkdir -p "$INSTALL_DIR"
    
    # Copy files to installation directory
    print_status "Copying files to $INSTALL_DIR..."
    sudo cp -r "$CURRENT_DIR"/* "$INSTALL_DIR/Slave/"
    
    # Set permissions
    sudo chown -R pi:pi "$INSTALL_DIR"
    sudo chmod +x "$INSTALL_DIR/Slave/slave_helmet_camera.py"
    
    print_success "Directories and files set up"
}

install_service() {
    print_status "Installing systemd service..."
    
    # Update service file paths if needed
    ACTUAL_USER=$(whoami)
    SERVICE_CONTENT=$(cat "$SERVICE_FILE")
    
    # Replace pi user with actual user if different
    if [ "$ACTUAL_USER" != "pi" ]; then
        print_status "Adapting service for user: $ACTUAL_USER"
        SERVICE_CONTENT=$(echo "$SERVICE_CONTENT" | sed "s/User=pi/User=$ACTUAL_USER/g")
        SERVICE_CONTENT=$(echo "$SERVICE_CONTENT" | sed "s/Group=pi/Group=$ACTUAL_USER/g")
        SERVICE_CONTENT=$(echo "$SERVICE_CONTENT" | sed "s|/home/pi/|/home/$ACTUAL_USER/|g")
    fi
    
    # Install service file
    echo "$SERVICE_CONTENT" | sudo tee "/etc/systemd/system/$SERVICE_NAME.service" > /dev/null
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    print_success "Service installed"
}

configure_permissions() {
    print_status "Configuring permissions for camera and GPIO access..."
    
    # Add user to required groups
    ACTUAL_USER=$(whoami)
    sudo usermod -a -G video,gpio,i2c,spi "$ACTUAL_USER"
    
    # Enable camera interface
    if command -v raspi-config &> /dev/null; then
        print_status "Enabling camera interface..."
        sudo raspi-config nonint do_camera 0
    fi
    
    # Enable I2C interface  
    if command -v raspi-config &> /dev/null; then
        print_status "Enabling I2C interface..."
        sudo raspi-config nonint do_i2c 0
    fi
    
    print_success "Permissions configured"
}

enable_service() {
    print_status "Enabling and starting service..."
    
    # Enable service to start on boot
    sudo systemctl enable "$SERVICE_NAME.service"
    
    # Start service now
    sudo systemctl start "$SERVICE_NAME.service"
    
    # Check status
    sleep 2
    if sudo systemctl is-active --quiet "$SERVICE_NAME.service"; then
        print_success "Service is running successfully"
    else
        print_error "Service failed to start"
        print_status "Checking service status..."
        sudo systemctl status "$SERVICE_NAME.service" --no-pager
        exit 1
    fi
}

show_status() {
    print_status "Service Status:"
    sudo systemctl status "$SERVICE_NAME.service" --no-pager
    
    echo
    print_status "Recent logs:"
    sudo journalctl -u "$SERVICE_NAME.service" --no-pager -n 10
    
    echo
    print_status "Management commands:"
    echo "  Start service:   sudo systemctl start $SERVICE_NAME"
    echo "  Stop service:    sudo systemctl stop $SERVICE_NAME"
    echo "  Restart service: sudo systemctl restart $SERVICE_NAME"
    echo "  View logs:       sudo journalctl -u $SERVICE_NAME -f"
    echo "  Disable service: sudo systemctl disable $SERVICE_NAME"
}

main() {
    echo "============================================="
    echo "Helmet Camera Slave Service Installer"
    echo "============================================="
    echo
    
    check_requirements
    install_dependencies
    setup_directories
    install_service
    configure_permissions
    enable_service
    
    echo
    print_success "Installation completed successfully!"
    
    echo
    show_status
    
    echo
    print_warning "IMPORTANT: You may need to reboot for group permissions to take effect"
    read -p "Reboot now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Rebooting..."
        sudo reboot
    fi
}

# Handle command line arguments
case "${1:-install}" in
    "install")
        main
        ;;
    "uninstall")
        print_status "Uninstalling service..."
        sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
        sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
        sudo rm -f "/etc/systemd/system/$SERVICE_NAME.service"
        sudo systemctl daemon-reload
        print_success "Service uninstalled"
        ;;
    "status")
        show_status
        ;;
    "restart")
        print_status "Restarting service..."
        sudo systemctl restart "$SERVICE_NAME"
        show_status
        ;;
    *)
        echo "Usage: $0 [install|uninstall|status|restart]"
        echo "  install   - Install and start the service (default)"
        echo "  uninstall - Stop and remove the service"
        echo "  status    - Show service status and logs"
        echo "  restart   - Restart the service"
        exit 1
        ;;
esac 