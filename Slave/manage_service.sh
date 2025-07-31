#!/bin/bash

# Quick Service Management Script for Helmet Camera Slave
# Provides easy commands for common service operations

SERVICE_NAME="helmet-camera-slave"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if service exists
check_service() {
    if ! systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
        print_error "Service '$SERVICE_NAME' is not installed"
        echo "Run './install_service.sh' to install the service first"
        exit 1
    fi
}

# Show service status
show_status() {
    print_status "Service Status:"
    sudo systemctl status "$SERVICE_NAME" --no-pager -l
    
    echo
    print_status "Service is $(sudo systemctl is-enabled $SERVICE_NAME) for automatic startup"
    
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "Service is currently running"
    else
        print_error "Service is not running"
    fi
}

# Show recent logs
show_logs() {
    local lines=${1:-20}
    print_status "Recent logs (last $lines lines):"
    sudo journalctl -u "$SERVICE_NAME" --no-pager -n "$lines"
}

# Follow logs in real-time
follow_logs() {
    print_status "Following logs in real-time (Ctrl+C to stop):"
    sudo journalctl -u "$SERVICE_NAME" -f
}

# Start service
start_service() {
    print_status "Starting service..."
    if sudo systemctl start "$SERVICE_NAME"; then
        print_success "Service started successfully"
    else
        print_error "Failed to start service"
        show_logs 5
        exit 1
    fi
}

# Stop service
stop_service() {
    print_status "Stopping service..."
    if sudo systemctl stop "$SERVICE_NAME"; then
        print_success "Service stopped successfully"
    else
        print_error "Failed to stop service"
        exit 1
    fi
}

# Restart service
restart_service() {
    print_status "Restarting service..."
    if sudo systemctl restart "$SERVICE_NAME"; then
        print_success "Service restarted successfully"
        sleep 2
        show_status
    else
        print_error "Failed to restart service"
        show_logs 10
        exit 1
    fi
}

# Enable service (auto-start on boot)
enable_service() {
    print_status "Enabling service for automatic startup..."
    if sudo systemctl enable "$SERVICE_NAME"; then
        print_success "Service enabled for automatic startup"
    else
        print_error "Failed to enable service"
        exit 1
    fi
}

# Disable service
disable_service() {
    print_status "Disabling service automatic startup..."
    if sudo systemctl disable "$SERVICE_NAME"; then
        print_success "Service disabled from automatic startup"
    else
        print_error "Failed to disable service"
        exit 1
    fi
}

# Show help
show_help() {
    echo "Helmet Camera Slave Service Manager"
    echo "=================================="
    echo
    echo "Usage: $0 <command>"
    echo
    echo "Commands:"
    echo "  status     - Show service status and state"
    echo "  start      - Start the service"
    echo "  stop       - Stop the service"
    echo "  restart    - Restart the service"
    echo "  enable     - Enable automatic startup on boot"
    echo "  disable    - Disable automatic startup"
    echo "  logs [N]   - Show last N log lines (default: 20)"
    echo "  follow     - Follow logs in real-time"
    echo "  quick      - Quick status overview"
    echo "  help       - Show this help message"
    echo
    echo "Examples:"
    echo "  $0 status          # Show detailed status"
    echo "  $0 restart         # Restart service"
    echo "  $0 logs 50         # Show last 50 log lines"
    echo "  $0 follow          # Monitor logs in real-time"
}

# Quick status overview
quick_status() {
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}● Service is running${NC}"
    else
        echo -e "${RED}● Service is stopped${NC}"
    fi
    
    if sudo systemctl is-enabled --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}● Auto-start enabled${NC}"
    else
        echo -e "${YELLOW}● Auto-start disabled${NC}"
    fi
    
    # Last restart time
    local last_start=$(sudo systemctl show "$SERVICE_NAME" --property=ActiveEnterTimestamp --value)
    if [ -n "$last_start" ] && [ "$last_start" != "n/a" ]; then
        echo -e "${BLUE}● Last started: $last_start${NC}"
    fi
    
    # Check for recent failures
    local failed_count=$(sudo journalctl -u "$SERVICE_NAME" --since "1 hour ago" --grep "failed\|error\|exception" --no-pager | wc -l)
    if [ "$failed_count" -gt 0 ]; then
        echo -e "${RED}● $failed_count error(s) in last hour${NC}"
    else
        echo -e "${GREEN}● No recent errors${NC}"
    fi
}

# Main script logic
case "${1:-help}" in
    "status")
        check_service
        show_status
        ;;
    "start")
        check_service
        start_service
        ;;
    "stop")
        check_service
        stop_service
        ;;
    "restart")
        check_service
        restart_service
        ;;
    "enable")
        check_service
        enable_service
        ;;
    "disable")
        check_service
        disable_service
        ;;
    "logs")
        check_service
        show_logs "${2:-20}"
        ;;
    "follow")
        check_service
        follow_logs
        ;;
    "quick")
        check_service
        quick_status
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo
        show_help
        exit 1
        ;;
esac 