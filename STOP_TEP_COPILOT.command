#!/bin/bash
# Kill every process started by START_TEP_COPILOT.command.

cd "$(dirname "$0")"

printf "Stopping TEP Live Copilot stack...\n"
pkill -f "backend/app.py" 2>/dev/null && echo "  ✓ backend stopped" || echo "  - backend not running"
pkill -f "python.*unified_console.py" 2>/dev/null && echo "  ✓ unified console stopped" || echo "  - unified console not running"
pkill -f "vite" 2>/dev/null && echo "  ✓ frontend (vite) stopped" || echo "  - frontend not running"

sleep 1
printf "\nRemaining processes on TEP ports:\n"
for p in 8000 9002 5173 5174; do
  if lsof -i ":$p" -t >/dev/null 2>&1; then
    echo "  port $p still occupied:"
    lsof -i ":$p" | head -3
  else
    echo "  port $p free"
  fi
done

echo
echo "Done. Close this window."
