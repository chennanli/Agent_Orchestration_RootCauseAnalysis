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
from backend.agent_models import (
    list_models,
    make_workflow_yaml,
    get_model,
    DEFAULT_MODEL_ID,
)

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
    # Optional overrides. If omitted, the model selection from the original
    # run JSON (`run["model_id"]`) is used. The api_key is a BYOK fallback
    # for users running without a server-side env var (e.g. Gemini key pasted
    # in the UI). It is NOT persisted into the run JSON.
    model_id: Optional[str] = None
    api_key: Optional[str] = None


# Cache of (model_id, masked_key) → OpenAI client. Keyed on a hash of the
# resolved API key so a per-request BYOK key still gets its own client.
# Cleared automatically if the process restarts.
_followup_clients: Dict[str, Any] = {}


def _resolve_followup_provider(
    model_id: str, user_api_key: Optional[str]
) -> Dict[str, Any]:
    """Resolve the OpenAI-compatible {base_url, model_name, api_key} for a
    follow-up call.

    Mirrors what `make_workflow_yaml()` does for the agent run, so a
    follow-up against a Gemini-routed run goes to Gemini (not NIM) and a
    follow-up against a NIM run respects NVIDIA_API_KEY.
    """
    model = get_model(model_id)
    block = model["yaml"]
    name = block["model_name"]
    if block.get("_type") == "openai":
        base = block.get("base_url") or "https://api.openai.com/v1"
    else:
        # NIM: NAT's nim plugin uses the OpenAI-compatible NIM proxy.
        base = os.environ.get(
            "NVIDIA_NIM_BASE", "https://integrate.api.nvidia.com/v1"
        )
    api_key = user_api_key or os.environ.get(model["api_key_env"])
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{model['api_key_env']} not set; follow-up against "
                f"{model['provider']} cannot reach the LLM. Either set the "
                f"env var on the server or paste an API key in the UI."
            ),
        )
    return {"base": base, "model_name": name, "api_key": api_key}


def _get_followup_client(model_id: str, user_api_key: Optional[str]):
    """Return a per-(model, key) cached OpenAI client.

    The cache key includes a fingerprint of the API key so a UI-pasted BYOK
    key gets its own client (and revocation by the user invalidates the
    cached entry on next process restart).
    """
    provider = _resolve_followup_provider(model_id, user_api_key)
    cache_key = f"{model_id}::{hash(provider['api_key'])}"
    cached = _followup_clients.get(cache_key)
    if cached is not None:
        return cached, provider["model_name"]
    from openai import OpenAI  # type: ignore

    client = OpenAI(base_url=provider["base"], api_key=provider["api_key"])
    _followup_clients[cache_key] = client
    return client, provider["model_name"]


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

    # Resolve the model & key for THIS follow-up. Priority:
    #   1. Explicit override in the request body (req.model_id / req.api_key)
    #   2. The model_id saved into the run JSON at diagnose() time
    #   3. The library default
    # This means a follow-up against a Gemini-routed run hits Gemini, not
    # Llama; and a BYOK key pasted in the UI works without env vars.
    chosen_model_id = req.model_id or run.get("model_id") or DEFAULT_MODEL_ID
    client, model_name = _get_followup_client(chosen_model_id, req.api_key)

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

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=512,
        )
    except Exception as exc:  # noqa: BLE001
        # Surface a 502 so the UI shows a clean error instead of a 500
        # stack-trace page; the message includes provider context.
        raise HTTPException(
            status_code=502,
            detail=f"followup LLM call failed ({chosen_model_id}): {exc}",
        ) from exc
    answer = completion.choices[0].message.content or ""

    entry = {
        "q": req.question,
        "a": answer,
        "ts": _utc_now_iso(),
        "model_id": chosen_model_id,
    }
    run.setdefault("followups", []).append(entry)
    f.write_text(json.dumps(run, indent=2, default=str), encoding="utf-8")
    return entry


# -----------------------------------------------------------------------------
# Bake-off (T9) — naive single-shot LLM call on the same snapshot
# -----------------------------------------------------------------------------
#
# Industry-standard way to demonstrate why agent orchestration matters: run
# the SAME question against the SAME LLM on the SAME snapshot, with NO tools
# and NO ReAct loop, and show both answers side-by-side. The bare LLM
# typically returns a vague "may be a cooling-related deviation"; the NAT
# agent returns "XMV_6 (Purge valve) saturated at 87%, see Downs & Vogel
# §5.4". The gap is the value of orchestration.


class BakeoffRequest(BaseModel):
    """Request body for the bake-off endpoint.

    Optional model/api_key overrides so the side-by-side can be run against
    a different model than the original run — useful when the user wants
    to test "would a stronger model not need tools?" hypothesis.
    """

    model_id: Optional[str] = None
    api_key: Optional[str] = None


