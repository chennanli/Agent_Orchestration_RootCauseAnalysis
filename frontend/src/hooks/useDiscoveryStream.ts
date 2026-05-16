// SSE driver for the AI Discovery Workbench.
// Mirrors the shape of useAgentStream but for the langgraph_api endpoints.

import { useCallback, useEffect, useRef, useState } from "react";
import {
  DISCOVERY_NODES,
  DiscoveryDoneEvent,
  DiscoveryNodeEvent,
  DiscoveryNodeName,
  DiscoveryStateSnapshot,
  startDiscoveryRun,
} from "../api/discovery";

export type DiscoveryPhase = "idle" | "submitting" | "streaming" | "done" | "error";

export interface DiscoveryStreamState {
  phase: DiscoveryPhase;
  runId: string | null;
  faultId: string | null;
  // Set of nodes that have completed at least once. Set is unordered, but
  // DISCOVERY_NODES gives us the canonical render order.
  nodesCompleted: DiscoveryNodeName[];
  // Last node that fired. For highlighting "currently active".
  activeNode: DiscoveryNodeName | null;
  // Latest accumulated state snapshot.
  state: DiscoveryStateSnapshot;
  error: string | null;
  startedAt: number | null;
  durationSec: number | null;
}

const INITIAL: DiscoveryStreamState = {
  phase: "idle",
  runId: null,
  faultId: null,
  nodesCompleted: [],
  activeNode: null,
  state: {},
  error: null,
  startedAt: null,
  durationSec: null,
};

export function useDiscoveryStream() {
  const [state, setState] = useState<DiscoveryStreamState>(INITIAL);
  const esRef = useRef<EventSource | null>(null);

  const closeStream = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
  }, []);

  // Always tear down on unmount.
  useEffect(() => closeStream, [closeStream]);

  const openStream = useCallback(
    (runId: string, faultId: string) => {
      closeStream();
      const es = new EventSource(`/api/discovery/runs/${runId}/stream`);
      esRef.current = es;

      es.addEventListener("node", (ev: MessageEvent) => {
        try {
          const data = JSON.parse(ev.data) as DiscoveryNodeEvent;
          const nodeName = data.node as DiscoveryNodeName;
          setState((s) => {
            const completed = s.nodesCompleted.includes(nodeName)
              ? s.nodesCompleted
              : [...s.nodesCompleted, nodeName];
            return {
              ...s,
              phase: "streaming",
              activeNode: nodeName,
              nodesCompleted: completed,
              state: { ...s.state, ...data.state },
            };
          });
        } catch (e) {
          console.error("bad node event", e);
        }
      });

      es.addEventListener("done", (ev: MessageEvent) => {
        try {
          const data = JSON.parse(ev.data) as DiscoveryDoneEvent;
          setState((s) => ({
            ...s,
            phase: "done",
            state: data.final ?? s.state,
            durationSec: s.startedAt
              ? (Date.now() - s.startedAt) / 1000
              : null,
            activeNode: null,
          }));
        } finally {
          closeStream();
        }
      });

      es.addEventListener("error", (ev) => {
        // SSE errors fire on close too; only surface if we haven't finished.
        setState((s) => {
          if (s.phase === "done" || s.phase === "error") return s;
          const msg =
            ev instanceof MessageEvent && typeof ev.data === "string"
              ? ev.data
              : "stream interrupted";
          return { ...s, phase: "error", error: msg };
        });
        closeStream();
      });

      setState((s) => ({
        ...s,
        runId,
        faultId,
        phase: "streaming",
      }));
    },
    [closeStream],
  );

  const start = useCallback(
    async (faultId: string, question?: string) => {
      closeStream();
      setState({
        ...INITIAL,
        phase: "submitting",
        faultId,
        startedAt: Date.now(),
      });
      try {
        const started = await startDiscoveryRun(faultId, question);
        openStream(started.run_id, started.fault_id);
      } catch (exc) {
        setState((s) => ({
          ...s,
          phase: "error",
          error: exc instanceof Error ? exc.message : String(exc),
        }));
      }
    },
    [closeStream, openStream],
  );

  const reset = useCallback(() => {
    closeStream();
    setState(INITIAL);
  }, [closeStream]);

  return { ...state, start, reset, canonicalNodes: DISCOVERY_NODES };
}
