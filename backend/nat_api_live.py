"""Live-mode FastAPI routes for the NAT TEP Copilot.

This router is mounted by `backend.app` and provides the endpoints the new
LiveCopilotPage needs:

  POST  /api/agent/diagnose
  GET   /api/agent/runs/{run_id}/stream      (SSE)
  GET   /api/agent/runs
  GET   /api/agent/runs/{run_id}
  POST  /api/agent/runs/{run_id}/followup
  GET   /api/anomaly/state

The existing `/api/agent/run` and `/api/agent/runs/latest` routes (in
`backend.nat_api`) are not modified.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.agent_tools.live_snapshot import snapshot_live_buffer
from backend.nat_runner import RUNS_DIR, run_nat_streaming, NAT_WORKFLOW_FILE
from backend.agent_models import list_models, make_workflow_yaml, DEFAULT_MODEL_ID

logger = logging.getLogger("nat_api_live")
router = APIRouter()

# Validates ids used as filename components. Anything not matching is rejected
# before being concatenated into a Path — defence against ../../ traversal.
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def _must_be_safe_id(kind: str, value: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID_RE.fullmatch(value):
        raise HTTPException(status_code=400, detail=f"invalid {kind}: {value!r}")
    return value


class _LiveRun(BaseModel):
    """In-process record of a running NAT execution.

    Held in the `_active_runs` registry between the moment `diagnose` returns
    a run_id and the moment the SSE consumer reads the `done` event. The
    canonical copy of the run lives on disk under RUNS_DIR after completion.
    """

    run_id: str
    queue: Any
    task: Any
    started_at: str
    fault_id: str
    question: str

    class Config:
        arbitrary_types_allowed = True


_active_runs: Dict[str, _LiveRun] = {}


class DiagnoseRequest(BaseModel):
    question: str = (
        "Diagnose the current TEP anomaly and recommend operator review steps."
    )
    points: int = 200
    fault_id: Optional[str] = None
    # Model selector: one of the ids returned by GET /api/agent/models.
    # If None, falls back to DEFAULT_MODEL_ID.
    model_id: Optional[str] = None
    # Optional user-supplied API key (BYOK). Sent only over the local Vite
    # proxy → 127.0.0.1:8000, never persisted on disk by the server.
    api_key: Optional[str] = None


def _utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _utc_compact() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%S%f")


def _resolve_app_module():
    """Return the running backend.app module instance.

    When the user runs ``python backend/app.py`` directly, the module is
    loaded under the name ``__main__``. A ``from backend import app`` from
    inside this router would load a *second*, independent copy whose own
    ``live_buffer`` deque is empty — which is the wrong one.

    We prefer ``sys.modules['__main__']`` when it carries the expected
    attributes, and fall back to the package path when the backend was
    started via ``uvicorn backend.app:app`` (which loads as ``backend.app``).
    """
    import sys
    main = sys.modules.get("__main__")
    if main is not None and hasattr(main, "live_buffer"):
        return main
    from backend import app as _a
    return _a


def _make_live_snapshot(points: int) -> str:
    """Pull `points` rows from the running app's `live_buffer` and freeze a CSV.

    Raises 409 if the live buffer is empty (simulator not running, or no
    data ingested yet).
    """
    rows = list(getattr(_resolve_app_module(), "live_buffer", []))[-points:]
    if not rows:
        raise HTTPException(
            status_code=409,
            detail="no live data; start the simulator first",
        )
    return snapshot_live_buffer(rows)


@router.post("/api/agent/diagnose")
async def diagnose(req: DiagnoseRequest) -> Dict[str, Any]:
    """Start a NAT run against a live snapshot (default) or a seeded fault.

    Returns immediately with a `run_id`; the caller then opens
    GET /api/agent/runs/{run_id}/stream to receive IntermediateSteps as they
    arrive.
    """
    fault_id = req.fault_id or _make_live_snapshot(req.points)
    run_id = f"run_{_utc_compact()}_{fault_id}"

    # Materialise the chosen model's NAT workflow YAML. Falls back to the
    # canonical default model when model_id is missing or unknown.
    workflow_yaml = make_workflow_yaml(
        NAT_WORKFLOW_FILE,
        req.model_id or DEFAULT_MODEL_ID,
        user_api_key=req.api_key,
    )

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def _on_step(step: Dict[str, Any]) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, step)

    async def _runner() -> None:
        try:
            payload = await run_nat_streaming(
                fault_id, req.question, _on_step,
                workflow_file=str(workflow_yaml),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("NAT streaming run failed")
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"__error__": f"{type(exc).__name__}: {exc}"},
            )
            # The SSE consumer pops _active_runs on receipt of __error__,
            # but if no consumer is connected the entry would leak. Defer
            # the cleanup to a fallback timer so a never-connected error
            # run is reaped automatically.
            loop.call_later(60.0, lambda: _active_runs.pop(run_id, None))
            return
        payload.setdefault("followups", [])
        payload["snapshot_csv"] = f"{fault_id}.csv"
        payload["run_id"] = run_id
        payload["model_id"] = req.model_id or DEFAULT_MODEL_ID
        out = RUNS_DIR / f"{run_id}.json"
        out.write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )
        # Clean up the per-request workflow YAML temp file.
        try:
            workflow_yaml.unlink(missing_ok=True)
        except Exception:
            pass
        loop.call_soon_threadsafe(queue.put_nowait, {"__done__": payload})
        # Same fallback for a __done__ that no consumer ever reads.
        loop.call_later(60.0, lambda: _active_runs.pop(run_id, None))

    task = asyncio.create_task(_runner())
    _active_runs[run_id] = _LiveRun(
        run_id=run_id,
        queue=queue,
        task=task,
        started_at=_utc_now_iso(),
        fault_id=fault_id,
        question=req.question,
    )
    return {
        "run_id": run_id,
        "fault_id": fault_id,
        "started_at": _utc_now_iso(),
    }


def _sse(event: str, data: Any) -> str:
    body = json.dumps(data, default=str)
    return f"event: {event}\ndata: {body}\n\n"


@router.get("/api/agent/runs/{run_id}/stream")
async def stream_run(run_id: str) -> StreamingResponse:
    """Server-Sent Events stream of IntermediateSteps for a live run.

    If the run is still in `_active_runs`, the stream tails its queue. If
    the run has already finished and been written to disk, the stream
    replays the saved trace once and closes.
    """
    _must_be_safe_id("run_id", run_id)
    run = _active_runs.get(run_id)
    if run is None:
        disk = RUNS_DIR / f"{run_id}.json"
        if disk.exists():
            payload = json.loads(disk.read_text())

            async def _replay():
                for step in payload.get("tool_trace") or []:
                    yield _sse("step", step)
                yield _sse("done", payload)

            resp = StreamingResponse(_replay(), media_type="text/event-stream")
            resp.headers["Cache-Control"] = "no-cache"
            resp.headers["X-Accel-Buffering"] = "no"
            resp.headers["Access-Control-Allow-Origin"] = "*"
            return resp
        raise HTTPException(status_code=404, detail=f"unknown run_id {run_id}")

    queue = run.queue

    async def _event_gen():
        try:
            while True:
                item = await queue.get()
                if isinstance(item, dict) and "__error__" in item:
                    yield _sse("error", {"message": item["__error__"]})
                    yield _sse("done", {})
                    return
                if isinstance(item, dict) and "__done__" in item:
                    yield _sse("done", item["__done__"])
                    return
                yield _sse("step", item)
        finally:
            # Reap the registry entry regardless of how we exit (normal,
            # exception, or client disconnect via GeneratorExit). The
            # background `_runner` task already wrote the canonical run
            # JSON to disk before pushing __done__; if it is still running
            # we leave it alone (the run is short and will reap itself via
            # the 60s call_later fallback in `_runner`).
            _active_runs.pop(run_id, None)

    resp = StreamingResponse(_event_gen(), media_type="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


# -----------------------------------------------------------------------------
# Past-run browsing (T6)
# -----------------------------------------------------------------------------

@router.get("/api/agent/runs")
def list_runs(limit: int = 50) -> Dict[str, Any]:
    """List the most recent saved NAT runs, newest first."""
    files = sorted(
        RUNS_DIR.glob("run_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]
    items: List[Dict[str, Any]] = []
    for f in files:
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        final = d.get("final_answer") or {}
        items.append(
            {
                "run_id": d.get("run_id") or f.stem,
                "fault_id": d.get("fault_id"),
                "started_at": d.get("started_at"),
                "runtime_seconds": d.get("runtime_seconds"),
                "policy_safe": (final.get("policy_check") or {}).get(
                    "is_advisory_safe"
                ),
                "summary": (final.get("text") or "")[:180],
                "followup_count": len(d.get("followups") or []),
                "error": d.get("error"),
            }
        )
    return {"runs": items}


@router.get("/api/agent/runs/{run_id}")
def get_run(run_id: str) -> Dict[str, Any]:
    _must_be_safe_id("run_id", run_id)
    f = RUNS_DIR / f"{run_id}.json"
    if not f.exists():
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    return json.loads(f.read_text())


# -----------------------------------------------------------------------------
# Follow-up chat (T7) — single-shot LLM, no ReAct loop
# -----------------------------------------------------------------------------

class FollowupRequest(BaseModel):
    question: str


_followup_client = None  # OpenAI client singleton, lazily constructed


def _get_followup_client():
    """Return a cached OpenAI client pointed at the NIM endpoint.

    Constructed lazily on first use so module import does not require
    `NVIDIA_API_KEY` to be set.
    """
    global _followup_client
    if _followup_client is not None:
        return _followup_client
    from openai import OpenAI  # type: ignore

    base = os.environ.get(
        "NVIDIA_NIM_BASE", "https://integrate.api.nvidia.com/v1"
    )
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="NVIDIA_API_KEY not set; follow-up cannot reach the LLM",
        )
    _followup_client = OpenAI(base_url=base, api_key=api_key)
    return _followup_client


def _summarise_trace(run: Dict[str, Any], max_steps: int = 8) -> str:
    """Compact trace summary used as the followup prompt context."""
    lines: List[str] = []
    for step in (run.get("tool_trace") or [])[:max_steps]:
        p = step.get("payload") or {}
        et = p.get("event_type")
        nm = p.get("name") or ""
        if et == "FUNCTION_END":
            data = p.get("data") or {}
            out = data.get("output")
            preview = json.dumps(out, default=str)[:300] if out else ""
            lines.append(f"- {nm} -> {preview}")
    final = run.get("final_answer") or {}
    if final.get("text"):
        lines.append(f"agent advisory: {final['text'][:500]}")
    return "\n".join(lines) or "(no trace available)"


@router.post("/api/agent/runs/{run_id}/followup")
def followup(run_id: str, req: FollowupRequest) -> Dict[str, Any]:
    _must_be_safe_id("run_id", run_id)
    f = RUNS_DIR / f"{run_id}.json"
    if not f.exists():
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    run = json.loads(f.read_text())

    client = _get_followup_client()

    sys_prompt = (
        "You are an industrial process diagnosis assistant. Answer ONLY based "
        "on the snapshot and the agent's prior trace. Stay advisory-only: do "
        "not propose changing setpoints, opening/closing valves, or starting/"
        "stopping equipment. Cite source documents by name when relevant."
    )
    history = "\n".join(
        f"Q: {fu['q']}\nA: {fu['a']}"
        for fu in (run.get("followups") or [])
    )
    user_prompt = (
        f"Fault id: {run.get('fault_id')}\n"
        f"Prior agent trace summary:\n{_summarise_trace(run)}\n\n"
        f"Followups so far:\n{history or '(none)'}\n\n"
        f"New question: {req.question}"
    )

    completion = client.chat.completions.create(
        model="meta/llama-3.3-70b-instruct",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=512,
    )
    answer = completion.choices[0].message.content or ""

    entry = {"q": req.question, "a": answer, "ts": _utc_now_iso()}
    run.setdefault("followups", []).append(entry)
    f.write_text(json.dumps(run, indent=2, default=str), encoding="utf-8")
    return entry


# -----------------------------------------------------------------------------
# Anomaly state (T8) — read-only view of the existing PCA detector
# -----------------------------------------------------------------------------

@router.get("/api/agent/models")
def list_available_models() -> Dict[str, Any]:
    """Manifest of LLM choices for the model-selector dropdown.

    Includes whether each provider's API key is present in the server env;
    UI uses this to show a "bring your own key" input for missing ones.
    """
    return {"models": list_models(), "default": DEFAULT_MODEL_ID}


@router.get("/api/anomaly/state")
def anomaly_state() -> Dict[str, Any]:
    """Read-only view of the PCA detector + a tail of the T² series.

    The `t2_series` array lets the frontend draw a live T² spike chart
    (the dramatic "spike" that should make the Diagnose Now button glow).
    """
    mod = _resolve_app_module()
    last = getattr(mod, "_last_analysis_result", None)
    consec = int(getattr(mod, "_consecutive_anomalies", 0) or 0)
    threshold = int(getattr(mod, "consecutive_anomalies_required", 1) or 1)
    buf = getattr(mod, "live_buffer", None)
    buf_len = len(buf) if buf is not None else 0

    # Pull the recent T² history out of live_buffer.
    t2_series: List[Dict[str, Any]] = []
    t2_threshold = None
    recent_anomalies = 0
    if buf:
        for row in list(buf)[-50:]:
            try:
                a = bool(row.get("anomaly", False))
                t2_series.append(
                    {
                        "t": int(row.get("time", 0)),
                        "t2_stat": float(row.get("t2_stat", 0.0)),
                        "anomaly": a,
                    }
                )
                if t2_threshold is None and "threshold" in row:
                    t2_threshold = float(row["threshold"])
            except Exception:
                continue
        # Count anomalies in the last 5 samples — used to arm the button
        # even when the spikes aren't strictly consecutive (50× sim is noisy
        # and PCA T² often jitters around the threshold).
        for row in list(buf)[-5:]:
            if bool(row.get("anomaly", False)):
                recent_anomalies += 1

    # Two ways to "arm" the Diagnose button: strict consecutive run (the
    # original gating) OR ≥1 anomaly in the last 5 samples (relaxed for
    # noisy live data so a transient spike is enough to enable diagnosis).
    armed = (
        (consec >= threshold and threshold > 0)
        or recent_anomalies >= 1
    )

    return {
        "armed": armed,
        "consecutive_anomalies": consec,
        "threshold": threshold,
        "recent_anomalies_5": recent_anomalies,
        "buffer_len": buf_len,
        "t2_series": t2_series,
        "t2_threshold": t2_threshold,
        "last_analysis_excerpt": (
            json.dumps(last, default=str)[:240] if last else None
        ),
        "ts": _utc_now_iso(),
    }
