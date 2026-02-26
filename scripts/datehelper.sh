#!/usr/bin/env bash
# datehelper.sh — Dubai timezone date utility for Viktor scripts.
# Usage: source scripts/datehelper.sh
#   or:  scripts/datehelper.sh [today|yesterday|tomorrow|format <strftime_fmt>]
#
# Exports:
#   DUBAI_TZ  — "Asia/Dubai"
#   DUBAI_DATE — today's date in Dubai time (YYYY-MM-DD)
#   DUBAI_DATETIME — full datetime in Dubai time (YYYY-MM-DD HH:MM:SS)

DUBAI_TZ="Asia/Dubai"

dubai_date() {
    TZ="$DUBAI_TZ" date +"%Y-%m-%d"
}

dubai_datetime() {
    TZ="$DUBAI_TZ" date +"%Y-%m-%d %H:%M:%S"
}

dubai_format() {
    local fmt="${1:-%Y-%m-%d}"
    TZ="$DUBAI_TZ" date +"$fmt"
}

dubai_yesterday() {
    TZ="$DUBAI_TZ" date -v-1d +"%Y-%m-%d" 2>/dev/null \
        || TZ="$DUBAI_TZ" date -d "yesterday" +"%Y-%m-%d"
}

dubai_tomorrow() {
    TZ="$DUBAI_TZ" date -v+1d +"%Y-%m-%d" 2>/dev/null \
        || TZ="$DUBAI_TZ" date -d "tomorrow" +"%Y-%m-%d"
}

# Export convenience variables when sourced
DUBAI_DATE="$(dubai_date)"
DUBAI_DATETIME="$(dubai_datetime)"
export DUBAI_TZ DUBAI_DATE DUBAI_DATETIME

# If executed directly (not sourced), handle CLI args
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-today}" in
        today)     dubai_date ;;
        yesterday) dubai_yesterday ;;
        tomorrow)  dubai_tomorrow ;;
        datetime)  dubai_datetime ;;
        format)    dubai_format "${2:-%Y-%m-%d}" ;;
        *)
            echo "Usage: datehelper.sh [today|yesterday|tomorrow|datetime|format <fmt>]" >&2
            exit 1
            ;;
    esac
fi
