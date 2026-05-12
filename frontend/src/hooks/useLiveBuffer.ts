import { useEffect, useRef, useState } from "react";

/**
 * Subscribe to the legacy `/stream` SSE endpoint that `backend/app.py`
 * already exposes for the old DCS UI, but treat each event as a sensor
 * dict. Drop messages we don't recognise.
 *
 * Returns a rolling window of the last `maxRows` rows (default 200) plus
 * a connection flag and a tick counter.
 */
export interface LiveRow extends Record<string, number> {
  // `time` and a handful of friendly-named sensor columns expected.
  time: number;
}

export interface LiveBufferState {
  rows: LiveRow[];
  connected: boolean;
  lastTickAt: number | null;
  reconnects: number;
}

export function useLiveBuffer(maxRows = 200): LiveBufferState {
  const [state, setState] = useState<LiveBufferState>({
    rows: [],
    connected: false,
    lastTickAt: null,
    reconnects: 0,
  });
  const rowsRef = useRef<LiveRow[]>([]);

  useEffect(() => {
    let cancelled = false;
    let es: EventSource | null = null;

    const open = () => {
      if (cancelled) return;
      es = new EventSource("/stream");
      es.onopen = () => {
        if (cancelled) return;
        setState((s) => ({ ...s, connected: true }));
      };
      es.onerror = () => {
        if (cancelled) return;
        setState((s) => ({
          ...s,
          connected: false,
          reconnects: s.reconnects + 1,
        }));
        es?.close();
        // EventSource auto-reconnects, but defensively reopen if it didn't.
        window.setTimeout(open, 2000);
      };
      es.onmessage = (ev) => {
        if (cancelled) return;
        let parsed: unknown;
        try {
          parsed = JSON.parse(ev.data);
        } catch {
          return;
        }
        if (!parsed || typeof parsed !== "object") return;
        const obj = parsed as Record<string, unknown>;
        // The /stream endpoint sends events in one of three shapes:
        //   { point: {sensor: value, ...} }
        //   { data_point: {sensor: value, ...} }
        //   { "A Feed": value, "D Feed": value, ... }   ← current backend
        // Accept any of them. The "flat dict" shape is detected by the
        // presence of at least one known friendly sensor name.
        const wrapped =
          (obj.point as Record<string, number> | undefined) ||
          (obj.data_point as Record<string, number> | undefined);
        const looksLikeFlatRow =
          typeof obj === "object" &&
          (("A Feed" in obj) ||
            ("Reactor Pressure" in obj) ||
            ("Reactor Temperature" in obj) ||
            ("time" in obj));
        const row =
          wrapped ||
          (looksLikeFlatRow ? (obj as Record<string, number>) : undefined);
        if (!row) return;
        const enriched: LiveRow = {
          ...(row as Record<string, number>),
          time: Number(row.time ?? rowsRef.current.length),
        };
        const next = [...rowsRef.current, enriched];
        if (next.length > maxRows) next.splice(0, next.length - maxRows);
        rowsRef.current = next;
        setState((s) => ({
          ...s,
          rows: next,
          lastTickAt: Date.now(),
        }));
      };
    };

    open();
    return () => {
      cancelled = true;
      es?.close();
    };
  }, [maxRows]);

  return state;
}
