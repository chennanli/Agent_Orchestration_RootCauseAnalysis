"""Smoke tests — fast, no external dependencies, no NAT runtime.

These guard the most basic regressions Codex flagged in CODEX_REVIEW_FOR_CLAUDE.md:
  - `backend.app` must be importable as a package (uvicorn deployment path)
  - The Live Copilot router must register the expected routes
  - The model registry must include every advertised model id
  - /api/anomaly/state must return the expected shape even with an empty buffer

We intentionally use FastAPI's TestClient against the live ASGI app rather
than mocking; this catches wiring bugs (e.g. router not actually mounted)
that a unit test would miss.
"""
from __future__ import annotations

import os

# Make sure `from backend import app` works regardless of how pytest is
# launched. The `backend/__init__.py` package marker handles the rest.
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_backend_app_importable():
    """`uvicorn backend.app:app` must work — Codex P0-1."""
    from backend import app as appmod

    assert hasattr(appmod, "app"), "backend.app module must export `app`"
    # ASGI callable shape
    assert callable(appmod.app)


def test_agent_models_registry_has_default():
    """Every advertised model id must resolve through get_model()."""
    from backend.agent_models import MODELS, DEFAULT_MODEL_ID, get_model

    assert DEFAULT_MODEL_ID in MODELS, "default must be a real entry"
    # Each entry should round-trip
    for mid in MODELS.keys():
        resolved = get_model(mid)
        assert resolved["id"] == mid
        # yaml block must carry the fields make_workflow_yaml depends on
        assert "model_name" in resolved["yaml"]
        assert "_type" in resolved["yaml"]


def test_models_endpoint_via_testclient():
    """GET /api/agent/models returns the registry + default id."""
    from fastapi.testclient import TestClient
    from backend.app import app

    client = TestClient(app)
    r = client.get("/api/agent/models")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "models" in body and "default" in body
    assert isinstance(body["models"], list) and body["models"], "non-empty"
    # Every model entry should have the fields the UI dropdown needs.
    for m in body["models"]:
        assert {"id", "label", "provider", "api_key_env", "api_key_present"} <= m.keys()


def test_anomaly_state_shape():
    """GET /api/anomaly/state returns shape the frontend expects.

    With no live data ingested the buffer is empty; the response should
    still be a well-formed JSON with `armed`, `t2_series`, etc.
    """
    from fastapi.testclient import TestClient
    from backend.app import app

    client = TestClient(app)
    r = client.get("/api/anomaly/state")
    assert r.status_code == 200, r.text
    body = r.json()
    for key in (
        "armed",
        "consecutive_anomalies",
        "threshold",
        "buffer_len",
        "t2_series",
        "ts",
    ):
        assert key in body, f"missing key {key} in {body!r}"
    assert isinstance(body["t2_series"], list)


def test_run_id_safety_guard():
    """Stream endpoint must reject path-traversal-y run ids."""
    from fastapi.testclient import TestClient
    from backend.app import app

    client = TestClient(app)
    # `..` should fail the _SAFE_ID_RE regex, returning 400 not 404 (and
    # NOT touching the filesystem).
    r = client.get("/api/agent/runs/..%2Fetc%2Fpasswd/stream")
    assert r.status_code in (400, 404)


def test_nat_api_live_router_has_expected_routes():
    """The Live Copilot router must register the routes the frontend hits."""
    from backend.nat_api_live import router

    paths = {getattr(r, "path", None) for r in router.routes}
    expected = {
        "/api/agent/diagnose",
        "/api/agent/runs/{run_id}/stream",
        "/api/agent/runs",
        "/api/agent/runs/{run_id}",
        "/api/agent/runs/{run_id}/followup",
        "/api/agent/runs/{run_id}/bakeoff",
        "/api/agent/models",
        "/api/anomaly/state",
    }
    missing = expected - paths
    assert not missing, f"router is missing {missing}"
