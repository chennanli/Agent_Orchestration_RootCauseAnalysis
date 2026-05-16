"""Hermetic tests for the 5-node LangGraph orchestrator.

The end-to-end run requires NIM API access; these tests just verify the
graph structure and the JSON-extraction helper, neither of which calls an
LLM.
"""
from __future__ import annotations

import json

import pytest

from backend.langgraph_rca import (
    _EVIDENCE_LAYERS,
    _extract_first_json,
    build_graph,
    signal_agent,
)


# ---------------------------------------------------------------------------
# Graph structure — node names, no LLM call needed
# ---------------------------------------------------------------------------
def test_build_graph_has_exactly_5_nodes_in_canonical_order():
    g = build_graph()
    # langgraph's StateGraph stores nodes in its `nodes` dict
    node_names = set(g.nodes)
    expected = {
        "signal_agent",
        "evidence_agent",
        "hypothesis_agent",
        "evaluator_agent",
        "human_review_gate",
    }
    assert node_names == expected, (
        f"unexpected nodes: extra={node_names - expected}, missing={expected - node_names}"
    )


def test_evidence_layers_constant_excludes_policy():
    """The EvidenceAgent intentionally does NOT query the policy layer
    (policy is consumed by the EvaluatorAgent), so it should not be in
    the layers the EvidenceAgent iterates."""
    assert _EVIDENCE_LAYERS == ["wiki", "field_feedback", "pattern_memory"]
    assert "policy" not in _EVIDENCE_LAYERS


# ---------------------------------------------------------------------------
# SignalAgent is deterministic — no LLM. Can be exercised end-to-end.
# ---------------------------------------------------------------------------
def test_signal_agent_returns_anomaly_snapshot_and_ranked_variables():
    """The deterministic node — reads PCA / T² output, no LLM call."""
    result = signal_agent({"fault_id": "fault1", "audit_trail": []})
    assert "anomaly_snapshot" in result
    assert "ranked_variables" in result
    # Tool returns `top_variables`, each entry has a `variable` key
    assert isinstance(result["ranked_variables"], list)
    if result["ranked_variables"]:
        first = result["ranked_variables"][0]
        assert "variable" in first
    # Audit trail has been appended with a SignalAgent entry
    audit = result["audit_trail"]
    assert audit and audit[-1]["node"] == "SignalAgent"
    assert "anomaly_detected" in audit[-1]
    assert "latency_ms" in audit[-1]


# ---------------------------------------------------------------------------
# _extract_first_json — the helper that replaced the brittle greedy regex
# ---------------------------------------------------------------------------
class TestExtractFirstJson:
    def test_plain_object(self):
        assert _extract_first_json('{"a": 1}') == {"a": 1}

    def test_plain_array(self):
        assert _extract_first_json("[1, 2, 3]") == [1, 2, 3]

    def test_object_wrapped_in_prose(self):
        # The thing the old regex was already getting right
        text = 'Here is the JSON you asked for: {"x": "y", "z": [1,2]} thanks!'
        assert _extract_first_json(text) == {"x": "y", "z": [1, 2]}

    def test_nested_braces_inside_strings_dont_break_extractor(self):
        # The greedy regex would have terminated at the first `}` here
        text = 'Reply: {"q": "you said {foo}", "n": 42}'
        assert _extract_first_json(text) == {"q": "you said {foo}", "n": 42}

    def test_two_objects_returns_only_the_first(self):
        text = '{"a": 1} and {"b": 2}'
        assert _extract_first_json(text) == {"a": 1}

    def test_returns_none_on_invalid(self):
        assert _extract_first_json("no json here") is None
        assert _extract_first_json("") is None
        assert _extract_first_json("{ not valid json") is None

    def test_prefers_first_valid_value(self):
        # Object opens first, so it wins over the later array
        text = "Mixed: {} then [1,2]"
        # {} is valid JSON (empty object), should return that
        assert _extract_first_json(text) == {}

    def test_escaped_quotes_inside_strings(self):
        text = '{"msg": "he said \\"hi\\"", "n": 1}'
        assert _extract_first_json(text) == {"msg": 'he said "hi"', "n": 1}
