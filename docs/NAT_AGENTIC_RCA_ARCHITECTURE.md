# NAT Agentic RCA Architecture

## Purpose

The TEP NAT agentic RCA workflow upgrades the Tennessee Eastman Process demo
from a fixed RAG / multi-LLM pipeline into a read-only agent orchestration:
deterministic anomaly detection produces an event, a NeMo Agent Toolkit
(NAT) workflow chooses which diagnostic tools to call, and the system
returns an operator advisory with evidence, citations, and a tool trace
that can be audited and evaluated. The agent never controls the process.

## Current vs. Upgraded Architecture

```
Current:
  TEP simulation
    -> PCA / T2 anomaly detection
    -> fixed knowledge retrieval (single keyword pass)
    -> parallel Claude / Gemini / LMStudio analysis
    -> operator-facing RCA text

Upgraded:
  TEP simulation OR sample fault CSV
    -> deterministic anomaly event (same PCA / T2 layer, untouched)
    -> NAT RCA workflow
         -> inspect_anomaly_snapshot  (read-only)
         -> rank_contributing_variables (read-only)
         -> search_process_knowledge  (read-only, keyword)
         -> get_sensor_window         (read-only)
         -> find_similar_faults       (read-only)
         -> check_advisory_policy     (read-only, wording check)
    -> operator advisory (evidence + citations + safety notice)
    -> persisted run trace + evaluation result
```

The upgrade is *additive*. The legacy multi-LLM RCA path in
`backend/multi_llm_client.py` is unchanged and still ships in the demo.

## Tool Table

| Tool                          | Reads                                              | Returns                                                                 | Why an agent calls it                                                | Safety boundary                          |
|-------------------------------|----------------------------------------------------|-------------------------------------------------------------------------|----------------------------------------------------------------------|------------------------------------------|
| `inspect_anomaly_snapshot`    | `frontend/public/faultN.csv` (preferred), `backend/data/faultN.csv` | T^2 statistic, threshold, anomaly index, sample count, plain explanation | Anchor the run on the deterministic event before any LLM speculation | Read-only; never triggers a callback     |
| `rank_contributing_variables` | Same fault CSV + `backend/stats/features_mean_std.csv` | Top-K variables with T^2 contribution and mean-shift vs. baseline      | Convert raw T^2 numbers into a short, ranked, human-readable list    | Read-only; no model retraining           |
| `search_process_knowledge`    | `RAG/converted_markdown/*.md`                      | Source-cited excerpts (document, section, score, text)                  | Ground every claim in the local TEP knowledge base                   | Read-only; keyword-only, not vector      |
| `get_sensor_window`           | Fault CSV + baseline stats                         | Last-N values, mean, std, baseline mean / std, % change                 | Verify a hypothesis against a specific sensor                        | Read-only; never writes                  |
| `find_similar_faults`         | Canonical IDV fault catalog + `backend/LLM_RCA_Results/`, `RCA_Results/` | Ranked matches with fault family + evidence snippet           | Provide a "have we seen this before?" view                           | Read-only; keyword similarity, demo only |
| `check_advisory_policy`       | Draft answer text                                  | `is_advisory_safe`, forbidden phrases, overclaims, suggestions          | Self-check the wording before showing the operator                   | Read-only; gates wording, not control    |

## Evaluation

Evaluation is workflow-level (did the agent call the right tools, gather
the right evidence, cite sources, and avoid unsafe wording?), not pure
retrieval-quality. Run it with:

```bash
python backend/evaluation/evaluate_nat_rca.py --tools-only   # no NAT needed
python backend/evaluation/evaluate_nat_rca.py --run-agent    # NAT + key
```

Per-case metrics:

| Metric                          | Definition                                                            |
|---------------------------------|-----------------------------------------------------------------------|
| `tool_availability`             | Every tool ran without an error key in its output                     |
| `required_tools_hit`            | All `must_use_tools` from the golden case were actually called        |
| `evidence_variable_hit_rate`    | Fraction of `expected_evidence_variables` that show up in top ranks   |
| `forbidden_phrase_count`        | Count of `must_not_say` phrases that appear in the final answer text  |
| `source_citation_present`       | Run cited at least one source document                                |
| `trajectory_available`          | Run produced a non-empty tool trace                                   |
| `policy_check_passed`           | `check_advisory_policy.is_advisory_safe` was True                     |
| `latency_seconds`               | Wall-clock duration                                                   |

Rolled-up summary lives at `backend/evaluation/results/summary.json` and the
per-case detail at `backend/evaluation/results/cases.jsonl`.

## What this is NOT

* **Not** autonomous process control. No tool can change a setpoint, open
  or close a valve, or trip equipment.
* **Not** deployed APC or RTO. The PCA / T^2 layer is the same demo-grade
  detector that ships with the original TEP demo.
* **Not** a certified safety system. The advisory always ends with
  "requires SME review" and the runner refuses to omit the safety notice.
* **Not** proof of grid-domain expertise. TEP is a benchmark chemical
  process, not a power grid. This project demonstrates AI architecture and
  governance, not power-system engineering.

## How this maps to the GE Vernova AI/ML Director profile

* **Thought leadership:** the project takes a public benchmark process and
  separates the layers (simulation, anomaly detection, retrieval, agent
  orchestration, evaluation, policy) so non-ML executives can see what each
  layer does and what it does not do.
* **AI strategy aligned to business:** the upgrade is framed as an
  *advisory-only* read-only workflow. That is the only framing that fits a
  safety-critical industrial customer in a defensible way; the architecture
  reflects that decision.
* **Scalable / integrated workflows:** NAT functions are reused by the
  runner, the evaluation script, and (optionally) the UI. Adding a new tool
  is a single Python function plus one entry in the workflow YAML.
* **MLOps / evaluation mindset:** golden cases, per-case metrics, summary
  rollup, and policy-check pass rate are first-class outputs of the run,
  not an afterthought.
* **Industrial automation safety boundary:** every tool docstring,
  `check_advisory_policy`, and the runner's `safety_notice` reinforce that
  the agent does not control the process.
* **Communication across customers / sales / C-level:** the architecture
  doc, blog, and demo script are written for non-ML readers and avoid
  unsupported claims, certification language, or invented accuracy gains.
