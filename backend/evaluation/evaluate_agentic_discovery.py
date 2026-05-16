"""Evaluation harness: NAT baseline vs LangGraph multi-evidence.

Runs each golden case through two modes:
  nat_baseline             — existing NAT ReAct agent (backend/nat_runner.py)
  langgraph_multi_evidence — new LangGraph 5-node orchestrator

Metrics per (mode, case):
  runtime_seconds, evidence_layers_used, policy_pass, grounded_ratio,
  evidence_hit_rate, revision_count, hitl_required

Outputs:
  backend/evaluation/results/discovery_summary.json
  backend/evaluation/results/discovery_report.md

Usage:
  python backend/evaluation/evaluate_agentic_discovery.py --limit 3
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv()

# ---------------------------------------------------------------------------
# Golden cases (3 for MVP speed)
# ---------------------------------------------------------------------------
_GOLDEN_CASES = [
    {
        "fault_id": "fault1",
        "question": (
            "Diagnose the current TEP process anomaly. "
            "Identify the most likely root cause and any contributing variables."
        ),
    },
    {
        "fault_id": "fault6",
        "question": (
            "Diagnose the TEP anomaly for fault6. "
            "Is this consistent with a feed-loss scenario?"
        ),
    },
    {
        "fault_id": "fault4",
        "question": (
            "Diagnose the TEP anomaly for fault4. "
            "What process variable is most likely driving this event?"
        ),
    },
]

# ---------------------------------------------------------------------------
# LLM-as-judge for NAT grounding (fairness — same check as LangGraph)
# ---------------------------------------------------------------------------
_JUDGE_PROMPT_TEMPLATE = """You are an Evidence Grounding judge.

ADVISORY TEXT: {text}

FAULT ID: {fault_id}

Estimate what fraction of the factual claims in this advisory are supported
by observable process data or domain knowledge (as opposed to speculation).

