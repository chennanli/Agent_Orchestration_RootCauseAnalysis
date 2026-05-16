"""Multi-Agent RCA Orchestrator — LangGraph 5-node state machine.

Architecture (single file for MVP):

  SignalAgent  →  EvidenceAgent  →  HypothesisAgent
                                           ↓
                                    EvaluatorAgent
                                           ↓
                                   HumanReviewGate ──(acceptable)──► END (final_advisory)
                                           │
                                   (not acceptable & revisions < 3)
                                           │
                                           └──────────────────────► HypothesisAgent (loop)
                                   (not acceptable & revisions ≥ 3)
                                           │
                                           └──────────────────────► END (hitl_required=True)

CLI usage:
  python backend/langgraph_rca.py --fault fault1 \\
    --question "Diagnose the current TEP anomaly."
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
# ---------------------------------------------------------------------------
# Env
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv()

# ---------------------------------------------------------------------------
# LangGraph
# ---------------------------------------------------------------------------
from typing_extensions import TypedDict  # noqa: E402
from langgraph.graph import StateGraph, END  # noqa: E402
from langgraph.checkpoint.sqlite import SqliteSaver  # noqa: E402

# ---------------------------------------------------------------------------
# LLM wiring: try langchain_nvidia_ai_endpoints first, then generic init
# ---------------------------------------------------------------------------
def _build_llm():
    """Return a LangChain chat model backed by NVIDIA NIM."""
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA  # noqa: WPS433
        return ChatNVIDIA(
            model="meta/llama-3.3-70b-instruct",
            api_key=api_key,
            temperature=0.2,
            max_tokens=1024,
        )
    except Exception:
        from langchain.chat_models import init_chat_model  # noqa: WPS433
        return init_chat_model(
            model="meta/llama-3.3-70b-instruct",
            model_provider="openai",  # NIM is OpenAI-compatible
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
            temperature=0.2,
            max_tokens=1024,
        )


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
class RCAState(TypedDict, total=False):
    fault_id: str
    question: str
    anomaly_snapshot: dict
    ranked_variables: list
    evidence_by_layer: dict          # {"wiki":[...], "field_feedback":[...], "pattern_memory":[...]}
    hypotheses: list
    draft_advisory: str
    evaluation: dict
    revision_count: int
    final_advisory: str
    hitl_required: bool
    audit_trail: list                # append-only per-node log
    error: Optional[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _append_audit(state: RCAState, node: str, data: dict) -> list:
    trail = list(state.get("audit_trail") or [])
    trail.append({"node": node, "ts": datetime.now(timezone.utc).isoformat(), **data})
    return trail


def _safe_invoke(llm, messages: list) -> str:
    """Invoke LLM and return content string; raise on failure."""
    response = llm.invoke(messages)
    return response.content if hasattr(response, "content") else str(response)


def _extract_first_json(text: str) -> Optional[Any]:
    """Find and parse the first top-level JSON value in `text`.

    Earlier code used `re.search(r'\\{.*\\}', text, re.DOTALL)` which is greedy
    and silently spans multiple JSON objects, or fails on prose that contains
    a `}` after the actual JSON. This walks the string and uses balanced-brace
    counting (tracking string literals + escapes) so it returns the FIRST
    syntactically complete JSON value. Returns None if no parseable value is
    found. Supports both object and array top-level values.
    """
    if not text:
        return None
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        while start != -1:
            depth = 0
            in_str = False
            escape = False
            for i in range(start, len(text)):
                ch = text[i]
                if in_str:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == '"':
                        in_str = False
                else:
                    if ch == '"':
                        in_str = True
                    elif ch == opener:
                        depth += 1
                    elif ch == closer:
                        depth -= 1
                        if depth == 0:
                            try:
                                return json.loads(text[start: i + 1])
                            except Exception:
                                break  # malformed; try next opener
            start = text.find(opener, start + 1)
    return None


# ---------------------------------------------------------------------------
# Node 1 — SignalAgent (no LLM)
# ---------------------------------------------------------------------------
def signal_agent(state: RCAState) -> dict:
    """Calls inspect_anomaly_snapshot + rank_contributing_variables.
    No LLM. Writes anomaly_snapshot and ranked_variables to state."""
    from backend.agent_tools.anomaly_tools import (
        inspect_anomaly_snapshot,
        rank_contributing_variables,
    )
    fault_id = state.get("fault_id", "fault1")
    t0 = time.time()

    snapshot = inspect_anomaly_snapshot(fault_id)
    ranked = rank_contributing_variables(fault_id, top_k=8)

    # NOTE: the tool's actual key is `top_variables` (not `top_contributors`).
    # Each item is a dict with: variable, tag, label, kind, t2_contribution,
    # mean_change_pct, direction.
    top_vars_list = ranked.get("top_variables") or []

    audit = _append_audit(state, "SignalAgent", {
        "anomaly_detected": snapshot.get("anomaly_detected"),
        "top_vars": [v.get("variable") for v in top_vars_list[:3]],
        "latency_ms": round((time.time() - t0) * 1000),
    })

    return {
        "anomaly_snapshot": snapshot,
        "ranked_variables": top_vars_list,
        "audit_trail": audit,
    }


# ---------------------------------------------------------------------------
# Node 2 — EvidenceAgent (LLM-driven)
# ---------------------------------------------------------------------------
_EVIDENCE_LAYERS = ["wiki", "field_feedback", "pattern_memory"]
_MAX_RETRIEVAL_CALLS = 6


def evidence_agent(state: RCAState) -> dict:
    """LLM decides which evidence layers to query and with what terms.
    Hard cap: 6 retrieval calls. Skips `policy` (used by Evaluator)."""
    from backend.agent_tools.evidence_router import retrieve_evidence

    fault_id = state.get("fault_id", "fault1")
    question = state.get("question", "Diagnose the anomaly.")
    snapshot = state.get("anomaly_snapshot", {})
    top_vars = [v.get("variable", "") for v in (state.get("ranked_variables") or [])[:5]]

    t0 = time.time()

    # Ask LLM to plan evidence queries
    plan_prompt = f"""You are an Evidence Router agent. Your job is to decide which evidence layers to query.

