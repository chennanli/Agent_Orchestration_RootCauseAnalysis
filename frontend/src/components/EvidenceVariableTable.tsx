import { Card, Group, Text, Table, Badge } from "@mantine/core";
import { IconChartBar } from "@tabler/icons-react";

export interface EvidenceVariableRow {
  variable: string;
  t2_contribution: number;
  mean_change_pct: number;
  direction: string;
}

interface Props {
  rows: EvidenceVariableRow[];
  caption?: string;
}

function directionColor(dir: string): string {
  if (dir === "increasing") return "red";
  if (dir === "decreasing") return "blue";
  return "gray";
}

export default function EvidenceVariableTable({ rows, caption }: Props) {
  if (!rows || rows.length === 0) {
    return (
      <Card withBorder padding="md" radius="sm">
        <Text size="sm" c="dimmed">
          No ranked variables. Run the agent to see top contributors.
        </Text>
      </Card>
    );
  }
  return (
    <Card withBorder padding="md" radius="sm">
      <Group gap="xs" mb="xs">
        <IconChartBar size={16} />
        <Text fw={600} size="sm">
          Evidence variables
        </Text>
      </Group>
      {caption && (
        <Text size="xs" c="dimmed" mb="xs">
          {caption}
        </Text>
      )}
      <Table striped highlightOnHover withTableBorder withColumnBorders fz="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Variable</Table.Th>
            <Table.Th style={{ textAlign: "right" }}>T² contribution</Table.Th>
            <Table.Th style={{ textAlign: "right" }}>% mean change</Table.Th>
            <Table.Th>Direction</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((r) => (
            <Table.Tr key={r.variable}>
              <Table.Td>{r.variable}</Table.Td>
              <Table.Td style={{ textAlign: "right" }}>
                {r.t2_contribution?.toFixed(2) ?? "n/a"}
              </Table.Td>
              <Table.Td style={{ textAlign: "right" }}>
                {r.mean_change_pct?.toFixed(2) ?? "n/a"}%
              </Table.Td>
              <Table.Td>
                <Badge size="sm" variant="light" color={directionColor(r.direction)}>
                  {r.direction}
                </Badge>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Card>
  );
}
