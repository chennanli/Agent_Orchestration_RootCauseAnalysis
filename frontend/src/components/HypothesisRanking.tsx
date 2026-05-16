// Ranked hypothesis cards from HypothesisAgent's draft.

import { Badge, Group, Paper, Stack, Text } from "@mantine/core";
import { Hypothesis } from "../api/discovery";

interface Props {
  hypotheses: Hypothesis[] | undefined;
}

const CONF_COLOR: Record<string, string> = {
  high: "green",
  medium: "yellow",
  low: "gray",
};

export default function HypothesisRanking({ hypotheses }: Props) {
  const items = hypotheses ?? [];
  return (
    <Stack gap="xs">
      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
        Ranked hypotheses (HypothesisAgent)
      </Text>
      {items.length === 0 ? (
        <Paper p="sm" withBorder>
          <Text size="xs" c="dimmed" fs="italic">
            no hypotheses yet — waiting for the HypothesisAgent node to fire
          </Text>
        </Paper>
      ) : (
        items.slice(0, 3).map((h, i) => {
          const conf = (h.confidence || "").toLowerCase();
          return (
            <Paper key={i} p="sm" withBorder>
              <Stack gap={6}>
                <Group gap="xs" wrap="nowrap" justify="space-between">
                  <Group gap="xs" wrap="nowrap">
                    <Badge size="sm" variant="filled" color="violet">
                      #{h.rank ?? i + 1}
                    </Badge>
                    {h.confidence && (
                      <Badge
                        size="sm"
                        variant="light"
                        color={CONF_COLOR[conf] ?? "gray"}
                      >
                        {h.confidence}
                      </Badge>
                    )}
                  </Group>
                  {h.supporting_evidence_ids && h.supporting_evidence_ids.length > 0 && (
                    <Group gap={4}>
                      {h.supporting_evidence_ids.slice(0, 4).map((eid) => (
                        <Badge key={eid} size="xs" variant="dot" color="violet">
                          {eid}
                        </Badge>
                      ))}
                    </Group>
                  )}
                </Group>
                <Text size="sm" c="gray.2">
                  {h.statement || "(no statement)"}
                </Text>
              </Stack>
            </Paper>
          );
        })
      )}
    </Stack>
  );
}
