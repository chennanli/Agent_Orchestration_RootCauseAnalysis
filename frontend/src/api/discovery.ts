// Typed client for the AI Discovery Workbench endpoints
// (mounted from backend/langgraph_api.py).
//
// All paths are relative; Vite proxies /api/* to http://127.0.0.1:8000 in dev.

export interface DiscoveryStarted {
  run_id: string;
  fault_id: string;
  started_at: string;
  stream_url: string;
}

export interface RankedVariable {
  variable: string;
  tag?: string;
  label?: string;
  kind?: string;
  t2_contribution?: number;
  mean_change_pct?: number;
  direction?: string;
}

export interface EvidenceHit {
  source?: string;
  section?: string;
  text?: string;
  score?: number;
  // pattern_memory-specific
  known_pattern?: string;
  distance?: number;
  matched_range?: [number, number];
  // wiki hybrid annotations
  substrates?: string[];
  via?: string;
}

export interface Hypothesis {
  rank?: number;
  statement?: string;
  supporting_evidence_ids?: string[];
  confidence?: string;
}

export interface DiscoveryEvaluation {
  policy?: {
    is_advisory_safe?: boolean;
    forbidden_phrases?: string[];
    overclaims?: string[];
  };
  grounded_ratio?: number;
  citation_coverage?: number;
  acceptable?: boolean;
  feedback?: string;
  llm_critique_used?: boolean;
}

export interface DiscoveryAuditEntry {
  node: string;
  ts: string;
  [key: string]: unknown;
}

// State snapshot the SSE stream sends after each LangGraph node.
export interface DiscoveryStateSnapshot {
  anomaly_snapshot?: Record<string, unknown> | null;
  ranked_variables?: RankedVariable[];
  evidence_by_layer?: Record<string, EvidenceHit[]>;
  hypotheses?: Hypothesis[];
  draft_advisory?: string;
  evaluation?: DiscoveryEvaluation;
  revision_count?: number;
  hitl_required?: boolean;
  final_advisory?: string;
  audit_trail?: DiscoveryAuditEntry[];
}

// What the SSE `node` event sends.
export interface DiscoveryNodeEvent {
  node: string;
  state: DiscoveryStateSnapshot;
}

// What the SSE `done` event sends.
export interface DiscoveryDoneEvent {
  final: (DiscoveryStateSnapshot & { _runtime_seconds?: number }) | null;
}

// Saved-run list item from GET /api/discovery/runs
export interface DiscoveryRunListItem {
  file: string;
  fault_id?: string;
  runtime_seconds?: number | null;
  final_advisory_snippet?: string;
  hitl_required?: boolean | null;
  evaluation_grounded_ratio?: number | null;
}

export async function startDiscoveryRun(
  fault_id: string,
  question?: string,
): Promise<DiscoveryStarted> {
  const r = await fetch("/api/discovery/diagnose", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fault_id, question: question ?? null }),
  });
  if (!r.ok) throw new Error(`discovery start failed: ${r.status}`);
  return (await r.json()) as DiscoveryStarted;
}

export async function listDiscoveryRuns(limit = 20): Promise<DiscoveryRunListItem[]> {
  const r = await fetch(`/api/discovery/runs?limit=${limit}`);
  if (!r.ok) throw new Error(`list discovery runs: ${r.status}`);
  const body = (await r.json()) as { runs: DiscoveryRunListItem[] };
  return body.runs;
}

// Canonical node order — used by the graph component to render the pipeline
// even before any state has arrived.
export const DISCOVERY_NODES = [
  "signal_agent",
  "evidence_agent",
  "hypothesis_agent",
  "evaluator_agent",
  "human_review_gate",
] as const;

export type DiscoveryNodeName = (typeof DISCOVERY_NODES)[number];

export const NODE_LABELS: Record<DiscoveryNodeName, string> = {
  signal_agent: "Signal",
  evidence_agent: "Evidence",
  hypothesis_agent: "Hypothesis",
  evaluator_agent: "Evaluator",
  human_review_gate: "Human Review",
};

export const EVIDENCE_LAYERS = ["wiki", "field_feedback", "pattern_memory"] as const;
export type EvidenceLayerName = (typeof EVIDENCE_LAYERS)[number];

export const LAYER_LABELS: Record<EvidenceLayerName, string> = {
  wiki: "Governed Wiki RAG",
  field_feedback: "Field Feedback (prior RCAs)",
  pattern_memory: "Time-Series Case Memory",
};
