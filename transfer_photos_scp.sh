#!/bin/bash
# transfer_photos_scp.sh
# Transfers all photo sessions from helmet camera boards using scp
# Simple recursive copy for complete session downloads

# set -e disabled to prevent interference with return codes

# Configuration - Edit these variables as needed
REMOTE_USER="rpi"
REMOTE_BASE_DIR="/home/rpi"
LOCAL_BASE_DIR="./helmet_photos"
SSH_KEY=""  # Path to SSH key if needed (e.g., ~/.ssh/id_rsa)
SSH_PORT="22"
PARALLEL_JOBS=3  # Number of concurrent transfers

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
LOG_FILE="transfer_scp_$(date +%Y%m%d_%H%M%S).log"
TEMP_DIR="/tmp/helmet_transfer_$$"

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] ${message}${NC}" | tee -a "$LOG_FILE"
}

# Function to cleanup on exit
cleanup() {
    rm -rf "$TEMP_DIR"
    # Kill any background jobs
    jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

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
    local opts="-o ConnectTimeout=10 -o StrictHostKeyChecking=no -o BatchMode=yes"
    if [[ -n "$SSH_KEY" && -f "$SSH_KEY" ]]; then
        opts="$opts -i $SSH_KEY"
    fi
    if [[ "$SSH_PORT" != "22" ]]; then
        opts="$opts -P $SSH_PORT"
    fi
    echo "$opts"
}

# Function to get SCP options
get_scp_opts() {
    local opts="-r -p -o ConnectTimeout=10 -o StrictHostKeyChecking=no"
    if [[ -n "$SSH_KEY" && -f "$SSH_KEY" ]]; then
        opts="$opts -i $SSH_KEY"
    fi
    if [[ "$SSH_PORT" != "22" ]]; then
        opts="$opts -P $SSH_PORT"
    fi
    echo "$opts"
}

