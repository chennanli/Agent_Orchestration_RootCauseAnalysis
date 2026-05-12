#!/bin/bash
# Double-click this file on macOS to launch the full TEP Live Copilot stack:
#
#   1. Backend  (FastAPI)        — port 8000   [REQUIRED]
#   2. Unified  (Fortran sim)    — port 9002   [optional, gives live data]
#   3. Frontend (React/Vite)     — port 5173   [REQUIRED]
#
# Logs land in /tmp/tep_*.log. Browser opens automatically on port 5173.
# Press Ctrl+C in any open Terminal window or run `pkill -f "backend/app.py"` /
# `pkill -f unified_console.py` / `pkill -f vite` to stop the stack.

set -euo pipefail

cd "$(dirname "$0")"
REPO_ROOT="$(pwd)"
PY="$REPO_ROOT/.venv/bin/python"

bold() { printf "\033[1;36m%s\033[0m\n" "$*"; }
ok()   { printf "\033[1;32m✓ %s\033[0m\n" "$*"; }
warn() { printf "\033[1;33m! %s\033[0m\n" "$*"; }
fail() { printf "\033[1;31m✗ %s\033[0m\n" "$*"; }

bold "TEP Live Copilot — one-click launcher"
echo "Repo:  $REPO_ROOT"
echo "Logs:  /tmp/tep_backend.log  /tmp/tep_unified.log  /tmp/tep_frontend.log"
echo

# ----- prerequisite check -----
if [ ! -x "$PY" ]; then
  fail "venv not found at .venv/. Run: uv sync --extra nat   (or pip install -r ...)"
  exit 1
fi

if [ ! -d frontend/node_modules ]; then
  warn "frontend/node_modules missing — installing now (one-time, ~60s)"
  (cd frontend && npm install)
fi

# ----- 1. backend -----
bold "[1/3] backend (port 8000)"
pkill -f "backend/app.py" 2>/dev/null || true
sleep 1
"$PY" backend/app.py > /tmp/tep_backend.log 2>&1 &
BACKEND_PID=$!
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8000/api/anomaly/state >/dev/null 2>&1; then
    ok "backend up (pid $BACKEND_PID) after ${i}s"
    break
  fi
  sleep 1
done
if ! curl -sf http://127.0.0.1:8000/api/anomaly/state >/dev/null 2>&1; then
  fail "backend never responded — see /tmp/tep_backend.log"
  tail -20 /tmp/tep_backend.log
  exit 1
fi

# ----- 2. unified_console (Fortran sim driver) -----
bold "[2/3] Fortran sim driver (port 9002) — optional"
pkill -f "python.*unified_console.py" 2>/dev/null || true
sleep 1
"$PY" unified_console.py > /tmp/tep_unified.log 2>&1 &
UNIFIED_PID=$!

UNIFIED_UP=0
for i in $(seq 1 25); do
  if curl -sf http://127.0.0.1:9002/api/status >/dev/null 2>&1; then
    UNIFIED_UP=1
    ok "unified console up (pid $UNIFIED_PID) after ${i}s"
    break
  fi
  sleep 1
done

if [ $UNIFIED_UP -eq 1 ]; then
  bold "    starting Fortran simulation at 50x speed (POST /api/ultra_start)"
  if curl -sf -X POST http://127.0.0.1:9002/api/ultra_start \
       -H 'content-type: application/json' -d '{}' >/dev/null 2>&1; then
    ok "Fortran sim started; live data will flow into /ingest within ~5s"
  else
    warn "could not auto-start sim — open http://localhost:9002 and click Start"
  fi
else
  warn "unified_console did not come up — live data will be unavailable"
  warn "you can still test the agent with pre-baked faults (fault0..14)"
  warn "see /tmp/tep_unified.log for the reason"
fi

# ----- 3. frontend (vite dev server) -----
bold "[3/3] frontend (port 5173)"
pkill -f "vite" 2>/dev/null || true
sleep 1
(cd frontend && nohup npm run dev > /tmp/tep_frontend.log 2>&1) &
FRONTEND_PID=$!
for i in $(seq 1 30); do
  if curl -sf -o /dev/null -w "%{http_code}" http://127.0.0.1:5173/ 2>/dev/null | grep -q "^200$"; then
    ok "frontend up (pid $FRONTEND_PID) after ${i}s"
    break
  fi
  sleep 1
done

echo
bold "All set."
echo
echo "Open in your browser:"
echo "  • Live Copilot (new UI): http://localhost:5173/"
echo "  • Fortran control panel (Flask): http://localhost:9002/"
echo "  • Backend API root: http://localhost:8000/"
echo
echo "Stop the stack later with:"
echo "  pkill -f 'backend/app.py' ; pkill -f unified_console.py ; pkill -f vite"
echo

# Open the browser automatically on macOS
if command -v open >/dev/null 2>&1; then
  open "http://localhost:5173/"
fi

# Keep the Terminal window alive so the user can see the log tails if they want
echo "Tailing all three logs (Ctrl+C to detach without stopping servers):"
echo
tail -f /tmp/tep_backend.log /tmp/tep_unified.log /tmp/tep_frontend.log
