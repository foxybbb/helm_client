#!/bin/bash
# connect_to_helmet_ap.sh
# Connects slave board to HelmetAP WiFi network

# Configuration
AP_SSID="HelmetAP"
AP_PASSWORD="12345678"
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

# Function to backup original configurations
backup_configs() {
    print_status "$BLUE" "Backing up original WiFi configurations..."
    
    # Backup wpa_supplicant.conf
    if [[ -f /etc/wpa_supplicant/wpa_supplicant.conf && ! -f /etc/wpa_supplicant/wpa_supplicant.conf.backup ]]; then
        cp /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf.backup
        print_status "$GREEN" "Backed up /etc/wpa_supplicant/wpa_supplicant.conf"
    fi
    
    # Backup dhcpcd.conf
    if [[ -f /etc/dhcpcd.conf && ! -f /etc/dhcpcd.conf.backup ]]; then
        cp /etc/dhcpcd.conf /etc/dhcpcd.conf.backup
        print_status "$GREEN" "Backed up /etc/dhcpcd.conf"
    fi
}

# Function to check WiFi interface
check_wifi_interface() {
    print_status "$BLUE" "Checking WiFi interface..."
    
    if ! ip link show $INTERFACE &>/dev/null; then
        print_status "$RED" "WiFi interface $INTERFACE not found"
        print_status "$BLUE" "Available interfaces:"
        ip link show | grep -E "^[0-9]+:" | awk '{print $2}' | sed 's/:$//' | grep -v lo
        exit 1
    fi
    
    # Bring interface up if down
    ip link set $INTERFACE up
    print_status "$GREEN" "WiFi interface $INTERFACE is available"
}

# Function to scan for HelmetAP
scan_for_ap() {
    print_status "$BLUE" "Scanning for HelmetAP network..."
    
    # Kill any existing wpa_supplicant processes on this interface
    pkill -f "wpa_supplicant.*$INTERFACE"
    sleep 2
    
    # Scan for networks
    local scan_result=$(iwlist $INTERFACE scan 2>/dev/null | grep -A 5 "ESSID:\"$AP_SSID\"")
    
    if [[ -n "$scan_result" ]]; then
        print_status "$GREEN" "HelmetAP network found"
        # Extract signal quality
        local quality=$(echo "$scan_result" | grep "Quality" | awk -F'=' '{print $2}' | awk '{print $1}')
        if [[ -n "$quality" ]]; then
            print_status "$BLUE" "Signal quality: $quality"
        fi
        return 0
    else
        print_status "$YELLOW" "HelmetAP network not found in scan"
        print_status "$BLUE" "Available networks:"
        iwlist $INTERFACE scan 2>/dev/null | grep "ESSID:" | sort | uniq
        return 1
    fi
}

# Function to configure wpa_supplicant
configure_wpa_supplicant() {
    print_status "$BLUE" "Configuring wpa_supplicant for HelmetAP..."
    
    # Create wpa_supplicant configuration
    cat > /etc/wpa_supplicant/wpa_supplicant.conf << EOF
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

# HelmetAP network configuration
network={
    ssid="$AP_SSID"
    psk="$AP_PASSWORD"
    priority=10
    key_mgmt=WPA-PSK
}
EOF

    print_status "$GREEN" "wpa_supplicant configured for HelmetAP"
}

# Function to configure dhcpcd
configure_dhcpcd() {
    print_status "$BLUE" "Configuring DHCP client..."
    
    # Create dhcpcd configuration for DHCP (dynamic IP)
    cat > /etc/dhcpcd.conf << EOF
# A sample configuration for dhcpcd.
# See dhcpcd.conf(5) for details.

# Allow users of this group to interact with dhcpcd via the control socket.
#controlgroup wheel

# Inform the DHCP server of our hostname for DDNS.
hostname

# Use the hardware address of the interface for the Client ID.
clientid

# Persist interface configuration when dhcpcd exits.
persistent

# Rapid commit support.
option rapid_commit

# A ServerID is required by RFC2131.
require dhcp_server_identifier

# Generate Stable Private IPv6 Addresses instead of hardware based ones
slaac private

# Use DHCP for WiFi interface
interface $INTERFACE
# Request specific information from DHCP server
option domain_name_servers, domain_name, domain_search, host_name
option classless_static_routes
option ntp_servers

# Fallback to static IP if DHCP fails (optional)
# profile static_$INTERFACE
# static ip_address=192.168.4.100/24
# static routers=192.168.4.1
# static domain_name_servers=192.168.4.1

# fallback static_$INTERFACE
EOF

    print_status "$GREEN" "DHCP client configured"
}

