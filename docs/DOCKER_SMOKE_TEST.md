# Docker smoke test

Run-once verification that `docker compose up --build` actually produces a
working stack with the post-MVP code paths (LangGraph orchestrator, A2A
surface, hybrid retrieval, NAT ReAct, RAG markdown). The repo's
`.dockerignore`, `requirements.txt`, and `Dockerfile.*` were repaired
statically; this checklist is the proof-of-life that anyone with Docker
should run before relying on the image.

## Prerequisites

- Docker Desktop (or `docker` + `docker compose` >= 2.0)
- `NVIDIA_API_KEY` in `.env` (free from <https://build.nvidia.com/>)

```bash
git clone https://github.com/chennanli/Agent_Orchestration_RootCauseAnalysis.git
cd Agent_Orchestration_RootCauseAnalysis
echo "NVIDIA_API_KEY=your_key_here" > .env
docker compose up --build
```

First build is slow (~5–10 min) because `chromadb` and `nvidia-nat[langchain]`
pull a lot. Subsequent builds use Docker's layer cache.

## The 6 checks

Run all six in a separate terminal after `docker compose up --build` has
settled. They are independent — if a later one fails, the earlier output
narrows the cause.

### 1. All three services healthy

```bash
docker compose ps                                       # backend / console / frontend up
docker compose logs backend  --tail 80                  # no ImportError / no traceback
docker compose logs console  --tail 40                  # Fortran sim loaded
docker compose logs frontend --tail 20                  # nginx serving
```

Expected: `tep-backend`, `tep-console`, `tep-frontend` all `Up`. No
`ImportError` or `ModuleNotFoundError` in the backend log.

### 2. Base FastAPI surface reachable

```bash
curl -fsS http://localhost:8000/                        # 200
curl -fsS http://localhost:8000/api/agent/models        # JSON
curl -fsS http://localhost:5173/                        # frontend HTML
```

### 3. Post-MVP endpoints (A2A + LangGraph) reachable

```bash
curl -fsS http://localhost:8000/.well-known/agent-card.json  | head -5
curl -fsS -X POST http://localhost:8000/a2a \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"smoke","method":"message/send",
       "params":{"skill":"review_advisory_policy",
                 "message":{"role":"user","parts":[{"text":"open valve"}]}}}'
```

Expected: agent card JSON; JSON-RPC `Task` envelope with a policy-check result.

### 4. LangGraph orchestrator runs end-to-end inside the backend image

```bash
docker compose exec backend python backend/langgraph_rca.py --fault fault1 \
  --question "Smoke test inside Docker."
```

Expected: prints `Nodes visited: [SignalAgent, EvidenceAgent, HypothesisAgent,
EvaluatorAgent, HumanReviewGate]` and a final advisory. Runtime ~10–40 s
depending on NIM load.

### 5. NAT path (`Diagnose Now` flow) works

```bash
# 5a) NAT toolkit is installed
docker compose exec backend python -c "import nat"      # silent = pass

# 5b) Deterministic tool-chain (explicit no-LLM fallback)
docker compose exec backend python backend/nat_runner.py --fault fault1 --tools-only

# 5c) Real NAT LLM path end-to-end
docker compose exec backend python backend/nat_runner.py --fault fault1 \
  --question "Smoke: diagnose the current TEP anomaly."
```

The three sub-checks isolate failure modes:

- **5a passes / 5c fails:** NAT package is installed, but the LLM call fails.
  Most often `NVIDIA_API_KEY` not set or NIM model name retired. Check
  `backend/nat_workflows/tep_rca_workflow.yml`.
- **5a fails:** `nvidia-nat[langchain]` didn't make it into the image. Real
  `Diagnose Now` button will return `NAT unavailable` rather than producing
  an agent trace. `Dockerfile.backend` must install both `requirements.txt`
  and `requirements-nat.txt`.

### 6. Governed-wiki markdown made it into the image

```bash
docker compose exec backend ls RAG/converted_markdown/         # 6 .md files
docker compose exec backend python -c "
from backend.agent_tools.knowledge_tools import search_process_knowledge
r = search_process_knowledge('reactor cooling water', max_results=2)
print('hits:', len(r.get('excerpts', [])))                     # must be > 0
"
```

The `*.md` rule in `.dockerignore` has stripped this once before; this check
catches it.

## If anything fails

| Failure | Likely cause | Where to look |
|---|---|---|
| `import nat` ImportError | `requirements-nat.txt` not installed | `Dockerfile.backend` line 54 should `COPY` and `pip install` both `requirements.txt` and `requirements-nat.txt` |
| `search_process_knowledge` returns 0 hits | `*.md` rule in `.dockerignore` stripped the corpus | `.dockerignore` must have `!RAG/converted_markdown/*.md` AFTER the generic `*.md` exclude |
| `temain_mod` import error in console logs | Linux Fortran `.so` not copied | `.dockerignore` must have `!backend/simulation/temain_mod.cpython-36m-x86_64-linux-gnu.so` |
| `/api/agent/diagnose` 401 / 429 | `NVIDIA_API_KEY` missing or quota exhausted | Check `.env`, retry on fresh quota |
| Backend up but `/discovery` 404 in browser | Frontend image was built before Phase 9 routes existed | `docker compose build --no-cache frontend && docker compose up -d frontend` |

## Realistic time budget

- If everything is correct on the first try: **30 min** wall-clock (mostly
  waiting for the first build).
- If something is misconfigured: **half a day** is realistic (build failure
  → diagnose → rebuild → re-run the 6 checks).

The image is not certified production-ready — it's a research prototype.
Don't expose the API on a network without putting an auth proxy in front.
