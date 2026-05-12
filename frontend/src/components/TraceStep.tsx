import { useMemo, useState } from "react";
import {
  Badge,
  Box,
  Code,
  Group,
  Text,
  Collapse,
  Anchor,
} from "@mantine/core";
import { Link as RouterLink } from "react-router-dom";
import { TraceStepPayload } from "../api/agent";

interface Props {
  step: TraceStepPayload;
  index: number;
}

/**
 * One step in the agent timeline. Visual layout depends on the
 * IntermediateStep event_type:
 *
 *   WORKFLOW_START : faint top header
 *   FUNCTION_START : 🔧 tool invocation, with collapsible input preview
 *   FUNCTION_END   : 📋 result, with collapsible output JSON
 *   WORKFLOW_END   : faint bottom marker (the final answer is rendered
 *                    separately by AgentTimelinePanel from `final`).
 */
export default function TraceStep({ step, index }: Props) {
  const p = step.payload || {};
  const et = p.event_type || "UNKNOWN";
  const name = p.name || "?";
  const data = p.data || {};
  const [open, setOpen] = useState(false);

  // IMPORTANT: hooks must run in the same order every render — keep this
  // useMemo ABOVE any early return below. (Previously placed after the
  // WORKFLOW_START/END short-circuit, which made it conditional and
  // tripped react-hooks/rules-of-hooks.) For knowledge-search results,
  // surface the cited source documents as clickable chips that deep-link
  // into the wiki page.
  const sourceChips = useMemo(
    () => extractSourceDocs(name, data.output),
    [name, data.output],
  );

  const palette: Record<string, { color: string; icon: string; label: string }> = {
    WORKFLOW_START: { color: "gray", icon: "▸", label: "workflow start" },
    WORKFLOW_END: { color: "gray", icon: "■", label: "workflow end" },
    FUNCTION_START: { color: "violet", icon: "🔧", label: "tool call" },
    FUNCTION_END: { color: "teal", icon: "📋", label: "result" },
  };
  const meta = palette[et] || { color: "blue", icon: "·", label: et };

  // Workflow markers are rendered compact — they are scaffolding, not signal.
  if (et === "WORKFLOW_START" || et === "WORKFLOW_END") {
    return (
      <Group gap={6} my={6}>
        <Text c="dimmed" size="xs" ff="monospace">
          {meta.icon} {meta.label} · {name}
        </Text>
      </Group>
    );
  }

  const inputPreview = previewJSON(data.input);
  const outputPreview = previewJSON(data.output);
  const oneLine = (s: string) => (s.length > 200 ? s.slice(0, 200) + "…" : s);

  return (
    <Box
      style={{
        borderLeft: `3px solid var(--mantine-color-${meta.color}-6)`,
        paddingLeft: 10,
        marginTop: 8,
        cursor: outputPreview || inputPreview ? "pointer" : "default",
      }}
      onClick={() =>
        (outputPreview || inputPreview) && setOpen((v) => !v)
      }
    >
      <Group gap={8} align="center">
        <Badge size="xs" color={meta.color} variant="light">
          {index + 1}
        </Badge>
        <Text size="sm" ff="monospace">
          {meta.icon} <b>{name}</b>
        </Text>
        <Text size="xs" c="dimmed">
          {meta.label}
        </Text>
      </Group>

      {et === "FUNCTION_START" && inputPreview && (
        <Text size="xs" c="dimmed" ff="monospace" mt={2}>
          input: {oneLine(inputPreview)}
        </Text>
      )}
      {et === "FUNCTION_END" && outputPreview && (
        <Text size="xs" c="dimmed" ff="monospace" mt={2}>
          output: {oneLine(outputPreview)}
        </Text>
      )}

      {sourceChips.length > 0 && (
        <Group gap={4} mt={4} onClick={(e) => e.stopPropagation()}>
          {sourceChips.map((src) => (
            <Anchor
              key={src}
              component={RouterLink}
              to={`/wiki?doc=${encodeURIComponent(src)}`}
              underline="never"
            >
              <Badge size="xs" variant="light" color="cyan" style={{ cursor: "pointer" }}>
                📚 {truncateMid(src, 28)}
              </Badge>
            </Anchor>
          ))}
        </Group>
      )}

      <Collapse in={open}>
        <Code block mt={6} fz={11}>
          {JSON.stringify({ input: data.input, output: data.output }, null, 2)}
        </Code>
      </Collapse>
    </Box>
  );
}

function previewJSON(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

function truncateMid(s: string, max: number): string {
  if (s.length <= max) return s;
  const half = Math.floor((max - 1) / 2);
  return s.slice(0, half) + "…" + s.slice(s.length - half);
}

/**
 * From the FUNCTION_END output of a `search_process_knowledge` or
 * `find_similar_faults` call, pull out the unique `source_document`
 * strings. Returns [] for any other tool. The agent_tools shape we expect:
 *   search_process_knowledge -> { excerpts: [{source_document: "..."}, ...] }
 *   find_similar_faults      -> { matches:  [{source_document: "..."}, ...] }
 *   inspect_anomaly_snapshot -> {csv_file: ".../faultN.csv", ...} (not a source)
 */
function extractSourceDocs(toolName: string, out: unknown): string[] {
  if (
    toolName !== "search_process_knowledge" &&
    toolName !== "find_similar_faults"
  ) {
    return [];
  }
  if (!out || typeof out !== "object") return [];
  const collection: unknown =
    (out as Record<string, unknown>).excerpts ??
    (out as Record<string, unknown>).matches;
  if (!Array.isArray(collection)) return [];
  const seen = new Set<string>();
  const result: string[] = [];
  for (const item of collection) {
    if (!item || typeof item !== "object") continue;
    const src = (item as Record<string, unknown>).source_document;
    if (typeof src === "string" && src && !seen.has(src)) {
      seen.add(src);
      result.push(src);
    }
  }
  return result;
}
