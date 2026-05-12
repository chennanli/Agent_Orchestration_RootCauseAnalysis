import { useCallback, useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Group,
  SimpleGrid,
  Stack,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";
import { IconAlertTriangle, IconReload } from "@tabler/icons-react";
import IDVKnob from "./IDVKnob";
import { triggerFault, SimStatus } from "../api/agent";

interface Props {
  simStatus: SimStatus | null;
}

/**
 * The 20 Tennessee Eastman disturbance variables (IDV_1 .. IDV_20), per
 * Downs & Vogel (1993). Each row describes one canonical fault category.
 * IDV-16..20 are intentionally vague — Downs & Vogel left them as
 * "unknown" disturbances for stress-testing fault detectors.
 *
 * The user is NOT restricted to one IDV at a time — multiple knobs can be
 * active simultaneously, producing compound faults the simulator handles
 * naturally.
 */
const IDV_CATALOG: { idv: number; name: string; subtitle: string }[] = [
  { idv: 1,  name: "A/C feed ratio",        subtitle: "Stream 4, B held" },
  { idv: 2,  name: "B composition",          subtitle: "A/C ratio held" },
  { idv: 3,  name: "D feed temperature",     subtitle: "Stream 2" },
  { idv: 4,  name: "Reactor cooling water",  subtitle: "Inlet temp step" },
  { idv: 5,  name: "Condenser cooling water",subtitle: "Inlet temp step" },
  { idv: 6,  name: "A feed loss",            subtitle: "Stream 1" },
  { idv: 7,  name: "C header pressure loss", subtitle: "Stream 4" },
  { idv: 8,  name: "A, B, C composition",    subtitle: "Random Stream 4" },
  { idv: 9,  name: "D feed temperature",     subtitle: "Random Stream 2" },
  { idv: 10, name: "C feed temperature",     subtitle: "Random Stream 4" },
  { idv: 11, name: "Reactor cooling temp",   subtitle: "Random variation" },
  { idv: 12, name: "Condenser cooling temp", subtitle: "Random variation" },
  { idv: 13, name: "Reaction kinetics",      subtitle: "Slow drift" },
  { idv: 14, name: "Reactor cooling valve",  subtitle: "Sticking" },
  { idv: 15, name: "Condenser cooling valve",subtitle: "Sticking" },
  { idv: 16, name: "Unknown",                subtitle: "stress-test #1" },
  { idv: 17, name: "Unknown",                subtitle: "stress-test #2" },
  { idv: 18, name: "Unknown",                subtitle: "stress-test #3" },
  { idv: 19, name: "Unknown",                subtitle: "stress-test #4" },
  { idv: 20, name: "Unknown",                subtitle: "stress-test #5" },
];

/**
 * Operator-style IDV control panel. Each knob is a 0-100% dial. Turning a
 * knob ≥ 50% triggers that disturbance in the running Fortran sim
 * (POST /api/sim/fault with value=1); turning back below 50% clears it.
 *
 * "Reset all" lifts every active fault in one click.
 */
export default function IDVPanel({ simStatus }: Props) {
  const simAlive = simStatus?.sim_alive ?? false;
  const [values, setValues] = useState<number[]>(() => Array(21).fill(0));
  const [busy, setBusy] = useState(false);
  const [hint, setHint] = useState<string | null>(null);

  // Bootstrap values from unified_console's reported idv_values when we
  // first see them. After that, the UI is authoritative until the user
  // resets or refreshes.
  useEffect(() => {
    const remote =
      simStatus &&
      typeof simStatus.payload === "object" &&
      simStatus.payload !== null &&
      (simStatus.payload as { idv_values?: unknown }).idv_values;
    if (Array.isArray(remote)) {
      // unified_console reports 20-length array (IDV 1..20). Map each 0/1
      // back to 0% / 100% so the dials reflect reality on first paint.
      setValues((prev) => {
        const seeded = [...prev];
        for (let i = 0; i < 20 && i < remote.length; i++) {
          const v = Number(remote[i]);
          seeded[i + 1] = v >= 1 ? 100 : seeded[i + 1] === 0 ? 0 : seeded[i + 1];
        }
        return seeded;
      });
    }
    // We only want this to seed once on connection; re-running on every
    // simStatus poll would clobber the user's mid-drag values.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [simAlive]);

  const flash = (msg: string) => {
    setHint(msg);
    window.setTimeout(() => setHint(null), 4000);
  };

  const handleCommit = useCallback(
    async (idv: number, valuePercent: number) => {
      if (!simAlive || busy) return;
      setValues((prev) => {
        const next = [...prev];
        next[idv] = valuePercent;
        return next;
      });
      setBusy(true);
      try {
        // Wire-level: anything ≥50% is on. <50% is off.
        const magnitude = valuePercent >= 50 ? 1 : 0;
        await triggerFault(idv, magnitude);
        flash(
          magnitude === 1
            ? `IDV-${idv} (${IDV_CATALOG[idv - 1]?.name}) triggered at ${valuePercent}%`
            : `IDV-${idv} cleared`,
        );
      } catch (e) {
        flash(`IDV-${idv} failed: ${(e as Error).message.slice(0, 100)}`);
      } finally {
        setBusy(false);
      }
    },
    [simAlive, busy],
  );

  const resetAll = async () => {
    if (!simAlive || busy) return;
    setBusy(true);
    try {
      for (let i = 1; i <= 20; i++) {
        if (values[i] >= 50) {
          await triggerFault(i, 0);
        }
      }
      setValues(Array(21).fill(0));
      flash("All IDVs cleared");
    } catch (e) {
      flash(`reset failed: ${(e as Error).message.slice(0, 100)}`);
    } finally {
      setBusy(false);
    }
  };

  const activeCount = values.slice(1).filter((v) => v >= 50).length;

  return (
    <Card withBorder padding="sm" radius="md">
      <Stack gap="xs">
        <Group justify="space-between" align="center">
          <Group gap={6}>
            <Title order={5}>Disturbance injection (IDV)</Title>
            <Badge size="xs" color={activeCount ? "red" : "gray"} variant="light">
              {activeCount} active
            </Badge>
            <Tooltip
              label="Turn a dial ≥50% to inject the disturbance into the running simulator. You can stack multiple at once (compound faults)."
              multiline
              w={300}
            >
              <Text size="xs" c="dimmed" style={{ cursor: "help" }}>
                ⓘ rotary knob · ≥50% triggers
              </Text>
            </Tooltip>
          </Group>
          <Button
            size="xs"
            variant="light"
            color="gray"
            leftSection={<IconReload size={12} />}
            onClick={resetAll}
            disabled={!simAlive || busy || activeCount === 0}
          >
            Reset all
          </Button>
        </Group>

        {!simAlive && (
          <Group gap={4}>
            <IconAlertTriangle size={14} style={{ color: "var(--mantine-color-orange-5)" }} />
            <Text size="xs" c="dimmed">
              Simulator offline. Start <code>unified_console.py</code> to enable IDV controls.
            </Text>
          </Group>
        )}

        <SimpleGrid cols={{ base: 3, sm: 4, md: 5 }} spacing="xs" verticalSpacing="xs">
          {IDV_CATALOG.map((d) => (
            <IDVKnob
              key={d.idv}
              idv={d.idv}
              name={d.name}
              subtitle={d.subtitle}
              value={values[d.idv]}
              disabled={!simAlive || busy}
              onCommit={handleCommit}
            />
          ))}
        </SimpleGrid>

        {hint && (
          <Text size="xs" c="dimmed" ff="monospace">
            {hint}
          </Text>
        )}
      </Stack>
    </Card>
  );
}
