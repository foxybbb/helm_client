#!/bin/bash
# delete_photos_from_boards.sh
# Safely deletes photo sessions from helmet camera boards
# Features: dry-run mode, confirmations, selective deletion, detailed logging

# Configuration - Edit these variables as needed
REMOTE_USER="rpi"
REMOTE_BASE_DIR="/home/rpi"
SSH_KEY=""  # Path to SSH key if needed (e.g., ~/.ssh/id_rsa)
SSH_PORT="22"
DRY_RUN=true  # Default to dry-run for safety

# Helmet camera boards configuration
# Format: "hostname:camera_number"
declare -a BOARDS=(
    "rpihelmet1.local:1"      # Master board with cam1
    "rpihelmet2.local:2"      # Slave boards
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
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="delete_photos_$(date +%Y%m%d_%H%M%S).log"

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] ${message}${NC}" | tee -a "$LOG_FILE"
}

# Function to print dry-run prefix
print_dry_run() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -n "[DRY-RUN] "
    fi
}

# Function to check if host is reachable
check_host() {
    local hostname=$1
    print_status "$BLUE" "$(print_dry_run)Checking connectivity to $hostname..."
    
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

# Function to list sessions on remote board
list_remote_sessions() {
    local hostname=$1
    local cam_number=$2
    local remote_path="${REMOTE_BASE_DIR}/helmet-cam${cam_number}"
    
    print_status "$BLUE" "$(print_dry_run)Listing sessions on $hostname (cam$cam_number)..."
    
    local ssh_opts=$(get_ssh_opts)
    local sessions=$(ssh $ssh_opts "${REMOTE_USER}@${hostname}" "find $remote_path -maxdepth 1 -type d -name 'session_*' 2>/dev/null | sort" 2>/dev/null || echo "")
    
    if [[ -n "$sessions" ]]; then
        local session_count=0
        local total_photos=0
        local total_size=0
        
        echo "$sessions" | while read -r session_path; do
            local session_name=$(basename "$session_path")
            local file_count=$(ssh $ssh_opts "${REMOTE_USER}@${hostname}" "find $session_path -name '*.jpg' 2>/dev/null | wc -l" 2>/dev/null || echo "0")
            local session_size=$(ssh $ssh_opts "${REMOTE_USER}@${hostname}" "du -s $session_path 2>/dev/null | cut -f1" 2>/dev/null || echo "0")
            local session_size_human=$(ssh $ssh_opts "${REMOTE_USER}@${hostname}" "du -sh $session_path 2>/dev/null | cut -f1" 2>/dev/null || echo "unknown")
            
            print_status "$YELLOW" "  Found: $session_name ($file_count photos, $session_size_human)"
            ((session_count++))
            ((total_photos += file_count))
            ((total_size += session_size))
        done
        
        print_status "$GREEN" "Total on $hostname: $session_count sessions, $total_photos photos"
        return 0
    else
        print_status "$YELLOW" "  No sessions found on $hostname"
        return 1
    fi
}

# Function to delete sessions from a single board
delete_board_sessions() {
    local hostname=$1
    local cam_number=$2
    local date_filter=$3  # Optional: YYYYMMDD format
    local board_success=0
    
    print_status "$BLUE" "=== $(print_dry_run)Processing $hostname (cam$cam_number) ==="
    
    # Check connectivity
    if ! check_host "$hostname"; then
        print_status "$RED" "Skipping $hostname due to connectivity issues"
        return 1
    fi
    
    # List sessions first
    if ! list_remote_sessions "$hostname" "$cam_number"; then
        print_status "$YELLOW" "No sessions to delete on $hostname"
        return 0
    fi
    
    local remote_path="${REMOTE_BASE_DIR}/helmet-cam${cam_number}"
    local ssh_opts=$(get_ssh_opts)
    
    # Build find command with optional date filter
    local find_cmd="find $remote_path -maxdepth 1 -type d -name 'session_*'"
    if [[ -n "$date_filter" ]]; then
        find_cmd="$find_cmd -name 'session_${date_filter}*'"
        print_status "$BLUE" "$(print_dry_run)Filtering sessions for date: $date_filter"
    fi
    
    # Get sessions to delete
    local sessions_to_delete=$(ssh $ssh_opts "${REMOTE_USER}@${hostname}" "$find_cmd 2>/dev/null | sort" 2>/dev/null || echo "")
    
    if [[ -z "$sessions_to_delete" ]]; then
        print_status "$YELLOW" "No matching sessions found on $hostname"
        return 0
    fi
    
    # Count what will be deleted
    local session_count=$(echo "$sessions_to_delete" | wc -l)
    local total_photos=0
    local total_size=0
    
    echo "$sessions_to_delete" | while read -r session_path; do
        local file_count=$(ssh $ssh_opts "${REMOTE_USER}@${hostname}" "find $session_path -name '*.jpg' 2>/dev/null | wc -l" 2>/dev/null || echo "0")
        local session_size=$(ssh $ssh_opts "${REMOTE_USER}@${hostname}" "du -s $session_path 2>/dev/null | cut -f1" 2>/dev/null || echo "0")
        ((total_photos += file_count))
        ((total_size += session_size))
    done
    
    local total_size_human=$(ssh $ssh_opts "${REMOTE_USER}@${hostname}" "echo $total_size | awk '{printf \"%.1fMB\", \$1/1024}'" 2>/dev/null || echo "unknown")
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_status "$PURPLE" "[DRY-RUN] Would delete from $hostname:"
        print_status "$PURPLE" "  - $session_count sessions"
        print_status "$PURPLE" "  - $total_photos photos"
        print_status "$PURPLE" "  - $total_size_human of data"
        
        echo "$sessions_to_delete" | while read -r session_path; do
            print_status "$PURPLE" "  - $(basename "$session_path")"
        done
        
        board_success=0
    else
        # Actual deletion
        print_status "$RED" "DELETING from $hostname: $session_count sessions, $total_photos photos, $total_size_human"
        
        local deleted_count=0
        local failed_count=0
        
        echo "$sessions_to_delete" | while read -r session_path; do
            local session_name=$(basename "$session_path")
            print_status "$BLUE" "Deleting $session_name..."
            
            if ssh $ssh_opts "${REMOTE_USER}@${hostname}" "rm -rf '$session_path'" 2>/dev/null; then
                print_status "$GREEN" "✓ Deleted $session_name"
                ((deleted_count++))
            else
                print_status "$RED" "✗ Failed to delete $session_name"
                ((failed_count++))
            fi
        done
        
        if [[ $failed_count -eq 0 ]]; then
            print_status "$GREEN" "✓ Successfully deleted all sessions from $hostname"
            board_success=0
        else
            print_status "$YELLOW" "⚠ Deleted $deleted_count sessions, $failed_count failed on $hostname"
            board_success=1
        fi
    fi
    
    return $board_success
}

# Function to show summary
show_summary() {
    local successful_boards=$1
    local total_boards=$2
    local dry_run=$3
    
    print_status "$BLUE" "=== $(print_dry_run)Deletion Summary ==="
    
    if [[ "$dry_run" == "true" ]]; then
        print_status "$PURPLE" "DRY-RUN completed: $successful_boards/$total_boards boards processed"
        print_status "$BLUE" "No files were actually deleted. Use --execute to perform actual deletion."
    else
        print_status "$GREEN" "Deletion completed: $successful_boards/$total_boards boards processed"
    fi
    
    print_status "$BLUE" "Log file: $(realpath "$LOG_FILE")"
}

# Function to get user confirmation
confirm_deletion() {
    if [[ "$DRY_RUN" == "true" ]]; then
        return 0  # No confirmation needed for dry-run
    fi
    
    echo
    print_status "$RED" "⚠  WARNING: This will PERMANENTLY DELETE photos from all boards!"
    print_status "$RED" "⚠  This action CANNOT be undone!"
    echo
    
    read -p "Are you absolutely sure you want to delete photos? (type 'YES' to confirm): " confirmation
    
    if [[ "$confirmation" != "YES" ]]; then
        print_status "$YELLOW" "Deletion cancelled by user"
        exit 0
    fi
    
    echo
    read -p "Last chance! Type 'DELETE' to proceed: " final_confirmation
    
    if [[ "$final_confirmation" != "DELETE" ]]; then
        print_status "$YELLOW" "Deletion cancelled by user"
        exit 0
    fi
    
    print_status "$RED" "User confirmed deletion. Proceeding..."
}

# Function to check prerequisites
check_prerequisites() {
    # Check for required commands
    local required_commands=("ssh" "ping")
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
    local date_filter=""
    local boards_filter=()
    
    print_status "$BLUE" "=== Helmet Camera Photos Deletion Tool ==="
    print_status "$BLUE" "Started at: $(date)"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_status "$PURPLE" "Running in DRY-RUN mode (no files will be deleted)"
    else
        print_status "$RED" "Running in EXECUTE mode (files WILL be deleted)"
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Get user confirmation for actual deletion
    confirm_deletion
    
    # Statistics
    local successful_boards=0
    local total_boards=${#BOARDS[@]}
    
    # Process boards filter or all boards
    local boards_to_process=("${BOARDS[@]}")
    if [[ ${#boards_filter[@]} -gt 0 ]]; then
        boards_to_process=("${boards_filter[@]}")
        total_boards=${#boards_filter[@]}
    fi
    
    # Process each board
    for board in "${boards_to_process[@]}"; do
        IFS=':' read -r hostname cam_number <<< "$board"
        
        if delete_board_sessions "$hostname" "$cam_number" "$date_filter"; then
            successful_boards=$((successful_boards + 1))
        fi
        
        echo # Add spacing between boards
    done
    
    # Show summary
    show_summary $successful_boards $total_boards "$DRY_RUN"
    
    print_status "$BLUE" "Operation completed at: $(date)"
    
    # Exit code based on success rate
    if [[ $successful_boards -eq $total_boards ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            print_status "$GREEN" "Dry-run completed successfully!"
        else
            print_status "$GREEN" "All deletions completed successfully!"
        fi
        exit 0
    elif [[ $successful_boards -gt 0 ]]; then
        print_status "$YELLOW" "Partial success: $successful_boards/$total_boards boards processed"
        exit 1
    else
        print_status "$RED" "All operations failed!"
        exit 2
    fi
}

# Help function
show_help() {
    cat << EOF
Helmet Camera Photos Deletion Tool

Usage: $0 [OPTIONS]

This script safely deletes photo sessions from helmet camera boards.
By default, it runs in DRY-RUN mode to show what would be deleted.

Configuration (edit the script):
  REMOTE_USER      - SSH username (default: rpi)
  REMOTE_BASE_DIR  - Base directory on remote boards (default: /home/rpi)
  SSH_KEY          - Path to SSH private key (optional)
  SSH_PORT         - SSH port (default: 22)
  BOARDS           - Array of hostname:camera_number pairs

Safety Features:
  - DRY-RUN mode by default (use --execute for actual deletion)
  - Multiple confirmation prompts for actual deletion
  - Detailed logging of all operations
  - Per-board error handling
  - Connection testing before operations

Options:
  -h, --help       Show this help message
  --execute        Execute actual deletion (default is dry-run)
  --dry-run        Force dry-run mode (default)
  --date YYYYMMDD  Delete only sessions from specific date
  --board HOSTNAME Delete from specific board only

Examples:
  $0                              # Dry-run: show what would be deleted
  $0 --execute                    # Actually delete all photos
  $0 --execute --date 20250801    # Delete only photos from Aug 1, 2025
  $0 --execute --board rpihelmet2.local  # Delete from specific board

⚠  WARNING: Deletion is PERMANENT and cannot be undone!
   Always run dry-run first to verify what will be deleted.

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --execute)
            DRY_RUN=false
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --date)
            DATE_FILTER="$2"
            shift 2
            ;;
        --board)
            BOARD_FILTER="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Apply filters if specified
if [[ -n "$DATE_FILTER" ]]; then
    if [[ ! "$DATE_FILTER" =~ ^[0-9]{8}$ ]]; then
        print_status "$RED" "Error: Date filter must be in YYYYMMDD format"
        exit 1
    fi
fi

if [[ -n "$BOARD_FILTER" ]]; then
    # Find matching board
    found_board=""
    for board in "${BOARDS[@]}"; do
        IFS=':' read -r hostname cam_number <<< "$board"
        if [[ "$hostname" == "$BOARD_FILTER" ]]; then
            found_board="$board"
            break
        fi
    done
    
    if [[ -z "$found_board" ]]; then
        print_status "$RED" "Error: Board '$BOARD_FILTER' not found in configuration"
        exit 1
    fi
    
    BOARDS=("$found_board")
fi

# Run main function
main "$@" 