# Function to list available sessions on remote board
list_remote_sessions() {
    local hostname=$1
    local cam_number=$2
    local remote_path="${REMOTE_BASE_DIR}/helmet-cam${cam_number}"
    
    print_status "$BLUE" "Listing sessions on $hostname (cam$cam_number)..."
    
    local ssh_opts="-o ConnectTimeout=10 -o StrictHostKeyChecking=no"
    if [[ -n "$SSH_KEY" && -f "$SSH_KEY" ]]; then
        ssh_opts="$ssh_opts -i $SSH_KEY"
    fi
    if [[ "$SSH_PORT" != "22" ]]; then
        ssh_opts="$ssh_opts -p $SSH_PORT"
    fi
    
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

# Function to download a single session
download_session() {
    local hostname=$1
    local cam_number=$2
    local session_path=$3
    local local_board_dir=$4
    local session_name=$(basename "$session_path")
    
    print_status "$BLUE" "Downloading $session_name from $hostname..."
    
    local local_session_dir="${local_board_dir}/helmet-cam${cam_number}/${session_name}"
    
    # Skip if already exists and not empty
    if [[ -d "$local_session_dir" ]] && [[ $(find "$local_session_dir" -name "*.jpg" 2>/dev/null | wc -l) -gt 0 ]]; then
        local existing_count=$(find "$local_session_dir" -name "*.jpg" 2>/dev/null | wc -l)
        print_status "$YELLOW" "  Session $session_name already exists with $existing_count photos, skipping"
        return 0
    fi
    
    # Create local directory
    mkdir -p "$local_session_dir"
    
    # SCP options
    local scp_opts=$(get_scp_opts)
    
    # Download session
    local remote_session="${REMOTE_USER}@${hostname}:${session_path}/"
    
    if scp $scp_opts "$remote_session" "$local_session_dir/" 2>>"$LOG_FILE"; then
        local downloaded_count=$(find "$local_session_dir" -name "*.jpg" 2>/dev/null | wc -l)
        local downloaded_size=$(du -sh "$local_session_dir" 2>/dev/null | cut -f1)
        print_status "$GREEN" "  ✓ Downloaded $session_name: $downloaded_count photos, $downloaded_size"
        return 0
    else
        print_status "$RED" "  ✗ Failed to download $session_name"
        rm -rf "$local_session_dir" 2>/dev/null || true
        return 1
    fi
}

# Function to copy entire camera directory (alternative method)
copy_camera_directory() {
    local hostname=$1
    local cam_number=$2
    local local_board_dir=$3
    
    local remote_cam_path="${REMOTE_BASE_DIR}/helmet-cam${cam_number}"
    local scp_opts=$(get_scp_opts)
    
    print_status "$BLUE" "Copying entire camera directory from $hostname (cam$cam_number)..."
    
    if scp $scp_opts "${REMOTE_USER}@${hostname}:${remote_cam_path}" "$local_board_dir/" 2>>"$LOG_FILE"; then
        print_status "$GREEN" "✓ Successfully copied camera directory from $hostname"
        return 0
    else
        print_status "$RED" "✗ Failed to copy camera directory from $hostname"
        return 1
    fi
}

# Function to sync photos from a single board
sync_board() {
    local hostname=$1
    local cam_number=$2
    local board_success=0
    
    print_status "$BLUE" "=== Processing $hostname (cam$cam_number) ==="
    
    # Check connectivity
    if ! check_host "$hostname"; then
        print_status "$RED" "Skipping $hostname due to connectivity issues"
        return 1
    fi
    
    # Create local directory structure
    local local_board_dir="${LOCAL_BASE_DIR}/${hostname}"
    mkdir -p "$local_board_dir"
    
    # Try session-by-session download first
    local ssh_opts="-o ConnectTimeout=10 -o StrictHostKeyChecking=no"
    if [[ -n "$SSH_KEY" && -f "$SSH_KEY" ]]; then
        ssh_opts="$ssh_opts -i $SSH_KEY"
    fi
    if [[ "$SSH_PORT" != "22" ]]; then
        ssh_opts="$ssh_opts -p $SSH_PORT"
    fi
    
    local remote_cam_path="${REMOTE_BASE_DIR}/helmet-cam${cam_number}"
    local sessions=$(ssh $ssh_opts "${REMOTE_USER}@${hostname}" "find $remote_cam_path -maxdepth 1 -type d -name 'session_*' 2>/dev/null | sort" 2>/dev/null || echo "")
    
    if [[ -n "$sessions" ]]; then
        # Download sessions individually
        local session_success=0
        local session_total=0
        
        echo "$sessions" | while read -r session_path; do
            ((session_total++))
            if download_session "$hostname" "$cam_number" "$session_path" "$local_board_dir"; then
                ((session_success++))
            fi
        done
        
        board_success=0  # 0 = success in bash return codes
    else
        # Fallback: try to copy entire camera directory
        print_status "$YELLOW" "No sessions found, trying to copy entire camera directory..."
        if copy_camera_directory "$hostname" "$cam_number" "$local_board_dir"; then
            board_success=0  # 0 = success in bash return codes
        else
            board_success=1  # 1 = failure in bash return codes
        fi
    fi
    
    # Count local files after sync
    local local_photos=$(find "$local_board_dir" -name "*.jpg" 2>/dev/null | wc -l)
    local local_sessions=$(find "$local_board_dir" -maxdepth 2 -type d -name "session_*" 2>/dev/null | wc -l)
    print_status "$GREEN" "Local summary for $hostname: $local_sessions sessions, $local_photos photos"
    
    return $board_success
}

# Function to sync board in background
sync_board_background() {
    local hostname=$1
    local cam_number=$2
    local result_file="${TEMP_DIR}/result_${hostname}"
    
    {
        if sync_board "$hostname" "$cam_number"; then
            echo "success" > "$result_file"
        else
            echo "failed" > "$result_file"
        fi
    } &
}

# Function to show final summary
show_summary() {
    local successful_boards=$1
    local total_boards=$2
    
    print_status "$BLUE" "=== Transfer Summary ==="
    print_status "$GREEN" "Successfully copied: $successful_boards/$total_boards boards"
    
    if [[ -d "$LOCAL_BASE_DIR" ]]; then
        local total_photos=$(find "$LOCAL_BASE_DIR" -name "*.jpg" 2>/dev/null | wc -l)
        local total_sessions=$(find "$LOCAL_BASE_DIR" -maxdepth 3 -type d -name "session_*" 2>/dev/null | wc -l)
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
    local required_commands=("scp" "ssh" "ping")
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
    print_status "$BLUE" "=== Helmet Camera Photos Transfer (SCP) ==="
    print_status "$BLUE" "Started at: $(date)"
    
    # Check prerequisites
    check_prerequisites
    
    # Create base directory and temp directory
    mkdir -p "$LOCAL_BASE_DIR"
    mkdir -p "$TEMP_DIR"
    
    # Statistics
    local successful_boards=0
    local total_boards=${#BOARDS[@]}
    
    if [[ $PARALLEL_JOBS -gt 1 ]]; then
        print_status "$BLUE" "Using parallel transfers ($PARALLEL_JOBS concurrent jobs)"
        
        # Start background jobs
        local active_jobs=0
        local board_index=0
        
        while [[ $board_index -lt $total_boards ]]; do
            # Start new jobs up to limit
            while [[ $active_jobs -lt $PARALLEL_JOBS && $board_index -lt $total_boards ]]; do
                local board=${BOARDS[$board_index]}
                IFS=':' read -r hostname cam_number <<< "$board"
                
                print_status "$BLUE" "Starting background transfer for $hostname..."
                sync_board_background "$hostname" "$cam_number"
                ((active_jobs++))
                ((board_index++))
            done
            
            # Wait for any job to complete
            wait -n 2>/dev/null || true
            ((active_jobs--))
        done
        
        # Wait for all remaining jobs
        wait
        
        # Check results
        for board in "${BOARDS[@]}"; do
            IFS=':' read -r hostname cam_number <<< "$board"
            local result_file="${TEMP_DIR}/result_${hostname}"
            if [[ -f "$result_file" && "$(cat "$result_file")" == "success" ]]; then
                successful_boards=$((successful_boards + 1))
            fi
        done
    else
        # Sequential processing
        print_status "$BLUE" "Using sequential transfers"
        
        for board in "${BOARDS[@]}"; do
            IFS=':' read -r hostname cam_number <<< "$board"
            
            if sync_board "$hostname" "$cam_number"; then
                successful_boards=$((successful_boards + 1))
            fi
            
            echo # Add spacing between boards
        done
    fi
    
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
Helmet Camera Photos Transfer Script (SCP)

Usage: $0 [OPTIONS]

This script transfers all photo sessions from helmet camera boards to the local computer
using scp for complete session copying.

Configuration (edit the script):
  REMOTE_USER      - SSH username (default: rpi)
  REMOTE_BASE_DIR  - Base directory on remote boards (default: /home/rpi)
  LOCAL_BASE_DIR   - Local destination directory (default: ./helmet_photos)
  SSH_KEY          - Path to SSH private key (optional)
  SSH_PORT         - SSH port (default: 22)
  PARALLEL_JOBS    - Number of concurrent transfers (default: 3)
  BOARDS           - Array of hostname:camera_number pairs

Features:
  - Complete session downloads
  - Parallel transfers for speed
  - Skip existing sessions  
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
  --sequential  Force sequential transfers (no parallel)

EOF
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    --sequential)
        PARALLEL_JOBS=1
        shift
        main "$@"
        ;;
    *)
        main "$@"
        ;;
esac 