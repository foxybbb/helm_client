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
        
        if not master_system or not hasattr(master_system, 'capture_single_photo'):
            return jsonify({"error": "Master system not ready"}), 503
        
        # Execute capture sequence using single photo captures
        def execute_capture():
            try:
                for i in range(count):
                    command_id, success = master_system.capture_single_photo(f"web_sequence_{i+1}")
                    if i < count - 1:  # Don't wait after last capture
                        time.sleep(interval)
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

@app.route('/api/master/single_capture', methods=['POST'])
def api_single_capture():
    """API endpoint for single photo capture with extra session info"""
    global master_system
    
    try:
        if not master_system or not hasattr(master_system, 'web_capture_single_photo'):
            return jsonify({"error": "Master system not ready"}), 503
        
        # Execute single capture in background thread
        result = {"command_id": None, "success": False, "error": None}
        
        def execute_single_capture():
            try:
                command_id, success = master_system.web_capture_single_photo()
                result["command_id"] = command_id
                result["success"] = success
                web_status["total_commands_sent"] += 1
            except Exception as e:
                result["error"] = str(e)
                logging.error(f"Error executing single capture: {e}")
        
        thread = threading.Thread(target=execute_single_capture, daemon=True)
        thread.start()
        thread.join(timeout=2)  # Wait briefly for result
        
        web_status["last_session"] = datetime.now().isoformat()
        
        if result["error"]:
            return jsonify({"error": result["error"]}), 500
        
        return jsonify({
            "status": "completed" if result["command_id"] else "failed",
            "command_id": result["command_id"],
            "master_success": result["success"],
            "message": f"Single photo capture {'completed' if result['command_id'] else 'failed'}"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to execute single capture: {e}"}), 500

@app.route('/api/master/triggers/status')
def api_triggers_status():
    """API endpoint for automatic capture triggers status"""
    global master_system, config
    
    try:
        if not master_system or not hasattr(master_system, 'auto_capture'):
            return jsonify({"error": "Master system not ready"}), 503
        
        triggers_config = config.get("capture_triggers", {})
        auto_capture = master_system.auto_capture
        
        status = {
            "timer": {
                "enabled": triggers_config.get("timer_enabled", False),
                "running": auto_capture.timer_running,
                "interval_seconds": triggers_config.get("timer_interval_seconds", 5)
            },
            "imu_movement": {
                "enabled": triggers_config.get("imu_movement_enabled", False),
                "running": auto_capture.imu_monitoring,
                "threshold": triggers_config.get("imu_movement_threshold", 2.0),
                "cooldown_seconds": triggers_config.get("imu_movement_cooldown_seconds", 2.0),
                "sensor_available": master_system.imu_sensor.available if hasattr(master_system, 'imu_sensor') else False
            },
            "gpio_pin20": {
                "enabled": triggers_config.get("gpio_pin20_enabled", False),
                "running": auto_capture.gpio20_monitoring,
                "pin": triggers_config.get("gpio_pin20_pin", 20),
                "initialized": auto_capture.gpio20_initialized
            }
        }
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({"error": f"Failed to get triggers status: {e}"}), 500

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
    """Get recent master log entries"""
    try:
        log_lines = []
        
        # Try to read from the application log
        log_dir = Path.home() / "helmet_camera_logs"
        if log_dir.exists():
            # Get the most recent log file
            log_files = list(log_dir.glob("helmet_camera_*.log"))
            if log_files:
                latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
                
                # Read last 100 lines
                with open(latest_log, 'r') as f:
                    lines = f.readlines()
                    log_lines = lines[-100:] if len(lines) > 100 else lines
        
        return jsonify({
            "lines": [line.strip() for line in log_lines],
            "total_lines": len(log_lines)
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to read logs: {e}"})

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
        .logs { font-family: monospace; font-size: 12px; max-height: 400px; overflow-y: scroll; background: #f8f9fa; padding: 15px; border-radius: 4px; }
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
                <button onclick="singleWebCapture()" class="btn btn-danger">Web Single Photo</button>
            </div>
            <div id="captureStatus"></div>
        </div>
        
        <div class="card">
            <h2>Automatic Triggers Status</h2>
            <div id="triggersStatus" class="status-grid">
                <!-- Will be populated by JavaScript -->
            </div>
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
            
            // Triggers status
            const triggersStatus = await fetchJSON('/api/master/triggers/status');
            if (triggersStatus) {
                document.getElementById('triggersStatus').innerHTML = `
                    <div class="status-item ${triggersStatus.timer.enabled ? (triggersStatus.timer.running ? 'status-online' : 'status-warning') : 'status-offline'}">
                        <strong>Timer Capture</strong><br>
                        ${triggersStatus.timer.enabled ? (triggersStatus.timer.running ? `Running (${triggersStatus.timer.interval_seconds}s)` : 'Enabled (Stopped)') : 'Disabled'}
                    </div>
                    <div class="status-item ${triggersStatus.imu_movement.enabled ? (triggersStatus.imu_movement.running ? 'status-online' : 'status-warning') : 'status-offline'}">
                        <strong>Movement Detection</strong><br>
                        ${triggersStatus.imu_movement.enabled ? (triggersStatus.imu_movement.sensor_available ? (triggersStatus.imu_movement.running ? `Running (${triggersStatus.imu_movement.threshold} m/s²)` : 'Enabled (Stopped)') : 'No IMU Sensor') : 'Disabled'}
                    </div>
                    <div class="status-item ${triggersStatus.gpio_pin20.enabled ? (triggersStatus.gpio_pin20.running ? 'status-online' : 'status-warning') : 'status-offline'}">
                        <strong>GPIO Pin ${triggersStatus.gpio_pin20.pin}</strong><br>
                        ${triggersStatus.gpio_pin20.enabled ? (triggersStatus.gpio_pin20.running ? `Running (${triggersStatus.gpio_pin20.initialized ? 'Initialized' : 'Not Initialized'})` : 'Enabled (Stopped)') : 'Disabled'}
                    </div>
                `;
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
        
        async function singleWebCapture() {
            const result = await fetchJSON('/api/master/single_capture', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            
            if (result) {
                if (result.error) {
                    document.getElementById('captureStatus').innerHTML = `<div style="color: red;">ERROR: ${result.error}</div>`;
                } else {
                    document.getElementById('captureStatus').innerHTML = `<div style="color: green;">SUCCESS: ${result.message} (Command ID: ${result.command_id})</div>`;
                    setTimeout(() => {
                        document.getElementById('captureStatus').innerHTML = '';
                    }, 5000);
                }
            }
        }
        
        function viewSlaveDetails(slaveId) {
            // Open slave web interface in new tab
            // Assuming slaves use port 8080
            const slaveUrl = `http://${slaveId}:8080`;
            window.open(slaveUrl, '_blank');
        }
        
        // Auto-refresh every 10 seconds
        setInterval(refreshStatus, 10000);
        
        // Initial load
        refreshStatus();
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