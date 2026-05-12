import { useEffect, useState } from "react";
import {
  ActionIcon,
  Badge,
  Drawer,
  Group,
  ScrollArea,
  Stack,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { IconHistory, IconSearch, IconExternalLink } from "@tabler/icons-react";
import { RunSummary, listRuns } from "../api/agent";

interface Props {
  opened: boolean;
  onClose: () => void;
  onSelect: (run: RunSummary) => void;
}

/**
 * Right-side drawer listing past NAT runs from disk. Click a row to open
 * that run read-only in the main panel (handled by the parent).
 *
 * Reads `/api/agent/runs` each time it opens. Cheap — runs are < 50 KB
 * each and the endpoint summarises rather than streaming the full trace.
 */
export default function HistoryDrawer({ opened, onClose, onSelect }: Props) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!opened) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    listRuns(100)
      .then((r) => {
        if (!cancelled) setRuns(r.runs);
      })
      .catch((e) => {
        if (!cancelled) setError((e as Error).message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [opened]);

  const filtered = runs.filter((r) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    return (
      (r.run_id ?? "").toLowerCase().includes(q) ||
      (r.fault_id ?? "").toLowerCase().includes(q) ||
      (r.summary ?? "").toLowerCase().includes(q)
    );
  });

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      position="right"
      size="lg"
      title={
        <Group gap={6}>
          <IconHistory size={18} />
          <Text fw={600}>Past NAT runs</Text>
          <Badge size="xs" variant="light">
            {runs.length}
          </Badge>
        </Group>
      }
    >
      <Stack gap="sm" style={{ height: "100%" }}>
        <TextInput
          placeholder="search by id, fault, or advisory text..."
          leftSection={<IconSearch size={14} />}
          value={query}
          onChange={(e) => setQuery(e.currentTarget.value)}
          size="xs"
        />

        {loading && (
          <Text size="xs" c="dimmed">
            loading...
          </Text>
        )}
        {error && (
          <Text size="xs" c="red" ff="monospace">
            {error}
          </Text>
        )}

        <ScrollArea offsetScrollbars style={{ flex: 1 }}>
          {filtered.length === 0 && !loading && (
            <Text size="xs" c="dimmed" ta="center" py="lg">
              No runs match.
            </Text>
          )}
          <Stack gap={4}>
            {filtered.map((r) => (
              <Group
                key={r.run_id}
                wrap="nowrap"
                align="flex-start"
                gap={6}
                px={6}
                py={6}
                style={{
                  borderRadius: 6,
                  border: "1px solid var(--mantine-color-default-border)",
                  cursor: "pointer",
                }}
                onClick={() => {
                  onSelect(r);
                  onClose();
                }}
              >
                <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
                  <Group gap={6} wrap="nowrap">
                    <Badge size="xs" variant="light" color="blue">
                      {r.fault_id ?? "?"}
                    </Badge>
                    {r.policy_safe === true && (
                      <Badge size="xs" variant="light" color="green">
                        safe
                      </Badge>
                    )}
                    {r.policy_safe === false && (
                      <Badge size="xs" variant="light" color="red">
                        flagged
                      </Badge>
                    )}
                    {r.error && (
                      <Badge size="xs" variant="light" color="red">
                        error
                      </Badge>
                    )}
                    {r.followup_count > 0 && (
                      <Badge size="xs" variant="light" color="violet">
                        {r.followup_count} f/u
                      </Badge>
                    )}
                    <Text size="xs" c="dimmed">
                      {r.runtime_seconds != null
                        ? `${r.runtime_seconds.toFixed(1)}s`
                        : "?"}
                    </Text>
                  </Group>
                  <Text size="xs" ff="monospace" c="dimmed" truncate>
                    {r.run_id}
                  </Text>
                  <Text size="xs" lineClamp={2}>
                    {r.summary || "(no summary)"}
                  </Text>
                </Stack>
                <Tooltip label="open in main panel">
                  <ActionIcon variant="subtle" size="sm">
                    <IconExternalLink size={14} />
                  </ActionIcon>
                </Tooltip>
              </Group>
            ))}
          </Stack>
        </ScrollArea>
      </Stack>
    </Drawer>
  );
}
