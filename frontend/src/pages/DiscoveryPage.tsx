// AI Discovery Workbench — the React surface for backend/langgraph_rca.py.
//
// Layout:
//   ┌────────────────────────────────────────────────────────────────────┐
//   │ Header: fault selector + Run button + status pill                  │
//   ├────────────────────────────────────────────────────────────────────┤
//   │ 5-node pipeline (active highlight, completed fill, HITL banner)    │
//   ├────────────────────────────────────────────────────────────────────┤
//   │ 3-column evidence panel (wiki / field_feedback / pattern_memory)   │
//   ├────────────────────────────────────────────────────────────────────┤
//   │ Hypotheses (left, 60%)        │ Evaluator verdict + advisory (40%) │
//   └────────────────────────────────────────────────────────────────────┘

import {
  Alert,
  Badge,
  Button,
  Group,
  NativeSelect,
  Paper,
  Stack,
  Text,
  Title,
  Loader,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconPlayerPlayFilled,
  IconRefresh,
} from "@tabler/icons-react";
import { useEffect, useState } from "react";
import DiscoveryGraphPipeline from "../components/DiscoveryGraphPipeline";
import EvaluatorVerdictPanel from "../components/EvaluatorVerdictPanel";
import EvidenceByLayerPanel from "../components/EvidenceByLayerPanel";
import HypothesisRanking from "../components/HypothesisRanking";
import { useDiscoveryStream } from "../hooks/useDiscoveryStream";
import type { DiscoveryStateSnapshot } from "../api/discovery";

const FAULT_OPTIONS = [
  { value: "fault1", label: "fault1 — A/C feed ratio variation" },
  { value: "fault4", label: "fault4 — reactor cooling-water temp step" },
  { value: "fault6", label: "fault6 — A feed loss" },
  { value: "fault7", label: "fault7 — C header pressure loss" },
  { value: "fault11", label: "fault11 — reactor cooling water random" },
  { value: "fault14", label: "fault14 — reactor cooling valve sticking" },
];

const PHASE_COLOR: Record<string, string> = {
  idle: "gray",
  submitting: "violet",
  streaming: "violet",
  done: "green",
  error: "red",
};

