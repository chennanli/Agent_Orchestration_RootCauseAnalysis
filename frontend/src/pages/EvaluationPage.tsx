import { useEffect, useState } from "react";
import {
  Stack,
  Title,
  Text,
  SimpleGrid,
  Card,
  Group,
  Badge,
  Table,
  Button,
} from "@mantine/core";
import { IconRefresh, IconClipboardCheck } from "@tabler/icons-react";
import SafetyBoundaryBanner from "../components/SafetyBoundaryBanner";

interface CaseMetrics {
  case_id: string;
  fault_file: string;
  metrics: {
    tool_availability: boolean;
    required_tools_hit: boolean;
    tools_called: string[];
    evidence_variable_hit_rate: number;
    forbidden_phrase_count: number;
    source_citation_present: boolean;
    latency_seconds: number;
    trajectory_available: boolean;
    policy_check_passed: boolean | null;
  };
}

interface Summary {
  total_cases: number;
  tool_availability_pass_rate?: number;
  required_tools_hit_rate?: number;
  avg_evidence_variable_hit_rate?: number;
  forbidden_phrase_total?: number;
  source_citation_present_rate?: number;
  trajectory_available_rate?: number;
  policy_check_pass_rate?: number;
  avg_latency_seconds?: number;
  generated_at?: string;
  mode?: string;
}

const STATIC_DEMO_SUMMARY: Summary = {
  total_cases: 7,
  tool_availability_pass_rate: 1.0,
  required_tools_hit_rate: 1.0,
  avg_evidence_variable_hit_rate: 0.71,
  forbidden_phrase_total: 0,
  source_citation_present_rate: 0.86,
  trajectory_available_rate: 1.0,
  policy_check_pass_rate: 1.0,
  avg_latency_seconds: 0.05,
  mode: "tools (static demo)",
};

function pct(v?: number) {
  if (typeof v !== "number") return "—";
  return `${(v * 100).toFixed(0)}%`;
}

export default function EvaluationPage() {
  const [summary, setSummary] = useState<Summary>(STATIC_DEMO_SUMMARY);
  const [cases, setCases] = useState<CaseMetrics[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/evaluation/summary");
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data = await res.json();
      setSummary(data.summary || STATIC_DEMO_SUMMARY);
      setCases(data.cases || []);
    } catch (e: any) {
      setError(
        `Live evaluation endpoint not available; showing static demo numbers from the latest tools-only run. Run 'python backend/evaluation/evaluate_nat_rca.py --tools-only' and wire /api/evaluation/summary to refresh. (${e?.message ?? e})`
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const kpis = [
    { label: "Cases", value: summary.total_cases ?? 0 },
    { label: "Tool availability", value: pct(summary.tool_availability_pass_rate) },
    { label: "Required tools hit", value: pct(summary.required_tools_hit_rate) },
    {
      label: "Evidence variable hit rate",
      value: pct(summary.avg_evidence_variable_hit_rate),
    },
    { label: "Forbidden phrases", value: summary.forbidden_phrase_total ?? 0 },
    { label: "Source citation present", value: pct(summary.source_citation_present_rate) },
    { label: "Policy check pass rate", value: pct(summary.policy_check_pass_rate) },
    {
      label: "Avg latency",
      value:
        typeof summary.avg_latency_seconds === "number"
          ? `${summary.avg_latency_seconds.toFixed(2)}s`
          : "—",
    },
  ];

  return (
    <Stack gap="md">
      <div>
        <Title order={2}>Evaluation</Title>
        <Text size="sm" c="dimmed">
          Workflow-level evaluation of the NAT RCA workflow against golden cases.
          Not generic RAG evaluation - the metrics reflect tool use, evidence
          recall, source citation, and unsafe-wording avoidance.
        </Text>
      </div>

      <SafetyBoundaryBanner variant="compact" />

      <Card withBorder padding="md" radius="sm">
        <Group justify="space-between" mb="xs">
          <Group gap="xs">
            <IconClipboardCheck size={16} />
            <Text fw={600} size="sm">
              Summary
            </Text>
            {summary.mode && (
              <Badge variant="light" color="indigo">
                mode: {summary.mode}
              </Badge>
            )}
            {summary.generated_at && (
              <Text size="xs" c="dimmed">
                generated {summary.generated_at.slice(0, 19)}
              </Text>
            )}
          </Group>
          <Button
            variant="default"
            size="xs"
            leftSection={<IconRefresh size={14} />}
            onClick={load}
            loading={loading}
          >
            Refresh
          </Button>
        </Group>
        <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="sm">
          {kpis.map((k) => (
            <Card key={k.label} withBorder padding="sm" radius="sm">
              <Text size="xs" c="dimmed">
                {k.label}
              </Text>
              <Text fw={700} size="lg">
                {k.value}
              </Text>
            </Card>
          ))}
        </SimpleGrid>
        {error && (
          <Text size="xs" c="orange" mt={6}>
            {error}
          </Text>
        )}
      </Card>

      <Card withBorder padding="md" radius="sm">
        <Text fw={600} size="sm" mb="xs">
          Per-case detail
        </Text>
        {cases.length === 0 ? (
          <Text size="xs" c="dimmed">
            No live per-case detail. Run the evaluator and wire
            /api/evaluation/summary to surface it here.
          </Text>
        ) : (
          <Table striped highlightOnHover withTableBorder withColumnBorders fz="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Case</Table.Th>
                <Table.Th>Fault</Table.Th>
                <Table.Th>Tools called</Table.Th>
                <Table.Th>Required hit</Table.Th>
                <Table.Th>Evidence hit</Table.Th>
                <Table.Th>Forbidden</Table.Th>
                <Table.Th>Citation</Table.Th>
                <Table.Th>Policy</Table.Th>
                <Table.Th>Latency</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {cases.map((c) => (
                <Table.Tr key={c.case_id}>
                  <Table.Td>{c.case_id}</Table.Td>
                  <Table.Td>{c.fault_file}</Table.Td>
                  <Table.Td>{c.metrics.tools_called.length}</Table.Td>
                  <Table.Td>
                    <Badge color={c.metrics.required_tools_hit ? "green" : "red"} variant="light">
                      {c.metrics.required_tools_hit ? "yes" : "no"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{(c.metrics.evidence_variable_hit_rate * 100).toFixed(0)}%</Table.Td>
                  <Table.Td>{c.metrics.forbidden_phrase_count}</Table.Td>
                  <Table.Td>
                    <Badge color={c.metrics.source_citation_present ? "green" : "gray"} variant="light">
                      {c.metrics.source_citation_present ? "yes" : "no"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      color={
                        c.metrics.policy_check_passed === true
                          ? "green"
                          : c.metrics.policy_check_passed === false
                            ? "red"
                            : "gray"
                      }
                      variant="light"
                    >
                      {c.metrics.policy_check_passed === null
                        ? "n/a"
                        : c.metrics.policy_check_passed
                          ? "passed"
                          : "blocked"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{c.metrics.latency_seconds.toFixed(2)}s</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>
    </Stack>
  );
}
