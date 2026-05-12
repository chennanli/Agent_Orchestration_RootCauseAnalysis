"""History / similarity tools that read real CSV-derived sensor windows and
fault descriptions for the agent's `find_similar_faults` tool.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import pandas as pd

from .anomaly_tools import (
    _find_first_stable_anomaly,
    _load_baseline_stats,
    _load_fault_csv,
    _normalize_fault_id,
    _resolve_csv_path,
    ANOMALY_RUN_LENGTH,
)
from .schemas import (
    SensorWindowResult,
    SimilarFaultResult,
    to_dict as _to_dict_helper,
)

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

# Possible folders that contain historical RCA markdown produced by the
# legacy demo. We treat them as 'past investigations' for keyword-based
# similarity search.
_HISTORICAL_RCA_DIRS = [
    _BACKEND_DIR / "LLM_RCA_Results",
    _PROJECT_ROOT / "RCA_Results",
]


def _to_dict(model: Any) -> Dict[str, Any]:
    return _to_dict_helper(model)


def get_sensor_window(
    sensor_name: str,
    fault_id: Union[str, int] = "fault1",
    window: int = 20,
) -> Dict[str, Any]:
    """Return a CSV-derived window of values for `sensor_name`.

    Read-only. The window is centered on the deterministic anomaly index,
    so the agent gets the actual data the operator would have looked at.
    Falls back to the tail of the CSV if no anomaly is present.
    """
    canonical = _normalize_fault_id(fault_id)
    try:
        df, csv_path = _load_fault_csv(canonical)
    except FileNotFoundError as exc:
        return _to_dict(SensorWindowResult(
            sensor_name=sensor_name,
            fault_id=canonical,
            available=False,
            window=0,
            values=[],
            note=f"Fault CSV not found: {exc}",
        ))

    if sensor_name not in df.columns:
        return _to_dict(SensorWindowResult(
            sensor_name=sensor_name,
            fault_id=canonical,
            available=False,
            window=0,
            values=[],
            note=(f"Sensor '{sensor_name}' is not a column in {csv_path.name}. "
                  "Tip: pass an exact CSV header such as 'Reactor Pressure'."),
        ))

    anomaly_idx = _find_first_stable_anomaly(df)
    if anomaly_idx < 0:
        end = len(df)
    else:
        end = min(len(df), anomaly_idx + 1)
    start = max(0, end - max(1, window))
    series = df.iloc[start:end][sensor_name].astype(float)
    values = series.tolist()

    baseline = _load_baseline_stats()
    baseline_mean = 0.0
    baseline_std = 0.0
    if not baseline.empty and sensor_name in baseline["feature"].values:
        row = baseline[baseline["feature"] == sensor_name].iloc[0]
        baseline_mean = float(row["mean"])
        baseline_std = float(row["std"])

    pct_change = 0.0
    if baseline_mean != 0:
        pct_change = (float(series.mean()) - baseline_mean) / baseline_mean * 100.0

    return _to_dict(SensorWindowResult(
        sensor_name=sensor_name,
        fault_id=canonical,
        available=True,
        window=len(values),
        values=[round(v, 4) for v in values],
        mean=round(float(series.mean()), 4),
        std=round(float(series.std(ddof=0)), 4),
        baseline_mean=round(baseline_mean, 4),
        baseline_std=round(baseline_std, 4),
        pct_change_vs_baseline=round(pct_change, 3),
        note=("Window taken from CSV (read-only). "
              "Centered on deterministic anomaly index when available."),
    ))


# ---------------------------------------------------------------------------
# Similar fault search
# ---------------------------------------------------------------------------

# Keep a static map of fault descriptions from analysis.py / Downs & Vogel
# so we do not depend on importing analysis.py (which executes side effects
# at import time).
_FAULT_DESCRIPTIONS: List[Tuple[str, str]] = [
    ("fault0", "Normal Operating Conditions"),
    ("fault1", "IDV(1) A/C Feed Ratio, B Composition Constant (Stream 4) - Step"),
    ("fault2", "IDV(2) B Composition, A/C Ratio Constant (Stream 4) - Step"),
    ("fault3", "IDV(3) D Feed Temperature (Stream 2) - Step"),
    ("fault4", "IDV(4) Reactor Cooling Water Inlet Temperature - Step"),
    ("fault5", "IDV(5) Condenser Cooling Water Inlet Temperature - Step"),
    ("fault6", "IDV(6) A Feed Loss (Stream 1) - Step"),
    ("fault7", "IDV(7) C Header Pressure Loss - Reduced Availability (Stream 4) - Step"),
    ("fault8", "IDV(8) A, B, C Feed Composition (Stream 4) - Random Variation"),
    ("fault9", "IDV(9) D Feed Temperature (Stream 2) - Random Variation"),
    ("fault10", "IDV(10) C Feed Temperature (Stream 4) - Random Variation"),
    ("fault11", "IDV(11) Reactor Cooling Water Inlet Temperature - Random Variation"),
    ("fault12", "IDV(12) Condenser Cooling Water Inlet Temperature - Random Variation"),
    ("fault13", "IDV(13) Reaction Kinetics - Slow Drift"),
    ("fault14", "IDV(14) Reactor Cooling Water Valve - Sticking"),
    ("fault15", "IDV(15) Condenser Cooling Water Valve - Sticking"),
]

_FAULT_FAMILIES = {
    "fault1": "feed composition or ratio disturbance",
    "fault2": "feed composition or ratio disturbance",
    "fault3": "feed temperature disturbance",
    "fault4": "reactor cooling water disturbance",
    "fault5": "condenser cooling water disturbance",
    "fault6": "feed loss",
    "fault7": "header pressure loss",
    "fault8": "feed composition random variation",
    "fault9": "feed temperature random variation",
    "fault10": "feed temperature random variation",
    "fault11": "reactor cooling water random variation",
    "fault12": "condenser cooling water random variation",
    "fault13": "reaction kinetics slow drift",
    "fault14": "reactor cooling water valve sticking",
    "fault15": "condenser cooling water valve sticking",
}

_STOPWORDS = {
    "the", "and", "for", "with", "of", "in", "on", "to", "a", "is", "are",
    "fault", "anomaly", "process", "tep", "demo",
}


def _tokens(text: str) -> List[str]:
    return [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_]+", text or "")
            if w.lower() not in _STOPWORDS and len(w) > 2]


def _gather_historical_rca_snippets(limit: int = 30) -> List[Tuple[str, str]]:
    """Return [(label, text)] from past LLM RCA markdown if any exist."""
    snippets: List[Tuple[str, str]] = []
    for d in _HISTORICAL_RCA_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md"))[:limit]:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue
            label = f"{d.name}/{p.name}"
            snippets.append((label, text[:4000]))
    return snippets


def find_similar_faults(signature: str, top_k: int = 3) -> Dict[str, Any]:
    """Keyword-based similarity over canonical TEP fault descriptions and
    historical LLM RCA outputs.

    Returns a `SimilarFaultResult` dict. Marked clearly as keyword-based
    demo similarity, not embeddings.
    """
    sig_tokens = set(_tokens(signature))
    matches: List[Dict[str, Any]] = []

    if not sig_tokens:
        return _to_dict(SimilarFaultResult(
            signature=signature,
            matches=[],
            note="Empty signature; nothing to compare.",
        ))

    # 1) Score against canonical fault descriptions.
    desc_scored: List[Tuple[float, str, str, str]] = []
    for fid, desc in _FAULT_DESCRIPTIONS:
        d_tokens = set(_tokens(desc))
        overlap = sig_tokens & d_tokens
        if not overlap:
            continue
        score = len(overlap) / max(1, len(sig_tokens | d_tokens))
        desc_scored.append((score, fid, _FAULT_FAMILIES.get(fid, ""), desc))
    desc_scored.sort(reverse=True)

    for score, fid, family, desc in desc_scored[:top_k]:
        matches.append({
            "fault_id": fid,
            "fault_family": family,
            "score": round(score, 3),
            "evidence": desc,
            "source": "Downs & Vogel canonical IDV catalog",
        })

    # 2) Score against historical LLM RCA outputs (if present).
    hist = _gather_historical_rca_snippets()
    hist_scored: List[Tuple[float, str, str]] = []
    for label, text in hist:
        tokens = set(_tokens(text))
        overlap = sig_tokens & tokens
        if not overlap:
            continue
        score = len(overlap) / max(1, len(sig_tokens | tokens))
        snippet = text[:300].replace("\n", " ")
        hist_scored.append((score, label, snippet))
    hist_scored.sort(reverse=True)

    for score, label, snippet in hist_scored[:top_k]:
        matches.append({
            "fault_id": label,
            "fault_family": "historical RCA report",
            "score": round(score, 3),
            "evidence": snippet,
            "source": "backend/LLM_RCA_Results or RCA_Results",
        })

    return _to_dict(SimilarFaultResult(
        signature=signature,
        matches=matches[: max(top_k * 2, top_k)],
        note=("Similarity is keyword-based demo similarity. "
              "Not vector / embedding similarity."),
    ))
