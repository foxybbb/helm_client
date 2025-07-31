# Helmet Camera Slave Service Setup

## Overview
This guide explains how to set up the helmet camera slave software as a **systemd service** that automatically starts on boot and restarts if it crashes.

## Benefits of Running as a Service
- ✅ **Automatic startup** on system boot
- ✅ **Automatic restart** if software crashes
- ✅ **Background operation** without user login
- ✅ **Centralized logging** via systemd journal
- ✅ **Resource management** and security controls
- ✅ **Easy management** with systemctl commands

## Quick Installation

### 1. Navigate to Slave Directory
```bash
cd /path/to/helmet_camera/Slave
```

### 2. Make Installation Script Executable
```bash
chmod +x install_service.sh
```

### 3. Run Installation
```bash
./install_service.sh
```

The installer will:
- Check system requirements
- Install Python dependencies
- Copy files to system location
- Configure permissions for camera/GPIO access
- Install and start the systemd service
- Enable automatic startup on boot

## Manual Installation

If you prefer manual installation or need custom configuration:

### 1. Install Dependencies
```bash
pip3 install --user -r requirements.txt
```

### 2. Copy Service File
```bash
sudo cp helmet-camera-slave.service /etc/systemd/system/
```

### 3. Edit Service Paths (if needed)
```bash
sudo nano /etc/systemd/system/helmet-camera-slave.service
# Modify paths to match your installation
```

### 4. Reload and Enable Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable helmet-camera-slave
sudo systemctl start helmet-camera-slave
```

## Service Management Commands

### Basic Operations
```bash
# Start the service
sudo systemctl start helmet-camera-slave

# Stop the service  
sudo systemctl stop helmet-camera-slave

# Restart the service
sudo systemctl restart helmet-camera-slave

# Check service status
sudo systemctl status helmet-camera-slave

# Enable automatic startup (on boot)
sudo systemctl enable helmet-camera-slave

# Disable automatic startup
sudo systemctl disable helmet-camera-slave
```

### Monitoring and Logs
```bash
# View real-time logs
sudo journalctl -u helmet-camera-slave -f

# View recent logs
sudo journalctl -u helmet-camera-slave -n 50

# View logs from today
sudo journalctl -u helmet-camera-slave --since today

# View logs with timestamps
sudo journalctl -u helmet-camera-slave -o short-iso
```

### Quick Management Script
Use the installation script for quick management:
```bash
# Check status
./install_service.sh status

# Restart service
./install_service.sh restart

# Uninstall service
./install_service.sh uninstall
```

## Service Configuration

### Service File Location
```
/etc/systemd/system/helmet-camera-slave.service
```

### Key Configuration Options

#### Working Directory
```ini
WorkingDirectory=/home/pi/helmet_camera/Slave
```

#### Python Script Path
```ini
ExecStart=/usr/bin/python3 /home/pi/helmet_camera/Slave/slave_helmet_camera.py
```

#### User and Group
```ini
User=pi
Group=pi
```

#### Restart Policy
```ini
Restart=always
RestartSec=10
StartLimitBurst=5
StartLimitIntervalSec=30
```

#### Resource Limits
```ini
MemoryLimit=512M
CPUQuota=80%
```

### Security Features
- **NoNewPrivileges**: Prevents privilege escalation
- **PrivateTmp**: Isolated temporary directories
- **ProtectSystem**: Read-only system directories
- **Supplementary Groups**: Camera and GPIO access

## Troubleshooting

### Service Won't Start
```bash
# Check detailed status
sudo systemctl status helmet-camera-slave -l

# Check recent logs
sudo journalctl -u helmet-camera-slave --since "5 minutes ago"

# Check configuration
sudo systemctl cat helmet-camera-slave
```

### Permission Issues
```bash
# Add user to required groups
sudo usermod -a -G video,gpio,i2c,spi pi

# Enable camera interface
sudo raspi-config nonint do_camera 0

# Enable I2C interface
sudo raspi-config nonint do_i2c 0

