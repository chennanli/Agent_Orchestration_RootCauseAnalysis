// Evaluator's composite verdict: policy check + grounded_ratio + revision
// counter + HITL banner.

import {
  Alert,
  Badge,
  Group,
  Paper,
  Progress,
  Stack,
  Text,
} from "@mantine/core";
import { IconCheck, IconUserShield, IconX } from "@tabler/icons-react";
import { DiscoveryEvaluation } from "../api/discovery";

interface Props {
  evaluation: DiscoveryEvaluation | undefined;
  revisionCount: number;
  hitlRequired: boolean;
  finalAdvisory: string;
  draftAdvisory: string;
}

export default function EvaluatorVerdictPanel({
  evaluation,
  revisionCount,
  hitlRequired,
  finalAdvisory,
  draftAdvisory,
}: Props) {
  const ev = evaluation ?? {};
  const policyOk = ev.policy?.is_advisory_safe;
  const grounded = ev.grounded_ratio ?? 0;
  const groundedPct = Math.round(grounded * 100);
  const acceptable = ev.acceptable;

  return (
    <Stack gap="xs">
      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
        Evaluator verdict + Human-Review gate
      </Text>

      {hitlRequired && (
        <Alert
          color="orange"
          icon={<IconUserShield size={18} />}
          title="Human review required"
          variant="light"
        >
          The Evaluator could not validate this advisory after {revisionCount}{" "}
          revision{revisionCount === 1 ? "" : "s"}. Routed to HITL gate; no
          autonomous action taken.
        </Alert>
      )}

      <Paper p="sm" withBorder>
        <Stack gap="sm">
          <Group justify="space-between" gap="xs">
            <Group gap="xs">
              <Text size="xs" c="dimmed">
                policy_pass
              </Text>
              {policyOk === undefined ? (
                <Badge size="sm" variant="light" color="gray">
                  pending
                </Badge>
              ) : policyOk ? (
                <Badge
                  size="sm"
                  variant="filled"
                  color="green"
                  leftSection={<IconCheck size={11} />}
                >
                  safe
                </Badge>
              ) : (
                <Badge
                  size="sm"
                  variant="filled"
                  color="red"
                  leftSection={<IconX size={11} />}
                >
                  blocked
                </Badge>
              )}
            </Group>
            <Group gap="xs">
              <Text size="xs" c="dimmed">
                revisions
              </Text>
              <Badge size="sm" variant="light" color="violet">
                {revisionCount}
              </Badge>
            </Group>
            <Group gap="xs">
              <Text size="xs" c="dimmed">
                acceptable
              </Text>
              <Badge
                size="sm"
                variant="light"
                color={acceptable ? "green" : acceptable === false ? "red" : "gray"}
              >
                {acceptable === undefined ? "pending" : String(acceptable)}
              </Badge>
            </Group>
          </Group>

          <Stack gap={4}>
            <Group justify="space-between">
              <Text size="xs" c="dimmed">
                grounded_ratio
              </Text>
              <Text size="xs" fw={600}>
                {groundedPct}%
              </Text>
            </Group>
            <Progress
              value={groundedPct}
              size="sm"
              color={grounded >= 0.5 ? "green" : grounded >= 0.25 ? "yellow" : "red"}
            />
          </Stack>

          {ev.feedback && (
            <Paper p={8} bg="var(--mantine-color-dark-7)" radius="sm">
              <Text size="xs" c="gray.3" fs="italic">
                {ev.feedback}
              </Text>
            </Paper>
          )}
        </Stack>
      </Paper>

      <Paper p="sm" withBorder>
        <Stack gap={4}>
          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
            Advisory ({finalAdvisory ? "final" : draftAdvisory ? "draft" : "none yet"})
          </Text>
          <Text size="sm" c="gray.2">
            {finalAdvisory || draftAdvisory || (
              <Text component="span" c="dimmed" fs="italic">
                The HypothesisAgent has not produced a draft yet.
              </Text>
            )}
          </Text>
        </Stack>
      </Paper>
    </Stack>
  );
}
