#!/usr/bin/env python3
"""
Master Web Status Server

Provides a web interface for the master system to monitor all connected slaves,
view their status, images, and coordinate capture sessions.
"""

import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'helmet_master_web_status'

# Global variables
master_system = None
config = None
web_status = {
    "startup_time": datetime.now().isoformat(),
    "total_commands_sent": 0,
    "active_slaves": [],
    "last_session": None
}

@app.route('/')
def index():
    """Main master dashboard"""
    return render_template('master_dashboard.html')

@app.route('/api/master/status')
def api_master_status():
    """API endpoint for master system status"""
    global master_system, config, web_status
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": (datetime.now() - datetime.fromisoformat(web_status["startup_time"])).total_seconds(),
        "master": web_status
    }
    
    if master_system and config:
        # Get enhanced statistics
        mqtt_stats = master_system.mqtt_service.get_stats() if hasattr(master_system, 'mqtt_service') else {}
        
        status.update({
            "master_id": config.get("master_id", "unknown"),
            "mqtt_connected": master_system.mqtt_service.connected if hasattr(master_system, 'mqtt_service') else False,
            "configured_slaves": config.get("slaves", []),
            "pending_commands": len(master_system.mqtt_service.pending_commands) if hasattr(master_system, 'mqtt_service') else 0,
            "running": master_system.running if hasattr(master_system, 'running') else False,
            "imu_available": master_system.imu_sensor.available if hasattr(master_system, 'imu_sensor') else False,
            "session_name": master_system.mqtt_service.session_name if hasattr(master_system, 'mqtt_service') else None,
            "session_directory": str(master_system.session_dir) if hasattr(master_system, 'session_dir') and master_system.session_dir else None,
            "display_available": master_system.oled_display.available if hasattr(master_system, 'oled_display') else False,
            "statistics": mqtt_stats
        })
    
    return jsonify(status)

@app.route('/api/master/slaves')
def api_slaves_status():
    """API endpoint for all slaves status"""
    global master_system, config
    
    slaves = []
    
    if config:
        # Get board statistics from master system
        board_stats = {}
        if master_system and hasattr(master_system, 'mqtt_service'):
            board_stats = master_system.mqtt_service.get_board_stats()
        
        for slave_id in config.get("slaves", []):
            slave_info = {
                "slave_id": slave_id,
                "status": "unknown",
                "last_seen": None,
                "last_response": None,
                "response_count": 0,
                "successful_responses": 0,
                "failed_responses": 0,
                "timeout_responses": 0,
                "avg_response_time_ms": 0,
                "last_response_time_ms": 0
            }
            
            # Get detailed statistics if available
            if slave_id in board_stats:
                board_stat = board_stats[slave_id]
                slave_info.update({
                    "status": board_stat["status"],
                    "last_seen": board_stat["last_seen"],
                    "response_count": board_stat["response_count"],
                    "successful_responses": board_stat["successful_responses"],
                    "failed_responses": board_stat["failed_responses"],
                    "timeout_responses": board_stat["timeout_responses"],
                    "avg_response_time_ms": round(board_stat["avg_response_time_ms"], 1),
                    "last_response_time_ms": round(board_stat["last_response_time_ms"], 1),
                    "total_commands": board_stat["total_commands"]
                })
            
            slaves.append(slave_info)
    
    return jsonify({
        "slaves": slaves,
        "total_configured": len(slaves),
        "total_online": len([s for s in slaves if s["status"] == "online"]),
        "total_timeout": len([s for s in slaves if s["status"] == "timeout"]),
        "total_error": len([s for s in slaves if s["status"] == "error"])
    })

