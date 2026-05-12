import { useCallback, useEffect, useRef, useState } from "react";
import {
  AgentRun,
  TraceStepPayload,
  diagnoseFault,
  diagnoseLive,
  getRun,
} from "../api/agent";

// Persist the last completed run id across navigations so leaving Live
// Copilot → LLM Wiki → coming back doesn't wipe what you just diagnosed.
const STORAGE_KEY = "tep_copilot_last_run_id";

export type AgentStreamPhase =
  | "idle"
  | "submitting"
  | "streaming"
  | "done"
  | "error";

export interface AgentStreamState {
  phase: AgentStreamPhase;
  runId: string | null;
  faultId: string | null;
  steps: TraceStepPayload[];
  final: AgentRun | null;
  error: string | null;
  startedAt: number | null;
  durationSec: number | null;
}

const INITIAL: AgentStreamState = {
  phase: "idle",
  runId: null,
  faultId: null,
  steps: [],
  final: null,
  error: null,
  startedAt: null,
  durationSec: null,
};

/**
 * Drives the diagnose-and-stream lifecycle.
 *
 * - `startWithFault(id, q?)` runs against a seeded fault (e.g. "fault1")
 * - `startWithLive(q?)` snapshots the current live buffer and runs against
 *    that snapshot
 *
 * The hook opens an EventSource to `/api/agent/runs/{id}/stream`, accumulates
 * each `step` event into `steps`, and sets `final` on `done`.
 * `reset()` clears state for the next run.
 */
export function useAgentStream() {
  const [state, setState] = useState<AgentStreamState>(INITIAL);
  const esRef = useRef<EventSource | null>(null);

  const closeStream = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
  }, []);

  const reset = useCallback(() => {
    closeStream();
    setState(INITIAL);
    // Clear the persisted last-run id so a fresh "Diagnose Now" starts clean.
    try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
  }, [closeStream]);

  const openStream = useCallback(
    (runId: string, faultId: string, startedAt: number) => {
      closeStream();
      const url = `/api/agent/runs/${encodeURIComponent(runId)}/stream`;
      const es = new EventSource(url);
      esRef.current = es;

      es.addEventListener("step", (ev) => {
        try {
          const step = JSON.parse((ev as MessageEvent).data) as TraceStepPayload;
          setState((s) => ({
            ...s,
            phase: "streaming",
            steps: [...s.steps, step],
          }));
        } catch {
          // ignore malformed events
        }
      });

      es.addEventListener("done", (ev) => {
        let final: AgentRun | null = null;
        try {
          final = JSON.parse((ev as MessageEvent).data) as AgentRun;
        } catch {
          // ignore
        }
        const dur = (Date.now() - startedAt) / 1000;
        setState((s) => ({
          ...s,
          phase: "done",
          final,
          durationSec: Math.round(dur * 10) / 10,
        }));
        // Persist so navigating away → coming back rehydrates this run.
        try { localStorage.setItem(STORAGE_KEY, runId); } catch { /* ignore */ }
        closeStream();
      });

      es.addEventListener("error", (ev) => {
        // SSE 'error' event from the server (we emit one before done on failure).
        const data = (ev as MessageEvent).data;
        let msg = "stream error";
        if (typeof data === "string") {
          try {
            msg = (JSON.parse(data).message as string) ?? data;
          } catch {
            msg = data;
          }
        }
        setState((s) => ({
          ...s,
          phase: "error",
          error: msg || "stream closed unexpectedly",
        }));
        closeStream();
      });

      es.onerror = () => {
        // Native transport-level error (network drop). Only surface if we
        // haven't already finished.
        setState((s) =>
          s.phase === "done" || s.phase === "error"
            ? s
            : {
                ...s,
                phase: "error",
                error: "connection to /api/agent/runs/.../stream lost",
              },
        );
        closeStream();
      };

      setState({
        phase: "streaming",
        runId,
        faultId,
        steps: [],
        final: null,
        error: null,
        startedAt,
        durationSec: null,
      });
    },
    [closeStream],
  );

  const startWithFault = useCallback(
    async (
      faultId: string,
      opts: { question?: string; model_id?: string | null; api_key?: string | null } = {},
    ) => {
      const started = Date.now();
      setState({ ...INITIAL, phase: "submitting", startedAt: started, faultId });
      try {
        const r = await diagnoseFault(faultId, opts);
        openStream(r.run_id, r.fault_id, started);
      } catch (e) {
        setState((s) => ({
          ...s,
          phase: "error",
          error: (e as Error).message,
        }));
      }
    },
    [openStream],
  );

  const startWithLive = useCallback(
    async (
      opts: { question?: string; model_id?: string | null; api_key?: string | null; points?: number } = {},
    ) => {
      const started = Date.now();
      setState({
        ...INITIAL,
        phase: "submitting",
        startedAt: started,
        faultId: null,
      });
      try {
        const r = await diagnoseLive(opts.points ?? 200, opts);
        openStream(r.run_id, r.fault_id, started);
      } catch (e) {
        setState((s) => ({
          ...s,
          phase: "error",
          error: (e as Error).message,
        }));
      }
    },
    [openStream],
  );

  const loadFromDisk = useCallback(
    async (runId: string) => {
      closeStream();
      setState({ ...INITIAL, phase: "submitting", runId });
      try {
        const run = await getRun(runId);
        setState({
          phase: "done",
          runId: run.run_id ?? runId,
          faultId: run.fault_id,
          steps: run.tool_trace ?? [],
          final: run,
          error: null,
          startedAt: null,
          durationSec: run.runtime_seconds ?? null,
        });
      } catch (e) {
        setState({
          ...INITIAL,
          phase: "error",
          error: (e as Error).message,
          runId,
        });
      }
    },
    [closeStream],
  );

  // On first mount, if there's a saved run id from a previous navigation,
  // auto-rehydrate it so the user's last analysis is still visible.
  useEffect(() => {
    if (state.phase !== "idle") return;
    let saved: string | null = null;
    try { saved = localStorage.getItem(STORAGE_KEY); } catch { /* ignore */ }
    if (saved) loadFromDisk(saved);
    // Run once on mount. loadFromDisk is stable (useCallback) — including
    // it would re-fire on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const clearSaved = useCallback(() => {
    try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
    setState(INITIAL);
  }, []);

  return {
    ...state,
    startWithFault,
    startWithLive,
    loadFromDisk,
    reset,
    clearSaved,
  };
}