Respond with JSON only:
{{"grounded_ratio": 0.0-1.0, "note": "brief one-sentence reason"}}"""


def _judge_grounding(text: str, fault_id: str) -> float:
    """Call LLM to estimate grounding ratio."""
    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        llm = ChatNVIDIA(
            model="meta/llama-3.3-70b-instruct",
            api_key=os.environ.get("NVIDIA_API_KEY", ""),
            temperature=0.0,
            max_tokens=256,
        )
        prompt = _JUDGE_PROMPT_TEMPLATE.format(text=text[:800], fault_id=fault_id)
        resp = llm.invoke([{"role": "user", "content": prompt}])
        content = resp.content if hasattr(resp, "content") else str(resp)
        m = re.search(r'\{.*?\}', content, re.DOTALL)
        if m:
            return float(json.loads(m.group()).get("grounded_ratio", 0.5))
    except Exception:
        pass
    return 0.5  # fallback


# ---------------------------------------------------------------------------
# NAT baseline runner
# ---------------------------------------------------------------------------
def _run_nat_case(case: Dict[str, Any]) -> Dict[str, Any]:
    fault_id = case["fault_id"]
    question = case["question"]
    t0 = time.time()
    error = None
    policy_pass = None
    grounded_ratio = 0.5
    final_text = ""

    try:
        from backend.nat_runner import run_nat
        from backend.agent_tools.policy_tools import check_advisory_policy
        result = run_nat(fault_id=fault_id, question=question)

        # NAT returns final_answer as {"text": ..., "policy_check": ..., ...}
        fa = result.get("final_answer") or {}
        if isinstance(fa, dict):
            final_text = str(fa.get("text") or "")
            nat_policy = fa.get("policy_check") or {}
        else:
            final_text = str(fa)
            nat_policy = {}
        final_text = final_text[:1000] if final_text else ""

        # Surface NAT's own error if it failed internally
        nat_error = result.get("error")
        if nat_error:
            error = f"NAT internal error: {str(nat_error)[:200]}"

        # Use NAT's own policy_check; fall back to recomputing
        if nat_policy:
            policy_pass = bool(nat_policy.get("is_advisory_safe", True))
        elif final_text:
            policy_pass = bool(check_advisory_policy(final_text).get("is_advisory_safe", True))
        else:
            policy_pass = None

        # Only judge grounding if we have real text (skip the failure stub)
        if final_text and "execution failed" not in final_text.lower():
            grounded_ratio = _judge_grounding(final_text, fault_id)
        else:
            grounded_ratio = 0.0
    except Exception as exc:
        error = f"Harness {type(exc).__name__}: {exc}"
        policy_pass = None
        grounded_ratio = 0.0
        final_text = ""

    runtime = round(time.time() - t0, 2)

    return {
        "mode": "nat_baseline",
        "fault_id": fault_id,
        "runtime_seconds": runtime,
        "evidence_layers_used": ["wiki", "field_feedback"],  # NAT uses these 2
        "policy_pass": policy_pass,
        "grounded_ratio": grounded_ratio,
        "evidence_hit_rate": 1.0 if not error else 0.0,
        "revision_count": 0,
        "hitl_required": False,
        "error": error,
        "final_text_snippet": final_text[:300],
    }


# ---------------------------------------------------------------------------
# LangGraph multi-evidence runner
# ---------------------------------------------------------------------------
def _run_langgraph_case(case: Dict[str, Any]) -> Dict[str, Any]:
    fault_id = case["fault_id"]
    question = case["question"]
    error = None

    try:
        from backend.langgraph_rca import run_langgraph
        final = run_langgraph(fault_id=fault_id, question=question)
    except Exception as exc:
        return {
            "mode": "langgraph_multi_evidence",
            "fault_id": fault_id,
            "runtime_seconds": 0.0,
            "evidence_layers_used": [],
            "policy_pass": None,
            "grounded_ratio": 0.0,
            "evidence_hit_rate": 0.0,
            "revision_count": 0,
            "hitl_required": False,
            "error": f"{type(exc).__name__}: {exc}",
            "final_text_snippet": "",
        }

    ev = final.get("evidence_by_layer", {})
    layers_used = [L for L, hits in ev.items() if hits]
    # Use the source-of-truth layer list from langgraph_rca rather than the
    # number `3.0`. If a 4th evidence layer is ever wired into the
    # EvidenceAgent (the `policy` layer is intentionally NOT queried here —
    # it's used by the Evaluator), this normaliser updates with it.
    try:
        from backend.langgraph_rca import _EVIDENCE_LAYERS as _LG_LAYERS
        _n_possible = max(len(_LG_LAYERS), 1)
    except Exception:
        _n_possible = 3  # safe fallback if the import path moves
    ev_hit_rate = (
        len(layers_used) / float(_n_possible)
        if layers_used else 0.0
    )

    eval_d = final.get("evaluation", {})
    policy_d = eval_d.get("policy", {})

    return {
        "mode": "langgraph_multi_evidence",
        "fault_id": fault_id,
        "runtime_seconds": final.get("_runtime_seconds", 0.0),
        "evidence_layers_used": layers_used,
        "policy_pass": bool(policy_d.get("is_advisory_safe", True)),
        "grounded_ratio": float(eval_d.get("grounded_ratio", 0.5)),
        "evidence_hit_rate": round(ev_hit_rate, 3),
        "revision_count": int(final.get("revision_count", 0)),
        "hitl_required": bool(final.get("hitl_required", False)),
        "error": final.get("error"),
        "final_text_snippet": (final.get("final_advisory") or "")[:300],
    }


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------
def _build_markdown_report(records: List[Dict[str, Any]]) -> str:
    nat_recs = [r for r in records if r["mode"] == "nat_baseline"]
    lg_recs = [r for r in records if r["mode"] == "langgraph_multi_evidence"]

    def avg(lst, key):
        vals = [r[key] for r in lst if r.get(key) is not None
                and isinstance(r[key], (int, float))]
        return round(sum(vals) / len(vals), 3) if vals else "n/a"

    def fmt_layers(lst):
        all_layers = []
        for r in lst:
            all_layers.extend(r.get("evidence_layers_used", []))
        if not all_layers:
            return "0"
        from collections import Counter
        c = Counter(all_layers)
        top = sorted(c.items(), key=lambda x: -x[1])
        return ", ".join(f"{k}({v})" for k, v in top[:4])

    lines = [
        "# Agentic Discovery Evaluation Report",
        f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Cases:** {len(set(r['fault_id'] for r in records))}",
        "",
        "## Summary Table",
        "",
        "| Metric | NAT Baseline | LangGraph Multi-Evidence |",
        "|--------|-------------|--------------------------|",
        f"| grounded_ratio (mean) | {avg(nat_recs, 'grounded_ratio')} | {avg(lg_recs, 'grounded_ratio')} |",
        f"| evidence_layers_used | {fmt_layers(nat_recs)} | {fmt_layers(lg_recs)} |",
        f"| evidence_hit_rate (mean) | {avg(nat_recs, 'evidence_hit_rate')} | {avg(lg_recs, 'evidence_hit_rate')} |",
        f"| policy_pass rate | {sum(1 for r in nat_recs if r.get('policy_pass'))/max(len(nat_recs),1):.0%} | {sum(1 for r in lg_recs if r.get('policy_pass'))/max(len(lg_recs),1):.0%} |",
        f"| revision_count (mean) | {avg(nat_recs, 'revision_count')} | {avg(lg_recs, 'revision_count')} |",
        f"| hitl_required | — | {sum(1 for r in lg_recs if r.get('hitl_required'))} / {len(lg_recs)} |",
        f"| runtime_seconds (mean) | {avg(nat_recs, 'runtime_seconds')} | {avg(lg_recs, 'runtime_seconds')} |",
        "",
        "## Per-Case Results",
        "",
    ]

    for r in records:
        lines.append(f"### {r['mode']} / {r['fault_id']}")
        if r.get("error"):
            lines.append(f"- **ERROR**: {r['error']}")
        lines.append(f"- runtime: {r['runtime_seconds']}s")
        lines.append(f"- evidence_layers: {r.get('evidence_layers_used', [])}")
        lines.append(f"- policy_pass: {r.get('policy_pass')}")
        lines.append(f"- grounded_ratio: {r.get('grounded_ratio')}")
        lines.append(f"- revision_count: {r.get('revision_count', 0)}")
        lines.append(f"- hitl_required: {r.get('hitl_required', False)}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Evaluate NAT vs LangGraph")
    parser.add_argument("--limit", type=int, default=3,
                        help="Number of golden cases to run (default 3)")
    parser.add_argument("--skip-nat", action="store_true",
                        help="Skip the NAT baseline (run LangGraph only)")
    parser.add_argument("--skip-langgraph", action="store_true",
                        help="Skip the LangGraph mode (run NAT only); merges with existing LangGraph results in discovery_summary.json if present")
    args = parser.parse_args()

    cases = _GOLDEN_CASES[: args.limit]
    print(f"\n{'='*60}")
    print(f"  Agentic Discovery Evaluation  |  {len(cases)} case(s)")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"{'='*60}\n")

    records: List[Dict[str, Any]] = []

    # If --skip-langgraph or --skip-nat: pre-load the corresponding records
    # from the previous discovery_summary.json so we can merge cleanly.
    existing_lg_recs: List[Dict[str, Any]] = []
    existing_nat_recs: List[Dict[str, Any]] = []
    if args.skip_langgraph or args.skip_nat:
        prev = _ROOT / "backend" / "evaluation" / "results" / "discovery_summary.json"
        if prev.exists():
            try:
                prev_data = json.loads(prev.read_text())
                existing_lg_recs = [
                    r for r in prev_data.get("per_case", [])
                    if r.get("mode") == "langgraph_multi_evidence"
                ]
                existing_nat_recs = [
                    r for r in prev_data.get("per_case", [])
                    if r.get("mode") == "nat_baseline"
                ]
                if args.skip_langgraph:
                    print(f"[info] reusing {len(existing_lg_recs)} langgraph records from previous run")
                if args.skip_nat:
                    print(f"[info] reusing {len(existing_nat_recs)} nat_baseline records from previous run")
            except Exception as exc:
                print(f"[warn] could not load previous summary: {exc}")

    for i, case in enumerate(cases, 1):
        fid = case["fault_id"]
        print(f"[{i}/{len(cases)}] {fid}")

        # --- LangGraph ---
        if args.skip_langgraph:
            # Pull from the previous run if we have it
            match = next((r for r in existing_lg_recs if r["fault_id"] == fid), None)
            if match:
                records.append(match)
                print(f"  → langgraph_multi_evidence (reused from previous summary)")
        else:
            print(f"  → langgraph_multi_evidence ...")
            lg_rec = _run_langgraph_case(case)
            records.append(lg_rec)
            status = "ERROR" if lg_rec.get("error") else "OK"
            print(f"     {status}  runtime={lg_rec['runtime_seconds']}s  "
                  f"layers={lg_rec['evidence_layers_used']}  "
                  f"grounded={lg_rec['grounded_ratio']}")

        # --- NAT baseline ---
        if args.skip_nat:
            match = next((r for r in existing_nat_recs if r["fault_id"] == fid), None)
            if match:
                records.append(match)
                print(f"  → nat_baseline (reused from previous summary)")
        else:
            print(f"  → nat_baseline ...")
            nat_rec = _run_nat_case(case)
            records.append(nat_rec)
            status = "ERROR" if nat_rec.get("error") else "OK"
            print(f"     {status}  runtime={nat_rec['runtime_seconds']}s  "
                  f"grounded={nat_rec['grounded_ratio']}")

        print()

    # --- Outputs ---
    _OUT = _ROOT / "backend" / "evaluation" / "results"
    _OUT.mkdir(parents=True, exist_ok=True)

    # Compute summary statistics
    nat_recs = [r for r in records if r["mode"] == "nat_baseline"]
    lg_recs  = [r for r in records if r["mode"] == "langgraph_multi_evidence"]

    def _mean(lst, key):
        vals = [r[key] for r in lst
                if r.get(key) is not None and isinstance(r[key], (int, float))]
        return round(sum(vals) / len(vals), 4) if vals else None

    summary = {
        "generated_at": datetime.utcnow().isoformat(),
        "cases_run": len(cases),
        "nat_baseline": {
            "grounded_ratio_mean": _mean(nat_recs, "grounded_ratio"),
            "evidence_hit_rate_mean": _mean(nat_recs, "evidence_hit_rate"),
            "policy_pass_rate": (
                sum(1 for r in nat_recs if r.get("policy_pass")) / max(len(nat_recs), 1)
            ) if nat_recs else None,
            "runtime_seconds_mean": _mean(nat_recs, "runtime_seconds"),
            "evidence_layers_always": ["wiki", "field_feedback"],
        },
        "langgraph_multi_evidence": {
            "grounded_ratio_mean": _mean(lg_recs, "grounded_ratio"),
            "evidence_hit_rate_mean": _mean(lg_recs, "evidence_hit_rate"),
            "policy_pass_rate": (
                sum(1 for r in lg_recs if r.get("policy_pass")) / max(len(lg_recs), 1)
            ) if lg_recs else None,
            "revision_count_mean": _mean(lg_recs, "revision_count"),
            "hitl_required_count": sum(1 for r in lg_recs if r.get("hitl_required")),
            "runtime_seconds_mean": _mean(lg_recs, "runtime_seconds"),
            "evidence_layers_dynamic": True,
        },
        "per_case": records,
    }

    json_path = _OUT / "discovery_summary.json"
    md_path   = _OUT / "discovery_report.md"

    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    md_content = _build_markdown_report(records)
    with open(md_path, "w") as f:
        f.write(md_content)

    print(f"\nOutputs written:")
    print(f"  {json_path}")
    print(f"  {md_path}")

    # Print headline numbers
    lg_grounded = summary["langgraph_multi_evidence"].get("grounded_ratio_mean")
    nat_grounded = summary["nat_baseline"].get("grounded_ratio_mean")
    lg_layers   = summary["langgraph_multi_evidence"].get("evidence_hit_rate_mean")
    # Pull layer count from the source of truth so the headline stays correct
    # if the EvidenceAgent ever adds a 4th queryable layer.
    try:
        from backend.langgraph_rca import _EVIDENCE_LAYERS as _LG_LAYERS
        _n_layers = len(_LG_LAYERS)
    except Exception:
        _n_layers = 3

    print(f"\n{'='*60}")
    print(f"  HEADLINE NUMBERS")
    print(f"  LangGraph grounded_ratio : {lg_grounded}")
    print(f"  NAT      grounded_ratio : {nat_grounded}")
    print(f"  LangGraph evidence_hit_rate: {lg_layers} "
          f"(fraction of {_n_layers} configured evidence layers hit)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
