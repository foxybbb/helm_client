# Helmet Camera Slave Service - Quick Reference

## 🚀 Quick Setup (Recommended)
```bash
# 1. Make scripts executable
chmod +x install_service.sh manage_service.sh

# 2. Install service
./install_service.sh

# 3. Service will start automatically on boot!
```

## 📋 Service Management
```bash
# Quick status check
./manage_service.sh quick

# Detailed status
./manage_service.sh status

# Control service
./manage_service.sh start
./manage_service.sh stop
./manage_service.sh restart

# View logs
./manage_service.sh logs
./manage_service.sh follow    # Real-time logs

# Boot settings
./manage_service.sh enable    # Auto-start on boot
./manage_service.sh disable   # Don't auto-start
```

## 🔧 What the Service Does
- ✅ **Automatically starts** helmet camera software on boot
- ✅ **Restarts automatically** if software crashes
- ✅ **Runs in background** without needing user login
- ✅ **Logs everything** to systemd journal
- ✅ **Manages resources** (memory/CPU limits)
- ✅ **Security controls** (restricted permissions)

## 📂 Files Created
- **Service file**: `/etc/systemd/system/helmet-camera-slave.service`
- **Software location**: `/home/pi/helmet_camera/Slave/`
- **Logs**: `sudo journalctl -u helmet-camera-slave`

## 🛠 Manual Commands (if needed)
```bash
# Traditional systemctl commands
sudo systemctl start helmet-camera-slave
sudo systemctl stop helmet-camera-slave
sudo systemctl restart helmet-camera-slave
sudo systemctl status helmet-camera-slave
sudo systemctl enable helmet-camera-slave
sudo systemctl disable helmet-camera-slave

# View logs
sudo journalctl -u helmet-camera-slave -f
```

## 🚨 Troubleshooting
```bash
# Check if service exists
systemctl list-unit-files | grep helmet

# Check detailed status
sudo systemctl status helmet-camera-slave -l

# Check recent errors
sudo journalctl -u helmet-camera-slave --since "10 minutes ago"

# Test script manually
cd /home/pi/helmet_camera/Slave
python3 slave_helmet_camera.py

# Uninstall if needed
./install_service.sh uninstall
```

## 🔄 After Installation
The service will:
1. **Start automatically** when Raspberry Pi boots
2. **Restart automatically** if it crashes (every 10 seconds)
3. **Connect to MQTT** and wait for commands from master
4. **Log all activity** to system journal
5. **Run with appropriate permissions** for camera/GPIO access

## 📊 Service Status Indicators
- **🟢 Active (running)**: Service is working normally
- **🟡 Inactive (dead)**: Service is stopped
- **🔴 Failed**: Service crashed and couldn't restart
- **🔄 Activating**: Service is starting up

## 📱 Monitoring Service Health
```bash
# Quick health check
./manage_service.sh quick

# Expected output:
# ● Service is running
# ● Auto-start enabled  
# ● Last started: [timestamp]
# ● No recent errors
```

Perfect for **production deployment** on helmet camera slaves! 🎯 