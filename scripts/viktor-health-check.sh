#!/usr/bin/env bash
# viktor-health-check.sh — Full system health check for Viktor.
# Checks: services running, FAISS index health, cognitive loop status,
#         brief freshness, and tracker status.
# Outputs a human-readable health report to stdout.
# Always exits 0.

set -euo pipefail

VIKTOR_WORKSPACE="${VIKTOR_WORKSPACE:-$HOME/clawd}"
VIKTOR_PYTHON="${VIKTOR_PYTHON:-$VIKTOR_WORKSPACE/vector-memory/venv/bin/python3}"
VENV_ACTIVATE="$VIKTOR_WORKSPACE/vector-memory/venv/bin/activate"
DUBAI_TZ="Asia/Dubai"

PASS="✅"
WARN="⚠️ "
FAIL="❌"

NOW="$(TZ="$DUBAI_TZ" date '+%Y-%m-%d %H:%M:%S')"
TODAY="$(TZ="$DUBAI_TZ" date '+%Y-%m-%d')"

echo "======================================"
echo " Viktor System Health Check"
echo " $NOW (Dubai)"
echo "======================================"
echo ""

# ── 1. Python venv ─────────────────────────────────────────────────────────
echo "── Python Environment ──"
if [ -f "$VENV_ACTIVATE" ]; then
    # shellcheck source=/dev/null
    source "$VENV_ACTIVATE"
    echo "$PASS venv activated: $VIKTOR_PYTHON"
else
    echo "$WARN venv not found at $VIKTOR_WORKSPACE/vector-memory/venv"
fi

if "$VIKTOR_PYTHON" -c "import faiss" 2>/dev/null; then
    echo "$PASS faiss importable"
else
    echo "$FAIL faiss not importable — FAISS recall will not work"
fi
echo ""

# ── 2. FAISS index ──────────────────────────────────────────────────────────
echo "── FAISS Index ──"
INDEX_FILE="$VIKTOR_WORKSPACE/vector-memory/memory.index"
BUILT_AT_FILE="$VIKTOR_WORKSPACE/vector-memory/index_built_at.txt"

if [ -f "$INDEX_FILE" ]; then
    INDEX_SIZE="$(du -sh "$INDEX_FILE" 2>/dev/null | cut -f1)"
    echo "$PASS index exists ($INDEX_SIZE)"
else
    echo "$FAIL index file missing: $INDEX_FILE"
fi

if [ -f "$BUILT_AT_FILE" ]; then
    BUILT_EPOCH="$(cat "$BUILT_AT_FILE" 2>/dev/null | cut -d'.' -f1)"
    if [ -n "$BUILT_EPOCH" ]; then
        BUILT_DATE="$(TZ="$DUBAI_TZ" date -r "$BUILT_EPOCH" '+%Y-%m-%d %H:%M:%S' 2>/dev/null \
                      || TZ="$DUBAI_TZ" date -d "@$BUILT_EPOCH" '+%Y-%m-%d %H:%M:%S' 2>/dev/null \
                      || echo 'unknown')"
        echo "$PASS last built: $BUILT_DATE"
    fi
else
    echo "$WARN index_built_at.txt missing — staleness tracking inactive"
fi
echo ""

# ── 3. Memory services (compaction-watcher, context-injector) ───────────────
echo "── Background Services ──"
if pgrep -f "compaction-watcher.py" >/dev/null 2>&1; then
    echo "$PASS compaction-watcher running"
else
    echo "$WARN compaction-watcher NOT running"
fi

if pgrep -f "context_injector.py" >/dev/null 2>&1; then
    echo "$PASS context-injector running"
else
    echo "$WARN context-injector NOT running"
fi
echo ""

# ── 4. Morning brief freshness ──────────────────────────────────────────────
echo "── Morning Brief ──"
BRIEF_FILE="$VIKTOR_WORKSPACE/morning-briefs/brief-${TODAY}.html"
PRESENTED_FILE="$VIKTOR_WORKSPACE/second-brain/.brief-presented-date"

if [ -f "$BRIEF_FILE" ]; then
    echo "$PASS today's brief exists: brief-${TODAY}.html"
else
    echo "$WARN today's brief NOT found (expected: $BRIEF_FILE)"
fi

if [ -f "$PRESENTED_FILE" ]; then
    PRESENTED_DATE="$(cat "$PRESENTED_FILE" 2>/dev/null)"
    if [ "$PRESENTED_DATE" = "$TODAY" ]; then
        echo "$PASS brief already presented today"
    else
        echo "$WARN brief NOT yet presented today (last: ${PRESENTED_DATE:-never})"
    fi
else
    echo "$WARN .brief-presented-date not found — brief tracking inactive"
fi
echo ""

# ── 5. Commitments tracker ──────────────────────────────────────────────────
echo "── Commitments Tracker ──"
TRACKER="$VIKTOR_WORKSPACE/COMMITMENTS_TRACKER.md"
TRACKER_SCRIPT="$VIKTOR_WORKSPACE/scripts/tracker_health.py"

if [ -f "$TRACKER" ]; then
    if [ -f "$TRACKER_SCRIPT" ]; then
        TRACKER_JSON="$("$VIKTOR_PYTHON" "$TRACKER_SCRIPT" "$TRACKER" 2>/dev/null || echo '{}')"
        PENDING="$(echo "$TRACKER_JSON" | "$VIKTOR_PYTHON" -c "import json,sys; d=json.load(sys.stdin); print(d.get('pending_count',0))" 2>/dev/null || echo '?')"
        OVERDUE="$(echo "$TRACKER_JSON" | "$VIKTOR_PYTHON" -c "import json,sys; d=json.load(sys.stdin); print(d.get('overdue_count',0))" 2>/dev/null || echo '?')"
        STALE="$(echo "$TRACKER_JSON"   | "$VIKTOR_PYTHON" -c "import json,sys; d=json.load(sys.stdin); print(d.get('stale',False))" 2>/dev/null || echo 'False')"
        echo "$PASS tracker found — pending: $PENDING, overdue: $OVERDUE, stale: $STALE"
        if [ "$OVERDUE" != "0" ] && [ "$OVERDUE" != "?" ]; then
            echo "$WARN $OVERDUE overdue commitment(s) detected"
        fi
    else
        echo "$WARN tracker_health.py not found — skipping analysis"
    fi
else
    echo "$FAIL COMMITMENTS_TRACKER.md not found at $TRACKER"
fi
echo ""

# ── 6. second-brain directory ───────────────────────────────────────────────
echo "── Second Brain ──"
SECOND_BRAIN="$VIKTOR_WORKSPACE/second-brain"
for f in "recall-failures.log" "auto-snapshot.log" "session-state.json"; do
    if [ -f "$SECOND_BRAIN/$f" ]; then
        echo "$PASS $f exists"
    else
        echo "$WARN $f missing from second-brain/"
    fi
done
echo ""

echo "======================================"
echo " Health check complete"
echo "======================================"
exit 0
