"""Hermetic tests for the MCP server surface.

Verifies that the 11 tools (6 deterministic + 4 evidence wrappers + 1
LangGraph) are all registered with sane JSON schemas, and that invoking
a deterministic tool through the MCP machinery returns the expected
structured payload.

No NIM, no chromadb, no network — these run offline.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from backend.mcp_server import mcp


# ---------------------------------------------------------------------------
# Tool registry — every advertised tool is present + has a usable schema
# ---------------------------------------------------------------------------
EXPECTED_TOOLS = {
    # 6 deterministic read-only tools
    "inspect_anomaly_snapshot",
    "rank_contributing_variables",
    "get_sensor_window",
    "search_process_knowledge",
    "find_similar_faults",
    "check_advisory_policy",
    # 4 evidence-router wrappers
    "retrieve_wiki",
    "retrieve_field_feedback",
    "retrieve_policy_catalog",
    "retrieve_pattern_memory",
    # 1 high-level orchestrator
    "diagnose_with_langgraph",
}


def test_mcp_server_advertises_exactly_the_documented_tools():
    """If a tool is renamed or removed, this fails — the README + the
    MCP_INTEGRATION.md doc both name these explicitly."""
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == EXPECTED_TOOLS, (
        f"tool registry drift — extra={names - EXPECTED_TOOLS}, "
        f"missing={EXPECTED_TOOLS - names}"
    )


def test_every_tool_has_a_non_empty_description():
    """MCP clients show the description in their tool picker. An empty
    description means the docstring went missing."""
    tools = asyncio.run(mcp.list_tools())
    for t in tools:
        assert t.description, f"tool {t.name} has empty description"


def test_every_tool_has_a_valid_input_schema():
    """The decorator should derive a JSON schema from the function
    signature. We just assert the schema has the expected top-level
    shape — `type: object` with `properties`."""
    tools = asyncio.run(mcp.list_tools())
    for t in tools:
        schema = t.inputSchema
        assert isinstance(schema, dict), f"{t.name}: schema not a dict"
        assert schema.get("type") == "object", f"{t.name}: schema type != object"
        assert "properties" in schema, f"{t.name}: schema lacks 'properties'"


def test_inspect_anomaly_snapshot_tool_advertises_fault_id_parameter():
    tools = asyncio.run(mcp.list_tools())
    t = next(t for t in tools if t.name == "inspect_anomaly_snapshot")
    assert "fault_id" in t.inputSchema["properties"]
    assert t.inputSchema["properties"]["fault_id"]["type"] == "string"
    assert t.inputSchema["properties"]["fault_id"].get("default") == "fault1"


def test_retrieve_pattern_memory_advertises_optional_variables_list():
    tools = asyncio.run(mcp.list_tools())
    t = next(t for t in tools if t.name == "retrieve_pattern_memory")
    props = t.inputSchema["properties"]
    assert "fault_id" in props and "variables" in props
    assert "top_k" in props and "window" in props


# ---------------------------------------------------------------------------
# Invocation — call a deterministic tool through the MCP machinery
# ---------------------------------------------------------------------------
def test_call_check_advisory_policy_blocks_control_verb():
    """`check_advisory_policy` is fully deterministic — call it through
    the MCP server and verify it correctly flags a control-style verb."""
    result = asyncio.run(
        mcp.call_tool(
            "check_advisory_policy",
            {"candidate_answer": "Operator should open the cooling water valve immediately."},
        )
    )
    # FastMCP.call_tool returns a (content_list, structured_content) tuple
    content_list, structured = result
    assert content_list, "no content returned"
    text = content_list[0].text  # JSON-encoded result
    parsed = json.loads(text)
    assert parsed["is_advisory_safe"] is False, (
        "policy check should flag 'open the valve'"
    )
    assert parsed["forbidden_phrases_found"], (
        "expected at least one forbidden phrase match"
    )


def test_call_check_advisory_policy_passes_safe_advisory():
    safe_text = (
        "PCA T² statistic indicates an anomaly in the reactor cooling "
        "system. Top contributing variables: A feed, D feed. SME review "
        "recommended before any operator action."
    )
    result = asyncio.run(
        mcp.call_tool("check_advisory_policy", {"candidate_answer": safe_text})
    )
    content_list, _ = result
    parsed = json.loads(content_list[0].text)
    assert parsed["is_advisory_safe"] is True
    assert not parsed["forbidden_phrases_found"]
    assert not parsed["overclaims_found"]


def test_call_get_sensor_window_returns_window_of_correct_length():
    result = asyncio.run(
        mcp.call_tool(
            "get_sensor_window",
            {"fault_id": "fault1", "variable": "A Feed", "window": 25},
        )
    )
    content_list, _ = result
    parsed = json.loads(content_list[0].text)
    assert parsed["fault_id"] == "fault1"
    assert parsed["variable"] == "A Feed"
    assert parsed["n_returned"] == 25
    assert len(parsed["values"]) == 25
    assert all(isinstance(v, (int, float)) for v in parsed["values"])


def test_call_get_sensor_window_rejects_unknown_variable():
    result = asyncio.run(
        mcp.call_tool(
            "get_sensor_window",
            {"fault_id": "fault1", "variable": "Imaginary Variable XYZ"},
        )
    )
    content_list, _ = result
    parsed = json.loads(content_list[0].text)
    assert "error" in parsed
    assert "available_columns_sample" in parsed
