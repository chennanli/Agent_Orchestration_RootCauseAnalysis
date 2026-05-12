import { useMemo, useState } from "react";
import { Grid } from "@mantine/core";
import LiveSimPanel from "../components/LiveSimPanel";
import AgentTimelinePanel from "../components/AgentTimelinePanel";
import HistoryDrawer from "../components/HistoryDrawer";
import { useAgentStream } from "../hooks/useAgentStream";
import { useAnomalyState } from "../hooks/useAnomalyState";
import { useLiveBuffer } from "../hooks/useLiveBuffer";
import { TraceStepPayload } from "../api/agent";

// Walk the agent's trace, find the rank_contributing_variables FUNCTION_END
// step, and pull its top_variables list. Returns up to 6 friendly names.
function extractTopVariables(steps: TraceStepPayload[]): string[] {
  for (const s of steps) {
    const p = s.payload || {};
    if (
      p.event_type === "FUNCTION_END" &&
      p.name === "rank_contributing_variables"
    ) {
      const data = (p.data || {}) as { output?: unknown };
      const out = data.output as { top_variables?: { variable?: string }[] } | undefined;
      const vars = out?.top_variables;
      if (Array.isArray(vars)) {
        return vars
          .map((v) => v.variable)
          .filter((x): x is string => typeof x === "string" && x.length > 0)
          .slice(0, 6);
      }
    }
  }
  return [];
}

/**
 * The TEP Live Copilot — main page.
 *
 *   left 60%   LiveSimPanel
 *   right 40%  AgentTimelinePanel
 *
 * The agent never runs automatically. The user presses Diagnose Now in the
 * right panel; the snapshot is frozen, NAT is dispatched, and the trace
 * streams in step by step.
 */
export default function LiveCopilotPage() {
  const stream = useAgentStream();
  const anomaly = useAnomalyState(2000);
  const buffer = useLiveBuffer(200);
  const [seededFaultId, setSeededFaultId] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);

  // Model selection. ModelSelector seeds this on mount via its onChange.
  const [modelId, setModelId] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const handleModelChange = (id: string, key: string | null) => {
    setModelId(id);
    setApiKey(key);
  };

  // After the agent finishes, swap the sparkline grid to the variables IT
  // ranked highest. Falls back to the default 6 until then.
  const agentTopVariables = useMemo(
    () => (stream.steps.length ? extractTopVariables(stream.steps) : []),
    [stream.steps],
  );

  return (
    <>
      <Grid
        gutter="sm"
        style={{ minHeight: "calc(100vh - 90px)" }}
        align="stretch"
      >
        <Grid.Col span={{ base: 12, sm: 7 }} style={{ display: "flex" }}>
          <div style={{ flex: 1 }}>
            <LiveSimPanel
              seededFaultId={seededFaultId}
              onSeededFaultChange={setSeededFaultId}
              agentTopVariables={agentTopVariables}
            />
          </div>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 5 }} style={{ display: "flex" }}>
          <div style={{ flex: 1 }}>
            <AgentTimelinePanel
              stream={stream}
              anomaly={anomaly.state}
              liveBufferLen={buffer.rows.length}
              seededFaultId={seededFaultId}
              onOpenHistory={() => setHistoryOpen(true)}
              modelId={modelId}
              apiKey={apiKey}
              onModelChange={handleModelChange}
            />
          </div>
        </Grid.Col>
      </Grid>
      <HistoryDrawer
        opened={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onSelect={(run) => stream.loadFromDisk(run.run_id)}
      />
    </>
  );
}
