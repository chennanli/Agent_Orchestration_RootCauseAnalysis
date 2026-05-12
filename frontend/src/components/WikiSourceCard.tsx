import { Card, Group, Text, Badge, Stack } from "@mantine/core";
import { IconBookmark } from "@tabler/icons-react";

export interface WikiSourceExcerpt {
  source_document: string;
  section?: string;
  relevance_score?: number;
  excerpt: string;
  used_in_last_run?: boolean;
  tags?: string[];
}

interface Props {
  excerpt: WikiSourceExcerpt;
  onSelect?: () => void;
  selected?: boolean;
}

export default function WikiSourceCard({ excerpt, onSelect, selected }: Props) {
  return (
    <Card
      withBorder
      radius="sm"
      padding="sm"
      style={{
        cursor: onSelect ? "pointer" : "default",
        background: selected ? "#eef2ff" : undefined,
      }}
      onClick={onSelect}
    >
      <Stack gap={4}>
        <Group justify="space-between" wrap="nowrap" gap="xs">
          <Group gap={6} wrap="nowrap" style={{ minWidth: 0 }}>
            <IconBookmark size={14} />
            <Text fw={600} size="sm" truncate>
              {excerpt.source_document}
            </Text>
          </Group>
          {typeof excerpt.relevance_score === "number" && (
            <Badge size="sm" variant="light" color="indigo">
              {excerpt.relevance_score.toFixed(2)}
            </Badge>
          )}
        </Group>
        {excerpt.section && (
          <Text size="xs" c="dimmed" truncate>
            {excerpt.section}
          </Text>
        )}
        <Text size="xs" lineClamp={3}>
          {excerpt.excerpt}
        </Text>
        <Group gap={4} wrap="wrap">
          {(excerpt.tags || []).map((t) => (
            <Badge key={t} size="xs" variant="outline" color="gray">
              {t}
            </Badge>
          ))}
          {excerpt.used_in_last_run && (
            <Badge size="xs" variant="light" color="teal">
              used in last agent run
            </Badge>
          )}
        </Group>
      </Stack>
    </Card>
  );
}
