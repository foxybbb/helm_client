#!/bin/bash
# cleanup_web_sequences.sh
# Cleans up problematic web sequence directories and reorganizes photos into proper daily sessions

# Configuration
LOCAL_BASE_DIR="./helmet_photos"
DRY_RUN=true  # Default to dry-run for safety

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="cleanup_web_sequences_$(date +%Y%m%d_%H%M%S).log"

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

# Function to extract date from session name
extract_date_from_session() {
    local session_name=$1
    # Extract YYYYMMDD pattern from various formats
    if [[ $session_name =~ session_([0-9]{8}) ]]; then
        echo "${BASH_REMATCH[1]}"
    elif [[ $session_name =~ ([0-9]{8}) ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        # Default to today if no date found
        date +%Y%m%d
    fi
}

# Function to move photo to proper session
move_photo_to_session() {
    local photo_path=$1
    local target_session_dir=$2
    local photo_name=$(basename "$photo_path")
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_status "$PURPLE" "$(print_dry_run)Would move: $photo_name -> $(basename "$target_session_dir")"
    else
        # Create target directory if it doesn't exist
        mkdir -p "$target_session_dir"
        
        # Move the photo
        if mv "$photo_path" "$target_session_dir/"; then
            print_status "$GREEN" "Moved: $photo_name -> $(basename "$target_session_dir")"
            return 0
        else
            print_status "$RED" "Failed to move: $photo_name"
            return 1
        fi
    fi
    return 0
}

# Function to remove empty directory
remove_empty_dir() {
    local dir_path=$1
    
    if [[ ! -d "$dir_path" ]]; then
        return 0
    fi
    
    # Check if directory is empty
    if [[ -z "$(ls -A "$dir_path" 2>/dev/null)" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            print_status "$PURPLE" "$(print_dry_run)Would remove empty directory: $(basename "$dir_path")"
        else
            if rmdir "$dir_path" 2>/dev/null; then
                print_status "$GREEN" "Removed empty directory: $(basename "$dir_path")"
                return 0
            else
                print_status "$YELLOW" "Could not remove directory: $(basename "$dir_path") (may not be empty)"
                return 1
            fi
        fi
    fi
    return 0
}

# Function to cleanup board directory
cleanup_board() {
    local board_dir=$1
    local board_name=$(basename "$board_dir")
    
    print_status "$BLUE" "=== $(print_dry_run)Processing $board_name ==="
    
    if [[ ! -d "$board_dir" ]]; then
        print_status "$YELLOW" "Board directory not found: $board_dir"
        return 1
    fi
    
    local photos_moved=0
    local sessions_removed=0
    
    # Find all problematic session directories
    local problematic_sessions=$(find "$board_dir" -maxdepth 1 -type d \( \
        -name "*web_sequence*" -o \
        -name "*web_single*" -o \
        -name "session_*_[0-9][0-9][0-9]" -o \
        -name "session_????????_??????*" \
        \) | sort)
    
    if [[ -z "$problematic_sessions" ]]; then
        print_status "$GREEN" "No problematic sessions found in $board_name"
        return 0
    fi
    
    print_status "$YELLOW" "Found problematic sessions in $board_name:"
    echo "$problematic_sessions" | while read -r session_dir; do
        print_status "$YELLOW" "  - $(basename "$session_dir")"
    done
    
    # Process each problematic session
    echo "$problematic_sessions" | while read -r session_dir; do
        local session_name=$(basename "$session_dir")
        local session_date=$(extract_date_from_session "$session_name")
        local target_session_dir="$board_dir/session_$session_date"
        
        print_status "$BLUE" "$(print_dry_run)Processing session: $session_name (Date: $session_date)"
        
        # Find all photos in this session
        local photos=$(find "$session_dir" -name "*.jpg" 2>/dev/null | sort)
        
        if [[ -n "$photos" ]]; then
            local photo_count=$(echo "$photos" | wc -l)
            print_status "$BLUE" "$(print_dry_run)Found $photo_count photos to move"
            
            # Move each photo to the proper daily session
            echo "$photos" | while read -r photo_path; do
                if move_photo_to_session "$photo_path" "$target_session_dir"; then
                    ((photos_moved++))
                fi
            done
        fi
        
        # Check for session log and move it too
        local session_log="$session_dir/session_log.json"
        if [[ -f "$session_log" ]]; then
            if [[ "$DRY_RUN" == "true" ]]; then
                print_status "$PURPLE" "$(print_dry_run)Would move session log to $(basename "$target_session_dir")"
            else
                mkdir -p "$target_session_dir"
                if mv "$session_log" "$target_session_dir/"; then
                    print_status "$GREEN" "Moved session log to $(basename "$target_session_dir")"
                fi
            fi
        fi
        
        # Remove the empty problematic session directory
        if remove_empty_dir "$session_dir"; then
            ((sessions_removed++))
        fi
    done
    
    print_status "$GREEN" "$(print_dry_run)Completed $board_name: would reorganize sessions"
    return 0
}

# Function to consolidate small daily sessions
consolidate_daily_sessions() {
    local board_dir=$1
    local board_name=$(basename "$board_dir")
    
    print_status "$BLUE" "=== $(print_dry_run)Consolidating sessions in $board_name ==="
    
    # Find all session directories for the same date (including numbered ones)
    local dates=$(find "$board_dir" -maxdepth 1 -type d -name "session_????????*" | \
                  sed 's/.*session_\([0-9]\{8\}\).*/\1/' | sort -u)
    
    if [[ -z "$dates" ]]; then
        print_status "$YELLOW" "No sessions to consolidate in $board_name"
        return 0
    fi
    
    echo "$dates" | while read -r date; do
        local main_session="$board_dir/session_$date"
        local numbered_sessions=$(find "$board_dir" -maxdepth 1 -type d -name "session_${date}_*" | sort)
        
        if [[ -n "$numbered_sessions" ]]; then
            print_status "$BLUE" "$(print_dry_run)Consolidating sessions for date $date"
            
            echo "$numbered_sessions" | while read -r numbered_session; do
                local session_name=$(basename "$numbered_session")
                print_status "$BLUE" "$(print_dry_run)Consolidating $session_name into session_$date"
                
                # Move all photos from numbered session to main session
                local photos=$(find "$numbered_session" -name "*.jpg" 2>/dev/null)
                if [[ -n "$photos" ]]; then
                    echo "$photos" | while read -r photo; do
                        move_photo_to_session "$photo" "$main_session"
                    done
                fi
                
                # Move session log if exists
                local session_log="$numbered_session/session_log.json"
                if [[ -f "$session_log" ]]; then
                    if [[ "$DRY_RUN" == "true" ]]; then
                        print_status "$PURPLE" "$(print_dry_run)Would merge session log"
                    else
                        mkdir -p "$main_session"
                        # For now, just move it with a different name to avoid conflicts
                        local log_name="session_log_$(basename "$numbered_session").json"
                        mv "$session_log" "$main_session/$log_name"
                        print_status "$GREEN" "Moved session log as $log_name"
                    fi
                fi
                
                # Remove empty numbered session
                remove_empty_dir "$numbered_session"
            done
        fi
    done
}

# Function to show summary
show_summary() {
    local total_boards=$1
    local dry_run=$2
    
    print_status "$BLUE" "=== $(print_dry_run)Cleanup Summary ==="
    
    if [[ "$dry_run" == "true" ]]; then
        print_status "$PURPLE" "DRY-RUN completed for $total_boards boards"
        print_status "$BLUE" "No files were actually moved/deleted. Use --execute to perform actual cleanup."
    else
        print_status "$GREEN" "Cleanup completed for $total_boards boards"
    fi
    
    # Show final structure
    if [[ -d "$LOCAL_BASE_DIR" ]]; then
        print_status "$BLUE" "Current structure:"
        find "$LOCAL_BASE_DIR" -maxdepth 2 -type d -name "session_*" | sort | head -20
    fi
    
    print_status "$BLUE" "Log file: $(realpath "$LOG_FILE")"
}

# Function to confirm cleanup
confirm_cleanup() {
    if [[ "$DRY_RUN" == "true" ]]; then
        return 0  # No confirmation needed for dry-run
    fi
    
    echo
    print_status "$YELLOW" "⚠  WARNING: This will reorganize and move photo files!"
    print_status "$YELLOW" "⚠  Make sure you have backups before proceeding!"
    echo
    
    read -p "Are you sure you want to reorganize photos? (type 'YES' to confirm): " confirmation
    
    if [[ "$confirmation" != "YES" ]]; then
        print_status "$YELLOW" "Cleanup cancelled by user"
        exit 0
    fi
    
    print_status "$GREEN" "User confirmed cleanup. Proceeding..."
}

# Main function
main() {
    print_status "$BLUE" "=== Helmet Camera Photos Cleanup Tool ==="
    print_status "$BLUE" "Started at: $(date)"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_status "$PURPLE" "Running in DRY-RUN mode (no files will be moved)"
    else
        print_status "$RED" "Running in EXECUTE mode (files WILL be moved)"
    fi
    
    # Check if photos directory exists
    if [[ ! -d "$LOCAL_BASE_DIR" ]]; then
        print_status "$RED" "Photos directory not found: $LOCAL_BASE_DIR"
        exit 1
    fi
    
    # Get user confirmation for actual cleanup
    confirm_cleanup
    
    # Find all board directories
    local board_dirs=$(find "$LOCAL_BASE_DIR" -maxdepth 1 -type d -name "rpihelmet*.local" | sort)
    
    if [[ -z "$board_dirs" ]]; then
        print_status "$YELLOW" "No board directories found in $LOCAL_BASE_DIR"
        exit 0
    fi
    
    local total_boards=$(echo "$board_dirs" | wc -l)
    print_status "$BLUE" "Found $total_boards board directories to process"
    
    # Process each board
    echo "$board_dirs" | while read -r board_dir; do
        cleanup_board "$board_dir"
        consolidate_daily_sessions "$board_dir"
        echo # Add spacing between boards
    done
    
    # Show summary
    show_summary $total_boards "$DRY_RUN"
    
    print_status "$BLUE" "Cleanup completed at: $(date)"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_status "$GREEN" "Dry-run completed successfully!"
        print_status "$BLUE" "Run with --execute to perform actual cleanup"
        exit 0
    else
        print_status "$GREEN" "Cleanup completed successfully!"
        exit 0
    fi
}

# Help function
show_help() {
    cat << EOF
Helmet Camera Photos Cleanup Tool

Usage: $0 [OPTIONS]

This script cleans up problematic web sequence directories and reorganizes
photos into proper daily sessions.

Problems this fixes:
  - session_YYYYMMDD_HHMMSS_web_sequence_N directories
  - session_YYYYMMDD_HHMMSS_web_single_N directories  
  - Multiple small sessions that should be grouped by date
  - Scattered photos across many tiny session directories

Safety Features:
  - DRY-RUN mode by default (use --execute for actual cleanup)
  - Detailed logging of all operations
  - Confirmation prompts for actual changes

Options:
  -h, --help       Show this help message
  --execute        Execute actual cleanup (default is dry-run)
  --dry-run        Force dry-run mode (default)

Examples:
  $0                # Dry-run: show what would be cleaned up
  $0 --execute      # Actually reorganize photos

⚠  WARNING: Always run dry-run first to verify changes!

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
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function
main "$@" 