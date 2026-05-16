"""FastAPI routes for the AI Discovery Workbench (Phase 9 — UI surfacing).

This is the bridge between the backend LangGraph orchestrator and the React
`/discovery` page. Mirrors the shape of `backend/nat_api_live.py`:

  POST  /api/discovery/diagnose      → kick off a run, return run_id
  GET   /api/discovery/runs/{id}     → fetch the saved final-state JSON
  GET   /api/discovery/runs/{id}/stream  → SSE stream of per-node updates
  GET   /api/discovery/runs          → list recent saved runs

The streaming endpoint emits one of these event types per line:

  event: node            data: {"node": "<name>", "state": {...accumulated...}}
  event: done            data: {"final": {...full final state...}}
  event: error           data: {"message": "..."}

State is snapshotted after each LangGraph node so the UI can render the
graph's progress live (highlight active node → fill evidence panels →
populate hypothesis cards → show evaluator verdict → final advisory).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger("tep.discovery")

_ROOT = Path(__file__).resolve().parent.parent
_RUNS_DIR = _ROOT / "backend" / "diagnostics" / "multi_agent_runs"
_RUNS_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()

# ---------------------------------------------------------------------------
# Active-run registry (queues per run_id) — patterned after nat_api_live
# ---------------------------------------------------------------------------
class _ActiveRun:
    """Holds an asyncio queue the SSE generator drains."""

    def __init__(self) -> None:
        self.queue: asyncio.Queue = asyncio.Queue()
        self.started_at: float = time.time()


_active_runs: Dict[str, _ActiveRun] = {}


def _safe_id(name: str, value: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_\-]{1,80}", value):
        raise HTTPException(status_code=400, detail=f"bad {name}")


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _apply_sse_cors(resp: StreamingResponse, request: Request) -> None:
    """Mirror the CORS allowlist from backend.app for SSE responses."""
    try:
        from backend.app import origins as _allowed
        req_origin = request.headers.get("origin") if request is not None else None
    except Exception:
        return
    if req_origin and req_origin in _allowed:
        resp.headers["Access-Control-Allow-Origin"] = req_origin
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Vary"] = "Origin"


# ---------------------------------------------------------------------------
# Request / response shapes
# ---------------------------------------------------------------------------
class DiagnoseRequest(BaseModel):
    fault_id: str = "fault1"
    question: Optional[str] = None
    thread_id: Optional[str] = None


class DiagnoseStarted(BaseModel):
    run_id: str
    fault_id: str
    started_at: str
    stream_url: str


# ---------------------------------------------------------------------------
# Runner: invokes run_langgraph with an on_node callback that pushes to the
# active-run queue. Sync graph + asyncio glue via run_in_executor.
# ---------------------------------------------------------------------------
def _run_blocking(run_id: str, fault_id: str, question: str) -> None:
    """Blocking entry point; called via asyncio.to_thread / executor."""
    from backend.langgraph_rca import run_langgraph

    active = _active_runs.get(run_id)
    if active is None:
        return
    main_loop = active.loop  # set by caller before scheduling

    def _on_node(node_name: str, state: Dict[str, Any]) -> None:
        # Trim the snapshot to UI-relevant keys (don't ship the whole
        # checkpointer state per event).
        snapshot = {
            "anomaly_snapshot": state.get("anomaly_snapshot"),
            "ranked_variables": (state.get("ranked_variables") or [])[:5],
            "evidence_by_layer": state.get("evidence_by_layer") or {},
            "hypotheses": state.get("hypotheses") or [],
            "draft_advisory": state.get("draft_advisory", ""),
            "evaluation": state.get("evaluation") or {},
            "revision_count": int(state.get("revision_count") or 0),
            "hitl_required": bool(state.get("hitl_required") or False),
            "final_advisory": state.get("final_advisory", ""),
            "audit_trail": state.get("audit_trail") or [],
        }
        payload = {"node": node_name, "state": snapshot}
        # Hop from the worker thread back to the event loop so asyncio.Queue
        # gets it consistently.
        try:
            asyncio.run_coroutine_threadsafe(active.queue.put(payload), main_loop)
        except Exception as exc:
            logger.warning("on_node enqueue failed: %s", exc)

    try:
        final = run_langgraph(
            fault_id=fault_id,
            question=question,
            on_node=_on_node,
        )
        asyncio.run_coroutine_threadsafe(
            active.queue.put({"__done__": final}), main_loop,
        )
    except Exception as exc:
        asyncio.run_coroutine_threadsafe(
            active.queue.put({"__error__": f"{type(exc).__name__}: {exc}"}),
            main_loop,
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/api/discovery/diagnose", response_model=DiagnoseStarted)
async def discovery_diagnose(req: DiagnoseRequest) -> DiagnoseStarted:
    """Kick off a LangGraph multi-evidence run; return the run_id immediately.
    Stream progress via GET /api/discovery/runs/{run_id}/stream.
    """
    _safe_id("fault_id", req.fault_id)
    run_id = f"disc_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
    active = _ActiveRun()
    active.loop = asyncio.get_event_loop()
    _active_runs[run_id] = active

    question = req.question or (
        "Diagnose the current TEP process anomaly. "
        "Identify the most likely root cause and the contributing variables."
    )

    # Launch the synchronous LangGraph run in a worker thread so we don't
    # block the FastAPI event loop. The on_node callback inside _run_blocking
    # uses run_coroutine_threadsafe to push to the asyncio.Queue.
    asyncio.create_task(asyncio.to_thread(_run_blocking, run_id, req.fault_id, question))

    return DiagnoseStarted(
        run_id=run_id,
        fault_id=req.fault_id,
        started_at=datetime.now(timezone.utc).isoformat() + "Z",
        stream_url=f"/api/discovery/runs/{run_id}/stream",
    )


@router.get("/api/discovery/runs/{run_id}/stream")
async def stream_discovery(run_id: str, request: Request) -> StreamingResponse:
    """SSE stream of per-node state updates.

    Events: `node` (one per LangGraph node completion), `done` (final state),
    `error` (run failed).
    """
    _safe_id("run_id", run_id)
    active = _active_runs.get(run_id)

    if active is None:
        # Maybe the run already finished and was reaped — try the saved JSON
        # files in _RUNS_DIR (best-effort replay so reloads work).
        candidate = _find_saved_run(run_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail=f"unknown run_id {run_id}")
        # Replay the saved final state as a single `done` event.
        async def _replay():
            payload = json.loads(candidate.read_text())
            yield _sse("done", {"final": payload})
        resp = StreamingResponse(_replay(), media_type="text/event-stream")
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["X-Accel-Buffering"] = "no"
        _apply_sse_cors(resp, request)
        return resp

    async def _event_gen():
        try:
            while True:
                item = await active.queue.get()
                if isinstance(item, dict) and "__error__" in item:
                    yield _sse("error", {"message": item["__error__"]})
                    yield _sse("done", {"final": None})
                    return
                if isinstance(item, dict) and "__done__" in item:
                    yield _sse("done", {"final": item["__done__"]})
                    return
                yield _sse("node", item)
        finally:
            _active_runs.pop(run_id, None)

    resp = StreamingResponse(_event_gen(), media_type="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    _apply_sse_cors(resp, request)
    return resp


@router.get("/api/discovery/runs/{run_id}")
def get_discovery_run(run_id: str) -> Dict[str, Any]:
    """Fetch the saved final-state JSON for a completed run."""
    _safe_id("run_id", run_id)
    candidate = _find_saved_run(run_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"unknown run_id {run_id}")
    try:
        return json.loads(candidate.read_text())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"could not read run: {exc}")


@router.get("/api/discovery/runs")
def list_discovery_runs(limit: int = 20) -> Dict[str, Any]:
    """List the most recent saved LangGraph runs, newest first."""
    files = sorted(
        _RUNS_DIR.glob("lg_run_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[: max(1, min(limit, 200))]
    items = []
    for p in files:
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        items.append({
            "file": p.name,
            "fault_id": d.get("fault_id"),
            "runtime_seconds": d.get("_runtime_seconds"),
            "final_advisory_snippet": (d.get("final_advisory") or "")[:160],
            "hitl_required": d.get("hitl_required"),
            "evaluation_grounded_ratio": (d.get("evaluation") or {}).get("grounded_ratio"),
        })
    return {"runs": items}


def _find_saved_run(run_id: str) -> Optional[Path]:
    """Saved runs use a timestamp-based filename, not the run_id. Best-effort
    match: return the most recent file with that fault id if run_id starts
    with `disc_<unix_ms>_*`; otherwise return None."""
    # Simple heuristic: if the run_id maps to a recently-finished file, find
    # any lg_run_*.json with mtime within 5s of the run_id's timestamp.
    if not run_id.startswith("disc_"):
        return None
    try:
        run_ts_ms = int(run_id.split("_")[1])
    except Exception:
        return None
    target = run_ts_ms / 1000.0
    best: Optional[Path] = None
    best_dt: float = 1e9
    for p in _RUNS_DIR.glob("lg_run_*.json"):
        dt = abs(p.stat().st_mtime - target)
        if dt < 120 and dt < best_dt:
            best, best_dt = p, dt
    return best
