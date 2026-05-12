"""FastAPI router exposing the NAT agentic RCA workflow to the public UI.

Mount with:

    from backend.nat_api import nat_router
    app.include_router(nat_router)

All endpoints are read-only. They never mutate process state, never call
the simulator's setpoint/valve interface, and never store anything outside
``backend/diagnostics/nat_runs/`` and ``backend/evaluation/results/``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel  # type: ignore

from backend.agent_tools import search_process_knowledge
from backend.knowledge_manager import EnhancedKnowledgeManager
from backend.nat_runner import RUNS_DIR, run_nat, run_tools_only, _nat_available

nat_router = APIRouter(tags=["nat"])

_KM_SINGLETON: Optional[EnhancedKnowledgeManager] = None


def _km() -> EnhancedKnowledgeManager:
    global _KM_SINGLETON
    if _KM_SINGLETON is None:
        _KM_SINGLETON = EnhancedKnowledgeManager()
    return _KM_SINGLETON


# ---------------------------------------------------------------------------
# Wiki endpoints
# ---------------------------------------------------------------------------

@nat_router.get("/wiki/sources")
def wiki_sources() -> Dict[str, Any]:
    """List source documents and per-document chunk counts."""
    km = _km()
    by_doc: Dict[str, int] = {}
    for chunk in km.chunks:
        by_doc[chunk.source_document] = by_doc.get(chunk.source_document, 0) + 1
    return {
        "sources": [
            {"source_document": doc, "chunk_count": count}
            for doc, count in sorted(by_doc.items())
        ],
        "total_chunks": len(km.chunks),
    }


@nat_router.get("/wiki/search")
def wiki_search(q: str = Query("", min_length=0), max_results: int = 8) -> Dict[str, Any]:
    """Keyword-based search returning source-cited excerpts."""
    if not q.strip():
        return {"query": q, "excerpts": [], "note": "Empty query."}
    return search_process_knowledge(q, max_results=max_results)


# ---------------------------------------------------------------------------
# Agent endpoints
# ---------------------------------------------------------------------------

class AgentRunRequest(BaseModel):
    fault_id: str = "fault1"
    question: str = "Diagnose the current TEP anomaly and recommend operator review steps."
    use_nat: bool = False


@nat_router.post("/agent/run")
def agent_run(req: AgentRunRequest) -> Dict[str, Any]:
    """Trigger an agent run.

    By default we run the deterministic tool-trace path so the UI works
    without NAT installed. Pass ``use_nat=true`` to attempt the real NAT
    workflow when available.
    """
    if req.use_nat and _nat_available():
        payload = run_nat(req.fault_id, req.question)
    else:
        payload = run_tools_only(req.fault_id, req.question)
    return payload


@nat_router.get("/agent/runs/latest")
def agent_runs_latest() -> Dict[str, Any]:
    runs = sorted(RUNS_DIR.glob("run_*.json"))
    if not runs:
        raise HTTPException(status_code=404, detail="No agent runs yet.")
    return json.loads(runs[-1].read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Evaluation endpoint
# ---------------------------------------------------------------------------

_RESULTS_DIR = Path(__file__).resolve().parent / "evaluation" / "results"


@nat_router.get("/evaluation/summary")
def evaluation_summary() -> Dict[str, Any]:
    summary_path = _RESULTS_DIR / "summary.json"
    cases_path = _RESULTS_DIR / "cases.jsonl"
    if not summary_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No evaluation summary yet. Run "
                   "'python backend/evaluation/evaluate_nat_rca.py --tools-only'.",
        )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    cases: List[Dict[str, Any]] = []
    if cases_path.exists():
        for line in cases_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return {"summary": summary, "cases": cases}
