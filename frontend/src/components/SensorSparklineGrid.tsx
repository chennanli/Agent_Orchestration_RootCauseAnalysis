import { Badge, Card, Group, SimpleGrid, Text } from "@mantine/core";
import { LineChart } from "@mantine/charts";
import { LiveRow } from "../hooks/useLiveBuffer";

interface Props {
  rows: LiveRow[];
  /**
   * Optional sensor names to display. When set (e.g. the top-6 variables
   * from the last agent run), the grid swaps to those sensors. Falls back
   * to the curated 6 default headline sensors otherwise.
   */
  dynamicSensors?: string[];
}

// Default headline sensors. Used until the agent runs once and produces a
// top-contributors list. After that the grid auto-swaps to the agent's
// top-6 so each fault highlights its OWN most-affected sensors.
const DEFAULT_SENSORS: { key: string; color: string }[] = [
  { key: "Reactor Pressure", color: "blue.6" },
  { key: "Reactor Temperature", color: "red.6" },
  { key: "A Feed", color: "violet.6" },
  { key: "Stripper Pressure", color: "cyan.6" },
  { key: "Reactor Coolant Temp", color: "orange.6" },
  { key: "Separator Coolant Temp", color: "teal.6" },
];

const PALETTE = ["blue.6", "red.6", "violet.6", "cyan.6", "orange.6", "teal.6", "pink.5", "yellow.5"];

export default function SensorSparklineGrid({ rows, dynamicSensors }: Props) {
  const sensorList =
    dynamicSensors && dynamicSensors.length > 0
      ? dynamicSensors.slice(0, 6).map((key, i) => ({
          key,
          color: PALETTE[i % PALETTE.length],
        }))
      : DEFAULT_SENSORS;
  const usingDynamic = Boolean(dynamicSensors && dynamicSensors.length > 0);
  const empty = rows.length === 0;

  return (
    <>
      {usingDynamic && (
        <Group justify="flex-end" mb={4}>
          <Badge size="xs" color="violet" variant="light">
            agent-driven · top {sensorList.length} from last run
          </Badge>
        </Group>
      )}
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="xs">
        {sensorList.map((s) => {
          const data = rows.map((r, i) => ({
            t: r.time ?? i,
            v: Number(r[s.key] ?? NaN),
          }));
          const valid = data.filter((d) => Number.isFinite(d.v));
          const last = valid.length ? valid[valid.length - 1].v : null;
          const min = valid.length ? Math.min(...valid.map((d) => d.v)) : 0;
          const max = valid.length ? Math.max(...valid.map((d) => d.v)) : 0;
          return (
            <Card key={s.key} withBorder padding="xs" radius="md">
              <Group justify="space-between" align="center" mb={4}>
                <Text size="xs" fw={600}>
                  {s.key}
                </Text>
                <Text size="xs" c="dimmed" ff="monospace">
                  {last == null ? "—" : last.toFixed(2)}
                </Text>
              </Group>
              {empty || valid.length < 2 ? (
                <Text size="xs" c="dimmed" ta="center" py="md" ff="monospace">
                  ░░░░ no data ░░░░
                </Text>
              ) : (
                <LineChart
                  h={90}
                  data={valid.map((d) => ({ t: d.t, [s.key]: d.v }))}
                  dataKey="t"
                  series={[{ name: s.key, color: s.color }]}
                  withDots={false}
                  withXAxis={false}
                  withYAxis={false}
                  withLegend={false}
                  withTooltip={false}
                  strokeWidth={2}
                  curveType="monotone"
                  yAxisProps={{
                    domain: [min - (max - min) * 0.1, max + (max - min) * 0.1],
                  }}
                />
              )}
            </Card>
          );
        })}
      </SimpleGrid>
    </>
  );
}
