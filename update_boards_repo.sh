#!/bin/bash
# update_boards_repo.sh
# Updates helm_client repository on all slave boards using SSH

# Configuration
BOARDS=(
    "rpihelmet2.local:2"
    "rpihelmet3.local:3"
    "rpihelmet4.local:4"
    "rpihelmet5.local:5"
    "rpihelmet6.local:6"
    "rpihelmet7.local:7"
)

# SSH configuration
SSH_USER="rpi"
SSH_OPTIONS="-o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
REPO_PATH="helm_client"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="update_boards_repo_$(date +%Y%m%d_%H%M%S).log"

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] ${message}${NC}" | tee -a "$LOG_FILE"
}

# Function to test SSH connectivity
test_ssh_connection() {
    local board_hostname=$1
    local board_number=$2
    
    print_status "$BLUE" "Testing SSH connection to $board_hostname..."
    
    if ssh $SSH_OPTIONS "$SSH_USER@$board_hostname" "echo 'SSH connection successful'" >/dev/null 2>&1; then
        print_status "$GREEN" "✓ SSH connection to $board_hostname successful"
        return 0
    else
        print_status "$RED" "✗ SSH connection to $board_hostname failed"
        return 1
    fi
}

# Function to check if repository exists
check_repo_exists() {
    local board_hostname=$1
    local board_number=$2
    
    print_status "$BLUE" "Checking if repository exists on $board_hostname..."
    
    if ssh $SSH_OPTIONS "$SSH_USER@$board_hostname" "test -d $REPO_PATH/.git" 2>/dev/null; then
        print_status "$GREEN" "✓ Repository found on $board_hostname"
        return 0
    else
        print_status "$RED" "✗ Repository not found on $board_hostname (path: ~/$REPO_PATH)"
        return 1
    fi
}

# Function to get current git status
get_git_status() {
    local board_hostname=$1
    local board_number=$2
    
    print_status "$BLUE" "Getting git status from $board_hostname..."
    
    local git_status=$(ssh $SSH_OPTIONS "$SSH_USER@$board_hostname" "cd $REPO_PATH && git status --porcelain" 2>/dev/null)
    local current_branch=$(ssh $SSH_OPTIONS "$SSH_USER@$board_hostname" "cd $REPO_PATH && git branch --show-current" 2>/dev/null)
    local current_commit=$(ssh $SSH_OPTIONS "$SSH_USER@$board_hostname" "cd $REPO_PATH && git rev-parse --short HEAD" 2>/dev/null)
    
    print_status "$BLUE" "  Branch: $current_branch"
    print_status "$BLUE" "  Commit: $current_commit"
    
    if [[ -n "$git_status" ]]; then
        print_status "$YELLOW" "  Warning: Repository has uncommitted changes:"
        echo "$git_status" | while read -r line; do
            print_status "$YELLOW" "    $line"
        done
        return 1
    else
        print_status "$GREEN" "  Repository is clean"
        return 0
    fi
}

# Function to update repository
update_board_repo() {
    local board_hostname=$1
    local board_number=$2
    
    print_status "$BLUE" "=== Updating Repository on Board $board_number ($board_hostname) ==="
    
    # Test SSH connection
    if ! test_ssh_connection "$board_hostname" "$board_number"; then
        print_status "$RED" "Skipping $board_hostname due to SSH connection failure"
        return 1
    fi
    
    # Check if repository exists
    if ! check_repo_exists "$board_hostname" "$board_number"; then
        print_status "$RED" "Skipping $board_hostname due to missing repository"
        return 1
    fi
    
    # Get current git status
    local clean_repo=0
    if get_git_status "$board_hostname" "$board_number"; then
        clean_repo=1
    fi
    
    # Ask for confirmation if repo has uncommitted changes
    if [[ $clean_repo -eq 0 ]]; then
        echo
        print_status "$YELLOW" "⚠  Warning: $board_hostname has uncommitted changes!"
        read -p "Continue with git pull anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "$YELLOW" "Skipping $board_hostname due to uncommitted changes"
            return 1
        fi
    fi
    
    # Perform git pull
    print_status "$BLUE" "Running git pull on $board_hostname..."
    
    local pull_output=$(ssh $SSH_OPTIONS "$SSH_USER@$board_hostname" "cd $REPO_PATH && git pull 2>&1")
    local pull_exit_code=$?
    
    if [[ $pull_exit_code -eq 0 ]]; then
        print_status "$GREEN" "✓ Git pull successful on $board_hostname"
        
        # Show what was updated
        if [[ "$pull_output" == *"Already up to date"* ]]; then
            print_status "$BLUE" "  Repository was already up to date"
        else
            print_status "$GREEN" "  Updates applied:"
            echo "$pull_output" | grep -E "^\s*(Updating|Fast-forward|Merge|files? changed)" | while read -r line; do
                print_status "$GREEN" "    $line"
            done
        fi
        
        # Get new commit info
        local new_commit=$(ssh $SSH_OPTIONS "$SSH_USER@$board_hostname" "cd $REPO_PATH && git rev-parse --short HEAD" 2>/dev/null)
        print_status "$GREEN" "  New commit: $new_commit"
        
        return 0
    else
        print_status "$RED" "✗ Git pull failed on $board_hostname"
        print_status "$RED" "  Error output:"
        echo "$pull_output" | while read -r line; do
            print_status "$RED" "    $line"
        done
        return 1
    fi
}

