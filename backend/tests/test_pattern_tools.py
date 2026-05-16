"""Hermetic tests for Matrix Profile time-series case memory.

These don't call NIM, don't depend on network, and don't require the full
21-fault archive — they assert the cross-fault-boundary masking, the
fallback path when stumpy isn't available, and the basic shape of the
returned dict.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from backend.agent_tools import pattern_tools


# ---------------------------------------------------------------------------
# Top-level smoke: real archive, real call, just verify shape
# ---------------------------------------------------------------------------
def test_match_historical_patterns_real_archive_returns_finite_distances():
    """End-to-end smoke against the real fault CSVs in the repo.

    Doesn't assert specific distances — those depend on stumpy vs numpy
    fallback. Asserts only structural invariants.
    """
    r = pattern_tools.match_historical_patterns(
        "fault1", variables=["Reactor Pressure", "A Feed"], top_k=3,
    )
    assert r["method"] in {"matrix_profile_ab_join", "fallback_normalized_l2"}
    assert isinstance(r["matches"], list)
    assert len(r["matches"]) == 3
    for m in r["matches"]:
        assert {"case_id", "matched_range", "distance",
                "known_pattern", "evidence_snippet"} <= set(m)
        assert math.isfinite(m["distance"])
        assert isinstance(m["matched_range"], list) and len(m["matched_range"]) == 2


# ---------------------------------------------------------------------------
# The bug we previously shipped + fixed: cross-fault boundary windows
# ---------------------------------------------------------------------------
def test_no_match_straddles_two_fault_files():
    """A match window [start:end] must be entirely within one fault file.

    Earlier code concatenated all fault CSVs into one archive without a
    boundary mask, so a top-1 like `fault0 [499:529]` could span into
    fault1's first 29 rows — bogus.
    """
    r = pattern_tools.match_historical_patterns(
        "fault1", variables=["Reactor Pressure"], top_k=5, window=30,
    )
    for m in r["matches"]:
        start, end = m["matched_range"]
        # Each fault CSV in the repo is 500 rows. The window must fit:
        assert end - start == 30, f"window length not preserved: {m}"
        assert start >= 0
        assert end <= 500, (
            f"match {m['case_id']} [{start}:{end}] straddles a fault boundary "
            f"(each CSV is 500 rows)"
        )


# ---------------------------------------------------------------------------
# Self-match exclusion: the query fault is never a top-K match against itself
# ---------------------------------------------------------------------------
def test_query_fault_excluded_from_matches():
    """If you query fault1, the top-K must not include fault1 itself."""
    r = pattern_tools.match_historical_patterns(
        "fault1", variables=["A Feed"], top_k=5,
    )
    case_ids = {m["case_id"] for m in r["matches"]}
    assert "fault1" not in case_ids, (
        f"self-match leaked into top-K: {case_ids}"
    )


# ---------------------------------------------------------------------------
# Interpretation heuristic — pure function, no I/O
# ---------------------------------------------------------------------------
def test_interpret_match_thresholds():
    interp = pattern_tools._interpret_match
    assert "Strong analog" in interp(0.5, 1000)         # < 1.5
    assert "Borderline" in interp(2.5, 1000)             # 1.5–3.5
    assert "No strong historical analog" in interp(5.0, 1000)  # > 3.5
    assert "No strong historical analog" in interp(float("inf"), 0)


# ---------------------------------------------------------------------------
# NumPy fallback distance — runs even if stumpy isn't available
# ---------------------------------------------------------------------------
def test_mass_distances_fallback_returns_correct_length(monkeypatch):
    """Force the numpy fallback path and verify the distance array length."""
    monkeypatch.setattr(pattern_tools, "_STUMPY_AVAILABLE", False)
    query = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    archive = np.random.RandomState(42).randn(50)
    dists = pattern_tools._mass_distances(query, archive)
    assert len(dists) == 50 - 5 + 1
    assert np.all(np.isfinite(dists))
