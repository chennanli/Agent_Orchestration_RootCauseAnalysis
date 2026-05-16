"""A2A (Agent-to-Agent) interface for the TEP RCA workbench.

Exposes three skills to other agents over the standard A2A surface:
  - diagnose_process_anomaly  → runs the LangGraph orchestrator
  - search_governed_wiki      → runs the hybrid wiki retrieval
  - review_advisory_policy    → runs the policy check

Endpoints (per A2A spec, https://github.com/google/A2A):
  GET  /.well-known/agent-card.json   → AgentCard JSON
  POST /a2a                            → JSON-RPC 2.0  (method "message/send")
  POST /a2a/stream                     → SSE           (method "message/stream")

Mount this on the existing FastAPI app at startup:
    from backend.a2a_router import a2a_router, well_known_router
    app.include_router(a2a_router)
    app.include_router(well_known_router)

Or run standalone (for the bonus "Wiki delegation via A2A" demo):
    uvicorn backend.a2a_router:standalone_wiki_app --port 8765
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

# ---------------------------------------------------------------------------
# Agent card (A2A-style agent-card JSON; shaped against the public protocol,
# not production-hardened — see docs/A2A_INTEGRATION.md)
# ---------------------------------------------------------------------------
def _full_agent_card(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    return {
        "protocolVersion": "0.3.0",
        "name": "TEP RCA Multi-Agent Workbench",
        "description": (
            "Multi-evidence agentic RCA over the Tennessee Eastman Process. "
            "Combines a 5-node LangGraph orchestrator with four evidence "
            "layers (governed wiki / field RCA notes / policy catalog / "
            "time-series case memory) and a read-only advisory-only policy."
        ),
        "url": f"{base_url}/a2a",
        "preferredTransport": "JSONRPC",
        "version": "0.1.0",
        "provider": {
            "organization": "chennanli",
            "url": "https://github.com/chennanli/Agent_Orchestration_RootCauseAnalysis",
        },
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
            "stateTransitionHistory": True,
        },
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "skills": [
            {
                "id": "diagnose_process_anomaly",
                "name": "Diagnose TEP process anomaly",
                "description": (
                    "Run the LangGraph multi-evidence orchestrator on a TEP "
                    "fault snapshot. Returns ranked root-cause hypotheses, "
                    "an advisory draft, policy-check, and grounded_ratio."
                ),
                "tags": ["rca", "industrial", "tennessee-eastman"],
                "examples": [
                    "Diagnose the current TEP process anomaly for fault1.",
                    "Is fault6 consistent with a feed-loss scenario?",
                ],
                "inputModes": ["text/plain"],
                "outputModes": ["application/json"],
            },
            {
                "id": "search_governed_wiki",
                "name": "Search governed TEP wiki",
                "description": (
                    "Hybrid (NIM dense + BM25 sparse + RRF) retrieval over "
                    "the governed TEP knowledge base (Downs & Vogel, McAvoy, "
                    "calculation methods)."
                ),
                "tags": ["retrieval", "rag", "wiki"],
                "examples": [
                    "What is the control structure for the TEP?",
                    "Search for PCA T2 anomaly detection method.",
                ],
                "inputModes": ["text/plain"],
                "outputModes": ["application/json"],
            },
            {
                "id": "review_advisory_policy",
                "name": "Review advisory policy",
                "description": (
                    "Check whether a candidate operator advisory is safe to "
                    "ship (no control-style verbs, no overclaims)."
                ),
                "tags": ["policy", "safety"],
                "examples": [
                    "Review this advisory: 'Open the reactor cooling valve.'",
                ],
                "inputModes": ["text/plain"],
                "outputModes": ["application/json"],
            },
        ],
    }


def _wiki_only_agent_card(base_url: str = "http://localhost:8765") -> Dict[str, Any]:
    """Smaller card for the standalone Wiki A2A server (bonus delegation)."""
    full = _full_agent_card(base_url)
    full["name"] = "TEP Governed Wiki Agent"
    full["description"] = (
        "A2A boundary in front of the TEP governed wiki "
        "(hybrid retrieval). The LangGraph orchestrator delegates to this "
        "agent through agent-card / task interface."
    )
    full["skills"] = [s for s in full["skills"] if s["id"] == "search_governed_wiki"]
    return full


# ---------------------------------------------------------------------------
# Skill implementations
# ---------------------------------------------------------------------------
def _skill_diagnose(text: str, params: Dict[str, Any]) -> Dict[str, Any]:
    from backend.langgraph_rca import run_langgraph
    fault_id = str(params.get("fault_id") or "fault1")
    final = run_langgraph(fault_id=fault_id, question=text or "Diagnose.")
    return {
        "fault_id": fault_id,
        "final_advisory": final.get("final_advisory", ""),
        "hitl_required": final.get("hitl_required", False),
        "evaluation": final.get("evaluation", {}),
        "evidence_layers_used": [
            L for L, hits in (final.get("evidence_by_layer") or {}).items() if hits
        ],
        "revision_count": int(final.get("revision_count") or 0),
        "runtime_seconds": final.get("_runtime_seconds"),
    }


def _skill_wiki(text: str, params: Dict[str, Any]) -> Dict[str, Any]:
    from backend.agent_tools.vector_knowledge import (
        hybrid_search,
        build_or_load_index,
    )
    build_or_load_index()
    k = int(params.get("k") or 5)
    hits = hybrid_search(text, k=k)
    return {"query": text, "k": k, "hits": hits, "count": len(hits)}


def _skill_policy(text: str, params: Dict[str, Any]) -> Dict[str, Any]:
    from backend.agent_tools.policy_tools import check_advisory_policy
    return check_advisory_policy(text)


_SKILL_REGISTRY: Dict[str, Callable[[str, Dict[str, Any]], Dict[str, Any]]] = {
    "diagnose_process_anomaly": _skill_diagnose,
    "search_governed_wiki": _skill_wiki,
    "review_advisory_policy": _skill_policy,
}


# ---------------------------------------------------------------------------
# Message helpers (A2A v0.3 shape)
# ---------------------------------------------------------------------------
def _extract_user_text(params: Dict[str, Any]) -> str:
    """Pull the user's text from an A2A `message` payload.

    Expected shape:
        params = {"message": {"role": "user", "parts": [{"text": "..."}, ...]}}
    Falls back to params["text"] if a caller sent a simplified shape.
    """
    msg = params.get("message") or {}
    parts = msg.get("parts") or []
    chunks = []
    for p in parts:
        if isinstance(p, dict):
            t = p.get("text") or p.get("content") or ""
            if isinstance(t, str):
                chunks.append(t)
    if chunks:
        return " ".join(chunks).strip()
    if isinstance(params.get("text"), str):
        return params["text"]
    return ""


def _wrap_agent_message(skill_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap a skill result in an A2A `message` envelope (role=agent)."""
    return {
        "messageId": str(uuid.uuid4()),
        "role": "agent",
        "parts": [
            {"text": f"[{skill_id}] complete."},
            {"data": result},
        ],
    }


