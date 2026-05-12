import { useEffect, useMemo, useState } from "react";
import {
  Stack,
  Title,
  Text,
  SimpleGrid,
  Card,
  Group,
  Badge,
  Select,
  Loader,
  Table,
} from "@mantine/core";
import { LineChart } from "@mantine/charts";
import Papa from "papaparse";
import { IconActivityHeartbeat, IconAlertTriangle } from "@tabler/icons-react";
import SafetyBoundaryBanner from "../components/SafetyBoundaryBanner";

const FAULT_OPTIONS = Array.from({ length: 16 }, (_, i) => ({
  value: `fault${i}`,
  label: `fault${i}`,
}));

const KEY_TRENDS = [
  "Reactor Pressure",
  "Reactor Temperature",
  "Reactor Coolant Temp",
  "Separator Coolant Temp",
  "Stripper Pressure",
  "A Feed",
];

const T2_THRESHOLD = 55;

interface Row {
  time: number;
  [k: string]: number;
}

export default function LiveProcessPage() {
  const [fault, setFault] = useState<string>("fault1");
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`/${fault}.csv`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then((text) => {
        if (cancelled) return;
        const parsed = Papa.parse<Row>(text, {
          header: true,
          dynamicTyping: true,
          skipEmptyLines: true,
        });
        setRows((parsed.data as Row[]).filter(Boolean));
        setLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e.message);
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [fault]);

  const stats = useMemo(() => {
    const sample = rows.length;
    const t2vals = rows.map((r) => r["t2_stat" as any] as unknown as number).filter((v) => typeof v === "number");
    const maxT2 = t2vals.length ? Math.max(...t2vals) : 0;
    const aboveCount = t2vals.filter((v) => v > T2_THRESHOLD).length;
    const firstAbove = t2vals.findIndex((v) => v > T2_THRESHOLD);
    const t2Available = t2vals.length > 0;
    return { sample, maxT2, aboveCount, firstAbove, t2Available };
  }, [rows]);

  const chartData = useMemo(() => {
    return rows.slice(0, 500).map((r) => ({
      time: r.time,
      ...Object.fromEntries(KEY_TRENDS.map((k) => [k, r[k as any]])),
    }));
  }, [rows]);

  const t2Data = useMemo(() => {
    return rows.slice(0, 500).map((r) => ({
      time: r.time,
      "T²": r["t2_stat" as any] as unknown as number,
    }));
  }, [rows]);

  const topVariables = useMemo(() => {
    if (!stats.t2Available || stats.firstAbove < 0) return [];
    const target = rows[stats.firstAbove];
    if (!target) return [];
    const t2Cols = Object.keys(target).filter(
      (k) => k.startsWith("t2_") && k !== "t2_stat"
    );
    const ranked = t2Cols
      .map((k) => ({
        variable: k.replace("t2_", ""),
        contribution: target[k as any] as unknown as number,
      }))
      .filter((r) => typeof r.contribution === "number")
      .sort((a, b) => b.contribution - a.contribution)
      .slice(0, 6);
    return ranked;
  }, [rows, stats]);

  return (
    <Stack gap="md">
      <div>
        <Title order={2}>Live Process</Title>
        <Text size="sm" c="dimmed">
          Process trends, T² statistic, anomaly status, and the top contributing
          variables. The agent does not live here - it lives one tab over, on
          the Agent Run page.
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
          <Group gap="md">
            <Group gap={6}>
              <Text size="xs" c="dimmed">samples</Text>
              <Badge variant="light">{stats.sample}</Badge>
            </Group>
            <Group gap={6}>
              <Text size="xs" c="dimmed">max T²</Text>
              <Badge variant="light">
                {stats.t2Available ? stats.maxT2.toFixed(0) : "—"}
              </Badge>
            </Group>
            <Group gap={6}>
              <Text size="xs" c="dimmed">threshold</Text>
              <Badge variant="light">{T2_THRESHOLD}</Badge>
            </Group>
            <Group gap={6}>
              <Text size="xs" c="dimmed">first anomaly</Text>
              <Badge
                variant="light"
                color={stats.firstAbove >= 0 ? "red" : "gray"}
                leftSection={
                  stats.firstAbove >= 0 ? <IconAlertTriangle size={12} /> : undefined
                }
              >
                {stats.firstAbove >= 0 ? `row ${stats.firstAbove}` : "none"}
              </Badge>
            </Group>
          </Group>
        </Group>
      </Card>

      {loading && (
        <Card withBorder padding="md" radius="sm">
          <Group gap="xs">
            <Loader size="xs" />
            <Text size="sm" c="dimmed">Loading {fault}.csv ...</Text>
          </Group>
        </Card>
      )}
      {error && (
        <Card withBorder padding="md" radius="sm">
          <Text size="sm" c="red">Could not load /{fault}.csv: {error}</Text>
        </Card>
      )}

      {!loading && !error && (
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
          <Card withBorder padding="md" radius="sm">
            <Group gap="xs" mb="xs">
              <IconActivityHeartbeat size={16} />
              <Text fw={600} size="sm">Key process trends</Text>
            </Group>
            <LineChart
              h={260}
              data={chartData}
              dataKey="time"
              series={KEY_TRENDS.map((k, i) => ({
                name: k,
                color: ["indigo", "teal", "orange", "blue", "grape", "lime"][i % 6],
              }))}
              withLegend
              legendProps={{ verticalAlign: "bottom", height: 50 }}
              gridAxis="xy"
            />
          </Card>
          <Card withBorder padding="md" radius="sm">
            <Group gap="xs" mb="xs">
              <Text fw={600} size="sm">T² statistic vs. threshold</Text>
            </Group>
            {stats.t2Available ? (
              <LineChart
                h={260}
                data={t2Data}
                dataKey="time"
                series={[{ name: "T²", color: "red" }]}
                referenceLines={[
                  { y: T2_THRESHOLD, label: `threshold ${T2_THRESHOLD}`, color: "gray" },
                ]}
                gridAxis="xy"
              />
            ) : (
              <Text size="xs" c="dimmed">
                t2_stat column missing in this CSV. Run the PCA preprocessor to
                add it (see backend/model.py process_files_in_folder).
              </Text>
            )}
          </Card>
        </SimpleGrid>
      )}

      <Card withBorder padding="md" radius="sm">
        <Group gap="xs" mb="xs">
          <Text fw={600} size="sm">Top contributing variables (at first anomaly)</Text>
        </Group>
        {topVariables.length === 0 ? (
          <Text size="xs" c="dimmed">
            No t2_* contribution columns or no stable anomaly. Try fault1, fault4, or fault6.
          </Text>
        ) : (
          <Table fz="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Variable</Table.Th>
                <Table.Th style={{ textAlign: "right" }}>T² contribution</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {topVariables.map((v) => (
                <Table.Tr key={v.variable}>
                  <Table.Td>{v.variable}</Table.Td>
                  <Table.Td style={{ textAlign: "right" }}>
                    {v.contribution.toFixed(2)}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>
    </Stack>
  );
}
