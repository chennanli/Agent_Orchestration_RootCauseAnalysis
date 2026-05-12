"""Smoke tests for the TEP Copilot backend.

These tests do NOT exercise the NAT runtime (which requires an
NVIDIA_API_KEY and pulls in heavyweight LLM SDKs); they verify the parts
of the backend that *should* be importable and routable without external
services. Run with:

    uv sync --extra dev   # or: .venv/bin/pip install pytest pytest-asyncio
    .venv/bin/pytest backend/tests -q

See `pyproject.toml [tool.pytest.ini_options]` for default options.
"""
