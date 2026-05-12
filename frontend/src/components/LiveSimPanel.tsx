import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Code,
  Stack,
  Text,
  Title,
  Divider,
  Group,
  Select,
} from "@mantine/core";
import { IconInfoCircle, IconLayoutGrid } from "@tabler/icons-react";
import StatusBar from "./StatusBar";
import SensorSparklineGrid from "./SensorSparklineGrid";
import SimControls from "./SimControls";
import AnomalyScoreChart from "./AnomalyScoreChart";
import All52SensorsDrawer from "./All52SensorsDrawer";
import IDVPanel from "./IDVPanel";
import { useLiveBuffer } from "../hooks/useLiveBuffer";
import { useAnomalyState } from "../hooks/useAnomalyState";
import { getSimStatus, SimStatus } from "../api/agent";

interface Props {
  seededFaultId: string | null;
  onSeededFaultChange: (id: string | null) => void;
  /**
   * When the agent has run, this is the top-6 contributing variables from
   * its last run (by friendly name). When set, the sparkline grid swaps
   * to these instead of the default 6 headline sensors.
   */
  agentTopVariables?: string[];
}

// Available pre-baked fault datasets that come with the demo. Used so the
// user can do a meaningful click-to-diagnose even when no live sim is
// running.
const SEEDED_FAULTS = [
  { value: "fault0", label: "fault0 (normal)" },
  { value: "fault1", label: "fault1 (A feed loss)" },
  { value: "fault4", label: "fault4 (reactor cooling)" },
  { value: "fault5", label: "fault5 (condenser cooling)" },
  { value: "fault6", label: "fault6 (A feed loss alt)" },
  { value: "fault13", label: "fault13 (kinetics drift)" },
  { value: "fault14", label: "fault14 (reactor valve sticking)" },
];

export default function LiveSimPanel({
  seededFaultId,
  onSeededFaultChange,
  agentTopVariables,
}: Props) {
  const buffer = useLiveBuffer(200);
  const anomaly = useAnomalyState(2000);
  const [simStatus, setSimStatus] = useState<SimStatus | null>(null);
  const [all52Open, setAll52Open] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const s = await getSimStatus();
        if (!cancelled) setSimStatus(s);
      } catch {
        if (!cancelled) setSimStatus({ sim_alive: false });
      }
    };
    tick();
    const h = window.setInterval(tick, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(h);
    };
  }, []);

  return (
    <Stack gap="sm" style={{ height: "100%" }}>
      <Card withBorder padding="sm" radius="md">
        <Stack gap={6}>
          <Group justify="space-between" align="center">
            <Title order={4}>Live Process</Title>
            <Text size="xs" c="dimmed">
              Tennessee Eastman dynamic simulation
            </Text>
          </Group>
          <StatusBar
            buffer={buffer}
            anomaly={anomaly.state}
            simStatus={simStatus}
          />
        </Stack>
      </Card>

      <AnomalyScoreChart anomaly={anomaly.state} />

      <Card withBorder padding="sm" radius="md" style={{ flex: 1 }}>
        <Stack gap="sm" style={{ height: "100%" }}>
          <Group justify="space-between" align="center">
            <Title order={5}>
              {agentTopVariables && agentTopVariables.length > 0
                ? "Top sensors (agent-curated)"
                : "6 headline sensors (live)"}
            </Title>
            <Group gap={6}>
              {buffer.rows.length > 0 && (
                <Text size="xs" c="dimmed">
                  rolling window · 200 pts
                </Text>
              )}
              <Button
                size="xs"
                variant="light"
                leftSection={<IconLayoutGrid size={12} />}
                onClick={() => setAll52Open(true)}
              >
                All 52
              </Button>
            </Group>
          </Group>
          {buffer.rows.length === 0 && !(simStatus?.sim_alive) && (
            <Alert
              variant="light"
              color="gray"
              icon={<IconInfoCircle size={14} />}
              styles={{ message: { fontSize: 12 } }}
            >
              The Fortran simulator is offline. Start it in a separate
              terminal and live sensor data will start flowing here:
              <Code block mt={6} fz={11}>
                {".venv/bin/python unified_console.py"}
              </Code>
              <Text size="xs" mt={6}>
                You can still test the agent without the sim: pick a
                pre-baked fault below and press Diagnose Now.
              </Text>
            </Alert>
          )}
          <SensorSparklineGrid
            rows={buffer.rows}
            dynamicSensors={agentTopVariables}
          />
        </Stack>
      </Card>

      <All52SensorsDrawer
        opened={all52Open}
        onClose={() => setAll52Open(false)}
        rows={buffer.rows}
      />

      <IDVPanel simStatus={simStatus} />

      <Card withBorder padding="sm" radius="md">
        <Stack gap="sm">
          <SimControls simStatus={simStatus} />
          {/* Pre-baked fault selector lives under a collapsed details so it
              doesn't compete with the live IDV story. Recovery / offline /
              testing use only. */}
          <details style={{ marginTop: 6 }}>
            <summary style={{ cursor: "pointer", fontSize: 12, color: "var(--mantine-color-dimmed)" }}>
              Developer: diagnose a pre-baked fault snapshot instead
            </summary>
            <Stack gap={4} mt={6}>
              <Select
                description="Replays a recorded sensor trace (offline / when the live sim is unavailable). The agent treats it the same as a live snapshot."
                data={SEEDED_FAULTS}
                value={seededFaultId}
                onChange={onSeededFaultChange}
                size="xs"
                clearable
                placeholder="(default: use live snapshot)"
                comboboxProps={{ withinPortal: true }}
              />
            </Stack>
          </details>
        </Stack>
      </Card>
    </Stack>
  );
}
