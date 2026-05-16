# AI Discovery Brief — Multi-Evidence Agentic RCA Workbench

**Status:** Experimental prototype, MVP evaluation complete.

## Research Signal

Three threads are converging in agentic AI for industrial knowledge work:
multi-agent **orchestration** (LangGraph, A2A), **hybrid retrieval** that mixes
governed wikis with field experience and time-series memory, and
**evaluation harnesses** that compare patterns rather than score a single model.
The open question this prototype tests: do these patterns produce more
grounded, more robust answers on a controlled industrial benchmark than the
single-ReAct-agent design we already had?

## Hypothesis

> **A LangGraph orchestrator that draws on four parallel evidence layers
> (governed wiki, field feedback, constraint catalog, time-series pattern
> memory) produces more grounded hypotheses than a single ReAct agent over
> keyword RAG, at acceptable latency overhead — and is more robust to LLM
> parsing brittleness.**

## Prototype Architecture

```
┌──────────────┐    ┌────────────────┐    ┌──────────────────┐
│ SignalAgent  │ →  │ EvidenceAgent  │ →  │ HypothesisAgent  │
│ (no LLM)     │    │ (LLM router)   │    │ (LLM)            │
└──────────────┘    └────────┬───────┘    └────────┬─────────┘
                             ▼                     ▼
                ┌─────────────────────────┐  ┌─────────────────┐
                │ 4 Evidence Layers       │  │ EvaluatorAgent  │
                │  • wiki  (KB RAG)       │  │ (policy +       │
                │  • field_feedback (RCA) │  │  grounding LLM) │
                │  • policy   (catalog)   │  └────────┬────────┘
                │  • pattern_memory (MP)  │           ▼
                └─────────────────────────┘  ┌─────────────────┐
                                             │ HumanReviewGate │
                                             │ (loop ≤3 or END)│
                                             └─────────────────┘
```

* **Signal**: deterministic anomaly snapshot + top contributing variables.
* **Evidence**: LLM picks which layers to query (cap 6 retrieval calls).
* **Hypothesis**: single LLM call writes 1–3 ranked root causes + draft advisory.
* **Evaluator**: policy regex check **plus** LLM grounding critic; sets
  `acceptable` and feedback.
* **HumanReviewGate**: loop back to Hypothesis with feedback (≤3 revisions),
  else flag `hitl_required` and END.

The 4th evidence layer is new: a **Matrix Profile** (stumpy `mass` AB-join)
historical analog retriever over all 21 fault CSVs (21 × 500 = 10,500 rows
archive), called **"time-series case memory retrieval"** — explicitly distinct
from the existing PCA / T² anomaly detector.

## Evaluation

Three golden cases (`fault1`, `fault4`, `fault6`), two modes. Real numbers
from `backend/evaluation/results/discovery_summary.json`:

| Metric | NAT baseline | LangGraph multi-evidence |
|---|---|---|
| grounded_ratio (mean, same-family critic) | **0.167** | **0.583** |
| grounded_ratio (held-out 8b judge, 4-way harness, n=5) | (not run) | **~0.2–0.4** (run-dependent; see note) |
| evidence layers used | wiki + field_feedback (fixed) | wiki + field_feedback + pattern_memory (dynamic, 3/3 each run) |
| revision_count (mean) | n/a | 0.33 (1 case revised once) |
| policy_pass | 100% | 100% |
| runtime (mean) | 1161 s | **9.4 s** |
| produced a reviewable advisory | 1 / 3 | **3 / 3** (2 used 429 fallback — see note) |
| strictly completed (no node errored) | 1 / 3 | 1 / 3 |

