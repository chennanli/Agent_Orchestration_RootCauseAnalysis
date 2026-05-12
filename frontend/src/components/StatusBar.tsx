import { Badge, Group, Text } from "@mantine/core";
import { AnomalyState, SimStatus } from "../api/agent";
import { LiveBufferState } from "../hooks/useLiveBuffer";

interface Props {
  buffer: LiveBufferState;
  anomaly: AnomalyState | null;
  simStatus: SimStatus | null;
}

export default function StatusBar({ buffer, anomaly, simStatus }: Props) {
  const live = buffer.connected;
  const armed = anomaly?.armed ?? false;
  const simAlive = simStatus?.sim_alive ?? false;

  return (
    <Group gap="lg" wrap="wrap" align="center">
      <Group gap={6}>
        <Badge
          size="sm"
          color={live ? "teal" : "gray"}
          variant={live ? "filled" : "outline"}
        >
          ● {live ? "stream live" : "no stream"}
        </Badge>
        <Text size="xs" c="dimmed">
          {buffer.rows.length} pts buffered
        </Text>
      </Group>

      <Group gap={6}>
        <Badge
          size="sm"
          color={simAlive ? "blue" : "gray"}
          variant={simAlive ? "filled" : "outline"}
        >
          fortran sim {simAlive ? "alive" : "offline"}
        </Badge>
      </Group>

      <Group gap={6}>
        <Badge
          size="sm"
          color={armed ? "red" : "gray"}
          variant={armed ? "filled" : "outline"}
        >
          {armed
            ? `Anomaly armed (${anomaly?.consecutive_anomalies}/${anomaly?.threshold})`
            : "Anomaly quiet"}
        </Badge>
      </Group>

      {buffer.lastTickAt && (
        <Text size="xs" c="dimmed">
          last tick {new Date(buffer.lastTickAt).toLocaleTimeString()}
        </Text>
      )}
      {buffer.reconnects > 0 && (
        <Text size="xs" c="dimmed">
          reconnects: {buffer.reconnects}
        </Text>
      )}
    </Group>
  );
}
