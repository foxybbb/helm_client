#!/bin/bash
# transfer_photos_rsync.sh
# Transfers all photo sessions from helmet camera boards using rsync
# Supports incremental sync, resume, and progress monitoring

# set -e disabled to prevent interference with return codes

# Configuration - Edit these variables as needed
REMOTE_USER="rpi"
REMOTE_BASE_DIR="/home/rpi"
LOCAL_BASE_DIR="./helmet_photos"
SSH_KEY=""  # Path to SSH key if needed (e.g., ~/.ssh/id_rsa)
SSH_PORT="22"

# Helmet camera boards configuration
# Format: "hostname:camera_number"
declare -a BOARDS=(
    "rpihelmet1.local:1"      # Master board with cam1
    "rpihelmet2.local:2"       # Slave boards
    "rpihelmet3.local:3"
    "rpihelmet4.local:4"
    "rpihelmet5.local:5"
    "rpihelmet6.local:6"
    "rpihelmet7.local:7"
)

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="transfer_$(date +%Y%m%d_%H%M%S).log"

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] ${message}${NC}" | tee -a "$LOG_FILE"
}

# Function to check if host is reachable
check_host() {
    local hostname=$1
    print_status "$BLUE" "Checking connectivity to $hostname..."
    
    if ping -c 1 -W 3 "$hostname" >/dev/null 2>&1; then
        print_status "$GREEN" "✓ $hostname is reachable"
        return 0
    else
        print_status "$RED" "✗ $hostname is not reachable"
        return 1
    fi
}

# Function to get SSH options
get_ssh_opts() {
    local opts="-o ConnectTimeout=10 -o StrictHostKeyChecking=no"
    if [[ -n "$SSH_KEY" && -f "$SSH_KEY" ]]; then
        opts="$opts -i $SSH_KEY"
    fi
    if [[ "$SSH_PORT" != "22" ]]; then
        opts="$opts -p $SSH_PORT"
    fi
    echo "$opts"
}

# Function to get rsync SSH options
get_rsync_ssh_opts() {
    local ssh_opts=$(get_ssh_opts)
    echo "ssh $ssh_opts"
}

# Function to list available sessions on remote board
list_remote_sessions() {
    local hostname=$1
    local cam_number=$2
    local remote_path="${REMOTE_BASE_DIR}/helmet-cam${cam_number}"
    
    print_status "$BLUE" "Listing sessions on $hostname (cam$cam_number)..."
    
    local ssh_opts=$(get_ssh_opts)
    local sessions=$(ssh $ssh_opts "${REMOTE_USER}@${hostname}" "find $remote_path -maxdepth 1 -type d -name 'session_*' 2>/dev/null | sort" 2>/dev/null || echo "")
    
    if [[ -n "$sessions" ]]; then
        echo "$sessions" | while read -r session_path; do
            local session_name=$(basename "$session_path")
            local file_count=$(ssh $ssh_opts "${REMOTE_USER}@${hostname}" "find $session_path -name '*.jpg' 2>/dev/null | wc -l" 2>/dev/null || echo "0")
            local total_size=$(ssh $ssh_opts "${REMOTE_USER}@${hostname}" "du -sh $session_path 2>/dev/null | cut -f1" 2>/dev/null || echo "unknown")
            print_status "$GREEN" "  Found: $session_name ($file_count photos, $total_size)"
        done
        return 0
    else
        print_status "$YELLOW" "  No sessions found on $hostname"
        return 1
    fi
}

# Function to sync photos from a single board
sync_board() {
    local hostname=$1
    local cam_number=$2
    local board_success=0
    
    print_status "$BLUE" "=== Syncing $hostname (cam$cam_number) ==="
    
    # Check connectivity
    if ! check_host "$hostname"; then
        print_status "$RED" "Skipping $hostname due to connectivity issues"
        return 1
    fi
    
    # List available sessions
    if ! list_remote_sessions "$hostname" "$cam_number"; then
        print_status "$YELLOW" "No sessions to sync from $hostname"
        return 0  # 0 = success (no sessions is not an error)
    fi
    
    # Create local directory structure
    local local_board_dir="${LOCAL_BASE_DIR}/${hostname}"
    mkdir -p "$local_board_dir"
    
    # Remote path for this camera
    local remote_cam_path="${REMOTE_BASE_DIR}/helmet-cam${cam_number}/"
    
    # Rsync options
    local rsync_opts="-avz --progress --partial --inplace"
    rsync_opts="$rsync_opts --exclude='*.tmp' --exclude='*.lock'"
    rsync_opts="$rsync_opts --log-file=${LOG_FILE}.rsync"
    
    # SSH options for rsync
    local ssh_command=$(get_rsync_ssh_opts)
    
    print_status "$BLUE" "Starting rsync from ${REMOTE_USER}@${hostname}:${remote_cam_path}"
    print_status "$BLUE" "Destination: ${local_board_dir}/"
    
    # Execute rsync
    if rsync $rsync_opts -e "$ssh_command" \
        "${REMOTE_USER}@${hostname}:${remote_cam_path}" \
        "${local_board_dir}/"; then
        print_status "$GREEN" "✓ Successfully synced $hostname"
        board_success=0  # 0 = success in bash return codes
    else
        print_status "$RED" "✗ Failed to sync $hostname"
        board_success=1  # 1 = failure in bash return codes
    fi
    
    # Count local files after sync
    local local_photos=$(find "$local_board_dir" -name "*.jpg" 2>/dev/null | wc -l)
    local local_sessions=$(find "$local_board_dir" -maxdepth 3 -type d -name "session_*" 2>/dev/null | wc -l)
    print_status "$GREEN" "Local summary for $hostname: $local_sessions sessions, $local_photos photos"
    
    return $board_success
}