export default function DiscoveryPage() {
  const stream = useDiscoveryStream();
  const [faultId, setFaultId] = useState("fault1");
  const isRunning = stream.phase === "submitting" || stream.phase === "streaming";

  // Visible error state when `?replay=<url>` fails. Pure console.error
  // leaves the page looking idle — a reviewer/operator can't tell whether
  // the link is broken or the orchestrator just hasn't been triggered yet.
  const [replayError, setReplayError] = useState<{
    url: string;
    detail: string;
  } | null>(null);

  // `?replay=<url>` hydrates the page from a previously captured run JSON
  // (no SSE, no LLM call). Useful for sharing a finished investigation as a
  // link, for rendering doc screenshots from `docs/sample_runs/*.json`, and
  // for offline review when the orchestrator isn't running.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const replayUrl = params.get("replay");
    if (!replayUrl) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(replayUrl);
        if (!r.ok) {
          const msg = `HTTP ${r.status} ${r.statusText || ""}`.trim();
          console.error(`replay: ${msg} for ${replayUrl}`);
          if (!cancelled) setReplayError({ url: replayUrl, detail: msg });
          return;
        }
        let snapshot: DiscoveryStateSnapshot & {
          fault_id?: string;
          _runtime_seconds?: number;
        };
        try {
          snapshot = (await r.json()) as typeof snapshot;
        } catch (parseExc) {
          const msg =
            parseExc instanceof Error ? parseExc.message : String(parseExc);
          console.error(`replay: JSON parse failed for ${replayUrl}`, parseExc);
          if (!cancelled)
            setReplayError({
              url: replayUrl,
              detail: `JSON parse failed: ${msg}`,
            });
          return;
        }
        if (cancelled) return;
        const replayFault = snapshot.fault_id ?? "fault1";
        setFaultId(replayFault);
        setReplayError(null);
        stream.loadSnapshot(snapshot, replayFault);
      } catch (exc) {
        const msg = exc instanceof Error ? exc.message : String(exc);
        console.error("replay: fetch failed", exc);
        if (!cancelled) setReplayError({ url: replayUrl, detail: msg });
      }
    })();
    return () => {
      cancelled = true;
    };
    // We intentionally run this only once on mount; loadSnapshot is stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Stack gap="md" pb="xl">
      <Group justify="space-between" align="flex-end" wrap="wrap">
        <Stack gap={2}>
          <Title order={3}>AI Discovery Workbench</Title>
          <Text size="sm" c="dimmed">
            5-node LangGraph orchestrator over 4 evidence layers (wiki RAG,
            field feedback, policy catalog, time-series case memory). Research
            prototype; advisory-only.
          </Text>
        </Stack>
        <Group gap="sm">
          <NativeSelect
            value={faultId}
            onChange={(e) => setFaultId(e.currentTarget.value)}
            data={FAULT_OPTIONS}
            disabled={isRunning}
            w={260}
          />
          <Button
            leftSection={
              isRunning ? <Loader size={14} color="white" /> : <IconPlayerPlayFilled size={16} />
            }
            color="violet"
            disabled={isRunning}
            onClick={() => stream.start(faultId)}
          >
            {isRunning ? "running…" : "Run discovery"}
          </Button>
          {stream.phase !== "idle" && (
            <Button
              variant="subtle"
              leftSection={<IconRefresh size={16} />}
              onClick={stream.reset}
              disabled={isRunning}
            >
              Reset
            </Button>
          )}
        </Group>
      </Group>

      {replayError && (
        <Alert
          color="red"
          icon={<IconAlertCircle size={18} />}
          title="Replay failed"
          variant="light"
          withCloseButton
          onClose={() => setReplayError(null)}
        >
          Could not load the saved-run snapshot from{" "}
          <Text component="span" ff="monospace" fw={600}>
            {replayError.url}
          </Text>
          : {replayError.detail}. The page is in the idle state — click{" "}
          <strong>Run discovery</strong> to start a fresh orchestrator run, or
          fix the <code>?replay=</code> URL and reload.
        </Alert>
      )}

      <Group gap="sm" wrap="wrap">
        <Badge size="md" color={PHASE_COLOR[stream.phase] ?? "gray"} variant="light">
          phase: {stream.phase}
        </Badge>
        {stream.runId && (
          <Badge size="md" variant="dot" color="violet">
            run_id: {stream.runId.slice(0, 16)}…
          </Badge>
        )}
        {stream.durationSec !== null && (
          <Badge size="md" variant="light" color="gray">
            runtime: {stream.durationSec.toFixed(1)}s
          </Badge>
        )}
        {typeof stream.state.evaluation?.grounded_ratio === "number" && (
          <Badge size="md" variant="light" color="violet">
            grounded_ratio: {(stream.state.evaluation.grounded_ratio * 100).toFixed(0)}%
          </Badge>
        )}
        {stream.error && (
          <Badge size="md" variant="filled" color="red">
            error: {stream.error.slice(0, 80)}
          </Badge>
        )}
      </Group>

      <DiscoveryGraphPipeline
        active={stream.activeNode}
        completed={stream.nodesCompleted}
        hitlRequired={stream.state.hitl_required}
      />

      <EvidenceByLayerPanel evidence={stream.state.evidence_by_layer} />

      <Group align="flex-start" gap="md" wrap="nowrap" grow>
        <div style={{ flex: 1.4, minWidth: 0 }}>
          <HypothesisRanking hypotheses={stream.state.hypotheses} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <EvaluatorVerdictPanel
            evaluation={stream.state.evaluation}
            revisionCount={stream.state.revision_count ?? 0}
            hitlRequired={stream.state.hitl_required ?? false}
            finalAdvisory={stream.state.final_advisory ?? ""}
            draftAdvisory={stream.state.draft_advisory ?? ""}
          />
        </div>
      </Group>

      <Paper p="sm" withBorder bg="var(--mantine-color-dark-7)">
        <Stack gap={4}>
          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
            Audit trail
          </Text>
          {(stream.state.audit_trail ?? []).length === 0 ? (
            <Text size="xs" c="dimmed" fs="italic">
              no audit entries yet
            </Text>
          ) : (
            (stream.state.audit_trail ?? []).map((entry, i) => (
              <Text key={i} size="11px" c="gray.4" ff="monospace">
                {`[${String(entry.ts ?? "").slice(11, 19)}] ${entry.node}` +
                  (entry.calls_used !== undefined
                    ? ` · calls=${String(entry.calls_used)}`
                    : "") +
                  (entry.hypothesis_count !== undefined
                    ? ` · hypotheses=${String(entry.hypothesis_count)}`
                    : "") +
                  (entry.acceptable !== undefined
                    ? ` · acceptable=${String(entry.acceptable)}`
                    : "") +
                  (entry.decision !== undefined
                    ? ` · decision=${String(entry.decision)}`
                    : "")}
                {entry.plan_parse_error ? (
                  <Text component="span" c="orange.4" ml={6}>
                    · plan_parse_error
                  </Text>
                ) : null}
              </Text>
            ))
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}
