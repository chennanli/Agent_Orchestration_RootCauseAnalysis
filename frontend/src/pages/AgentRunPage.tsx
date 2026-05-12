import { useEffect, useState } from "react";
import {
  Stack,
  Title,
  Text,
  SimpleGrid,
  Card,
  Group,
  Badge,
  Select,
  Textarea,
  Button,
  Code,
} from "@mantine/core";
import { IconPlayerPlay, IconRefresh } from "@tabler/icons-react";
import SafetyBoundaryBanner from "../components/SafetyBoundaryBanner";
import ToolTraceTimeline, { ToolTraceStep } from "../components/ToolTraceTimeline";
import EvidenceVariableTable, {
  EvidenceVariableRow,
} from "../components/EvidenceVariableTable";
import AgentAdvisoryPanel, { AgentAdvisory } from "../components/AgentAdvisoryPanel";

interface AgentRun {
  mode?: string;
  fault_id?: string;
  question?: string;
  runtime_seconds?: number;
  tool_trace?: ToolTraceStep[];
  final_answer?: AgentAdvisory & { evidence_variables?: string[] };
  error?: string | null;
}

const FAULT_OPTIONS = [
  "fault0", "fault1", "fault2", "fault3", "fault4", "fault5", "fault6",
  "fault7", "fault8", "fault9", "fault10", "fault11", "fault12",
  "fault13", "fault14", "fault15",
].map((f) => ({ value: f, label: f }));

function extractEvidenceRows(run: AgentRun | null): EvidenceVariableRow[] {
  if (!run?.tool_trace) return [];
  for (const step of run.tool_trace) {
    if (step.tool === "rank_contributing_variables") {
      const out = step.output as any;
      return (out?.top_variables || []) as EvidenceVariableRow[];
    }
  }
  return [];
}

export default function AgentRunPage() {
  const [fault, setFault] = useState<string>("fault1");
  const [question, setQuestion] = useState<string>(
    "Diagnose the current TEP anomaly and recommend operator review steps."
  );
  const [run, setRun] = useState<AgentRun | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchLatest() {
    setError(null);
    try {
      const res = await fetch("/api/agent/runs/latest");
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data = await res.json();
      setRun(data);
    } catch (e: any) {
      setError(`Could not load latest run from /api/agent/runs/latest. ${e?.message ?? e}`);
    }
  }

  async function triggerRun() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/agent/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fault_id: fault, question }),
      });
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data = await res.json();
      setRun(data);
    } catch (e: any) {
      setError(
        `Backend endpoint /api/agent/run is not reachable yet. Use 'python backend/nat_runner.py --tools-only' from a terminal to generate a run JSON. (${e?.message ?? e})`
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchLatest();
  }, []);

  const evidenceRows = extractEvidenceRows(run);
  const policy = run?.final_answer?.policy_check;
  const trajectoryAvailable = !!(run?.tool_trace && run.tool_trace.length);

  return (
    <Stack gap="md">
      <div>
        <Title order={2}>Agent Run</Title>
        <Text size="sm" c="dimmed">
          NAT read-only diagnosis: tool trace, evidence, source excerpts,
          and policy-checked operator advisory.
        </Text>
      </div>

      <SafetyBoundaryBanner variant="compact" />

      <Card withBorder padding="md" radius="sm">
        <Group align="flex-end" gap="md" wrap="wrap">
          <Select
            label="Fault case"
            data={FAULT_OPTIONS}
            value={fault}
            onChange={(v) => v && setFault(v)}
            w={140}
          />
          <Textarea
            label="Operator question"
            value={question}
            onChange={(e) => setQuestion(e.currentTarget.value)}
            autosize
            minRows={1}
            maxRows={2}
            style={{ flex: 1, minWidth: 240 }}
          />
          <Group gap="xs">
            <Button
              leftSection={<IconPlayerPlay size={14} />}
              onClick={triggerRun}
              loading={loading}
            >
              Run agent
            </Button>
            <Button
              variant="default"
              leftSection={<IconRefresh size={14} />}
              onClick={fetchLatest}
            >
              Load latest
            </Button>
          </Group>
        </Group>
        {error && (
          <Text size="xs" c="orange" mt={6}>
            {error}
          </Text>
        )}
      </Card>

      <Card withBorder padding="sm" radius="sm">
        <Group gap="md" wrap="wrap">
          <Group gap={6}>
            <Text size="xs" c="dimmed">
              mode
            </Text>
            <Badge variant="light" color="indigo">
              {run?.mode || "—"}
            </Badge>
          </Group>
          <Group gap={6}>
            <Text size="xs" c="dimmed">
              latency
            </Text>
            <Badge variant="light">
              {typeof run?.runtime_seconds === "number"
                ? `${run.runtime_seconds.toFixed(2)}s`
                : "—"}
            </Badge>
          </Group>
          <Group gap={6}>
            <Text size="xs" c="dimmed">
              tools called
            </Text>
            <Badge variant="light">{run?.tool_trace?.length ?? 0}</Badge>
          </Group>
          <Group gap={6}>
            <Text size="xs" c="dimmed">
              trajectory available
            </Text>
            <Badge variant="light" color={trajectoryAvailable ? "green" : "gray"}>
              {trajectoryAvailable ? "yes" : "no"}
            </Badge>
          </Group>
          {policy && (
            <Group gap={6}>
              <Text size="xs" c="dimmed">
                policy
              </Text>
              <Badge
                variant="light"
                color={policy.is_advisory_safe ? "green" : "red"}
              >
                {policy.is_advisory_safe ? "passed" : "blocked"}
              </Badge>
            </Group>
          )}
        </Group>
      </Card>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <ToolTraceTimeline
          trace={run?.tool_trace || []}
          emptyState={
            "No tool trace yet. Try 'python backend/nat_runner.py --fault fault1 --tools-only' or wire /api/agent/run."
          }
        />
        <EvidenceVariableTable
          rows={evidenceRows}
          caption={
            run?.fault_id
              ? `${run.fault_id} - ranked by precomputed T² contribution`
              : undefined
          }
        />
      </SimpleGrid>

      <AgentAdvisoryPanel advisory={run?.final_answer || null} />

      <Card withBorder padding="md" radius="sm">
        <Title order={5}>Why this is different from fixed RAG</Title>
        <Text size="xs" c="dimmed" mt={4}>
          <Code>Fixed RAG: retrieve once → answer.</Code>
          <br />
          <Code>
            NAT Agent: inspect anomaly → rank variables → search wiki → inspect
            sensor window → find similar faults → check advisory policy → answer.
          </Code>
          <br />
          The label here is <em>tool trace</em>, not hidden reasoning. Every step
          is a real tool call with a real, source-cited result.
        </Text>
      </Card>
    </Stack>
  );
}
