# Changelog

All notable changes to this project are documented here. Format roughly
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the
project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — AI Discovery Workbench (research-prototype layer over the existing Live Copilot)
- **5-node LangGraph orchestrator** (`backend/langgraph_rca.py`): Signal →
  Evidence → Hypothesis → Evaluator → Human Review, with bounded revision
  loop and HITL gate. CLI + library + SSE-streaming HTTP API at
  `backend/langgraph_api.py`.
- **4 evidence layers** behind a single router (`backend/agent_tools/evidence_router.py`):
  governed wiki, field-feedback (prior RCA notes), policy / constraint
  catalog, time-series case memory.
- **Hybrid wiki retrieval** (`backend/agent_tools/vector_knowledge.py`):
  ChromaDB + NIM `nv-embedqa-e5-v5` dense embeddings + `rank_bm25` sparse,
  fused with reciprocal-rank fusion.
- **Time-series case memory** (`backend/agent_tools/pattern_tools.py`):
  Matrix Profile AB-join via `stumpy`; cross-fault-boundary masking.
- **A2A-style JSON-RPC surface** (`backend/a2a_router.py`): agent card at
  `/.well-known/agent-card.json`, `message/send` at `/a2a`, SSE at
  `/a2a/stream`. Includes a standalone wiki agent for delegation demos.
- **Held-out LLM-as-judge** (`backend/evaluation/judge.py`):
  `meta/llama-3.1-8b-instruct` grades the grounding of advisories
  produced by the 70b generator — stricter than same-family critic.
- **4-way comparator harness** (`backend/evaluation/evaluate_full.py`):
  `tools_only` / `nat_react` / `langchain_react` / `langgraph_multi` on
  the same prompts with the same held-out judge.
- **Synthetic case generator** (`backend/evaluation/synth_cases.py`):
  LLM-generated diagnostic prompts conditioned per fault id.
- **React `/discovery` page** (`frontend/src/pages/DiscoveryPage.tsx`):
  live LangGraph pipeline + evidence-by-layer panel + hypothesis ranking
  + evaluator verdict, all streamed over SSE.
- `docs/DOCKER_SMOKE_TEST.md` — 6-step verification that the Docker image
  actually runs all post-MVP endpoints.

### Verified metrics (smoke-test scale, n=3 + n=5; not a benchmark)

JSON sources: `backend/evaluation/results/*.json`.

| Subject | Number | Source |
|---|---|---|
| Hybrid retrieval, recall@5 | **0.857** | `retrieval_summary.json` |
| Hybrid retrieval, MRR | **1.000** | `retrieval_summary.json` |
| Sparse-only recall@5 / MRR | 0.857 / 0.929 | `retrieval_summary.json` |
| Dense-only recall@5 / MRR | 0.714 / 1.000 | `retrieval_summary.json` |
| Keyword baseline recall@5 / MRR | 0.643 / 0.821 | `retrieval_summary.json` |
| LangGraph grounded_ratio (same-family critic, n=3) | **0.583** | `discovery_summary.json` |
| NAT baseline grounded_ratio (n=3) | 0.167 | `discovery_summary.json` |
| LangGraph grounded_ratio (held-out 8b judge, n=5) | ~0.2 – 0.4 (run-noisy) | `full_eval_summary.json` |
| LangGraph mean runtime (n=3) | 9.4 s | `discovery_summary.json` |
| NAT mean runtime (n=3) | 1161 s | `discovery_summary.json` |
| Matrix Profile top-1 on fault1 | dist = 4.58 (no strong analog) | CLI |

### Security
- `backend/app.py` CORS no longer includes `"*"` in `allow_origins`; only
  enumerated dev ports (override via `TEP_CORS_EXTRA_ORIGINS`).
- SSE responses use a shared `_apply_sse_cors()` helper that echoes the
  request origin only if in the allowlist (was hardcoded `"*"`).
- `backend/app.py __main__` binds `127.0.0.1` by default; `TEP_BIND_ALL=1`
  opts into all-interfaces exposure (set in `docker-compose.yml`).
- `docker-compose.yml` publishes on `127.0.0.1:PORT` by default;
  `COMPOSE_HOST_BIND=0.0.0.0` opts in to LAN exposure.

