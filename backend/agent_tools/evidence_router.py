"""4-Layer Evidence Router.

Single entry point that maps a layer name to the appropriate retrieval
backend. Turns the existing 6 agent tools into a coherent 4-layer evidence
narrative:

  wiki           → Governed Wiki RAG (keyword search over TEP markdown KB)
  field_feedback → Field Feedback RAG (prior RCA notes / similar-fault notes)
  policy         → Policy / Constraint Catalog (queryable view of advisory rules)
  pattern_memory → Time-Series Case Memory (matrix profile historical analog)

Each layer returns a uniform envelope:
  {layer, query, hits: list[dict], source_count, latency_ms}

This wrapper adds no new logic — it re-frames existing tools as a story.
Phase 6 will swap `wiki` to hybrid vector+BM25 retrieval.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Layer implementations
# ---------------------------------------------------------------------------

def _retrieve_wiki(query: str, **kwargs) -> List[Dict[str, Any]]:
    """Governed Wiki RAG.

    Default substrate = hybrid (RRF of NIM dense + BM25 sparse).
    Override:
      - env  TEP_WIKI_SUBSTRATE in {"keyword","dense","sparse","hybrid"}
      - kwarg substrate=...     (same options; takes precedence over env)
    A2A delegation:
      - env TEP_WIKI_VIA_A2A=1 + TEP_WIKI_A2A_URL=http://...:8765 → call
        the standalone Wiki A2A server instead of in-process search. This
        demonstrates the agent-card / task-interface boundary; the
        orchestrator depends only on the A2A contract.
    Fallbacks: any failure falls back to keyword.
    """
    import os
    max_results = int(kwargs.get("max_results", 4))

    # --- A2A delegation path (opt-in) ---
    if os.environ.get("TEP_WIKI_VIA_A2A") == "1":
        try:
            from backend.a2a_router import call_remote_wiki_via_a2a
            url = os.environ.get("TEP_WIKI_A2A_URL", "http://127.0.0.1:8765")
            r = call_remote_wiki_via_a2a(query, base_url=url, k=max_results)
            hits = r.get("hits", [])
            if hits:
                # Tag the hits so audit_trail can show the A2A boundary fired
                for h in hits:
                    h["via"] = "a2a"
                return hits
        except Exception:
            pass  # fall through to in-process path

    substrate = str(
        kwargs.get("substrate")
        or os.environ.get("TEP_WIKI_SUBSTRATE", "hybrid")
    ).lower()

    try:
        from backend.agent_tools.vector_knowledge import (
            hybrid_search, dense_search, sparse_search, keyword_search,
            build_or_load_index,
        )
        build_or_load_index()  # idempotent if already built
        if substrate == "hybrid":
            hits = hybrid_search(query, k=max_results)
        elif substrate == "dense":
            hits = dense_search(query, k=max_results)
        elif substrate == "sparse":
            hits = sparse_search(query, k=max_results)
        else:
            hits = keyword_search(query, k=max_results)
        # If something returned with an error marker, fall back to keyword
        if hits and isinstance(hits[0], dict) and hits[0].get("error"):
            hits = keyword_search(query, k=max_results)
    except Exception:
        # Hard fallback: legacy keyword path
        hits = keyword_search(query, k=max_results)

    return hits


def _retrieve_field_feedback(query: str, **kwargs) -> List[Dict[str, Any]]:
    """Field Feedback RAG — keyword search over prior RCA investigation notes.

    Re-frames `find_similar_faults` as "field feedback / past RCA notes"
    rather than an anomaly similarity check.

    The underlying tool returns:
        {"signature": str, "matches": [
            {"fault_id", "fault_family", "score", "evidence", "source"}, ...
         ], "note": str}
    """
    from backend.agent_tools.history_tools import find_similar_faults
    top_k = int(kwargs.get("top_k", 3))
    raw = find_similar_faults(query, top_k=top_k)
    matches = raw.get("matches") or []
    hits = [
        {
            "source": m.get("fault_id", "unknown"),
            "fault_family": m.get("fault_family", ""),
            "score": float(m.get("score", 0.0)),
            "text": m.get("evidence", "") or m.get("fault_family", ""),
            "evidence_source": m.get("source", ""),
        }
        for m in (matches if isinstance(matches, list) else [matches])
    ]
    return hits


def _retrieve_policy(query: str, **kwargs) -> List[Dict[str, Any]]:
    """Policy / Constraint Catalog — queryable view of advisory rule patterns.

    Returns the forbidden-control and overclaim pattern sets as a structured
    catalog so the Evidence and Evaluator agents can reason about constraints
    without calling `check_advisory_policy` on a draft text.
    """
    from backend.agent_tools.policy_tools import (
        _FORBIDDEN_CONTROL_PATTERNS,
        _OVERCLAIM_PATTERNS,
        _SUGGESTIONS,
    )
    q_lower = query.lower()
    # Simple keyword filter on patterns
    def _matches(pat: str) -> bool:
        # strip regex metacharacters for display matching
        clean = pat.replace(r"\b", "").replace("(", "").replace(")", "")
        return any(w in q_lower for w in clean.split() if len(w) > 3)

    hits: List[Dict[str, Any]] = []
    for pat in _FORBIDDEN_CONTROL_PATTERNS:
        hits.append({"type": "forbidden_control", "pattern": pat, "score": 1.0})
    for pat in _OVERCLAIM_PATTERNS:
        hits.append({"type": "overclaim", "pattern": pat, "score": 1.0})
    for sug in _SUGGESTIONS:
        hits.append({"type": "suggestion", "pattern": sug, "score": 0.5})
    return hits


def _retrieve_pattern_memory(query: str, **kwargs) -> List[Dict[str, Any]]:
    """Time-Series Case Memory — Matrix Profile historical analog retrieval.

    kwargs may include: fault_id, variables, window, top_k.
    If fault_id is not provided, defaults to "fault1".
    """
    from backend.agent_tools.pattern_tools import match_historical_patterns
    fault_id = str(kwargs.get("fault_id", "fault1"))
    variables = kwargs.get("variables", None)
    window = int(kwargs.get("window", 30))
    top_k = int(kwargs.get("top_k", 5))

    raw = match_historical_patterns(
        fault_id=fault_id,
        variables=list(variables) if variables else None,
        window=window,
        top_k=top_k,
    )
    hits = [
        {
            "source": m["case_id"],
            "score": 1.0 / (1.0 + m["distance"]),  # invert distance → score
            "distance": m["distance"],
            "text": m["evidence_snippet"],
            "known_pattern": m["known_pattern"],
            "matched_range": m["matched_range"],
            "linked_notes": m["linked_notes"],
        }
        for m in raw.get("matches", [])
    ]
    return hits


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------
_LAYER_FNS = {
    "wiki": _retrieve_wiki,
    "field_feedback": _retrieve_field_feedback,
    "policy": _retrieve_policy,
    "pattern_memory": _retrieve_pattern_memory,
}

_VALID_LAYERS = set(_LAYER_FNS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def retrieve_evidence(layer: str, query: str, **kwargs) -> Dict[str, Any]:
    """Retrieve evidence from the specified layer.

    Parameters
    ----------
    layer  : one of "wiki", "field_feedback", "policy", "pattern_memory"
    query  : free-text query string
    **kwargs : layer-specific options (e.g. fault_id, top_k, max_results)

    Returns
    -------
    {
        "layer"        : str,
        "query"        : str,
        "hits"         : list[dict],
        "source_count" : int,
        "latency_ms"   : float,
        "error"        : str | None,
    }
    """
    if layer not in _VALID_LAYERS:
        return {
            "layer": layer,
            "query": query,
            "hits": [],
            "source_count": 0,
            "latency_ms": 0.0,
            "error": (
                f"Unknown layer '{layer}'. "
                f"Valid layers: {sorted(_VALID_LAYERS)}"
            ),
        }

    t0 = time.time()
    error: Optional[str] = None
    hits: List[Dict[str, Any]] = []

    try:
        hits = _LAYER_FNS[layer](query, **kwargs)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"

    return {
        "layer": layer,
        "query": query,
        "hits": hits,
        "source_count": len(hits),
        "latency_ms": round((time.time() - t0) * 1000, 1),
        "error": error,
    }
