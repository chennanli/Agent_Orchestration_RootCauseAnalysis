import { Card, Group, Text, Stack, Badge, Code, Box } from "@mantine/core";
import {
  IconActivityHeartbeat,
  IconChartBar,
  IconBook2,
  IconWaveSine,
  IconHistory,
  IconShieldCheck,
  IconTool,
} from "@tabler/icons-react";

export interface ToolTraceStep {
  tool: string;
  args?: Record<string, unknown>;
  output?: unknown;
  ts?: string;
}

interface Props {
  trace: ToolTraceStep[];
  emptyState?: string;
}

const ICON_MAP: Record<string, JSX.Element> = {
  inspect_anomaly_snapshot: <IconActivityHeartbeat size={16} />,
  rank_contributing_variables: <IconChartBar size={16} />,
  search_process_knowledge: <IconBook2 size={16} />,
  get_sensor_window: <IconWaveSine size={16} />,
  find_similar_faults: <IconHistory size={16} />,
  check_advisory_policy: <IconShieldCheck size={16} />,
};

function summarizeOutput(tool: string, output: any): string {
  if (output == null) return "no output";
  try {
    if (tool === "inspect_anomaly_snapshot") {
      return `T2=${output.t2_statistic?.toFixed?.(1) ?? "n/a"} idx=${output.anomaly_index} threshold=${output.t2_threshold}`;
    }
    if (tool === "rank_contributing_variables") {
      const top = (output.top_variables || []).slice(0, 3).map((v: any) => v.variable).join(", ");
      return `top: ${top || "n/a"}`;
    }
    if (tool === "search_process_knowledge") {
      const sources = (output.excerpts || []).map((e: any) => e.source_document);
      const dedup = Array.from(new Set(sources)).slice(0, 3);
      return `sources: ${dedup.join(", ") || "n/a"}`;
    }
    if (tool === "get_sensor_window") {
      return `${output.sensor_name}: mean=${output.mean} drift=${output.pct_change_vs_baseline}%`;
    }
    if (tool === "find_similar_faults") {
      const top = (output.matches || []).slice(0, 2).map((m: any) => `${m.fault_id} (${m.score})`);
      return `matches: ${top.join(", ") || "n/a"}`;
    }
    if (tool === "check_advisory_policy") {
      return output.is_advisory_safe ? "advisory safe" : "advisory blocked";
    }
  } catch {
    // fall through
  }
  return JSON.stringify(output).slice(0, 80) + "...";
}

export default function ToolTraceTimeline({ trace, emptyState }: Props) {
  if (!trace || trace.length === 0) {
    return (
      <Card withBorder padding="md" radius="sm">
        <Text size="sm" c="dimmed">
          {emptyState ||
            "No tool trace yet. Trigger an Agent Run to see the read-only tools the agent chose."}
        </Text>
      </Card>
    );
  }

  return (
    <Card withBorder padding="md" radius="sm">
      <Stack gap="xs">
        <Group gap="xs">
          <IconTool size={16} />
          <Text fw={600} size="sm">
            Tool trace ({trace.length} steps)
          </Text>
        </Group>
        <Stack gap={6}>
          {trace.map((step, idx) => (
            <Group
              key={idx}
              wrap="nowrap"
              align="flex-start"
              gap="sm"
              style={{
                borderLeft: "2px solid #c8d0db",
                paddingLeft: 10,
                paddingTop: 4,
                paddingBottom: 4,
              }}
            >
              <Badge variant="light" color="indigo" size="sm" radius="sm">
                {idx + 1}
              </Badge>
              <Box style={{ minWidth: 18, marginTop: 2 }}>
                {ICON_MAP[step.tool] || <IconTool size={16} />}
              </Box>
              <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
                <Group gap={6} wrap="nowrap">
                  <Code>{step.tool}</Code>
                  {step.ts && (
                    <Text size="xs" c="dimmed">
                      {step.ts.slice(11, 19)}
                    </Text>
                  )}
                </Group>
                <Text size="xs" c="dimmed" style={{ wordBreak: "break-word" }}>
                  {summarizeOutput(step.tool, step.output)}
                </Text>
              </Stack>
            </Group>
          ))}
        </Stack>
      </Stack>
    </Card>
  );
}
