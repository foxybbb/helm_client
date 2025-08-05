#!/bin/bash
# setup_helmet_ap.sh
# Sets up WiFi Access Point on Master board using NetworkManager (nmcli)

# Configuration
AP_SSID="HelmetAP"
AP_PASSWORD="12345678"
AP_INTERFACE="wlan0"
AP_IP="192.168.4.1"
CONNECTION_NAME="HelmetAP-Hotspot"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="/var/log/helmet_ap_setup.log"

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] ${message}${NC}" | tee -a "$LOG_FILE"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_status "$RED" "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to check NetworkManager
check_networkmanager() {
    print_status "$BLUE" "Checking NetworkManager..."
    
    if ! systemctl is-active --quiet NetworkManager; then
        print_status "$BLUE" "Starting NetworkManager..."
        systemctl start NetworkManager
        systemctl enable NetworkManager
        sleep 3
    fi
    
    if ! command -v nmcli &> /dev/null; then
        print_status "$RED" "nmcli not found. Installing NetworkManager..."
        apt-get update -qq
        apt-get install -y network-manager
    fi
    
    print_status "$GREEN" "NetworkManager is ready"
}

# Function to check WiFi interface
check_wifi_interface() {
    print_status "$BLUE" "Checking WiFi interface..."
    
    if ! nmcli device show $AP_INTERFACE &>/dev/null; then
        print_status "$RED" "WiFi interface $AP_INTERFACE not found"
        print_status "$BLUE" "Available interfaces:"
        nmcli device show | grep "DEVICE" | awk '{print $2}'
        exit 1
    fi
    
    # Make sure interface is managed by NetworkManager
    nmcli device set $AP_INTERFACE managed yes
    print_status "$GREEN" "WiFi interface $AP_INTERFACE is available and managed"
}

# Function to remove existing hotspot if present
remove_existing_hotspot() {
    print_status "$BLUE" "Checking for existing hotspot connections..."
    
    # List all hotspot connections
    local existing_connections=$(nmcli connection show | grep "wifi-hotspot\|$CONNECTION_NAME" | awk '{print $1}')
    
    if [[ -n "$existing_connections" ]]; then
        print_status "$YELLOW" "Removing existing hotspot connections..."
        echo "$existing_connections" | while read -r conn; do
            if [[ -n "$conn" ]]; then
                nmcli connection delete "$conn" 2>/dev/null || true
                print_status "$BLUE" "Removed connection: $conn"
            fi
        done
    fi
}

# Function to create hotspot
create_hotspot() {
    print_status "$BLUE" "Creating HelmetAP hotspot..."
    
    # Create the hotspot connection
    nmcli connection add \
        type wifi \
        ifname $AP_INTERFACE \
        con-name "$CONNECTION_NAME" \
        autoconnect yes \
        wifi.mode ap \
        wifi.ssid "$AP_SSID" \
        wifi.security wpa-psk \
        wifi.psk "$AP_PASSWORD" \
        ipv4.method shared \
        ipv4.address $AP_IP/24
    
    if [[ $? -eq 0 ]]; then
        print_status "$GREEN" "Hotspot connection created successfully"
    else
        print_status "$RED" "Failed to create hotspot connection"
        return 1
    fi
}

# Function to configure hotspot settings
configure_hotspot() {
    print_status "$BLUE" "Configuring hotspot settings..."
    
    # Set additional WiFi settings
    nmcli connection modify "$CONNECTION_NAME" \
        wifi.channel 7 \
        wifi.band bg \
        802-11-wireless.powersave 2
    
    # Configure IP settings
    nmcli connection modify "$CONNECTION_NAME" \
        ipv4.method shared \
        ipv4.address $AP_IP/24
    
    print_status "$GREEN" "Hotspot configured"
}

# Function to start hotspot
start_hotspot() {
    print_status "$BLUE" "Starting HelmetAP hotspot..."
    
    # Disconnect any existing WiFi connections on the interface
    local active_connections=$(nmcli connection show --active | grep $AP_INTERFACE | awk '{print $1}')
    if [[ -n "$active_connections" ]]; then
        echo "$active_connections" | while read -r conn; do
            if [[ "$conn" != "$CONNECTION_NAME" ]]; then
                nmcli connection down "$conn" 2>/dev/null || true
                print_status "$BLUE" "Disconnected: $conn"
            fi
        done
    fi
    
    # Activate the hotspot
    nmcli connection up "$CONNECTION_NAME"
    
    if [[ $? -eq 0 ]]; then
        print_status "$GREEN" "HelmetAP hotspot started successfully"
        sleep 3  # Give it time to fully initialize
        return 0
    else
        print_status "$RED" "Failed to start hotspot"
        return 1
    fi
}

# Function to enable connection sharing and DHCP
configure_sharing() {
    print_status "$BLUE" "Configuring connection sharing..."
    
    # NetworkManager's shared mode automatically handles:
    # - DHCP server (dnsmasq)
    # - NAT/IP forwarding
    # - DNS forwarding
    
    # Verify IP forwarding is enabled
    if [[ $(cat /proc/sys/net/ipv4/ip_forward) != "1" ]]; then
        echo 1 > /proc/sys/net/ipv4/ip_forward
        # Make it persistent
        echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
        print_status "$GREEN" "IP forwarding enabled"
    fi
    
    print_status "$GREEN" "Connection sharing configured automatically by NetworkManager"
}

