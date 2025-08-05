# WiFi Network Setup (NetworkManager)

This guide explains how to set up a dedicated WiFi network for the helmet camera system using NetworkManager (modern approach for Raspberry Pi OS Bookworm).

## Overview

The helmet camera system uses a dedicated WiFi network where:
- **Master board** creates a WiFi access point called "HelmetAP" 
- **Slave boards** connect to this access point
- All communication happens within this local network (192.168.4.0/24)

## Quick Setup

### 1. Master Board (Access Point)

```bash
# Set up and start the access point
sudo Master/setup_helmet_ap.sh setup

# Check status
sudo Master/setup_helmet_ap.sh status

# Restart if needed
sudo Master/setup_helmet_ap.sh restart
```

### 2. Slave Boards (Clients)

```bash
# Connect to HelmetAP
sudo Slave/connect_to_helmet_ap.sh connect

# Check connection status
sudo Slave/connect_to_helmet_ap.sh status

# Reconnect if needed
sudo Slave/connect_to_helmet_ap.sh reconnect
```

## Network Configuration

| Setting | Value |
|---------|-------|
| **SSID** | HelmetAP |
| **Password** | 12345678 |
| **Master IP** | 192.168.4.1 |
| **DHCP Range** | 192.168.4.10 - 192.168.4.254 |
| **Security** | WPA2-PSK |

## Features

### Master AP Script (`Master/setup_helmet_ap.sh`)

✅ **Modern NetworkManager Integration**
- Uses `nmcli` commands (Bookworm default)
- No manual configuration files
- Automatic service management

✅ **Built-in Services**
- DHCP server (automatic)
- DNS server (automatic)
- NAT/IP forwarding (automatic)

✅ **Management Features**
- Start/stop/restart commands
- Status monitoring
- Connection removal
- Auto-start on boot

### Slave Connection Script (`Slave/connect_to_helmet_ap.sh`)

✅ **Intelligent Connection**
- Network scanning
- Signal strength monitoring
- Automatic reconnection
- Connection validation

✅ **Connectivity Testing**
- Gateway reachability
- DNS resolution
- MQTT broker detection

✅ **Persistence**
- Auto-connect on boot
- Connection profiles
- Service management

## Commands Reference

### Master Board Commands

```bash
# Initial setup (run once)
sudo Master/setup_helmet_ap.sh setup

# Daily operations
sudo Master/setup_helmet_ap.sh start     # Start AP
sudo Master/setup_helmet_ap.sh stop      # Stop AP
sudo Master/setup_helmet_ap.sh restart   # Restart AP
sudo Master/setup_helmet_ap.sh status    # Check status

# Management
sudo Master/setup_helmet_ap.sh remove    # Remove AP completely
Master/setup_helmet_ap.sh help           # Show help
```

### Slave Board Commands

```bash
# Initial setup (run once per slave)
sudo Slave/connect_to_helmet_ap.sh connect

# Daily operations
sudo Slave/connect_to_helmet_ap.sh status      # Check status
sudo Slave/connect_to_helmet_ap.sh reconnect   # Reconnect
sudo Slave/connect_to_helmet_ap.sh disconnect  # Disconnect

# Management
sudo Slave/connect_to_helmet_ap.sh scan        # Scan for HelmetAP
sudo Slave/connect_to_helmet_ap.sh remove      # Remove connection
Slave/connect_to_helmet_ap.sh help             # Show help
```

## Troubleshooting

### Master Board Issues

**AP not starting:**
```bash
# Check NetworkManager status
sudo systemctl status NetworkManager

# Check WiFi interface
nmcli device show wlan0

# View logs
sudo journalctl -u NetworkManager -f
tail -f /var/log/helmet_ap_setup.log
```

**No clients connecting:**
```bash
# Check AP status
sudo Master/setup_helmet_ap.sh status

# Restart the hotspot
sudo Master/setup_helmet_ap.sh restart

# Check for interference
nmcli device wifi list
```

### Slave Board Issues

**Cannot find HelmetAP:**
```bash
# Check if master AP is running
sudo Slave/connect_to_helmet_ap.sh scan

# Check WiFi interface
nmcli device show wlan0

# Enable WiFi radio
nmcli radio wifi on
```

**Connected but no internet:**
```bash
# Check connection details
sudo Slave/connect_to_helmet_ap.sh status

# Test connectivity
ping 192.168.4.1

# Check routing
ip route show
```

**Connection keeps dropping:**
```bash
# Check signal strength
nmcli device wifi list | grep HelmetAP

# View connection logs
sudo journalctl -u NetworkManager -f
tail -f /var/log/helmet_wifi_connect.log

# Reconnect
sudo Slave/connect_to_helmet_ap.sh reconnect
```

## Network Architecture

```
Master Board (192.168.4.1)
    ├── WiFi AP: HelmetAP
    ├── MQTT Broker: port 1883
    ├── Web Server: port 8081
    └── DHCP Server: 192.168.4.10-254

Slave Boards (192.168.4.10+)
    ├── rpihelmet2 → 192.168.4.x
    ├── rpihelmet3 → 192.168.4.x
    ├── rpihelmet4 → 192.168.4.x
    ├── rpihelmet5 → 192.168.4.x
    ├── rpihelmet6 → 192.168.4.x
    └── rpihelmet7 → 192.168.4.x
```

## Advanced Configuration

### Change WiFi Channel

```bash
# Modify the master script or run:
nmcli connection modify HelmetAP-Hotspot wifi.channel 11
sudo Master/setup_helmet_ap.sh restart
```

### Static IP for Slaves

```bash
# Set static IP for a specific slave
nmcli connection modify HelmetAP-Client ipv4.method manual
nmcli connection modify HelmetAP-Client ipv4.address 192.168.4.20/24
nmcli connection modify HelmetAP-Client ipv4.gateway 192.168.4.1
nmcli connection modify HelmetAP-Client ipv4.dns 192.168.4.1
```

### Monitor Connected Clients

```bash
# View DHCP leases (on master)
sudo journalctl -u NetworkManager | grep DHCP

# Check ARP table
arp -a | grep 192.168.4
```

## Log Files

- **Master**: `/var/log/helmet_ap_setup.log`
- **Slave**: `/var/log/helmet_wifi_connect.log`
- **NetworkManager**: `sudo journalctl -u NetworkManager`

## Migration from Old Scripts

If you were using the old wpa_supplicant-based scripts:

1. **Stop old services:**
   ```bash
   sudo systemctl stop hostapd dnsmasq
   sudo systemctl disable hostapd dnsmasq
   ```

2. **Remove old configurations:**
   ```bash
   sudo Master/setup_helmet_ap.sh remove
   sudo Slave/connect_to_helmet_ap.sh remove
   ```

3. **Use new NetworkManager scripts:**
   ```bash
   sudo Master/setup_helmet_ap.sh setup
   sudo Slave/connect_to_helmet_ap.sh connect
   ```

## Requirements

- **Raspberry Pi OS Bookworm** (or any OS with NetworkManager)
- **NetworkManager package** (usually pre-installed)
- **WiFi interface** (wlan0)
- **Root privileges** for network configuration

The NetworkManager approach is more reliable, easier to manage, and the modern standard for Raspberry Pi OS Bookworm and later versions. 