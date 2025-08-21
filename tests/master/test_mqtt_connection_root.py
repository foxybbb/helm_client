#!/usr/bin/env python3
"""
MQTT Connection Test Script

Test script to verify MQTT broker connectivity before running the main applications.
"""

import time
import json
import logging
import paho.mqtt.client as mqtt
from pathlib import Path

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_mqtt_connection():
    """Test MQTT broker connection"""
    
    # Default MQTT configuration
    mqtt_config = {
        "broker_host": "192.168.1.100",  # Change this to your MQTT broker IP
        "broker_port": 1883,
        "topic_test": "helmet/test",
        "keepalive": 60
    }
    
    print("MQTT Connection Test")
    print("===================")
    print(f"Broker: {mqtt_config['broker_host']}:{mqtt_config['broker_port']}")
    print(f"Test topic: {mqtt_config['topic_test']}")
    print()
    
    # Connection status
    connected = False
    messages_received = []
    
    def on_connect(client, userdata, flags, rc):
        nonlocal connected
        if rc == 0:
            connected = True
            logger.info("Successfully connected to MQTT broker")
            # Subscribe to test topic
            client.subscribe(mqtt_config["topic_test"])
            logger.info(f"Subscribed to {mqtt_config['topic_test']}")
        else:
            logger.error(f"Failed to connect to MQTT broker (code {rc})")
            connected = False
    
    def on_message(client, userdata, msg):
        try:
            message = msg.payload.decode('utf-8')
            logger.info(f"Received message: {message}")
            messages_received.append(message)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def on_disconnect(client, userdata, rc):
        nonlocal connected
        connected = False
        logger.warning(f"Disconnected from MQTT broker (code {rc})")
    
    # Create MQTT client
    client = mqtt.Client(client_id="mqtt_test_client")
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    try:
        # Connect to broker
        logger.info("Connecting to MQTT broker...")
        client.connect(mqtt_config["broker_host"], mqtt_config["broker_port"], mqtt_config["keepalive"])
        
        # Start network loop
        client.loop_start()
        
        # Wait for connection
        for i in range(10):
            if connected:
                break
            time.sleep(0.5)
            if i == 4:
                logger.info("Still connecting...")
        
        if not connected:
            logger.error("Failed to connect within timeout")
            return False
        
        # Test publishing
        logger.info("Testing message publishing...")
        test_message = {"test": "Hello from MQTT test", "timestamp": time.time()}
        test_payload = json.dumps(test_message)
        
        result = client.publish(mqtt_config["topic_test"], test_payload)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info("Message published successfully")
        else:
            logger.error(f"Failed to publish message (code {result.rc})")
        
        # Wait for message to be received
        logger.info("Waiting for message to be received...")
        time.sleep(2)
        
        if messages_received:
            logger.info("Message received successfully")
            logger.info("MQTT test completed successfully!")
            return True
        else:
            logger.warning("Message was published but not received")
            return False
        
    except Exception as e:
        logger.error(f"MQTT test failed: {e}")
        return False
    finally:
        try:
            client.loop_stop()
            client.disconnect()
        except:
            pass

def main():
    """Run MQTT connection test"""
    print("This script tests MQTT broker connectivity.")
    print("Make sure your MQTT broker (e.g., Mosquitto) is running.")
    print()
    
    broker_ip = input("Enter MQTT broker IP address (default: 192.168.1.100): ").strip()
    if not broker_ip:
        broker_ip = "192.168.1.100"
    
    # Update the broker IP in the test
    global mqtt_config
    test_mqtt_connection.__globals__['mqtt_config'] = {
        "broker_host": broker_ip,
        "broker_port": 1883,
        "topic_test": "helmet/test",
        "keepalive": 60
    }
    
    success = test_mqtt_connection()
    
    print()
    if success:
        print("MQTT broker is working correctly!")
        print("You can now run the master and slave applications.")
    else:
        print("MQTT test failed. Please check:")
        print("1. MQTT broker is running and accessible")
        print("2. Network connectivity")
        print("3. Firewall settings")
        print("4. MQTT broker configuration")

if __name__ == "__main__":
    main() 