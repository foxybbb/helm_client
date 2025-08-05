#!/bin/bash
# setup_helmet_ap.sh
# Sets up WiFi Access Point on Master board for helmet camera network

# Configuration
AP_SSID="HelmetAP"
AP_PASSWORD="12345678"
AP_INTERFACE="wlan0"
AP_IP="192.168.4.1"
AP_SUBNET="192.168.4.0/24"
DHCP_RANGE_START="192.168.4.10"
DHCP_RANGE_END="192.168.4.50"

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

# Function to backup original configuration files
backup_configs() {
    print_status "$BLUE" "Backing up original configuration files..."
    
    # Backup network interfaces
    if [[ -f /etc/dhcpcd.conf && ! -f /etc/dhcpcd.conf.backup ]]; then
        cp /etc/dhcpcd.conf /etc/dhcpcd.conf.backup
        print_status "$GREEN" "Backed up /etc/dhcpcd.conf"
    fi
    
    # Backup hostapd config if exists
    if [[ -f /etc/hostapd/hostapd.conf && ! -f /etc/hostapd/hostapd.conf.backup ]]; then
        cp /etc/hostapd/hostapd.conf /etc/hostapd/hostapd.conf.backup
        print_status "$GREEN" "Backed up /etc/hostapd/hostapd.conf"
    fi
    
    # Backup dnsmasq config if exists
    if [[ -f /etc/dnsmasq.conf && ! -f /etc/dnsmasq.conf.backup ]]; then
        cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup
        print_status "$GREEN" "Backed up /etc/dnsmasq.conf"
    fi
}

# Function to install required packages
install_packages() {
    print_status "$BLUE" "Installing required packages..."
    
    # Update package list
    apt-get update -qq
    
    # Install hostapd and dnsmasq
    if ! command -v hostapd &> /dev/null; then
        print_status "$BLUE" "Installing hostapd..."
        apt-get install -y hostapd
    fi
    
    if ! command -v dnsmasq &> /dev/null; then
        print_status "$BLUE" "Installing dnsmasq..."
        apt-get install -y dnsmasq
    fi
    
    print_status "$GREEN" "Required packages installed"
}

# Function to configure static IP for AP interface
configure_static_ip() {
    print_status "$BLUE" "Configuring static IP for AP interface..."
    
    # Configure dhcpcd.conf for static IP
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

# Static IP configuration for AP
interface $AP_INTERFACE
static ip_address=$AP_IP/24
nohook wpa_supplicant

# Example static IP configuration for ethernet
#interface eth0
#static ip_address=192.168.0.10/24
#static routers=192.168.0.1
#static domain_name_servers=192.168.0.1 8.8.8.8
EOF

    print_status "$GREEN" "Static IP configured: $AP_IP"
}

# Function to configure hostapd
configure_hostapd() {
    print_status "$BLUE" "Configuring hostapd..."
    
    # Create hostapd directory if it doesn't exist
    mkdir -p /etc/hostapd
    
    # Create hostapd configuration
    cat > /etc/hostapd/hostapd.conf << EOF
# Interface to use
interface=$AP_INTERFACE

# Driver to use
driver=nl80211

# Name of the network
ssid=$AP_SSID

# Network mode (g = 2.4GHz)
hw_mode=g

# Channel to use
channel=7

# Enable WPA2
wpa=2
wpa_passphrase=$AP_PASSWORD
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP

# Beacon interval in kus (1.024 ms)
beacon_int=100

# DTIM (delivery traffic information message)
dtim_period=2

# Maximum number of stations allowed
max_num_sta=10

# RTS/CTS threshold
rts_threshold=2347

# Fragmentation threshold
fragm_threshold=2346

# Enable 802.11n
ieee80211n=1

# QoS support
wmm_enabled=1

# Country code (adjust as needed)
country_code=US

# Ignore broadcast SSID requests
ignore_broadcast_ssid=0
EOF

    # Set hostapd configuration path
    sed -i 's/#DAEMON_CONF=""/DAEMON_CONF="\/etc\/hostapd\/hostapd.conf"/' /etc/default/hostapd
    
    print_status "$GREEN" "hostapd configured"
}