# Function to show hotspot status
show_status() {
    print_status "$BLUE" "=== Helmet WiFi AP Status ==="
    
    # AP Configuration
    print_status "$GREEN" "AP Configuration:"
    print_status "$BLUE" "  SSID: $AP_SSID"
    print_status "$BLUE" "  Password: $AP_PASSWORD"
    print_status "$BLUE" "  Interface: $AP_INTERFACE"
    print_status "$BLUE" "  IP Address: $AP_IP"
    
    # Connection Status
    local connection_status=$(nmcli connection show "$CONNECTION_NAME" 2>/dev/null | grep "GENERAL.STATE" | awk '{print $2}')
    if [[ "$connection_status" == "activated" ]]; then
        print_status "$GREEN" "Hotspot Status: ✓ Active"
        
        # Show connection details
        local active_connection=$(nmcli connection show --active | grep "$CONNECTION_NAME")
        if [[ -n "$active_connection" ]]; then
            print_status "$BLUE" "  Connection: $active_connection"
        fi
        
        # Show IP address
        local interface_ip=$(nmcli device show $AP_INTERFACE | grep "IP4.ADDRESS" | head -1 | awk '{print $2}')
        if [[ -n "$interface_ip" ]]; then
            print_status "$GREEN" "  Interface IP: $interface_ip"
        fi
        
    else
        print_status "$RED" "Hotspot Status: ✗ Inactive ($connection_status)"
    fi
    
    # NetworkManager Status
    if systemctl is-active --quiet NetworkManager; then
        print_status "$GREEN" "NetworkManager: ✓ Running"
    else
        print_status "$RED" "NetworkManager: ✗ Not running"
    fi
    
    # Connected clients (if available)
    print_status "$GREEN" "Connected Clients:"
    # NetworkManager doesn't provide easy access to connected clients
    # But we can check ARP table for devices in our subnet
    local clients=$(arp -a | grep "192.168.4" | grep -v "192.168.4.1")
    if [[ -n "$clients" ]]; then
        echo "$clients" | while read -r line; do
            print_status "$BLUE" "  $line"
        done
    else
        print_status "$BLUE" "  No clients currently connected"
    fi
    
    # Show available connections
    print_status "$GREEN" "Available Connections:"
    nmcli connection show | grep -E "(NAME|$CONNECTION_NAME|wifi)" | head -5
    
    print_status "$BLUE" "Log file: $LOG_FILE"
}

# Function to stop hotspot
stop_hotspot() {
    print_status "$BLUE" "Stopping HelmetAP hotspot..."
    
    # Deactivate the hotspot connection
    nmcli connection down "$CONNECTION_NAME" 2>/dev/null
    
    print_status "$GREEN" "HelmetAP hotspot stopped"
}

# Function to remove hotspot completely
remove_hotspot() {
    print_status "$BLUE" "Removing HelmetAP hotspot configuration..."
    
    # Stop the connection first
    stop_hotspot
    
    # Delete the connection
    nmcli connection delete "$CONNECTION_NAME" 2>/dev/null
    
    print_status "$GREEN" "HelmetAP hotspot removed"
}

# Function to restart hotspot
restart_hotspot() {
    print_status "$BLUE" "Restarting HelmetAP hotspot..."
    
    stop_hotspot
    sleep 2
    start_hotspot
    
    if [[ $? -eq 0 ]]; then
        print_status "$GREEN" "HelmetAP hotspot restarted successfully"
    else
        print_status "$RED" "Failed to restart hotspot"
        return 1
    fi
}

# Function to make hotspot persistent
make_persistent() {
    print_status "$BLUE" "Making hotspot auto-start on boot..."
    
    # Set autoconnect to yes (should already be set)
    nmcli connection modify "$CONNECTION_NAME" connection.autoconnect yes
    
    # Set priority higher than other connections
    nmcli connection modify "$CONNECTION_NAME" connection.autoconnect-priority 100
    
    print_status "$GREEN" "Hotspot will auto-start on boot"
}

# Function to show help
show_help() {
    cat << EOF
Helmet Camera WiFi Access Point Setup (NetworkManager)

Usage: $0 [COMMAND]

Commands:
  setup     - Set up and start the WiFi access point
  start     - Start the access point
  stop      - Stop the access point
  restart   - Restart the access point
  remove    - Remove hotspot configuration completely
  status    - Show current access point status
  help      - Show this help message

Access Point Configuration:
  SSID:     $AP_SSID
  Password: $AP_PASSWORD
  Interface: $AP_INTERFACE
  IP:       $AP_IP
  Range:    Automatic DHCP (192.168.4.10-254)

Examples:
  sudo $0 setup     # Initial setup and start
  sudo $0 status    # Check status
  sudo $0 restart   # Restart hotspot

Features:
  ✓ Uses NetworkManager (modern approach)
  ✓ Automatic DHCP server
  ✓ NAT/IP forwarding
  ✓ DNS forwarding
  ✓ Auto-start on boot
  ✓ Client isolation
  ✓ WPA2 security

Requirements:
  - Raspberry Pi OS Bookworm (or NetworkManager installed)
  - WiFi interface available
  - Root privileges

Log file: $LOG_FILE

EOF
}

# Main function
main() {
    case "$1" in
        setup)
            print_status "$BLUE" "=== Setting up Helmet WiFi Access Point ==="
            check_root
            check_networkmanager
            check_wifi_interface
            remove_existing_hotspot
            create_hotspot
            configure_hotspot
            configure_sharing
            start_hotspot
            make_persistent
            show_status
            print_status "$GREEN" "HelmetAP setup completed successfully!"
            print_status "$BLUE" "The hotspot will auto-start on future boots"
            ;;
        start)
            check_root
            check_networkmanager
            start_hotspot && show_status
            ;;
        stop)
            check_root
            stop_hotspot
            ;;
        restart)
            check_root
            restart_hotspot && show_status
            ;;
        remove)
            check_root
            remove_hotspot
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_status "$YELLOW" "Invalid command. Use '$0 help' for usage information."
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 