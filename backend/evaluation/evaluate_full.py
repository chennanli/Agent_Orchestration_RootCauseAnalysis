"""4-way comparative harness:

  1. tools_only             — deterministic tool pipeline, no LLM
                              (mimics nat_runner.py --tools-only)
  2. nat_react              — NAT (NeMo Agent Toolkit) ReAct agent
  3. langchain_react        — pure-LangChain prebuilt ReAct agent over the
                              same 4-layer evidence router (no NAT)
  4. langgraph_multi        — our 5-node LangGraph orchestrator

For each (mode × case) we record:
  runtime_seconds, evidence_layers_used, policy_pass, grounded_ratio
  (held-out 8b judge), revision_count, hitl_required, error, completed.

Cases can come from:
  - hand-curated golden set (3 cases, same as discovery_summary)
  - synthetic_cases.json (run synth_cases.py first)
  - both (default)

Outputs:
  backend/evaluation/results/full_eval_summary.json
  backend/evaluation/results/full_eval_report.md

Usage:
  python backend/evaluation/evaluate_full.py --limit 4
  python backend/evaluation/evaluate_full.py --modes langgraph_multi langchain_react --limit 2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.evaluation.judge import grade_grounding  # noqa: E402


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------
_GOLDEN_CASES: List[Dict[str, Any]] = [
    {"fault_id": "fault1", "question": "Diagnose the current TEP process anomaly.",
     "source": "golden"},
    {"fault_id": "fault6", "question": "Diagnose fault6. Is this a feed-loss scenario?",
     "source": "golden"},
    {"fault_id": "fault4", "question": "Diagnose fault4. Which variable is driving it?",
     "source": "golden"},
]


def _load_synthetic(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    return [{**c, "source": "synthetic"} for c in raw]


def _collect_evidence_snippets_from_lg(final: Dict[str, Any]) -> List[str]:
    """Pull text snippets out of LangGraph evidence_by_layer for the judge."""
    out: List[str] = []
    for L, hits in (final.get("evidence_by_layer") or {}).items():
        for h in (hits or [])[:3]:
            t = h.get("text") or str(h)
            if t:
                out.append(f"[{L}] {t[:300]}")
    return out


# ---------------------------------------------------------------------------
# Mode 1 — tools_only
# ---------------------------------------------------------------------------
def _run_tools_only(case: Dict[str, Any]) -> Dict[str, Any]:
    from backend.agent_tools.anomaly_tools import (
        inspect_anomaly_snapshot, rank_contributing_variables,
    )
    from backend.agent_tools.history_tools import find_similar_faults
    from backend.agent_tools.policy_tools import check_advisory_policy

    fid = case["fault_id"]
    t0 = time.time()
    try:
        snap = inspect_anomaly_snapshot(fid)
        ranked = rank_contributing_variables(fid, top_k=5)
        # The tool's actual key is `top_variables`, not `top_contributors`.
        # The earlier draft used the wrong key here, which made `top_vars`
        # silently empty in tools_only runs (advisory text rendered with a
        # bare comma, and the similar-faults query was an empty string).
        top_vars = [v["variable"] for v in ranked.get("top_variables", [])[:5]]
        sim = find_similar_faults(" ".join(top_vars), top_k=3)
        advisory = (
            f"Anomaly detected in {fid}. Top contributing variables: "
            f"{', '.join(top_vars)}. SME review recommended."
        )
        pol = check_advisory_policy(advisory)
        # Grounding "judge" for tools_only — trivially 1.0 because text is
        # 100% mechanically derived from tool output.
        grounded = 1.0
        return {
            "mode": "tools_only", "fault_id": fid, "case_source": case["source"],
            "runtime_seconds": round(time.time() - t0, 2),
            "evidence_layers_used": ["pattern_memory_proxy(tools)"],
            "policy_pass": bool(pol.get("is_advisory_safe", True)),
            "grounded_ratio": grounded, "judge_model": "deterministic_self",
            "supported_claims": 1, "unsupported_claims": 0,
            "revision_count": 0, "hitl_required": False,
            "completed": True, "error": None,
            "final_text_snippet": advisory[:300],
        }
    except Exception as exc:
        return {
            "mode": "tools_only", "fault_id": fid, "case_source": case["source"],
            "runtime_seconds": round(time.time() - t0, 2),
            "evidence_layers_used": [], "policy_pass": None,
            "grounded_ratio": 0.0, "judge_model": "none",
            "supported_claims": 0, "unsupported_claims": 0,
            "revision_count": 0, "hitl_required": False,
            "completed": False, "error": f"{type(exc).__name__}: {exc}",
            "final_text_snippet": "",
        }


# ---------------------------------------------------------------------------
# Mode 2 — nat_react
# ---------------------------------------------------------------------------
def _run_nat_react(case: Dict[str, Any]) -> Dict[str, Any]:
    fid, q = case["fault_id"], case["question"]
    t0 = time.time()
    try:
        from backend.nat_runner import run_nat
        result = run_nat(fault_id=fid, question=q)
    except Exception as exc:
        return {
            "mode": "nat_react", "fault_id": fid, "case_source": case["source"],
            "runtime_seconds": round(time.time() - t0, 2),
            "evidence_layers_used": [], "policy_pass": None,
            "grounded_ratio": 0.0, "judge_model": "none",
            "supported_claims": 0, "unsupported_claims": 0,
            "revision_count": 0, "hitl_required": False,
            "completed": False, "error": f"Harness: {type(exc).__name__}: {exc}",
            "final_text_snippet": "",
        }
    fa = result.get("final_answer") or {}
    final_text = str(fa.get("text") or "") if isinstance(fa, dict) else str(fa)
    nat_error = result.get("error")
    nat_pol = fa.get("policy_check") or {} if isinstance(fa, dict) else {}
    completed = bool(final_text) and not nat_error \
                and "execution failed" not in final_text.lower()

    # Pass NAT's tool_trace outputs to the grounding judge so it gets the
    # same kind of ground-truth retrieval text as langgraph_multi /
    # langchain_react. Earlier drafts passed [] here, which made the
    # comparison unfair to NAT.
    nat_evidence_snippets: List[str] = []
    for step in (result.get("tool_trace") or [])[:8]:
        tool_name = step.get("tool", "")
        out = step.get("output", "")
        if isinstance(out, (dict, list)):
            out = json.dumps(out)[:400]
        elif isinstance(out, str):
            out = out[:400]
        else:
            out = str(out)[:400]
        if tool_name and out:
            nat_evidence_snippets.append(f"[{tool_name}] {out}")

    # Held-out judge
    grade = grade_grounding(final_text, nat_evidence_snippets, fault_id=fid) \
            if completed else \
            {"grounded_ratio": 0.0, "supported_claims": 0,
             "unsupported_claims": 0, "judge_model": "none",
             "note": "skipped: nat errored"}

    return {
        "mode": "nat_react", "fault_id": fid, "case_source": case["source"],
        "runtime_seconds": round(time.time() - t0, 2),
        "evidence_layers_used": ["wiki", "field_feedback"],
        "policy_pass": bool(nat_pol.get("is_advisory_safe", True)) if nat_pol else None,
        "grounded_ratio": grade["grounded_ratio"],
        "judge_model": grade["judge_model"],
        "supported_claims": grade["supported_claims"],
        "unsupported_claims": grade["unsupported_claims"],
        "revision_count": 0, "hitl_required": False,
        "completed": completed,
        "error": f"NAT: {str(nat_error)[:200]}" if nat_error else None,
        "final_text_snippet": final_text[:300],
    }


# ---------------------------------------------------------------------------
# Mode 3 — langchain_react (pure LangChain via langgraph.prebuilt)
# ---------------------------------------------------------------------------
def _build_langchain_react_tools():
    """Adapt the 4 evidence-router layers as LangChain Tools."""
    from langchain_core.tools import tool

    @tool
    def wiki_search(query: str) -> str:
        """Search the governed TEP knowledge base (hybrid retrieval)."""
        from backend.agent_tools.evidence_router import retrieve_evidence
        r = retrieve_evidence("wiki", query, max_results=3)
        return json.dumps([{"source": h.get("source"), "text": h.get("text", "")[:300]}
                           for h in r["hits"]])

    @tool
    def find_similar_rca_notes(query: str) -> str:
        """Look up past RCA investigation notes (field feedback)."""
        from backend.agent_tools.evidence_router import retrieve_evidence
        r = retrieve_evidence("field_feedback", query)
        return json.dumps(r["hits"][:3])

    @tool
    def match_historical_patterns(fault_id: str) -> str:
        """Time-series case memory: find historical analogs."""
        from backend.agent_tools.evidence_router import retrieve_evidence
        r = retrieve_evidence("pattern_memory", "", fault_id=fault_id, top_k=3)
        return json.dumps(r["hits"][:3])

    @tool
    def inspect_anomaly(fault_id: str) -> str:
        """Inspect anomaly snapshot for a fault."""
        from backend.agent_tools.anomaly_tools import inspect_anomaly_snapshot
        return json.dumps(inspect_anomaly_snapshot(fault_id))

    return [wiki_search, find_similar_rca_notes, match_historical_patterns, inspect_anomaly]


def _run_langchain_react(case: Dict[str, Any]) -> Dict[str, Any]:
    fid, q = case["fault_id"], case["question"]
    t0 = time.time()
    try:
        from langgraph.prebuilt import create_react_agent
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        llm = ChatNVIDIA(
            model="meta/llama-3.3-70b-instruct",
            api_key=os.environ.get("NVIDIA_API_KEY", ""),
            temperature=0.2,
        )
        tools = _build_langchain_react_tools()
        agent = create_react_agent(llm, tools)

        system_msg = (
            "You are a Tennessee Eastman process RCA assistant. The current fault "
            f"is {fid}. Use the available tools to investigate and produce an "
            "operator advisory. Cite which tools/sources you used. ADVISORY-ONLY: "
            "do NOT suggest opening/closing valves or changing setpoints."
        )

        # Configure a high recursion_limit so it doesn't trip the same as NAT
        result = agent.invoke(
            {"messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": q},
            ]},
            config={"recursion_limit": 25},
        )
        msgs = result.get("messages", [])
        # Walk messages; track tool-name → evidence layer; collect tool outputs
        # as evidence snippets (so the held-out judge gets the same kind of
        # ground-truth retrieval text it gets for langgraph_multi — otherwise
        # the comparison is unfair); take the LAST AIMessage with non-empty
        # string content as the advisory.
        final_text = ""
        evidence_layers_used: List[str] = []
        evidence_snippets: List[str] = []
        for m in msgs:
            # Resolve role robustly (typed object OR dict)
            if isinstance(m, dict):
                role = m.get("role") or m.get("type") or ""
                content = m.get("content") or ""
                name = m.get("name") or ""
            else:
                role = getattr(m, "type", "") or ""
                content = getattr(m, "content", "") or ""
                name = getattr(m, "name", "") or ""
            # Content may be a list of blocks; collapse to string
            if isinstance(content, list):
                content = " ".join(
                    str(b.get("text", "")) if isinstance(b, dict) else str(b)
                    for b in content
                )
            if role in ("tool", "function") and name:
                if name == "wiki_search":
                    evidence_layers_used.append("wiki")
                elif name == "find_similar_rca_notes":
                    evidence_layers_used.append("field_feedback")
                elif name == "match_historical_patterns":
                    evidence_layers_used.append("pattern_memory")
                elif name == "inspect_anomaly":
                    evidence_layers_used.append("snapshot")
                # Capture the tool's actual output for the grounding judge
                if isinstance(content, str) and content.strip():
                    evidence_snippets.append(f"[{name}] {content[:400]}")
            if role in ("ai", "assistant") and isinstance(content, str) and content.strip():
                final_text = content  # keep last non-empty AI content

        from backend.agent_tools.policy_tools import check_advisory_policy
        pol = check_advisory_policy(final_text or "")
        completed = bool(final_text)

        # Pass the ReAct agent's actual tool outputs to the grounding judge.
        # Earlier drafts passed [] here, which made the langchain_react
        # vs langgraph_multi comparison unfair (langgraph_multi was being
        # judged WITH retrieved evidence in scope).
        grade = grade_grounding(final_text, evidence_snippets, fault_id=fid) \
                if completed else \
                {"grounded_ratio": 0.0, "supported_claims": 0,
                 "unsupported_claims": 0, "judge_model": "none",
                 "note": "skipped: no final text"}

        return {
            "mode": "langchain_react", "fault_id": fid, "case_source": case["source"],
            "runtime_seconds": round(time.time() - t0, 2),
            "evidence_layers_used": sorted(set(evidence_layers_used)),
            "policy_pass": bool(pol.get("is_advisory_safe", True)),
            "grounded_ratio": grade["grounded_ratio"],
            "judge_model": grade["judge_model"],
            "supported_claims": grade["supported_claims"],
            "unsupported_claims": grade["unsupported_claims"],
            "revision_count": 0, "hitl_required": False,
            "completed": completed, "error": None,
            "final_text_snippet": final_text[:300],
        }
    except Exception as exc:
        return {
            "mode": "langchain_react", "fault_id": fid, "case_source": case["source"],
            "runtime_seconds": round(time.time() - t0, 2),
            "evidence_layers_used": [], "policy_pass": None,
            "grounded_ratio": 0.0, "judge_model": "none",
            "supported_claims": 0, "unsupported_claims": 0,
            "revision_count": 0, "hitl_required": False,
            "completed": False, "error": f"{type(exc).__name__}: {exc}",
            "final_text_snippet": "",
        }


# ---------------------------------------------------------------------------
# Mode 4 — langgraph_multi (our orchestrator)
# ---------------------------------------------------------------------------
def _run_langgraph_multi(case: Dict[str, Any]) -> Dict[str, Any]:
    fid, q = case["fault_id"], case["question"]
    try:
        from backend.langgraph_rca import run_langgraph
        final = run_langgraph(fault_id=fid, question=q)
    except Exception as exc:
        return {
            "mode": "langgraph_multi", "fault_id": fid, "case_source": case["source"],
            "runtime_seconds": 0.0, "evidence_layers_used": [],
            "policy_pass": None, "grounded_ratio": 0.0, "judge_model": "none",
            "supported_claims": 0, "unsupported_claims": 0,
            "revision_count": 0, "hitl_required": False,
            "completed": False, "error": f"{type(exc).__name__}: {exc}",
            "final_text_snippet": "",
        }

    ev = final.get("evidence_by_layer") or {}
    layers = [L for L, hits in ev.items() if hits]
    eval_d = final.get("evaluation") or {}
    pol = eval_d.get("policy") or {}
    final_text = final.get("final_advisory") or ""
    completed = bool(final_text) and not final.get("hitl_required")

    # Held-out judge using the actual retrieved evidence
    grade = grade_grounding(
        final_text, _collect_evidence_snippets_from_lg(final), fault_id=fid,
    ) if completed else {"grounded_ratio": 0.0, "supported_claims": 0,
                          "unsupported_claims": 0, "judge_model": "none",
                          "note": "skipped"}

    return {
        "mode": "langgraph_multi", "fault_id": fid, "case_source": case["source"],
        "runtime_seconds": final.get("_runtime_seconds", 0.0),
        "evidence_layers_used": layers,
        "policy_pass": bool(pol.get("is_advisory_safe", True)),
        "grounded_ratio": grade["grounded_ratio"],
        "judge_model": grade["judge_model"],
        "supported_claims": grade["supported_claims"],
        "unsupported_claims": grade["unsupported_claims"],
        "revision_count": int(final.get("revision_count") or 0),
        "hitl_required": bool(final.get("hitl_required") or False),
        "completed": completed,
        "error": final.get("error"),
        "final_text_snippet": final_text[:300],
    }


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------
_MODE_RUNNERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "tools_only":       _run_tools_only,
    "nat_react":        _run_nat_react,
    "langchain_react":  _run_langchain_react,
    "langgraph_multi":  _run_langgraph_multi,
}


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def _summarise(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    from collections import defaultdict
    by_mode: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_mode[r["mode"]].append(r)

    def _mean(lst, key):
        vals = [r[key] for r in lst
                if r.get(key) is not None and isinstance(r[key], (int, float))]
        return round(sum(vals) / len(vals), 4) if vals else None

    summary: Dict[str, Any] = {}
    for mode, recs in by_mode.items():
        n = len(recs)
        n_done = sum(1 for r in recs if r.get("completed"))
        summary[mode] = {
            "n_runs": n,
            "n_completed": n_done,
            "completion_rate": round(n_done / n, 3) if n else 0,
            "grounded_ratio_mean": _mean(recs, "grounded_ratio"),
            "policy_pass_rate": round(
                sum(1 for r in recs if r.get("policy_pass") is True) / max(n, 1), 3),
            "runtime_seconds_mean": _mean(recs, "runtime_seconds"),
        }
    return summary


def _build_markdown(records: List[Dict[str, Any]], summary: Dict[str, Any],
                    judge_models_used: List[str]) -> str:
    lines = [
        "# 4-Way Comparative Evaluation",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Total runs:** {len(records)}",
        f"**Held-out judge model(s):** {judge_models_used}",
        "",
        "## Summary",
        "",
        "| Mode | runs | completed | grounded_ratio | policy_pass | runtime_mean (s) |",
        "|---|---|---|---|---|---|",
    ]
    for mode in ("tools_only", "nat_react", "langchain_react", "langgraph_multi"):
        if mode not in summary:
            continue
        s = summary[mode]
        lines.append(
            f"| {mode} | {s['n_runs']} | {s['n_completed']} | "
            f"{s['grounded_ratio_mean']} | {s['policy_pass_rate']} | "
            f"{s['runtime_seconds_mean']} |"
        )
    lines.append("")
    lines.append("## Per-run detail")
    for r in records:
        lines.append(
            f"- **[{r['mode']}/{r['fault_id']}/{r.get('case_source','?')}]** "
            f"completed={r.get('completed')} | grounded={r.get('grounded_ratio')} "
            f"| judge={r.get('judge_model','-')} "
            f"| layers={r.get('evidence_layers_used')} "
            f"| runtime={r.get('runtime_seconds')}s "
            + (f"| ERROR={r['error']}" if r.get('error') else "")
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--modes", nargs="+",
        default=list(_MODE_RUNNERS),
        help="Subset of modes to run",
    )
    parser.add_argument("--limit", type=int, default=4,
                        help="Max cases (golden + synthetic combined)")
    parser.add_argument("--no-synth", action="store_true",
                        help="Skip synthetic cases")
    args = parser.parse_args()

    # Load cases
    cases = list(_GOLDEN_CASES)
    if not args.no_synth:
        synth_path = _ROOT / "backend" / "evaluation" / "results" / "synthetic_cases.json"
        cases += _load_synthetic(synth_path)
    cases = cases[: args.limit]

    print(f"\n{'='*68}")
    print(f"  4-Way Eval | modes={args.modes} | {len(cases)} cases")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"{'='*68}\n")

    records: List[Dict[str, Any]] = []
    for i, case in enumerate(cases, 1):
        print(f"[case {i}/{len(cases)}] {case['fault_id']}  ({case.get('source','?')})")
        for mode in args.modes:
            if mode not in _MODE_RUNNERS:
                print(f"  [skip] unknown mode: {mode}")
                continue
            print(f"  → {mode} ...", end="", flush=True)
            rec = _MODE_RUNNERS[mode](case)
            records.append(rec)
            tag = "OK" if rec.get("completed") else "ERR"
            print(
                f"   {tag} runtime={rec.get('runtime_seconds')}s "
                f"grounded={rec.get('grounded_ratio')} "
                f"layers={rec.get('evidence_layers_used')}"
            )
        print()

    summary = _summarise(records)
    judges = sorted({r["judge_model"] for r in records if r.get("judge_model") and r["judge_model"] != "none"})

    out_dir = _ROOT / "backend" / "evaluation" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "full_eval_summary.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "modes": args.modes,
        "n_cases": len(cases),
        "judge_models_used": judges,
        "summary": summary,
        "per_run": records,
    }, indent=2, default=str))
    (out_dir / "full_eval_report.md").write_text(_build_markdown(records, summary, judges))

    print(f"\nWrote: {out_dir / 'full_eval_summary.json'}")
    print(f"Wrote: {out_dir / 'full_eval_report.md'}")
    print(f"\n=== Summary ===")
    for mode in args.modes:
        if mode in summary:
            s = summary[mode]
            print(f"  {mode:18s}  done={s['n_completed']}/{s['n_runs']}  "
                  f"grounded={s['grounded_ratio_mean']}  "
                  f"runtime={s['runtime_seconds_mean']}s")


if __name__ == "__main__":
    main()
