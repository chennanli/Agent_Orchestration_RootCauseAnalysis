// 3-column panel showing the EvidenceAgent's retrieved hits per layer.
// Each column = one of {wiki, field_feedback, pattern_memory}.

import { Badge, Group, Paper, ScrollArea, Stack, Text } from "@mantine/core";
import {
  EVIDENCE_LAYERS,
  EvidenceHit,
  EvidenceLayerName,
  LAYER_LABELS,
} from "../api/discovery";

interface Props {
  evidence: Record<string, EvidenceHit[]> | undefined;
}

function LayerColumn({
  layer,
  hits,
}: {
  layer: EvidenceLayerName;
  hits: EvidenceHit[];
}) {
  return (
    <Paper p="sm" withBorder style={{ flex: 1, minWidth: 0 }}>
      <Stack gap={6}>
        <Group justify="space-between" gap="xs" wrap="nowrap">
          <Text size="xs" fw={600} tt="uppercase" c="violet.3" lh={1.2}>
            {LAYER_LABELS[layer]}
          </Text>
          <Badge size="xs" variant="light" color={hits.length ? "violet" : "gray"}>
            {hits.length}
          </Badge>
        </Group>
        <ScrollArea h={210} type="auto" offsetScrollbars>
          <Stack gap={6}>
            {hits.length === 0 ? (
              <Text size="xs" c="dimmed" fs="italic">
                no hits yet
              </Text>
            ) : (
              hits.slice(0, 6).map((h, i) => (
                <Paper key={i} p={6} withBorder bg="var(--mantine-color-dark-7)">
                  <Stack gap={2}>
                    <Group gap="xs" justify="space-between" wrap="nowrap">
                      <Text size="xs" fw={600} c="violet.1" lineClamp={1}>
                        {h.source || h.known_pattern || "(unknown)"}
                      </Text>
                      {typeof h.score === "number" && (
                        <Badge size="xs" variant="outline" color="violet">
                          {h.score.toFixed(2)}
                        </Badge>
                      )}
                    </Group>
                    {h.section && (
                      <Text size="9px" c="dimmed">
                        §{h.section}
                      </Text>
                    )}
                    {h.text && (
                      <Text size="xs" c="gray.4" lineClamp={3}>
                        {h.text}
                      </Text>
                    )}
                    {h.matched_range && (
                      <Text size="9px" c="dimmed">
                        rows [{h.matched_range[0]}:{h.matched_range[1]}] dist=
                        {typeof h.distance === "number" ? h.distance.toFixed(2) : "?"}
                      </Text>
                    )}
                    {h.substrates && h.substrates.length > 0 && (
                      <Group gap={4}>
                        {h.substrates.map((s) => (
                          <Badge key={s} size="xs" variant="dot" color="violet">
                            {s}
                          </Badge>
                        ))}
                      </Group>
                    )}
                    {h.via === "a2a" && (
                      <Badge size="xs" variant="light" color="cyan">
                        via A2A
                      </Badge>
                    )}
                  </Stack>
                </Paper>
              ))
            )}
          </Stack>
        </ScrollArea>
      </Stack>
    </Paper>
  );
}

export default function EvidenceByLayerPanel({ evidence }: Props) {
  const ev = evidence ?? {};
  return (
    <Stack gap="xs">
      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
        Evidence by layer
      </Text>
      <Group gap="xs" align="stretch" wrap="nowrap">
        {EVIDENCE_LAYERS.map((layer) => (
          <LayerColumn
            key={layer}
            layer={layer}
            hits={(ev[layer] as EvidenceHit[]) ?? []}
          />
        ))}
      </Group>
    </Stack>
  );
}
