"""Regression guard: tool output and committed sample runs must NOT leak
absolute home-directory paths (`/Users/...`, `/home/...`, `C:\\Users\\...`).

Why this exists
---------------
The reviewer found `csv_file` fields in `docs/sample_runs/*.json` and
`frontend/public/sample_runs/*.json` carrying
`"/Users/chennanMac_mini_SE/Desktop/LLM_Project/TEP_demo-main/..."` —
a public-repo leak of the developer's username + machine name + local
directory layout. Root cause was `inspect_anomaly_snapshot` serialising
`str(csv_path)` directly. Fixed by `_csv_str()` in
`backend/agent_tools/anomaly_tools.py` (repo-relative POSIX paths only).

These tests prevent regression on three surfaces:

  1. The tool function itself returns a repo-relative `csv_file`.
  2. The two committed sample-run JSONs don't carry a home path anywhere.
  3. `_csv_str()` falls back to bare filename for paths outside the repo
     (so a tempfile fixture in some future test can't accidentally leak).
"""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

import pytest

from backend.agent_tools import anomaly_tools
from backend.agent_tools.anomaly_tools import (
    _csv_str,
    inspect_anomaly_snapshot,
    rank_contributing_variables,
)


_REPO_ROOT = Path(anomaly_tools.__file__).resolve().parent.parent.parent

# Patterns that indicate an absolute home-style path. Matches:
#   /Users/foo/...
#   /home/foo/...
#   C:\Users\foo\... (case-insensitive)
_HOME_PATH_RE = re.compile(
    r"(/Users/[^/\s]+|/home/[^/\s]+|[A-Za-z]:[\\/]Users[\\/][^\\/\s]+)",
    re.IGNORECASE,
)


def _assert_no_home_path(payload: object, context: str) -> None:
    blob = json.dumps(payload) if not isinstance(payload, str) else payload
    m = _HOME_PATH_RE.search(blob)
    assert m is None, (
        f"{context}: tool output carried an absolute home-style path "
        f"({m.group(0)!r}). Use `_csv_str()` from anomaly_tools and keep "
        f"paths repo-relative."
    )


def test_inspect_anomaly_snapshot_csv_file_is_repo_relative():
    snap = inspect_anomaly_snapshot("fault1")
    csv_file = snap.get("csv_file", "")
    assert csv_file, "inspect_anomaly_snapshot must populate csv_file"
    # Repo-relative means it does not start with a path separator and does
    # not contain a Users/home segment.
    assert not csv_file.startswith("/"), (
        f"csv_file must be repo-relative, got absolute: {csv_file!r}"
    )
    _assert_no_home_path(snap, "inspect_anomaly_snapshot('fault1')")


def test_rank_contributing_variables_csv_file_is_repo_relative():
    out = rank_contributing_variables("fault1", top_k=3)
    csv_file = out.get("csv_file", "")
    assert csv_file, "rank_contributing_variables must populate csv_file"
    assert not csv_file.startswith("/"), (
        f"csv_file must be repo-relative, got absolute: {csv_file!r}"
    )
    _assert_no_home_path(out, "rank_contributing_variables('fault1')")


@pytest.mark.parametrize(
    "rel",
    [
        "docs/sample_runs/lg_run_fault4_sample.json",
        "frontend/public/sample_runs/lg_run_fault4_sample.json",
    ],
)
def test_committed_sample_runs_have_no_home_paths(rel: str):
    """The two tracked sample-run JSONs must be clean of home paths."""
    path = _REPO_ROOT / rel
    if not path.exists():
        pytest.skip(f"{rel} not present in this checkout")
    payload = json.loads(path.read_text())
    _assert_no_home_path(payload, rel)


def test_csv_str_strips_home_dir_for_out_of_repo_paths():
    """A path outside the repo should serialize to bare filename only —
    never to the absolute home-style path."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        rendered = _csv_str(tmp_path)
        _assert_no_home_path(rendered, "_csv_str(tempfile)")
        assert rendered == tmp_path.name, (
            f"out-of-repo path should fall back to filename only, got: {rendered!r}"
        )
    finally:
        tmp_path.unlink(missing_ok=True)


def test_csv_str_returns_repo_relative_posix_for_in_repo_paths():
    """An in-repo path returns a repo-relative POSIX string."""
    in_repo = _REPO_ROOT / "frontend" / "public" / "fault4.csv"
    if not in_repo.exists():
        pytest.skip("frontend/public/fault4.csv not present in checkout")
    rendered = _csv_str(in_repo)
    assert rendered == "frontend/public/fault4.csv", rendered
    _assert_no_home_path(rendered, "_csv_str(in_repo)")
