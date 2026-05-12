import { Alert, Text } from "@mantine/core";
import { IconShieldLock } from "@tabler/icons-react";

interface Props {
  variant?: "compact" | "full";
}

/**
 * Reusable safety-boundary banner. Stamped on every page so the read-only
 * boundary is impossible to miss.
 */
export default function SafetyBoundaryBanner({ variant = "full" }: Props) {
  const compact = variant === "compact";
  return (
    <Alert
      icon={<IconShieldLock size={16} />}
      color="yellow"
      variant="light"
      title={compact ? undefined : "Read-only diagnosis boundary"}
      radius="sm"
      styles={{
        root: { borderLeft: "4px solid #d6b300", paddingTop: compact ? 6 : 12, paddingBottom: compact ? 6 : 12 },
      }}
    >
      <Text size={compact ? "xs" : "sm"} c="dimmed">
        Advisory-only demo. The agent can inspect, retrieve, compare, and explain.
        It cannot change setpoints, open or close valves, or control the simulated process.
        Every advisory requires SME review.
      </Text>
    </Alert>
  );
}
