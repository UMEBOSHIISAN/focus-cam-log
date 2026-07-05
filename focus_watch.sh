#!/bin/bash
# Live view of what focus-cam-log is currently detecting. Run this in a
# separate terminal window/tab while focus_on.sh is running in the background.
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

LOG_FILE="focus_monitor.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "No $LOG_FILE yet — start the monitor first with ./focus_on.sh"
    exit 1
fi

echo "=== focus-cam-log: live activity feed (Ctrl+C to stop watching) ==="
echo "This only tails the log — it does not stop or affect the monitor."
echo

tail -n 5 -f "$LOG_FILE" | grep --line-buffered -E "Logged:|Focus drift|フォーカスのゆらぎ|Provider:|Mode:"
