# Smart Helmet Camera Setup Instructions

## Quick Setup Guide

### 1. MQTT Broker Setup
Install Mosquitto MQTT broker on your network:

**On Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

**Test broker:**
```bash
mosquitto_pub -h localhost -t test -m "Hello MQTT"
mosquitto_sub -h localhost -t test
```

### 2. Master Setup
1. **Install on master device:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure MQTT broker IP in `config.json`:**
   ```json
   "mqtt": {
     "broker_host": "YOUR_BROKER_IP",
     ...
   }
   ```

3. **Test MQTT connection:**
   ```bash
   python test_mqtt_connection.py
   ```

4. **Run master:**
   ```bash
   python master_helmet_system.py
   ```

### 3. Slave Setup (Repeat for each helmet)
1. **Copy Slave folder to each Raspberry Pi**

2. **Install dependencies:**
   ```bash
   cd Slave
   pip install -r requirements.txt
   ```

3. **Configure each slave in `slave_config.json`:**
   ```json
   {
     "client_id": "rpihelmet1",  # Change for each device
     "mqtt": {
       "broker_host": "YOUR_BROKER_IP",
       ...
     }
   }
   ```

4. **Test components:**
   ```bash
   python test_camera.py      # Test picamera2
   python test_gpio.py        # Test GPIO
   python check_gpio.py       # Diagnostics if issues
   ```

5. **Run slave:**
   ```bash
   python slave_helmet_camera.py
   ```

### 4. Usage
1. Start all slaves first
2. Start master
3. In master console, use commands:
   - `capture 3 2` - Take 3 photos with 2-second intervals
   - `help` - Show available commands
   - `quit` - Shutdown

### 5. Troubleshooting

**MQTT Connection Issues:**
- Check broker IP address
- Verify firewall settings
- Test with `mosquitto_pub`/`mosquitto_sub`

**GPIO Permission Issues:**
```bash
sudo usermod -a -G gpio $USER
# Then logout and login
```

**Camera Issues:**
```bash
sudo raspi-config
# Enable camera in Interface Options
```

### 6. File Structure After Setup
```
master_device/
├── master_helmet_system.py
├── config.json
├── requirements.txt
└── camera/

slave_device_1/
├── Slave/
│   ├── slave_helmet_camera.py
│   ├── slave_config.json
│   ├── camera/
│   └── test_*.py

slave_device_2/
├── Slave/
│   ├── slave_helmet_camera.py
│   ├── slave_config.json (with client_id: "rpihelmet2")
│   └── ...
```

### 7. Network Configuration
- All devices should be on the same network
- MQTT broker should be accessible from all devices
- Default MQTT port: 1883
- Ensure no firewall blocking MQTT traffic 