FAULT: {fault_id}
QUESTION: {question}
TOP ANOMALOUS VARIABLES: {top_vars}

Available layers:
- wiki: Governed TEP process knowledge base
- field_feedback: Prior RCA investigation notes
- pattern_memory: Time-series historical analog matching (requires fault_id)

Respond with a JSON array of up to 6 query objects. Each: {{"layer": "...", "query": "..."}}
Only include layers that are genuinely useful. Respond with ONLY valid JSON array."""

    evidence_by_layer: Dict[str, list] = {L: [] for L in _EVIDENCE_LAYERS}
    calls_used = 0
    llm_plan_used = False
    plan_parse_error: Optional[str] = None  # surfaced in audit_trail below

    try:
        llm = _build_llm()
        plan_text = _safe_invoke(llm, [{"role": "user", "content": plan_prompt}])
        # Balanced-brace extractor — robust to LLM output that wraps the JSON
        # in prose (the greedy `re.search` we used before could span multiple
        # objects or fail on a trailing `]` in the explanation).
        parsed = _extract_first_json(plan_text)
        if isinstance(parsed, list):
            plan = parsed
        else:
            raise ValueError("LLM plan response did not contain a JSON array")
        llm_plan_used = True
    except Exception as exc:
        # Capture WHY the LLM plan was discarded so the audit trail shows it
        # — earlier drafts swallowed this silently, and a malformed plan would
        # look identical to a successful "all-3-layers" fallback.
        plan_parse_error = f"{type(exc).__name__}: {str(exc)[:160]}"
        # Fallback plan: query all 3 layers with the question
        plan = [
            {"layer": "wiki", "query": question},
            {"layer": "field_feedback", "query": f"{fault_id} {question}"},
            {"layer": "pattern_memory", "query": question},
        ]

    # Execute the plan (respect hard cap)
    for item in plan:
        if calls_used >= _MAX_RETRIEVAL_CALLS:
            break
        layer = item.get("layer", "")
        query = item.get("query", question)
        if layer not in _EVIDENCE_LAYERS:
            continue
        kwargs: Dict[str, Any] = {}
        if layer == "pattern_memory":
            kwargs["fault_id"] = fault_id
        result = retrieve_evidence(layer, query, **kwargs)
        if result.get("error"):
            continue
        evidence_by_layer[layer].extend(result.get("hits", []))
        calls_used += 1

    audit = _append_audit(state, "EvidenceAgent", {
        "calls_used": calls_used,
        "llm_plan_used": llm_plan_used,
        "plan_parse_error": plan_parse_error,   # None on success
        "layers_hit": [L for L, hits in evidence_by_layer.items() if hits],
        "total_hits": sum(len(v) for v in evidence_by_layer.values()),
        "latency_ms": round((time.time() - t0) * 1000),
    })

    return {
        "evidence_by_layer": evidence_by_layer,
        "audit_trail": audit,
    }


# ---------------------------------------------------------------------------
# Node 3 — HypothesisAgent (LLM)
# ---------------------------------------------------------------------------
def hypothesis_agent(state: RCAState) -> dict:
    """Single LLM call. Reads full state, writes 1-3 ranked hypotheses."""
    fault_id = state.get("fault_id", "fault1")
    question = state.get("question", "Diagnose the anomaly.")
    snapshot = state.get("anomaly_snapshot", {})
    top_vars = state.get("ranked_variables", [])[:5]
    evidence = state.get("evidence_by_layer", {})
    revision = state.get("revision_count", 0)
    prev_feedback = (state.get("evaluation") or {}).get("feedback", "")

    # Summarise evidence compactly
    ev_lines: list[str] = []
    for layer, hits in evidence.items():
        for h in hits[:2]:
            snippet = h.get("text", str(h))[:200]
            ev_lines.append(f"[{layer}] {snippet}")

    ev_summary = "\n".join(ev_lines) or "No evidence retrieved."

    revision_note = ""
    if revision > 0 and prev_feedback:
        revision_note = f"\n\nPrevious evaluation feedback (revision {revision}): {prev_feedback}\nPlease address these issues."

    prompt = f"""You are a Root-Cause Hypothesis agent for the Tennessee Eastman Process.

