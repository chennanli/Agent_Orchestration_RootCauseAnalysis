"""Hermetic tests for the held-out grounding judge.

The judge calls a NIM model — we monkeypatch the LLM builder so these
run offline.
"""
from __future__ import annotations

import json
import types

import pytest

from backend.evaluation import judge


# ---------------------------------------------------------------------------
# Trivial-case shortcuts (no LLM call needed)
# ---------------------------------------------------------------------------
def test_empty_advisory_returns_zero_without_calling_llm():
    """Empty advisory short-circuits before any model is invoked."""
    r = judge.grade_grounding("", evidence_snippets=[], fault_id="fault1")
    assert r["grounded_ratio"] == 0.0
    assert r["supported_claims"] == 0
    assert r["unsupported_claims"] == 0
    assert r["judge_model"] == "none"


def test_whitespace_only_advisory_returns_zero():
    r = judge.grade_grounding("   \n\t  ", evidence_snippets=[], fault_id="fault1")
    assert r["grounded_ratio"] == 0.0
    assert r["judge_model"] == "none"


# ---------------------------------------------------------------------------
# Mock the LLM — verify the JSON parsing + clamping
# ---------------------------------------------------------------------------
class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    def __init__(self, content: str):
        self._content = content
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        return _FakeResponse(self._content)


def test_grade_grounding_parses_json_response(monkeypatch):
    fake = _FakeLLM(json.dumps({
        "supported_claims": 3,
        "unsupported_claims": 1,
        "grounded_ratio": 0.75,
        "note": "three claims have evidence backing, one is speculative"
    }))
    monkeypatch.setattr(judge, "_build_llm", lambda model: fake)
    r = judge.grade_grounding(
        "Reactor cooling water is dropping. PCA T² is high. SME review.",
        evidence_snippets=["[wiki] reactor cooling water IDV-4"],
        fault_id="fault4",
    )
    assert r["grounded_ratio"] == 0.75
    assert r["supported_claims"] == 3
    assert r["unsupported_claims"] == 1
    assert "three claims" in r["note"]
    assert r["judge_model"] in judge._JUDGE_MODELS_TO_TRY


def test_grade_grounding_clamps_ratio_into_valid_range(monkeypatch):
    """A misbehaving LLM that returns ratio > 1 or < 0 should get clamped."""
    fake = _FakeLLM(json.dumps({
        "supported_claims": 5,
        "unsupported_claims": 0,
        "grounded_ratio": 1.7,           # invalid
        "note": "all good"
    }))
    monkeypatch.setattr(judge, "_build_llm", lambda model: fake)
    r = judge.grade_grounding(
        "Something",
        evidence_snippets=["a"],
        fault_id="fault1",
    )
    assert 0.0 <= r["grounded_ratio"] <= 1.0


def test_grade_grounding_falls_back_when_llm_returns_garbage(monkeypatch):
    """If the LLM returns prose with no JSON, judge should try the next
    model in the fallback chain. Here all of them produce garbage."""
    garbage = _FakeLLM("I refuse to answer in JSON.")
    monkeypatch.setattr(judge, "_build_llm", lambda model: garbage)
    r = judge.grade_grounding(
        "Some advisory text.",
        evidence_snippets=["a"],
        fault_id="fault1",
    )
    # Falls all the way through to the safe default
    assert r["grounded_ratio"] == 0.0
    assert r["judge_model"] == "none"
    assert "failed" in r["note"].lower() or r["note"] == ""


def test_grade_grounding_tolerates_prose_around_json(monkeypatch):
    """The _extract_first_json helper should let the judge work even when
    the LLM wraps its answer in prose."""
    wrapped = _FakeLLM(
        'Here is my assessment as a strict judge:\n\n'
        '{"supported_claims": 2, "unsupported_claims": 2, '
        '"grounded_ratio": 0.5, "note": "half-half"}\n\n'
        'I hope this helps.'
    )
    monkeypatch.setattr(judge, "_build_llm", lambda model: wrapped)
    r = judge.grade_grounding("text", evidence_snippets=[], fault_id="fault1")
    assert r["grounded_ratio"] == 0.5
    assert r["supported_claims"] == 2
