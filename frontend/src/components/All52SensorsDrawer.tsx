import { Drawer, SimpleGrid, Card, Group, Text, ScrollArea } from "@mantine/core";
import { LineChart } from "@mantine/charts";
import { LiveRow } from "../hooks/useLiveBuffer";

interface Props {
  opened: boolean;
  onClose: () => void;
  rows: LiveRow[];
}

// All 52 TEP sensors in canonical XMEAS / XMV order. Friendly names match
// the live ingest schema.
const ALL_SENSORS: { key: string; tag: string }[] = [
  { key: "A Feed", tag: "XMEAS_1" },
  { key: "D Feed", tag: "XMEAS_2" },
  { key: "E Feed", tag: "XMEAS_3" },
  { key: "A and C Feed", tag: "XMEAS_4" },
  { key: "Recycle Flow", tag: "XMEAS_5" },
  { key: "Reactor Feed Rate", tag: "XMEAS_6" },
  { key: "Reactor Pressure", tag: "XMEAS_7" },
  { key: "Reactor Level", tag: "XMEAS_8" },
  { key: "Reactor Temperature", tag: "XMEAS_9" },
  { key: "Purge Rate", tag: "XMEAS_10" },
  { key: "Product Sep Temp", tag: "XMEAS_11" },
  { key: "Product Sep Level", tag: "XMEAS_12" },
  { key: "Product Sep Pressure", tag: "XMEAS_13" },
  { key: "Product Sep Underflow", tag: "XMEAS_14" },
  { key: "Stripper Level", tag: "XMEAS_15" },
  { key: "Stripper Pressure", tag: "XMEAS_16" },
  { key: "Stripper Underflow", tag: "XMEAS_17" },
  { key: "Stripper Temp", tag: "XMEAS_18" },
  { key: "Stripper Steam Flow", tag: "XMEAS_19" },
  { key: "Compressor Work", tag: "XMEAS_20" },
  { key: "Reactor Coolant Temp", tag: "XMEAS_21" },
  { key: "Separator Coolant Temp", tag: "XMEAS_22" },
  { key: "Component A to Reactor", tag: "XMEAS_23" },
  { key: "Component B to Reactor", tag: "XMEAS_24" },
  { key: "Component C to Reactor", tag: "XMEAS_25" },
  { key: "Component D to Reactor", tag: "XMEAS_26" },
  { key: "Component E to Reactor", tag: "XMEAS_27" },
  { key: "Component F to Reactor", tag: "XMEAS_28" },
  { key: "Component A in Purge", tag: "XMEAS_29" },
  { key: "Component B in Purge", tag: "XMEAS_30" },
  { key: "Component C in Purge", tag: "XMEAS_31" },
  { key: "Component D in Purge", tag: "XMEAS_32" },
  { key: "Component E in Purge", tag: "XMEAS_33" },
  { key: "Component F in Purge", tag: "XMEAS_34" },
  { key: "Component G in Purge", tag: "XMEAS_35" },
  { key: "Component H in Purge", tag: "XMEAS_36" },
  { key: "Component D in Product", tag: "XMEAS_37" },
  { key: "Component E in Product", tag: "XMEAS_38" },
  { key: "Component F in Product", tag: "XMEAS_39" },
  { key: "Component G in Product", tag: "XMEAS_40" },
  { key: "Component H in Product", tag: "XMEAS_41" },
  { key: "D feed load", tag: "XMV_1" },
  { key: "E feed load", tag: "XMV_2" },
  { key: "A feed load", tag: "XMV_3" },
  { key: "A and C feed load", tag: "XMV_4" },
  { key: "Compressor recycle valve", tag: "XMV_5" },
  { key: "Purge valve", tag: "XMV_6" },
  { key: "Separator liquid load", tag: "XMV_7" },
  { key: "Stripper liquid load", tag: "XMV_8" },
  { key: "Stripper steam valve", tag: "XMV_9" },
  { key: "Reactor coolant load", tag: "XMV_10" },
  { key: "Condenser coolant load", tag: "XMV_11" },
];

/**
 * Drawer that renders ALL 52 TEP sensors in a compact 4-column grid. This
 * is the "operator's full DCS view" — the user opens it when they want to
 * see everything rather than the 6 headline sensors.
 */
export default function All52SensorsDrawer({ opened, onClose, rows }: Props) {
  const empty = rows.length === 0;
  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      position="right"
      size="80%"
      title="All 52 sensors"
    >
      <ScrollArea offsetScrollbars style={{ height: "calc(100vh - 80px)" }}>
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3, lg: 4 }} spacing="xs">
          {ALL_SENSORS.map((s) => {
            const data = rows.map((r, i) => ({
              t: r.time ?? i,
              v: Number(r[s.key] ?? NaN),
            }));
            const valid = data.filter((d) => Number.isFinite(d.v));
            const last = valid.length ? valid[valid.length - 1].v : null;
            const min = valid.length
              ? Math.min(...valid.map((d) => d.v))
              : 0;
            const max = valid.length
              ? Math.max(...valid.map((d) => d.v))
              : 0;
            return (
              <Card key={s.key} withBorder padding="xs" radius="md">
                <Group justify="space-between" align="center" mb={2} gap={4}>
                  <Text size="xs" fw={600} truncate>
                    {s.tag}
                  </Text>
                  <Text size="xs" c="dimmed" ff="monospace">
                    {last == null ? "—" : last.toFixed(2)}
                  </Text>
                </Group>
                <Text size="xs" c="dimmed" truncate mb={4}>
                  {s.key}
                </Text>
                {empty || valid.length < 2 ? (
                  <Text size="xs" c="dimmed" ta="center" py="xs" ff="monospace">
                    ░░░ no data ░░░
                  </Text>
                ) : (
                  <LineChart
                    h={60}
                    data={valid.map((d) => ({ t: d.t, v: d.v }))}
                    dataKey="t"
                    series={[
                      { name: "v", color: s.tag.startsWith("XMV") ? "orange.5" : "blue.5" },
                    ]}
                    withDots={false}
                    withXAxis={false}
                    withYAxis={false}
                    withLegend={false}
                    withTooltip={false}
                    strokeWidth={1.5}
                    curveType="monotone"
                    yAxisProps={{
                      domain: [
                        min - (max - min) * 0.1,
                        max + (max - min) * 0.1,
                      ],
                    }}
                  />
                )}
              </Card>
            );
          })}
        </SimpleGrid>
      </ScrollArea>
    </Drawer>
  );
}
