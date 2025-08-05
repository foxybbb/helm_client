#!/bin/bash
# connect_to_helmet_ap.sh
# Connects slave board to HelmetAP WiFi network using NetworkManager (nmcli)

# Configuration
AP_SSID="HelmetAP"
AP_PASSWORD="12345678"
CONNECTION_NAME="HelmetAP-Client"
INTERFACE="wlan0"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="/var/log/helmet_wifi_connect.log"

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
    
    if ! nmcli device show $INTERFACE &>/dev/null; then
        print_status "$RED" "WiFi interface $INTERFACE not found"
        print_status "$BLUE" "Available interfaces:"
        nmcli device show | grep "DEVICE" | awk '{print $2}'
        exit 1
    fi
    
    # Make sure interface is managed by NetworkManager
    nmcli device set $INTERFACE managed yes
    
    # Enable WiFi if disabled
    nmcli radio wifi on
    
    print_status "$GREEN" "WiFi interface $INTERFACE is available and managed"
}

# Function to scan for HelmetAP
scan_for_ap() {
    print_status "$BLUE" "Scanning for HelmetAP network..."
    
    # Rescan for networks
    nmcli device wifi rescan ifname $INTERFACE 2>/dev/null
    sleep 3
    
    # Look for HelmetAP
    local ap_found=$(nmcli device wifi list ifname $INTERFACE | grep "$AP_SSID")
    
    if [[ -n "$ap_found" ]]; then
        print_status "$GREEN" "HelmetAP network found"
        # Show signal strength
        local signal=$(echo "$ap_found" | awk '{print $7}')
        local security=$(echo "$ap_found" | awk '{print $8}')
        print_status "$BLUE" "Signal: $signal, Security: $security"
        return 0
    else
        print_status "$YELLOW" "HelmetAP network not found in scan"
        print_status "$BLUE" "Available networks:"
        nmcli device wifi list ifname $INTERFACE | head -10
        return 1
    fi
}

# Function to remove existing connections to HelmetAP
remove_existing_connection() {
    print_status "$BLUE" "Checking for existing HelmetAP connections..."
    
    # Find existing connections to the same SSID
    local existing_connections=$(nmcli connection show | grep -E "$AP_SSID|$CONNECTION_NAME" | awk '{print $1}')
    
    if [[ -n "$existing_connections" ]]; then
        print_status "$YELLOW" "Removing existing HelmetAP connections..."
        echo "$existing_connections" | while read -r conn; do
            if [[ -n "$conn" ]]; then
                nmcli connection delete "$conn" 2>/dev/null || true
                print_status "$BLUE" "Removed connection: $conn"
            fi
        done
    fi
}

# Function to create connection profile
create_connection() {
    print_status "$BLUE" "Creating HelmetAP connection profile..."
    
    # Create WiFi connection with correct NetworkManager syntax
    nmcli connection add \
        type wifi \
        ifname $INTERFACE \
        con-name "$CONNECTION_NAME" \
        autoconnect yes \
        wifi.ssid "$AP_SSID" \
        wifi-sec.key-mgmt wpa-psk \
        wifi-sec.psk "$AP_PASSWORD"
    
    if [[ $? -eq 0 ]]; then
        print_status "$GREEN" "Connection profile created successfully"
    else
        print_status "$RED" "Failed to create connection profile"
        return 1
    fi
}

# Function to configure connection settings
configure_connection() {
    print_status "$BLUE" "Configuring connection settings..."
    
    # Set connection priority (higher than other WiFi connections)
    nmcli connection modify "$CONNECTION_NAME" connection.autoconnect-priority 100
    
    # Set to auto-connect
    nmcli connection modify "$CONNECTION_NAME" connection.autoconnect yes
    
    # Configure to use DHCP
    nmcli connection modify "$CONNECTION_NAME" ipv4.method auto
    nmcli connection modify "$CONNECTION_NAME" ipv6.method auto
    
    print_status "$GREEN" "Connection configured"
}