### Eval-harness correctness
- `_run_langchain_react` and `_run_nat_react` in `evaluate_full.py` now
  collect each comparator's actual tool outputs and pass them to the
  judge symmetrically (was: comparator got `[]` while langgraph got real
  evidence — unfair grading).
- `_run_tools_only` reads `top_variables` (was reading a wrong key,
  producing empty advisories).
- `evidence_hit_rate` denominator uses `len(_EVIDENCE_LAYERS)` from
  `langgraph_rca` (was hardcoded 3.0).
- `evidence_router._retrieve_field_feedback` reads `matches` (the actual
  key returned by `find_similar_faults`; was returning 0 hits).
- `pattern_tools.match_historical_patterns` masks windows that straddle
  two adjacent fault CSVs in the archive (eliminates bogus top-1 matches).

### Docker / packaging
- `requirements.txt` adds the AI Discovery runtime: `langgraph`,
  `langgraph-checkpoint-sqlite`, `langchain`,
  `langchain-nvidia-ai-endpoints`, `chromadb`, `rank-bm25`, `stumpy`,
  `typing-extensions`.
- `Dockerfile.backend` installs both `requirements.txt` and
  `requirements-nat.txt` so the NAT path works inside the image.
- `.dockerignore` re-includes the Linux Fortran extension and the
  governed-wiki markdown corpus (both were being stripped from the
  build context by generic ignore rules).

### Existing additions (carried from earlier in `[Unreleased]`)
- Frontend test suite (`vitest` + Testing Library) with 10 baseline tests
  covering the agent API client and the BakeoffCard component.
- CI runs `npm test` on every push.
- CI runs `docker compose config --quiet` to validate the compose file
  + Dockerfile paths on every push.
- `release.yml` creates a GitHub Release entry with auto-generated notes
  on every `v*` tag push.

## [0.3.1] — 2026-05-12

**First complete release.** All three Docker images publish to GHCR.

### Fixed
- Backend image build failed in v0.3.0 because `COPY RAG/` referenced a
  gitignored directory. `RAG/converted_markdown/*.md` is now committed (it
  is public TEP literature, not secret), and the `.gitignore` rule was
  narrowed to `RAG/*` with explicit re-includes.

### Published images
```
ghcr.io/chennanli/agent_orchestration_rootcauseanalysis/backend:v0.3.1
ghcr.io/chennanli/agent_orchestration_rootcauseanalysis/console:v0.3.1
ghcr.io/chennanli/agent_orchestration_rootcauseanalysis/frontend:v0.3.1
```

## [0.3.0] — 2026-05-12  *(broken — use v0.3.1)*

**Do not use this tag.** The release workflow succeeded for `frontend` and
`console` but the `backend` image build failed (gitignored `RAG/` path).
The two published images are left in place for historical accuracy; pulling
`backend:v0.3.0` will 404.

### Added (the intended scope of this release)
- Three-image CI/CD: backend / console / frontend all built and pushed to
  GHCR on every `v*` tag (`release.yml` matrix build).
- `docker-compose.yml` orchestrating the full stack — `docker compose up`
  is now the recommended way to run the demo.
- README quick-start section with API-key signup links and a "Published
  images" subsection listing the GHCR paths.
- New `Dockerfile.console` with a slim ~150 MB image (was pulling the
  whole 1.5 GB requirements.txt).
- `frontend/Dockerfile` rewritten to build from REPO_ROOT context (fixes a
  pre-existing build-context contradiction).
- `BACKEND_INGEST_URL` and `UNIFIED_CONSOLE_URL` env vars so the three
  containers can resolve each other by service name.

## [0.2.x]

Pre-CD work — see `git log` for the granular history. Highlights:

- 8 business-logic tests for the agent tools (PCA detection on fault1,
  policy gate on control-style phrasing, KB retrieval).
- 6 backend import-smoke tests; CI fully wired (`ci.yml`).
- Misc tab (export-as-Markdown, email, operator notes, KB upload).
- "Naive LLM vs NAT agent" bake-off feature.
- Follow-up chat respects the originally-selected model + BYOK API key.

[Unreleased]: https://github.com/chennanli/Agent_Orchestration_RootCauseAnalysis/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/chennanli/Agent_Orchestration_RootCauseAnalysis/releases/tag/v0.3.1
[0.3.0]: https://github.com/chennanli/Agent_Orchestration_RootCauseAnalysis/releases/tag/v0.3.0
