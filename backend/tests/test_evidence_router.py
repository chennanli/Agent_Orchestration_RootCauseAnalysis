"""Hermetic tests for the 4-layer evidence router.

Each test isolates one layer with monkeypatch so no NIM / no chromadb / no
real index is needed.
"""
from __future__ import annotations

import pytest

from backend.agent_tools import evidence_router as er


# ---------------------------------------------------------------------------
# Envelope shape — every layer returns the same uniform envelope
# ---------------------------------------------------------------------------
def test_unknown_layer_returns_error_envelope_with_empty_hits():
    r = er.retrieve_evidence("bogus_layer_name", "anything")
    assert r["layer"] == "bogus_layer_name"
    assert r["hits"] == []
    assert r["source_count"] == 0
    assert "error" in r and r["error"]


@pytest.mark.parametrize("layer", ["wiki", "field_feedback", "policy", "pattern_memory"])
def test_each_known_layer_returns_canonical_envelope(layer, monkeypatch):
    """Each layer's hits are well-shaped; envelope keys are uniform."""
    # Stub each layer's underlying function so we don't hit real backends
    monkeypatch.setitem(er._LAYER_FNS, "wiki",            lambda q, **kw: [{"source": "x", "text": "y"}])
    monkeypatch.setitem(er._LAYER_FNS, "field_feedback",  lambda q, **kw: [{"source": "fault4", "score": 0.5, "text": "z"}])
    monkeypatch.setitem(er._LAYER_FNS, "policy",          lambda q, **kw: [{"type": "forbidden_control", "pattern": "r1"}])
    monkeypatch.setitem(er._LAYER_FNS, "pattern_memory",  lambda q, **kw: [{"source": "fault8", "score": 0.4}])
    r = er.retrieve_evidence(layer, "test query")
    assert r["layer"] == layer
    assert r["query"] == "test query"
    assert isinstance(r["hits"], list)
    assert r["source_count"] == len(r["hits"]) > 0
    assert r["error"] is None
    assert "latency_ms" in r


# ---------------------------------------------------------------------------
# Regression: field_feedback used to read `similar_faults` instead of `matches`
# ---------------------------------------------------------------------------
def test_field_feedback_reads_matches_key_not_similar_faults(monkeypatch):
    """`find_similar_faults` returns {"matches": [...]} — earlier code looked
    for the wrong key and silently returned 0 hits. This test guards the fix.
    """
    fake_return = {
        "signature": "rcw test",
        "matches": [
            {"fault_id": "fault14", "fault_family": "cooling water valve sticking",
             "score": 0.5, "evidence": "IDV(14)", "source": "Downs & Vogel"},
            {"fault_id": "fault4", "fault_family": "cooling water step",
             "score": 0.4, "evidence": "IDV(4)", "source": "Downs & Vogel"},
        ],
        "note": "two matches",
    }
    import backend.agent_tools.history_tools as ht
    monkeypatch.setattr(ht, "find_similar_faults", lambda q, top_k=3: fake_return)
    hits = er._retrieve_field_feedback("reactor cooling water")
    assert len(hits) == 2
    assert hits[0]["source"] == "fault14"
    assert hits[0]["fault_family"] == "cooling water valve sticking"
    assert hits[0]["score"] == 0.5


# ---------------------------------------------------------------------------
# vector_knowledge contract: dense_search returns [] (not error-as-hit)
# when embedding fails. This test guards the B5 fix.
# ---------------------------------------------------------------------------
def test_wiki_layer_falls_back_to_keyword_when_dense_returns_empty(monkeypatch):
    """If hybrid/dense/sparse returns [], the router falls back to keyword."""
    import backend.agent_tools.vector_knowledge as vk
    monkeypatch.setattr(vk, "build_or_load_index", lambda **kw: {"status": "loaded"})
    monkeypatch.setattr(vk, "hybrid_search", lambda q, k=5: [])
    monkeypatch.setattr(vk, "keyword_search", lambda q, k=5: [
        {"source": "x.md", "text": "fallback hit", "score": 1.0}
    ])
    hits = er._retrieve_wiki("anything", max_results=3)
    assert len(hits) == 1
    assert hits[0]["text"] == "fallback hit"
