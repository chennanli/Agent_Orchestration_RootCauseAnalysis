"""Business-logic smoke tests for the TEP RCA agent tools.

These are the "operate the valves, check the trip signals" tests from
the GE-Power dynamic-simulation comparison: we don't just verify that
modules import — we verify that the *outputs* are right on a known
fixture.

Every assertion below is anchored to a TEP fixture that ships with the
repo:

  - `frontend/public/fault1.csv` — pre-computed Tennessee-Eastman fault
    1 run (cooling-water step). PCA T² and the per-variable contribution
    columns are baked in.
  - `backend/data/fault0.csv` — pre-computed normal-operation run.
  - `knowledge_base/` — Markdown copies of "Downs & Vogel 1993" and
    "TEP McAvoy 2003"; `search_process_knowledge` indexes these.

The tests are deterministic — no LLM calls, no live data, no NAT
runtime — so they run in <2 seconds on CI and don't need any API keys.

If a future refactor accidentally turns off PCA detection, drops the KB
index, or weakens the policy gate, one of these will go red on CI
before the bug ships.
"""
from __future__ import annotations

import pathlib
import sys

# Mirror the path bootstrap from test_smoke.py so the imports work
# whether pytest is run from REPO_ROOT, from backend/, or via the
# `testpaths = ["backend"]` setting in pyproject.toml.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.agent_tools.anomaly_tools import (
    inspect_anomaly_snapshot,
    rank_contributing_variables,
)
from backend.agent_tools.knowledge_tools import search_process_knowledge
from backend.agent_tools.policy_tools import check_advisory_policy


# ---------------------------------------------------------------------------
# PCA anomaly detection
# ---------------------------------------------------------------------------

def test_pca_detects_fault1():
    """Cooling-water step fault MUST be flagged.

    `fault1.csv` is the canonical IDV-4 cooling-water step from the
    Downs-Vogel 1993 spec. The pre-computed `anomaly` column should
    contain a stable run of `1`s, and `inspect_anomaly_snapshot` should
    surface that as `is_anomaly=True` with a positive `anomaly_index`
    and a T² value comfortably above the demo threshold (55.0).

    If this test goes red, somebody has broken the detection layer —
    `_find_first_stable_anomaly`, `ANOMALY_RUN_LENGTH`, or the bundled
    CSV itself.
    """
    snap = inspect_anomaly_snapshot("fault1")
    assert snap["is_anomaly"] is True, snap
    assert snap["anomaly_index"] >= 0, snap
    assert snap["t2_statistic"] > 55.0, (
        f"fault1 T² should exceed the demo threshold (55); got "
        f"{snap['t2_statistic']:.2f}"
    )
    # Reasonable lower bound on row count — guards against a truncated
    # CSV being shipped by mistake.
    assert snap["sample_count"] >= 100, snap


def test_pca_quiet_on_fault0():
    """Normal operation MUST NOT trigger a stable anomaly.

    `fault0.csv` is the steady-state base case (no disturbance). PCA
    should fail to find ANOMALY_RUN_LENGTH consecutive anomalous rows
    and return `is_anomaly=False`. A false positive here would mean
    the detector is too sensitive in production — operators would get
    chronic false alerts.
    """
    snap = inspect_anomaly_snapshot("fault0")
    assert snap["is_anomaly"] is False, snap
    assert snap["anomaly_index"] == -1, snap


def test_rank_contributing_variables_returns_top_k():
    """The agent's `rank_contributing_variables` tool should pick out
    the top-K most-deviating process variables for fault1.

    We check shape (a list of length K), not exact identity, because
    the precomputed T² contributions can shift slightly if the baseline
    stats are recomputed. But the *count* is contractual — the tool
    promises top_k items.
    """
    r = rank_contributing_variables("fault1", top_k=6)
    top = r.get("top_variables")
    assert isinstance(top, list), r
    assert len(top) == 6, f"expected exactly 6 ranked vars, got {len(top)}"
    # Each entry must at least carry a human-readable name field —
    # otherwise the agent's downstream prompt can't cite it.
    for item in top:
        assert isinstance(item, dict), item
        # The schema uses `label` (e.g., "XMV_3 (A feed load)") — that's
        # what the agent's downstream prompt cites. Tolerate `name` /
        # `feature_name` as benign-rename safety nets.
        name = item.get("label") or item.get("feature_name") or item.get("name")
        assert name and isinstance(name, str), item


