import { useEffect, useState } from "react";
import { getAnomalyState, AnomalyState } from "../api/agent";

interface State {
  state: AnomalyState | null;
  error: string | null;
}

/**
 * Poll `/api/anomaly/state` every `intervalMs` (default 2s).
 *
 * The PCA detector runs on every `/ingest` call on the backend, so polling
 * cheap state is enough for the UI; no SSE needed here.
 */
export function useAnomalyState(intervalMs = 2000): State {
  const [state, setState] = useState<State>({ state: null, error: null });

  useEffect(() => {
    let cancelled = false;

    const tick = async () => {
      try {
        const s = await getAnomalyState();
        if (!cancelled) setState({ state: s, error: null });
      } catch (e) {
        if (!cancelled) {
          setState((prev) => ({
            state: prev.state,
            error: (e as Error).message,
          }));
        }
      }
    };

    tick();
    const handle = window.setInterval(tick, intervalMs);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, [intervalMs]);

  return state;
}
