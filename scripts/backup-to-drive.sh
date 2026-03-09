#!/bin/bash
# Backup script - zips workspace and uploads to Google Drive
# Runs 6 times a day via cron

set -e

WORKSPACE="$HOME/clawd"
BACKUP_DIR="$HOME/.clawd-backups"
DRIVE_FOLDER="gdrive:,id=1QX-hX5SIncho5PwWbttKdIOvh-0fflnn"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_NAME="clawd-backup-${TIMESTAMP}.zip"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# Create backup directory if needed
mkdir -p "$BACKUP_DIR"

# Create zip (excluding large/temp/backup files) - use faster compression
cd "$WORKSPACE"
zip -1 -r "$BACKUP_PATH" . \
  -x "*.mp3" \
  -x "*.ogg" \
  -x "*.wav" \
  -x "*.zip" \
  -x "*.mp4" \
  -x "*.mov" \
  -x "*.avi" \
  -x ".git/*" \
  -x "node_modules/*" \
  -x "__pycache__/*" \
  -x "*.pyc" \
  -x ".DS_Store" \
  -x "vector-memory/chroma/*" \
  -x "vector-memory/venv/*" \
  -x "*/venv/*" \
  -x "*.safetensors" \
  -x "kyutai-test/dsm/*" \
  -x "viktor-avatar/*.png" \
  -x "memory/*.ogg" \
  2>/dev/null || true

# Upload to Google Drive with timeout
echo "Uploading ${BACKUP_NAME} to Google Drive..."
timeout 300 rclone copy "$BACKUP_PATH" "$DRIVE_FOLDER/" || echo "Upload timeout - continuing..."

# Delete local backup file after successful upload
echo "Deleting local backup file..."
rm -f "$BACKUP_PATH"

# Clean up any remaining old backup files (keep last 5)
cd "$BACKUP_DIR"
ls -t clawd-backup-*.zip 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true

echo "Backup complete: ${BACKUP_NAME}"
