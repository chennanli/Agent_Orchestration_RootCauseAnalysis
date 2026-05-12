#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Real NAT verification script.
#
# Run this on your Mac (Python 3.11+ required by nvidia-nat). It does:
#   1. Builds / reuses a uv venv with the `nat` extra
#   2. Loads NVIDIA_API_KEY from .env (bash 3.2 safe loader)
#   3. Confirms the `nat` CLI is installed
#   4. Runs the real NAT workflow against fault1
#   5. Re-runs the evaluator with --run-agent for real-LLM workflow metrics
#
# Usage (run from the repo root):
#   bash scripts/test_nat_real.sh
# -----------------------------------------------------------------------------

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Repo: $REPO_ROOT"

if [ ! -f .env ]; then
  echo "ERROR: .env not found at $REPO_ROOT/.env" >&2
  echo "       Copy .env.template to .env and add NVIDIA_API_KEY=nvapi-..." >&2
  exit 1
fi

# ----- 1. Load NVIDIA_API_KEY from .env into the current shell --------------
#
# Bash 3.2 friendly (macOS default /bin/bash). Reads the file line by line,
# strips inline comments / surrounding whitespace, and exports only the
# keys we actually want. No process substitution, no eval surprises.
load_env_key() {
  local target_key="$1"
  local line key val
  while IFS= read -r line || [ -n "$line" ]; do
    # Strip CR (Windows line endings) and leading whitespace.
    line="${line%$'\r'}"
    line="${line#"${line%%[![:space:]]*}"}"
    # Skip blank lines and comments.
    case "$line" in
      ''|'#'*) continue ;;
    esac
    key="${line%%=*}"
    val="${line#*=}"
    # Trim trailing whitespace from the value.
    val="${val%"${val##*[![:space:]]}"}"
    # Strip optional surrounding quotes.
    case "$val" in
      \"*\") val="${val#\"}"; val="${val%\"}" ;;
      \'*\') val="${val#\'}"; val="${val%\'}" ;;
    esac
    if [ "$key" = "$target_key" ] && [ -n "$val" ]; then
      export "$target_key=$val"
      return 0
    fi
  done < .env
  return 1
}

load_env_key NVIDIA_API_KEY     || true
load_env_key NVIDIA_NIM_API_KEY || true

# Some NAT builds look for NVIDIA_NIM_API_KEY, some for NVIDIA_API_KEY.
# Mirror one to the other so both are always set.
if [ -n "${NVIDIA_API_KEY:-}" ] && [ -z "${NVIDIA_NIM_API_KEY:-}" ]; then
  export NVIDIA_NIM_API_KEY="$NVIDIA_API_KEY"
fi
if [ -n "${NVIDIA_NIM_API_KEY:-}" ] && [ -z "${NVIDIA_API_KEY:-}" ]; then
  export NVIDIA_API_KEY="$NVIDIA_NIM_API_KEY"
fi

if [ -z "${NVIDIA_API_KEY:-}" ]; then
  echo "ERROR: NVIDIA_API_KEY missing in .env" >&2
  echo "       Looked at: $REPO_ROOT/.env" >&2
  echo "       Expected a line like: NVIDIA_API_KEY=nvapi-..." >&2
  echo "" >&2
  echo "   Debug hint - first matching line in .env:" >&2
  grep -E '^NVIDIA_API_KEY=' .env | head -1 >&2 || echo "       (no matching line found)" >&2
  exit 1
fi

mask="${NVIDIA_API_KEY:0:9}...${NVIDIA_API_KEY: -6}"
echo "==> NVIDIA_API_KEY loaded ($mask)"

# ----- 2. uv sync with the nat extra ----------------------------------------
if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv not on PATH. Install with: brew install uv" >&2
  exit 1
fi

echo "==> uv sync --extra nat (installs nvidia-nat[langchain] + base deps)"
uv sync --extra nat

# ----- 3. Sanity check the nat CLI ------------------------------------------
echo "==> nat --version"
.venv/bin/nat --version || {
  echo "WARNING: '.venv/bin/nat --version' failed. Check 'uv sync --extra nat' output above." >&2
}

# ----- 4. Real NAT workflow run on fault1 -----------------------------------
echo ""
echo "==> Real NAT workflow run (fault1)"
.venv/bin/python backend/nat_runner.py \
  --fault fault1 \
  --question "Diagnose the current TEP anomaly and recommend operator review steps." \
  || echo "WARNING: nat_runner returned non-zero (NAT API drift is common across releases)." >&2

# ----- 5. Real-agent evaluation ---------------------------------------------
echo ""
echo "==> Real NAT evaluation (golden cases)"
.venv/bin/python backend/evaluation/evaluate_nat_rca.py --run-agent \
  || echo "WARNING: evaluator returned non-zero. Inspect backend/evaluation/results/ for partial output." >&2

echo ""
echo "==> DONE."
echo "    Latest run JSON(s):"
ls -1t backend/diagnostics/nat_runs/ 2>/dev/null | head -3 || true
echo ""
echo "    Latest evaluation summary:"
cat backend/evaluation/results/summary.json 2>/dev/null | head -20 || true
