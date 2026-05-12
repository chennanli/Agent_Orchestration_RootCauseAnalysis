/**
 * Misc tab — the catch-all home for "lost" features from the old demo
 * that are useful but don't belong on the Live Copilot canvas:
 *
 *   1. Knowledge-base upload (drop a PDF into knowledge_base/, re-index)
 *   2. Operator scratchpad notes (persisted server-side at backend/diagnostics/notes.json)
 *   3. Export any saved run as Markdown (one-click download)
 *   4. Email any saved run to a reviewer (uses SMTP_*; shows hint when unset)
 *
 * Deliberately a flat, stitchwork page — these are utilities, not the
 * main demonstration.
 */
import { useEffect, useState } from "react";
import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Code,
  Divider,
  FileButton,
  Group,
  List,
  Loader,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import {
  IconBriefcase,
  IconCheck,
  IconCloudUpload,
  IconDownload,
  IconMail,
  IconNotes,
} from "@tabler/icons-react";
import {
  EmailRunResult,
  KbUploadResult,
  NotesPayload,
  RunSummary,
  emailRun,
  exportRunMarkdownUrl,
  getNotes,
  listRuns,
  saveNotes,
  uploadKbFiles,
} from "../api/agent";

export default function MiscPage() {
  return (
    <Stack gap="lg" p="md" maw={960} mx="auto">
      <Group gap={8} align="center">
        <IconBriefcase size={20} />
        <Title order={3}>Misc</Title>
        <Badge variant="light" color="gray">
          utilities
        </Badge>
      </Group>
      <Text size="sm" c="dimmed">
        Bundled features that don't belong on the Live Copilot canvas. None of
        these change process setpoints; this page is purely advisory bookkeeping.
      </Text>

      <RunExportEmailCard />
      <Divider />
      <NotesCard />
      <Divider />
      <KbUploadCard />
    </Stack>
  );
}

// ---------------------------------------------------------------------------
// Run export / email
// ---------------------------------------------------------------------------

