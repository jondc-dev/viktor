#!/usr/bin/env bash
# now.sh — Quick Dubai-time timestamp for Viktor scripts.
# Usage: scripts/now.sh [format]
#   Default format: YYYY-MM-DD HH:MM:SS
#   Example: scripts/now.sh "+%H:%M"

DUBAI_TZ="Asia/Dubai"
FMT="${1:-%Y-%m-%d %H:%M:%S}"

TZ="$DUBAI_TZ" date +"$FMT"