NAT baseline failed internally on 2 of 3 cases (one recursion-limit / one
ReAct parse failure inside `nvidia-nat-langchain`'s agent loop). LangGraph
produced a reviewable advisory on every case; on 2 of the 3, the
`HypothesisAgent` hit a NIM **429** mid-run and the run completed via the
fallback hypothesis (the orchestrator's bounded state machine handled the
rate-limit gracefully — exactly the kind of brittleness this design was
intended to absorb). Use the "produced a reviewable advisory" row to talk
about robustness; the "strictly completed" row is the cleaner apples-to-apples.

With a held-out smaller-model judge (`meta/llama-3.1-8b-instruct`, run
separately in `backend/evaluation/results/full_eval_summary.json` over 5
cases) the LangGraph grounded ratio sits in the 0.2–0.4 range depending
on the run (currently 0.23 on a 429-throttled re-run, 0.37 on the prior
fresh-quota run). The held-out judge is stricter than same-family
self-critique, which is the right direction for an honest number.

**Initial comparator run completed but its grounding score is not yet
apples-to-apples.** An earlier draft of this brief reported "LangGraph
0.37 vs LangChain ReAct 0.00" as a clean head-to-head — that claim has
been retracted because the harness was passing real evidence snippets to
LangGraph's grader and `[]` to the comparator's grader, so the comparator
was being scored against an empty evidence pack. The harness now collects
each comparator's actual tool outputs and feeds them to the judge
symmetrically. The first symmetric re-run was rate-limit-throttled (the
comparator only completed 1/5; that one case scored 0.4, comparable to
LangGraph's per-case range). A fresh-quota re-run is needed before any
head-to-head number is quoted externally.

## Findings

* **LangGraph orchestrator is ~123× faster wall-clock** (9.4 s vs 1161 s mean)
  on the cases that NAT could finish, mainly because it makes one bounded
  hypothesis call rather than open-ended ReAct iteration.
* **Robustness gap is the headline.** NAT failed internally on 2 of 3 cases.
  LangGraph produced a reviewable advisory on 3/3 cases (with 2 of those using
  the fallback hypothesis after a 429 mid-run). Strict completion is the same
  1/3 — the win is that the bounded state machine absorbed the rate-limit
  rather than crashing the whole investigation.
* **All 3 evidence layers fire on every run now.** The EvidenceAgent
  queried wiki + field_feedback + pattern_memory on each of 3 cases (mean
  evidence_hit_rate = 1.0). The earlier draft of this brief reported only
  2 layers because of a router key-name bug (`similar_faults` vs
  `matches`) — the bug was found in code review, fixed, and the eval
  re-run produced these higher numbers.
* **Pattern memory fires consistently and honestly reports discord.** All 3
  LangGraph runs queried the Matrix Profile layer. Top-1 distance is
  **4.58** on `fault1`, well above the 1.5 strong-analog threshold, so the
  matcher correctly reports *no strong analog* rather than fabricating a
  match. (An earlier draft reported top-1 = 3.6 — that match straddled
  two adjacent fault CSVs in the archive; the cross-boundary case is now
  masked out in `pattern_tools.py`.)
* **Grounding ratio 0.58 (same-family) → ~0.2–0.4 (held-out 8b judge).**
  The spread between the two judge configurations is itself informative —
  it is the standard same-family bias of LLM-as-judge, and the held-out
  number is the one to quote externally. The held-out figure is run-noisy:
  0.37 on the fresh-quota run, 0.23 on a 429-throttled re-run.
* **Comparator delta retracted, pending a fair re-run.** An earlier draft
  reported "LangGraph 0.37 vs ReAct 0.00" — that was an artifact of
  asymmetric grader inputs (real evidence to LangGraph, `[]` to the
  ReAct comparator). The harness is now symmetric. First symmetric run
  was throttled; the one comparator case that completed scored 0.4. A
  fresh-quota re-run is needed before quoting a head-to-head number.

## Reusable Capabilities Identified

* **Evidence-layer router** (4 layers, single entry point) — drop-in for
  any tool-using agent.
* **Time-series case memory tool** — Matrix Profile AB-join with a
  NumPy fallback for portable installs.
* **Hybrid governed-wiki retriever** — dense NIM embeddings + BM25 sparse
  retrieval fused with RRF, with keyword fallback.
* **LangGraph + Critic-as-node pattern** — composite policy + grounding
  evaluator with explicit `acceptable` flag and bounded revision loop.
* **A2A-style agent boundary** — local agent card + JSON-RPC `message/send`
  surface, including optional wiki-agent delegation.
* **Held-out judge harness** — separate smaller-model judge for stricter
  grounding estimates.
* **Evaluation harness** — comparing dissimilar agent frameworks on the
  same prompts with the same LLM-judge for grounding (fairness).

## Next Innovation Sprint

* UI surfacing for the discovery graph: node transitions, evidence-by-layer,
  hypothesis ranking, and evaluator feedback.
* Larger evaluation set with synthetic case generation, plus a clean fresh-quota
  re-run so the held-out judge has comparator data for a real head-to-head.
* GraphRAG-lite over variables, equipment, fault families, and knowledge chunks.
* MCP server exposing the read-only tools to external MCP clients.
* A2A hardening: auth, more granular streaming events, and broader client
  compatibility tests.
* Tracing / observability with OpenTelemetry-style spans for each graph node and
  retrieval call.

## Limitations

* Three golden discovery cases and five full-eval cases are smoke tests, not a
  statistical benchmark. The grounded_ratio delta is suggestive, not
  statistically meaningful.
* The held-out 8b judge is more honest than same-family self-critique, but it is
  still an LLM-as-judge. Human adjudication or a larger labeled claim-level set
  would be stronger.
* NAT's high failure rate may partly reflect prompt engineering rather
  than an inherent architectural weakness; a fairer comparison would tune
  NAT's ReAct system prompt to this task.
* The first version of `evaluate_full.py` graded LangGraph with retrieved
  evidence snippets but graded the LangChain ReAct comparator (and the NAT
  comparator) with an empty evidence list. That asymmetry produced an
  unfair "0.37 vs 0.00" delta in an earlier draft of this brief. The
  harness has since been changed to feed each comparator's actual tool
  outputs to the judge symmetrically. The symmetric re-run was rate-limit
  -throttled, so the published delta needs a fresh-quota repeat before
  citing externally.
* The A2A surface is a local research interface implemented against the public
  protocol shape. It is not production-hardened and does not include auth.
* TEP is a controlled manufacturing-like surrogate, not pharma data. The
  transferable value is the evidence architecture and evaluation pattern.
