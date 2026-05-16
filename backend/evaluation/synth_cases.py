"""Synthetic golden-case generator.

The hand-curated 3-case eval is a smoke test. For Sprint 2 we want a larger,
honest sample. This script asks an LLM to generate a diverse set of natural
diagnosis questions for each fault, anchored on:
  - the known TEP fault family description (from pattern_tools._FAULT_PATTERNS)
  - the top contributing variables observed by inspect_anomaly_snapshot

Each generated case carries the fault_id and a `synthetic=True` tag so the
4-way harness can keep them separate from the hand-curated golden set.

Outputs:
  backend/evaluation/results/synthetic_cases.json

Usage:
  python backend/evaluation/synth_cases.py --faults fault1 fault4 fault6 --per-fault 3
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
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv()


_PROMPT_TMPL = """You generate honest diagnostic questions that a control-room
operator (or junior process engineer) might type into a TEP RCA copilot.

Context for this fault:
  fault_id          : {fault_id}
  known fault type  : {family}
  top variables now : {top_vars}

Produce {n} DISTINCT questions. Each must:
  - feel natural, not templated
  - be answerable with the existing tools (anomaly snapshot, variable ranking,
    wiki RAG, prior RCA notes, time-series case memory, policy check)
  - vary in framing (some open-ended, some about a specific variable, some
    asking about historical analogs, etc.)
  - NOT reveal the fault type to the agent (the agent should diagnose, not
    have it spoonfed)

Respond with a JSON array of {n} strings only. No prose, no markdown."""


def _generator_llm():
    from langchain_nvidia_ai_endpoints import ChatNVIDIA  # noqa: WPS433
    return ChatNVIDIA(
        model="meta/llama-3.3-70b-instruct",
        api_key=os.environ.get("NVIDIA_API_KEY", ""),
        temperature=0.7,
        max_tokens=512,
    )


def _top_vars_for(fault_id: str, k: int = 5) -> List[str]:
    try:
        from backend.agent_tools.anomaly_tools import rank_contributing_variables
        ranked = rank_contributing_variables(fault_id, top_k=k)
        # Tool actually returns key `top_variables` (not `top_contributors`).
        return [v.get("variable", "") for v in ranked.get("top_variables", [])[:k]]
    except Exception:
        return []


def _family_for(fault_id: str) -> str:
    from backend.agent_tools.pattern_tools import _FAULT_PATTERNS
    return _FAULT_PATTERNS.get(fault_id, "unknown disturbance type")


def generate_cases(fault_ids: List[str], per_fault: int = 3) -> List[Dict[str, Any]]:
    llm = _generator_llm()
    out: List[Dict[str, Any]] = []
    for fid in fault_ids:
        family = _family_for(fid)
        top = _top_vars_for(fid)
        prompt = _PROMPT_TMPL.format(
            fault_id=fid,
            family=family,
            top_vars=top,
            n=per_fault,
        )
        try:
            resp = llm.invoke([{"role": "user", "content": prompt}])
            content = resp.content if hasattr(resp, "content") else str(resp)
            m = re.search(r"\[.*\]", content, re.DOTALL)
            if not m:
                continue
            questions = json.loads(m.group())
            if not isinstance(questions, list):
                continue
        except Exception as exc:
            print(f"[warn] gen failed for {fid}: {exc}")
            continue
        for q in questions:
            if isinstance(q, str) and len(q.strip()) > 12:
                out.append({
                    "fault_id": fid,
                    "question": q.strip(),
                    "family_label": family,  # ground truth, hidden from agent
                    "synthetic": True,
                    "generated_at": datetime.utcnow().isoformat(),
                })
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--faults", nargs="+",
        default=["fault1", "fault4", "fault6", "fault7", "fault11"],
    )
    parser.add_argument("--per-fault", type=int, default=3)
    parser.add_argument(
        "--out",
        default=str(_ROOT / "backend" / "evaluation" / "results" / "synthetic_cases.json"),
    )
    args = parser.parse_args()

    print(f"Generating {args.per_fault} cases × {len(args.faults)} faults …")
    t0 = time.time()
    cases = generate_cases(args.faults, args.per_fault)
    elapsed = time.time() - t0
    print(f"Generated {len(cases)} cases in {elapsed:.1f}s")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(cases, indent=2))
    print(f"Wrote: {out_path}")

    # Show a sample
    for c in cases[:3]:
        print(f"  - [{c['fault_id']}] {c['question'][:90]}")


if __name__ == "__main__":
    main()
