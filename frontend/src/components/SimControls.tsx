import { useState } from "react";
import {
  Button,
  Group,
  Select,
  Slider,
  Stack,
  Text,
  Badge,
} from "@mantine/core";
import { SimStatus, setSpeed, triggerFault } from "../api/agent";

interface Props {
  simStatus: SimStatus | null;
}

const IDV_OPTIONS = [
  { value: "0", label: "IDV-0  (clear / none)" },
  ...Array.from({ length: 20 }, (_, i) => ({
    value: String(i + 1),
    label: `IDV-${i + 1}`,
  })),
];

const SPEED_MARKS = [
  { value: 1, label: "1x" },
  { value: 10, label: "10x" },
  { value: 25, label: "25x" },
  { value: 50, label: "50x" },
];

/**
 * Speed slider + IDV trigger. Wires to `/api/sim/*`. When the proxy
 * returns 501 (unified_console has no matching endpoint yet) we surface
 * a small warning but stay friendly — the rest of the UI keeps working.
 */
export default function SimControls({ simStatus }: Props) {
  const simAlive = simStatus?.sim_alive ?? false;

  const [speed, setSpeedState] = useState(20);
  const [idv, setIdv] = useState<string | null>("0");
  const [busy, setBusy] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const [hintColor, setHintColor] = useState<"red" | "teal" | "gray">("gray");

  const flash = (msg: string, color: "red" | "teal" | "gray" = "gray") => {
    setHint(msg);
    setHintColor(color);
    window.setTimeout(() => setHint(null), 4000);
  };

  const applySpeed = async () => {
    if (!simAlive) return;
    setBusy(true);
    try {
      await setSpeed(speed);
      flash(`speed set to ${speed}x`, "teal");
    } catch (e) {
      flash((e as Error).message.slice(0, 120), "red");
    } finally {
      setBusy(false);
    }
  };

  const applyIdv = async () => {
    if (!simAlive || idv == null) return;
    setBusy(true);
    try {
      await triggerFault(Number(idv));
      flash(
        idv === "0" ? "cleared all IDVs" : `IDV-${idv} triggered`,
        "teal",
      );
    } catch (e) {
      flash((e as Error).message.slice(0, 120), "red");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack gap="xs">
      <Group justify="space-between" align="center">
        <Text size="sm" fw={600}>
          Simulator controls
        </Text>
        {!simAlive && (
          <Badge size="xs" color="gray" variant="outline">
            offline · start unified_console.py
          </Badge>
        )}
      </Group>

      <Stack gap={4}>
        <Group justify="space-between" align="center">
          <Text size="xs">Speed</Text>
          <Text size="xs" c="dimmed">
            {speed}x (1x = real time)
          </Text>
        </Group>
        <Slider
          min={1}
          max={50}
          step={1}
          marks={SPEED_MARKS}
          value={speed}
          onChange={setSpeedState}
          disabled={!simAlive || busy}
        />
        <Group justify="flex-end">
          <Button
            size="xs"
            variant="light"
            onClick={applySpeed}
            disabled={!simAlive || busy}
          >
            Apply speed
          </Button>
        </Group>
      </Stack>

      {/* IDV fault triggering moved to the new IDVPanel rotary-knob grid;
          the old single-select dropdown lives on as a hidden fallback only
          for users who prefer keyboard / accessibility. */}
      <details style={{ marginTop: 4 }}>
        <summary style={{ cursor: "pointer", fontSize: 11, color: "var(--mantine-color-dimmed)" }}>
          Accessibility: dropdown IDV trigger
        </summary>
        <Group gap="xs" align="end" mt={6}>
          <Select
            label="Fault disturbance (IDV)"
            data={IDV_OPTIONS}
            value={idv}
            onChange={setIdv}
            disabled={!simAlive || busy}
            size="xs"
            comboboxProps={{ withinPortal: true }}
            style={{ flex: 1 }}
          />
          <Button
            size="xs"
            variant="light"
            color={idv === "0" ? "gray" : "orange"}
            onClick={applyIdv}
            disabled={!simAlive || busy}
          >
            {idv === "0" ? "Clear" : "Trigger"}
          </Button>
        </Group>
      </details>

      {hint && (
        <Text size="xs" c={hintColor}>
          {hint}
        </Text>
      )}
    </Stack>
  );
}