FAULT: {fault_id}
QUESTION: {question}

TOP ANOMALOUS VARIABLES:
{json.dumps(top_vars[:5], indent=2)}

EVIDENCE:
{ev_summary}
{revision_note}

Write 1-3 ranked root-cause hypotheses. For each hypothesis:
- rank (1=most likely)
- statement (one concise sentence)
- supporting_evidence_ids (list of layer names used)
- confidence (high/medium/low)

Also write a short draft_advisory (2-4 sentences, advisory-only, no control commands).

Respond with JSON:
{{
  "hypotheses": [
    {{"rank": 1, "statement": "...", "supporting_evidence_ids": [...], "confidence": "..."}}
  ],
  "draft_advisory": "..."
}}"""

    t0 = time.time()
    hypotheses = []
    draft_advisory = ""
    error = None

    try:
        llm = _build_llm()
        resp = _safe_invoke(llm, [{"role": "user", "content": prompt}])
        parsed = _extract_first_json(resp)
        if isinstance(parsed, dict):
            hypotheses = parsed.get("hypotheses", [])
            draft_advisory = parsed.get("draft_advisory", "")
        else:
            raise ValueError("LLM hypothesis response did not contain a JSON object")
    except Exception as exc:
        error = f"HypothesisAgent LLM error: {exc}"
        draft_advisory = (
            f"Signal analysis detected anomaly in {fault_id}. "
            "Top contributing variables indicate a process disturbance. "
            "SME review recommended before any action."
        )
        hypotheses = [{"rank": 1, "statement": draft_advisory,
                       "supporting_evidence_ids": [], "confidence": "low"}]

    audit = _append_audit(state, "HypothesisAgent", {
        "revision": revision,
        "hypothesis_count": len(hypotheses),
        "latency_ms": round((time.time() - t0) * 1000),
        "error": error,
    })

    updates: dict = {
        "hypotheses": hypotheses,
        "draft_advisory": draft_advisory,
        "audit_trail": audit,
    }
    if error:
        updates["error"] = error
    return updates


# ---------------------------------------------------------------------------
# Node 4 — EvaluatorAgent (composite check)
# ---------------------------------------------------------------------------
def evaluator_agent(state: RCAState) -> dict:
    """Critic + Compliance + Grounding check rolled into one MVP node."""
    from backend.agent_tools.policy_tools import check_advisory_policy

    draft = state.get("draft_advisory", "")
    hypotheses = state.get("hypotheses", [])
    evidence = state.get("evidence_by_layer", {})

    t0 = time.time()

    # --- Policy check (deterministic) ---
    policy_result = check_advisory_policy(draft)

    # --- Grounding self-critique (LLM) ---
    grounded_ratio = 0.5  # default if LLM fails
    citation_coverage = 0.0
    llm_critique_used = False

    ev_summary = "; ".join(
        f"{L}:{len(hits)} hits"
        for L, hits in evidence.items() if hits
    ) or "no evidence"

    critique_prompt = f"""You are an Evidence Grounding critic.

