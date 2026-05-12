#!/usr/bin/env python3
"""Evaluate the TEP NAT agentic RCA workflow.

Two evaluation modes:

1. ``--tools-only`` (default-friendly):
   Run the deterministic tool-trace path implemented in
   ``backend.nat_runner.run_tools_only`` against each golden case and check
   the structural metrics. This works without NAT installed and without
   any external API keys.

2. ``--run-agent``:
   Run the actual NAT workflow against each golden case via
   ``backend.nat_runner.run_nat``. Requires NAT and an API key.

Metrics (recorded per case and rolled up):

  * tool_availability    - did all required tools execute without error?
  * required_tools_hit   - were all `must_use_tools` actually called?
  * evidence_variable_hit_rate - fraction of expected evidence variables
                                 that appeared in the top-K ranked output
                                 or in the final advisory text.
  * forbidden_phrase_count    - count of `must_not_say` phrases that appear
                                in the final advisory text.
  * source_citation_present   - did the run cite at least one source doc?
  * latency_seconds           - wall-clock seconds for the run.
  * trajectory_available      - True if the run produced a tool trace.

A summary is written to ``backend/evaluation/results/summary.json`` and the
per-case detail to ``backend/evaluation/results/cases.jsonl``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.nat_runner import run_tools_only, run_nat, _nat_available  # noqa: E402

GOLDEN_FILE = Path(__file__).resolve().parent / "golden_cases.jsonl"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_golden_cases() -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    with open(GOLDEN_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cases.append(json.loads(line))
    return cases


def _flatten_text(payload: Any) -> str:
    """Join everything 'final_answer'-ish into one searchable string."""
    if not payload:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        bits = [
            payload.get("summary", ""),
            payload.get("text", ""),
        ]
        for w in payload.get("sensor_windows", []) or []:
            bits.append(json.dumps(w, default=str))
        for k in payload.get("knowledge_excerpts", []) or []:
            bits.append(json.dumps(k, default=str))
        return " \n ".join(b for b in bits if b)
    return json.dumps(payload, default=str)


# Known TEP tool function names. NAT 1.6 also emits FUNCTION_START/END for
# wrapper functions like `react_agent` and `<workflow>`; we only want the
# actual diagnostic tools when counting per-case tool calls.
_KNOWN_TOOL_NAMES = {
    "inspect_anomaly_snapshot",
    "rank_contributing_variables",
    "search_process_knowledge",
    "get_sensor_window",
    "find_similar_faults",
    "check_advisory_policy",
}


def _iter_steps_normalized(
    trace: Iterable[Dict[str, Any]] | None,
) -> Iterator[Tuple[Optional[str], Any, Optional[str]]]:
    """Yield `(tool_name, output, event_type)` for both trace shapes.

    Two shapes are supported:

    * Tools-only: ``{"tool": "foo", "output": {...}, ...}``.
      Yields ``(name, output, None)``.
    * NAT 1.6 IntermediateStep: ``{"payload": {"event_type": "FUNCTION_END",
      "name": "foo", "data": {"output": {...}}}}``. Yields
      ``(name, output, event_type)`` so callers can filter to FUNCTION_END.
    """
    if not trace:
        return
    for step in trace:
        if not isinstance(step, dict):
            continue
        if step.get("tool"):
            yield step.get("tool"), step.get("output"), None
            continue
        payload = step.get("payload")
        if isinstance(payload, dict):
            data = payload.get("data") or {}
            yield payload.get("name"), data.get("output"), payload.get("event_type")


def _tools_called(trace: Iterable[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for name, _output, event_type in _iter_steps_normalized(trace):
        if not name:
            continue
        if event_type is None:
            # Tools-only shape: every entry is a real tool call.
            out.append(name)
        elif event_type == "FUNCTION_END" and name in _KNOWN_TOOL_NAMES:
            # NAT shape: count one call per FUNCTION_END of a known tool, and
            # skip the wrapper events (react_agent / <workflow>).
            out.append(name)
    return out


def _evidence_variables_in_run(run: Dict[str, Any]) -> List[str]:
    """Pull the ranked top variables out of the tool trace."""
    out: List[str] = []
    for name, output, event_type in _iter_steps_normalized(run.get("tool_trace") or []):
        if name != "rank_contributing_variables":
            continue
        # tools-only: event_type=None. NAT: only FUNCTION_END carries output.
        if event_type not in (None, "FUNCTION_END"):
            continue
        if not isinstance(output, dict):
            continue
        for v in output.get("top_variables") or []:
            vn = v.get("variable") if isinstance(v, dict) else None
            if vn:
                out.append(vn)
    # Also include variables explicitly listed in final_answer.evidence_variables
    final = run.get("final_answer") or {}
    for v in final.get("evidence_variables", []) or []:
        if v and v not in out:
            out.append(v)
    return out


def _sources_cited_in_run(run: Dict[str, Any]) -> List[str]:
    sources: List[str] = []
    for name, output, event_type in _iter_steps_normalized(run.get("tool_trace") or []):
        if name != "search_process_knowledge":
            continue
        if event_type not in (None, "FUNCTION_END"):
            continue
        if not isinstance(output, dict):
            continue
        for e in output.get("excerpts") or []:
            src = e.get("source_document") if isinstance(e, dict) else None
            if src and src not in sources:
                sources.append(src)
    final = run.get("final_answer") or {}
    for e in final.get("knowledge_excerpts", []) or []:
        src = e.get("source_document") if isinstance(e, dict) else None
        if src and src not in sources:
            sources.append(src)
    return sources


def evaluate_case(case: Dict[str, Any], run_mode: str) -> Dict[str, Any]:
    fault_id = case["fault_file"]
    question = case["question"]
    started = time.time()

    if run_mode == "agent":
        run = run_nat(fault_id, question)
    else:
        run = run_tools_only(fault_id, question)

    runtime = round(time.time() - started, 3)
    text_blob = _flatten_text(run.get("final_answer"))

    tools_called = _tools_called(run.get("tool_trace") or [])
    must_use = set(case.get("must_use_tools", []))
    required_tools_hit = must_use.issubset(set(tools_called))

    # Tool availability: any error key in any step?
    tool_availability = True
    for step in run.get("tool_trace") or []:
        out = (step or {}).get("output") or {}
        if isinstance(out, dict) and out.get("error"):
            tool_availability = False
            break

    expected_vars = case.get("expected_evidence_variables", []) or []
    found_vars = _evidence_variables_in_run(run)
    found_set_lower = {v.lower() for v in found_vars}
    text_lower = text_blob.lower()

    if not expected_vars:
        evidence_hit_rate = 1.0
        evidence_hits: List[str] = []
    else:
        hits = []
        for v in expected_vars:
            if v.lower() in found_set_lower or v.lower() in text_lower:
                hits.append(v)
        evidence_hits = hits
        evidence_hit_rate = round(len(hits) / len(expected_vars), 3)

    forbidden = case.get("must_not_say", []) or []
    forbidden_hits = [p for p in forbidden if p.lower() in text_lower]

    sources = _sources_cited_in_run(run)
    source_citation_present = bool(sources)

    trajectory_available = bool(run.get("tool_trace"))

    return {
        "case_id": case.get("case_id"),
        "fault_file": fault_id,
        "mode": run.get("mode"),
        "metrics": {
            "tool_availability": tool_availability,
            "required_tools_hit": required_tools_hit,
            "tools_called": tools_called,
            "evidence_variable_hit_rate": evidence_hit_rate,
            "evidence_hits": evidence_hits,
            "expected_evidence_variables": expected_vars,
            "forbidden_phrase_count": len(forbidden_hits),
            "forbidden_hits": forbidden_hits,
            "source_citation_present": source_citation_present,
            "sources_cited": sources,
            "latency_seconds": runtime,
            "trajectory_available": trajectory_available,
            "policy_check_passed": (run.get("final_answer") or {})
                .get("policy_check", {})
                .get("is_advisory_safe", None),
        },
        "run_runtime_seconds": run.get("runtime_seconds"),
        "error": run.get("error"),
        "tool_trace_summary": [
            {
                "tool": name,
                "event": event_type,
                "ok": not (isinstance(output, dict) and output.get("error")),
            }
            for name, output, event_type in _iter_steps_normalized(run.get("tool_trace") or [])
            if name
        ],
    }


def summarize(per_case: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(per_case)
    if total == 0:
        return {"total_cases": 0}

    def _avg(key: str) -> float:
        vals = [c["metrics"].get(key, 0) for c in per_case]
        return round(sum(vals) / total, 3)

    def _ratio(predicate) -> float:
        return round(sum(1 for c in per_case if predicate(c)) / total, 3)

    return {
        "total_cases": total,
        "tool_availability_pass_rate": _ratio(lambda c: c["metrics"]["tool_availability"]),
        "required_tools_hit_rate": _ratio(lambda c: c["metrics"]["required_tools_hit"]),
        "avg_evidence_variable_hit_rate": _avg("evidence_variable_hit_rate"),
        "forbidden_phrase_total": sum(c["metrics"]["forbidden_phrase_count"] for c in per_case),
        "source_citation_present_rate": _ratio(lambda c: c["metrics"]["source_citation_present"]),
        "trajectory_available_rate": _ratio(lambda c: c["metrics"]["trajectory_available"]),
        "policy_check_pass_rate": _ratio(
            lambda c: c["metrics"].get("policy_check_passed") is True
        ),
        "avg_latency_seconds": _avg("latency_seconds"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the TEP NAT RCA workflow.")
    parser.add_argument("--tools-only", action="store_true",
                        help="Use the deterministic tools-only trace (no NAT/LLM).")
    parser.add_argument("--run-agent", action="store_true",
                        help="Use the real NAT agent (requires nvidia-nat + API key).")
    parser.add_argument("--limit", type=int, default=0,
                        help="Optional cap on number of golden cases to run.")
    args = parser.parse_args()

    mode = "agent" if args.run_agent and not args.tools_only else "tools"
    if mode == "agent" and not _nat_available():
        print("[evaluate_nat_rca] NAT not installed - falling back to tools-only.")
        mode = "tools"

    cases = load_golden_cases()
    if args.limit:
        cases = cases[: args.limit]

    per_case: List[Dict[str, Any]] = []
    for case in cases:
        result = evaluate_case(case, mode)
        per_case.append(result)
        m = result["metrics"]
        print(
            f"[{result['case_id']}] tools_ok={m['tool_availability']} "
            f"required_hit={m['required_tools_hit']} "
            f"evidence={m['evidence_variable_hit_rate']} "
            f"forbidden={m['forbidden_phrase_count']} "
            f"sources={m['source_citation_present']} "
            f"latency={m['latency_seconds']}s"
        )

    summary = summarize(per_case)
    summary["mode"] = mode

    cases_path = RESULTS_DIR / "cases.jsonl"
    with open(cases_path, "w", encoding="utf-8") as f:
        for r in per_case:
            f.write(json.dumps(r, default=str) + "\n")
    summary_path = RESULTS_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print("\n=== summary ===")
    print(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {cases_path} and {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