# Function to show final summary
show_summary() {
    local successful_boards=$1
    local total_boards=$2
    
    print_status "$BLUE" "=== Transfer Summary ==="
    print_status "$GREEN" "Successfully synced: $successful_boards/$total_boards boards"
    
    if [[ -d "$LOCAL_BASE_DIR" ]]; then
        local total_photos=$(find "$LOCAL_BASE_DIR" -name "*.jpg" 2>/dev/null | wc -l)
        local total_sessions=$(find "$LOCAL_BASE_DIR" -maxdepth 4 -type d -name "session_*" 2>/dev/null | wc -l)
        local total_size=$(du -sh "$LOCAL_BASE_DIR" 2>/dev/null | cut -f1)
        
        print_status "$GREEN" "Total downloaded: $total_sessions sessions, $total_photos photos, $total_size"
        print_status "$BLUE" "Photos stored in: $(realpath "$LOCAL_BASE_DIR")"
        
        # Show directory structure
        print_status "$BLUE" "Directory structure:"
        tree "$LOCAL_BASE_DIR" -d -L 3 2>/dev/null || find "$LOCAL_BASE_DIR" -type d | head -20
    fi
    
    print_status "$BLUE" "Log file: $(realpath "$LOG_FILE")"
}

# Function to check prerequisites
check_prerequisites() {
    # Check for required commands
    local required_commands=("rsync" "ssh" "ping")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            print_status "$RED" "Error: Required command '$cmd' not found"
            exit 1
        fi
    done
    
    # Check SSH key if specified
    if [[ -n "$SSH_KEY" && ! -f "$SSH_KEY" ]]; then
        print_status "$RED" "Error: SSH key not found: $SSH_KEY"
        exit 1
    fi
    
    print_status "$GREEN" "✓ Prerequisites check passed"
}

# Main function
main() {
    print_status "$BLUE" "=== Helmet Camera Photos Transfer (rsync) ==="
    print_status "$BLUE" "Started at: $(date)"
    
    # Check prerequisites
    check_prerequisites
    
    # Create base directory
    mkdir -p "$LOCAL_BASE_DIR"
    
    # Statistics
    local successful_boards=0
    local total_boards=${#BOARDS[@]}
    
    # Process each board
    for board in "${BOARDS[@]}"; do
        IFS=':' read -r hostname cam_number <<< "$board"
        
        if sync_board "$hostname" "$cam_number"; then
            successful_boards=$((successful_boards + 1))
        fi
        
        echo # Add spacing between boards
    done
    
    # Show summary
    show_summary $successful_boards $total_boards
    
    print_status "$BLUE" "Transfer completed at: $(date)"
    
    # Exit code based on success rate
    if [[ $successful_boards -eq $total_boards ]]; then
        print_status "$GREEN" "All transfers completed successfully!"
        exit 0
    elif [[ $successful_boards -gt 0 ]]; then
        print_status "$YELLOW" "Partial success: $successful_boards/$total_boards boards transferred"
        exit 1
    else
        print_status "$RED" "All transfers failed!"
        exit 2
    fi
}

# Help function
show_help() {
    cat << EOF
Helmet Camera Photos Transfer Script (rsync)

Usage: $0 [OPTIONS]

This script transfers all photo sessions from helmet camera boards to the local computer
using rsync for incremental synchronization.

Configuration (edit the script):
  REMOTE_USER      - SSH username (default: rpi)
  REMOTE_BASE_DIR  - Base directory on remote boards (default: /home/rpi)
  LOCAL_BASE_DIR   - Local destination directory (default: ./helmet_photos)
  SSH_KEY          - Path to SSH private key (optional)
  SSH_PORT         - SSH port (default: 22)
  BOARDS           - Array of hostname:camera_number pairs

Features:
  - Incremental sync (only downloads new/changed files)
  - Resume capability for interrupted transfers  
  - Progress monitoring
  - Connectivity checking
  - Detailed logging
  - Error handling

Directory structure created:
  LOCAL_BASE_DIR/
  ├── helm_master/
  │   └── helmet-cam1/
  │       ├── session_20250115/
  │       └── session_20250116/
  ├── rpihelmet2/
  │   └── helmet-cam2/
  └── ...

Options:
  -h, --help    Show this help message

EOF
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac 