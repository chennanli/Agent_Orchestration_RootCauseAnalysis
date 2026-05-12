"""Advisory policy check.

The agent must produce *advisory-only* RCA. This tool inspects a candidate
final answer and flags wording that suggests autonomous control or
overclaims. The check is intentionally conservative for a portfolio demo.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from .schemas import AdvisoryPolicyResult, to_dict as _to_dict_helper


# Phrases that imply the system / agent is taking control of the process.
_FORBIDDEN_CONTROL_PATTERNS = [
    r"\bopen valve\b",
    r"\bclose valve\b",
    r"\bopen the valve\b",
    r"\bclose the valve\b",
    r"\b(open|close|adjust|change)\s+(?:the\s+)?(?:[a-z0-9_/-]+\s+){0,5}valve\b",
    r"\bopen \w+ valve\b",
    r"\bclose \w+ valve\b",
    r"\bset[- ]?point\b.*\b(change|adjust|increase|decrease|raise|lower|set)\b",
    r"\bchange (the )?setpoint\b",
    r"\b(start|stop|trip|isolate)\s+(the )?(reactor|pump|compressor|valve)\b",
    r"\binitiate (an? )?shutdown\b",
    r"\btake control\b",
    r"\bautomatically (open|close|adjust|change|set)\b",
    r"\bclosed[- ]loop control\b",
    r"\bAPC action\b",
    r"\bRTO action\b",
]

# Phrases that overclaim certainty or safety.
_OVERCLAIM_PATTERNS = [
    r"\bsafe to operate\b",
    r"\bguaranteed (root cause|diagnosis)\b",
    r"\bdefinitely the root cause\b",
    r"\b(the )?root cause is certain\b",
    r"\bproduction[- ]ready\b",
    r"\bindustrial[- ]grade certified\b",
    r"\bcertified safe\b",
    r"\b100% (sure|certain|safe)\b",
    r"\bprecise diagnosis\b",
    r"\bguaranteed to (work|succeed|fix)\b",
]

# Suggested rewrites the advisory should use.
_SUGGESTIONS = [
    "Use 'possible cause' rather than asserting a single root cause.",
    "Use 'recommended next inspection' rather than 'open/close valve'.",
    "State 'operator should verify' before any corrective step.",
    "End with 'requires SME review' to keep the boundary clear.",
]


def _to_dict(model: Any) -> Dict[str, Any]:
    return _to_dict_helper(model)


def _scan(text: str, patterns: List[str]) -> List[str]:
    hits: List[str] = []
    if not text:
        return hits
    lowered = text.lower()
    for pat in patterns:
        for m in re.finditer(pat, lowered, flags=re.IGNORECASE):
            snippet = m.group(0)
            if snippet not in hits:
                hits.append(snippet)
    return hits


def check_advisory_policy(candidate_answer: str) -> Dict[str, Any]:
    """Return whether `candidate_answer` is safe to show as an operator advisory."""
    text = candidate_answer or ""
    forbidden = _scan(text, _FORBIDDEN_CONTROL_PATTERNS)
    overclaims = _scan(text, _OVERCLAIM_PATTERNS)
    is_safe = not (forbidden or overclaims)

    if is_safe:
        notes = (
            "No forbidden control-style phrases or overclaims were detected. "
            "Reviewer should still confirm the advisory is human-readable and "
            "stays within read-only diagnosis scope."
        )
    else:
        bits = []
        if forbidden:
            bits.append(f"control-style phrases: {forbidden}")
        if overclaims:
            bits.append(f"overclaim phrases: {overclaims}")
        notes = (
            "Advisory is NOT safe as written. Detected " + "; ".join(bits) +
            ". Rewrite as advisory-only and require SME review."
        )

    result = AdvisoryPolicyResult(
        is_advisory_safe=is_safe,
        forbidden_phrases_found=forbidden,
        overclaims_found=overclaims,
        suggestions=_SUGGESTIONS if not is_safe else [],
        notes=notes,
    )
    return _to_dict(result)
