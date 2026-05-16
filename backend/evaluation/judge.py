"""Held-out hallucination / grounding judge.

The MVP eval used the same model family (llama-3.3-70b) for both generation
and grounding self-critique. This is honest-ish but biased — the model knows
its own claims. Phase 8 introduces a held-out judge: a *smaller different*
NIM model evaluates the grounding of advisories produced by the 70b.

Default judge model: nvidia/llama-3.1-nemotron-70b-instruct  → swap to a
smaller model when available; if it 404s we degrade to mistralai/mixtral-8x7b.

Public API:
  grade_grounding(advisory_text, evidence_snippets, fault_id) -> dict

Returned shape:
  {
    "grounded_ratio": float in [0,1],
    "supported_claims": int,
    "unsupported_claims": int,
    "note": str,
    "judge_model": str,
  }
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()


_JUDGE_MODELS_TO_TRY = [
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.1-70b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "mistralai/mixtral-8x7b-instruct-v0.1",
]


_JUDGE_SYSTEM = """You are a strict evidence-grounding judge for industrial process diagnosis.

You receive:
 - an ADVISORY draft from an autonomous RCA agent
 - a list of EVIDENCE SNIPPETS the agent retrieved

For each substantive factual claim in the ADVISORY, decide whether the claim
is supported by AT LEAST ONE evidence snippet, OR by uncontested process
knowledge about the Tennessee Eastman Process (TEP) benchmark.

Counts:
  supported_claims  — claims clearly grounded
  unsupported_claims — claims that appear to be speculation or fabrication

Be honest — under-grounding is more dangerous than over-grounding. Cite
specific phrases from the evidence when the claim is supported.

Respond ONLY with valid JSON:
{
  "supported_claims": int,
  "unsupported_claims": int,
  "grounded_ratio": float (supported / (supported+unsupported), 0..1),
  "note": "brief one-sentence rationale, ≤200 chars"
}
"""


def _build_llm(model: str):
    from langchain_nvidia_ai_endpoints import ChatNVIDIA  # noqa: WPS433
    return ChatNVIDIA(
        model=model,
        api_key=os.environ.get("NVIDIA_API_KEY", ""),
        temperature=0.0,
        max_tokens=512,
    )


def grade_grounding(
    advisory_text: str,
    evidence_snippets: List[str],
    fault_id: str = "",
    preferred_model: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a held-out grounding judge over the advisory text.

    Tries preferred_model first; falls back through _JUDGE_MODELS_TO_TRY.
    """
    if not advisory_text or not advisory_text.strip():
        return {
            "grounded_ratio": 0.0,
            "supported_claims": 0,
            "unsupported_claims": 0,
            "note": "Empty advisory text.",
            "judge_model": "none",
        }

    evidence_block = "\n".join(f"- {s[:400]}" for s in evidence_snippets[:8]) \
        or "(no evidence retrieved)"

    user_prompt = f"""FAULT: {fault_id or 'unspecified'}

ADVISORY:
{advisory_text[:1200]}

EVIDENCE SNIPPETS:
{evidence_block}

Judge the grounding now. Respond with JSON only."""

    candidate_models = []
    if preferred_model:
        candidate_models.append(preferred_model)
    for m in _JUDGE_MODELS_TO_TRY:
        if m not in candidate_models:
            candidate_models.append(m)

    last_err: Optional[str] = None
    for model in candidate_models:
        try:
            llm = _build_llm(model)
            resp = llm.invoke([
                {"role": "system", "content": _JUDGE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ])
            content = resp.content if hasattr(resp, "content") else str(resp)
            m = re.search(r"\{.*\}", content, re.DOTALL)
            if not m:
                continue
            parsed = json.loads(m.group())
            sup = int(parsed.get("supported_claims", 0))
            unsup = int(parsed.get("unsupported_claims", 0))
            total = sup + unsup
            ratio = float(parsed.get("grounded_ratio",
                                    (sup / total) if total > 0 else 0.0))
            ratio = max(0.0, min(1.0, ratio))
            return {
                "grounded_ratio": round(ratio, 4),
                "supported_claims": sup,
                "unsupported_claims": unsup,
                "note": str(parsed.get("note", ""))[:240],
                "judge_model": model,
            }
        except Exception as exc:
            last_err = f"{type(exc).__name__}: {str(exc)[:160]}"
            continue

    return {
        "grounded_ratio": 0.0,
        "supported_claims": 0,
        "unsupported_claims": 0,
        "note": f"All judge models failed: {last_err}",
        "judge_model": "none",
    }
