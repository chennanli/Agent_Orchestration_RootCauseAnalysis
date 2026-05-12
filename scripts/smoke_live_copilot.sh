#!/usr/bin/env bash
# Live Copilot Phase 1 smoke test.
#
# Starts the FastAPI backend (port 8000), hits every endpoint the new
# nat_api_live + sim_control routers expose, and reports pass/fail. Does
# NOT start unified_console.py; the sim routes are expected to report
# `sim_alive: false` here.
#
# Usage:
#   scripts/smoke_live_copilot.sh           # against seeded fault4 (fast)
#   FAULT=fault1 scripts/smoke_live_copilot.sh
#
# Exits 0 on success, 1 on the first failure. Backend is left running so
# you can re-curl manually; kill it with `pkill -f 'backend/app.py'`.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

FAULT="${FAULT:-fault4}"
PY=".venv/bin/python"
PORT=8000
LOG="/tmp/tep_smoke_backend.log"

step() { printf "\n\033[1;36m== %s ==\033[0m\n" "$*"; }
fail() { printf "\033[1;31mFAIL:\033[0m %s\n" "$*"; exit 1; }
ok()   { printf "\033[1;32mOK:\033[0m %s\n" "$*"; }

step "ensure port $PORT is free"
pkill -f "backend/app.py" 2>/dev/null
sleep 1
if lsof -i ":$PORT" -t >/dev/null 2>&1; then
  fail "port $PORT still occupied after pkill"
fi

step "start backend (logs at $LOG)"
$PY backend/app.py > "$LOG" 2>&1 &
BACKEND_PID=$!
echo "pid=$BACKEND_PID"

step "wait for /api/anomaly/state to respond (up to 30s)"
for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:$PORT/api/anomaly/state" >/dev/null 2>&1; then
    ok "backend is alive after ${i}s"
    break
  fi
  sleep 1
done
if ! curl -sf "http://127.0.0.1:$PORT/api/anomaly/state" >/dev/null 2>&1; then
  tail -40 "$LOG"
  fail "backend never became responsive"
fi

step "GET /api/anomaly/state"
curl -s "http://127.0.0.1:$PORT/api/anomaly/state" | $PY -m json.tool || fail "anomaly_state JSON malformed"

step "GET /api/agent/runs?limit=2"
RUNS_COUNT=$(curl -s "http://127.0.0.1:$PORT/api/agent/runs?limit=2" \
  | $PY -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('runs',[])))")
[ "$RUNS_COUNT" -ge 0 ] || fail "runs list malformed"
ok "runs list returned $RUNS_COUNT items"

step "GET /api/sim/status (unified_console NOT running)"
curl -s "http://127.0.0.1:$PORT/api/sim/status" | $PY -m json.tool || fail "sim/status JSON malformed"

step "POST /api/agent/diagnose with empty buffer (expect 409)"
HTTP=$(curl -s -o /tmp/d409.json -w "%{http_code}" -X POST \
  "http://127.0.0.1:$PORT/api/agent/diagnose" \
  -H 'content-type: application/json' -d '{}')
[ "$HTTP" = "409" ] || fail "empty-buffer diagnose expected 409, got $HTTP"
ok "diagnose with empty buffer returned 409 as expected"

step "POST /api/agent/diagnose with seeded $FAULT"
RUN_ID=$(curl -s -X POST "http://127.0.0.1:$PORT/api/agent/diagnose" \
  -H 'content-type: application/json' \
  -d "{\"fault_id\":\"$FAULT\",\"question\":\"Diagnose $FAULT briefly.\"}" \
  | $PY -c "import sys,json; print(json.load(sys.stdin)['run_id'])")
echo "RUN_ID=$RUN_ID"
[ -n "$RUN_ID" ] || fail "diagnose did not return a run_id"

step "GET /api/agent/runs/${RUN_ID}/stream (up to 3 min, looking for event: done)"
if curl -sN --max-time 180 "http://127.0.0.1:$PORT/api/agent/runs/${RUN_ID}/stream" \
     | tee /tmp/sse.log | grep -q "^event: done"; then
  STEP_COUNT=$(grep -c "^event: step" /tmp/sse.log || true)
  ok "SSE produced $STEP_COUNT step events and 1 done event"
else
  tail -30 /tmp/sse.log
  fail "SSE stream did not emit event: done within 3 min"
fi

step "GET /api/agent/runs/${RUN_ID} (saved JSON)"
curl -sf "http://127.0.0.1:$PORT/api/agent/runs/${RUN_ID}" | $PY -c "
import sys,json
d=json.load(sys.stdin)
assert d.get('mode')=='nat', f'mode is {d.get(\"mode\")}'
assert d.get('final_answer',{}).get('text'), 'final_answer.text empty'
print('saved run runtime:', d.get('runtime_seconds'), 'sec')
" || fail "saved run JSON not loadable / fields missing"

step "POST /api/agent/runs/${RUN_ID}/followup"
curl -sf -X POST "http://127.0.0.1:$PORT/api/agent/runs/${RUN_ID}/followup" \
  -H 'content-type: application/json' \
  -d '{"question":"Which sensor would you check next, and why?"}' \
  | $PY -m json.tool || fail "followup endpoint did not return JSON"

step "all phase 1 backend smokes passed"
echo "backend is still running on port $PORT (pid $BACKEND_PID); kill with: pkill -f 'backend/app.py'"
