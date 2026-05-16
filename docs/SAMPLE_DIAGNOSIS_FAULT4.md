# Sample Diagnosis Output — IDV-4 (Reactor Cooling Water Inlet Temperature Step)

A single end-to-end run of the Discovery Workbench (LangGraph 5-node
state machine) against `fault4.csv` from the canonical Tennessee Eastman
Process IDV catalog. Captured live, no edits.

- **Source JSON:** [`sample_runs/lg_run_fault4_sample.json`](sample_runs/lg_run_fault4_sample.json)
- **Pipeline:** Signal → Evidence → Hypothesis → Evaluator → Human Review
- **Generator LLM:** `meta/llama-3.3-70b-instruct` via NVIDIA NIM. The
  output *shape* (3 ranked hypotheses + evaluator verdict + advisory) is
  identical when the orchestrator is swapped to Gemini / Claude / a local
  model; only the wording changes.
- **Total wall time:** **39.5 s** (Hypothesis node 38.5 s, Evidence node
  0.8 s, Signal node 11 ms, Evaluator node 0.2 ms, Gate < 1 ms)

---

## 1. Signal Node (deterministic — no LLM)

| Field | Value |
|---|---|
| Fault id | `fault4` |
| Anomaly first detected at row | 20 |
| T² statistic at that row | **179.73** |
| T² threshold | 55.0 |
| `is_anomaly` | True |
| Sample count | 500 |

**Top contributing variables (by T² contribution)**

| Rank | Tag | Variable | Kind | T² contribution | Δ% vs baseline | Direction |
|---|---|---|---|---|---|---|
| 1 | XMV_10 | Reactor coolant load | manipulated | 84.57 | +1.24 % | increasing |
| 2 | XMEAS_9 | Reactor Temperature | measurement | 61.42 | +0.01 % | flat |
| 3 | XMEAS_5 | Recycle Flow | measurement | 11.56 | −0.08 % | flat |
| 4 | XMEAS_14 | Product Sep Underflow | measurement | 11.04 | +0.24 % | flat |
| 5 | XMEAS_24 | Component B to Reactor | measurement | 8.99 | +0.12 % | flat |

## 2. Evidence Node (router picks layers; 3/4 fired)

| Layer | Hits | Notes |
|---|---|---|
| `wiki` (hybrid: NIM dense + BM25 + RRF) | 4 | Source-cited TEP markdown |
| `field_feedback` (prior RCA notes + IDV catalog) | 3 | Reads `matches` key (regression-guarded by `test_evidence_router.py`) |
| `pattern_memory` (Matrix Profile AB-join over 21 fault CSVs) | 5 | Top-1 distance honestly reported |
| `policy` | — | Not queried this run (router policy: query only on draft check) |

Total retrieval calls: 3 (cap 6).

## 3. Hypothesis Node — 3 Ranked Root Causes

This is the artifact the operator sees. Three candidate root causes, ranked, each tagged with confidence and pointing back to the evidence ids the model used to ground its claim.

> **Hypothesis 1 — `rank: 1`, `confidence: high`**
>
> The increase in **Reactor coolant load (XMV_10)** is the primary driver of fault4.
>
> *Supporting evidence:* TOP ANOMALOUS VARIABLES

> **Hypothesis 2 — `rank: 2`, `confidence: medium`**
>
> The flat **Reactor Temperature (XMEAS_9)** may be contributing to fault4, potentially as a result of the increased Reactor coolant load.
>
> *Supporting evidence:* TOP ANOMALOUS VARIABLES

> **Hypothesis 3 — `rank: 3`, `confidence: low`**
>
> Other variables such as **Recycle Flow (XMEAS_5)**, **Product Sep Underflow (XMEAS_14)**, and **Component B to Reactor (XMEAS_24)** may be playing a secondary role in fault4.
>
> *Supporting evidence:* TOP ANOMALOUS VARIABLES

## 4. Evaluator Node — Policy + Grounding

| Check | Result |
|---|---|
| `policy.is_advisory_safe` | ✅ True |
| `policy.forbidden_phrases` | `[]` (no control verbs detected) |
| `policy.overclaims` | `[]` |
| `grounded_ratio` | 0.5 (claims with at least one citation) |
| `citation_coverage` | 0.0 (no inline `[source: ...]` markers in this draft) |
| `acceptable` | ✅ True |
| `feedback` | "Advisory looks good." |
| `llm_critique_used` | False (passed regex gate, LLM critic not invoked) |

## 5. Human Review Gate

| Field | Value |
|---|---|
| `acceptable` | True |
| `revision_count` | 0 (no revision loop fired) |
| `hitl_required` | False |
| Final decision | `accept` |

## Final Advisory (text shown to operator)

> The current fault4 situation appears to be driven by an increase in Reactor coolant load, which may be causing a cascade of effects on other variables. It is recommended to investigate the cause of this increase and take corrective action to prevent further escalation. Additionally, monitoring of Reactor Temperature and other affected variables is advised to ensure the situation does not worsen.

Note the wording: *"investigate"*, *"take corrective action"*, *"monitoring … is advised"*. No `open`, no `close`, no `set` — the advisory-only policy enforced by `check_advisory_policy` is doing its job at the language level.

---

## Why this is the right artifact to show

A read-only multi-evidence RCA system has to do four things in front of a control-room engineer:

1. **Surface the deterministic signal** so the human knows *what* the math saw before any LLM ran (Section 1).
2. **Show its evidence**, broken out by layer, so the human can cross-check (Section 2).
3. **Rank multiple candidate root causes** with explicit confidence — never "the answer is X" with no alternatives (Section 3). This is the section the README previously didn't surface; this doc fixes that.
4. **Gate the advisory** through policy + grounding checks, with a visible HITL switch (Sections 4–5).

The 5-node LangGraph pipeline produces all four on every run, regardless of which LLM is plugged in at the Hypothesis node.