# Function to connect to WiFi
connect_wifi() {
    print_status "$BLUE" "Connecting to HelmetAP WiFi network..."
    
    # Stop any existing connections
    systemctl stop wpa_supplicant
    pkill -f "wpa_supplicant.*$INTERFACE"
    sleep 2
    
    # Start wpa_supplicant
    print_status "$BLUE" "Starting wpa_supplicant..."
    wpa_supplicant -B -i $INTERFACE -c /etc/wpa_supplicant/wpa_supplicant.conf
    
    # Wait for connection
    local retry_count=0
    local max_retries=30
    
    while [[ $retry_count -lt $max_retries ]]; do
        local status=$(wpa_cli -i $INTERFACE status 2>/dev/null | grep "wpa_state")
        
        if [[ "$status" == *"COMPLETED"* ]]; then
            print_status "$GREEN" "WiFi connection established"
            break
        elif [[ "$status" == *"DISCONNECTED"* ]] || [[ "$status" == *"SCANNING"* ]]; then
            print_status "$BLUE" "Connecting... (attempt $((retry_count + 1))/$max_retries)"
        else
            print_status "$YELLOW" "Connection status: $status"
        fi
        
        sleep 2
        ((retry_count++))
    done
    
    if [[ $retry_count -eq $max_retries ]]; then
        print_status "$RED" "Failed to connect to HelmetAP after $max_retries attempts"
        return 1
    fi
    
    # Start DHCP client
    print_status "$BLUE" "Starting DHCP client..."
    systemctl restart dhcpcd
    
    # Wait for IP address
    retry_count=0
    max_retries=20
    
    while [[ $retry_count -lt $max_retries ]]; do
        local ip_addr=$(ip addr show $INTERFACE | grep "inet " | awk '{print $2}' | head -1)
        
        if [[ -n "$ip_addr" && "$ip_addr" != "169.254."* ]]; then
            print_status "$GREEN" "IP address obtained: $ip_addr"
            return 0
        fi
        
        print_status "$BLUE" "Waiting for IP address... (attempt $((retry_count + 1))/$max_retries)"
        sleep 3
        ((retry_count++))
    done
    
    print_status "$RED" "Failed to obtain IP address"
    return 1
}

# Function to test connectivity
test_connectivity() {
    print_status "$BLUE" "Testing connectivity to HelmetAP..."
    
    # Test connection to AP gateway
    local gateway="192.168.4.1"
    
    if ping -c 3 -W 5 $gateway >/dev/null 2>&1; then
        print_status "$GREEN" "✓ Gateway connectivity test passed ($gateway)"
    else
        print_status "$RED" "✗ Gateway connectivity test failed ($gateway)"
        return 1
    fi
    
    # Test DNS resolution
    if nslookup master.helmet.local $gateway >/dev/null 2>&1; then
        print_status "$GREEN" "✓ DNS resolution test passed"
    else
        print_status "$YELLOW" "⚠ DNS resolution test failed (non-critical)"
    fi
    
    # Test MQTT broker connectivity (if available)
    if nc -z $gateway 1883 2>/dev/null; then
        print_status "$GREEN" "✓ MQTT broker connectivity test passed"
    else
        print_status "$YELLOW" "⚠ MQTT broker not available yet (may start later)"
    fi
    
    return 0
}

# Function to create auto-connect service
create_auto_connect_service() {
    print_status "$BLUE" "Creating auto-connect service..."
    
    cat > /etc/systemd/system/helmet-wifi-connect.service << EOF
[Unit]
Description=Auto-connect to HelmetAP WiFi
After=network.target
Wants=network.target

[Service]
Type=oneshot
ExecStart=/bin/bash $(realpath "$0") connect-only
RemainAfterExit=true
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

    # Enable the service
    systemctl enable helmet-wifi-connect.service
    
    print_status "$GREEN" "Auto-connect service created and enabled"
}

# Function to show current status
show_status() {
    print_status "$BLUE" "=== Helmet WiFi Connection Status ==="
    
    # Interface status
    local interface_status=$(ip link show $INTERFACE | grep "state")
    print_status "$BLUE" "Interface: $interface_status"
    
    # IP address
    local ip_addr=$(ip addr show $INTERFACE | grep "inet " | awk '{print $2}' | head -1)
    if [[ -n "$ip_addr" ]]; then
        print_status "$GREEN" "IP Address: $ip_addr"
    else
        print_status "$RED" "IP Address: Not assigned"
    fi
    
    # WiFi connection status
    local wifi_status=$(wpa_cli -i $INTERFACE status 2>/dev/null | grep "wpa_state" | cut -d'=' -f2)
    if [[ "$wifi_status" == "COMPLETED" ]]; then
        print_status "$GREEN" "WiFi Status: Connected"
        
        # Show connected network
        local connected_ssid=$(wpa_cli -i $INTERFACE status 2>/dev/null | grep "ssid" | cut -d'=' -f2)
        print_status "$BLUE" "Connected to: $connected_ssid"
        
        # Show signal strength
        local signal=$(wpa_cli -i $INTERFACE signal_poll 2>/dev/null | grep "RSSI" | cut -d'=' -f2)
        if [[ -n "$signal" ]]; then
            print_status "$BLUE" "Signal strength: $signal dBm"
        fi
    else
        print_status "$RED" "WiFi Status: $wifi_status"
    fi
    
    # Gateway connectivity
    if ping -c 1 -W 2 192.168.4.1 >/dev/null 2>&1; then
        print_status "$GREEN" "Gateway: Reachable (192.168.4.1)"
    else
        print_status "$RED" "Gateway: Not reachable"
    fi
    
    # Service status
    if systemctl is-enabled helmet-wifi-connect.service >/dev/null 2>&1; then
        if systemctl is-active helmet-wifi-connect.service >/dev/null 2>&1; then
            print_status "$GREEN" "Auto-connect service: Enabled and active"
        else
            print_status "$YELLOW" "Auto-connect service: Enabled but inactive"
        fi
    else
        print_status "$BLUE" "Auto-connect service: Not enabled"
    fi
    
    print_status "$BLUE" "Log file: $LOG_FILE"
}

