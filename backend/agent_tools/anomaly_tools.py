"""Read-only anomaly inspection tools for TEP fault CSVs.

These tools wrap the deterministic PCA/T^2 outputs already produced by the
existing demo (`backend/data/faultN.csv` files contain `t2_stat`, `anomaly`
and per-variable `t2_*` contributions). They never run the simulator and
they never change the data.

Public functions:
    inspect_anomaly_snapshot(fault_id) -> dict
    rank_contributing_variables(fault_id, top_k) -> dict
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import pandas as pd

from .schemas import AnomalySnapshot, VariableContribution, to_dict as _to_dict_helper
from .tep_tags import tag_for, label_with_tag, is_manipulated

# Demo-time T^2 threshold used by FaultDetectionModel.set_t2_threshold().
T2_THRESHOLD_DEMO = 55.0
# How many consecutive rows above threshold define a stable anomaly start.
ANOMALY_RUN_LENGTH = 20

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_DATA_DIR = _BACKEND_DIR / "data"
_FRONTEND_PUBLIC = _REPO_ROOT / "frontend" / "public"
_STATS_FILE = _BACKEND_DIR / "stats" / "features_mean_std.csv"


def _csv_str(p: Path) -> str:
    """Serialize a fault-CSV Path for tool output.

    Returns a repo-relative POSIX string when the path is inside the repo,
    falling back to just the filename otherwise. This is the only public
    serialization site for csv paths in tool output — keep it repo-relative
    so we never leak the developer's home directory (`/Users/foo/...`)
    into committed sample runs, A2A responses, MCP responses, or SSE
    state snapshots delivered to the browser.
    """
    try:
        rel = p.resolve().relative_to(_REPO_ROOT)
        return rel.as_posix()
    except ValueError:
        # Path is outside the repo (e.g. a tempfile from a test); strip
        # everything but the filename so absolute home paths can't leak.
        return p.name


def _normalize_fault_id(fault_id: Union[str, int]) -> str:
    """Accept 'fault1', '1' or 1 and return canonical 'faultN'.

    Live snapshots use the literal `live_<utc-ts>` id (case-preserving, with
    underscores) and are passed through unchanged.
    """
    if isinstance(fault_id, int):
        return f"fault{fault_id}"
    s = str(fault_id).strip()
    if s.lower().startswith("live_"):
        return s
    s = s.lower()
    if s.startswith("fault"):
        return s
    if s.isdigit():
        return f"fault{int(s)}"
    return s or "fault1"


def _resolve_csv_path(fault_id: Union[str, int]) -> Path:
    """Resolve a fault CSV.

    Seeded golden faults like `fault1` live under `frontend/public/`.
    Live snapshots written by `backend.agent_tools.live_snapshot` use the
    `live_<utc-ts>` id and live under `backend/diagnostics/snapshots/`.
    """
    name = _normalize_fault_id(fault_id)
    if name.startswith("live_"):
        import re as _re
        if not _re.fullmatch(r"live_[A-Za-z0-9_\-]+", name):
            raise ValueError(f"unsafe live fault_id: {name!r}")
        from backend.agent_tools.live_snapshot import SNAPSHOTS_DIR
        return SNAPSHOTS_DIR / f"{name}.csv"
    candidates = [_FRONTEND_PUBLIC / f"{name}.csv", _DATA_DIR / f"{name}.csv"]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def _load_fault_csv(fault_id: Union[str, int]) -> Tuple[pd.DataFrame, Path]:
    csv_path = _resolve_csv_path(fault_id)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"TEP fault CSV not found for '{fault_id}'. Looked at: {csv_path}"
        )
    df = pd.read_csv(csv_path)
    return df, csv_path


def _load_baseline_stats() -> pd.DataFrame:
    if _STATS_FILE.exists():
        return pd.read_csv(_STATS_FILE)
    return pd.DataFrame(columns=["feature", "mean", "std"])


def _find_first_stable_anomaly(df: pd.DataFrame) -> int:
    """First index where ANOMALY_RUN_LENGTH consecutive rows are anomalous.

    Returns -1 if not present. Falls back to first row above T^2 threshold
    when the 'anomaly' column is missing.
    """
    if "anomaly" in df.columns:
        anomaly_bool = df["anomaly"].astype(bool)
        run = anomaly_bool.rolling(window=ANOMALY_RUN_LENGTH).sum() == ANOMALY_RUN_LENGTH
        if run.any():
            return int(run.idxmax())
        if anomaly_bool.any():
            return int(anomaly_bool.idxmax())
        return -1
    if "t2_stat" in df.columns:
        above = df["t2_stat"] > T2_THRESHOLD_DEMO
        if above.any():
            return int(above.idxmax())
    return -1


def _to_dict(model: Any) -> Dict[str, Any]:
    """Backward-compatible alias for schemas.to_dict."""
    return _to_dict_helper(model)


def inspect_anomaly_snapshot(fault_id: Union[str, int] = "fault1") -> Dict[str, Any]:
    """Return a structured snapshot of the deterministic anomaly state.

    Read-only. Uses the precomputed `anomaly`, `t2_stat` columns shipped in
    the fault CSVs. Falls back gracefully if columns are missing.
    """
    canonical = _normalize_fault_id(fault_id)
    try:
        df, csv_path = _load_fault_csv(canonical)
    except FileNotFoundError as exc:
        snap = AnomalySnapshot(
            fault_id=canonical,
            csv_file=_csv_str(_resolve_csv_path(canonical)),
            anomaly_index=-1,
            t2_statistic=0.0,
            t2_threshold=T2_THRESHOLD_DEMO,
            is_anomaly=False,
            sample_count=0,
            plain_explanation=f"Fault CSV for '{canonical}' was not found. {exc}",
        )
        return _to_dict(snap)

    anomaly_idx = _find_first_stable_anomaly(df)
    t2_value = 0.0
    if "t2_stat" in df.columns and anomaly_idx >= 0:
        t2_value = float(df.loc[anomaly_idx, "t2_stat"])

    sample_count = int(len(df))
    is_anom = anomaly_idx >= 0

    if is_anom:
        explanation = (
            f"Deterministic detector first sees {ANOMALY_RUN_LENGTH} consecutive anomalous "
            f"samples at row {anomaly_idx}. T2 statistic at that row is {t2_value:.2f}, "
            f"versus threshold {T2_THRESHOLD_DEMO}. Total rows analysed: {sample_count}."
        )
    else:
        explanation = (
            f"Deterministic detector did not flag a stable anomaly in {sample_count} rows of '{canonical}'. "
            "Either the run is normal or the precomputed columns are missing."
        )

    snap = AnomalySnapshot(
        fault_id=canonical,
        csv_file=_csv_str(csv_path),
        anomaly_index=anomaly_idx,
        t2_statistic=t2_value,
        t2_threshold=T2_THRESHOLD_DEMO,
        is_anomaly=is_anom,
        sample_count=sample_count,
        plain_explanation=explanation,
    )
    return _to_dict(snap)


def rank_contributing_variables(
    fault_id: Union[str, int] = "fault1",
    top_k: int = 6,
) -> Dict[str, Any]:
    """Rank top-K process variables driving the anomaly.

    Uses the precomputed per-variable T^2 contributions (`t2_<feature>`
    columns) when present. Falls back to comparing recent-window mean vs
    baseline mean when contributions are missing.
    """
    canonical = _normalize_fault_id(fault_id)
    try:
        df, csv_path = _load_fault_csv(canonical)
    except FileNotFoundError as exc:
        return {
            "fault_id": canonical,
            "csv_file": _csv_str(_resolve_csv_path(canonical)),
            "top_variables": [],
            "method": "none",
            "error": str(exc),
        }

    anomaly_idx = _find_first_stable_anomaly(df)
    if anomaly_idx < 0:
        return {
            "fault_id": canonical,
            "csv_file": _csv_str(csv_path),
            "top_variables": [],
            "method": "none",
            "note": "No stable anomaly found; nothing to rank.",
        }

    baseline = _load_baseline_stats()
    baseline_means: Dict[str, float] = {}
    if not baseline.empty:
        baseline_means = dict(zip(baseline["feature"], baseline["mean"]))

    t2_cols = [c for c in df.columns if c.startswith("t2_") and c != "t2_stat"]

    contributions: List[VariableContribution] = []
    method = ""

    if t2_cols:
        method = "per_variable_t2_contribution"
        ranked = (
            df.loc[anomaly_idx, t2_cols]
            .astype(float)
            .sort_values(ascending=False)
            .head(top_k)
        )
        recent_window = df.iloc[max(0, anomaly_idx - ANOMALY_RUN_LENGTH + 1): anomaly_idx + 1]
        for col, contrib in ranked.items():
            var_name = col[len("t2_"):]
            mean_change_pct = 0.0
            direction = "flat"
            if var_name in df.columns:
                recent_mean = float(recent_window[var_name].mean())
                base_mean = float(baseline_means.get(var_name, recent_mean))
                if base_mean != 0:
                    mean_change_pct = (recent_mean - base_mean) / base_mean * 100.0
                if mean_change_pct > 1:
                    direction = "increasing"
                elif mean_change_pct < -1:
                    direction = "decreasing"
            _tag = tag_for(var_name) or ""
            contributions.append(VariableContribution(
                variable=var_name,
                tag=_tag,
                label=label_with_tag(var_name),
                kind=("manipulated" if is_manipulated(var_name)
                      else ("measurement" if _tag else "")),
                t2_contribution=float(contrib),
                mean_change_pct=round(mean_change_pct, 3),
                direction=direction,
            ))
    else:
        # Fallback: rank by absolute % mean change vs baseline.
        method = "mean_shift_vs_baseline"
        candidate_vars = [c for c in df.columns
                          if c not in {"time", "t2_stat", "anomaly"}
                          and not c.startswith("t2_")]
        recent_window = df.iloc[max(0, anomaly_idx - ANOMALY_RUN_LENGTH + 1): anomaly_idx + 1]
        scored: List[Tuple[float, str, float, float]] = []
        for v in candidate_vars:
            if v not in recent_window.columns:
                continue
            recent_mean = float(recent_window[v].mean())
            base_mean = float(baseline_means.get(v, recent_mean))
            if base_mean == 0:
                continue
            pct = (recent_mean - base_mean) / base_mean * 100.0
            scored.append((abs(pct), v, pct, recent_mean))
        scored.sort(reverse=True)
        for _, v, pct, _recent_mean in scored[:top_k]:
            direction = "increasing" if pct > 1 else ("decreasing" if pct < -1 else "flat")
            _tag = tag_for(v) or ""
            contributions.append(VariableContribution(
                variable=v,
                tag=_tag,
                label=label_with_tag(v),
                kind=("manipulated" if is_manipulated(v)
                      else ("measurement" if _tag else "")),
                t2_contribution=0.0,
                mean_change_pct=round(pct, 3),
                direction=direction,
            ))

    return {
        "fault_id": canonical,
        "csv_file": _csv_str(csv_path),
        "anomaly_index": int(anomaly_idx),
        "method": method,
        "top_variables": [_to_dict(c) for c in contributions],
        "note": "Variables ranked from precomputed T2 contributions; mean-change context attached for interpretability.",
    }