# Function to configure dnsmasq
configure_dnsmasq() {
    print_status "$BLUE" "Configuring dnsmasq..."
    
    # Create dnsmasq configuration
    cat > /etc/dnsmasq.conf << EOF
# Configuration file for dnsmasq - Helmet Camera AP

# Interface to bind to
interface=$AP_INTERFACE

# Never forward plain names (without a dot or domain part)
domain-needed

# Never forward addresses in the non-routed address spaces
bogus-priv

# Enable DHCP logging
log-dhcp

# Set the domain for dnsmasq
domain=helmet.local

# Set the range of IP addresses to hand out
dhcp-range=$DHCP_RANGE_START,$DHCP_RANGE_END,255.255.255.0,24h

# Set the gateway
dhcp-option=3,$AP_IP

# Set the DNS server (this Pi)
dhcp-option=6,$AP_IP

# Set the DHCP server to authoritative mode
dhcp-authoritative

# Static IP assignments for known devices (optional)
# Format: dhcp-host=MAC_ADDRESS,IP_ADDRESS,HOSTNAME
# dhcp-host=b8:27:eb:xx:xx:xx,192.168.4.11,rpihelmet2
# dhcp-host=b8:27:eb:xx:xx:xx,192.168.4.12,rpihelmet3

# Local domain resolution
address=/helmet.local/$AP_IP
address=/master.helmet.local/$AP_IP

# Enable DNS server on port 53
port=53

# Cache size
cache-size=1000

# Local queries only
local=/helmet.local/
EOF

    print_status "$GREEN" "dnsmasq configured"
}

# Function to enable IP forwarding
enable_ip_forwarding() {
    print_status "$BLUE" "Enabling IP forwarding..."
    
    # Enable IP forwarding
    echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
    
    # Apply immediately
    echo 1 > /proc/sys/net/ipv4/ip_forward
    
    print_status "$GREEN" "IP forwarding enabled"
}

# Function to configure iptables for NAT
configure_iptables() {
    print_status "$BLUE" "Configuring iptables for NAT..."
    
    # Clear existing rules
    iptables -F
    iptables -t nat -F
    
    # Set up NAT from AP interface to ethernet
    iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
    iptables -A FORWARD -i eth0 -o $AP_INTERFACE -m state --state RELATED,ESTABLISHED -j ACCEPT
    iptables -A FORWARD -i $AP_INTERFACE -o eth0 -j ACCEPT
    
    # Allow local communication within AP network
    iptables -A FORWARD -i $AP_INTERFACE -o $AP_INTERFACE -j ACCEPT
    
    # Save iptables rules
    sh -c "iptables-save > /etc/iptables.ipv4.nat"
    
    # Make iptables rules persistent
    cat > /etc/systemd/system/helmet-iptables.service << EOF
[Unit]
Description=Restore iptables rules for Helmet AP
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/iptables-restore /etc/iptables.ipv4.nat
RemainAfterExit=true

[Install]
WantedBy=multi-user.target
EOF

    # Enable the service
    systemctl enable helmet-iptables.service
    
    print_status "$GREEN" "iptables configured for NAT"
}

# Function to create systemd service for AP management
create_ap_service() {
    print_status "$BLUE" "Creating AP management service..."
    
    cat > /etc/systemd/system/helmet-ap.service << EOF
[Unit]
Description=Helmet Camera WiFi Access Point
After=network.target
Wants=network.target

[Service]
Type=forking
ExecStart=/usr/sbin/hostapd -B /etc/hostapd/hostapd.conf
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=process
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Enable services
    systemctl enable hostapd
    systemctl enable dnsmasq
    systemctl enable helmet-ap.service
    
    print_status "$GREEN" "AP management service created"
}

# Function to start services
start_services() {
    print_status "$BLUE" "Starting services..."
    
    # Stop any conflicting services
    systemctl stop wpa_supplicant
    systemctl disable wpa_supplicant
    
    # Restart network configuration
    systemctl restart dhcpcd
    
    # Start AP services
    systemctl restart hostapd
    systemctl restart dnsmasq
    systemctl start helmet-iptables.service
    
    # Wait a moment for services to start
    sleep 3
    
    # Check service status
    if systemctl is-active --quiet hostapd; then
        print_status "$GREEN" "hostapd is running"
    else
        print_status "$RED" "hostapd failed to start"
        systemctl status hostapd --no-pager -l
    fi
    
    if systemctl is-active --quiet dnsmasq; then
        print_status "$GREEN" "dnsmasq is running"
    else
        print_status "$RED" "dnsmasq failed to start"
        systemctl status dnsmasq --no-pager -l
    fi
}