# Reboot to apply group changes
sudo reboot
```

### Python Module Issues
```bash
# Install missing dependencies
pip3 install --user -r requirements.txt

# Check Python path
which python3

# Test script manually
cd /home/pi/helmet_camera/Slave
python3 slave_helmet_camera.py
```

### Configuration File Issues
```bash
# Check config file exists and is readable
ls -la slave_config.json
cat slave_config.json

# Validate JSON syntax
python3 -m json.tool slave_config.json
```

## Common Issues and Solutions

### Issue: "Failed to start helmet-camera-slave.service"
**Solution:**
1. Check file permissions: `ls -la slave_helmet_camera.py`
2. Make script executable: `chmod +x slave_helmet_camera.py`
3. Check Python path: `which python3`
4. Test script manually first

### Issue: "Permission denied" for camera
**Solution:**
```bash
sudo usermod -a -G video pi
sudo reboot
```

### Issue: "MQTT connection failed"
**Solution:**
1. Check network connectivity
2. Verify MQTT broker address in `slave_config.json`
3. Check firewall settings
4. Test MQTT connection: `mosquitto_pub -h broker_ip -t test -m "hello"`

### Issue: Service restarts constantly
**Solution:**
1. Check logs: `sudo journalctl -u helmet-camera-slave -f`
2. Look for error patterns
3. Test configuration file
4. Check resource limits

## Performance Monitoring

### Resource Usage
```bash
# Check service resource usage
systemctl show helmet-camera-slave --property=CPUUsageNSec,MemoryCurrent

# Monitor with top
top -p $(pgrep -f slave_helmet_camera)

# Check system load
htop
```

### Log Size Management
```bash
# Check log size
sudo journalctl --disk-usage

# Limit log size (optional)
sudo nano /etc/systemd/journald.conf
# Add: SystemMaxUse=500M
sudo systemctl restart systemd-journald
```

## Network Configuration

### Static IP Setup
For reliable operation, consider setting a static IP:
```bash
sudo nano /etc/dhcpcd.conf
# Add:
# interface wlan0
# static ip_address=192.168.1.100/24
# static routers=192.168.1.1
# static domain_name_servers=192.168.1.1
```

### WiFi Auto-Reconnect
```bash
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
# Ensure network block has:
# network={
#     ssid="TSI2024"
#     psk="TSIRIGA2024"
#     priority=1
# }
```

## Deployment Checklist

Before deploying to production:

- [ ] Service installs and starts successfully
- [ ] Camera functionality tested
- [ ] MQTT connection established
- [ ] Auto-restart on crash verified
- [ ] Boot startup tested
- [ ] Logs are being written properly
- [ ] Resource usage is acceptable
- [ ] Network connectivity is stable
- [ ] Configuration file is correct
- [ ] GPIO permissions working

## Backup and Recovery

### Backup Configuration
```bash
# Backup service file
sudo cp /etc/systemd/system/helmet-camera-slave.service ~/helmet-service-backup.service

# Backup configuration
cp slave_config.json ~/slave-config-backup.json
```

### Quick Recovery
```bash
# Restore service
sudo cp ~/helmet-service-backup.service /etc/systemd/system/helmet-camera-slave.service
sudo systemctl daemon-reload
sudo systemctl enable helmet-camera-slave
sudo systemctl start helmet-camera-slave
```

## Advanced Configuration

### Custom Service Name
To use a custom service name, edit the service file and rename it:
```bash
sudo cp helmet-camera-slave.service helmet-cam-rpi01.service
sudo nano helmet-cam-rpi01.service
# Update Description and service name
```

### Multiple Instances
For running multiple instances (not recommended):
```bash
sudo cp helmet-camera-slave.service helmet-camera-slave@.service
# Modify service file to use %i for instance name
sudo systemctl enable helmet-camera-slave@instance1
```

The service setup provides a robust foundation for deploying helmet camera slaves in production environments with automatic recovery and monitoring capabilities. 