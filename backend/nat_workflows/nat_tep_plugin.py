"""NAT plugin: register the TEP read-only diagnostic tools as NAT functions.

NAT >= 1.6 builds its function registry from `FunctionBaseConfig` subclasses
that declare the `_type` discriminator via the **class keyword argument**
``name="..."`` (consumed by ``__init_subclass__``). A dynamic ``type()``
call with ``name`` as a plain class attribute does NOT register, which is
what bit the first iteration of this file.

Each tool here therefore gets its own explicit ``class FooConfig(...)``,
plus an ``async def`` decorated with ``@register_function(config_type=...)``
that yields a ``FunctionInfo``. The inner ``_impl`` keeps explicit typed
parameters so NAT can auto-generate the JSON schema the react_agent uses
to call the tool.

If NAT is not installed (legacy demo only), this module logs a clear note
and exits cleanly so importing it never breaks the non-NAT path.
"""

# NOTE: deliberately NOT using `from __future__ import annotations` here.
# NAT 1.6 introspects each registered function with `typing.get_type_hints()`
# inside its own module's globals, so string-form annotations (PEP 563) can
# fail with NameError on imports that exist only in this file. Keeping
# annotations as live Python objects avoids that.

import logging
from typing import Any  # noqa: F401  (kept for backward-compat with helpers)

from backend.agent_tools import (
    inspect_anomaly_snapshot as _tool_inspect_anomaly_snapshot,
    rank_contributing_variables as _tool_rank_contributing_variables,
    search_process_knowledge as _tool_search_process_knowledge,
    get_sensor_window as _tool_get_sensor_window,
    find_similar_faults as _tool_find_similar_faults,
    check_advisory_policy as _tool_check_advisory_policy,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Try to import NAT. If anything is missing we exit cleanly so the legacy
# demo path keeps working.
# ---------------------------------------------------------------------------
_NAT_OK = False
try:
    from nat.builder.function_info import FunctionInfo  # type: ignore
    from nat.cli.register_workflow import register_function  # type: ignore
    from nat.data_models.function import FunctionBaseConfig  # type: ignore
    _NAT_OK = True
except Exception as _exc:  # noqa: BLE001
    logger.info("NAT not detected; TEP NAT plugin will not register: %s", _exc)


if _NAT_OK:

    # ----- 1. inspect_anomaly_snapshot --------------------------------------
    class _InspectAnomalyConfig(FunctionBaseConfig, name="tep_inspect_anomaly_snapshot"):
        """Read-only TEP anomaly snapshot."""

    @register_function(config_type=_InspectAnomalyConfig)
    async def _register_inspect_anomaly(config: _InspectAnomalyConfig, builder):
        async def _impl(fault_id: str = "fault1") -> dict:
            """Return T2 statistic, threshold, anomaly index, and a plain explanation
            for a TEP fault CSV (read-only)."""
            return _tool_inspect_anomaly_snapshot(fault_id)

        yield FunctionInfo.from_fn(
            _impl,
            description=(
                "Read-only inspection of the deterministic PCA / Hotelling T2 anomaly "
                "state for a TEP fault CSV. Input is a fault id like 'fault1'."
            ),
        )

    # ----- 2. rank_contributing_variables -----------------------------------
    class _RankVariablesConfig(FunctionBaseConfig, name="tep_rank_contributing_variables"):
        """Rank top contributing process variables."""

    @register_function(config_type=_RankVariablesConfig)
    async def _register_rank_variables(config: _RankVariablesConfig, builder):
        async def _impl(fault_id: str = "fault1", top_k: int = 6) -> dict:
            """Rank top-K process variables driving the anomaly using
            precomputed per-variable T2 contributions."""
            return _tool_rank_contributing_variables(fault_id, top_k=top_k)

        yield FunctionInfo.from_fn(
            _impl,
            description=(
                "Return the top contributing process variables for the current TEP "
                "anomaly with their T2 contribution and percent mean shift versus baseline."
            ),
        )

    # ----- 3. search_process_knowledge --------------------------------------
    class _SearchKnowledgeConfig(FunctionBaseConfig, name="tep_search_process_knowledge"):
        """Keyword search over the TEP knowledge base."""

    @register_function(config_type=_SearchKnowledgeConfig)
    async def _register_search_knowledge(config: _SearchKnowledgeConfig, builder):
        async def _impl(query: str, max_results: int = 4) -> dict:
            """Keyword search over RAG/converted_markdown returning source-cited excerpts."""
            return _tool_search_process_knowledge(query, max_results=max_results)

        yield FunctionInfo.from_fn(
            _impl,
            description=(
                "Keyword-based search over the local TEP knowledge base "
                "(RAG/converted_markdown). Returns a list of source-cited excerpts. "
                "Not vector / semantic search."
            ),
        )

    # ----- 4. get_sensor_window ---------------------------------------------
    class _SensorWindowConfig(FunctionBaseConfig, name="tep_get_sensor_window"):
        """Return a windowed slice of one sensor."""

    @register_function(config_type=_SensorWindowConfig)
    async def _register_sensor_window(config: _SensorWindowConfig, builder):
        async def _impl(
            sensor_name: str,
            fault_id: str = "fault1",
            window: int = 20,
        ) -> dict:
            """Return last-N values, mean, std and baseline drift for one process variable."""
            return _tool_get_sensor_window(sensor_name, fault_id=fault_id, window=window)

        yield FunctionInfo.from_fn(
            _impl,
            description=(
                "Return a windowed slice of raw sensor values for one TEP process "
                "variable (e.g. 'Reactor Pressure'), with mean / std / pct change vs baseline."
            ),
        )

    # ----- 5. find_similar_faults -------------------------------------------
    class _SimilarFaultsConfig(FunctionBaseConfig, name="tep_find_similar_faults"):
        """Keyword similarity over canonical IDV faults + past LLM RCA reports."""

    @register_function(config_type=_SimilarFaultsConfig)
    async def _register_similar_faults(config: _SimilarFaultsConfig, builder):
        async def _impl(signature: str, top_k: int = 3) -> dict:
            """Keyword similarity search over canonical IDV faults and historical
            LLM RCA reports."""
            return _tool_find_similar_faults(signature, top_k=top_k)

        yield FunctionInfo.from_fn(
            _impl,
            description=(
                "Keyword similarity search over canonical IDV fault descriptions and "
                "historical LLM RCA reports. Demo similarity, not vector embeddings."
            ),
        )

    # ----- 6. check_advisory_policy -----------------------------------------
    class _AdvisoryPolicyConfig(FunctionBaseConfig, name="tep_check_advisory_policy"):
        """Inspect a draft advisory for unsafe wording."""

    @register_function(config_type=_AdvisoryPolicyConfig)
    async def _register_advisory_policy(config: _AdvisoryPolicyConfig, builder):
        async def _impl(candidate_answer: str) -> dict:
            """Inspect a candidate operator advisory for forbidden control-style
            language and overclaims. Returns is_advisory_safe + suggested rewrites."""
            return _tool_check_advisory_policy(candidate_answer)

        yield FunctionInfo.from_fn(
            _impl,
            description=(
                "Self-check the agent's draft operator advisory against a wording "
                "policy. Flags control-style commands (open valve, change setpoint) "
                "and overclaims (safe to operate, root cause certain). Always call "
                "this last."
            ),
        )

    logger.info("TEP NAT plugin registered 6 tools: tep_inspect_anomaly_snapshot, "
                "tep_rank_contributing_variables, tep_search_process_knowledge, "
                "tep_get_sensor_window, tep_find_similar_faults, "
                "tep_check_advisory_policy.")