# Function to show AP status
show_status() {
    print_status "$BLUE" "=== Helmet WiFi AP Status ==="
    
    # AP Configuration
    print_status "$GREEN" "AP Configuration:"
    print_status "$BLUE" "  SSID: $AP_SSID"
    print_status "$BLUE" "  Password: $AP_PASSWORD"
    print_status "$BLUE" "  IP Address: $AP_IP"
    print_status "$BLUE" "  DHCP Range: $DHCP_RANGE_START - $DHCP_RANGE_END"
    
    # Service Status
    print_status "$GREEN" "Service Status:"
    if systemctl is-active --quiet hostapd; then
        print_status "$GREEN" "  hostapd: ✓ Running"
    else
        print_status "$RED" "  hostapd: ✗ Not running"
    fi
    
    if systemctl is-active --quiet dnsmasq; then
        print_status "$GREEN" "  dnsmasq: ✓ Running"
    else
        print_status "$RED" "  dnsmasq: ✗ Not running"
    fi
    
    # Network Interface Status
    print_status "$GREEN" "Network Interface:"
    local interface_ip=$(ip addr show $AP_INTERFACE | grep "inet " | awk '{print $2}' | head -1)
    if [[ -n "$interface_ip" ]]; then
        print_status "$GREEN" "  $AP_INTERFACE: $interface_ip"
    else
        print_status "$RED" "  $AP_INTERFACE: No IP assigned"
    fi
    
    # Connected clients
    print_status "$GREEN" "Connected Clients:"
    if [[ -f /var/lib/dhcp/dhcpd.leases ]]; then
        awk '/lease/ { ip = $2 } /client-hostname/ { hostname = $2; gsub(/[";]/, "", hostname) } /binding state active/ { print "  " ip " - " hostname }' /var/lib/dhcp/dhcpd.leases 2>/dev/null || echo "  No active leases found"
    else
        # Try dnsmasq leases
        if [[ -f /var/lib/dnsmasq/dnsmasq.leases ]]; then
            while read -r line; do
                set -- $line
                print_status "$BLUE" "  $3 - $4 ($2)"
            done < /var/lib/dnsmasq/dnsmasq.leases
        else
            print_status "$YELLOW" "  No lease file found"
        fi
    fi
    
    print_status "$BLUE" "Log file: $LOG_FILE"
}

# Function to stop AP
stop_ap() {
    print_status "$BLUE" "Stopping Helmet WiFi AP..."
    
    systemctl stop hostapd
    systemctl stop dnsmasq
    systemctl stop helmet-iptables.service
    
    # Restore original network configuration
    if [[ -f /etc/dhcpcd.conf.backup ]]; then
        cp /etc/dhcpcd.conf.backup /etc/dhcpcd.conf
        systemctl restart dhcpcd
    fi
    
    # Re-enable wpa_supplicant for normal WiFi
    systemctl enable wpa_supplicant
    
    print_status "$GREEN" "Helmet WiFi AP stopped"
}

# Function to show help
show_help() {
    cat << EOF
Helmet Camera WiFi Access Point Setup

Usage: $0 [COMMAND]

Commands:
  setup     - Set up and start the WiFi access point
  start     - Start the access point services
  stop      - Stop the access point and restore normal WiFi
  status    - Show current access point status
  restart   - Restart the access point services
  help      - Show this help message

Access Point Configuration:
  SSID:     $AP_SSID
  Password: $AP_PASSWORD
  IP:       $AP_IP
  Range:    $DHCP_RANGE_START - $DHCP_RANGE_END

Examples:
  sudo $0 setup     # Initial setup and start
  sudo $0 status    # Check status
  sudo $0 restart   # Restart services

Log file: $LOG_FILE

EOF
}

# Main function
main() {
    case "$1" in
        setup)
            print_status "$BLUE" "=== Setting up Helmet WiFi Access Point ==="
            check_root
            backup_configs
            install_packages
            configure_static_ip
            configure_hostapd
            configure_dnsmasq
            enable_ip_forwarding
            configure_iptables
            create_ap_service
            start_services
            show_status
            print_status "$GREEN" "Helmet WiFi AP setup completed!"
            print_status "$YELLOW" "Please reboot the system to ensure all changes take effect"
            ;;
        start)
            check_root
            print_status "$BLUE" "Starting Helmet WiFi AP..."
            start_services
            show_status
            ;;
        stop)
            check_root
            stop_ap
            ;;
        restart)
            check_root
            print_status "$BLUE" "Restarting Helmet WiFi AP..."
            systemctl restart hostapd
            systemctl restart dnsmasq
            show_status
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