def _resolve_skill_id(params: Dict[str, Any]) -> Optional[str]:
    """Find the requested skill ID — explicit (params.skill / metadata.skill)
    or by simple keyword guess from the user's text."""
    if isinstance(params.get("skill"), str):
        return params["skill"]
    md = params.get("metadata") or {}
    if isinstance(md.get("skill"), str):
        return md["skill"]
    txt = _extract_user_text(params).lower()
    if "wiki" in txt or "search" in txt or "knowledge" in txt:
        return "search_governed_wiki"
    if "policy" in txt or "review" in txt or "advisory" in txt:
        return "review_advisory_policy"
    return "diagnose_process_anomaly"


# ---------------------------------------------------------------------------
# FastAPI routers
# ---------------------------------------------------------------------------
well_known_router = APIRouter(prefix="/.well-known", tags=["a2a"])
a2a_router = APIRouter(prefix="/a2a", tags=["a2a"])


@well_known_router.get("/agent-card.json")
async def agent_card_main(request: Request) -> JSONResponse:
    base = str(request.base_url).rstrip("/")
    return JSONResponse(_full_agent_card(base))


def _make_jsonrpc_error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id,
            "error": {"code": code, "message": message}}


def _make_jsonrpc_result(req_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


@a2a_router.post("")
async def jsonrpc_endpoint(request: Request) -> JSONResponse:
    """JSON-RPC 2.0 endpoint. Supported method: `message/send`."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(_make_jsonrpc_error(None, -32700, "Parse error"))

    req_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params") or {}

    if method != "message/send":
        return JSONResponse(_make_jsonrpc_error(req_id, -32601,
            f"Method not found: {method}. Supported: message/send"))

    skill_id = _resolve_skill_id(params)
    if skill_id not in _SKILL_REGISTRY:
        return JSONResponse(_make_jsonrpc_error(req_id, -32602,
            f"Unknown skill: {skill_id}"))

    user_text = _extract_user_text(params)
    task_id = str(uuid.uuid4())
    started = time.time()
    try:
        skill_result = _SKILL_REGISTRY[skill_id](user_text, params)
    except Exception as exc:
        return JSONResponse(_make_jsonrpc_error(req_id, -32000,
            f"Skill execution error: {type(exc).__name__}: {exc}"))

    task = {
        "id": task_id,
        "contextId": params.get("contextId") or str(uuid.uuid4()),
        "status": {"state": "completed", "timestamp": time.time()},
        "history": [{"role": "user", "parts": [{"text": user_text}]}],
        "artifacts": [
            {
                "artifactId": str(uuid.uuid4()),
                "name": f"{skill_id}_result",
                "parts": [{"data": skill_result}],
            }
        ],
        "metadata": {
            "skill": skill_id,
            "runtime_seconds": round(time.time() - started, 3),
        },
    }
    return JSONResponse(_make_jsonrpc_result(req_id, task))


@a2a_router.post("/stream")
async def sse_stream(request: Request) -> StreamingResponse:
    """SSE streaming endpoint. Emits status-update events then a final task."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    req_id = body.get("id")
    params = body.get("params") or {}
    skill_id = _resolve_skill_id(params)
    user_text = _extract_user_text(params)

    async def event_stream():
        # status: working
        yield (
            f"data: {json.dumps({'jsonrpc': '2.0', 'id': req_id, 'result': {'kind':'status-update','status':{'state':'working'}}})}\n\n"
        )
        # invoke skill (sync run — wrap in run_in_executor for true async if needed)
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, _SKILL_REGISTRY[skill_id], user_text, params
            )
        except Exception as exc:
            yield (
                f"data: {json.dumps({'jsonrpc':'2.0','id':req_id,'error':{'code':-32000,'message':str(exc)}})}\n\n"
            )
            return
        # final task event
        task = {
            "kind": "task",
            "id": str(uuid.uuid4()),
            "status": {"state": "completed"},
            "artifacts": [
                {"artifactId": str(uuid.uuid4()),
                 "name": f"{skill_id}_result",
                 "parts": [{"data": result}]},
            ],
            "metadata": {"skill": skill_id},
        }
        yield f"data: {json.dumps({'jsonrpc':'2.0','id':req_id,'result':task})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Standalone "wiki delegation" A2A app (the bonus)
