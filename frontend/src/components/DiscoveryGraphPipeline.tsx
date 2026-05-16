// Horizontal 5-node pipeline. Renders all canonical nodes greyed out,
// highlights the currently-active one in violet, and fills completed nodes
// solid. This is the centerpiece of the /discovery page.

import { Box, Group, Paper, Stack, Text } from "@mantine/core";
import {
  IconActivity,
  IconBooks,
  IconBulb,
  IconChecks,
  IconUserShield,
  type Icon as TablerIcon,
} from "@tabler/icons-react";
import {
  DISCOVERY_NODES,
  DiscoveryNodeName,
  NODE_LABELS,
} from "../api/discovery";

const NODE_ICONS: Record<DiscoveryNodeName, TablerIcon> = {
  signal_agent: IconActivity,
  evidence_agent: IconBooks,
  hypothesis_agent: IconBulb,
  evaluator_agent: IconChecks,
  human_review_gate: IconUserShield,
};

interface Props {
  active: DiscoveryNodeName | null;
  completed: DiscoveryNodeName[];
  hitlRequired?: boolean;
}

export default function DiscoveryGraphPipeline({
  active,
  completed,
  hitlRequired,
}: Props) {
  const completedSet = new Set(completed);
  return (
    <Paper p="md" withBorder>
      <Stack gap="xs">
        <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
          LangGraph state machine
        </Text>
        <Group gap={0} wrap="nowrap" align="stretch">
          {DISCOVERY_NODES.map((node, idx) => {
            const Icon = NODE_ICONS[node];
            const isActive = active === node;
            const isDone = completedSet.has(node);
            const isHITL = node === "human_review_gate" && hitlRequired;
            const bg = isActive
              ? "var(--mantine-color-violet-6)"
              : isHITL
              ? "var(--mantine-color-orange-7)"
              : isDone
              ? "var(--mantine-color-violet-9)"
              : "var(--mantine-color-dark-6)";
            const fg = isActive || isDone || isHITL ? "white" : "var(--mantine-color-dark-1)";
            return (
              <Group key={node} gap={0} wrap="nowrap" style={{ flex: 1 }} align="stretch">
                <Box
                  style={{
                    flex: 1,
                    background: bg,
                    color: fg,
                    padding: "12px 10px",
                    borderRadius: 6,
                    minWidth: 0,
                    transition: "background 0.2s ease",
                  }}
                >
                  <Stack gap={2} align="center">
                    <Icon size={20} stroke={1.5} />
                    <Text size="xs" fw={600} ta="center" lh={1.2}>
                      {NODE_LABELS[node]}
                    </Text>
                    {isActive && (
                      <Text size="9px" fw={500} c="violet.0">
                        running…
                      </Text>
                    )}
                    {isHITL && (
                      <Text size="9px" fw={500} c="orange.0">
                        HITL required
                      </Text>
                    )}
                  </Stack>
                </Box>
                {idx < DISCOVERY_NODES.length - 1 && (
                  <Box
                    style={{
                      width: 18,
                      alignSelf: "center",
                      borderTop:
                        "1px dashed var(--mantine-color-dark-3)",
                    }}
                  />
                )}
              </Group>
            );
          })}
        </Group>
      </Stack>
    </Paper>
  );
}
