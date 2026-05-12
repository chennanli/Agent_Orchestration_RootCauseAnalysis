#!/bin/bash

# TEP Unified Control System - Stop Script

cd "$(dirname "$0")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🛑 TEP Unified Control System - Stopping..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Kill by PID files
if [ -f ".console.pid" ]; then
    PID=$(cat .console.pid)
    kill -9 $PID 2>/dev/null && echo "✅ Stopped Unified Console (PID: $PID)"
    rm .console.pid
fi

if [ -f ".backend.pid" ]; then
    PID=$(cat .backend.pid)
    kill -9 $PID 2>/dev/null && echo "✅ Stopped Backend API (PID: $PID)"
    rm .backend.pid
fi

if [ -f ".frontend.pid" ]; then
    PID=$(cat .frontend.pid)
    kill -9 $PID 2>/dev/null && echo "✅ Stopped Frontend (PID: $PID)"
    rm .frontend.pid
fi

# 🔧 NEW: Kill TEP Bridge (this was missing!)
echo ""
echo "Stopping TEP Bridge..."
pkill -f "tep_faultexplainer_bridge" && echo "✅ Stopped TEP Bridge" || echo "⚠️  TEP Bridge not running"

# Kill by port (backup method)
echo ""
echo "Checking for remaining processes..."
kill -9 $(lsof -ti :9002) 2>/dev/null && echo "✅ Killed process on port 9002"
kill -9 $(lsof -ti :8000) 2>/dev/null && echo "✅ Killed process on port 8000"
kill -9 $(lsof -ti :5173) 2>/dev/null && echo "✅ Killed process on port 5173"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All Services Stopped"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
