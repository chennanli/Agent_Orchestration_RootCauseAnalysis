"""Freeze the last N rows of the FastAPI live buffer into a fault-shaped CSV.

The agent tools in `backend.agent_tools.anomaly_tools` already know how to
read 107-column TEP fault CSVs (52 friendly-named sensors + per-variable t2
contributions + an `anomaly` flag + a `t2_stat`). This module produces one
of those, so the agent can run on live data without any tool changes.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Iterable, List, Mapping, Optional

import numpy as np
import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SNAPSHOTS_DIR = _REPO_ROOT / "backend" / "diagnostics" / "snapshots"
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def _utc_compact() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%S")


def _columns_from_fault1() -> List[str]:
    """Return the canonical 107-column header used by the existing CSVs."""
    fault1 = _REPO_ROOT / "frontend" / "public" / "fault1.csv"
    return pd.read_csv(fault1, nrows=0).columns.tolist()


def snapshot_live_buffer(
    rows: Iterable[Mapping[str, float]],
    *,
    fault_id: Optional[str] = None,
    extra_t2_threshold: float = 11.0,
) -> str:
    """Write a fault-shaped CSV from the most recent buffered rows.

    Parameters
    ----------
    rows : iterable of dict
        Sensor rows in chronological order. Each row maps the canonical
        friendly column name (e.g. "Reactor Pressure") to a float. Missing
        columns are filled with NaN.
    fault_id : str, optional
        Override the generated id. By default a `live_<utc-ts>` id is
        generated. The CSV is written to
        `backend/diagnostics/snapshots/<fault_id>.csv`.
    extra_t2_threshold : float
        Threshold used to fill the `anomaly` 0/1 column when no PCA result is
        available row-by-row. The existing fault CSVs are pre-computed; for a
        live snapshot we approximate by flagging rows whose `t2_stat` exceeds
        this value. Pure post-hoc; agent tools only use it as a coarse cue.

    Returns
    -------
    str
        The `fault_id` written, e.g. `"live_20260512T012530"`.
    """
    canonical = _columns_from_fault1()
    rows = list(rows)
    if not rows:
        raise ValueError("snapshot_live_buffer: rows is empty")
    if extra_t2_threshold <= 0.0:
        raise ValueError(
            "snapshot_live_buffer: extra_t2_threshold must be positive "
            "(t2_stat is always >= 0, so a non-positive threshold would "
            "flag every row as anomalous)"
        )

    df = pd.DataFrame(rows)
    df["time"] = list(range(len(df)))

    for col in canonical:
        if col not in df.columns:
            df[col] = np.nan

    sensor_cols = [
        c for c in canonical
        if c not in {"time", "anomaly", "t2_stat"} and not c.startswith("t2_")
    ]
    sensor_df = df[sensor_cols].astype(float)
    means = sensor_df.mean(numeric_only=True)
    stds = sensor_df.std(numeric_only=True).replace(0.0, 1.0)
    z = (sensor_df - means) / stds
    df["t2_stat"] = (z.pow(2).sum(axis=1)).fillna(0.0)
    df["anomaly"] = (df["t2_stat"] > extra_t2_threshold).astype(int)

    for col in canonical:
        if col.startswith("t2_") and col != "t2_stat":
            base = col[len("t2_"):]
            if base in z.columns:
                df[col] = z[base].pow(2).fillna(0.0)
            else:
                df[col] = 0.0

    df = df[canonical]

    fault_id = fault_id or f"live_{_utc_compact()}"
    out = SNAPSHOTS_DIR / f"{fault_id}.csv"
    df.to_csv(out, index=False)
    return fault_id