# ---------------------------------------------------------------------------
standalone_wiki_app = FastAPI(title="TEP Wiki A2A Agent")

_wiki_well_known = APIRouter(prefix="/.well-known", tags=["a2a"])
_wiki_a2a = APIRouter(prefix="/a2a", tags=["a2a"])


@_wiki_well_known.get("/agent-card.json")
async def _wiki_card(request: Request) -> JSONResponse:
    base = str(request.base_url).rstrip("/")
    return JSONResponse(_wiki_only_agent_card(base))


@_wiki_a2a.post("")
async def _wiki_rpc(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(_make_jsonrpc_error(None, -32700, "Parse error"))
    req_id = body.get("id")
    method = body.get("method", "")
    if method != "message/send":
        return JSONResponse(_make_jsonrpc_error(req_id, -32601, "method not found"))
    params = body.get("params") or {}
    user_text = _extract_user_text(params)
    try:
        result = _skill_wiki(user_text, params)
    except Exception as exc:
        return JSONResponse(_make_jsonrpc_error(req_id, -32000, str(exc)))
    task = {
        "id": str(uuid.uuid4()),
        "status": {"state": "completed"},
        "artifacts": [
            {"artifactId": str(uuid.uuid4()),
             "name": "search_governed_wiki_result",
             "parts": [{"data": result}]},
        ],
        "metadata": {"skill": "search_governed_wiki"},
    }
    return JSONResponse(_make_jsonrpc_result(req_id, task))


standalone_wiki_app.include_router(_wiki_well_known)
standalone_wiki_app.include_router(_wiki_a2a)


# ---------------------------------------------------------------------------
# Delegation client helper (for the LangGraph orchestrator)
# ---------------------------------------------------------------------------
def call_remote_wiki_via_a2a(
    query: str,
    base_url: str = "http://127.0.0.1:8765",
    k: int = 5,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """Call the standalone Wiki A2A server via JSON-RPC `message/send`.

    Used by the langgraph orchestrator (when the WIKI_VIA_A2A env var is set)
    to delegate governed retrieval through an agent-card boundary instead of
    direct in-process calls.
    """
    import httpx
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "skill": "search_governed_wiki",
            "message": {
                "messageId": str(uuid.uuid4()),
                "role": "user",
                "parts": [{"text": query}],
            },
            "k": k,
        },
    }
    with httpx.Client(timeout=timeout) as client:
        r = client.post(f"{base_url}/a2a", json=payload)
    r.raise_for_status()
    resp = r.json()
    if "error" in resp:
        raise RuntimeError(f"A2A error: {resp['error']}")
    artifacts = resp["result"].get("artifacts", [])
    if not artifacts:
        return {"hits": []}
    data_part = next((p for p in artifacts[0].get("parts", []) if "data" in p), None)
    return data_part["data"] if data_part else {"hits": []}
