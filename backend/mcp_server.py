"""Model Context Protocol (MCP) server for the TEP Live Copilot project.

Exposes the existing read-only tools — anomaly inspection, variable ranking,
hybrid wiki retrieval, similar-fault lookup, time-series case memory,
advisory-policy check — as MCP tools so any MCP client (Claude Desktop,
Cline, Cursor, OpenAI's MCP-enabled clients) can call them.

Why this exists alongside A2A:
  - A2A   = agent ↔ agent communication; `backend/a2a_router.py`.
  - MCP   = LLM host ↔ tool server; this file.
The same underlying tool functions back both surfaces; nothing here adds
new diagnostic capability — it just exposes the existing surface over
the MCP transport.

Run as a stdio server (Claude Desktop / Cline / Cursor spawn it themselves):

    python -m backend.mcp_server

Run as an SSE server for HTTP-based clients:

    python -m backend.mcp_server --transport sse

See docs/MCP_INTEGRATION.md for client-side configuration snippets.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Make sure `backend.*` imports resolve regardless of how this is launched
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv()

from mcp.server.fastmcp import FastMCP  # noqa: E402

logger = logging.getLogger("tep.mcp")

mcp = FastMCP(
    "tep-rca",
    instructions=(
        "Read-only Tennessee Eastman Process root-cause-analysis toolkit. "
        "Every tool here is advisory-only and inspection-only — none of "
        "them can change a setpoint, open or close a valve, or affect the "
        "running simulation. Use them in sequence to (1) inspect an anomaly "
        "snapshot, (2) rank the most-affected process variables, (3) search "
        "the governed wiki / prior RCAs / time-series memory for evidence, "
        "(4) draft an advisory, (5) policy-check the draft before showing "
        "it to an operator. The `diagnose_with_langgraph` tool runs the "
        "whole pipeline as a single bounded state-machine call."
    ),
)


# ---------------------------------------------------------------------------
# 6 deterministic read-only tools
# ---------------------------------------------------------------------------
@mcp.tool()
def inspect_anomaly_snapshot(fault_id: str = "fault1") -> Dict[str, Any]:
    """Read the anomaly snapshot for a given TEP fault id.

    Returns the T² statistic, threshold, row index, fault id, and a short
    description of the fault scenario. Pure read-only — does not run any
    simulation.

    Parameters:
        fault_id: TEP fault identifier (e.g. "fault1", "fault4", "fault6").
                  Valid range: fault0..fault20.
    """
    from backend.agent_tools.anomaly_tools import inspect_anomaly_snapshot as _impl
    return _impl(fault_id)


@mcp.tool()
def rank_contributing_variables(fault_id: str = "fault1", top_k: int = 5) -> Dict[str, Any]:
    """Rank process variables by how much they contribute to the T² statistic.

    Returns the top-k variables with tag (XMV/XMEAS), label, kind
    (manipulated/measurement), T² contribution, percent change vs baseline,
    and direction (increasing/decreasing).

    Parameters:
        fault_id: TEP fault identifier.
        top_k: Number of variables to return (default 5).
    """
    from backend.agent_tools.anomaly_tools import rank_contributing_variables as _impl
    return _impl(fault_id, top_k=top_k)


@mcp.tool()
def get_sensor_window(
    fault_id: str = "fault1",
    variable: str = "Reactor Pressure",
    window: int = 30,
) -> Dict[str, Any]:
    """Return a raw-data window for one process variable from the saved fault CSV.

    Useful for "show me the trajectory" inspection — does not classify.

    Parameters:
        fault_id: TEP fault identifier.
        variable: One of the 52 process-variable column names
                  (e.g. "Reactor Pressure", "A Feed", "Recycle Flow").
        window: Number of rows to return (from the start of the fault).
    """
    from backend.agent_tools.anomaly_tools import _load_fault_csv  # noqa: WPS433
    df, _csv_path = _load_fault_csv(fault_id)  # returns (DataFrame, Path)
    if variable not in df.columns:
        return {"error": f"variable '{variable}' not in fault CSV columns",
                "available_columns_sample": list(df.columns)[:20]}
    series = df[variable].head(window).tolist()
    return {
        "fault_id": fault_id,
        "variable": variable,
        "window": window,
        "values": series,
        "n_returned": len(series),
    }


@mcp.tool()
def search_process_knowledge(query: str, max_results: int = 4) -> Dict[str, Any]:
    """Keyword search over the governed TEP knowledge base (markdown).

    Returns source-cited excerpts. The corpus includes Downs & Vogel 1993,
    McAvoy 2003, and the project's own TEP technical references.

    Parameters:
        query: Natural-language search string.
        max_results: Maximum number of excerpts to return.
    """
    from backend.agent_tools.knowledge_tools import search_process_knowledge as _impl
    return _impl(query, max_results=max_results)


@mcp.tool()
def find_similar_faults(signature: str, top_k: int = 3) -> Dict[str, Any]:
    """Match a fault signature against the canonical Downs & Vogel IDV catalog
    and prior RCA notes.

    Returns the top-k matches with fault_id, fault_family, similarity score,
    short evidence text, and source citation.

    Parameters:
        signature: Free-text description of the observed fault signature
                   (e.g. "reactor cooling water step disturbance").
        top_k: Maximum matches to return.
    """
    from backend.agent_tools.history_tools import find_similar_faults as _impl
    return _impl(signature, top_k=top_k)


@mcp.tool()
def check_advisory_policy(candidate_answer: str) -> Dict[str, Any]:
    """Inspect a candidate operator-advisory for control-style language or overclaims.

    Returns `is_advisory_safe` (bool), forbidden_phrases_found, overclaims_found,
    suggestions (rewrite hints), and a notes string. Call this on EVERY draft
    advisory before showing it to a human.

    Parameters:
        candidate_answer: The advisory text to check.
    """
    from backend.agent_tools.policy_tools import check_advisory_policy as _impl
    return _impl(candidate_answer)


# ---------------------------------------------------------------------------
# 4 evidence-layer wrappers (the unified 4-layer router from the LangGraph
# orchestrator, surfaced as individual MCP tools for clients that want
# fine-grained access)
# ---------------------------------------------------------------------------
@mcp.tool()
def retrieve_wiki(query: str, max_results: int = 4, substrate: str = "hybrid") -> Dict[str, Any]:
    """Governed wiki retrieval — hybrid by default (NIM dense + BM25 + RRF).

    Returns the canonical evidence envelope: {layer, query, hits, source_count,
    latency_ms, error}. Override `substrate` to "keyword", "dense", or
    "sparse" to compare retrieval methods.

    Parameters:
        query: Natural-language query.
        max_results: Top-k hits.
        substrate: "hybrid" (default) | "keyword" | "dense" | "sparse".
    """
    from backend.agent_tools.evidence_router import retrieve_evidence
    return retrieve_evidence("wiki", query, max_results=max_results, substrate=substrate)


@mcp.tool()
def retrieve_field_feedback(query: str, top_k: int = 3) -> Dict[str, Any]:
    """Field-feedback retrieval — searches prior RCA investigation notes
    and the canonical IDV catalog by keyword.

    Returns the canonical evidence envelope.
    """
    from backend.agent_tools.evidence_router import retrieve_evidence
    return retrieve_evidence("field_feedback", query, top_k=top_k)


@mcp.tool()
def retrieve_policy_catalog(query: str) -> Dict[str, Any]:
    """Policy / constraint catalog — returns the regex patterns that the
    advisory-policy check uses (forbidden control verbs, overclaim phrases,
    suggested rewrites).

    Useful for understanding what wording WILL be blocked before you draft
    an advisory.
    """
    from backend.agent_tools.evidence_router import retrieve_evidence
    return retrieve_evidence("policy", query)


@mcp.tool()
def retrieve_pattern_memory(
    fault_id: str = "fault1",
    variables: Optional[List[str]] = None,
    window: int = 30,
    top_k: int = 5,
) -> Dict[str, Any]:
    """Time-series case memory — Matrix Profile analog retrieval.

    Returns the top-k historical fault windows most similar to the current
    `fault_id`'s opening trajectory. Honestly reports "no strong analog"
    when the closest match is still distant.

    Parameters:
        fault_id: Query fault id.
        variables: Subset of process variables to use for the query
                   (default: all 52 columns).
        window: Length of the query window in rows.
        top_k: Number of historical matches to return.
    """
    from backend.agent_tools.evidence_router import retrieve_evidence
    return retrieve_evidence(
        "pattern_memory",
        "",  # query string unused for this layer
        fault_id=fault_id,
        variables=variables,
        window=window,
        top_k=top_k,
    )


# ---------------------------------------------------------------------------
# High-level: run the LangGraph orchestrator end-to-end
# ---------------------------------------------------------------------------
@mcp.tool()
def diagnose_with_langgraph(
    fault_id: str = "fault1",
    question: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the 5-node LangGraph multi-evidence RCA orchestrator end-to-end.

    Pipeline: Signal → Evidence → Hypothesis → Evaluator → Human Review.
    Returns the final state: anomaly_snapshot, ranked_variables,
    evidence_by_layer, hypotheses, draft/final advisory, evaluation
    (policy_pass + grounded_ratio), revision_count, hitl_required,
    audit_trail.

    This is a single high-level tool for clients that don't want to drive
    each step individually. Costs one or more NIM LLM calls.

    Parameters:
        fault_id: TEP fault identifier.
        question: Optional override for the diagnosis prompt; defaults to
                  a generic "Diagnose the current TEP anomaly" prompt.
    """
    from backend.langgraph_rca import run_langgraph
    return run_langgraph(
        fault_id=fault_id,
        question=question or (
            "Diagnose the current TEP process anomaly. "
            "Identify the most likely root cause and the contributing variables."
        ),
    )


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="MCP server for TEP RCA tools (read-only)",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default="stdio",
        help="MCP transport. stdio is what Claude Desktop / Cline / Cursor use; "
             "sse / streamable-http for HTTP clients (mount path /sse or /).",
    )
    args = parser.parse_args()
    logger.info("starting tep-rca MCP server (transport=%s)", args.transport)
    mcp.run(args.transport)


if __name__ == "__main__":
    main()