# Function to connect to WiFi
connect_wifi() {
    print_status "$BLUE" "Connecting to HelmetAP..."
    
    # Disconnect any active connections on the interface first
    local active_connections=$(nmcli connection show --active | grep $INTERFACE | awk '{print $1}')
    if [[ -n "$active_connections" ]]; then
        echo "$active_connections" | while read -r conn; do
            if [[ "$conn" != "$CONNECTION_NAME" ]]; then
                nmcli connection down "$conn" 2>/dev/null || true
                print_status "$BLUE" "Disconnected from: $conn"
            fi
        done
    fi
    
    # Connect to HelmetAP
    nmcli connection up "$CONNECTION_NAME"
    
    if [[ $? -eq 0 ]]; then
        print_status "$GREEN" "Connected to HelmetAP"
        
        # Wait for IP address
        local retry_count=0
        local max_retries=20
        
        while [[ $retry_count -lt $max_retries ]]; do
            local ip_addr=$(nmcli device show $INTERFACE | grep "IP4.ADDRESS" | head -1 | awk '{print $2}')
            
            if [[ -n "$ip_addr" && "$ip_addr" != "169.254."* ]]; then
                print_status "$GREEN" "IP address obtained: $ip_addr"
                return 0
            fi
            
            print_status "$BLUE" "Waiting for IP address... (attempt $((retry_count + 1))/$max_retries)"
            sleep 2
            ((retry_count++))
        done
        
        print_status "$YELLOW" "Connected but no IP address obtained yet"
        return 0
    else
        print_status "$RED" "Failed to connect to HelmetAP"
        return 1
    fi
}

# Function to test connectivity
test_connectivity() {
    print_status "$BLUE" "Testing connectivity..."
    
    # Get gateway from NetworkManager
    local gateway=$(nmcli device show $INTERFACE | grep "IP4.GATEWAY" | awk '{print $2}')
    
    if [[ -z "$gateway" ]]; then
        gateway="192.168.4.1"  # Default HelmetAP gateway
    fi
    
    # Test gateway connectivity
    if ping -c 3 -W 5 $gateway >/dev/null 2>&1; then
        print_status "$GREEN" "✓ Gateway connectivity test passed ($gateway)"
    else
        print_status "$RED" "✗ Gateway connectivity test failed ($gateway)"
        return 1
    fi
    
    # Test DNS resolution
    local dns_servers=$(nmcli device show $INTERFACE | grep "IP4.DNS" | awk '{print $2}')
    if [[ -n "$dns_servers" ]]; then
        print_status "$GREEN" "✓ DNS servers configured: $dns_servers"
    fi
    
    # Test MQTT broker connectivity
    if nc -z $gateway 1883 2>/dev/null; then
        print_status "$GREEN" "✓ MQTT broker connectivity test passed"
    else
        print_status "$YELLOW" "⚠ MQTT broker not available yet (may start later)"
    fi
    
    return 0
}

# Function to create auto-connect service
create_auto_connect_service() {
    print_status "$BLUE" "Configuring auto-connect behavior..."
    
    # NetworkManager handles auto-connect automatically
    # But we can create a service to ensure connection after boot
    cat > /etc/systemd/system/helmet-wifi-ensure.service << EOF
[Unit]
Description=Ensure HelmetAP WiFi Connection
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'sleep 10 && nmcli connection up "$CONNECTION_NAME" || true'
RemainAfterExit=true

[Install]
WantedBy=multi-user.target
EOF

    # Enable the service
    systemctl enable helmet-wifi-ensure.service
    
    print_status "$GREEN" "Auto-connect service configured"
}

# Function to show connection status
show_status() {
    print_status "$BLUE" "=== Helmet WiFi Connection Status ==="
    
    # Connection status
    local connection_state=$(nmcli connection show "$CONNECTION_NAME" 2>/dev/null | grep "GENERAL.STATE" | awk '{print $2}')
    if [[ "$connection_state" == "activated" ]]; then
        print_status "$GREEN" "Connection Status: ✓ Connected"
        
        # Show connection details
        local active_connection=$(nmcli connection show --active | grep "$CONNECTION_NAME")
        if [[ -n "$active_connection" ]]; then
            print_status "$BLUE" "Active Connection: $active_connection"
        fi
        
    else
        print_status "$RED" "Connection Status: ✗ Not connected ($connection_state)"
    fi
    
    # Interface status
    local device_state=$(nmcli device show $INTERFACE | grep "GENERAL.STATE" | awk '{print $2}')
    print_status "$BLUE" "Interface State: $device_state"
    
    # IP address information
    local ip_addr=$(nmcli device show $INTERFACE | grep "IP4.ADDRESS" | head -1 | awk '{print $2}')
    if [[ -n "$ip_addr" ]]; then
        print_status "$GREEN" "IP Address: $ip_addr"
    else
        print_status "$RED" "IP Address: Not assigned"
    fi
    
    # Gateway
    local gateway=$(nmcli device show $INTERFACE | grep "IP4.GATEWAY" | awk '{print $2}')
    if [[ -n "$gateway" ]]; then
        print_status "$BLUE" "Gateway: $gateway"
        
        # Test gateway connectivity
        if ping -c 1 -W 2 $gateway >/dev/null 2>&1; then
            print_status "$GREEN" "Gateway: ✓ Reachable"
        else
            print_status "$RED" "Gateway: ✗ Not reachable"
        fi
    fi
    
    # DNS servers
    local dns_servers=$(nmcli device show $INTERFACE | grep "IP4.DNS" | awk '{print $2}' | tr '\n' ' ')
    if [[ -n "$dns_servers" ]]; then
        print_status "$BLUE" "DNS Servers: $dns_servers"
    fi
    
    # WiFi signal strength
    if [[ "$connection_state" == "activated" ]]; then
        local signal_info=$(nmcli device wifi list | grep "$AP_SSID" | head -1)
        if [[ -n "$signal_info" ]]; then
            local signal=$(echo "$signal_info" | awk '{print $7}')
            print_status "$BLUE" "Signal Strength: $signal"
        fi
    fi
    
    # NetworkManager status
    if systemctl is-active --quiet NetworkManager; then
        print_status "$GREEN" "NetworkManager: ✓ Running"
    else
        print_status "$RED" "NetworkManager: ✗ Not running"
    fi
    
    # Auto-connect service
    if systemctl is-enabled helmet-wifi-ensure.service >/dev/null 2>&1; then
        print_status "$GREEN" "Auto-connect service: ✓ Enabled"
    else
        print_status "$BLUE" "Auto-connect service: Not configured"
    fi
    
    print_status "$BLUE" "Log file: $LOG_FILE"
}

