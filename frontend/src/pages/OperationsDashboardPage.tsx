import { Stack, Title, Text, SimpleGrid, Card, Group, Badge, List, Divider } from "@mantine/core";
import {
  IconActivityHeartbeat,
  IconChartBar,
  IconRobot,
  IconClipboardCheck,
} from "@tabler/icons-react";
import SafetyBoundaryBanner from "../components/SafetyBoundaryBanner";

const LAYERS = [
  {
    icon: <IconActivityHeartbeat size={18} />,
    title: "1. Physics simulation",
    body: "Tennessee Eastman benchmark process: 52 measured / manipulated variables, deterministic.",
  },
  {
    icon: <IconChartBar size={18} />,
    title: "2. Anomaly detection",
    body: "PCA / Hotelling T² with a fixed demo threshold. Marks the moment the process leaves its trained envelope.",
  },
  {
    icon: <IconRobot size={18} />,
    title: "3. NAT diagnostic tools",
    body: "Six read-only tools: anomaly inspection, variable ranking, knowledge search, sensor windowing, similar faults, advisory policy.",
  },
  {
    icon: <IconClipboardCheck size={18} />,
    title: "4. LLM advisory",
    body: "Operator-facing advisory with citations, evidence variables, policy check. Always requires SME review.",
  },
];

const SCOPE = {
  in: [
    "Read-only fault diagnosis on a benchmark process",
    "Source-cited evidence and tool trace",
    "Self-checked advisory wording (advisory policy)",
    "Workflow-level evaluation with golden cases",
  ],
  out: [
    "Autonomous process control",
    "Production APC / RTO",
    "Certified safety system",
    "Power-grid domain modeling",
  ],
};

export default function OperationsDashboardPage() {
  return (
    <Stack gap="md">
      <div>
        <Title order={2}>TEP Agentic RCA Workbench</Title>
        <Text size="sm" c="dimmed">
          Public portfolio demo. A read-only NeMo Agent Toolkit workflow over the
          Tennessee Eastman benchmark process.
        </Text>
      </div>

      <SafetyBoundaryBanner />

      <Card withBorder padding="md" radius="sm">
        <Title order={4} mb="xs">
          Four layers
        </Title>
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
          {LAYERS.map((l) => (
            <Card key={l.title} withBorder padding="sm" radius="sm">
              <Group gap="xs" mb={4}>
                {l.icon}
                <Text fw={600} size="sm">
                  {l.title}
                </Text>
              </Group>
              <Text size="xs" c="dimmed">
                {l.body}
              </Text>
            </Card>
          ))}
        </SimpleGrid>
      </Card>

      <Card withBorder padding="md" radius="sm">
        <Title order={4} mb="xs">
          What is in / out of scope
        </Title>
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          <div>
            <Badge color="green" variant="light" mb={6}>
              In scope
            </Badge>
            <List size="sm">
              {SCOPE.in.map((s, i) => (
                <List.Item key={i}>{s}</List.Item>
              ))}
            </List>
          </div>
          <div>
            <Badge color="red" variant="light" mb={6}>
              Out of scope
            </Badge>
            <List size="sm">
              {SCOPE.out.map((s, i) => (
                <List.Item key={i}>{s}</List.Item>
              ))}
            </List>
          </div>
        </SimpleGrid>
      </Card>

      <Card withBorder padding="md" radius="sm">
        <Title order={4} mb="xs">
          What does the agent actually do?
        </Title>
        <Text size="sm">
          The agent is given a fault event from the deterministic detector and is
          allowed to call six read-only tools. It chooses which to call and in what
          order, gathers evidence, checks its own advisory wording, and ends with
          an operator-facing summary that is grounded in source citations.
        </Text>
        <Divider my="sm" />
        <Text size="xs" c="dimmed">
          See the <strong>Agent Run</strong> page for a live trace, the{" "}
          <strong>LLM Wiki</strong> for the source documents the agent reads, and{" "}
          <strong>Evaluation</strong> for the workflow-level metrics.
        </Text>
      </Card>
    </Stack>
  );
}
