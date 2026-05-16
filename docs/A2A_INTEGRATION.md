# A2A (Agent-to-Agent) Integration

This repo exposes the TEP RCA workbench through an **A2A-style JSON-RPC
surface with an agent card**, implemented locally against the public
[A2A protocol](https://github.com/google/A2A) shape so other agents (or
other copies of this agent) can call it through an agent-card / JSON-RPC
boundary. It is a research prototype — useful for experimentation and
demos but **not production-hardened** (no auth, no input validation
beyond JSON-RPC shape, no rate limiting).

## Surface

Mounted on the existing FastAPI app at `backend/app.py` (port 8000):

| Endpoint | Description |
|---|---|
| `GET /.well-known/agent-card.json` | Public agent card |
| `POST /a2a`                         | JSON-RPC 2.0, method `message/send` |
| `POST /a2a/stream`                  | SSE streaming, method `message/stream` |

Implementation: `backend/a2a_router.py`. We emit JSON shaped to match the
A2A spec directly via FastAPI rather than using `a2a-sdk`'s protobuf
machinery — `a2a-sdk 1.0.3` provides typed primitives but no FastAPI
server adapter, and JSON-RPC is a small enough protocol to hand-roll
locally. Anything beyond the shape (auth, full input validation,
client compatibility against the official server SDK) is research-prototype-
quality, not production-grade.

## Skills exposed

| ID | Description |
|---|---|
| `diagnose_process_anomaly` | Runs the full LangGraph 5-node orchestrator on a TEP fault snapshot. |
| `search_governed_wiki`     | Hybrid (NIM dense + BM25 sparse + RRF) retrieval over the governed TEP KB. |
| `review_advisory_policy`   | Runs the regex-based advisory-policy check on a candidate text. |

Skill resolution: clients may set `params.skill` or
`params.metadata.skill` explicitly. If omitted, the router applies a
keyword heuristic to the user text (e.g. "wiki" or "search" →
`search_governed_wiki`).

## Bonus: Wiki delegation through an A2A boundary

The plan called for *also* wrapping the Wiki layer as a separate local
A2A server so the LangGraph orchestrator delegates governed retrieval
through an agent-card / task interface — not direct in-process calls.

This is implemented:

* `standalone_wiki_app` in `backend/a2a_router.py` is a FastAPI app that
  only exposes `search_governed_wiki`. Run with
  `uvicorn backend.a2a_router:standalone_wiki_app --port 8765`.
* `call_remote_wiki_via_a2a(query, base_url, k)` is a client helper that
  posts a `message/send` JSON-RPC envelope to that server and unpacks the
  artifact.
* `backend/agent_tools/evidence_router.py` reads `TEP_WIKI_VIA_A2A=1`
  (with optional `TEP_WIKI_A2A_URL`) and, when set, routes the `"wiki"`
  layer through the A2A client instead of the in-process hybrid search.
  Hits returned this way are tagged `via: "a2a"` so the LangGraph audit
  trail can show the boundary was actually crossed.

Demonstration:

```bash
# Terminal 1 — start the wiki agent
uvicorn backend.a2a_router:standalone_wiki_app --port 8765

# Terminal 2 — run the orchestrator delegating wiki calls
TEP_WIKI_VIA_A2A=1 TEP_WIKI_A2A_URL=http://127.0.0.1:8765 \
  python backend/langgraph_rca.py --fault fault1
```

The orchestrator behaviour is unchanged; only the transport for the
`wiki` layer flips from in-process Python to A2A JSON-RPC. This means
the LangGraph agent depends only on the A2A contract — a different team
could swap in a completely different wiki backend tomorrow.

## Cross-call example (manual JSON-RPC)

```bash
curl -X POST http://127.0.0.1:8765/a2a \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": "demo-1",
    "method": "message/send",
    "params": {
      "skill": "search_governed_wiki",
      "message": {"role": "user", "parts": [{"text": "PCA T2 statistic"}]},
      "k": 3
    }
  }'
```

Returns an A2A `Task` envelope with one `Artifact` whose parts contain
the structured retrieval result.

## Limits / honest notes

* The agent card emits `protocolVersion: "0.3.0"` and uses the
  `JSONRPC` transport. It does not yet expose `gRPC` or `HTTP+JSON`.
* `message/stream` is implemented but emits only a `working` then
  `completed` event — finer-grained per-node updates from LangGraph
  would require wiring the LangGraph step callback through `asyncio` to
  the SSE stream. Worth doing in Sprint 2.
* Auth is intentionally absent — these endpoints assume a local trust
  boundary (same machine, same operator). The agent card exposes
  `securitySchemes: {}` honestly; production deployment would need an
  API-key or OAuth scheme.
