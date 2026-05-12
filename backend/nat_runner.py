#!/usr/bin/env python3
"""Run the TEP read-only agentic RCA workflow.

Two modes:
  1. NAT mode (default): if `nvidia-nat` is installed and an NVIDIA_API_KEY
     is set, this script invokes the NAT runtime against
     `backend/nat_workflows/tep_rca_workflow.yml`.
  2. Tools-only mode (`--tools-only`): if NAT is not available, the script
     calls the read-only diagnostic tools in a deterministic order so the
     user still sees concrete tool output. This is also what the
     evaluation script uses when NAT is missing.

Outputs are written to `backend/diagnostics/nat_runs/<timestamp>.json` for
later inspection by the UI Evaluation page.

Usage:
  python backend/nat_runner.py --fault fault1 \
      --question "Diagnose the current TEP anomaly and recommend operator review steps."
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Make repo root importable when run as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Load .env so NVIDIA_API_KEY (and any other secrets) reach the NIM LLM
# without requiring the caller to `export` them in the shell. python-dotenv
# is already a transitive dep of nvidia-nat[langchain]; if absent we skip.
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(_REPO_ROOT / ".env", override=False)
except Exception:
    pass

from backend.agent_tools import (  # noqa: E402
    inspect_anomaly_snapshot,
    rank_contributing_variables,
    search_process_knowledge,
    get_sensor_window,
    find_similar_faults,
    check_advisory_policy,
)

NAT_WORKFLOW_FILE = _REPO_ROOT / "backend" / "nat_workflows" / "tep_rca_workflow.yml"
RUNS_DIR = _REPO_ROOT / "backend" / "diagnostics" / "nat_runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save_run(payload: Dict[str, Any]) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    mode = str(payload.get("mode", "unknown")).replace("/", "_")
    fault_id = str(payload.get("fault_id", "fault_unknown")).replace("/", "_")
    out = RUNS_DIR / f"run_{ts}_{fault_id}_{mode}.json"
    out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return out


def _nat_available() -> bool:
    try:
        import nat  # type: ignore  # noqa: F401
        return True
    except Exception:
        try:
            import aiq  # type: ignore  # noqa: F401
            return True
        except Exception:
            return False


def _print_setup_help() -> None:
    msg = (
        "\n[nat_runner] NeMo Agent Toolkit not detected.\n"
        "\n"
        "  Install NAT and re-run:\n"
        "    pip install -r requirements-nat.txt\n"
        "    export NVIDIA_API_KEY=...   # required for the `_type: nim` LLM\n"
        "\n"
        "  Or run the deterministic tools-only trace (no LLM):\n"
        "    python backend/nat_runner.py --fault fault1 --tools-only\n"
        "\n"
        "  See backend/nat_workflows/README.md for full setup notes.\n"
    )
    print(msg, file=sys.stderr)


def run_tools_only(fault_id: str, question: str) -> Dict[str, Any]:
    """Run a deterministic, scripted sequence of the diagnostic tools.

    This is not real agent reasoning. It exists so the demo, the
    evaluation script, and the UI Evaluation page all have something
    concrete to show even if NAT is not installed. The order mirrors a
    typical RCA workflow and is documented in the architecture doc.
    """
    started = time.time()
    trace: List[Dict[str, Any]] = []

    def _record(tool: str, args: Dict[str, Any], output: Any) -> None:
        trace.append({
            "tool": tool,
            "args": args,
            "output": output,
            "ts": _now_iso(),
        })

    snap = inspect_anomaly_snapshot(fault_id)
    _record("inspect_anomaly_snapshot", {"fault_id": fault_id}, snap)

    ranked = rank_contributing_variables(fault_id, top_k=6)
    _record("rank_contributing_variables", {"fault_id": fault_id, "top_k": 6}, ranked)

    top_vars: List[str] = [v["variable"] for v in ranked.get("top_variables", [])]
    signature_query = " ".join(top_vars[:4]) if top_vars else question
    kb = search_process_knowledge(signature_query, max_results=4)
    _record("search_process_knowledge", {"query": signature_query, "max_results": 4}, kb)

    sensor_windows: List[Dict[str, Any]] = []
    for variable in top_vars[:3]:
        win = get_sensor_window(variable, fault_id, window=20)
        sensor_windows.append(win)
        _record("get_sensor_window", {"sensor_name": variable, "fault_id": fault_id, "window": 20}, win)

    sim = find_similar_faults(signature_query, top_k=3)
    _record("find_similar_faults", {"signature": signature_query, "top_k": 3}, sim)

    # Build a deterministic, advisory-only candidate answer.
    likely_family = ""
    if sim.get("matches"):
        likely_family = sim["matches"][0].get("fault_family", "")
    sources_used = [e.get("source_document", "") for e in kb.get("excerpts", [])]
    citations = ", ".join(sorted(set(s for s in sources_used if s))) or "TEP knowledge base"

    candidate_answer = (
        f"Possible cause: deterministic detector flagged {snap.get('fault_id')} at row "
        f"{snap.get('anomaly_index')} with T2={snap.get('t2_statistic'):.1f} (threshold "
        f"{snap.get('t2_threshold')}). Top contributing variables include "
        f"{', '.join(top_vars[:4]) or 'n/a'}. Pattern is consistent with {likely_family or 'an unspecified disturbance'}. "
        f"Operator should verify by inspecting the variables above against {citations}, and requires SME review."
    )

    policy = check_advisory_policy(candidate_answer)
    _record("check_advisory_policy", {"candidate_answer": candidate_answer}, policy)

    final = {
        "summary": candidate_answer,
        "likely_causes": [m.get("fault_family") for m in sim.get("matches", []) if m.get("fault_family")],
        "evidence_variables": top_vars[:6],
        "sensor_windows": sensor_windows,
        "knowledge_excerpts": kb.get("excerpts", []),
        "policy_check": policy,
        "safety_notice": (
            "Advisory only. The agent cannot change setpoints, open/close valves, "
            "or control the process. Human review required."
        ),
    }

    return {
        "mode": "tools_only",
        "fault_id": fault_id,
        "question": question,
        "started_at": datetime.fromtimestamp(started, tz=timezone.utc).isoformat(),
        "runtime_seconds": round(time.time() - started, 3),
        "tool_trace": trace,
        "final_answer": final,
    }


def run_nat(
    fault_id: str,
    question: str,
    on_step: Optional[Callable[[Dict[str, Any]], None]] = None,
    workflow_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the NAT workflow defined in tep_rca_workflow.yml.

    Parameters
    ----------
    fault_id, question
        Identify the snapshot and free-text agent prompt.
    on_step : callable, optional
        Called once per IntermediateStep with the JSON-serialised payload.
        Used by the SSE endpoint to stream trace events to the frontend.
        Exceptions inside the callback are swallowed so a misbehaving
        consumer cannot break the run. The full trace is always returned
        in the saved JSON regardless of whether `on_step` is set.
    workflow_file : str, optional
        Override the canonical YAML path. The Live Copilot uses this to
        rewrite `llms.nim_llm` for the user-selected model.
    """
    _workflow_path = workflow_file or str(NAT_WORKFLOW_FILE)
    started = time.time()
    # Importing the plugin module triggers tool registration.
    import backend.nat_workflows  # noqa: F401

    error: Optional[str] = None
    final_text: str = ""
    raw_trace: Any = None

    try:
        # NAT 1.6+ ships `load_workflow` as an async context manager
        # (`@asynccontextmanager` over an async generator). To get the
        # actual workflow object we must `async with load_workflow(...) as w:`
        # and then call one of `w.run / w.ainvoke / w.arun`. The exact
        # entry-point name shifts across releases, so we introspect.
        nat_payload = None

        try:
            from nat.runtime.loader import load_workflow  # type: ignore
        except Exception:
            load_workflow = None

        if load_workflow is not None:
            input_text = (
                f"Diagnose TEP {fault_id}. Question: {question}. "
                f"Always end by calling check_advisory_policy on your draft."
            )

            async def _execute_with_context_manager() -> Any:
                """Open the loader, enter a Runner, subscribe to intermediate
                steps, then await the workflow result.

                NAT 1.6's `load_workflow` yields a `SessionManager`. Its `.run`
                is itself an `@asynccontextmanager` that yields a `Runner`.
                Calling `session_manager.run(msg)` without `async with` returns
                the unentered context manager object, which is the bug we are
                fixing here. The correct pattern is:

                    async with load_workflow(yaml) as session_manager:
                        async with session_manager.run(msg) as runner:
                            output = await runner.result()
                """
                async with load_workflow(_workflow_path) as session_manager:
                    async with session_manager.run(input_text) as runner:
                        trace_events: List[Dict[str, Any]] = []

                        def _on_next(step: Any) -> None:
                            try:
                                payload = step.model_dump(mode="json")
                            except Exception:
                                payload = {"repr": repr(step)[:1000]}
                            trace_events.append(payload)
                            if on_step is not None:
                                try:
                                    on_step(payload)
                                except Exception:
                                    pass

                        subscription = None
                        try:
                            subscription = runner.context.intermediate_step_manager.subscribe(
                                _on_next
                            )
                        except Exception:
                            # If the event stream is not available, we still
                            # want the run to complete; we just lose the trace.
                            subscription = None

                        try:
                            output = await runner.result()
                        finally:
                            if subscription is not None:
                                for disposer in ("dispose", "unsubscribe", "close"):
                                    fn = getattr(subscription, disposer, None)
                                    if callable(fn):
                                        try:
                                            fn()
                                        except Exception:
                                            pass
                                        break

                        return {
                            "output": output,
                            "intermediate_steps": trace_events,
                        }

            try:
                nat_payload = asyncio.run(_execute_with_context_manager())
            except RuntimeError as rexc:
                # If we are already inside an event loop (rare from CLI but
                # happens when called from a notebook), fall back to a thread.
                if "already running" in str(rexc):
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as ex:
                        nat_payload = ex.submit(
                            asyncio.run, _execute_with_context_manager()
                        ).result()
                else:
                    raise
        else:
            # Last-ditch: shell out to the `nat` CLI.
            import shutil
            import subprocess

            nat_bin = shutil.which("nat")
            if not nat_bin:
                raise RuntimeError(
                    "Neither nat.runtime.loader.load_workflow nor the `nat` CLI "
                    "was available; cannot execute workflow."
                )
            cmd = [
                nat_bin, "run",
                "--config_file", str(NAT_WORKFLOW_FILE),
                "--input",
                f"Diagnose TEP {fault_id}. Question: {question}.",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            nat_payload = {
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
            }
            final_text = proc.stdout

        # ----- Normalize the workflow output into final_text + raw_trace ----
        if nat_payload is None:
            final_text = "(NAT returned no payload)"
        elif isinstance(nat_payload, str):
            final_text = nat_payload
        elif isinstance(nat_payload, dict):
            final_text = (
                nat_payload.get("output")
                or nat_payload.get("answer")
                or nat_payload.get("text")
                or nat_payload.get("stdout")
                or json.dumps(nat_payload, default=str)[:1500]
            )
            raw_trace = (
                nat_payload.get("intermediate_steps")
                or nat_payload.get("trajectory")
                or nat_payload.get("trace")
                or nat_payload.get("messages")
                or nat_payload
            )
        else:
            # NAT may return a Pydantic model / custom object. Try .dict() /
            # .model_dump() first, then fall back to attribute introspection.
            for method_name in ("model_dump", "dict", "to_dict"):
                m = getattr(nat_payload, method_name, None)
                if callable(m):
                    try:
                        as_dict = m()
                        if isinstance(as_dict, dict):
                            final_text = (
                                as_dict.get("output")
                                or as_dict.get("answer")
                                or as_dict.get("text")
                                or json.dumps(as_dict, default=str)[:1500]
                            )
                            raw_trace = (
                                as_dict.get("intermediate_steps")
                                or as_dict.get("trajectory")
                                or as_dict.get("trace")
                                or as_dict.get("messages")
                                or as_dict
                            )
                            break
                    except Exception:
                        continue
            else:
                final_text = str(nat_payload)
                raw_trace = {"repr": repr(nat_payload)[:2000]}

    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        final_text = "(NAT execution failed; see error in saved run.)"

    # Always run the policy check on the final text so the run record is
    # consistent with the tools-only path.
    policy = check_advisory_policy(final_text)

    return {
        "mode": "nat",
        "fault_id": fault_id,
        "question": question,
        "started_at": datetime.fromtimestamp(started, tz=timezone.utc).isoformat(),
        "runtime_seconds": round(time.time() - started, 3),
        "workflow_file": _workflow_path,
        "tool_trace": raw_trace,
        "final_answer": {
            "text": final_text,
            "policy_check": policy,
            "safety_notice": (
                "Advisory only. The agent cannot change setpoints, open/close "
                "valves, or control the process. Human review required."
            ),
        },
        "error": error,
    }


async def run_nat_streaming(
    fault_id: str,
    question: str,
    on_step: Callable[[Dict[str, Any]], None],
    workflow_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Run NAT in a worker thread, pushing each IntermediateStep through
    `on_step` as it happens.

    `on_step` is invoked from the worker thread. If the consumer needs to
    deliver into an asyncio.Queue on the FastAPI loop, the consumer is
    responsible for using `loop.call_soon_threadsafe(...)`.

    `workflow_file` lets the caller override the canonical YAML path so the
    Live Copilot can rewrite the LLM section per request (model selector).
    """
    return await asyncio.to_thread(
        run_nat, fault_id, question, on_step, workflow_file
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the TEP NAT RCA workflow.")
    parser.add_argument("--fault", default="fault1", help="Fault id, e.g. fault1.")
    parser.add_argument(
        "--question",
        default="Diagnose the current TEP anomaly and recommend operator review steps.",
        help="Free-text question to send to the agent.",
    )
    parser.add_argument(
        "--tools-only",
        action="store_true",
        help="Skip NAT and run a deterministic tool trace only.",
    )
    args = parser.parse_args()

    if args.tools_only:
        payload = run_tools_only(args.fault, args.question)
    else:
        if not _nat_available():
            _print_setup_help()
            return 2
        payload = run_nat(args.fault, args.question)

    out_path = _save_run(payload)
    print(f"[nat_runner] wrote run to {out_path}")
    print(json.dumps({
        "mode": payload.get("mode"),
        "fault_id": payload.get("fault_id"),
        "runtime_seconds": payload.get("runtime_seconds"),
        "is_advisory_safe": (
            payload.get("final_answer", {}).get("policy_check", {}) or {}
        ).get("is_advisory_safe"),
    }, indent=2))
    return 0 if not payload.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
