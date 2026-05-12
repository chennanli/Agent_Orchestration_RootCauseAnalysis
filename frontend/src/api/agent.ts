// Typed fetch helpers for the Live Copilot backend.
//
// All paths are relative; Vite proxies /api/* and /stream to
// http://127.0.0.1:8000 in dev (see vite.config.ts).

export interface T2Point {
  t: number;
  t2_stat: number;
  anomaly: boolean;
}

export interface AnomalyState {
  armed: boolean;
  consecutive_anomalies: number;
  threshold: number;
  buffer_len: number;
  t2_series: T2Point[];
  t2_threshold: number | null;
  last_analysis_excerpt: string | null;
  ts: string;
}

export interface SimStatus {
  sim_alive: boolean;
  source?: string | null;
  reason?: string;
  payload?: unknown;
}

export interface DiagnoseStarted {
  run_id: string;
  fault_id: string;
  started_at: string;
}

export interface RunSummary {
  run_id: string;
  fault_id: string | null;
  started_at: string | null;
  runtime_seconds: number | null;
  policy_safe: boolean | null;
  summary: string;
  followup_count: number;
  error: string | null;
}

export interface PolicyCheck {
  is_advisory_safe: boolean;
  forbidden_phrases_found: string[];
  overclaims_found: string[];
  suggestions: string[];
  notes: string;
}

export interface FinalAnswer {
  text: string;
  policy_check: PolicyCheck;
  safety_notice: string;
}

export interface FollowupEntry {
  q: string;
  a: string;
  ts: string;
}

export interface AgentRun {
  mode: string;
  run_id?: string;
  fault_id: string;
  question: string;
  started_at: string;
  runtime_seconds: number;
  workflow_file?: string;
  snapshot_csv?: string;
  tool_trace: TraceStepPayload[] | null;
  final_answer: FinalAnswer;
  error: string | null;
  followups?: FollowupEntry[];
}

// One step from NAT IntermediateStep, JSON-serialised.
export interface TraceStepPayload {
  parent_id?: string | null;
  function_ancestry?: {
    function_id?: string;
    function_name?: string;
    parent_id?: string | null;
    parent_name?: string | null;
  };
  payload?: {
    event_type?:
      | "WORKFLOW_START"
      | "WORKFLOW_END"
      | "FUNCTION_START"
      | "FUNCTION_END"
      | string;
    event_timestamp?: number;
    name?: string;
    metadata?: Record<string, unknown> | null;
    data?: {
      input?: unknown;
      output?: unknown;
      chunk?: unknown;
      payload?: unknown;
    } | null;
    UUID?: string;
  };
}

async function jget<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) {
    throw new Error(`${path} -> ${r.status} ${await r.text().catch(() => "")}`);
  }
  return (await r.json()) as T;
}

async function jpost<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    throw new Error(`${path} -> ${r.status} ${await r.text().catch(() => "")}`);
  }
  return (await r.json()) as T;
}

// ---- agent endpoints ----

export interface DiagnoseOptions {
  question?: string;
  model_id?: string | null;
  api_key?: string | null;
}

export function diagnoseFault(
  faultId: string,
  opts: DiagnoseOptions = {},
): Promise<DiagnoseStarted> {
  return jpost<DiagnoseStarted>("/api/agent/diagnose", {
    fault_id: faultId,
    question:
      opts.question ??
      "Diagnose the current TEP anomaly and recommend operator review steps.",
    model_id: opts.model_id ?? null,
    api_key: opts.api_key ?? null,
  });
}

export function diagnoseLive(
  points = 200,
  opts: DiagnoseOptions = {},
): Promise<DiagnoseStarted> {
  return jpost<DiagnoseStarted>("/api/agent/diagnose", {
    points,
    question:
      opts.question ??
      "Diagnose the current TEP anomaly and recommend operator review steps.",
    model_id: opts.model_id ?? null,
    api_key: opts.api_key ?? null,
  });
}

// --- Model registry ---

export interface ModelInfo {
  id: string;
  label: string;
  provider: string;
  api_key_env: string;
  api_key_present: boolean;
}

export function listModels(): Promise<{ models: ModelInfo[]; default: string }> {
  return jget("/api/agent/models");
}

export function listRuns(limit = 50): Promise<{ runs: RunSummary[] }> {
  return jget(`/api/agent/runs?limit=${limit}`);
}

export function getRun(runId: string): Promise<AgentRun> {
  return jget(`/api/agent/runs/${encodeURIComponent(runId)}`);
}

export function followup(
  runId: string,
  question: string,
): Promise<FollowupEntry> {
  return jpost(`/api/agent/runs/${encodeURIComponent(runId)}/followup`, {
    question,
  });
}

// ---- state endpoints ----

export function getAnomalyState(): Promise<AnomalyState> {
  return jget("/api/anomaly/state");
}

export function getSimStatus(): Promise<SimStatus> {
  return jget("/api/sim/status");
}

export function setSpeed(speed: number): Promise<unknown> {
  return jpost("/api/sim/speed", { speed });
}

export function triggerFault(
  idv: number,
  magnitude = 1.0,
): Promise<unknown> {
  return jpost("/api/sim/fault", { idv, magnitude });
}
