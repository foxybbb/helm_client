# Smart Helmet Camera System - Complete Implementation

## 🎯 Project Overview

A distributed Raspberry Pi-based smart helmet camera system with MQTT communication between master and slave devices. The master generates GPIO pulses and coordinates synchronized photo capture across multiple helmet-mounted cameras.

## 📁 Final Project Structure

```
helm_client/
├── Master/                          # 🎛️  Master System Files
│   ├── master_helmet_system.py      # Main master application
│   ├── run_master.py               # Easy launcher with checks
│   ├── master_config.json          # Master configuration
│   ├── README.md                   # Master-specific documentation
│   ├── requirements.txt            # Dependencies
│   ├── test_mqtt_connection.py     # MQTT connectivity test
│   └── camera/                     # Shared utilities
│
├── Slave/                          # 📷 Slave System Files
│   ├── slave_helmet_camera.py      # Main slave application
│   ├── slave_config.json           # Slave configuration
│   ├── requirements.txt            # Dependencies
│   ├── test_camera.py              # Camera functionality test
│   ├── test_gpio.py                # GPIO functionality test
│   ├── check_gpio.py               # GPIO diagnostics
│   └── camera/                     # Camera services and factories
│       ├── services.py             # MQTT + Camera services
│       ├── factories/              # Component factories
│       └── utils/                  # Utilities
│
├── README.md                       # Main project documentation
├── SETUP_INSTRUCTIONS.md           # Quick setup guide
├── PROJECT_OVERVIEW.md             # This file
├── ARCHITECTURE.md                 # Technical architecture
└── helmet_camera.py                # Original implementation (reference)
```

## 🚀 Quick Start Guide

### 1. MQTT Broker Setup
```bash
# Install Mosquitto MQTT broker
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### 2. Master Setup
```bash
cd Master/
pip install -r requirements.txt

# Configure MQTT broker IP in master_config.json
# Edit "broker_host": "YOUR_BROKER_IP"

# Test MQTT connection
python test_mqtt_connection.py

# Run master system (recommended)
python run_master.py

# Or run directly
python master_helmet_system.py
```

### 3. Slave Setup (for each helmet)
```bash
cd Slave/
pip install -r requirements.txt

# Configure each slave in slave_config.json
# Edit "client_id": "rpihelmet1" (change number for each device)
# Edit "broker_host": "YOUR_BROKER_IP"

# Test components
python test_camera.py      # Test picamera2
python test_gpio.py        # Test GPIO
python check_gpio.py       # Diagnostics if issues

# Run slave
python slave_helmet_camera.py
```

## 📡 MQTT Communication Protocol

### Master → Slaves Command Format
```json
{
  "id": 321,                          // Monotonic counter
  "t_utc_ns": 1753828805123456789,   // Precise UTC timestamp
  "exposure_us": 8000,               // Camera exposure time
  "timeout_ms": 5000,                // Command timeout
  "notes": "session_20250729_01"     // Session identifier
}
```

### Slaves → Master Response Format
```json
{
  "id": 321,                         // Matching command ID
  "client": "rpihelmet3",           // Slave identifier
  "status": "ok",                   // ok | fail | timeout
  "started_ns": 1753828805123461000, // When processing started
  "finished_ns": 1753828805131461000, // When completed
  "file": "cam3_20250729_000321.jpg", // Generated filename
  "jitter_us": 43,                  // Timing jitter in microseconds
  "error": ""                       // Error message if failed
}
```

## 🎮 Master Interactive Commands

Once master is running, use these commands:

- `capture` - Take 1 synchronized photo
- `capture 5` - Take 5 photos with 5-second intervals
- `capture 3 2` - Take 3 photos with 2-second intervals
- `help` - Show available commands
- `quit` / `exit` - Shutdown system

## ⚙️ Key Features Implemented

### Master System Features ✅
- ✅ GPIO pulse generation for hardware synchronization
- ✅ MQTT command broadcasting to multiple slaves
- ✅ Response collection and logging from all slaves
- ✅ Interactive command interface
- ✅ Session management with timestamps
- ✅ Threading for concurrent MQTT operations
- ✅ Automatic slave tracking and timeout handling

### Slave System Features ✅
- ✅ MQTT command processing with threading
- ✅ Picamera2-based photo capture
- ✅ Precise timestamp tracking and jitter calculation
- ✅ Automatic response generation
- ✅ Error handling and reporting
- ✅ Connection resilience with auto-reconnect
- ✅ Duplicate command filtering

### Technical Implementation ✅
- ✅ **picamera2** package integration
- ✅ **paho-mqtt** for MQTT communication
- ✅ **Threading** for concurrent operations
- ✅ **JSON protocol** exactly as specified
- ✅ **GPIO pulse generation** for sync signals
- ✅ **Comprehensive error handling**
- ✅ **Graceful shutdown** on signals

## 🔧 Configuration Examples

### Master Configuration (`Master/master_config.json`)
```json
{
  "master_id": "helm_master",
  "gpio_pin": 17,
  "startup_delay": 5,
  "pulse_duration_ms": 100,
  "pulse_interval_ms": 1000,
  "exposure_us": 8000,
  "timeout_ms": 5000,
  "photo_base_dir": "/home/rpi",
  "log_dir": "~/helmet_camera_logs",
  "mqtt": {
    "broker_host": "192.168.1.100",
    "broker_port": 1883,
    "topic_commands": "helmet/commands",
    "topic_responses": "helmet/responses",
    "keepalive": 60,
    "qos": 1
  },
  "slaves": ["rpihelmet1", "rpihelmet2", "rpihelmet3"]
}
```

### Slave Configuration (`Slave/slave_config.json`)
```json
{
  "client_id": "rpihelmet3",
  "gpio_pin": 17,
  "startup_delay": 5,
  "photo_base_dir": "/home/rpi",
  "log_dir": "~/helmet_camera_logs",
  "mqtt": {
    "broker_host": "192.168.1.100",
    "broker_port": 1883,
    "topic_commands": "helmet/commands",
    "topic_responses": "helmet/responses",
    "keepalive": 60,
    "qos": 1
  }
}
```

## 📸 Photo Output Structure

Photos are automatically organized:
```
/home/rpi/helmet-cam{N}/{session_name}/
├── cam1_20250729_000321.jpg
├── cam2_20250729_000321.jpg
├── cam3_20250729_000321.jpg
└── ...
```

## 🔍 Testing & Validation

### Available Test Scripts
- `Master/test_mqtt_connection.py` - Test MQTT broker connectivity
- `Slave/test_camera.py` - Test picamera2 functionality
- `Slave/test_gpio.py` - Test GPIO interrupt functionality
- `Slave/check_gpio.py` - GPIO diagnostics and troubleshooting

### Example Test Workflow
```bash
# 1. Test MQTT broker
cd Master/
python test_mqtt_connection.py

# 2. Test slave cameras
cd ../Slave/
python test_camera.py

# 3. Test GPIO (optional)
python test_gpio.py

# 4. Start slaves
python slave_helmet_camera.py &

# 5. Start master
cd ../Master/
python run_master.py

# 6. In master console:
master> capture 3 2
```

## 🎉 Implementation Complete!

✅ **All requirements implemented:**
- ✅ Files transferred to Slave folder
- ✅ Files transferred to Master folder
- ✅ picamera2 package usage (was already implemented)
- ✅ MQTT protocol with exact JSON formats specified
- ✅ Master program with pulse generation
- ✅ Threading implementation for concurrent operations
- ✅ Complete working system ready for deployment

The system is now fully functional and ready for production use! 