"""Typed schemas used by the read-only diagnostic tools.

The tool layer is intentionally lightweight: we use stdlib dataclasses so
the package imports cleanly even when Pydantic / NAT extras are not
installed. NAT integration code can wrap these dataclasses as needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


@dataclass
class AnomalySnapshot:
    fault_id: str = "fault1"
    csv_file: str = ""
    anomaly_index: int = -1
    t2_statistic: float = 0.0
    t2_threshold: float = 0.0
    is_anomaly: bool = False
    sample_count: int = 0
    plain_explanation: str = ""


@dataclass
class VariableContribution:
    variable: str = ""          # friendly name, e.g. "A feed load"
    tag: str = ""               # canonical TEP tag, e.g. "XMV_3" (empty if unknown)
    label: str = ""             # human display, e.g. "XMV_3 (A feed load)"
    kind: str = ""              # "manipulated" (XMV) | "measurement" (XMEAS) | ""
    t2_contribution: float = 0.0
    mean_change_pct: float = 0.0
    direction: str = "flat"


@dataclass
class KnowledgeSearchInput:
    query: str = ""
    max_results: int = 4


@dataclass
class KnowledgeSearchResult:
    query: str = ""
    excerpts: List[Dict[str, Any]] = field(default_factory=list)
    note: str = ""


@dataclass
class SensorWindowInput:
    sensor_name: str = ""
    fault_id: str = "fault1"
    window: int = 20


@dataclass
class SensorWindowResult:
    sensor_name: str = ""
    fault_id: str = "fault1"
    available: bool = False
    window: int = 0
    values: List[float] = field(default_factory=list)
    mean: float = 0.0
    std: float = 0.0
    baseline_mean: float = 0.0
    baseline_std: float = 0.0
    pct_change_vs_baseline: float = 0.0
    note: str = ""


@dataclass
class SimilarFaultInput:
    signature: str = ""
    top_k: int = 3


@dataclass
class SimilarFaultResult:
    signature: str = ""
    matches: List[Dict[str, Any]] = field(default_factory=list)
    note: str = ""


@dataclass
class AdvisoryPolicyInput:
    candidate_answer: str = ""


@dataclass
class AdvisoryPolicyResult:
    is_advisory_safe: bool = True
    forbidden_phrases_found: List[str] = field(default_factory=list)
    overclaims_found: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class RCAFinalAnswer:
    summary: str = ""
    likely_causes: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    recommended_next_inspections: List[str] = field(default_factory=list)
    safety_notice: str = (
        "Advisory only. The agent cannot change setpoints, open/close valves, "
        "or control the process. Human review required."
    )


def to_dict(model: Any) -> Dict[str, Any]:
    """Dataclass-or-dict agnostic serializer used by the tool wrappers."""
    if hasattr(model, "__dataclass_fields__"):
        return asdict(model)
    if isinstance(model, dict):
        return dict(model)
    if hasattr(model, "__dict__"):
        return dict(model.__dict__)
    return dict(model)
