# ⚡ TEP Live Copilot · Agentic Discovery Workbench

> An industrial root-cause-analysis (RCA) prototype on the Tennessee Eastman Process — a published **first-principles chemical-plant model** used here as a safe surrogate for fine-chemical / pharma / polymer / refining / fab plants. Explores agentic AI patterns: multi-agent orchestration, hybrid retrieval, time-series memory, A2A & MCP inter-agent boundaries, and a held-out evaluation harness.

[![CI](https://github.com/chennanli/Agent_Orchestration_RootCauseAnalysis/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/chennanli/Agent_Orchestration_RootCauseAnalysis/actions/workflows/ci.yml)
[![Release](https://github.com/chennanli/Agent_Orchestration_RootCauseAnalysis/actions/workflows/release.yml/badge.svg)](https://github.com/chennanli/Agent_Orchestration_RootCauseAnalysis/actions/workflows/release.yml)

![python 3.11–3.13](https://img.shields.io/badge/python-3.11%E2%80%933.13-3776ab)
![LangGraph 1.x](https://img.shields.io/badge/LangGraph-1.x-a371f7)
![LangChain 1.x](https://img.shields.io/badge/LangChain-1.x-1c3c3c)
![NVIDIA NeMo Agent Toolkit 1.x · tested 1.6](https://img.shields.io/badge/NVIDIA%20NAT-1.x%20%C2%B7%20tested%201.6-76b900)
![NIM](https://img.shields.io/badge/NVIDIA%20NIM-llama--3.3--70b%20%C2%B7%20llama--3.1--8b%20%C2%B7%20nv--embedqa--e5--v5-76b900)
![A2A](https://img.shields.io/badge/A2A--style-JSON--RPC%20%2B%20agent%20card-2563eb)
![MCP](https://img.shields.io/badge/MCP-stdio%20%2B%20sse-7c3aed)
![ChromaDB 1.x](https://img.shields.io/badge/ChromaDB-1.x-ff6f00)
![BM25](https://img.shields.io/badge/BM25-rank__bm25-555)
![Matrix Profile](https://img.shields.io/badge/Matrix%20Profile-stumpy-006400)
![FastAPI](https://img.shields.io/badge/FastAPI-009688)
![React + Mantine + SSE](https://img.shields.io/badge/React%20%2B%20Mantine%20%2B%20SSE-61dafb)
![Docker Compose](https://img.shields.io/badge/Docker-compose-2496ed)
![safety: advisory only](https://img.shields.io/badge/safety-advisory%20only-orange)

![TEP Live Copilot — full run, live T² spike on the left, NAT agent trace + XMV/XMEAS-specific advisory on the right](docs/assets/tep_live_copilot_final.png)

*Real run, captured live: IDV-4 + IDV-6 disturbances injected into the Fortran simulator; PCA T² climbed past threshold; the agent walked through six tool calls in ReAct order; the final advisory called out **XMV_6 (Purge valve)** and **XMEAS_25 (Component C to Reactor)** by tag — specific variable tags, bounded by SME review (the advisory ends with the policy-enforced "requires SME review" line).*

---

> 📖 **Long-form write-up:** [From industrial RAG to a bounded LLM agent — a root-cause-analysis workbench](https://chennanli.github.io/posts/04-tep-agentic-rca-workbench/) — design rationale, the academic baseline this builds on (Prof. Can Li's FaultExplainer, [arXiv:2412.14492](https://arxiv.org/abs/2412.14492)), the three changes I made on top of it, and the bounded LangGraph workflow that followed.

---

## What this is

### About the Tennessee Eastman Process

The **Tennessee Eastman Process (TEP)** is a first-principles chemical-plant simulation published by Downs & Vogel (Eastman Chemical, 1993) and still the de-facto benchmark for industrial process monitoring and fault diagnosis. It is a Fortran solver of the mass, energy, and component balances of a complete continuous plant — **five interconnected unit operations** (reactor, condenser, vapor–liquid separator, product stripper, recycle compressor), **8 chemical species (A–H)**, **41 measured variables (XMEAS-1 … XMEAS-41)**, **12 manipulated variables (XMV-1 … XMV-12)**, and **20 canonical disturbance scenarios (IDV-1 … IDV-20)** ranging from feed-composition step changes to slow drifts in heat-exchanger fouling.

Because the dynamics come from real reaction kinetics and process physics rather than synthetic data, TEP is widely used as a stand-in for any regulated continuous- or batch-process plant. The patterns this repo explores — continuous PCA / T² anomaly detection, multi-evidence retrieval, multi-step diagnostic reasoning, advisory-only safety boundaries, held-out evaluation — transfer cleanly to:

- **Fine-chemical manufacturing** (continuous reactors, distillation trains, recycle loops)
- **Pharma drug-substance and drug-product plants** (API synthesis, crystallization, formulation lines under GxP constraints)
- **Polymer production** (continuous polymerization, devolatilization, extrusion)
- **Oil-and-gas refining and petrochemicals** (FCC units, hydrotreaters, separators)
- **Semiconductor fabs** (CVD / etch / CMP — different physics, same need for explainable RCA from sensor streams)

Anywhere there are PI / Historian tags, an MES, a recipe of unit operations, and a control room that wants to know *why* the trend is moving, **this prototype explores the kind of architecture you'd build**. Production hardening — historian connectors, AuthN/AuthZ, audit log, 21 CFR Part 11 / GAMP 5 evidence, change control — is out of scope and would sit on top of what's here.

### The prototype

A single-page web app that pairs a **live Fortran simulation** of the Tennessee Eastman Process with **two parallel agentic RCA paths** over the same deterministic substrate:

- **Live Copilot** (`/` tab) — a single NVIDIA NeMo Agent Toolkit (NAT) ReAct agent with six read-only tools. The original demo path; preserved end-to-end for honest comparison.
- **Discovery Workbench** (`/discovery` tab) — a 5-node LangGraph state machine (Signal → Evidence → Hypothesis → Evaluator → Human Review) that mixes four parallel evidence layers and is also reachable through an A2A-style JSON-RPC surface.

Both paths share the same deterministic substrate (Fortran sim, PCA/T² detector, 6 read-only tools, governed wiki) and the same held-out evaluation harness. The LLM is only called when the user explicitly initiates a diagnosis or a follow-up question; PCA anomaly detection runs continuously and costs nothing.

> **What this is NOT:** autonomous process control, APC, RTO, or a certified safety system. Read-only tools by construction; every advisory ends with *"requires SME review"*.

---

## Tech stack

Each row is a concrete component wired into the prototype, not a list of words.

| Technology | Role in this project | Code |
|---|---|---|
| **LangGraph** state machine | 5-node bounded orchestrator with critic-as-node + revision loop + HITL gate | `backend/langgraph_rca.py` |
| **LangChain** message types & tool abstractions | Underlying primitives for both LangGraph and the ReAct comparator | `backend/agent_tools/`, `backend/evaluation/evaluate_full.py` |
| **NVIDIA NeMo Agent Toolkit (NAT)** | Baseline ReAct agent with 6 read-only tools — the original single-agent path, kept end-to-end | `backend/nat_runner.py`, `backend/nat_workflows/tep_rca_workflow.yml` |
| **A2A-style JSON-RPC + agent card** | Inter-agent boundary: agent card at `/.well-known/agent-card.json`, `message/send` at `/a2a`, SSE at `/a2a/stream`. LangGraph can optionally delegate wiki retrieval through this boundary | `backend/a2a_router.py`, `docs/A2A_INTEGRATION.md` |
| **Model Context Protocol (MCP)** | LLM host ↔ tool-server boundary; 11 read-only tools (6 deterministic + 4 evidence-layer wrappers + LangGraph orchestrator) exposed over stdio / SSE / streamable-http. Any MCP-aware host (Claude Desktop, Cline, Cursor) can drive the toolkit | `backend/mcp_server.py`, `docs/MCP_INTEGRATION.md` |
| **ChromaDB + NVIDIA NIM embeddings** (`nv-embedqa-e5-v5`, 1024-d) | Dense vector retrieval over the governed wiki | `backend/agent_tools/vector_knowledge.py` |
| **BM25** (`rank_bm25`) | Sparse keyword retrieval over the same corpus | `backend/agent_tools/vector_knowledge.py` |
| **Reciprocal Rank Fusion (RRF)** | Hybrid retrieval fusing dense + sparse. **Recall@5 = 0.857, MRR = 1.000** on a smoke-test set of **7 hand-curated queries** (`backend/evaluation/results/retrieval_summary.json`). Not a benchmark; suggestive of fusion quality, not statistically meaningful at this scale. | `backend/agent_tools/vector_knowledge.py:hybrid_search` |
| **Matrix Profile** (`stumpy`, AB-join) | Time-series case memory over all 21 fault CSVs; cross-fault-boundary masking; returns top-K analog windows with linked RCA notes | `backend/agent_tools/pattern_tools.py` |
| **Held-out LLM-as-judge** | A smaller different-family model (`meta/llama-3.1-8b-instruct`) grades the grounding of advisories produced by the 70b generator — stricter than same-family self-critique | `backend/evaluation/judge.py` |
| **Synthetic case generator** | LLM-generated diagnostic prompts conditioned on each fault's family + top variables; used to extend the golden set beyond hand-curated cases | `backend/evaluation/synth_cases.py` |
| **4-way comparative harness** | Runs `tools_only` / `nat_react` / `langchain_react` / `langgraph_multi` over the same prompts with the same held-out judge, for apples-to-apples eval | `backend/evaluation/evaluate_full.py` |
| **PCA + Hotelling's T²** detector | Deterministic anomaly detection — pure NumPy, no LLM cost. Arms the diagnose-now flow | `backend/app.py` (continuous), `backend/agent_tools/anomaly_tools.py` (inspect) |
| **FastAPI + Server-Sent Events** | HTTP + SSE backend; per-node state streamed live to the React UI as the LangGraph orchestrator runs | `backend/app.py`, `backend/nat_api_live.py`, `backend/langgraph_api.py` |
| **React + Mantine + Vite** | Two-tab industrial-copilot UI. `/discovery` page renders the live LangGraph pipeline + evidence-by-layer + hypothesis ranking + evaluator verdict | `frontend/src/pages/{LiveCopilotPage,DiscoveryPage}.tsx` |
| **TEP Fortran simulator** (Downs & Vogel 1993, `tep2py`) | 50× real-time chemical-process simulation as the safe industrial surrogate. Compiled `temain_mod.so` shipped in-repo | `backend/simulation/`, `unified_console.py` |
| **NVIDIA NIM** (hosted) | `meta/llama-3.3-70b-instruct` for generation; `meta/llama-3.1-8b-instruct` as the held-out judge; `nv-embedqa-e5-v5` for embeddings. BYOK supported via the UI model dropdown | `backend/agent_models.py`, `backend/multi_llm_client.py` |
| **Docker Compose + GHCR CI/CD** | Three-image build (`backend` / `console` / `frontend`); GitHub Actions publishes to GHCR on every `v*` tag | `Dockerfile.*`, `docker-compose.yml`, `.github/workflows/release.yml` |

---

## Architecture

The deterministic substrate at the bottom, two agent orchestration paths in the middle, two UI tabs at the top, the held-out evaluation harness on the side, and the A2A boundary as a separate external surface.

```mermaid
flowchart TB
    classDef data fill:#0e1117,stroke:#5b6470,color:#e6edf3,font-size:11px
    classDef tool fill:#1a2540,stroke:#1f6feb,color:#e6edf3,font-size:11px
    classDef agent fill:#2a1f54,stroke:#a371f7,color:#fff,font-size:11px
    classDef ui fill:#1c3d2a,stroke:#3fb950,color:#fff,font-size:11px
    classDef ext fill:#3d2a14,stroke:#d29922,color:#fff,font-size:11px
    classDef eval fill:#3d1c1c,stroke:#f85149,color:#fff,font-size:11px

    subgraph DATA["Data substrate (read-only)"]
        SIM["Fortran TEP sim<br/>temain_mod.so · unified_console.py"]:::data
        FAULTS["21 fault CSVs<br/>backend/data + frontend/public"]:::data
        WIKI["Governed wiki<br/>RAG/converted_markdown/*.md"]:::data
        RCA["Field feedback<br/>backend/LLM_RCA_Results/ + RCA_Results/"]:::data
    end

    subgraph BACKEND["Backend · FastAPI on :8000  (backend/app.py)"]
        direction TB
        subgraph DET["Deterministic (no LLM)"]
            PCA["PCA / T² detector"]:::tool
            TOOLS6["6 read-only tools"]:::tool
        end
        subgraph RET["Retrieval (4 evidence layers)"]
            WIKI_R["wiki — hybrid<br/>NIM dense + BM25 + RRF"]:::tool
            FIELD_R["field_feedback"]:::tool
            POL_R["policy catalog"]:::tool
            MP_R["pattern_memory<br/>Matrix Profile"]:::tool
        end
        subgraph ORCH["Agent orchestrators"]
            NAT["NAT ReAct agent<br/>(nat_runner.py)"]:::agent
            LG["LangGraph 5-node<br/>(langgraph_rca.py)"]:::agent
        end
        A2A["A2A surface<br/>/.well-known/agent-card.json<br/>JSON-RPC /a2a · SSE"]:::agent
        MCP["MCP server<br/>backend/mcp_server.py<br/>11 tools · stdio / SSE / http"]:::agent
    end

    subgraph FRONTEND["Frontend · React/Mantine on :5173"]
        LC["/  ·  Live Copilot"]:::ui
        DISC["/discovery  ·  Workbench"]:::ui
        WIKI_UI["/wiki  ·  LLM Wiki<br/>governed-corpus browser"]:::ui
    end

    EVAL["Evaluation harness<br/>held-out 8b judge<br/>4-way comparator"]:::eval
    NIM["NVIDIA NIM (external)<br/>llama-3.3-70b · llama-3.1-8b · nv-embedqa-e5-v5"]:::ext
    EXTAGENT["External agent<br/>(any A2A client)"]:::ext
    MCPHOST["LLM host<br/>(Claude Desktop · Cline · Cursor)"]:::ext

    SIM --> PCA
    SIM --> FAULTS
    FAULTS --> TOOLS6
    FAULTS --> MP_R
    WIKI --> WIKI_R
    RCA --> FIELD_R

    PCA --> NAT
    TOOLS6 --> NAT
    WIKI_R --> NAT
    FIELD_R --> NAT

    TOOLS6 --> LG
    WIKI_R --> LG
    FIELD_R --> LG
    POL_R --> LG
    MP_R --> LG

    NAT -. ReAct loop .-> NIM
    LG  -. per-node LLM .-> NIM
    EVAL -. held-out judge .-> NIM

    NAT --> LC
    LG --> DISC
    WIKI_R --> WIKI_UI
    LG --> A2A
    EXTAGENT --> A2A

    %% Same Python tool functions back both inter-agent surfaces — MCP
    %% adds a transport, not new capability.
    TOOLS6 --> MCP
    WIKI_R --> MCP
    FIELD_R --> MCP
    POL_R  --> MCP
    MP_R   --> MCP
    LG     --> MCP
    MCPHOST --> MCP

    NAT --> EVAL
    LG  --> EVAL
```

- **Grey** — deterministic substrate; nothing calls an LLM.
- **Blue** — tools + retrieval. The 4 evidence layers (wiki hybrid, field-feedback, policy catalog, Matrix Profile case memory) are queried in parallel by the LangGraph orchestrator.
- **Violet** — two orchestrators *plus* two inter-agent surfaces over the same Python tool functions. NAT is a single ReAct agent; LangGraph is a 5-node state machine with a critic-as-node and a bounded revision loop. **A2A** exposes the orchestrator to other agents over JSON-RPC; **MCP** exposes the same 11 read-only tools (6 deterministic + 4 evidence-layer wrappers + the LangGraph orchestrator) to LLM hosts over stdio/SSE/http. Adding MCP added a transport, not new capability.
- **Green** — UI tabs. `/` Live Copilot consumes NAT; `/discovery` Workbench consumes LangGraph; `/wiki` is a governed-corpus browser backed by the same hybrid wiki retriever (`/api/wiki/sources` + `/api/wiki/search`) and deep-linkable from agent traces.
- **Red** — held-out evaluation harness, runs both orchestrators on the same prompts.
- **Amber** — NIM hosts the LLMs; any A2A-speaking agent can call in through the agent card; any MCP-speaking host can drive the same 11 tools.

A detailed click-flow for one Diagnose-Now interaction lives in [`docs/A2A_INTEGRATION.md`](docs/A2A_INTEGRATION.md) and [`docs/AI_DISCOVERY_BRIEF_AGENTIC_RCA.md`](docs/AI_DISCOVERY_BRIEF_AGENTIC_RCA.md).

---

## Quick start

```bash
git clone https://github.com/chennanli/Agent_Orchestration_RootCauseAnalysis.git
cd Agent_Orchestration_RootCauseAnalysis
echo "NVIDIA_API_KEY=your_key_here" > .env       # or GEMINI_API_KEY=...
docker compose up --build
```

Open <http://localhost:5173/> for the Live Copilot, or <http://localhost:5173/discovery> for the LangGraph Workbench.

Get a free NIM key from [build.nvidia.com](https://build.nvidia.com/) (Llama 3.3 70B + 3.1 8B + Mixtral 8x22B). Gemini works too; paste a key into the in-UI model dropdown — it stays in your browser's `localStorage`, never on the server.

CLI entry points (no UI needed):

```bash
python backend/langgraph_rca.py --fault fault1
python backend/evaluation/evaluate_retrieval.py
python backend/evaluation/evaluate_full.py --limit 5
```

A six-step Docker smoke test (verifies the post-MVP endpoints actually work inside a fresh build) is in [`docs/DOCKER_SMOKE_TEST.md`](docs/DOCKER_SMOKE_TEST.md).

---

## Two agent paths in one repo

| Aspect | Live Copilot (`/`) | Discovery Workbench (`/discovery`) |
|---|---|---|
| Orchestration | Single NAT ReAct agent | LangGraph 5-node state machine |
| LLM provider at the generation node | Pluggable (NIM · Gemini · Anthropic · LM-Studio) via `backend/multi_llm_client.py` | Currently NIM-only (`ChatNVIDIA` in `backend/langgraph_rca.py`) |
| Tools / evidence | 6 read-only tools | 4 evidence layers (wiki / field / policy / pattern memory), 6 tools shared |
| Wiki retrieval | Keyword search over markdown | **Hybrid** — NIM dense + BM25 sparse + RRF |
| Termination | Open-ended ReAct loop | Bounded (≤ 3 revisions); explicit HITL gate |
| Evaluator | Policy regex on final draft | Policy regex **+** LLM grounding critic as a graph node |
| External boundary | Internal HTTP only | Reachable from another agent via **A2A** JSON-RPC + agent card |
| UI rendering | Linear `Thought → Action → Observation` trace | 5-step pipeline highlight + evidence-by-layer + hypothesis ranking + evaluator verdict, all over SSE |
| Saved runs | `backend/diagnostics/nat_runs/*.json` | `backend/diagnostics/multi_agent_runs/*.json` |

Plus a third UI tab and a fifth surface that both share the same toolkit:

- **`/wiki` — LLM Wiki tab** (`frontend/src/pages/LLMWikiPage.tsx`). A governed-corpus browser backed by the same hybrid retriever the agents use (`/api/wiki/sources` + `/api/wiki/search`). Deep-linkable from agent traces via `?doc=<source>&q=<query>` — click any source citation in the Live Copilot trace and you land on that document with the query pre-filled.
- **MCP server** (`backend/mcp_server.py`). Exposes the **same** 11 read-only tools the rest of the project uses, over the Model Context Protocol — transports: stdio / SSE / streamable-http. Any MCP-aware host (Claude Desktop, Cline, Cursor, OpenAI's MCP-enabled clients) can drive the toolkit; client config snippets are in [`docs/MCP_INTEGRATION.md`](docs/MCP_INTEGRATION.md). One implementation backs the NAT path, the LangGraph path, the A2A surface, and MCP — adding MCP added a transport, not new capability.

All five surfaces run against the same Fortran sim, the same PCA detector, and the same governed knowledge base — so the comparison is honest.

---

## Sample diagnosis output

The shape an operator actually sees from the Discovery Workbench: a deterministic signal, retrieved evidence broken out by layer, **three ranked candidate root causes with explicit confidence**, an evaluator verdict, and a policy-checked advisory. Full captured run + per-node timings + raw JSON: **[`docs/SAMPLE_DIAGNOSIS_FAULT4.md`](docs/SAMPLE_DIAGNOSIS_FAULT4.md)**.

![Discovery Workbench React UI — fault4 captured run replayed via the ?replay= flag — three ranked root causes (#1 HIGH · XMV_10; #2 MEDIUM · XMEAS_9; #3 LOW · downstream group), evidence-by-layer panel, evaluator policy_pass + grounded_ratio 50%, advisory-only output, 39.5 s end-to-end](docs/assets/discovery_3_hypotheses.png)

*Actual `/discovery` page rendered by the React frontend (`frontend/src/pages/DiscoveryPage.tsx`), hydrated from the captured run JSON at [`docs/sample_runs/lg_run_fault4_sample.json`](docs/sample_runs/lg_run_fault4_sample.json) via the new `?replay=<url>` query-param flag (`useDiscoveryStream.loadSnapshot`). No mock, no Photoshop — boot Vite (`npm run dev`), open `http://127.0.0.1:5173/discovery?replay=/sample_runs/lg_run_fault4_sample.json`, and you'll see the same UI. The run itself (`fault4` / IDV-4 reactor cooling-water inlet step) was generated by NIM `llama-3.3-70b-instruct` at the Hypothesis node. Layout, top → bottom: 5-node LangGraph pipeline · evidence by layer (governed wiki / field feedback / time-series case memory) · three ranked hypotheses with high/medium/low confidence · evaluator verdict (policy ✓, grounded_ratio 50%, 0 revisions, no HITL) · the final advisory text · the per-node audit trail with timestamps.*

Excerpt — Hypothesis node on `fault4` (IDV-4, reactor coolant inlet step), 39.5 s end-to-end, generator `meta/llama-3.3-70b-instruct` via NVIDIA NIM, evaluator `acceptable: True`, 0 revisions, no HITL escalation:

> **Hypothesis 1 — `rank: 1`, `confidence: high`** — The increase in **Reactor coolant load (XMV_10)** is the primary driver of fault4.
>
> **Hypothesis 2 — `rank: 2`, `confidence: medium`** — The flat **Reactor Temperature (XMEAS_9)** may be contributing to fault4, potentially as a result of the increased Reactor coolant load.
>
> **Hypothesis 3 — `rank: 3`, `confidence: low`** — Other variables such as **Recycle Flow (XMEAS_5)**, **Product Sep Underflow (XMEAS_14)**, and **Component B to Reactor (XMEAS_24)** may be playing a secondary role in fault4.

The Discovery Workbench is **currently NIM-wired** at the Hypothesis node (`ChatNVIDIA` in `backend/langgraph_rca.py`); all captured runs in `backend/diagnostics/multi_agent_runs/` use `meta/llama-3.3-70b-instruct`. The **model-provider abstraction lives in the Live Copilot path** (`backend/multi_llm_client.py`, `/explain/{provider}`) and supports Gemini, Anthropic, NIM, and a local LM-Studio fallback today; extending that factory into LangGraph is a focused follow-up — the LangGraph node-state contract doesn't care which provider produced the JSON, so the 3-hypothesis + evaluator + advisory output shape is invariant by construction.

> **Replay any saved run.** Drop the JSON under `frontend/public/sample_runs/` (or any URL the browser can reach) and open `/discovery?replay=<url>`. The page hydrates from the snapshot — no LLM call, no NIM key required, no orchestrator booted. Useful for sharing finished investigations as links and for rendering this kind of figure without spending API quota.

---

## Tool surface (shared)

Each tool is read-only. The same Python functions back the NAT ReAct agent, the LangGraph orchestrator, the A2A surface, and the MCP server — only one implementation. Names below are the **MCP / A2A public tool name** (what an external host calls), with the internal function in parentheses where they differ.

| Public tool (MCP / A2A) | Purpose | Boundary |
|---|---|---|
| `inspect_anomaly_snapshot` | T² statistic, threshold, row index, fault id | Read-only |
| `rank_contributing_variables` | Process variables most associated with the anomaly | Explains; doesn't prescribe |
| `get_sensor_window` | Short raw-data window for one variable | Inspection only |
| `search_process_knowledge` / `retrieve_wiki` (hybrid NIM dense + BM25 + RRF) | Search the governed TEP knowledge base | Cites source documents |
| `find_similar_faults` / `retrieve_field_feedback` | Match the current signature against the IDV catalog + prior RCA notes | Demo similarity, not certified classifier |
| `retrieve_pattern_memory` *(impl. `match_historical_patterns`)* | Matrix Profile time-series analog retrieval over 21 fault CSVs | Reports honest discord when no strong analog exists |
| `retrieve_policy_catalog` | The forbidden-control / overclaim regex catalog | Catalog of what the gate will block |
| `check_advisory_policy` | Inspect the final draft for control-style verbs and overclaims | Rejects unsafe phrasing; doesn't certify correctness |
| `diagnose_with_langgraph` *(MCP-only convenience)* | Run the full 5-node LangGraph orchestrator end-to-end | Costs NIM LLM calls; minutes per call |

The agent's complete action space. No `set_setpoint`, no `open_valve`, no `start_pump` — *by construction*. The full MCP tool catalog (11 entries) is in [`docs/MCP_INTEGRATION.md`](docs/MCP_INTEGRATION.md); the A2A agent card enumerates the same set at [`/.well-known/agent-card.json`](backend/a2a_router.py).

---

## Project layout

```text
backend/
  agent_tools/                 6 deterministic tools + 4-evidence-layer router
    pattern_tools.py             Matrix Profile time-series case memory
    vector_knowledge.py          ChromaDB + BM25 + RRF hybrid retrieval
    evidence_router.py           single entry-point over the 4 evidence layers
    {anomaly,knowledge,history,policy}_tools.py
  nat_workflows/                 NAT ReAct workflow YAML + plugin
  langgraph_rca.py               5-node LangGraph orchestrator (CLI + library)
  langgraph_api.py               POST /api/discovery/diagnose + SSE per-node stream
  a2a_router.py                  A2A agent card + JSON-RPC + SSE + standalone wiki agent
  evaluation/
    evaluate_agentic_discovery.py  NAT baseline vs LangGraph multi-evidence
    evaluate_retrieval.py        keyword / sparse / dense / hybrid head-to-head
    evaluate_full.py             4-way comparator with held-out 8b judge
    judge.py                     held-out grounding judge
    synth_cases.py               synthetic case generator
  app.py                         FastAPI app + /ingest + PCA detector
unified_console.py               Fortran simulator driver on :9002
frontend/src/
  pages/{LiveCopilotPage,DiscoveryPage}.tsx
  components/{DiscoveryGraphPipeline,EvidenceByLayerPanel,HypothesisRanking,
              EvaluatorVerdictPanel,AgentTimelinePanel,FollowupChat,...}.tsx
  hooks/{useAgentStream,useDiscoveryStream,useAnomalyState,useLiveBuffer}.ts
RAG/converted_markdown/*.md      governed wiki corpus (TEP literature)
docs/
  A2A_INTEGRATION.md             A2A surface contract
  AI_DISCOVERY_BRIEF_AGENTIC_RCA.md  research write-up
.github/workflows/{ci,release}.yml   CI on every push, GHCR images on every v* tag
```

---

## What's intentionally NOT in this repo

- Autonomous process control. Every tool is read-only by construction.
- Production-hardened deployment. The A2A surface has no auth or rate limit; default bind is `127.0.0.1`; `TEP_BIND_ALL=1` opts into multi-interface exposure.
- Statistically meaningful benchmarks. Eval scale is 3 discovery cases + 5 full-eval cases — smoke-test scale. The brief is explicit about this.
- Real-process data. TEP is a controlled chemical-process surrogate, not field data.

---

## Sample run output

- [`docs/SAMPLE_DIAGNOSIS_FAULT4.md`](docs/SAMPLE_DIAGNOSIS_FAULT4.md) — full captured run on `fault4` with all 5 nodes broken out, 3 ranked hypotheses, evaluator + HITL state, and final advisory.
- [`docs/sample_runs/lg_run_fault4_sample.json`](docs/sample_runs/lg_run_fault4_sample.json) — raw JSON of the same run for machine inspection.

---

## Documentation

- [`docs/AI_DISCOVERY_BRIEF_AGENTIC_RCA.md`](docs/AI_DISCOVERY_BRIEF_AGENTIC_RCA.md) — research write-up: hypothesis, architecture, evaluation, findings, limitations
- [`docs/A2A_INTEGRATION.md`](docs/A2A_INTEGRATION.md) — A2A surface contract, demonstration commands, honest limits
- [`docs/MCP_INTEGRATION.md`](docs/MCP_INTEGRATION.md) — MCP server (11 tools), Claude Desktop / Cline / Cursor config snippets, demo prompts
- [`docs/DOCKER_SMOKE_TEST.md`](docs/DOCKER_SMOKE_TEST.md) — six-step verification that the post-MVP endpoints actually run inside the Docker image
- [`CHANGELOG.md`](CHANGELOG.md) — release notes and **latest verified smoke metrics** (recall@5, MRR, grounded_ratio, completion rates) under `[Unreleased]`. The underlying JSON in `backend/evaluation/results/` is gitignored — the numbers are the most recent reproduce-on-machine values, not a tagged-release snapshot
- Original YouTube walkthrough (fixed-RAG predecessor): <https://www.youtube.com/watch?v=_Sy__E4J0_Q>

---

## Acknowledgements

Built around the [NVIDIA NeMo Agent Toolkit](https://developer.nvidia.com/blog/build-an-agentic-video-workflow-with-video-search-and-summarization/) (`nvidia-nat[langchain]==1.6.0`), [LangGraph](https://github.com/langchain-ai/langgraph), [ChromaDB](https://github.com/chroma-core/chroma), [stumpy](https://github.com/TDAmeritrade/stumpy), and the open Tennessee Eastman Process simulator (Downs & Vogel 1993; Python wrapper [`tep2py`](https://github.com/camaramm/tep2py)).
