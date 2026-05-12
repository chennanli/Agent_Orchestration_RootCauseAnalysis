"""Available LLM choices for the NAT agent path.

Each model entry describes how to rewrite the `llms.nim_llm` block of
`backend/nat_workflows/tep_rca_workflow.yml` so the workflow uses that model
without changing any workflow / tool logic. The workflow keeps the
literal name `nim_llm` (the rest of the YAML references it by that name);
only the `_type`, `model_name`, `base_url`, and api-key handling change.

Why this file exists:
    The default model (`meta/llama-3.3-70b-instruct`) is small enough to
    hedge in its diagnoses. The user wants to pick stronger models
    (Llama 405B, Nemotron, Gemini, etc.) per-run. Users can also paste a
    custom API key in the UI that overrides the environment variable.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# Each entry: id → human label + how to rewrite the `nim_llm` block.
#
# All NIM-hosted models share the same endpoint (the OpenAI-compatible NIM
# proxy at integrate.api.nvidia.com) and just differ by model name. Gemini
# uses Google's OpenAI-compatible endpoint. Adding a new model = add a row.
MODELS: Dict[str, Dict[str, Any]] = {
    # NVIDIA NIM — free tier. We list models that are KNOWN to be on the
    # active catalog as of 2026-05; some popular ones (e.g. llama-3.1-405b)
    # were retired and 410-gone. If you add one, verify it's not EOL.
    "nim-llama-3.3-70b": {
        "label": "NIM · Llama 3.3 70B (default, free, balanced)",
        "provider": "NVIDIA NIM",
        "yaml": {
            "_type": "nim",
            "model_name": "meta/llama-3.3-70b-instruct",
            "temperature": 0.0,
        },
        "api_key_env": "NVIDIA_API_KEY",
    },
    "nim-llama-3.1-8b": {
        "label": "NIM · Llama 3.1 8B (free, fast fallback for rate limits)",
        "provider": "NVIDIA NIM",
        "yaml": {
            "_type": "nim",
            "model_name": "meta/llama-3.1-8b-instruct",
            "temperature": 0.0,
        },
        "api_key_env": "NVIDIA_API_KEY",
    },
    "nim-mixtral-8x22b": {
        "label": "NIM · Mixtral 8x22B (free, Mistral mixture-of-experts)",
        "provider": "NVIDIA NIM",
        "yaml": {
            "_type": "nim",
            "model_name": "mistralai/mixtral-8x22b-instruct-v0.1",
            "temperature": 0.0,
        },
        "api_key_env": "NVIDIA_API_KEY",
    },
    # Google Gemini — via the OpenAI-compatible endpoint at
    # generativelanguage.googleapis.com/v1beta/openai/. Model identifiers
    # match Google's stable API (no `-exp` suffix; the 1.5-flash alias was
    # retired from `v1main` in early 2026).
    "gemini-2.5-flash": {
        "label": "Google Gemini 2.5 Flash (free tier, fast, current stable)",
        "provider": "Google",
        "yaml": {
            "_type": "openai",
            "model_name": "gemini-2.5-flash",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "temperature": 0.0,
        },
        "api_key_env": "GEMINI_API_KEY",
    },
    "gemini-2.5-pro": {
        "label": "Google Gemini 2.5 Pro (paid, deepest reasoning + structure)",
        "provider": "Google",
        "yaml": {
            "_type": "openai",
            "model_name": "gemini-2.5-pro",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "temperature": 0.0,
        },
        "api_key_env": "GEMINI_API_KEY",
    },
}

DEFAULT_MODEL_ID = "nim-llama-3.3-70b"


def list_models() -> List[Dict[str, Any]]:
    """Public manifest used by the frontend dropdown."""
    out: List[Dict[str, Any]] = []
    for model_id, m in MODELS.items():
        env_var = m["api_key_env"]
        out.append({
            "id": model_id,
            "label": m["label"],
            "provider": m["provider"],
            "api_key_env": env_var,
            "api_key_present": bool(os.environ.get(env_var)),
        })
    return out


def get_model(model_id: Optional[str]) -> Dict[str, Any]:
    """Resolve a model id, falling back to the default."""
    if not model_id or model_id not in MODELS:
        model_id = DEFAULT_MODEL_ID
    return {**MODELS[model_id], "id": model_id}


def make_workflow_yaml(
    canonical_yaml: Path,
    model_id: Optional[str],
    user_api_key: Optional[str] = None,
) -> Path:
    """Read the canonical workflow YAML, rewrite the `llms.nim_llm` block
    for the chosen model, write it to a temp file, return the temp path.

    `user_api_key`, if provided, is exported to the environment variable the
    model expects (e.g. GEMINI_API_KEY) so a UI-pasted API key reaches NAT.

    Important nuance for non-NIM models: NAT's `_type: openai` plugin
    delegates to the OpenAI SDK, which looks for `OPENAI_API_KEY` by
    default — not `GEMINI_API_KEY`. So we must explicitly write the api_key
    into the YAML block. We resolve the actual key by:
      1. user_api_key (from the UI), if provided
      2. otherwise os.environ[model['api_key_env']]
    """
    model = get_model(model_id)
    yaml_block = dict(model["yaml"])

    # If the user pasted an API key in the UI, expose it via the model's env
    # var so the NAT client picks it up too (defence-in-depth).
    if user_api_key:
        os.environ[model["api_key_env"]] = user_api_key

    # Resolve the api key. For Gemini-via-OpenAI-compat this is crucial
    # because NAT's openai plugin won't know to look at GEMINI_API_KEY.
    resolved_key = user_api_key or os.environ.get(model["api_key_env"])
    if resolved_key and "api_key" not in yaml_block:
        yaml_block["api_key"] = resolved_key

    with open(canonical_yaml, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    if "llms" not in doc or "nim_llm" not in doc["llms"]:
        raise ValueError(
            f"{canonical_yaml} has no llms.nim_llm block to rewrite"
        )
    doc["llms"]["nim_llm"] = yaml_block

    tmp = tempfile.NamedTemporaryFile(
        prefix="tep_workflow_", suffix=".yml", delete=False, mode="w",
        encoding="utf-8",
    )
    yaml.safe_dump(doc, tmp, sort_keys=False)
    tmp.close()
    return Path(tmp.name)
