# MCP (Model Context Protocol) Integration

The repo ships an MCP server (`backend/mcp_server.py`) that exposes the same
read-only diagnostic tools the rest of the project uses, over the
[Model Context Protocol](https://modelcontextprotocol.io). Any MCP-aware
client (Claude Desktop, Cline, Cursor, OpenAI's MCP-enabled clients) can
discover and call these tools.

## What's exposed

11 tools, all read-only. Same underlying Python functions back both this
MCP surface and the A2A surface (`backend/a2a_router.py`) — adding MCP
adds zero new capability, just another transport.

| Category | Tool | What it does |
|---|---|---|
| **Anomaly** | `inspect_anomaly_snapshot` | T², threshold, index, fault id |
| | `rank_contributing_variables` | Top-k variables by T² contribution |
| | `get_sensor_window` | Raw-data window for one variable |
| **Knowledge** | `search_process_knowledge` | Keyword over TEP markdown |
| | `find_similar_faults` | Match signature against IDV catalog + RCA notes |
| **Policy** | `check_advisory_policy` | Regex check for control-style language / overclaims |
| **Evidence layers** | `retrieve_wiki` | Hybrid (NIM dense + BM25 + RRF) by default; substrate overrideable |
| | `retrieve_field_feedback` | Prior RCA notes |
| | `retrieve_policy_catalog` | The forbidden-control / overclaim regex catalog |
| | `retrieve_pattern_memory` | Matrix Profile time-series analogs |
| **Orchestrator** | `diagnose_with_langgraph` | Runs the full 5-node LangGraph pipeline end-to-end |

## Run it

### stdio (Claude Desktop / Cline / Cursor / Continue spawn it themselves)

```bash
python -m backend.mcp_server
# or explicitly:
python -m backend.mcp_server --transport stdio
```

### SSE (HTTP clients)

```bash
python -m backend.mcp_server --transport sse
# default mount: http://localhost:8000/sse
```

### streamable-http

```bash
python -m backend.mcp_server --transport streamable-http
```

## Client configuration

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "tep-rca": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "backend.mcp_server"],
      "cwd": "/absolute/path/to/Agent_Orchestration_RootCauseAnalysis",
      "env": {
        "NVIDIA_API_KEY": "your_key_here"
      }
    }
  }
}
```

Restart Claude Desktop. The 11 tools appear under the 🔌 / hammer icon.
Asking *"Inspect the TEP fault1 anomaly snapshot, then rank its top
variables"* will trigger two tool calls in sequence.

### Cline / Continue (VS Code)

In your Cline/Continue MCP settings file, add the same `command` + `args` +
`cwd` + `env` block.

### Cursor

`~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "tep-rca": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "backend.mcp_server"]
    }
  }
}
```

## Demo prompts you can paste into the host

Once connected, the host's LLM can compose multi-tool sequences. Try:

> *"Use the tep-rca tools to inspect the fault4 anomaly, rank its top
> contributing variables, search the wiki for any documentation about
> reactor cooling water disturbances, and draft a 2-sentence operator
> advisory. Then check the advisory against the policy before showing it
> to me."*

Expected sequence of tool calls:
1. `inspect_anomaly_snapshot(fault_id="fault4")`
2. `rank_contributing_variables(fault_id="fault4")`
3. `retrieve_wiki(query="reactor cooling water disturbance")` (or `search_process_knowledge`)
4. *(LLM drafts advisory text)*
5. `check_advisory_policy(candidate_answer=...)`

Or invoke the orchestrator directly:

> *"Run diagnose_with_langgraph on fault6 and summarise what the evaluator
> concluded."*

## How this fits next to A2A

| Surface | Talks to | Transport | Spec | File |
|---|---|---|---|---|
| **MCP** | LLM host (Claude Desktop, Cline, Cursor) | stdio · SSE · streamable-http | [modelcontextprotocol.io](https://modelcontextprotocol.io) | `backend/mcp_server.py` |
| **A2A** | Another agent (or another instance of this one) | JSON-RPC + SSE | [A2A protocol](https://github.com/google/A2A) | `backend/a2a_router.py` |

A2A is *agent-to-agent* (one orchestrator delegates work to another
agent). MCP is *host-to-tool-server* (an LLM host connects to a server
that provides tools). The same 6+4 read-only tools are exposed on both
surfaces; the difference is the consumer.

## Limits (honest)

- The MCP server is read-only by construction. There is no `set_setpoint`
  / `open_valve` / `start_pump` tool.
- No auth on the stdio transport (which is the common case — the client
  spawns the process directly, so trust is established at spawn time).
  On SSE / streamable-http, the same caveat as A2A applies: research
  prototype, not production-hardened.
- Resources (`mcp.resource()`) and prompts (`mcp.prompt()`) are not
  registered yet. The brief lists this as Sprint 2 work — a `tep-fault-catalog`
  resource that exposes the 21 IDV definitions plus a couple of canned
  diagnose prompts would be the natural next step.
- The `diagnose_with_langgraph` tool calls the LangGraph orchestrator
  end-to-end, which costs NIM LLM calls. Use the lower-level tools for
  cheaper read-only inspection.
