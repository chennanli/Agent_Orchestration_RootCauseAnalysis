import {
  ActionIcon,
  Alert,
  Badge,
  Card,
  Group,
  ScrollArea,
  Stack,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";
import {
  IconAlertTriangle,
  IconHistory,
  IconShieldCheck,
} from "@tabler/icons-react";
import DiagnoseButton from "./DiagnoseButton";
import TraceStep from "./TraceStep";
import FollowupChat from "./FollowupChat";
import ModelSelector from "./ModelSelector";
import BakeoffCard from "./BakeoffCard";
import { AgentStreamState } from "../hooks/useAgentStream";
import { AnomalyState } from "../api/agent";

interface DiagnoseOpts {
  question?: string;
  model_id?: string | null;
  api_key?: string | null;
  points?: number;
}

interface Props {
  stream: AgentStreamState & {
    startWithFault: (faultId: string, opts?: DiagnoseOpts) => void;
    startWithLive: (opts?: DiagnoseOpts) => void;
    reset: () => void;
  };
  anomaly: AnomalyState | null;
  liveBufferLen: number;
  seededFaultId: string | null;
  onOpenHistory: () => void;
  modelId: string | null;
  apiKey: string | null;
  onModelChange: (modelId: string, apiKey: string | null) => void;
}

/**
 * Right-hand panel. From top to bottom:
 *   - DiagnoseButton (the only thing that ever calls the LLM)
 *   - The live trace timeline (streams in as SSE events arrive)
 *   - Final Answer card + policy badge (when phase === "done")
 */
export default function AgentTimelinePanel({
  stream,
  anomaly,
  liveBufferLen,
  seededFaultId,
  onOpenHistory,
  modelId,
  apiKey,
  onModelChange,
}: Props) {
  const armed = anomaly?.armed ?? false;

  const dispatch = () => {
    const opts = { model_id: modelId, api_key: apiKey };
    if (seededFaultId) {
      stream.startWithFault(seededFaultId, opts);
    } else {
      stream.startWithLive(opts);
    }
  };

  const finalText = stream.final?.final_answer?.text ?? "";
  const safe = stream.final?.final_answer?.policy_check?.is_advisory_safe;

  return (
    <Stack gap="sm" style={{ height: "100%" }}>
      <Card withBorder padding="sm" radius="md">
        <Stack gap={6}>
          <Group justify="space-between" align="center" wrap="nowrap">
            <Group gap={6}>
              <Title order={4}>Agent Reasoning</Title>
              <Tooltip label="Past runs">
                <ActionIcon
                  variant="subtle"
                  size="sm"
                  onClick={onOpenHistory}
                  aria-label="open history drawer"
                >
                  <IconHistory size={16} />
                </ActionIcon>
              </Tooltip>
            </Group>
            <Text size="xs" c="dimmed">
              {stream.phase === "idle" && "press Diagnose Now to start"}
              {stream.phase === "submitting" && "snapshotting…"}
              {stream.phase === "streaming" &&
                `streaming · ${stream.steps.length} steps so far`}
              {stream.phase === "done" &&
                `done · ${stream.durationSec ?? "?"}s · ${stream.steps.length} steps`}
              {stream.phase === "error" && "failed"}
            </Text>
          </Group>
          <ModelSelector
            selectedModelId={modelId}
            onChange={onModelChange}
          />
          <DiagnoseButton
            phase={stream.phase}
            armed={armed}
            anomaly={anomaly}
            onDiagnose={dispatch}
            onReset={stream.reset}
            liveBufferLen={liveBufferLen}
            seededFaultMode={Boolean(seededFaultId)}
          />
          {seededFaultId && (
            <Text size="xs" c="dimmed">
              Will diagnose <b>{seededFaultId}</b> (pre-baked snapshot). Clear
              the selector in the left panel to diagnose live data instead.
            </Text>
          )}
        </Stack>
      </Card>

      <Card
        withBorder
        padding="xs"
        radius="md"
        style={{ flex: 1, minHeight: 200 }}
      >
        <Stack gap={4} style={{ height: "100%" }}>
          <Group justify="space-between" align="center" px={6}>
            <Text size="sm" fw={600}>
              Trace
            </Text>
            <Text size="xs" c="dimmed">
              {stream.steps.length} step{stream.steps.length === 1 ? "" : "s"}
            </Text>
          </Group>
          <ScrollArea offsetScrollbars style={{ flex: 1 }}>
            {stream.steps.length === 0 && stream.phase === "idle" && (
              <Text size="xs" c="dimmed" ta="center" py="xl">
                When you press Diagnose Now, each Thought / Action /
                Observation will appear here as the agent emits it.
              </Text>
            )}
            {stream.steps.map((s, i) => (
              <TraceStep key={i} step={s} index={i} />
            ))}
          </ScrollArea>
        </Stack>
      </Card>

      {stream.phase === "error" && stream.error && (
        <Alert
          color="red"
          variant="light"
          icon={<IconAlertTriangle size={16} />}
          title="NAT run failed"
        >
          <Text size="xs" ff="monospace">
            {stream.error}
          </Text>
        </Alert>
      )}

      {stream.phase === "done" && stream.final && (
        <>
          <Card withBorder padding="sm" radius="md">
            <Group justify="space-between" align="center" mb={6}>
              <Title order={5}>Final advisory</Title>
              <Badge
                color={safe ? "green" : "red"}
                variant="light"
                leftSection={<IconShieldCheck size={12} />}
              >
                {safe ? "policy safe" : "policy flagged"}
              </Badge>
            </Group>
            <Text size="sm" style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
              {finalText || "(no advisory text)"}
            </Text>
            <Text size="xs" c="dimmed" mt={6}>
              {stream.final.final_answer?.safety_notice}
            </Text>
          </Card>

          {stream.runId && (
            <FollowupChat
              runId={stream.runId}
              initialFollowups={stream.final.followups ?? []}
              modelId={modelId}
              apiKey={apiKey}
            />
          )}

          {/*
            Bake-off card: on-demand "naive LLM vs NAT agent" side-by-side
            comparison. This is the highest-impact way to demonstrate WHY
            agent orchestration matters — same model, same snapshot, with
            and without tools. We render it after the final advisory so
            the user reads the agent's answer first, then sees the gap.
          */}
          {stream.runId && (
            <BakeoffCard
              runId={stream.runId}
              modelId={modelId}
              apiKey={apiKey}
            />
          )}
        </>
      )}
    </Stack>
  );
}
