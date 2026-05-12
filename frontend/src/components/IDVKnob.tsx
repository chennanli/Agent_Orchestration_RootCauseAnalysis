import { useEffect, useRef, useState } from "react";
import { Group, Stack, Text } from "@mantine/core";

interface Props {
  /** IDV number, 1..20. */
  idv: number;
  /** Short name shown above the dial. */
  name: string;
  /** Subtitle below the name. */
  subtitle: string;
  /** Current value in percent, 0..100. */
  value: number;
  /** Disabled (sim offline). */
  disabled?: boolean;
  /** Called when the user releases the dial. Debounce is the caller's
   *  responsibility — we only fire on mouseUp / touchEnd, not on every
   *  drag tick. */
  onCommit: (idv: number, valuePercent: number) => void;
}

/**
 * A single TEP IDV rotary knob. Visually a circle with a pointer line; the
 * pointer angle encodes 0-100%. Drag to rotate. Mirrors the operator-feel
 * of the original TEP demo (a panel of rotary dials, not a dropdown).
 *
 * Activation rule: the underlying simulator only supports a 0/1 disturbance
 * flag per IDV, so the knob is "off" when value < 50% and "on" when ≥ 50%.
 * The 0-100% is still useful as a UI cue — the operator sees how hard
 * they've turned it — but at the wire level it becomes value=1 above 50%.
 */
export default function IDVKnob({
  idv,
  name,
  subtitle,
  value,
  disabled = false,
  onCommit,
}: Props) {
  // Render-time copy of the value that follows the cursor as the user drags;
  // the committed value flows back through `value` after `onCommit` fires.
  const [draft, setDraft] = useState(value);
  const draggingRef = useRef(false);
  const ringRef = useRef<SVGSVGElement | null>(null);

  // Sync external value updates into draft when not dragging.
  useEffect(() => {
    if (!draggingRef.current) setDraft(value);
  }, [value]);

  const active = draft >= 50;
  // Map 0..100 → -135° .. +135° around the bottom (so the "off" position
  // points down-left and the "max" position points down-right).
  const angle = (-135 + (draft / 100) * 270) * (Math.PI / 180);
  const r = 28;
  const cx = 36;
  const cy = 36;
  const px = cx + Math.cos(Math.PI / 2 + angle) * r;
  const py = cy + Math.sin(Math.PI / 2 + angle) * r;

  const handlePointer = (e: React.PointerEvent<SVGSVGElement>) => {
    if (disabled || !ringRef.current) return;
    const rect = ringRef.current.getBoundingClientRect();
    const x = e.clientX - (rect.left + rect.width / 2);
    const y = e.clientY - (rect.top + rect.height / 2);
    // Angle in radians, 0 pointing down (south). Range −π..π.
    let a = Math.atan2(x, -y); // east is +π/2, west is −π/2
    // Restrict to our sweep range, then convert to 0..100.
    // Sweep is −135°..+135° around the bottom (i.e. dial face).
    const SWEEP = (135 * Math.PI) / 180;
    if (a < -SWEEP) a = -SWEEP;
    if (a > SWEEP) a = SWEEP;
    const pct = ((a + SWEEP) / (2 * SWEEP)) * 100;
    setDraft(Math.round(pct));
  };

  const begin = (e: React.PointerEvent<SVGSVGElement>) => {
    if (disabled) return;
    draggingRef.current = true;
    e.currentTarget.setPointerCapture(e.pointerId);
    handlePointer(e);
  };
  const end = (e: React.PointerEvent<SVGSVGElement>) => {
    if (disabled) return;
    if (!draggingRef.current) return;
    draggingRef.current = false;
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      /* already released */
    }
    onCommit(idv, draft);
  };

  // Color: active = red-orange "fault active", inactive = subdued gray.
  const stroke = active ? "var(--mantine-color-red-6)" : "var(--mantine-color-dark-3)";
  const trackStroke = "var(--mantine-color-dark-5)";
  const labelColor = disabled
    ? "var(--mantine-color-dimmed)"
    : active
      ? "var(--mantine-color-red-4)"
      : "var(--mantine-color-gray-4)";

  return (
    <Stack
      gap={2}
      align="center"
      style={{ opacity: disabled ? 0.35 : 1, userSelect: "none" }}
    >
      <Group gap={4} align="baseline">
        <Text size="xs" fw={700} c={active ? "red.4" : "gray.3"}>
          IDV-{idv}
        </Text>
        <Text size="xs" c="dimmed" lineClamp={1} style={{ maxWidth: 140 }}>
          {name}
        </Text>
      </Group>
      <svg
        ref={ringRef}
        width={72}
        height={72}
        viewBox="0 0 72 72"
        style={{ cursor: disabled ? "not-allowed" : "grab", touchAction: "none" }}
        onPointerDown={begin}
        onPointerMove={(e) => {
          if (draggingRef.current) handlePointer(e);
        }}
        onPointerUp={end}
        onPointerCancel={end}
        role="slider"
        aria-label={`IDV-${idv} ${name} intensity`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={draft}
      >
        {/* outer ring */}
        <circle cx={cx} cy={cy} r={r + 4} fill="none" stroke={trackStroke} strokeWidth={2} />
        {/* inner disc */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill={active ? "rgba(255, 89, 112, 0.08)" : "rgba(255,255,255,0.02)"}
          stroke={stroke}
          strokeWidth={2}
        />
        {/* pointer */}
        <line
          x1={cx}
          y1={cy}
          x2={px}
          y2={py}
          stroke={active ? "var(--mantine-color-red-4)" : "var(--mantine-color-gray-4)"}
          strokeWidth={3}
          strokeLinecap="round"
        />
        {/* center dot */}
        <circle cx={cx} cy={cy} r={2.5} fill={stroke} />
        {/* tick marks at 0 and 100 ends of the sweep */}
        <circle cx={cx + Math.cos(Math.PI / 2 - (135 * Math.PI) / 180) * (r + 5)}
                cy={cy + Math.sin(Math.PI / 2 - (135 * Math.PI) / 180) * (r + 5)}
                r={1.5} fill="var(--mantine-color-dark-2)" />
        <circle cx={cx + Math.cos(Math.PI / 2 + (135 * Math.PI) / 180) * (r + 5)}
                cy={cy + Math.sin(Math.PI / 2 + (135 * Math.PI) / 180) * (r + 5)}
                r={1.5} fill="var(--mantine-color-dark-2)" />
      </svg>
      <Text size="xs" ff="monospace" c={labelColor} fw={active ? 700 : 400}>
        {draft}%
      </Text>
      <Text size="xs" c="dimmed" lineClamp={1} style={{ maxWidth: 140 }}>
        {subtitle}
      </Text>
    </Stack>
  );
}
