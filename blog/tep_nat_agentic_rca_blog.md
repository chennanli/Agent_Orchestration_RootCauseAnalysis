# From Industrial RAG Demo to Agentic RCA: A Read-Only NeMo Agent Toolkit Workflow for Tennessee Eastman Process Fault Diagnosis

**Author:** chennanli  ·  **Project:** TEP Agentic RCA Workbench
**Status:** Public portfolio demo. Not a production system.

## 1. The business problem

Industrial customers, executives, and even data-science teams routinely
confuse five very different things:

* **Process simulation** ("we have a model of the plant"),
* **Advanced Process Control / Real-Time Optimization** ("we close the loop"),
* **Data science** ("we look at sensor history"),
* **Generative AI / RAG** ("we let an LLM read the manuals"), and
* **Agentic AI** ("we let an LLM choose what to do next").

When all five are mashed into a single demo, conversations devolve into
"will this AI run my plant?" — a question nobody on the vendor side wants
to answer "yes" to, and nobody on the customer side wants to hear "no" to
without a much more careful explanation.

This project tries to do that careful explanation in code. It takes the
public Tennessee Eastman Process benchmark (TEP) and separates the
layers into pieces a non-ML reader can poke at. The point is not to ship
an industrial product; the point is to make the layers — and the safety
boundary between them — concrete.

## 2. Baseline: what the original TEP demo already does

The repository starts from a fairly capable demo:

* A **Tennessee Eastman simulation** producing 52 measured / manipulated
  variables.
* A **PCA / Hotelling T^2 anomaly detector** that flags when the joint
  process state moves outside its trained operating envelope.
* A **fixed RAG pipeline** that pulls keyword-matched excerpts from a
  Markdown knowledge base under `RAG/converted_markdown/`.
* A **multi-LLM RCA layer** (Claude / Gemini / a local model) that produces
  parallel root-cause-analysis text.

This is enough to be useful. It is not, however, agentic. The diagnosis
path is fixed: every anomaly produces the same shape of retrieval and the
same shape of prompt. The LLM never decides to look at one more sensor or
to compare against a similar past fault. The repo's own
`AGENTIC_UPGRADE.md` admits this.

## 3. Why fixed RAG is not enough

For a chemical-process diagnosis, "fixed retrieval then explain" misses
several things a human investigator would do:

* **Anchor on the deterministic signal.** The PCA / T^2 layer already
  knows when the process changed, where, and which variables contributed
  most. A fixed-RAG path tends to ignore that and re-explain the world
  from text.
* **Ask "what does this look like?" against past investigations.** The
  same fault family shows up across many runs.
* **Look at one sensor in detail when the rank list points at it.** Mean,
  std, baseline drift over the last twenty samples is often the difference
  between "this is the actual cause" and "this is a downstream effect".
* **Self-check the wording.** A diagnosis that ends with "open the cooling
  water valve" is unsafe regardless of how good the upstream reasoning is.

A fixed RAG pipeline cannot do these things, because nobody ever asked it
to. An agent can.

## 4. The NAT upgrade

The upgrade replaces the diagnosis layer with a NeMo Agent Toolkit (NAT)
workflow that has six **read-only** tools:

| Tool                          | What it does                                           |
|-------------------------------|--------------------------------------------------------|
| `inspect_anomaly_snapshot`    | Reads the deterministic T^2 state from the fault CSV   |
| `rank_contributing_variables` | Returns the top contributing process variables         |
| `search_process_knowledge`    | Keyword search over the local TEP knowledge base       |
| `get_sensor_window`           | Returns a windowed slice of one sensor                 |
| `find_similar_faults`         | Keyword similarity over past faults and IDV catalog    |
| `check_advisory_policy`       | Inspects a draft advisory for unsafe wording           |

The NAT workflow YAML wires the tools to a `react_agent` and an LLM:

```yaml
workflow:
  _type: react_agent
  llm_name: nim_llm
  tool_names:
    - inspect_anomaly_snapshot
    - rank_contributing_variables
    - search_process_knowledge
    - get_sensor_window
    - find_similar_faults
    - check_advisory_policy
```

Three things are deliberately not in this list:

1. Anything that writes to the process.
2. Anything that calls the simulator's setpoint / valve interface.
3. Anything that emits deployment-certification marketing wording. The policy
   tool actively flags those overclaims.

The runner (`backend/nat_runner.py`) supports two modes: a NAT mode that
talks to the real NAT runtime when `nvidia-nat` is installed, and a
`--tools-only` mode that runs the same tools in a deterministic order so
the project still demoes when NAT is missing or no API key is available.

## 5. Evaluation

Evaluation is workflow-level, not generic-RAG-quality. The
`backend/evaluation/golden_cases.jsonl` file ships seven small cases
covering common TEP IDV faults. Each case specifies:

* `expected_fault_family`,
* `expected_evidence_variables`,
* `must_use_tools`, and
* `must_not_say` (forbidden phrases).

The evaluator computes:

* **tool availability** — did every tool actually run?
* **required tools hit** — were the required tools called at all?
* **evidence variable hit rate** — did the run surface the right variables?
* **forbidden phrase count** — did anything unsafe slip into the output?
* **source citation present** — did the run cite a knowledge document?
* **policy check pass rate** — did `check_advisory_policy` return safe?
* **trajectory available** — did the run produce a tool trace?
* **latency** — wall-clock seconds.

In the current `--tools-only` baseline, the run hits 100% on tool
availability, required tools, policy check, and trajectory; ~71% on
evidence-variable recall; zero forbidden phrases; ~86% source citation
present; ~0.05s average latency on a laptop. Those numbers are not the
point of the project — the *fact that the evaluator exists* is.

## 6. Safety boundary

The hard rules:

* The agent does not change setpoints.
* The agent does not open or close valves.
* The agent does not start, stop, or trip equipment.
* The agent does not certify operating safety or assert root-cause certainty.
* Every advisory ends with "requires SME review".

`check_advisory_policy` enforces those constraints in code. The system
prompt of the workflow YAML restates them in natural language. The runner
appends them as a constant `safety_notice` field. None of these belt-and-
suspenders checks individually proves the system is safe — together they
make it very hard to accidentally ship a recommendation that crosses the
line.

## 7. Interview / leadership takeaway

The honest framing of this project, end-to-end, is:

> I started from a fixed industrial RAG demo because that was the clearest
> way to help customers and executives understand the layers: simulation,
> anomaly detection, retrieval, and LLM explanation. Then I upgraded the
> diagnosis layer into a NeMo Agent Toolkit workflow. The agent does not
> control the process. It chooses read-only diagnostic tools, gathers
> evidence, checks its advisory against safety language, and produces a
> traceable RCA for human review. The value is not the LLM — it is making
> industrial AI understandable, testable, and governable.

That framing maps cleanly to what an AI/ML director role for a heavy-
industry vendor actually has to do every week: keep the customer's
imagination ahead of the vendor's marketing, and the vendor's safety
posture ahead of the customer's imagination.
