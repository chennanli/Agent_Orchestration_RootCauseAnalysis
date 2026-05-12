import { Card, Group, Text, Badge, Tooltip } from "@mantine/core";
import { AreaChart } from "@mantine/charts";
import { IconInfoCircle } from "@tabler/icons-react";
import { AnomalyState } from "../api/agent";

interface Props {
  anomaly: AnomalyState | null;
}

/**
 * Live anomaly-detection score chart. Internally this is the PCA Hotelling
 * T² statistic, but the public-facing label is intentionally simpler —
 * operators don't need the statistics jargon to read the spike.
 *
 * Key UX decisions:
 *   - Y-axis is *bounded* (not auto-scaling) so a brief spike doesn't squash
 *     the rest of the chart into a flat line. Domain is [0, max(1.5×threshold,
 *     1.1×observed_max)]. Anything above that is clipped — we already know
 *     it's "very anomalous".
 *   - Color flips green → red once the score crosses the threshold line.
 *   - The threshold line is always visible (dashed gray) so the operator
 *     can see how close to alarm we are.
 */
export default function AnomalyScoreChart({ anomaly }: Props) {
  const series = anomaly?.t2_series ?? [];
  const threshold = anomaly?.t2_threshold ?? null;
  const armed = anomaly?.armed ?? false;

  const last = series.length ? series[series.length - 1] : null;

  // Compute a bounded y-axis. Default upper bound = 1.5 × threshold so the
  // threshold line sits at 2/3 of the chart. If the actual data goes higher,
  // grow the bound but cap at 3 × threshold (everything beyond that is
  // already "extreme anomaly" — we don't need more visual range).
  const observedMax = series.reduce(
    (m, p) => (p.t2_stat > m ? p.t2_stat : m),
    0,
  );
  const baseTop = threshold != null ? threshold * 1.5 : 100;
  const dataTop = observedMax * 1.1;
  const capTop = threshold != null ? threshold * 3.0 : 300;
  const yMax = Math.min(capTop, Math.max(baseTop, dataTop));

  // Clip individual values for display so the line stays inside the chart.
  const data = series.map((p) => ({
    t: p.t,
    score: Math.min(p.t2_stat, yMax),
    threshold: threshold ?? 0,
  }));

  return (
    <Card withBorder padding="sm" radius="md">
      <Group justify="space-between" align="center" mb={6}>
        <Group gap={6}>
          <Text size="sm" fw={600}>
            Anomaly detection score
          </Text>
          <Badge
            size="xs"
            color={armed ? "red" : "gray"}
            variant={armed ? "filled" : "light"}
          >
            {armed ? "anomaly detected" : "quiet"}
          </Badge>
          <Tooltip
            label="PCA Hotelling T² over the last ~50 decimated samples. The detector arms when the score crosses the dashed threshold."
            multiline
            w={260}
          >
            <IconInfoCircle size={12} style={{ color: "var(--mantine-color-dimmed)", cursor: "help" }} />
          </Tooltip>
        </Group>
        <Group gap={10}>
          <Text size="xs" c="dimmed">
            current
          </Text>
          <Text size="xs" ff="monospace" c={armed ? "red" : "dimmed"}>
            {last ? last.t2_stat.toFixed(1) : "—"}
          </Text>
          <Text size="xs" c="dimmed">
            · threshold
          </Text>
          <Text size="xs" ff="monospace" c="dimmed">
            {threshold == null ? "?" : threshold.toFixed(1)}
          </Text>
        </Group>
      </Group>
      {data.length < 2 ? (
        <Text size="xs" c="dimmed" ta="center" py="md" ff="monospace">
          waiting for buffer to fill...
        </Text>
      ) : (
        <AreaChart
          h={110}
          data={data}
          dataKey="t"
          series={[
            { name: "score", color: armed ? "red.6" : "teal.5" },
            {
              name: "threshold",
              color: "gray.5",
              strokeDasharray: "4 4",
            },
          ]}
          curveType="natural"
          withDots={false}
          withXAxis={false}
          withYAxis
          withTooltip={false}
          withLegend={false}
          gridAxis="y"
          fillOpacity={0.18}
          strokeWidth={2}
          yAxisProps={{ domain: [0, yMax] }}
        />
      )}
    </Card>
  );
}
