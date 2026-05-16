"""Time-Series Case Memory Tool — Matrix Profile-based historical analog retrieval.

Builds a historical archive from all fault CSVs and answers the question:
"Given the current fault trajectory, which past cases look most similar?"

Naming discipline (per project brief):
  - Call this "time-series case memory retrieval" or "pattern-based historical
    analog retrieval". Do NOT call it anomaly detection (the PCA/T² layer does that).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Optional stumpy import with graceful NumPy fallback
# ---------------------------------------------------------------------------
try:
    import stumpy  # type: ignore
    _STUMPY_AVAILABLE = True
except ImportError:
    _STUMPY_AVAILABLE = False

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent.parent
_PUBLIC_DATA = _ROOT / "frontend" / "public"
_BACKEND_DATA = _ROOT / "backend" / "data"
_ARCHIVE_PATH = _ROOT / "backend" / "data" / "embeddings" / "mp_archive.npz"

# Prefer public/ (has t2_stat); fall back to backend/data/
_CSV_SEARCH_PATHS = [_PUBLIC_DATA, _BACKEND_DATA]

# Known TEP fault family descriptions for annotation
_FAULT_PATTERNS: Dict[str, str] = {
    "fault0":  "normal steady-state operation",
    "fault1":  "A/C feed ratio variation (feed composition disturbance)",
    "fault2":  "B composition in feed (feed composition disturbance)",
    "fault3":  "D feed temperature step change",
    "fault4":  "reactor cooling water inlet temperature step",
    "fault5":  "condenser cooling water inlet temperature step",
    "fault6":  "A feed loss (feed loss family)",
    "fault7":  "C header pressure loss (feed loss family)",
    "fault8":  "A/B/C feed composition (random variation)",
    "fault9":  "D feed temperature (random variation)",
    "fault10": "C feed temperature (random variation)",
    "fault11": "reactor cooling water inlet temperature (random variation)",
    "fault12": "condenser cooling water inlet temperature (random variation)",
    "fault13": "reaction kinetics slow drift",
    "fault14": "reactor cooling water valve sticking",
    "fault15": "condenser cooling water valve sticking",
    "fault16": "unknown disturbance type 1",
    "fault17": "unknown disturbance type 2",
    "fault18": "unknown disturbance type 3",
    "fault19": "unknown disturbance type 4",
    "fault20": "unknown disturbance type 5",
}

# RCA note files that may be linked to historical cases
_RCA_DIRS = [
    _ROOT / "backend" / "LLM_RCA_Results",
    _ROOT / "RCA_Results",
]


# ---------------------------------------------------------------------------
# Column helpers
# ---------------------------------------------------------------------------
def _process_cols(df: pd.DataFrame) -> List[str]:
    """Return the 52 base process-variable column names (excludes t2_*, time, anomaly)."""
    return [
        c for c in df.columns
        if not c.startswith("t2_") and c not in ("time", "anomaly", "t2_stat")
    ]


def _load_fault_csv(fault_id: str) -> pd.DataFrame:
    """Load a fault CSV from the preferred search path."""
    fname = f"{fault_id}.csv"
    for base in _CSV_SEARCH_PATHS:
        p = base / fname
        if p.exists():
            return pd.read_csv(p)
    raise FileNotFoundError(f"CSV for {fault_id} not found in {_CSV_SEARCH_PATHS}")


# ---------------------------------------------------------------------------
# Archive build / load
# ---------------------------------------------------------------------------
def _build_archive() -> tuple[np.ndarray, list[tuple[str, int]]]:
    """Concatenate all fault CSVs into one archive matrix + index map."""
    fault_files = sorted(_PUBLIC_DATA.glob("fault*.csv"))
    if not fault_files:
        fault_files = sorted(_BACKEND_DATA.glob("fault*.csv"))

    matrices: list[np.ndarray] = []
    index_map: list[tuple[str, int]] = []

    ref_cols: Optional[List[str]] = None

    for csv_path in fault_files:
        fid = csv_path.stem  # e.g. "fault1"
        df = pd.read_csv(csv_path)
        proc = _process_cols(df)
        if ref_cols is None:
            ref_cols = proc
        # Align to reference columns (fill missing with col mean)
        data = df[ref_cols].fillna(df[ref_cols].mean()).values.astype(np.float64)
        matrices.append(data)
        for row_idx in range(len(data)):
            index_map.append((fid, row_idx))

    archive = np.vstack(matrices)  # shape: (N_total_rows, n_cols)
    return archive, index_map


def _load_archive() -> tuple[np.ndarray, list[tuple[str, int]]]:
    """Load cached archive or rebuild if missing."""
    if _ARCHIVE_PATH.exists():
        loaded = np.load(str(_ARCHIVE_PATH), allow_pickle=True)
        archive = loaded["archive"]
        index_map = list(loaded["index_map"])  # list of (fault_id, row_idx) tuples
        return archive, index_map

    archive, index_map = _build_archive()
    _ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        str(_ARCHIVE_PATH),
        archive=archive,
        index_map=np.array(index_map, dtype=object),
    )
    return archive, index_map


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------
def _znorm(x: np.ndarray) -> np.ndarray:
    """Z-normalise a 1-D array; return zeros if std ≈ 0."""
    std = x.std()
    if std < 1e-10:
        return np.zeros_like(x)
    return (x - x.mean()) / std


def _mass_distances(query_window: np.ndarray, archive_col: np.ndarray) -> np.ndarray:
    """
    Compute z-normalised sliding-window L2 distances from query_window to
    archive_col using stumpy.mass (if available) or the NumPy fallback.

    Returns distances array of length (len(archive_col) - len(query_window) + 1).
    """
    m = len(query_window)
    if _STUMPY_AVAILABLE:
        dists = stumpy.mass(query_window.astype(np.float64),
                            archive_col.astype(np.float64))
        # stumpy.mass may return NaN for very short sequences; fill with inf
        dists = np.where(np.isfinite(dists), dists, np.inf)
        return dists
    else:
        # NumPy fallback: z-normed sliding-window L2
        n = len(archive_col)
        n_windows = n - m + 1
        if n_windows <= 0:
            return np.array([np.inf])
        q_norm = _znorm(query_window)
        dists = np.empty(n_windows)
        for i in range(n_windows):
            w = archive_col[i: i + m]
            dists[i] = np.linalg.norm(q_norm - _znorm(w))
        return dists


# ---------------------------------------------------------------------------
# Interpretation heuristic
# ---------------------------------------------------------------------------
def _interpret_match(distance: float, n_distances: int) -> str:
    """
    Rank distance relative to archive size.
    Bottom 5%  → strong analog
    5-30%      → borderline match — SME inspection recommended
    >30%       → no strong historical analog (likely discord)
    """
    if not np.isfinite(distance) or n_distances == 0:
        return "No strong historical analog (likely discord)."
    # Use a simple absolute threshold (distances are z-normed L2)
    if distance < 1.5:
        return "Strong analog to a past trajectory — high confidence pattern match."
    elif distance < 3.5:
        return "Borderline match — SME inspection recommended."
    else:
        return "No strong historical analog (likely discord)."


# ---------------------------------------------------------------------------
# RCA note linker
# ---------------------------------------------------------------------------
def _linked_notes(fault_id: str) -> List[str]:
    """Return relative paths of any RCA markdown that mentions the fault_id."""
    links: list[str] = []
    tag = fault_id.replace("fault", "")
    for rca_dir in _RCA_DIRS:
        if not rca_dir.exists():
            continue
        for md in rca_dir.glob("*.md"):
            try:
                text = md.read_text(errors="ignore")
                if f"fault{tag}" in text.lower() or f"fault {tag}" in text.lower():
                    links.append(str(md.relative_to(_ROOT)))
            except Exception:
                pass
    return links[:3]  # cap at 3


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def match_historical_patterns(
    fault_id: str,
    variables: Optional[List[str]] = None,
    window: int = 30,
    top_k: int = 5,
) -> Dict[str, Any]:
    """Time-series case memory retrieval via Matrix Profile.

    Finds the *top_k* most similar historical windows in the fault archive
    to the first *window* rows of *fault_id*.

    Parameters
    ----------
    fault_id   : e.g. "fault1"
    variables  : subset of process variable names; None → use all 52
    window     : number of rows to use as the query window (default 30)
    top_k      : number of nearest-neighbor windows to return

    Returns
    -------
    dict with keys: query_window, method, variables_used, matches, interpretation
    """
    t0 = time.time()

    # --- Load query fault ---
    query_df = _load_fault_csv(fault_id)
    proc = _process_cols(query_df)

    # Resolve variables
    if variables:
        variables_used = [v for v in variables if v in proc]
        if not variables_used:
            variables_used = proc[:5]  # fallback to first 5
    else:
        variables_used = proc  # all 52

    # --- Load/build archive ---
    archive, index_map = _load_archive()

    # Determine column indices in the archive
    # Archive was built from the same set of proc cols (ref_cols in _build_archive)
    # We need to know which indices correspond to variables_used.
    # Re-read reference columns order from any fault CSV.
    _ref_df = pd.read_csv(next(iter(sorted(_PUBLIC_DATA.glob("fault*.csv")))))
    ref_cols = _process_cols(_ref_df)
    col_indices = [ref_cols.index(v) for v in variables_used if v in ref_cols]
    if not col_indices:
        col_indices = list(range(min(5, len(ref_cols))))
        variables_used = [ref_cols[i] for i in col_indices]

    # Extract query matrix
    query_mat = query_df[variables_used].fillna(0).values[:window].astype(np.float64)

    # --- Exclude windows that belong to the query fault (no self-match) ---
    query_rows = {i for i, (fid, _) in enumerate(index_map) if fid == fault_id}

    # --- Compute distances per variable, then average ---
    n_archive = archive.shape[0]
    n_windows = n_archive - window + 1
    if n_windows <= 0:
        return {
            "query_window": f"{fault_id} rows [0:{window}]",
            "method": "error",
            "variables_used": variables_used,
            "matches": [],
            "interpretation": "Archive too small for the requested window size.",
        }

    agg_distances = np.zeros(n_windows, dtype=np.float64)

    for ci in col_indices:
        q_col = query_mat[:, variables_used.index(ref_cols[ci])]
        arch_col = archive[:, ci]
        d = _mass_distances(q_col, arch_col)
        # Align length (stumpy may return slightly different length)
        min_len = min(len(d), n_windows)
        agg_distances[:min_len] += d[:min_len]

    agg_distances /= max(len(col_indices), 1)

    # Mask out query fault's own windows
    for qi in query_rows:
        if qi < n_windows:
            agg_distances[qi] = np.inf

    # --- Mask cross-fault-boundary windows (CRITICAL CORRECTNESS) ---
    # A window starting at archive index i spans rows [i, i+window). If
    # index_map[i].fault_id != index_map[i+window-1].fault_id, the window
    # straddles two fault files (which are independent runs) and the
    # distance is nonsense. Mark such windows as inf so they never rank.
    for i in range(n_windows):
        if index_map[i][0] != index_map[i + window - 1][0]:
            agg_distances[i] = np.inf

    # --- Top-K ---
    sorted_idx = np.argsort(agg_distances)
    matches: list[dict] = []
    seen_faults: set[str] = set()

    for idx in sorted_idx:
        if len(matches) >= top_k:
            break
        dist = float(agg_distances[idx])
        if not np.isfinite(dist):
            continue
        map_idx = min(idx, len(index_map) - 1)
        case_fid, case_row = index_map[map_idx]
        # Optionally deduplicate by fault (show each fault at most once)
        # For MVP, allow repeats to get top_k matches even from same fault
        matches.append(
            {
                "case_id": case_fid,
                "matched_range": [int(case_row), int(case_row + window)],
                "distance": round(dist, 4),
                "known_pattern": _FAULT_PATTERNS.get(case_fid, "unknown pattern"),
                "evidence_snippet": (
                    f"{case_fid} window [{case_row}:{case_row+window}]: "
                    f"distance={dist:.3f} on vars {variables_used[:3]}"
                ),
                "linked_notes": _linked_notes(case_fid),
            }
        )

    # Pick the best distance for interpretation
    best_dist = matches[0]["distance"] if matches else np.inf
    interp = _interpret_match(best_dist, n_windows)

    method = (
        "matrix_profile_ab_join" if _STUMPY_AVAILABLE else "fallback_normalized_l2"
    )

    return {
        "query_window": f"{fault_id} rows [0:{window}]",
        "method": method,
        "variables_used": variables_used,
        "matches": matches,
        "interpretation": interp,
        "latency_ms": round((time.time() - t0) * 1000, 1),
    }
