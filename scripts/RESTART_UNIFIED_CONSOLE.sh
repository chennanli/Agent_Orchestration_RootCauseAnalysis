#!/bin/bash
# Restart Unified Console with New Code
# This script stops the old process and starts a new one

echo "🔄 Restarting Unified Console..."

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Stop old process
echo "🛑 Stopping old unified console process..."
pkill -f "python.*unified_console.py"
sleep 2

# Verify stopped
if pgrep -f "python.*unified_console.py" > /dev/null; then
    echo "⚠️  Force killing old process..."
    pkill -9 -f "python.*unified_console.py"
    sleep 1
fi

# Start new process
echo "🚀 Starting unified console with new code..."
.venv/bin/python3 unified_console.py

echo "✅ Unified console restarted!"