def _format_snapshot_for_naive(fault_id: str, points: int = 50) -> str:
    """Render a compact text view of a saved snapshot CSV for the naive LLM.

    Includes the latest `points` rows and the column names. We do NOT
    include the anomaly score or the tool-curated top-6 features — those
    are tool outputs and would defeat the bake-off.

    Uses the existing `_resolve_csv_path` from anomaly_tools so this works
    identically for seeded faults (frontend/public/faultN.csv) and live
    snapshots (backend/diagnostics/snapshots/live_*.csv).
    """
    from backend.agent_tools.anomaly_tools import _resolve_csv_path

    try:
        csv_path = _resolve_csv_path(fault_id)
    except Exception as exc:  # noqa: BLE001
        return f"(could not resolve snapshot for {fault_id!r}: {exc})"
    if not csv_path.exists():
        return f"(snapshot {fault_id}.csv not on disk at {csv_path})"
    try:
        import pandas as pd

        df = pd.read_csv(csv_path)
    except Exception as exc:  # noqa: BLE001
        return f"(could not read snapshot: {exc})"
    # Strip the tool-output columns (t2_stat, t2_*, anomaly) — the naive
    # LLM is supposed to reason about raw sensors only. Leaving these in
    # would be giving it the PCA detector's answer for free.
    drop_cols = [c for c in df.columns if c.startswith("t2_") or c == "anomaly"]
    df = df.drop(columns=drop_cols, errors="ignore")
    tail = df.tail(points)
    head_cols = ", ".join(df.columns.tolist())
    body = tail.to_csv(index=False)
    if len(body) > 6000:
        body = body[:6000] + "\n... (truncated)"
    return f"columns:\n{head_cols}\n\nlast {len(tail)} rows:\n{body}"


@router.post("/api/agent/runs/{run_id}/bakeoff")
def bakeoff(run_id: str, req: BakeoffRequest = BakeoffRequest()) -> Dict[str, Any]:
    """Run the naive single-shot LLM on the same snapshot for comparison.

    Returns the bare-model response plus a few orchestration metrics that
    the UI can render alongside the agent's answer:
      - tool_count_agent: how many tools the agent called
      - sources_agent: cited source documents
      - specificity scores (count of XMV_X / XMEAS_Y tag mentions)
    """
    import re as _re
    import time as _time

    _must_be_safe_id("run_id", run_id)
    f = RUNS_DIR / f"{run_id}.json"
    if not f.exists():
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    run = json.loads(f.read_text())

    chosen_model_id = req.model_id or run.get("model_id") or DEFAULT_MODEL_ID
    client, model_name = _get_followup_client(chosen_model_id, req.api_key)

    fault_id = run.get("fault_id") or ""
    question = run.get("question") or (
        "Diagnose the current TEP anomaly and recommend operator review steps."
    )
    snapshot_text = _format_snapshot_for_naive(fault_id)

    sys_prompt = (
        "You are an industrial process diagnosis assistant. You are given a "
        "raw window of TEP sensor data. Answer the operator's question using "
        "ONLY this snapshot. You do not have access to any tools, knowledge "
        "base, or prior diagnoses — reason from the numbers alone. Stay "
        "advisory-only: do not propose changing setpoints or starting/stopping "
        "equipment."
    )
    user_prompt = (
        f"Fault id: {fault_id}\n\n"
        f"Snapshot:\n{snapshot_text}\n\n"
        f"Question: {question}"
    )

    started = _time.time()
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=512,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"bakeoff LLM call failed ({chosen_model_id}): {exc}",
        ) from exc
    runtime = _time.time() - started
    naive_text = completion.choices[0].message.content or ""

    # Specificity heuristic: how many concrete XMV_X / XMEAS_Y tags did
    # each answer reference? Tools force the agent to name specific tags
    # because rank_contributing_variables returns them by name. A naive
    # LLM often hedges with "the cooling subsystem" — fewer tag mentions.
    tag_re = _re.compile(r"\bXM(EAS|V)[ _\-]?\d+\b", _re.IGNORECASE)
    agent_text = (run.get("final_answer") or {}).get("text", "") or ""
    naive_tags = set(m.group(0).upper().replace(" ", "_").replace("-", "_")
                     for m in tag_re.finditer(naive_text))
    agent_tags = set(m.group(0).upper().replace(" ", "_").replace("-", "_")
                     for m in tag_re.finditer(agent_text))

    # Agent metrics derived from the saved tool_trace.
    trace = run.get("tool_trace") or []
    tool_calls = [
        (s.get("payload") or {}).get("name")
        for s in trace
        if (s.get("payload") or {}).get("event_type") == "FUNCTION_END"
    ]
    sources: List[str] = []
    for step in trace:
        p = step.get("payload") or {}
        if p.get("event_type") != "FUNCTION_END":
            continue
        out = (p.get("data") or {}).get("output")
        if not isinstance(out, dict):
            continue
        items = out.get("excerpts") or out.get("matches") or []
        if not isinstance(items, list):
            continue
        for it in items:
            src = (it or {}).get("source_document")
            if isinstance(src, str) and src and src not in sources:
                sources.append(src)

    return {
        "naive": {
            "text": naive_text,
            "model_id": chosen_model_id,
            "runtime_seconds": round(runtime, 2),
            "tag_count": len(naive_tags),
            "tags": sorted(naive_tags),
        },
        "agent": {
            "text": agent_text,
            "model_id": run.get("model_id"),
            "runtime_seconds": run.get("runtime_seconds"),
            "tool_count": len(tool_calls),
            "tool_calls": tool_calls,
            "sources_cited": sources,
            "tag_count": len(agent_tags),
            "tags": sorted(agent_tags),
        },
    }


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