# ---------------------------------------------------------------------------
# Knowledge-base retrieval
# ---------------------------------------------------------------------------

def test_search_process_knowledge_hits_downs_vogel():
    """Searching the KB for an obvious TEP query should return at least
    one excerpt — ideally citing Downs & Vogel since that paper IS the
    TEP spec.

    A green CI here means the KB is built, the keyword index is loaded,
    and `EnhancedKnowledgeManager.search_knowledge` is wired through to
    the agent tool. Red usually means somebody moved or renamed the
    `knowledge_base/` markdown.
    """
    result = search_process_knowledge("reactor pressure", max_results=3)
    excerpts = result.get("excerpts") or []
    assert excerpts, (
        f"expected at least one excerpt for 'reactor pressure'; got {result}"
    )
    # Every excerpt should at least name its source document — if not,
    # the agent has no way to cite anything in its final advisory.
    for e in excerpts:
        assert e.get("source_document"), e


def test_search_process_knowledge_empty_query_safe():
    """Empty queries must NOT crash — the agent occasionally fires them
    when the LLM produces a malformed Action input. The tool should
    return an empty result with a `note`, not a 500.
    """
    result = search_process_knowledge("", max_results=3)
    assert result.get("excerpts") == [], result


# ---------------------------------------------------------------------------
# Advisory policy gate
# ---------------------------------------------------------------------------

def test_policy_blocks_open_valve_command():
    """The policy gate exists to keep the agent advisory-only. A direct
    "open valve XMV_10 to 100%" must be flagged and rewritten.

    If this regresses, an LLM hallucination that proposes a control
    action would slip through to the operator UI. That's the failure
    mode we explicitly built `check_advisory_policy` to prevent.
    """
    unsafe = "Open valve XMV_10 to 100% immediately."
    r = check_advisory_policy(unsafe)
    assert r["is_advisory_safe"] is False, r
    assert r["forbidden_phrases_found"], r


def test_policy_passes_advisory_phrasing():
    """A well-phrased advisory ("recommend operator review", "consistent
    with...") should NOT trip the policy gate. A too-strict policy
    would force every advisory into a "manual review" queue and make
    the UI useless.

    Note we deliberately avoid the word "setpoint" — `_FORBIDDEN`
    patterns flag any "change setpoint" phrasing, and the safe-advisory
    rule of thumb is to talk about *symptoms and inspection* rather
    than *adjustments*.
    """
    safe = (
        "The reactor pressure XMEAS_7 shows a deviation consistent "
        "with a cooling-water loss; recommend operator inspection of "
        "the reactor cooling subsystem before any further action."
    )
    r = check_advisory_policy(safe)
    assert r["is_advisory_safe"] is True, r
    assert r["forbidden_phrases_found"] == [], r
    assert r["overclaims_found"] == [], r


def test_policy_blocks_overclaims():
    """Overclaim phrases must trip the gate. The agent works on a
    limited snapshot, not on the full plant history, so absolute
    certainty claims are unjustified.

    We use the exact wording `_OVERCLAIM_PATTERNS` lists — if anyone
    relaxes those patterns, this test goes red. (Substring testing
    here would be unreliable: the patterns are regex, and asserting on
    the literal phrase keeps the test deterministic and easy to debug.)
    """
    overclaim = (
        "This is definitely the root cause and the system is 100% safe "
        "to operate without further review."
    )
    r = check_advisory_policy(overclaim)
    assert r["is_advisory_safe"] is False, r
    assert r["overclaims_found"], r