# Function to disconnect
disconnect_wifi() {
    print_status "$BLUE" "Disconnecting from HelmetAP..."
    
    # Stop services
    systemctl stop wpa_supplicant
    systemctl stop dhcpcd
    
    # Kill wpa_supplicant processes
    pkill -f "wpa_supplicant.*$INTERFACE"
    
    # Bring interface down and up to reset
    ip link set $INTERFACE down
    sleep 1
    ip link set $INTERFACE up
    
    print_status "$GREEN" "Disconnected from WiFi"
}

# Function to restore original configuration
restore_config() {
    print_status "$BLUE" "Restoring original WiFi configuration..."
    
    # Stop current connections
    disconnect_wifi
    
    # Restore backups
    if [[ -f /etc/wpa_supplicant/wpa_supplicant.conf.backup ]]; then
        cp /etc/wpa_supplicant/wpa_supplicant.conf.backup /etc/wpa_supplicant/wpa_supplicant.conf
        print_status "$GREEN" "Restored wpa_supplicant.conf"
    fi
    
    if [[ -f /etc/dhcpcd.conf.backup ]]; then
        cp /etc/dhcpcd.conf.backup /etc/dhcpcd.conf
        print_status "$GREEN" "Restored dhcpcd.conf"
    fi
    
    # Disable auto-connect service
    systemctl disable helmet-wifi-connect.service 2>/dev/null
    
    # Restart services with original config
    systemctl restart dhcpcd
    systemctl restart wpa_supplicant
    
    print_status "$GREEN" "Original WiFi configuration restored"
}

# Function to show help
show_help() {
    cat << EOF
Helmet Camera WiFi Connection Script

Usage: $0 [COMMAND]

Commands:
  connect       - Connect to HelmetAP WiFi network
  connect-only  - Connect without creating auto-connect service (used by service)
  disconnect    - Disconnect from current WiFi
  status        - Show current connection status
  restore       - Restore original WiFi configuration
  scan          - Scan for HelmetAP network
  help          - Show this help message

WiFi Configuration:
  SSID:     $AP_SSID
  Password: $AP_PASSWORD
  Interface: $INTERFACE

Examples:
  sudo $0 connect   # Connect to HelmetAP
  sudo $0 status    # Check connection status
  sudo $0 restore   # Restore original config

The script will:
1. Backup original WiFi configuration
2. Configure for HelmetAP connection
3. Connect to the network
4. Test connectivity
5. Create auto-connect service

Log file: $LOG_FILE

EOF
}

# Main function
main() {
    case "$1" in
        connect)
            print_status "$BLUE" "=== Connecting to Helmet WiFi Network ==="
            check_root
            backup_configs
            check_wifi_interface
            
            if scan_for_ap; then
                configure_wpa_supplicant
                configure_dhcpcd
                
                if connect_wifi && test_connectivity; then
                    create_auto_connect_service
                    show_status
                    print_status "$GREEN" "Successfully connected to HelmetAP!"
                    print_status "$BLUE" "The system will auto-connect on future boots"
                else
                    print_status "$RED" "Failed to connect to HelmetAP"
                    exit 1
                fi
            else
                print_status "$RED" "Cannot connect - HelmetAP network not found"
                print_status "$YELLOW" "Make sure the master board is running and HelmetAP is active"
                exit 1
            fi
            ;;
        connect-only)
            # Used by systemd service - no auto-connect service creation
            check_wifi_interface
            configure_wpa_supplicant
            configure_dhcpcd
            connect_wifi
            test_connectivity
            ;;
        disconnect)
            check_root
            disconnect_wifi
            ;;
        status)
            show_status
            ;;
        scan)
            check_wifi_interface
            scan_for_ap
            ;;
        restore)
            check_root
            restore_config
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