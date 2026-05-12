import { useState } from "react";
import {
  Badge,
  Box,
  Button,
  Card,
  Code,
  Grid,
  Group,
  Loader,
  Stack,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";
import {
  IconArrowsLeftRight,
  IconRobot,
  IconSparkles,
  IconAlertCircle,
} from "@tabler/icons-react";
import { BakeoffResult, bakeoff } from "../api/agent";

interface Props {
  runId: string;
  modelId?: string | null;
  apiKey?: string | null;
}

/**
 * "Naive LLM vs NAT Agent" side-by-side bake-off.
 *
 * Industry-standard demo pattern for justifying agent orchestration: run
 * the SAME question against the SAME LLM on the SAME snapshot, with NO
 * tools, and show both answers side-by-side. The naive answer is usually
 * vague ("may be a cooling-related deviation"); the agent answer is
 * specific ("XMV_6 saturated at 87%, see Downs & Vogel §5.4"). The gap
 * is the value of orchestration.
 *
 * Renders three at-a-glance metrics under each column:
 *   - runtime (the agent is slower; that's the cost)
 *   - XMV/XMEAS tags mentioned (specificity)
 *   - tool calls / cited sources (only the agent has these)
 */
export default function BakeoffCard({ runId, modelId, apiKey }: Props) {
  const [result, setResult] = useState<BakeoffResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await bakeoff(runId, { model_id: modelId, api_key: apiKey });
      setResult(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card withBorder padding="sm" radius="md">
      <Stack gap="sm">
        <Group justify="space-between" align="center">
          <Title order={5}>
            <Group gap={6}>
              <IconArrowsLeftRight size={16} />
              Bake-off: naive LLM vs NAT agent
            </Group>
          </Title>
          {!result && (
            <Tooltip
              label={
                modelId
                  ? `runs the selected model with NO tools on the same snapshot`
                  : `runs the default model with NO tools on the same snapshot`
              }
            >
              <Button
                size="xs"
                variant="light"
                onClick={run}
                disabled={loading}
                leftSection={
                  loading ? <Loader size={12} /> : <IconSparkles size={14} />
                }
              >
                {loading ? "Running..." : "Compare"}
              </Button>
            </Tooltip>
          )}
        </Group>

        {!result && !error && !loading && (
          <Text size="xs" c="dimmed">
            Press <b>Compare</b> to ask the same LLM the same question on
            the same snapshot — but <i>without</i> any tools. The gap
            between the two answers is the value of orchestration.
          </Text>
        )}

        {error && (
          <Group gap={6}>
            <IconAlertCircle size={14} color="red" />
            <Text size="xs" c="red" ff="monospace">
              {error}
            </Text>
          </Group>
        )}

        {result && <BakeoffResultView result={result} />}
      </Stack>
    </Card>
  );
}

function BakeoffResultView({ result }: { result: BakeoffResult }) {
  const { naive, agent } = result;
  const tagGap = agent.tag_count - naive.tag_count;
  return (
    <Grid gutter="sm">
      <Grid.Col span={{ base: 12, md: 6 }}>
        <Stack gap={6}>
          <Group gap={6} align="center">
            <Badge variant="light" color="gray" leftSection={<IconRobot size={12} />}>
              naive LLM · no tools
            </Badge>
            <Text size="xs" c="dimmed">
              {naive.runtime_seconds}s · {naive.model_id}
            </Text>
          </Group>
          <Box
            style={{
              border: "1px solid var(--mantine-color-gray-7)",
              borderRadius: 6,
              padding: 8,
              minHeight: 140,
            }}
          >
            <Text size="sm" style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
              {naive.text || "(empty)"}
            </Text>
          </Box>
          <Group gap={6}>
            <Badge size="xs" variant="light" color="gray">
              {naive.tag_count} XMV/XMEAS tag{naive.tag_count === 1 ? "" : "s"}
            </Badge>
            <Badge size="xs" variant="light" color="gray">
              0 tools called
            </Badge>
            <Badge size="xs" variant="light" color="gray">
              0 sources cited
            </Badge>
          </Group>
        </Stack>
      </Grid.Col>

      <Grid.Col span={{ base: 12, md: 6 }}>
        <Stack gap={6}>
          <Group gap={6} align="center">
            <Badge
              variant="light"
              color="violet"
              leftSection={<IconSparkles size={12} />}
            >
              NAT agent · with tools
            </Badge>
            <Text size="xs" c="dimmed">
              {agent.runtime_seconds ?? "?"}s · {agent.model_id ?? "?"}
            </Text>
          </Group>
          <Box
            style={{
              border: "1px solid var(--mantine-color-violet-7)",
              borderRadius: 6,
              padding: 8,
              minHeight: 140,
            }}
          >
            <Text size="sm" style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
              {agent.text || "(empty)"}
            </Text>
          </Box>
          <Group gap={6}>
            <Tooltip label={agent.tags.join(", ") || "no tags found"}>
              <Badge size="xs" variant="light" color="violet">
                {agent.tag_count} XMV/XMEAS tag{agent.tag_count === 1 ? "" : "s"}
              </Badge>
            </Tooltip>
            <Tooltip label={agent.tool_calls.join(" → ") || "no tools"}>
              <Badge size="xs" variant="light" color="violet">
                {agent.tool_count} tool call{agent.tool_count === 1 ? "" : "s"}
              </Badge>
            </Tooltip>
            <Tooltip label={agent.sources_cited.join(", ") || "no citations"}>
              <Badge size="xs" variant="light" color="violet">
                {agent.sources_cited.length} source
                {agent.sources_cited.length === 1 ? "" : "s"} cited
              </Badge>
            </Tooltip>
          </Group>
        </Stack>
      </Grid.Col>

      <Grid.Col span={12}>
        <Card withBorder padding={8} radius="sm">
          <Group gap={6}>
            <Text size="xs" c="dimmed">
              Specificity delta:
            </Text>
            <Badge
              size="xs"
              variant="filled"
              color={tagGap > 0 ? "violet" : tagGap < 0 ? "gray" : "yellow"}
            >
              {tagGap > 0 ? "+" : ""}
              {tagGap} tag{Math.abs(tagGap) === 1 ? "" : "s"} (agent vs naive)
            </Badge>
            <Text size="xs" c="dimmed">
              · Tool orchestration forced the agent to read the actual
              snapshot, rank contributing variables, and cite source
              documents. The naive LLM only saw raw numbers.
            </Text>
          </Group>
        </Card>
      </Grid.Col>
    </Grid>
  );
}
