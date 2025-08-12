# Helmet Camera Photo Deletion Tool

A safe and comprehensive script for deleting photo sessions from all helmet camera boards.

## ⚠️ **SAFETY FIRST** ⚠️

**This script PERMANENTLY deletes photos from your helmet camera boards!**
- Always run in **dry-run mode first** to see what will be deleted
- Deletion is **irreversible** - make backups if needed
- Multiple confirmations required for actual deletion

## Quick Start

### 1. Check What Would Be Deleted (Safe)
```bash
./delete_photos_from_boards.sh
```
This runs in **dry-run mode** by default - no files are actually deleted.

### 2. Actually Delete All Photos (Dangerous!)
```bash
./delete_photos_from_boards.sh --execute
```
⚠️ **WARNING**: This will permanently delete ALL photos from ALL boards!

## Usage Examples

### Safe Preview Mode
```bash
# See what would be deleted from all boards
./delete_photos_from_boards.sh

# See what would be deleted from specific date
./delete_photos_from_boards.sh --date 20250801

# See what would be deleted from specific board
./delete_photos_from_boards.sh --board rpihelmet2.local
```

### Actual Deletion (Use with Caution!)
```bash
# Delete ALL photos from ALL boards
./delete_photos_from_boards.sh --execute

# Delete photos from specific date only
./delete_photos_from_boards.sh --execute --date 20250801

# Delete photos from specific board only  
./delete_photos_from_boards.sh --execute --board rpihelmet3.local

# Combine filters: specific board and date
./delete_photos_from_boards.sh --execute --board rpihelmet1.local --date 20250730
```

## Script Options

| Option | Description | Example |
|--------|-------------|---------|
| `--help` | Show help message | `./delete_photos_from_boards.sh --help` |
| `--execute` | Actually delete files (default is dry-run) | `./delete_photos_from_boards.sh --execute` |
| `--dry-run` | Force dry-run mode (default) | `./delete_photos_from_boards.sh --dry-run` |
| `--date YYYYMMDD` | Delete only from specific date | `./delete_photos_from_boards.sh --date 20250801` |
| `--board HOSTNAME` | Delete from specific board only | `./delete_photos_from_boards.sh --board rpihelmet2.local` |

## Safety Features

### 🛡️ **Multiple Safety Layers**
1. **Dry-run by default** - Shows what would be deleted without doing it
2. **Double confirmation** - Requires typing "YES" and "DELETE" for actual deletion
3. **Per-board error handling** - Continues if one board fails
4. **Detailed logging** - Everything is logged with timestamps
5. **Connection testing** - Verifies each board is reachable before proceeding

### 📋 **What Gets Deleted**
- `/home/rpi/helmet-cam{N}/session_*` directories
- All `.jpg` photo files in session directories  
- `session_log.json` and `master_imu_data.json` files
- **Does NOT delete** system files, configurations, or programs

## Configuration

Edit the script to match your setup:

```bash
# SSH Settings
REMOTE_USER="rpi"                    # Username on boards
SSH_KEY="~/.ssh/id_rsa"             # SSH key path (optional)
SSH_PORT="22"                       # SSH port

# Boards to process
BOARDS=(
    "rpihelmet1.local:1"
    "rpihelmet2.local:2"
    # ... add your boards
)
```

## Example Output

### Dry-Run Mode (Safe)
```
[2025-08-05 13:36:25] Running in DRY-RUN mode (no files will be deleted)
[2025-08-05 13:36:25] === [DRY-RUN] Processing rpihelmet1.local (cam1) ===
[2025-08-05 13:36:28] [DRY-RUN] Would delete from rpihelmet1.local:
[2025-08-05 13:36:28]   - 9 sessions
[2025-08-05 13:36:28]   - 87 photos  
[2025-08-05 13:36:28]   - 25.3MB of data
[2025-08-05 13:36:28]   - session_20250730
[2025-08-05 13:36:28]   - session_20250731
[2025-08-05 13:36:30] Dry-run completed successfully!
```

### Execute Mode (Dangerous)
```
[2025-08-05 13:40:15] Running in EXECUTE mode (files WILL be deleted)
⚠  WARNING: This will PERMANENTLY DELETE photos from all boards!
⚠  This action CANNOT be undone!

Are you absolutely sure you want to delete photos? (type 'YES' to confirm): YES

Last chance! Type 'DELETE' to proceed: DELETE

[2025-08-05 13:40:25] User confirmed deletion. Proceeding...
[2025-08-05 13:40:25] DELETING from rpihelmet1.local: 9 sessions, 87 photos, 25.3MB
[2025-08-05 13:40:27] ✓ Successfully deleted all sessions from rpihelmet1.local
```

## Use Cases

### 🧹 **Regular Cleanup**
```bash
# Weekly cleanup of old photos
./delete_photos_from_boards.sh --execute --date 20250720
```

### 🔧 **Development/Testing**
```bash
# Clear test data from one board
./delete_photos_from_boards.sh --execute --board rpihelmet7.local
```

### 💾 **Storage Management**
```bash
# Free up space - delete everything (after backup!)
./delete_photos_from_boards.sh --execute
```

### 🎯 **Selective Cleanup**
```bash
# Clean specific sessions (check first, then execute)
./delete_photos_from_boards.sh --date 20250801
./delete_photos_from_boards.sh --execute --date 20250801
```

## Best Practices

### ✅ **Before Deletion**
1. **Always backup important photos** using transfer scripts first
2. **Run dry-run mode** to verify what will be deleted
3. **Test network connectivity** to all boards
4. **Check free space** - deletion might not be necessary

### ✅ **During Deletion**
1. **Monitor the output** for any errors
2. **Don't interrupt** the process once started
3. **Check logs** if any boards fail

### ✅ **After Deletion**
1. **Verify results** by checking board storage
2. **Save log files** for record keeping
3. **Test camera functionality** to ensure boards still work

## Troubleshooting

### SSH Connection Issues
```bash
# Test SSH manually
ssh rpi@rpihelmet1.local

# Check SSH keys
ssh-add -l
```

### Permission Errors
```bash
# Ensure script is executable
chmod +x delete_photos_from_boards.sh

# Check SSH permissions
chmod 600 ~/.ssh/id_rsa
```

### Partial Failures
- Script continues if individual boards fail
- Check log file for detailed error messages
- Re-run for failed boards only using `--board` option

## Related Scripts

- `transfer_photos_rsync.sh` - Download photos before deletion
- `transfer_photos_scp.sh` - Alternative download method
- See `TRANSFER_README.md` for backup procedures

---

## ⚠️ **FINAL WARNING** ⚠️

**Photo deletion is PERMANENT and cannot be undone!**

Always:
1. 📥 **Backup first** using transfer scripts
2. 🧪 **Test with dry-run** mode  
3. 🎯 **Use specific filters** when possible
4. 📝 **Keep logs** for accountability

*"Measure twice, delete once"* 🔧 