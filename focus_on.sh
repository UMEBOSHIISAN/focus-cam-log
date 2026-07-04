#!/bin/bash
# Starts focus-cam-log in the background. Extra arguments are passed through
# to focus_monitor.py (e.g. ./focus_on.sh --interval 5 --save-photos --lang en).
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

PID_FILE="focus_monitor.pid"
LOG_FILE="focus_monitor.log"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Focus Monitor is already running (PID: $PID)."
        exit 0
    fi
fi

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Run ./setup.sh first."
    exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate

if [ -z "$GEMINI_API_KEY" ]; then
    echo "Note: GEMINI_API_KEY is not set in this shell;"
    echo "focus_monitor.py will also look in \${FOCUS_LOG_DATA_DIR:-~/.focus-log}/env."
fi

nohup python3 focus_monitor.py --watch "$@" > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Focus Monitor started in the background (PID: $(cat "$PID_FILE"))."
echo "Logs: $DIR/$LOG_FILE"
