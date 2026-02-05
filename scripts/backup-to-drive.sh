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

# Create zip (excluding large/temp/backup files)
cd "$WORKSPACE"
zip -r "$BACKUP_PATH" . \
  -x "*.mp3" \
  -x "*.ogg" \
  -x "*.wav" \
  -x "*.zip" \
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
  2>/dev/null || true

# Upload to Google Drive
echo "Uploading ${BACKUP_NAME} to Google Drive..."
rclone copy "$BACKUP_PATH" "$DRIVE_FOLDER/"

# Delete local backup file after successful upload
echo "Deleting local backup file..."
rm -f "$BACKUP_PATH"

# Clean up any remaining old backup files
cd "$BACKUP_DIR"
rm -f clawd-backup-*.zip 2>/dev/null || true

echo "Backup complete: ${BACKUP_NAME}"
