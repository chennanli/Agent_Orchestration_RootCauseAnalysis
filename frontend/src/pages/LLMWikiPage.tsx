import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Stack,
  Title,
  Text,
  Grid,
  Card,
  TextInput,
  Group,
  Badge,
  ScrollArea,
  Code,
  Button,
  Divider,
} from "@mantine/core";
import { IconSearch, IconRefresh, IconBook2 } from "@tabler/icons-react";
import SafetyBoundaryBanner from "../components/SafetyBoundaryBanner";
import WikiSourceCard, { WikiSourceExcerpt } from "../components/WikiSourceCard";

interface WikiSource {
  source_document: string;
  chunk_count?: number;
  tags?: string[];
}

const TAG_GUESS: { keyword: string; tag: string }[] = [
  { keyword: "reactor", tag: "reactor" },
  { keyword: "cooling", tag: "cooling" },
  { keyword: "separator", tag: "separator" },
  { keyword: "stripper", tag: "stripper" },
  { keyword: "fault", tag: "fault" },
  { keyword: "control", tag: "control" },
  { keyword: "feed", tag: "feed" },
  { keyword: "pca", tag: "pca" },
  { keyword: "valve", tag: "valve" },
  { keyword: "compressor", tag: "compressor" },
];

function deriveTags(text: string): string[] {
  const lc = (text || "").toLowerCase();
  return TAG_GUESS.filter((t) => lc.includes(t.keyword)).map((t) => t.tag);
}

