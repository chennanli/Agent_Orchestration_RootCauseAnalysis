import { useState } from "react";
import {
  Button,
  Card,
  Group,
  Loader,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { IconMessageCircle2, IconSend2 } from "@tabler/icons-react";
import { FollowupEntry, followup } from "../api/agent";

interface Props {
  runId: string;
  initialFollowups?: FollowupEntry[];
  // Pass the model + key currently selected in the right-hand panel so
  // follow-ups respect the same provider that ran the diagnosis. Without
  // these, a Gemini-routed run's follow-ups would silently fall back to
  // whatever model the run JSON happens to record (or DEFAULT_MODEL_ID).
  modelId?: string | null;
  apiKey?: string | null;
}

/**
 * Single-shot follow-up chat against a saved NAT run.
 *
 * Each post sends `{question, model_id, api_key}` to
 * `POST /api/agent/runs/{id}/followup`; the backend assembles a prompt out
 * of the original trace and snapshot, calls the chosen LLM once (not a
 * ReAct loop), and appends `{q, a, ts, model_id}` to the persisted run
 * JSON. So follow-ups are cheap and survive page reloads.
 */
export default function FollowupChat({
  runId,
  initialFollowups = [],
  modelId = null,
  apiKey = null,
}: Props) {
  const [history, setHistory] = useState<FollowupEntry[]>(initialFollowups);
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = async () => {
    const q = question.trim();
    if (!q) return;
    setSending(true);
    setError(null);
    try {
      const entry = await followup(runId, q, {
        model_id: modelId,
        api_key: apiKey,
      });
      setHistory((h) => [...h, entry]);
      setQuestion("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  };

  return (
    <Card withBorder padding="sm" radius="md">
      <Stack gap="sm">
        <Group justify="space-between" align="center">
          <Title order={5}>
            <Group gap={6}>
              <IconMessageCircle2 size={16} />
              Follow-up chat
            </Group>
          </Title>
          <Text size="xs" c="dimmed">
            {history.length} prior · single LLM call each
          </Text>
        </Group>

        {history.length === 0 && (
          <Text size="xs" c="dimmed">
            Ask anything about this diagnosis — the assistant sees the full
            trace and source citations from the original run. It will not
            call any tools; one shot, one answer.
          </Text>
        )}

        {history.map((fu, i) => (
          <Stack key={i} gap={4}>
            <Group gap={6}>
              <Text size="xs" c="dimmed">
                you
              </Text>
              <Text size="xs" c="dimmed">
                · {new Date(fu.ts).toLocaleTimeString()}
              </Text>
            </Group>
            <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
              {fu.q}
            </Text>
            <Group gap={6}>
              <Text size="xs" c="violet">
                agent
              </Text>
            </Group>
            <Text size="sm" style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
              {fu.a}
            </Text>
          </Stack>
        ))}

        <Textarea
          autosize
          minRows={2}
          maxRows={6}
          value={question}
          onChange={(e) => setQuestion(e.currentTarget.value)}
          placeholder="e.g. Why did the agent not look at the stripper temperature?"
          disabled={sending}
        />
        {error && (
          <Text size="xs" c="red" ff="monospace">
            {error}
          </Text>
        )}
        <Group justify="flex-end">
          <Button
            size="xs"
            leftSection={sending ? <Loader size={12} /> : <IconSend2 size={14} />}
            onClick={send}
            disabled={sending || !question.trim()}
          >
            {sending ? "Asking..." : "Ask"}
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}
