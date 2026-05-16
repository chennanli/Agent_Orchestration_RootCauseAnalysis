"""Retrieval substrate evaluation: keyword vs sparse vs dense vs hybrid.

Compares the four substrates from `backend/agent_tools/vector_knowledge.py` on
a small hand-curated query set. Reports recall@k, mean reciprocal rank (MRR),
and per-query latency.

The "gold" relevance signal for each query is the set of source markdown
filenames that should appear in the top-k. This is coarse but honest — the
goal is to show *relative* performance of the 4 substrates, not to claim a
production-grade recall number.

Outputs:
  backend/evaluation/results/retrieval_summary.json
  backend/evaluation/results/retrieval_report.md

Usage:
  python backend/evaluation/evaluate_retrieval.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.agent_tools.vector_knowledge import (  # noqa: E402
    build_or_load_index,
    keyword_search,
    sparse_search,
    dense_search,
    hybrid_search,
)

# ---------------------------------------------------------------------------
# Gold set: (query, set of relevant source filenames)
# ---------------------------------------------------------------------------
_GOLD: List[Dict[str, Any]] = [
    {
        "query": "reactor cooling water inlet temperature step disturbance",
        "relevant_sources": {"Downs & Vogel.md",
                             "4_TEP_Calculation_Methods_And_Equations.md"},
    },
    {
        "query": "A and C feed ratio fault stripper compositions",
        "relevant_sources": {"Downs & Vogel.md", "TEP McAvoy.md"},
    },
    {
        "query": "control structure for the Tennessee Eastman process plantwide",
        "relevant_sources": {"1_TEP_Control_Structure_Analysis.md",
                             "TEP McAvoy.md"},
    },
    {
        "query": "PCA Hotelling T2 statistic anomaly detection",
        "relevant_sources": {"4_TEP_Calculation_Methods_And_Equations.md",
                             "2_TEP_Complete_Technical_Reference.md"},
    },
    {
        "query": "process measurement noise standard deviation TEP",
        "relevant_sources": {"Downs & Vogel.md",
                             "2_TEP_Complete_Technical_Reference.md"},
    },
    {
        "query": "compressor work purge valve manipulated variable",
        "relevant_sources": {"TEP McAvoy.md",
                             "1_TEP_Control_Structure_Analysis.md"},
    },
    {
        "query": "reactor pressure level temperature kinetics",
        "relevant_sources": {"Downs & Vogel.md",
                             "4_TEP_Calculation_Methods_And_Equations.md"},
    },
]


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def _norm_source(s: str) -> str:
    """Normalise filename for comparison: lowercase, strip .md, strip spaces."""
    s = (s or "").strip().lower()
    if s.endswith(".md"):
        s = s[:-3]
    return s.replace(" ", "").replace("_", "")


def _recall_at_k(hits: List[Dict[str, Any]], relevant: set, k: int) -> float:
    """Fraction of relevant sources that appear in top-k hits (ext-insensitive)."""
    if not relevant:
        return 0.0
    rel_norm = {_norm_source(r) for r in relevant}
    seen = {_norm_source(h.get("source", "")) for h in hits[:k]}
    return len(seen & rel_norm) / len(rel_norm)


def _reciprocal_rank(hits: List[Dict[str, Any]], relevant: set) -> float:
    """1/rank of the first relevant hit, else 0 (ext-insensitive)."""
    rel_norm = {_norm_source(r) for r in relevant}
    for i, h in enumerate(hits, 1):
        if _norm_source(h.get("source", "")) in rel_norm:
            return 1.0 / i
    return 0.0


# ---------------------------------------------------------------------------
# Per-substrate runner
# ---------------------------------------------------------------------------
def _eval_substrate(name: str, search_fn, k: int = 5) -> Dict[str, Any]:
    per_query: List[Dict[str, Any]] = []
    recalls: List[float] = []
    rrs: List[float] = []
    latencies: List[float] = []

    for case in _GOLD:
        q = case["query"]
        rel = case["relevant_sources"]
        t0 = time.time()
        try:
            hits = search_fn(q, k=k)
            if hits and isinstance(hits[0], dict) and hits[0].get("error"):
                hits = []
        except Exception as exc:
            hits = []
        latency = (time.time() - t0) * 1000
        r = _recall_at_k(hits, rel, k)
        rr = _reciprocal_rank(hits, rel)
        recalls.append(r)
        rrs.append(rr)
        latencies.append(latency)
        per_query.append({
            "query": q,
            "top_sources": [h.get("source", "") for h in hits[:k]],
            "recall_at_k": round(r, 3),
            "rr": round(rr, 3),
            "latency_ms": round(latency, 1),
        })

    return {
        "substrate": name,
        "k": k,
        "queries": len(_GOLD),
        "recall_at_k_mean": round(sum(recalls) / len(recalls), 4),
        "mrr": round(sum(rrs) / len(rrs), 4),
        "latency_ms_mean": round(sum(latencies) / len(latencies), 1),
        "latency_ms_p95": round(sorted(latencies)[int(0.95 * len(latencies))], 1),
        "per_query": per_query,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("[info] ensuring index is built...")
    info = build_or_load_index()
    print(f"  {info}")

    K = 5
    print(f"\n=== Retrieval Eval (k={K}, {len(_GOLD)} queries) ===\n")

    results: Dict[str, Any] = {}
    for name, fn in [
        ("keyword", keyword_search),
        ("sparse",  sparse_search),
        ("dense",   dense_search),
        ("hybrid",  hybrid_search),
    ]:
        print(f"[{name}] running...")
        results[name] = _eval_substrate(name, fn, k=K)
        s = results[name]
        print(f"   recall@{K}={s['recall_at_k_mean']}  mrr={s['mrr']}  "
              f"latency_mean={s['latency_ms_mean']}ms")

    # --- Outputs ---
    _OUT = _ROOT / "backend" / "evaluation" / "results"
    _OUT.mkdir(parents=True, exist_ok=True)
    (_OUT / "retrieval_summary.json").write_text(json.dumps({
        "generated_at": datetime.utcnow().isoformat(),
        "k": K,
        "n_queries": len(_GOLD),
        "substrates": results,
    }, indent=2, default=str))

    md = [
        "# Retrieval Substrate Evaluation",
        f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Queries:** {len(_GOLD)}  |  **k:** {K}",
        "",
        f"| Substrate | recall@{K} | MRR | latency_mean (ms) | latency_p95 (ms) |",
        "|---|---|---|---|---|",
    ]
    for name in ("keyword", "sparse", "dense", "hybrid"):
        s = results[name]
        md.append(
            f"| {name} | {s['recall_at_k_mean']} | {s['mrr']} | "
            f"{s['latency_ms_mean']} | {s['latency_ms_p95']} |"
        )
    md.append("")
    md.append("## Per-query top sources")
    for q_idx, case in enumerate(_GOLD):
        md.append(f"\n### Q{q_idx+1}: {case['query']}")
        md.append(f"_relevant: {sorted(case['relevant_sources'])}_")
        for name in ("keyword", "sparse", "dense", "hybrid"):
            top = results[name]["per_query"][q_idx]["top_sources"]
            md.append(f"- **{name}**: {top}")

    (_OUT / "retrieval_report.md").write_text("\n".join(md))

    print(f"\nWrote: {_OUT / 'retrieval_summary.json'}")
    print(f"Wrote: {_OUT / 'retrieval_report.md'}")

    # Headline comparison
    print(f"\n{'='*60}")
    print(f"  HEADLINE")
    print(f"  keyword recall@{K} = {results['keyword']['recall_at_k_mean']}")
    print(f"  sparse  recall@{K} = {results['sparse']['recall_at_k_mean']}")
    print(f"  dense   recall@{K} = {results['dense']['recall_at_k_mean']}")
    print(f"  hybrid  recall@{K} = {results['hybrid']['recall_at_k_mean']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