DRAFT ADVISORY: {draft}

HYPOTHESES: {json.dumps(hypotheses[:2], indent=2)}

EVIDENCE AVAILABLE: {ev_summary}

For each factual claim in the draft advisory, determine if it is grounded
in the evidence listed. Count: grounded_claims / total_claims.

Respond with JSON only:
{{"grounded_ratio": 0.0-1.0, "citation_coverage": 0.0-1.0, "critique": "brief note"}}"""

    try:
        llm = _build_llm()
        resp = _safe_invoke(llm, [{"role": "user", "content": critique_prompt}])
        cr = _extract_first_json(resp)
        if isinstance(cr, dict):
            grounded_ratio = float(cr.get("grounded_ratio", 0.5))
            citation_coverage = float(cr.get("citation_coverage", 0.0))
            llm_critique_used = True
    except Exception:
        pass

    # --- Composite acceptable decision ---
    policy_ok = bool(policy_result.get("is_advisory_safe", True))
    grounding_ok = grounded_ratio >= 0.4
    acceptable = policy_ok and grounding_ok

    feedback_parts: list[str] = []
    if not policy_ok:
        found = policy_result.get("forbidden_phrases_found", []) + \
                policy_result.get("overclaims_found", [])
        feedback_parts.append(f"Policy violation: {found[:3]}")
    if not grounding_ok:
        feedback_parts.append(
            f"Low grounding ratio ({grounded_ratio:.0%}). "
            "Add more evidence citations to hypotheses."
        )
    feedback = " | ".join(feedback_parts) if feedback_parts else "Advisory looks good."

    evaluation = {
        "policy": {
            "is_advisory_safe": policy_ok,
            "forbidden_phrases": policy_result.get("forbidden_phrases_found", []),
            "overclaims": policy_result.get("overclaims_found", []),
        },
        "grounded_ratio": round(grounded_ratio, 3),
        "citation_coverage": round(citation_coverage, 3),
        "acceptable": acceptable,
        "feedback": feedback,
        "llm_critique_used": llm_critique_used,
    }

    audit = _append_audit(state, "EvaluatorAgent", {
        "acceptable": acceptable,
        "policy_ok": policy_ok,
        "grounded_ratio": grounded_ratio,
        "llm_critique_used": llm_critique_used,
        "latency_ms": round((time.time() - t0) * 1000),
    })

    return {
        "evaluation": evaluation,
        "audit_trail": audit,
    }


# ---------------------------------------------------------------------------
# Node 5 — HumanReviewGate (router / terminal)
# ---------------------------------------------------------------------------
def human_review_gate(state: RCAState) -> dict:
    """If evaluation.acceptable → write final_advisory and END.
    Else if revision_count < 3 → loop back to HypothesisAgent.
    Else → set hitl_required = True and END."""
    evaluation = state.get("evaluation", {})
    acceptable = evaluation.get("acceptable", False)
    revision_count = int(state.get("revision_count") or 0)

    audit = _append_audit(state, "HumanReviewGate", {
        "acceptable": acceptable,
        "revision_count": revision_count,
        "decision": "accept" if acceptable else (
            "loop_back" if revision_count < 3 else "hitl_required"
        ),
    })

    if acceptable:
        return {
            "final_advisory": state.get("draft_advisory", ""),
            "hitl_required": False,
            "audit_trail": audit,
        }

    if revision_count < 3:
        return {
            "revision_count": revision_count + 1,
            "audit_trail": audit,
        }

    return {
        "hitl_required": True,
        "final_advisory": state.get("draft_advisory", ""),
        "audit_trail": audit,
    }


def _route_after_gate(state: RCAState) -> str:
    """Conditional edge: loop back to hypothesis or end."""
    if state.get("hitl_required"):
        return END
    if state.get("final_advisory"):
        return END
    return "hypothesis_agent"


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------
def build_graph():
    graph = StateGraph(RCAState)

    graph.add_node("signal_agent", signal_agent)
    graph.add_node("evidence_agent", evidence_agent)
    graph.add_node("hypothesis_agent", hypothesis_agent)
    graph.add_node("evaluator_agent", evaluator_agent)
    graph.add_node("human_review_gate", human_review_gate)

    graph.set_entry_point("signal_agent")
    graph.add_edge("signal_agent", "evidence_agent")
    graph.add_edge("evidence_agent", "hypothesis_agent")
    graph.add_edge("hypothesis_agent", "evaluator_agent")
    graph.add_edge("evaluator_agent", "human_review_gate")
    graph.add_conditional_edges(
        "human_review_gate",
        _route_after_gate,
        {END: END, "hypothesis_agent": "hypothesis_agent"},
    )

    return graph


# ---------------------------------------------------------------------------
# Run functions
# ---------------------------------------------------------------------------
def _persist_run(final: dict, fault_id: str) -> Path:
    """Save run JSON to disk for replay / debugging."""
    _OUT_DIR = _ROOT / "backend" / "diagnostics" / "multi_agent_runs"
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = _OUT_DIR / f"lg_run_{fault_id}_{ts}.json"
    try:
        with open(out_path, "w") as f:
            json.dump(final, f, indent=2, default=str)
    except Exception:
        pass
    return out_path


def run_langgraph(
    fault_id: str,
    question: str,
    thread_id: Optional[str] = None,
    on_node: Optional[Callable[[str, dict], None]] = None,
) -> Dict[str, Any]:
    """Run the 5-node LangGraph and return the final state dict.

    Parameters
    ----------
    on_node : optional callback called after each node updates state, with
        (node_name, accumulated_state_so_far). Used by the SSE API in
        backend.langgraph_api to stream per-node progress to the UI.
    """
    _OUT_DIR = _ROOT / "backend" / "diagnostics" / "multi_agent_runs"
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    _DB_PATH = _OUT_DIR / "checkpoint.sqlite"

    t_start = time.time()

    with SqliteSaver.from_conn_string(str(_DB_PATH)) as checkpointer:
        graph = build_graph()
        app = graph.compile(checkpointer=checkpointer)

        tid = thread_id or f"{fault_id}_{int(t_start)}"
        config = {"configurable": {"thread_id": tid}}
        initial_state: RCAState = {
            "fault_id": fault_id,
            "question": question,
            "revision_count": 0,
            "audit_trail": [],
            "hitl_required": False,
        }

        # Use .stream() so we can fire the per-node callback as soon as a
        # node finishes — same semantics as .invoke(), but with intermediate
        # state events. Each item from .stream() is {node_name: state_delta}.
        accumulated: Dict[str, Any] = dict(initial_state)
        for step in app.stream(initial_state, config=config):
            for node_name, delta in step.items():
                if isinstance(delta, dict):
                    accumulated.update(delta)
                if on_node:
                    try:
                        on_node(node_name, dict(accumulated))
                    except Exception:
                        # never let a stream consumer crash the run
                        pass
        final = accumulated

    runtime = round(time.time() - t_start, 2)
    final["_runtime_seconds"] = runtime

    # Persist run JSON for replay / debugging (used by the SSE replay path).
    _persist_run(final, fault_id)

    return final


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="TEP Multi-Agent LangGraph RCA")
    parser.add_argument("--fault", default="fault1", help="Fault ID (e.g. fault1)")
    parser.add_argument(
        "--question",
        default="Diagnose the current TEP process anomaly and identify the most likely root cause.",
    )
    parser.add_argument("--thread", default=None, help="Checkpoint thread ID")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  TEP Multi-Agent LangGraph RCA")
    print(f"  Fault: {args.fault}  |  {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"{'='*60}\n")

    final = run_langgraph(args.fault, args.question, args.thread)

    # Concise summary
    audit = final.get("audit_trail", [])
    nodes_visited = [a["node"] for a in audit]
    ev = final.get("evidence_by_layer", {})
    layers_used = [L for L, hits in ev.items() if hits]
    hyps = final.get("hypotheses", [])
    evaluation = final.get("evaluation", {})

    print(f"Nodes visited    : {nodes_visited}")
    print(f"Evidence layers  : {layers_used}")
    print(f"Hypotheses       : {len(hyps)}")
    print(f"Eval acceptable  : {evaluation.get('acceptable')}")
    print(f"Grounded ratio   : {evaluation.get('grounded_ratio')}")
    print(f"Policy pass      : {evaluation.get('policy', {}).get('is_advisory_safe')}")
    print(f"Revisions        : {final.get('revision_count', 0)}")
    print(f"HITL required    : {final.get('hitl_required', False)}")
    print(f"Runtime          : {final.get('_runtime_seconds')}s")
    print(f"\n--- Final Advisory ---")
    print(final.get("final_advisory", "(none — see hitl_required)"))
    print()


if __name__ == "__main__":
    main()
