#!/bin/bash
# Stops a background focus-log started by focus_on.sh.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

PID_FILE="focus_monitor.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        kill "$PID"
        echo "Focus Monitor stopped (PID: $PID)."
    else
        echo "Focus Monitor process (PID: $PID) was not running."
    fi
    rm -f "$PID_FILE"
else
    PIDS=$(pgrep -f focus_monitor.py || true)
    if [ -n "$PIDS" ]; then
        kill $PIDS
        echo "Focus Monitor stopped."
    else
        echo "Focus Monitor is not running."
    fi
fi