export default function LLMWikiPage() {
  // Deep-link support: ?doc=<source_document>&q=<initial search>. Used when
  // the user clicks a source citation in the Live Copilot trace.
  const [searchParams] = useSearchParams();
  const linkedDoc = searchParams.get("doc");
  const linkedQuery = searchParams.get("q");

  const [sources, setSources] = useState<WikiSource[]>([]);
  const [excerpts, setExcerpts] = useState<WikiSourceExcerpt[]>([]);
  const [query, setQuery] = useState<string>(
    linkedQuery || "reactor cooling water disturbance",
  );
  const [selectedSrc, setSelectedSrc] = useState<string | null>(linkedDoc);
  const [selectedExcerpt, setSelectedExcerpt] = useState<WikiSourceExcerpt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  async function loadSources() {
    setError(null);
    try {
      const res = await fetch("/api/wiki/sources");
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data = await res.json();
      setSources(data.sources || []);
    } catch (e: any) {
      setError(`Could not load /api/wiki/sources. ${e?.message ?? e}`);
    }
  }

  async function runSearch() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/wiki/search?q=${encodeURIComponent(query)}&max_results=8`
      );
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data = await res.json();
      const items: WikiSourceExcerpt[] = (data.excerpts || []).map((e: any) => ({
        ...e,
        tags: deriveTags(`${e.section || ""} ${e.excerpt || ""}`),
      }));
      setExcerpts(items);
      setSelectedExcerpt(items[0] || null);
    } catch (e: any) {
      setError(
        `Wiki search endpoint /api/wiki/search not reachable. Backend may be running the legacy demo only. (${e?.message ?? e})`
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSources();
    // Fire one search on mount so the Source Excerpts panel isn't empty.
    // The user can refine the query afterwards; clicking a source name then
    // filters the visible excerpts to just that document.
    runSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When the user clicks a source in the left list, re-search scoped to that
  // doc's keywords so the right panel always has something to show.
  useEffect(() => {
    if (selectedSrc) {
      // Use the source name itself as a hint for the search if user hasn't
      // typed anything specific yet.
      runSearch();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSrc]);

  const filteredExcerpts = useMemo(() => {
    if (!selectedSrc) return excerpts;
    return excerpts.filter((e) => e.source_document === selectedSrc);
  }, [excerpts, selectedSrc]);

  return (
    <Stack gap="md">
      <div>
        <Title order={2}>LLM Wiki</Title>
        <Text size="sm" c="dimmed">
          Engineer-facing view of the source documents the agent reads. The wiki
          shows source excerpts and how the agent uses them. Retrieval here is
          keyword-based; embeddings / vector search would be a separate change.
        </Text>
      </div>

      <SafetyBoundaryBanner variant="compact" />

      <Card withBorder padding="md" radius="sm">
        <Group align="flex-end" gap="md" wrap="wrap">
          <TextInput
            label="Search the wiki"
            placeholder="reactor cooling water disturbance"
            value={query}
            onChange={(e) => setQuery(e.currentTarget.value)}
            leftSection={<IconSearch size={14} />}
            style={{ flex: 1, minWidth: 240 }}
            onKeyDown={(e) => e.key === "Enter" && runSearch()}
          />
          <Button onClick={runSearch} loading={loading}>
            Search
          </Button>
          <Button
            variant="default"
            leftSection={<IconRefresh size={14} />}
            onClick={loadSources}
          >
            Refresh wiki index
          </Button>
        </Group>
        {error && (
          <Text size="xs" c="orange" mt={6}>
            {error}
          </Text>
        )}
      </Card>

      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 3 }}>
          <Card withBorder padding="md" radius="sm" h="100%">
            <Group gap="xs" mb="xs">
              <IconBook2 size={16} />
              <Text fw={600} size="sm">
                Sources
              </Text>
            </Group>
            <ScrollArea h={420}>
              <Stack gap={6}>
                <Card
                  withBorder
                  padding="xs"
                  radius="sm"
                  style={{
                    cursor: "pointer",
                    background: selectedSrc === null ? "#eef2ff" : undefined,
                  }}
                  onClick={() => setSelectedSrc(null)}
                >
                  <Text size="sm">All sources</Text>
                </Card>
                {sources.length === 0 && (
                  <Text size="xs" c="dimmed">
                    No source list yet. Click "Refresh wiki index" or wire
                    /api/wiki/sources.
                  </Text>
                )}
                {sources.map((s) => (
                  <Card
                    key={s.source_document}
                    withBorder
                    padding="xs"
                    radius="sm"
                    style={{
                      cursor: "pointer",
                      background:
                        selectedSrc === s.source_document ? "#eef2ff" : undefined,
                    }}
                    onClick={() => setSelectedSrc(s.source_document)}
                  >
                    <Text size="sm" fw={500} truncate>
                      {s.source_document}
                    </Text>
                    {typeof s.chunk_count === "number" && (
                      <Text size="xs" c="dimmed">
                        {s.chunk_count} source excerpts
                      </Text>
                    )}
                  </Card>
                ))}
              </Stack>
            </ScrollArea>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder padding="md" radius="sm" h="100%">
            <Group gap="xs" mb="xs">
              <Text fw={600} size="sm">
                Source excerpts
              </Text>
              <Badge variant="light" color="indigo">
                {filteredExcerpts.length}
              </Badge>
            </Group>
            <ScrollArea h={420}>
              <Stack gap="sm">
                {filteredExcerpts.length === 0 && (
                  <Text size="xs" c="dimmed">
                    No excerpts yet. Try a search like "reactor cooling water".
                  </Text>
                )}
                {filteredExcerpts.map((e, i) => (
                  <WikiSourceCard
                    key={i}
                    excerpt={e}
                    onSelect={() => setSelectedExcerpt(e)}
                    selected={selectedExcerpt === e}
                  />
                ))}
              </Stack>
            </ScrollArea>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 3 }}>
          <Card withBorder padding="md" radius="sm" h="100%">
            <Text fw={600} size="sm" mb="xs">
              How the agent uses this
            </Text>
            {selectedExcerpt ? (
              <Stack gap="xs">
                <Text size="xs" c="dimmed">
                  When the agent calls{" "}
                  <Code>search_process_knowledge</Code>, this excerpt becomes a
                  candidate citation. The agent must keep the source document
                  name in its final advisory.
                </Text>
                <Divider />
                <Text size="xs" fw={600}>
                  source: {selectedExcerpt.source_document}
                </Text>
                {selectedExcerpt.section && (
                  <Text size="xs" c="dimmed">
                    section: {selectedExcerpt.section}
                  </Text>
                )}
                <Text size="xs" style={{ whiteSpace: "pre-wrap" }}>
                  {selectedExcerpt.excerpt}
                </Text>
              </Stack>
            ) : (
              <Text size="xs" c="dimmed">
                Pick a source excerpt to see how the agent would use it.
              </Text>
            )}
          </Card>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