# Function to restart services if needed
restart_board_service() {
    local board_hostname=$1
    local board_number=$2
    
    print_status "$BLUE" "Checking if service restart is needed on $board_hostname..."
    
    # Check if the service is running
    local service_status=$(ssh $SSH_OPTIONS "$SSH_USER@$board_hostname" "systemctl is-active helmet-camera-slave" 2>/dev/null)
    
    if [[ "$service_status" == "active" ]]; then
        echo
        read -p "Restart helmet-camera-slave service on $board_hostname? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "$BLUE" "Restarting service on $board_hostname..."
            
            if ssh $SSH_OPTIONS "$SSH_USER@$board_hostname" "sudo systemctl restart helmet-camera-slave" 2>/dev/null; then
                print_status "$GREEN" "✓ Service restarted successfully on $board_hostname"
                
                # Wait a moment and check status
                sleep 2
                local new_status=$(ssh $SSH_OPTIONS "$SSH_USER@$board_hostname" "systemctl is-active helmet-camera-slave" 2>/dev/null)
                if [[ "$new_status" == "active" ]]; then
                    print_status "$GREEN" "✓ Service is running properly on $board_hostname"
                else
                    print_status "$YELLOW" "⚠ Service status: $new_status on $board_hostname"
                fi
            else
                print_status "$RED" "✗ Failed to restart service on $board_hostname"
            fi
        else
            print_status "$BLUE" "Service restart skipped for $board_hostname"
        fi
    else
        print_status "$YELLOW" "Service not active on $board_hostname (status: $service_status)"
    fi
}

# Function to show summary
show_summary() {
    local total_boards=$1
    local successful_updates=$2
    local failed_updates=$3
    
    print_status "$BLUE" "=== Update Summary ==="
    print_status "$BLUE" "Total boards: $total_boards"
    print_status "$GREEN" "Successful updates: $successful_updates"
    print_status "$RED" "Failed updates: $failed_updates"
    
    if [[ $failed_updates -eq 0 ]]; then
        print_status "$GREEN" "All boards updated successfully! 🎉"
    else
        print_status "$YELLOW" "Some boards failed to update. Check log for details."
    fi
    
    print_status "$BLUE" "Log file: $(realpath "$LOG_FILE")"
}

# Function to check network connectivity
check_network() {
    print_status "$BLUE" "=== Network Connectivity Check ==="
    
    local reachable_boards=0
    local total_boards=${#BOARDS[@]}
    
    for board_info in "${BOARDS[@]}"; do
        local board_hostname=$(echo "$board_info" | cut -d':' -f1)
        local board_number=$(echo "$board_info" | cut -d':' -f2)
        
        print_status "$BLUE" "Checking connectivity to $board_hostname..."
        
        if ping -c 1 -W 2 "$board_hostname" >/dev/null 2>&1; then
            print_status "$GREEN" "✓ $board_hostname is reachable"
            ((reachable_boards++))
        else
            print_status "$RED" "✗ $board_hostname is not reachable"
        fi
    done
    
    print_status "$BLUE" "Network check: $reachable_boards/$total_boards boards reachable"
    
    if [[ $reachable_boards -eq 0 ]]; then
        print_status "$RED" "No boards are reachable. Check network connection."
        exit 1
    fi
    
    echo
}

# Function to show help
show_help() {
    cat << EOF
Helmet Camera Repository Update Tool

Usage: $0 [OPTIONS]

This script updates the helm_client repository on all slave boards using SSH.

Features:
  - Tests SSH connectivity before attempting updates
  - Checks for uncommitted changes and warns user
  - Shows detailed git pull output
  - Optionally restarts services after updates
  - Comprehensive logging and error handling

Boards Updated:
$(printf "  - %s\n" "${BOARDS[@]}")

SSH Configuration:
  - User: $SSH_USER
  - Repository path: ~/$REPO_PATH
  - SSH options: $SSH_OPTIONS

Options:
  -h, --help       Show this help message
  --check-network  Only check network connectivity to boards
  --no-restart     Skip service restart prompts

Examples:
  $0                    # Update all boards with interactive prompts
  $0 --check-network    # Only test connectivity
  $0 --no-restart       # Update without offering to restart services

Log Files:
  All operations are logged to update_boards_repo_YYYYMMDD_HHMMSS.log

Prerequisites:
  - SSH key authentication configured for boards
  - Network connectivity to board hostnames
  - Git repository exists in ~/$REPO_PATH on each board

EOF
}

# Main function
main() {
    local check_network_only=false
    local allow_restart=true
    
    # Parse command line arguments first
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --check-network)
                check_network_only=true
                shift
                ;;
            --no-restart)
                allow_restart=false
                shift
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    print_status "$BLUE" "=== Helmet Camera Repository Update Tool ==="
    print_status "$BLUE" "Started at: $(date)"
    
    if [[ "$check_network_only" == "true" ]]; then
        print_status "$BLUE" "Running network connectivity check only"
    else
        print_status "$BLUE" "Updating ${#BOARDS[@]} boards"
    fi
    
    # Check network connectivity first
    check_network
    
    if [[ "$check_network_only" == "true" ]]; then
        print_status "$BLUE" "Network check completed."
        exit 0
    fi
    
    local successful_updates=0
    local failed_updates=0
    
    # Process each board
    for board_info in "${BOARDS[@]}"; do
        local board_hostname=$(echo "$board_info" | cut -d':' -f1)
        local board_number=$(echo "$board_info" | cut -d':' -f2)
        
        if update_board_repo "$board_hostname" "$board_number"; then
            ((successful_updates++))
            
            # Offer to restart service if allowed
            if [[ "$allow_restart" == "true" ]]; then
                restart_board_service "$board_hostname" "$board_number"
            fi
        else
            ((failed_updates++))
        fi
        
        echo # Add spacing between boards
    done
    
    # Show summary
    show_summary ${#BOARDS[@]} $successful_updates $failed_updates
    
    print_status "$BLUE" "Update process completed at: $(date)"
    
    if [[ $failed_updates -eq 0 ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@" 