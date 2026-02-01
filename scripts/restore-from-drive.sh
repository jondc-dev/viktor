#!/bin/bash
# Restore workspace from Google Drive backup
# Usage: ./restore-from-drive.sh [backup-name]
#   - No args: lists available backups
#   - With arg: restores that specific backup
#   - "latest": restores most recent backup

set -e

DRIVE_FOLDER="***Important Backups***/viktor-backups"
RESTORE_DIR="/Users/victor/clawd"
TEMP_DIR="/tmp/clawd-restore-$$"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cleanup() {
    rm -rf "$TEMP_DIR" 2>/dev/null || true
}
trap cleanup EXIT

list_backups() {
    echo -e "${YELLOW}Available backups on Google Drive:${NC}"
    rclone lsf "gdrive:$DRIVE_FOLDER/" --files-only 2>/dev/null | grep "^clawd-backup-" | sort -r
}

get_latest() {
    rclone lsf "gdrive:$DRIVE_FOLDER/" --files-only 2>/dev/null | grep "^clawd-backup-" | sort -r | head -1
}

restore_backup() {
    local BACKUP_NAME="$1"
    
    # Handle "latest" keyword
    if [ "$BACKUP_NAME" = "latest" ]; then
        BACKUP_NAME=$(get_latest)
        if [ -z "$BACKUP_NAME" ]; then
            echo -e "${RED}No backups found on Google Drive${NC}"
            exit 1
        fi
        echo -e "${YELLOW}Latest backup: $BACKUP_NAME${NC}"
    fi
    
    # Validate backup exists
    if ! rclone lsf "gdrive:$DRIVE_FOLDER/$BACKUP_NAME" &>/dev/null; then
        echo -e "${RED}Backup not found: $BACKUP_NAME${NC}"
        echo "Use '$0' without arguments to list available backups"
        exit 1
    fi
    
    echo -e "${YELLOW}Downloading $BACKUP_NAME...${NC}"
    mkdir -p "$TEMP_DIR"
    rclone copy "gdrive:$DRIVE_FOLDER/$BACKUP_NAME" "$TEMP_DIR/" --progress
    
    echo -e "${YELLOW}Creating pre-restore backup...${NC}"
    PRE_RESTORE="/tmp/clawd-pre-restore-$(date +%Y%m%d_%H%M%S).zip"
    (cd "$RESTORE_DIR" && zip -r "$PRE_RESTORE" . -x "*.git/*" -x "*/venv/*" -x "*/__pycache__/*" -x "*.pyc") || true
    echo -e "${GREEN}Pre-restore backup saved: $PRE_RESTORE${NC}"
    
    echo -e "${YELLOW}Extracting backup...${NC}"
    mkdir -p "$TEMP_DIR/extracted"
    unzip -o "$TEMP_DIR/$BACKUP_NAME" -d "$TEMP_DIR/extracted"
    
    echo -e "${YELLOW}Restoring files...${NC}"
    # Restore files, preserving .git and venv
    rsync -av --exclude='.git' --exclude='venv' --exclude='__pycache__' \
        "$TEMP_DIR/extracted/" "$RESTORE_DIR/"
    
    echo -e "${GREEN}✓ Restore complete from: $BACKUP_NAME${NC}"
    echo -e "${GREEN}✓ Pre-restore backup at: $PRE_RESTORE${NC}"
}

# Main
if [ -z "$1" ]; then
    list_backups
    echo ""
    echo "Usage: $0 <backup-name>  - restore specific backup"
    echo "       $0 latest         - restore most recent backup"
else
    restore_backup "$1"
fi