function RunExportEmailCard() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [recipient, setRecipient] = useState("");
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<EmailRunResult | null>(null);

  useEffect(() => {
    listRuns(50)
      .then((r) => {
        setRuns(r.runs);
        if (r.runs.length > 0) setRunId(r.runs[0].run_id);
      })
      .catch((e) => setError((e as Error).message));
  }, []);

  const onEmail = async () => {
    if (!runId || !recipient.trim()) return;
    setSending(true);
    setResult(null);
    try {
      const r = await emailRun(runId, recipient.trim());
      setResult(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  };

  return (
    <Card withBorder padding="md" radius="md">
      <Stack gap="sm">
        <Group gap={6}>
          <IconDownload size={16} />
          <Title order={5}>Export or email a run</Title>
        </Group>
        <Text size="xs" c="dimmed">
          Pick any saved NAT diagnosis run. Download as Markdown (works
          offline) or email the report as an attachment (needs SMTP env vars
          on the server).
        </Text>

        {!runs && !error && <Loader size="sm" />}
        {error && (
          <Text size="xs" c="red" ff="monospace">
            {error}
          </Text>
        )}

        {runs && runs.length === 0 && (
          <Text size="sm" c="dimmed">
            No saved runs yet. Run a diagnosis from the Live Copilot first.
          </Text>
        )}

        {runs && runs.length > 0 && (
          <>
            <Select
              label="Run"
              value={runId}
              onChange={setRunId}
              data={runs.map((r) => ({
                value: r.run_id,
                label: `${r.run_id}  ·  ${r.fault_id ?? "?"}  ·  ${
                  r.runtime_seconds?.toFixed(1) ?? "?"
                }s`,
              }))}
              comboboxProps={{ withinPortal: true }}
              searchable
            />
            <Group>
              <Button
                variant="default"
                size="xs"
                leftSection={<IconDownload size={14} />}
                component="a"
                href={runId ? exportRunMarkdownUrl(runId) : "#"}
                target="_blank"
                rel="noopener"
                disabled={!runId}
              >
                Download Markdown
              </Button>
            </Group>

            <Divider label="email" labelPosition="left" />

            <TextInput
              label="Recipient"
              placeholder="ops-supervisor@company.com"
              value={recipient}
              onChange={(e) => setRecipient(e.currentTarget.value)}
              type="email"
            />
            <Group justify="flex-end">
              <Button
                size="xs"
                leftSection={
                  sending ? <Loader size={12} /> : <IconMail size={14} />
                }
                onClick={onEmail}
                disabled={
                  !runId || !recipient.trim() || !recipient.includes("@") || sending
                }
              >
                {sending ? "Sending..." : "Send report"}
              </Button>
            </Group>

            {result && result.sent && (
              <Alert
                color="green"
                variant="light"
                icon={<IconCheck size={16} />}
                title="Email sent"
              >
                Report attached and delivered to {recipient}.
              </Alert>
            )}
            {result && !result.sent && (
              <Alert color="yellow" variant="light" title="SMTP not configured">
                <Text size="sm">{result.reason}</Text>
              </Alert>
            )}
          </>
        )}
      </Stack>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Operator notes
// ---------------------------------------------------------------------------

function NotesCard() {
  const [payload, setPayload] = useState<NotesPayload | null>(null);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getNotes()
      .then((p) => {
        setPayload(p);
        setText(p.text ?? "");
      })
      .catch((e) => setError((e as Error).message));
  }, []);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const p = await saveNotes(text);
      setPayload(p);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const dirty = (payload?.text ?? "") !== text;

  return (
    <Card withBorder padding="md" radius="md">
      <Stack gap="sm">
        <Group gap={6} justify="space-between" wrap="nowrap">
          <Group gap={6}>
            <IconNotes size={16} />
            <Title order={5}>Operator scratchpad</Title>
          </Group>
          {payload?.updated_at && (
            <Text size="xs" c="dimmed">
              saved {new Date(payload.updated_at).toLocaleString()}
            </Text>
          )}
        </Group>
        <Text size="xs" c="dimmed">
          Free-form notes that survive page reloads and restarts. Stored on
          the server at <Code>backend/diagnostics/notes.json</Code>; shared
          across browsers. Not visible to the agent.
        </Text>
        <Textarea
          autosize
          minRows={4}
          maxRows={20}
          value={text}
          onChange={(e) => setText(e.currentTarget.value)}
          placeholder="e.g. IDV-4 + IDV-6 combo trips around 60% magnitude. Stripper steam valve runs hot when reactor temp drifts above 122.5°C."
        />
        {error && (
          <Text size="xs" c="red" ff="monospace">
            {error}
          </Text>
        )}
        <Group justify="flex-end">
          <Button
            size="xs"
            disabled={saving || !dirty}
            onClick={save}
            leftSection={saving ? <Loader size={12} /> : null}
          >
            {saving ? "Saving..." : dirty ? "Save" : "Saved"}
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// KB upload
// ---------------------------------------------------------------------------

function KbUploadCard() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<KbUploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onUpload = async (files: File[] | null) => {
    if (!files || files.length === 0) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await uploadKbFiles(files);
      setResult(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card withBorder padding="md" radius="md">
      <Stack gap="sm">
        <Group gap={6}>
          <IconCloudUpload size={16} />
          <Title order={5}>Upload to knowledge base</Title>
        </Group>
        <Text size="xs" c="dimmed">
          Add reference documents the agent can cite. Drop pre-converted{" "}
          <Code>.md</Code> files for immediate retrieval, or PDFs which will be
          stored alongside but only become searchable after offline conversion.
          See <Code>RAG/converted_markdown/</Code>.
        </Text>
        <Group>
          <FileButton
            multiple
            accept="application/pdf,text/markdown,.md,.pdf,.docx"
            onChange={onUpload}
          >
            {(props) => (
              <Button
                {...props}
                size="xs"
                variant="default"
                leftSection={
                  busy ? <Loader size={12} /> : <IconCloudUpload size={14} />
                }
                disabled={busy}
              >
                {busy ? "Uploading..." : "Choose files"}
              </Button>
            )}
          </FileButton>
        </Group>

        {error && (
          <Alert color="red" variant="light" title="Upload failed">
            <Text size="xs" ff="monospace">
              {error}
            </Text>
          </Alert>
        )}

        {result && (
          <Alert color="green" variant="light" title="Uploaded">
            <Stack gap={4}>
              <Text size="xs">{result.hint}</Text>
              <List size="xs">
                {result.saved.map((p) => (
                  <List.Item key={p}>
                    <Anchor size="xs" component="span" ff="monospace">
                      {p}
                    </Anchor>
                  </List.Item>
                ))}
              </List>
            </Stack>
          </Alert>
        )}
      </Stack>
    </Card>
  );
}
