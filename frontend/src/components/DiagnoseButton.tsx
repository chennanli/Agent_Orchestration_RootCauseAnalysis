import { useState } from "react";
import { Anchor, Button, Group, Loader, Stack, Text } from "@mantine/core";
import { IconBolt, IconCheck, IconRefresh, IconAlertTriangle } from "@tabler/icons-react";
import { AgentStreamPhase } from "../hooks/useAgentStream";
import { AnomalyState } from "../api/agent";

interface Props {
  phase: AgentStreamPhase;
  armed: boolean;
  anomaly: AnomalyState | null;
  onDiagnose: () => void;
  onReset: () => void;
  liveBufferLen: number;
  /**
   * `true` when the user has selected a pre-baked fault snapshot. In that
   * mode the button is always enabled (we don't need live PCA arming
   * because there's a real snapshot to diagnose right away).
   */
  seededFaultMode: boolean;
}

/**
 * The big "Diagnose Now" button. State machine:
 *
 *   idle     — no run yet
 *   armed    — anomaly detector flagged a spike; button glows red
 *   submitting — POST /api/agent/diagnose pending
 *   streaming — SSE in flight; button is disabled
 *   done     — run completed; offer "Diagnose again"
 *   error    — show retry
 */
export default function DiagnoseButton({
  phase,
  armed,
  anomaly,
  onDiagnose,
  onReset,
  liveBufferLen,
  seededFaultMode,
}: Props) {
  const running = phase === "submitting" || phase === "streaming";

  let color = "blue";
  let label = "Diagnose Now";
  let icon = <IconBolt size={18} />;
  let subtitle = "Press to run NAT on the current live snapshot.";
  let onClick = onDiagnose;

  if (armed && phase === "idle") {
    color = "red";
    label = "Diagnose Now — anomaly detected";
    subtitle = `Anomaly detected (${anomaly?.consecutive_anomalies ?? 0} consecutive samples over threshold).`;
  }
  if (phase === "submitting") {
    label = "Starting...";
    icon = <Loader size={16} />;
    subtitle = "Snapshotting live buffer and dispatching NAT.";
  }
  if (phase === "streaming") {
    label = "Streaming agent steps...";
    icon = <Loader size={16} />;
    subtitle = "Each step below appears as the agent emits it.";
  }
  if (phase === "done") {
    color = "green";
    label = "Diagnose again";
    icon = <IconCheck size={18} />;
    subtitle = "Done. Press to dispatch a new run.";
    onClick = onReset;
  }
  if (phase === "error") {
    color = "red";
    label = "Retry";
    icon = <IconAlertTriangle size={18} />;
    subtitle = "Last run failed. See the error below; press to retry.";
    onClick = onReset;
  }

  // "Override" lets the user bypass arming when they're confident the
  // process is misbehaving but the detector hasn't fired yet (e.g. an
  // early-stage slow drift). Click count, not a toggle — one click flips
  // it on for the next diagnose.
  const [override, setOverride] = useState(false);

  // Gate the button so users follow the intended flow:
  //   sim running → trigger IDV → wait for PCA to arm → THEN diagnose
  // Seeded-fault mode (user picked a pre-baked fault snapshot from the
  // dropdown) bypasses arming because there's a real snapshot to diagnose.
  // Override is a manual escape hatch.
  const liveAllowed = armed || override;
  const disabled =
    running ||
    (phase === "idle" && !seededFaultMode && liveBufferLen === 0) ||
    (phase === "idle" && !seededFaultMode && !liveAllowed && liveBufferLen > 0);

  // Update the subtitle so users understand WHY the button is disabled.
  if (phase === "idle" && !seededFaultMode && liveBufferLen > 0 && !armed && !override) {
    subtitle =
      "Waiting for anomaly detection to arm. Turn an IDV knob ≥50% to inject a disturbance, or use Override below.";
  }
  if (phase === "idle" && override) {
    subtitle = "Override on — will diagnose the current live snapshot regardless of detector state.";
  }

  return (
    <Stack gap={6}>
      <Button
        size="lg"
        color={color}
        leftSection={icon}
        rightSection={
          phase === "done" || phase === "error" ? (
            <IconRefresh size={16} />
          ) : null
        }
        onClick={onClick}
        disabled={disabled}
        fullWidth
        styles={{
          root: armed && phase === "idle"
            ? { boxShadow: "0 0 0 3px rgba(255, 89, 112, 0.25)" }
            : undefined,
        }}
      >
        {label}
      </Button>
      <Group justify="space-between" gap={6} wrap="nowrap">
        <Text size="xs" c="dimmed" style={{ lineHeight: 1.3 }}>
          {subtitle}
        </Text>
        <Text size="xs" c="dimmed">
          buffer: {liveBufferLen} pts
        </Text>
      </Group>

      {/* Override escape hatch: lets the user diagnose even when PCA hasn't
          armed. Only shows in live mode (seeded fault snapshots are
          always diagnosable without override). */}
      {phase === "idle" && !seededFaultMode && (
        <Group justify="flex-end" gap={6}>
          {override && (
            <Text size="xs" c="orange.4" ff="monospace">
              override on
            </Text>
          )}
          <Anchor
            component="button"
            type="button"
            size="xs"
            c="dimmed"
            onClick={() => setOverride((v) => !v)}
          >
            {override
              ? "✕ cancel override"
              : "override: diagnose anyway →"}
          </Anchor>
        </Group>
      )}
    </Stack>
  );
}
