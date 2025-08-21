# Helmet Camera Photo Transfer Scripts

Two bash scripts for transferring photo sessions from all helmet camera boards to your local PC.

## Scripts Overview

### 1. `transfer_photos_rsync.sh` - Incremental Sync ⚡
- **Best for**: Regular backups and incremental updates
- **Features**: 
  - Only downloads new/changed files
  - Resume interrupted transfers
  - Bandwidth efficient
  - Perfect for daily sync routines

### 2. `transfer_photos_scp.sh` - Complete Copy 📁
- **Best for**: Full downloads and one-time transfers  
- **Features**:
  - Downloads complete sessions
  - Parallel transfers for speed
  - Skip existing sessions
  - Simple and reliable

## Quick Start

### 1. Configure Board Addresses
Edit the scripts to match your helmet camera setup:

```bash
# Edit either script
vim transfer_photos_rsync.sh
# or
vim transfer_photos_scp.sh
```

Update the `BOARDS` array with your actual hostnames/IPs:
```bash
declare -a BOARDS=(
    "rpihelmet1.local:1"    # Master board (cam1)
    "rpihelmet2.local:2"    # rpihelmet2 (cam2)
    "rpihelmet3.local:3"    # rpihelmet3 (cam3)
    "rpihelmet4.local:4"    # rpihelmet4 (cam4)
    "rpihelmet5.local:5"    # rpihelmet5 (cam5)
    "rpihelmet6.local:6"    # rpihelmet6 (cam6)
    "rpihelmet7.local:7"    # rpihelmet7 (cam7)
)
```

### 2. Run the Transfer

**Option A: Incremental Sync (Recommended)**
```bash
./transfer_photos_rsync.sh
```

**Option B: Complete Copy**
```bash
./transfer_photos_scp.sh
```

## Directory Structure Created

```
helmet_photos/
├── rpihelmet1.local/
│   └── helmet-cam1/
│       ├── session_20250115/
│       │   ├── cam1_20250115_143022_001.jpg
│       │   ├── cam1_20250115_143027_002.jpg
│       │   ├── session_log.json
│       │   └── master_imu_data.json
│       └── session_20250116/
├── rpihelmet2.local/
│   └── helmet-cam2/
│       └── session_20250115/
├── rpihelmet3.local/
│   └── helmet-cam3/
└── ...
```

## Configuration Options

Edit these variables in the scripts:

```bash
# SSH Settings
REMOTE_USER="rpi"                    # Username on boards
SSH_KEY="~/.ssh/id_rsa"             # SSH key path (optional)
SSH_PORT="22"                       # SSH port

# Paths
REMOTE_BASE_DIR="/home/rpi"         # Remote base directory
LOCAL_BASE_DIR="./helmet_photos"    # Local download directory

# SCP Script Only
PARALLEL_JOBS=3                     # Concurrent transfers
```

## Usage Examples

### Daily Backup Routine
```bash
# Create a daily backup script
cat > daily_backup.sh << 'EOF'
#!/bin/bash
cd /path/to/helmet_photos_backup
./transfer_photos_rsync.sh
EOF

chmod +x daily_backup.sh

# Add to crontab for automatic daily backups
crontab -e
# Add: 0 2 * * * /path/to/daily_backup.sh
```

### One-time Full Download
```bash
# Download everything in parallel
./transfer_photos_scp.sh

# Or force sequential if network is slow
./transfer_photos_scp.sh --sequential
```

### Specific Date Range (Manual)
```bash
# After running either script, filter by date
find helmet_photos/ -name "session_202501*" -type d
```

## Troubleshooting

### SSH Connection Issues
```bash
# Test SSH connection manually
ssh rpi@rpihelmet1.local

# If using SSH keys
ssh -i ~/.ssh/id_rsa rpi@rpihelmet1.local

# Add your public key to boards
ssh-copy-id rpi@rpihelmet1.local
```

### Network Connectivity
```bash
# Test ping to all boards
ping rpihelmet1.local
ping rpihelmet2.local
# ... etc
```

### Permission Errors
```bash
# Ensure scripts are executable
chmod +x transfer_photos_*.sh

# Check SSH key permissions
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
```

### Large Transfers
```bash
# For very large transfers, use screen/tmux
screen -S transfer
./transfer_photos_rsync.sh
# Ctrl+A, D to detach

# Reattach later
screen -r transfer
```

## Log Files

Both scripts create detailed log files:
- `transfer_YYYYMMDD_HHMMSS.log` (rsync)
- `transfer_scp_YYYYMMDD_HHMMSS.log` (scp)

Check logs for detailed transfer information and error debugging.

## Advanced Usage

### Custom SSH Configuration
Create `~/.ssh/config`:
```
Host rpihelmet*.local
    User rpi
    IdentityFile ~/.ssh/helmet_key
    StrictHostKeyChecking no
    ConnectTimeout 10

# Optional: Add aliases for shorter names
Host helmet1
    HostName rpihelmet1.local

Host helmet2
    HostName rpihelmet2.local
```

### Bandwidth Limiting (rsync)
Edit rsync script and add to rsync options:
```bash
rsync_opts="$rsync_opts --bwlimit=1000"  # Limit to 1MB/s
```

### Exclude Certain Files
Add to rsync options:
```bash
rsync_opts="$rsync_opts --exclude='*.tmp' --exclude='test_*'"
```

## Performance Comparison

| Feature | rsync | scp |
|---------|-------|-----|
| Speed (first run) | Medium | Fast |
| Speed (subsequent) | Very Fast | Fast |
| Bandwidth usage | Low | High |
| Resume capability | Yes | No |
| Parallel transfers | No | Yes |
| Best for | Regular sync | One-time copy |

## Examples Output

### Successful Transfer
```
[2025-01-15 14:30:15] === Helmet Camera Photos Transfer (rsync) ===
[2025-01-15 14:30:15] ✓ Prerequisites check passed
[2025-01-15 14:30:16] ✓ rpihelmet1.local is reachable
[2025-01-15 14:30:17] Found: session_20250115 (45 photos, 12MB)
[2025-01-15 14:30:20] ✓ Successfully synced rpihelmet1.local
[2025-01-15 14:30:25] === Transfer Summary ===
[2025-01-15 14:30:25] Successfully synced: 7/7 boards
[2025-01-15 14:30:25] Total downloaded: 15 sessions, 312 photos, 89MB
```

## Support

For issues or questions:
1. Check the log files for detailed error messages
2. Verify network connectivity to all boards
3. Ensure SSH access is properly configured
4. Test with a single board first before running full transfer 