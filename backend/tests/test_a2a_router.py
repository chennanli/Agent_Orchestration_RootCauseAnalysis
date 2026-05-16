"""Hermetic tests for the A2A-style JSON-RPC + agent-card surface.

Uses FastAPI's TestClient against the standalone wiki app — no live NIM
calls (the policy skill is deterministic, the wiki skill is monkeypatched).
"""
from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from backend import a2a_router as a2a


# ---------------------------------------------------------------------------
# Agent card structure
# ---------------------------------------------------------------------------
def test_full_agent_card_has_required_a2a_fields():
    card = a2a._full_agent_card("http://localhost:8000")
    # A2A spec requirements
    assert card["protocolVersion"]
    assert card["name"]
    assert card["description"]
    assert card["url"].startswith("http")
    assert card["preferredTransport"] in {"JSONRPC", "GRPC", "HTTP+JSON"}
    assert card["version"]
    assert "capabilities" in card
    assert isinstance(card["defaultInputModes"], list)
    assert isinstance(card["defaultOutputModes"], list)
    # Three skills exposed
    skills = card["skills"]
    skill_ids = {s["id"] for s in skills}
    assert skill_ids == {
        "diagnose_process_anomaly",
        "search_governed_wiki",
        "review_advisory_policy",
    }
    # Each skill has the required fields
    for skill in skills:
        assert skill["id"] and skill["name"] and skill["description"]
        assert isinstance(skill.get("tags"), list)


def test_wiki_only_agent_card_only_advertises_wiki_skill():
    card = a2a._wiki_only_agent_card("http://localhost:8765")
    assert len(card["skills"]) == 1
    assert card["skills"][0]["id"] == "search_governed_wiki"


# ---------------------------------------------------------------------------
# Standalone wiki app — TestClient end-to-end (no real LLM)
# ---------------------------------------------------------------------------
@pytest.fixture
def wiki_client():
    return TestClient(a2a.standalone_wiki_app)


def test_well_known_agent_card_endpoint_returns_json(wiki_client):
    r = wiki_client.get("/.well-known/agent-card.json")
    assert r.status_code == 200
    body = r.json()
    assert body["protocolVersion"]
    assert body["skills"][0]["id"] == "search_governed_wiki"


def test_jsonrpc_unknown_method_returns_method_not_found(wiki_client):
    r = wiki_client.post("/a2a", json={
        "jsonrpc": "2.0",
        "id": "1",
        "method": "message/unknown_thing",
        "params": {},
    })
    assert r.status_code == 200
    body = r.json()
    assert body["jsonrpc"] == "2.0"
    assert body["id"] == "1"
    assert "error" in body
    assert body["error"]["code"] == -32601  # JSON-RPC "method not found"


def test_jsonrpc_malformed_body_returns_parse_error(wiki_client):
    r = wiki_client.post("/a2a", content=b"not valid json")
    assert r.status_code == 200
    body = r.json()
    assert body.get("error", {}).get("code") == -32700  # Parse error


def test_jsonrpc_wiki_skill_returns_task_envelope(wiki_client, monkeypatch):
    """Stub the underlying wiki skill so we don't hit ChromaDB / NIM."""
    monkeypatch.setattr(a2a, "_skill_wiki", lambda text, params: {
        "query": text,
        "k": int(params.get("k", 5)),
        "hits": [{"source": "fake.md", "text": "stubbed hit"}],
        "count": 1,
    })
    payload = {
        "jsonrpc": "2.0",
        "id": "demo-1",
        "method": "message/send",
        "params": {
            "skill": "search_governed_wiki",
            "message": {
                "messageId": str(uuid.uuid4()),
                "role": "user",
                "parts": [{"text": "PCA T2 statistic"}],
            },
            "k": 3,
        },
    }
    r = wiki_client.post("/a2a", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "demo-1"
    assert "result" in body
    task = body["result"]
    # A2A task envelope shape
    assert task["status"]["state"] == "completed"
    assert task["metadata"]["skill"] == "search_governed_wiki"
    assert len(task["artifacts"]) == 1
    artifact = task["artifacts"][0]
    assert artifact["name"] == "search_governed_wiki_result"
    # The artifact's data part carries our stub
    data_part = next(p for p in artifact["parts"] if "data" in p)
    assert data_part["data"]["count"] == 1
    assert data_part["data"]["hits"][0]["text"] == "stubbed hit"


# ---------------------------------------------------------------------------
# Skill dispatch logic — independent of HTTP
# ---------------------------------------------------------------------------
def test_resolve_skill_id_honours_explicit_param():
    sid = a2a._resolve_skill_id({"skill": "review_advisory_policy"})
    assert sid == "review_advisory_policy"


def test_resolve_skill_id_falls_through_to_keyword_heuristic():
    # No explicit skill: text contains "wiki" → wiki
    sid = a2a._resolve_skill_id({
        "message": {"role": "user", "parts": [{"text": "search the wiki"}]}
    })
    assert sid == "search_governed_wiki"
    # Default falls to diagnose
    sid = a2a._resolve_skill_id({
        "message": {"role": "user", "parts": [{"text": "what's happening?"}]}
    })
    assert sid == "diagnose_process_anomaly"


def test_extract_user_text_handles_multiple_parts():
    text = a2a._extract_user_text({
        "message": {
            "role": "user",
            "parts": [{"text": "hello"}, {"text": " world"}],
        }
    })
    assert text == "hello  world"
