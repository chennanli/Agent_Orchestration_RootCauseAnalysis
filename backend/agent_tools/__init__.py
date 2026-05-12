"""Read-only diagnostic tools for the TEP NAT agentic RCA workflow.

These tools wrap the existing deterministic anomaly-detection, knowledge-base
and history utilities into small, typed functions that an agent (NAT or any
other ReAct-style runner) can call.

Important boundaries:
- Every tool is read-only.
- No tool can change a setpoint, a valve, an operating mode, or any
  process-side state.
- Tools return structured data (dicts) suitable for an LLM to reason about
  and for an evaluator to score.
"""

from .schemas import (
    AnomalySnapshot,
    VariableContribution,
    KnowledgeSearchInput,
    KnowledgeSearchResult,
    SensorWindowInput,
    SensorWindowResult,
    SimilarFaultInput,
    SimilarFaultResult,
    AdvisoryPolicyInput,
    AdvisoryPolicyResult,
    RCAFinalAnswer,
)
from .anomaly_tools import (
    inspect_anomaly_snapshot,
    rank_contributing_variables,
)
from .knowledge_tools import search_process_knowledge
from .history_tools import get_sensor_window, find_similar_faults
from .policy_tools import check_advisory_policy

__all__ = [
    "AnomalySnapshot",
    "VariableContribution",
    "KnowledgeSearchInput",
    "KnowledgeSearchResult",
    "SensorWindowInput",
    "SensorWindowResult",
    "SimilarFaultInput",
    "SimilarFaultResult",
    "AdvisoryPolicyInput",
    "AdvisoryPolicyResult",
    "RCAFinalAnswer",
    "inspect_anomaly_snapshot",
    "rank_contributing_variables",
    "search_process_knowledge",
    "get_sensor_window",
    "find_similar_faults",
    "check_advisory_policy",
]
