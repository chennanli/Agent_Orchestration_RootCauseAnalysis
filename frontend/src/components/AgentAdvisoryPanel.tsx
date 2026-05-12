import { Card, Group, Text, Badge, Stack, Divider, List } from "@mantine/core";
import { IconClipboardCheck, IconShieldCheck, IconAlertTriangle } from "@tabler/icons-react";

export interface AgentAdvisory {
  summary?: string;
  text?: string;
  likely_causes?: string[];
  evidence_variables?: string[];
  recommended_next_inspections?: string[];
  policy_check?: {
    is_advisory_safe?: boolean;
    forbidden_phrases_found?: string[];
    overclaims_found?: string[];
    notes?: string;
  };
  safety_notice?: string;
}

interface Props {
  advisory: AgentAdvisory | null;
}

export default function AgentAdvisoryPanel({ advisory }: Props) {
  if (!advisory) {
    return (
      <Card withBorder padding="md" radius="sm">
        <Text size="sm" c="dimmed">
          No advisory yet. Run the agent to see its read-only diagnosis output.
        </Text>
      </Card>
    );
  }
  const safe = advisory.policy_check?.is_advisory_safe;
  return (
    <Card withBorder padding="md" radius="sm">
      <Stack gap="xs">
        <Group gap="xs" justify="space-between">
          <Group gap="xs">
            <IconClipboardCheck size={16} />
            <Text fw={600} size="sm">
              Operator advisory
            </Text>
          </Group>
          {typeof safe === "boolean" && (
            <Badge
              color={safe ? "green" : "red"}
              variant="light"
              leftSection={safe ? <IconShieldCheck size={12} /> : <IconAlertTriangle size={12} />}
            >
              policy {safe ? "passed" : "blocked"}
            </Badge>
          )}
        </Group>
        <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
          {advisory.summary || advisory.text || "(no advisory text)"}
        </Text>
        {advisory.likely_causes && advisory.likely_causes.length > 0 && (
          <>
            <Divider />
            <Text fw={600} size="xs" c="dimmed" tt="uppercase">
              Likely causes
            </Text>
            <List size="sm">
              {advisory.likely_causes.map((c, i) => (
                <List.Item key={i}>{c}</List.Item>
              ))}
            </List>
          </>
        )}
        {advisory.recommended_next_inspections && advisory.recommended_next_inspections.length > 0 && (
          <>
            <Divider />
            <Text fw={600} size="xs" c="dimmed" tt="uppercase">
              Recommended next inspections
            </Text>
            <List size="sm">
              {advisory.recommended_next_inspections.map((c, i) => (
                <List.Item key={i}>{c}</List.Item>
              ))}
            </List>
          </>
        )}
        {advisory.policy_check && safe === false && (
          <>
            <Divider />
            <Text fw={600} size="xs" c="red" tt="uppercase">
              Policy issues
            </Text>
            <List size="sm" c="red">
              {(advisory.policy_check.forbidden_phrases_found || []).map((p, i) => (
                <List.Item key={"f" + i}>forbidden: "{p}"</List.Item>
              ))}
              {(advisory.policy_check.overclaims_found || []).map((p, i) => (
                <List.Item key={"o" + i}>overclaim: "{p}"</List.Item>
              ))}
            </List>
          </>
        )}
        <Divider />
        <Text size="xs" c="dimmed" fs="italic">
          {advisory.safety_notice ||
            "Advisory only. The agent cannot change setpoints, open/close valves, or control the process. Human review required."}
        </Text>
      </Stack>
    </Card>
  );
}
