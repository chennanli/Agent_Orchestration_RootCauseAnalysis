# NAT TEP RCA Workflow

This folder contains the **NeMo Agent Toolkit (NAT)** workflow that upgrades
the TEP demo's diagnosis layer from a fixed RAG / multi-LLM pipeline into a
read-only agentic RCA workflow.

## Files

| File | Purpose |
|------|---------|
| `tep_rca_workflow.yml` | NAT workflow config (functions, llm, react_agent) |
| `nat_tep_plugin.py`    | Registers the six diagnostic tools under their `_type` names |
| `__init__.py`          | Imports the plugin so registration runs whenever the package is loaded |

The actual tool implementations live in `backend/agent_tools/` and are
plain Python functions that work without NAT installed. NAT only needs to
be installed when you want to run the workflow YAML through the `nat`
CLI or the `react_agent` runtime.

## Install NAT (optional)

```bash
pip install -r requirements-nat.txt
```

Then make sure the NeMo Agent Toolkit can find the plugin module. The
simplest way is to run from the repo root so `backend.nat_workflows` is on
the Python path:

```bash
cd /path/to/TEP_demo-main
python -c "import backend.nat_workflows"  # triggers tool registration
nat --version
nat run --config_file backend/nat_workflows/tep_rca_workflow.yml \
    --input "Diagnose fault1 and recommend operator review steps."
```

## Required environment

The example config requests `meta/llama-3.1-70b-instruct` from NVIDIA NIM.
Set:

```bash
export NVIDIA_API_KEY=...   # required by NAT for the `_type: nim` LLM
```

If you prefer another LLM provider (Anthropic, OpenAI), edit the `llms:`
block in `tep_rca_workflow.yml` to match the NAT provider syntax for your
installed NAT version.

## Falling back when NAT is not installed

`backend/nat_runner.py` and `backend/evaluation/evaluate_nat_rca.py` both
detect missing NAT and either:

- Use the Python tools directly to produce a deterministic "tools-only"
  trace (no LLM reasoning), or
- Print a useful setup message and exit non-zero.

The legacy multi-LLM RCA pipeline at `backend/multi_llm_client.py` is
unchanged.

## NAT version drift

NAT's Python API moved across releases. `nat_tep_plugin.py` tries the
modern `nat.cli.register_workflow.register_function` path first and falls
back to the legacy `aiq.cli.register_workflow.register_function` path
second. If both imports fail, the module logs a clear message and the
Python tools remain callable directly.

If you see registration errors with a newly-released NAT, please open an
issue with the exact `nat --version`, the import error, and the current
`tep_rca_workflow.yml`.
