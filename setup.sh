#!/bin/bash
# One-time setup: creates a virtual environment and installs dependencies.
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=== focus-log setup ==="

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo
echo "Setup complete. Next steps:"
echo "  1. export GEMINI_API_KEY=your-key   (or put GEMINI_API_KEY=... in ~/.focus-log/env)"
echo "  2. ./focus_on.sh                    (start monitoring in the background)"
echo "  3. ./focus_off.sh                   (stop monitoring)"