@app.route('/api/master/command', methods=['POST'])
def api_send_command():
    """API endpoint to send capture commands"""
    global master_system
    
    try:
        data = request.get_json()
        count = data.get('count', 1)
        interval = data.get('interval', 5)
        
        if not master_system or not hasattr(master_system, 'capture_sequence'):
            return jsonify({"error": "Master system not ready"}), 503
        
        # Execute capture sequence in background thread
        def execute_capture():
            try:
                master_system.capture_sequence(count, interval)
                web_status["total_commands_sent"] += count
            except Exception as e:
                logging.error(f"Error executing capture sequence: {e}")
        
        thread = threading.Thread(target=execute_capture, daemon=True)
        thread.start()
        
        web_status["last_session"] = datetime.now().isoformat()
        
        return jsonify({
            "status": "started",
            "count": count,
            "interval": interval,
            "message": f"Capture sequence started: {count} photos with {interval}s intervals"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to start capture: {e}"}), 500

@app.route('/api/master/statistics')
def api_master_statistics():
    """API endpoint for detailed master statistics"""
    global master_system
    
    if not master_system or not hasattr(master_system, 'mqtt_service'):
        return jsonify({"error": "Master system not available"}), 503
    
    try:
        detailed_status = master_system.mqtt_service.get_detailed_status()
        return jsonify(detailed_status)
    except Exception as e:
        return jsonify({"error": f"Failed to get statistics: {e}"}), 500

@app.route('/api/master/logs')
def api_master_logs():
    """API endpoint for master system logs"""
    try:
        # Read recent log entries
        log_dir = config.get("log_dir", "~/helmet_camera_logs")
        if log_dir.startswith("~"):
            log_dir = str(Path(log_dir).expanduser())
        
        log_dir = Path(log_dir)
        if not log_dir.exists():
            return jsonify({"lines": ["No log directory found"]})
        
        # Find the most recent log file
            log_files = list(log_dir.glob("helmet_camera_*.log"))
        if not log_files:
            return jsonify({"lines": ["No log files found"]})
        
                latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
                
        # Read last 50 lines
        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            recent_lines = [line.strip() for line in lines[-50:] if line.strip()]
        
        return jsonify({"lines": recent_lines})
        
    except Exception as e:
        return jsonify({"error": f"Failed to read logs: {e}"})

@app.route('/api/master/config')
def api_get_config():
    """API endpoint for getting current configuration"""
    global config
    
    try:
        if not config:
            return jsonify({"error": "Configuration not available"}), 503
        
        # Return sanitized config (remove sensitive info)
        safe_config = config.copy()
        if 'mqtt' in safe_config and 'password' in safe_config['mqtt']:
            safe_config['mqtt']['password'] = '***'
        if 'wifi_password' in safe_config:
            safe_config['wifi_password'] = '***'
            
        return jsonify({
            "config": safe_config,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get config: {e}"}), 500

@app.route('/api/master/config', methods=['POST'])
def api_update_config():
    """API endpoint for updating configuration parameters"""
    global config, master_system
    
    try:
        if not config:
            return jsonify({"error": "Configuration not available"}), 503
            
        data = request.get_json()
        if not data or 'config' not in data:
            return jsonify({"error": "Invalid request data"}), 400
        
        new_config = data['config']
        
        # Validate required fields
        required_fields = ['master_id', 'gpio_pin', 'pulse_duration_ms', 'exposure_us', 'timeout_ms']
        for field in required_fields:
            if field not in new_config:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Validate numeric ranges
        validations = {
            'gpio_pin': (1, 40),
            'pulse_duration_ms': (1, 5000),
            'pulse_interval_ms': (100, 10000),
            'exposure_us': (100, 100000),
            'timeout_ms': (1000, 30000),
            'startup_delay': (0, 60),
            'web_port': (1024, 65535)
        }
        
        for field, (min_val, max_val) in validations.items():
            if field in new_config:
                try:
                    value = int(new_config[field])
                    if not (min_val <= value <= max_val):
                        return jsonify({"error": f"{field} must be between {min_val} and {max_val}"}), 400
                except (ValueError, TypeError):
                    return jsonify({"error": f"{field} must be a valid number"}), 400
        
        # Validate MQTT configuration if present
        if 'mqtt' in new_config:
            mqtt_config = new_config['mqtt']
            if 'broker_port' in mqtt_config:
                try:
                    port = int(mqtt_config['broker_port'])
                    if not (1 <= port <= 65535):
                        return jsonify({"error": "MQTT broker port must be between 1 and 65535"}), 400
                except (ValueError, TypeError):
                    return jsonify({"error": "MQTT broker port must be a valid number"}), 400
        
        # Save configuration
        config_file = Path(__file__).parent / "master_config.json"
        backup_file = Path(__file__).parent / f"master_config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Create backup of current config
        with open(backup_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Update and save new config
        config.update(new_config)
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logging.info(f"Configuration updated via web interface. Backup saved to: {backup_file}")
        
        return jsonify({
            "status": "success",
            "message": "Configuration updated successfully",
            "backup_file": str(backup_file),
            "requires_restart": True
        })
        
    except Exception as e:
        logging.error(f"Failed to update config: {e}")
        return jsonify({"error": f"Failed to update config: {e}"}), 500

@app.route('/api/master/restart', methods=['POST'])
def api_restart_system():
    """API endpoint to restart the master system"""
    global master_system
    
    try:
        if master_system:
            # Schedule restart in a separate thread
            def restart_system():
                time.sleep(2)  # Give time for response to be sent
                logging.info("System restart requested via web interface")
                master_system.cleanup()
                os._exit(0)  # Force exit to trigger systemd restart
            
            thread = threading.Thread(target=restart_system, daemon=True)
            thread.start()
            
            return jsonify({
                "status": "success",
                "message": "System restart initiated. Please wait 30 seconds before refreshing."
            })
        else:
            return jsonify({"error": "Master system not available"}), 503
            
    except Exception as e:
        return jsonify({"error": f"Failed to restart system: {e}"}), 500

def create_master_templates():
    """Create HTML templates for the master web interface"""
    templates_dir = Path(__file__).parent / "templates"
    templates_dir.mkdir(exist_ok=True)
    
    # Create master dashboard template
    dashboard_template = '''<!DOCTYPE html>
<html>
<head>
    <title>Master Helmet Camera System</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        .status-item { padding: 15px; border-radius: 4px; text-align: center; }
        .status-online { background-color: #d4edda; color: #155724; }
        .status-offline { background-color: #f8d7da; color: #721c24; }
        .status-warning { background-color: #fff3cd; color: #856404; }
        .slaves-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }
        .slave-card { border: 1px solid #ddd; border-radius: 8px; padding: 15px; }
        .slave-online { border-color: #28a745; background-color: #f8fff9; }
        .slave-offline { border-color: #dc3545; background-color: #fff8f8; }
        .slave-timeout { border-color: #ffc107; background-color: #fffdf7; }
        .slave-error { border-color: #dc3545; background-color: #fff8f8; }
        .slave-unknown { border-color: #6c757d; background-color: #f8f9fa; }
        .status-badge { padding: 2px 8px; border-radius: 4px; color: white; font-size: 12px; font-weight: bold; }
        .status-badge.online { background-color: #28a745; }
        .status-badge.offline { background-color: #dc3545; }
        .status-badge.timeout { background-color: #ffc107; color: black; }
        .status-badge.error { background-color: #dc3545; }
        .status-badge.unknown { background-color: #6c757d; }
        .control-panel { background: #e9ecef; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
        .btn-primary { background: #007bff; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-warning { background: #ffc107; color: black; }
        .btn-danger { background: #dc3545; color: white; }
        .btn:hover { opacity: 0.8; }
        .input-group { margin: 10px 0; }
        .input-group label { display: inline-block; width: 120px; }
        .input-group input { padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .input-group select { padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .input-group textarea { padding: 8px; border: 1px solid #ddd; border-radius: 4px; width: 300px; resize: vertical; }
        .logs { font-family: monospace; font-size: 12px; max-height: 400px; overflow-y: scroll; background: #f8f9fa; padding: 15px; border-radius: 4px; }
        h3 { color: #495057; margin: 20px 0 10px 0; border-bottom: 2px solid #e9ecef; padding-bottom: 5px; }
        .config-section { margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 6px; }
        .warning-text { color: #856404; font-size: 12px; font-style: italic; }
        .success-text { color: #155724; }
        .error-text { color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Master Helmet Camera System</h1>
        
        <div class="card">
            <h2>System Status</h2>
            <div id="masterStatus" class="status-grid">
                <!-- Will be populated by JavaScript -->
            </div>
            <button onclick="refreshStatus()" class="btn btn-primary">Refresh Status</button>
        </div>
        
        <div class="card">
            <h2>Capture Control</h2>
            <div class="control-panel">
                <div class="input-group">
                    <label>Photo Count:</label>
                    <input type="number" id="photoCount" value="1" min="1" max="100">
                </div>
                <div class="input-group">
                    <label>Interval (seconds):</label>
                    <input type="number" id="photoInterval" value="5" min="1" max="60">
                </div>
                <button onclick="startCapture()" class="btn btn-success">Start Capture</button>
                <button onclick="quickCapture(1)" class="btn btn-primary">Quick Single</button>
                <button onclick="quickCapture(3)" class="btn btn-warning">Quick Burst (3)</button>
            </div>
            <div id="captureStatus"></div>
        </div>
        
        <div class="card">
            <h2>Statistics Summary</h2>
            <div id="statisticsStatus" class="status-grid">
                <!-- Will be populated by JavaScript -->
            </div>
        </div>
        
        <div class="card">
            <h2>Connected Slaves</h2>
            <div id="slavesStatus" class="slaves-grid">
                <!-- Will be populated by JavaScript -->
            </div>
        </div>
        
        <div class="card">
            <h2>System Configuration</h2>
            <div class="control-panel">
                <h3>GPIO Settings</h3>
                <div class="input-group">
                    <label>GPIO Pin:</label>
                    <input type="number" id="config_gpio_pin" min="1" max="40" title="GPIO pin for pulse generation (1-40)">
                </div>
                <div class="input-group">
                    <label>Pulse Duration (ms):</label>
                    <input type="number" id="config_pulse_duration_ms" min="1" max="5000" title="Duration of GPIO pulse in milliseconds (1-5000)">
                </div>
                <div class="input-group">
                    <label>Pulse Interval (ms):</label>
                    <input type="number" id="config_pulse_interval_ms" min="100" max="10000" title="Interval between pulses in milliseconds (100-10000)">
                </div>
                
                <h3>Camera Settings</h3>
                <div class="input-group">
                    <label>Exposure (μs):</label>
                    <input type="number" id="config_exposure_us" min="100" max="100000" title="Camera exposure time in microseconds (100-100000)">
                </div>
                <div class="input-group">
                    <label>Timeout (ms):</label>
                    <input type="number" id="config_timeout_ms" min="1000" max="30000" title="Command timeout in milliseconds (1000-30000)">
                </div>
                <div class="input-group">
                    <label>Photo Base Dir:</label>
                    <input type="text" id="config_photo_base_dir" title="Base directory for photo storage">
                </div>
                
                <h3>System Settings</h3>
                <div class="input-group">
                    <label>Master ID:</label>
                    <input type="text" id="config_master_id" title="Unique identifier for this master">
                </div>
                <div class="input-group">
                    <label>Startup Delay (s):</label>
                    <input type="number" id="config_startup_delay" min="0" max="60" title="Delay before system starts in seconds (0-60)">
                </div>
                <div class="input-group">
                    <label>Web Port:</label>
                    <input type="number" id="config_web_port" min="1024" max="65535" title="Port for web interface (1024-65535)">
                </div>
                <div class="input-group">
                    <label>Log Directory:</label>
                    <input type="text" id="config_log_dir" title="Directory for log files">
                </div>
                
                <h3>WiFi Settings</h3>
                <div class="input-group">
                    <label>WiFi SSID:</label>
                    <input type="text" id="config_wifi_ssid" title="WiFi network name">
                </div>
                <div class="input-group">
                    <label>WiFi Password:</label>
                    <input type="password" id="config_wifi_password" title="WiFi network password">
                </div>
                
                <h3>MQTT Settings</h3>
                <div class="input-group">
                    <label>Broker Host:</label>
                    <input type="text" id="config_mqtt_broker_host" title="MQTT broker IP address or hostname">
                </div>
                <div class="input-group">
                    <label>Broker Port:</label>
                    <input type="number" id="config_mqtt_broker_port" min="1" max="65535" title="MQTT broker port (1-65535)">
                </div>
                <div class="input-group">
                    <label>Command Topic:</label>
                    <input type="text" id="config_mqtt_topic_commands" title="MQTT topic for sending commands">
                </div>
                <div class="input-group">
                    <label>Response Topic:</label>
                    <input type="text" id="config_mqtt_topic_responses" title="MQTT topic for receiving responses">
                </div>
                <div class="input-group">
                    <label>Keepalive (s):</label>
                    <input type="number" id="config_mqtt_keepalive" min="10" max="300" title="MQTT keepalive interval in seconds">
                </div>
                <div class="input-group">
                    <label>QoS:</label>
                    <select id="config_mqtt_qos" title="MQTT Quality of Service level">
                        <option value="0">0 - At most once</option>
                        <option value="1">1 - At least once</option>
                        <option value="2">2 - Exactly once</option>
                    </select>
                </div>
                
                <h3>Slave Configuration</h3>
                <div class="input-group">
                    <label>Slaves (one per line):</label>
                    <textarea id="config_slaves" rows="4" placeholder="rpihelmet2&#10;rpihelmet3" title="List of slave hostnames, one per line"></textarea>
                </div>
                
                <div style="margin-top: 20px;">
                    <button onclick="loadConfiguration()" class="btn btn-primary">Load Current Config</button>
                    <button onclick="saveConfiguration()" class="btn btn-success">Save Configuration</button>
                    <button onclick="restartSystem()" class="btn btn-danger">Restart System</button>
                </div>
                <div id="configStatus" style="margin-top: 10px;"></div>
            </div>
        </div>
        
        <div class="card">
            <h2>System Logs</h2>
            <div id="logs" class="logs">
                <!-- Will be populated by JavaScript -->
            </div>
        </div>
    </div>

    <script>
        async function fetchJSON(url, options = {}) {
            try {
                const response = await fetch(url, options);
                return await response.json();
            } catch (error) {
                console.error('Fetch error:', error);
                return null;
            }
        }
        
        async function refreshStatus() {
            // Master status
            const masterStatus = await fetchJSON('/api/master/status');
            if (masterStatus) {
                const stats = masterStatus.statistics || {};
                document.getElementById('masterStatus').innerHTML = `
                    <div class="status-item ${masterStatus.mqtt_connected ? 'status-online' : 'status-offline'}">
                        <strong>MQTT Connection</strong><br>
                        ${masterStatus.mqtt_connected ? 'Connected' : 'Disconnected'}
                    </div>
                    <div class="status-item status-online">
                        <strong>Master ID</strong><br>
                        ${masterStatus.master_id || 'Unknown'}
                    </div>
                    <div class="status-item status-online">
                        <strong>Session</strong><br>
                        ${masterStatus.session_name || 'No active session'}
                    </div>
                    <div class="status-item ${masterStatus.imu_available ? 'status-online' : 'status-warning'}">
                        <strong>IMU Sensor</strong><br>
                        ${masterStatus.imu_available ? 'Available' : 'Not Available'}
                    </div>
                    <div class="status-item ${masterStatus.display_available ? 'status-online' : 'status-warning'}">
                        <strong>OLED Display</strong><br>
                        ${masterStatus.display_available ? 'Available' : 'Not Available'}
                    </div>
                    <div class="status-item ${masterStatus.pending_commands > 0 ? 'status-warning' : 'status-online'}">
                        <strong>Pending Commands</strong><br>
                        ${masterStatus.pending_commands || 0}
                    </div>
                    <div class="status-item status-online">
                        <strong>Commands Sent</strong><br>
                        ${stats.total_commands || 0}
                    </div>
                    <div class="status-item status-online">
                        <strong>Master Photos</strong><br>
                        ${stats.master_captures || 0} / ${(stats.master_captures + stats.master_capture_failures) || 0}
                    </div>
                    <div class="status-item ${masterStatus.running ? 'status-online' : 'status-offline'}">
                        <strong>System Status</strong><br>
                        ${masterStatus.running ? 'Running' : 'Stopped'}
                    </div>
                `;
            }
            
            // Statistics summary
            const statisticsData = await fetchJSON('/api/master/statistics');
            if (statisticsData && statisticsData.global_stats) {
                const gStats = statisticsData.global_stats;
                const totalBoards = Object.keys(statisticsData.board_stats || {}).length;
                const onlineBoards = Object.values(statisticsData.board_stats || {}).filter(s => s.status === 'online').length;
                
                document.getElementById('statisticsStatus').innerHTML = `
                    <div class="status-item status-online">
                        <strong>Total Commands</strong><br>
                        ${gStats.total_commands || 0}
                    </div>
                    <div class="status-item ${gStats.successful_responses > 0 ? 'status-online' : 'status-warning'}">
                        <strong>Success Rate</strong><br>
                        ${gStats.total_commands > 0 ? Math.round((gStats.successful_responses / gStats.total_commands) * 100) : 0}%
                    </div>
                    <div class="status-item ${gStats.failed_responses > 0 ? 'status-warning' : 'status-online'}">
                        <strong>Failures</strong><br>
                        ${gStats.failed_responses || 0}
                    </div>
                    <div class="status-item ${gStats.timeout_responses > 0 ? 'status-warning' : 'status-online'}">
                        <strong>Timeouts</strong><br>
                        ${gStats.timeout_responses || 0}
                    </div>
                    <div class="status-item status-online">
                        <strong>Master Photos</strong><br>
                        ${gStats.master_captures || 0}
                    </div>
                    <div class="status-item ${onlineBoards === totalBoards ? 'status-online' : 'status-warning'}">
                        <strong>Boards Online</strong><br>
                        ${onlineBoards}/${totalBoards}
                    </div>
                `;
            }
            
            // Slaves status
            const slavesStatus = await fetchJSON('/api/master/slaves');
            if (slavesStatus) {
                const slavesHtml = slavesStatus.slaves.map(slave => `
                    <div class="slave-card slave-${slave.status}">
                        <h3>${slave.slave_id}</h3>
                        <p><strong>Status:</strong> <span class="status-badge ${slave.status}">${slave.status.toUpperCase()}</span></p>
                        <p><strong>Commands:</strong> ${slave.total_commands || 0}</p>
                        <p><strong>Success Rate:</strong> ${slave.total_commands > 0 ? Math.round((slave.successful_responses / slave.total_commands) * 100) : 0}%</p>
                        <p><strong>Failures:</strong> ${slave.failed_responses || 0}</p>
                        <p><strong>Timeouts:</strong> ${slave.timeout_responses || 0}</p>
                        <p><strong>Avg Response:</strong> ${slave.avg_response_time_ms || 0}ms</p>
                        ${slave.last_seen ? `<p><strong>Last Seen:</strong> ${new Date(slave.last_seen).toLocaleString()}</p>` : '<p><strong>Last Seen:</strong> Never</p>'}
                        <button onclick="viewSlaveDetails('${slave.slave_id}')" class="btn btn-primary">View Details</button>
                    </div>
                `).join('');
                
                document.getElementById('slavesStatus').innerHTML = slavesHtml || '<p>No slaves configured</p>';
            }
            
            // Logs
            const logs = await fetchJSON('/api/master/logs');
            if (logs && logs.lines) {
                document.getElementById('logs').innerHTML = logs.lines.slice(-30).join('<br>');
                document.getElementById('logs').scrollTop = document.getElementById('logs').scrollHeight;
            }
        }
        
        async function startCapture() {
            const count = parseInt(document.getElementById('photoCount').value);
            const interval = parseInt(document.getElementById('photoInterval').value);
            
            const result = await fetchJSON('/api/master/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ count, interval })
            });
            
            if (result) {
                if (result.error) {
                    document.getElementById('captureStatus').innerHTML = `<div style="color: red;">ERROR: ${result.error}</div>`;
                } else {
                    document.getElementById('captureStatus').innerHTML = `<div style="color: green;">SUCCESS: ${result.message}</div>`;
                    setTimeout(() => {
                        document.getElementById('captureStatus').innerHTML = '';
                    }, 5000);
                }
            }
        }
        
        async function quickCapture(count) {
            document.getElementById('photoCount').value = count;
            await startCapture();
        }
        
        function viewSlaveDetails(slaveId) {
            // Open slave web interface in new tab
            // Assuming slaves use port 8080
            const slaveUrl = `http://${slaveId}:8080`;
            window.open(slaveUrl, '_blank');
        }
        
        async function loadConfiguration() {
            const configData = await fetchJSON('/api/master/config');
            if (configData && configData.config) {
                const config = configData.config;
                
                // Populate GPIO settings
                document.getElementById('config_gpio_pin').value = config.gpio_pin || '';
                document.getElementById('config_pulse_duration_ms').value = config.pulse_duration_ms || '';
                document.getElementById('config_pulse_interval_ms').value = config.pulse_interval_ms || '';
                
                // Populate camera settings
                document.getElementById('config_exposure_us').value = config.exposure_us || '';
                document.getElementById('config_timeout_ms').value = config.timeout_ms || '';
                document.getElementById('config_photo_base_dir').value = config.photo_base_dir || '';
                
                // Populate system settings
                document.getElementById('config_master_id').value = config.master_id || '';
                document.getElementById('config_startup_delay').value = config.startup_delay || '';
                document.getElementById('config_web_port').value = config.web_port || '';
                document.getElementById('config_log_dir').value = config.log_dir || '';
                
                // Populate WiFi settings
                document.getElementById('config_wifi_ssid').value = config.wifi_ssid || '';
                document.getElementById('config_wifi_password').value = config.wifi_password === '***' ? '' : (config.wifi_password || '');
                
                // Populate MQTT settings
                if (config.mqtt) {
                    document.getElementById('config_mqtt_broker_host').value = config.mqtt.broker_host || '';
                    document.getElementById('config_mqtt_broker_port').value = config.mqtt.broker_port || '';
                    document.getElementById('config_mqtt_topic_commands').value = config.mqtt.topic_commands || '';
                    document.getElementById('config_mqtt_topic_responses').value = config.mqtt.topic_responses || '';
                    document.getElementById('config_mqtt_keepalive').value = config.mqtt.keepalive || '';
                    document.getElementById('config_mqtt_qos').value = config.mqtt.qos || '';
                }
                
                // Populate slaves
                if (config.slaves && Array.isArray(config.slaves)) {
                    document.getElementById('config_slaves').value = config.slaves.join('\n');
                }
                
                document.getElementById('configStatus').innerHTML = '<div style="color: green;">Configuration loaded successfully</div>';
                setTimeout(() => document.getElementById('configStatus').innerHTML = '', 3000);
            } else {
                document.getElementById('configStatus').innerHTML = '<div style="color: red;">Failed to load configuration</div>';
            }
        }
        
        async function saveConfiguration() {
            // Collect all configuration values
            const newConfig = {
                master_id: document.getElementById('config_master_id').value,
                gpio_pin: parseInt(document.getElementById('config_gpio_pin').value),
                pulse_duration_ms: parseInt(document.getElementById('config_pulse_duration_ms').value),
                pulse_interval_ms: parseInt(document.getElementById('config_pulse_interval_ms').value),
                exposure_us: parseInt(document.getElementById('config_exposure_us').value),
                timeout_ms: parseInt(document.getElementById('config_timeout_ms').value),
                photo_base_dir: document.getElementById('config_photo_base_dir').value,
                startup_delay: parseInt(document.getElementById('config_startup_delay').value),
                web_port: parseInt(document.getElementById('config_web_port').value),
                log_dir: document.getElementById('config_log_dir').value,
                wifi_ssid: document.getElementById('config_wifi_ssid').value,
                mqtt: {
                    broker_host: document.getElementById('config_mqtt_broker_host').value,
                    broker_port: parseInt(document.getElementById('config_mqtt_broker_port').value),
                    topic_commands: document.getElementById('config_mqtt_topic_commands').value,
                    topic_responses: document.getElementById('config_mqtt_topic_responses').value,
                    keepalive: parseInt(document.getElementById('config_mqtt_keepalive').value),
                    qos: parseInt(document.getElementById('config_mqtt_qos').value)
                }
            };
            
            // Only include WiFi password if it was changed
            const wifiPassword = document.getElementById('config_wifi_password').value;
            if (wifiPassword && wifiPassword !== '***') {
                newConfig.wifi_password = wifiPassword;
            }
            
            // Parse slaves list
            const slavesText = document.getElementById('config_slaves').value;
            if (slavesText.trim()) {
                newConfig.slaves = slavesText.split('\n').map(s => s.trim()).filter(s => s.length > 0);
            } else {
                newConfig.slaves = [];
            }
            
            // Validate required fields
            const requiredFields = ['master_id', 'gpio_pin', 'pulse_duration_ms', 'exposure_us', 'timeout_ms'];
            const missingFields = requiredFields.filter(field => !newConfig[field]);
            if (missingFields.length > 0) {
                document.getElementById('configStatus').innerHTML = `<div style="color: red;">Missing required fields: ${missingFields.join(', ')}</div>`;
                return;
            }
            
            // Send configuration update
            const result = await fetchJSON('/api/master/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config: newConfig })
            });
            
            if (result) {
                if (result.error) {
                    document.getElementById('configStatus').innerHTML = `<div style="color: red;">ERROR: ${result.error}</div>`;
                } else {
                    document.getElementById('configStatus').innerHTML = `<div style="color: green;">SUCCESS: ${result.message}<br>Backup saved: ${result.backup_file}<br><strong>System restart required!</strong></div>`;
                }
            } else {
                document.getElementById('configStatus').innerHTML = '<div style="color: red;">Failed to save configuration</div>';
            }
        }
        
        async function restartSystem() {
            if (!confirm('Are you sure you want to restart the system? This will disconnect all current operations.')) {
                return;
            }
            
            const result = await fetchJSON('/api/master/restart', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (result) {
                if (result.error) {
                    document.getElementById('configStatus').innerHTML = `<div style="color: red;">ERROR: ${result.error}</div>`;
                } else {
                    document.getElementById('configStatus').innerHTML = `<div style="color: orange;">RESTARTING: ${result.message}</div>`;
                    // Disable all buttons during restart
                    const buttons = document.querySelectorAll('button');
                    buttons.forEach(btn => btn.disabled = true);
                }
            }
        }
        
        // Auto-refresh every 10 seconds
        setInterval(refreshStatus, 10000);
        
        // Initial load
        refreshStatus();
        loadConfiguration();  // Load config on page load
    </script>
</body>
</html>'''
    
    with open(templates_dir / "master_dashboard.html", "w") as f:
        f.write(dashboard_template)

def setup_master_web_server(master_system_instance, config_instance):
    """Setup the master web server with system instances"""
    global master_system, config
    
    master_system = master_system_instance
    config = config_instance
    
    # Create templates
    create_master_templates()
    
    # Configure Flask logging
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

def run_master_web_server(host='0.0.0.0', port=8081, debug=False):
    """Run the Flask master web server"""
    app.run(host=host, port=port, debug=debug, use_reloader=False)

if __name__ == "__main__":
    # Standalone mode for testing
    try:
        from camera.factories import ConfigLoader
        config = ConfigLoader.load_config("master_config.json")
        create_master_templates()
        
        print(f"Starting master web server...")
        print(f"Open http://localhost:8081 in your browser")
        
        app.run(host='0.0.0.0', port=8081, debug=True)
        
    except Exception as e:
        print(f"Failed to start master web server: {e}") 