# Function to disconnect
disconnect_wifi() {
    print_status "$BLUE" "Disconnecting from HelmetAP..."
    
    # Disconnect the connection
    nmcli connection down "$CONNECTION_NAME" 2>/dev/null
    
    print_status "$GREEN" "Disconnected from WiFi"
}

# Function to remove connection completely
remove_connection() {
    print_status "$BLUE" "Removing HelmetAP connection..."
    
    # Disconnect first
    disconnect_wifi
    
    # Delete the connection
    nmcli connection delete "$CONNECTION_NAME" 2>/dev/null
    
    # Remove auto-connect service
    systemctl disable helmet-wifi-ensure.service 2>/dev/null
    rm -f /etc/systemd/system/helmet-wifi-ensure.service
    
    print_status "$GREEN" "HelmetAP connection removed"
}

# Function to reconnect
reconnect_wifi() {
    print_status "$BLUE" "Reconnecting to HelmetAP..."
    
    # First disconnect
    disconnect_wifi
    sleep 2
    
    # Then connect
    connect_wifi
    
    if [[ $? -eq 0 ]]; then
        test_connectivity
        print_status "$GREEN" "Reconnected successfully"
    else
        print_status "$RED" "Failed to reconnect"
        return 1
    fi
}

# Function to show help
show_help() {
    cat << EOF
Helmet Camera WiFi Connection Script (NetworkManager)

Usage: $0 [COMMAND]

Commands:
  connect       - Connect to HelmetAP WiFi network
  disconnect    - Disconnect from HelmetAP
  reconnect     - Disconnect and reconnect
  remove        - Remove HelmetAP connection completely
  status        - Show current connection status
  scan          - Scan for HelmetAP network
  help          - Show this help message

WiFi Configuration:
  SSID:     $AP_SSID
  Password: $AP_PASSWORD
  Interface: $INTERFACE

Examples:
  sudo $0 connect   # Connect to HelmetAP
  sudo $0 status    # Check connection status
  sudo $0 remove    # Remove connection

Features:
  ✓ Uses NetworkManager (modern approach)
  ✓ Automatic reconnection
  ✓ Persistent configuration
  ✓ Auto-connect on boot
  ✓ Signal strength monitoring
  ✓ Connectivity testing

The script will:
1. Check NetworkManager status
2. Scan for HelmetAP network
3. Create connection profile
4. Connect to the network
5. Test connectivity
6. Configure auto-connect

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
        connect)
            print_status "$BLUE" "=== Connecting to Helmet WiFi Network ==="
            check_root
            check_networkmanager
            check_wifi_interface
            
            if scan_for_ap; then
                remove_existing_connection
                create_connection
                configure_connection
                
                if connect_wifi && test_connectivity; then
                    create_auto_connect_service
                    show_status
                    print_status "$GREEN" "Successfully connected to HelmetAP!"
                    print_status "$BLUE" "The system will auto-connect on future boots"
                else
                    print_status "$RED" "Connection established but connectivity test failed"
                    show_status
                fi
            else
                print_status "$RED" "Cannot connect - HelmetAP network not found"
                print_status "$YELLOW" "Make sure the master board is running and HelmetAP is active"
                exit 1
            fi
            ;;
        disconnect)
            check_root
            disconnect_wifi
            ;;
        reconnect)
            check_root
            check_networkmanager
            reconnect_wifi
            show_status
            ;;
        remove)
            check_root
            remove_connection
            ;;
        status)
            show_status
            ;;
        scan)
            check_wifi_interface
            scan_for_ap
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