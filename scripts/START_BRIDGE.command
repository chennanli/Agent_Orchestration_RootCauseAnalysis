#!/bin/bash

cd "$(dirname "$0")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌉 Starting TEP-FaultExplainer Data Bridge"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo "✅ Found virtual environment: .venv/"
    source .venv/bin/activate
else
    echo "⚠️  Virtual environment not found, using system Python"
fi

echo ""
echo "📋 Prerequisites Check:"
echo ""

# Check if backend is running
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "✅ Backend is running on port 8000"
else
    echo "❌ Backend is NOT running on port 8000"
    echo "   Please start backend first with:"
    echo "   cd backend && python app.py"
    echo ""
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

# Check if live data file exists
if [ -f "data/live_tep_data.csv" ]; then
    FILE_SIZE=$(stat -f%z "data/live_tep_data.csv" 2>/dev/null || stat -c%s "data/live_tep_data.csv" 2>/dev/null)
    if [ "$FILE_SIZE" -gt 0 ]; then
        echo "✅ Live data file exists with data ($FILE_SIZE bytes)"
    else
        echo "⚠️  Live data file is empty (TEP simulation might not be running)"
    fi
else
    echo "⚠️  Live data file does not exist yet"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Starting Bridge..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 The bridge will:"
echo "   1. Monitor data/live_tep_data.csv for new data"
echo "   2. Send each data point to http://127.0.0.1:8000/ingest"
echo "   3. Keep running until you press Ctrl+C"
echo ""
echo "Press Ctrl+C to stop the bridge"
echo ""

# Start the bridge
.venv/bin/python3 backend/tep_faultexplainer_bridge.py

# Keep terminal open on error
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Bridge exited with error"
    echo ""
    echo "Press any key to close..."
    read -n 1
fi
