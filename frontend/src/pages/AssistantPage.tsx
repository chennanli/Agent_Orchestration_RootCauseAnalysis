import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Container,
  Paper,
  Title,
  Text,
  Stack,
  Group,
  Button,
  Textarea,
  ActionIcon,
  ScrollArea,
  Accordion,
  Badge,
  Loader,
  Alert,
  Box,
  Divider,
  Select,
  Grid,
  Radio,
} from "@mantine/core";
import {
  IconSend,
  IconAlertCircle,
  IconRobot,
  IconUser,
  IconBook,
  IconChartLine,
  IconCheck,
  IconFolder,
} from "@tabler/icons-react";
import { marked } from "marked";

interface AnalysisSnapshot {
  id: string;
  timestamp: string;
  feature_analysis?: string;
  llm_analyses?: Record<string, any>;
  sensor_data?: Record<string, number[]>;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  sources?: KnowledgeSource[];  // NEW: RAG sources for this message
  model_used?: string;           // NEW: Which model generated this response
}

interface KnowledgeSource {
  source: string;
  section: string;
  relevance: number;
  page?: number;  // NEW: Page number if available
}

export default function AssistantPage() {
  const [searchParams] = useSearchParams();
  const [analysis, setAnalysis] = useState<AnalysisSnapshot | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [knowledgeSources, setKnowledgeSources] = useState<KnowledgeSource[]>([]);
  const [chatModel, setChatModel] = useState<string>("anthropic");  // Default to Claude
  const [generatingReport, setGeneratingReport] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
  const analysisId = searchParams.get("analysis_id");

  // Load analysis snapshot on mount
  useEffect(() => {
    if (analysisId) {
      loadAnalysis(analysisId);
    }
  }, [analysisId]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTo({
        top: scrollAreaRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages]);

  // 🔗 Listen for messages from Unified Console (iframe communication)
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Security check - only accept messages from Unified Console
      if (event.origin !== 'http://127.0.0.1:9002') {
        return;
      }

      console.log('📥 Frontend received message:', event.data);

      if (event.data.type === 'LOAD_SNAPSHOT') {
        const analysisId = event.data.analysis_id;
        console.log('🔗 Loading snapshot from Unified Console:', analysisId);

        // Load the snapshot
        loadAnalysis(analysisId.toString());

        // Send confirmation back to Unified Console
        window.parent.postMessage({
          type: 'SNAPSHOT_LOADED',
          success: true,
          analysis_id: analysisId
        }, 'http://127.0.0.1:9002');
      }
    };

    window.addEventListener('message', handleMessage);

    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, []);

  const loadAnalysis = async (id: string) => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${apiBaseUrl}/analysis/item/${id}`);
      
      if (!response.ok) {
        throw new Error(`Failed to load analysis: ${response.statusText}`);
      }
      
      const data = await response.json();
      setAnalysis(data);
      
      // Add welcome message
      setMessages([
        {
          role: "assistant",
          content: `I've loaded the analysis from ${data.timestamp || "unknown time"}. I can help you understand the fault diagnosis, suggest alternative root causes, or answer questions about the TEP process. What would you like to discuss?`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analysis");
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!inputText.trim() || !analysisId) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: inputText,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputText("");
    setLoading(true);

    try {
      const response = await fetch(`${apiBaseUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: "pinned",
          analysis_id: analysisId,
          query: inputText,
          model: chatModel,  // NEW: Send selected model
          history: messages.slice(-6), // Last 6 messages for context
        }),
      });

      if (!response.ok) {
        throw new Error(`Chat failed: ${response.statusText}`);
      }

      const data = await response.json();

      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: data.answer,
        timestamp: data.timestamp,
        sources: data.sources || [],      // NEW: Attach RAG sources to message
        model_used: data.model_used || chatModel,  // NEW: Track which model was used
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Update global knowledge sources if provided
      if (data.sources && data.sources.length > 0) {
        setKnowledgeSources(data.sources);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const quickActions = [
    { label: "Explain this analysis", query: "Can you explain this analysis in detail?" },
    { label: "Alternative causes", query: "What are alternative root causes for this fault?" },
    { label: "Recommended actions", query: "What corrective actions do you recommend?" },
    { label: "Similar faults", query: "What similar faults have occurred in TEP?" },
  ];

  const handleQuickAction = (query: string) => {
    setInputText(query);
  };

  const handleOpenReportsFolder = async () => {
    try {
      const unifiedConsoleUrl = "http://127.0.0.1:9002";
      const response = await fetch(`${unifiedConsoleUrl}/api/open-diagnostics-folder`, {
        method: "POST",
      });

      const data = await response.json();

      if (data.success) {
        console.log("✅ Opened reports folder");
      } else {
        alert(`❌ Failed to open folder: ${data.error || "Unknown error"}`);
      }
    } catch (error) {
      alert(`❌ Error opening folder: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  };

  const handleCompleteAnalysis = async () => {
    if (!analysisId) {
      alert("❌ No analysis loaded");
      return;
    }

    const conclusion = prompt(
      "Please provide your final conclusion for this RCA (optional):",
      "Root cause analysis completed via Interactive RCA"
    );

    if (conclusion === null) return; // User cancelled

    setGeneratingReport(true);

    try {
      const unifiedConsoleUrl = "http://127.0.0.1:9002";
      const response = await fetch(`${unifiedConsoleUrl}/api/report/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          snapshot_id: parseInt(analysisId),
          conclusion: conclusion,
          email: "tep-rca-system@example.com",
          chat_history: messages,
          ruled_out: [],
        }),
      });

      const data = await response.json();

      if (response.ok && data.filename) {
        alert(
          `✅ Report generated successfully!\n\nFile: ${data.filename}\nFormat: ${data.format || "PDF"}\n${
            data.email_sent
              ? `Email sent to: ${data.recipient || "tep-rca-system@example.com"}`
              : "Saved locally (email sending may have failed)"
          }`
        );
        setAnalysisComplete(true);
      } else {
        alert(`⚠️ Report generation completed with warnings:\n${data.error || "Unknown issue"}`);
      }
    } catch (error) {
      alert(`❌ Error generating report: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setGeneratingReport(false);
    }
  };

  return (
    <Container size="xl" py="md">
      <Stack gap="md">
        {/* Header */}
        <Paper p="md" withBorder>
          <Group justify="space-between">
            <div>
              <Title order={2}>Interactive RCA Assistant</Title>
              <Text size="sm" c="dimmed">
                {analysisId ? `Analysis ID: ${analysisId}` : "No analysis loaded"}
              </Text>
            </div>
            <Group gap="md">
              {analysis && (
                <Badge size="lg" variant="light" color="blue">
                  {analysis.timestamp || "Unknown time"}
                </Badge>
              )}
              <Button
                onClick={handleOpenReportsFolder}
                leftSection={<IconFolder size={16} />}
                variant="light"
                color="teal"
                size="sm"
              >
                Browse Reports
              </Button>
            </Group>
          </Group>
        </Paper>

        {/* Error Alert */}
        {error && (
          <Alert icon={<IconAlertCircle size={16} />} title="Error" color="red" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Main Content - Balanced Grid Layout */}
        <Grid gutter="md">
          {/* Left Panel - Analysis Summary (35% width) */}
          <Grid.Col span={4}>
            <Paper p="md" withBorder style={{ maxHeight: "calc(100vh - 200px)", overflow: "auto" }}>
              <Stack gap="sm">
                <Title order={4}>Analysis Summary</Title>
              
              {loading && !analysis && (
                <Group justify="center" p="xl">
                  <Loader size="sm" />
                  <Text size="sm">Loading analysis...</Text>
                </Group>
              )}

              {analysis && (
                <Accordion variant="separated">
                  {/* Feature Analysis */}
                  {analysis.feature_analysis && (
                    <Accordion.Item value="feature">
                      <Accordion.Control icon={<IconChartLine size={16} />}>
                        Feature Analysis
                      </Accordion.Control>
                      <Accordion.Panel>
                        <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                          {analysis.feature_analysis}
                        </Text>
                      </Accordion.Panel>
                    </Accordion.Item>
                  )}

                  {/* LLM Analyses */}
                  {analysis.llm_analyses && Object.entries(analysis.llm_analyses).map(([model, data]: [string, any]) => (
                    data && data.analysis && (
                      <Accordion.Item key={model} value={model}>
                        <Accordion.Control icon={<IconRobot size={16} />}>
                          {model.toUpperCase()} Analysis
                        </Accordion.Control>
                        <Accordion.Panel>
                          <div
                            dangerouslySetInnerHTML={{
                              __html: marked(data.analysis || "No analysis available"),
                            }}
                            style={{ fontSize: "0.875rem" }}
                          />
                        </Accordion.Panel>
                      </Accordion.Item>
                    )
                  ))}

                  {/* Knowledge Sources */}
                  {knowledgeSources.length > 0 && (
                    <Accordion.Item value="knowledge">
                      <Accordion.Control icon={<IconBook size={16} />}>
                        Knowledge Sources ({knowledgeSources.length})
                      </Accordion.Control>
                      <Accordion.Panel>
                        <Stack gap="xs">
                          {knowledgeSources.map((source, idx) => (
                            <Paper key={idx} p="xs" withBorder>
                              <Text size="xs" fw={500}>{source.source}</Text>
                              <Text size="xs" c="dimmed">{source.section}</Text>
                              <Badge size="xs" variant="light">
                                Relevance: {(source.relevance * 100).toFixed(0)}%
                              </Badge>
                            </Paper>
                          ))}
                        </Stack>
                      </Accordion.Panel>
                    </Accordion.Item>
                  )}
                </Accordion>
              )}
            </Stack>
          </Paper>
          </Grid.Col>

          {/* Right Panel - Chat Interface (65% width) */}
          <Grid.Col span={8}>
            <Paper p="md" withBorder style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 200px)" }}>
              <Stack gap="md" style={{ height: "100%" }}>
                {/* Chat Header with Model Selector */}
                <Group justify="space-between" align="flex-start">
                  <Title order={4}>Chat</Title>

                  {/* 🔧 FIXED: Allow free model selection */}
                  <Stack gap="xs">
                    <Text size="xs" fw={500}>Select AI Model</Text>
                    <Radio.Group
                      value={chatModel}
                      onChange={(value) => setChatModel(value)}
                      name="chatModel"
                    >
                      <Stack gap="xs">
                        <Radio
                          value="lmstudio"
                          label="💻 LMStudio (Local - Free)"
                          size="sm"
                        />
                        <Radio
                          value="gemini"
                          label="🌟 Gemini (Cloud - Budget)"
                          size="sm"
                        />
                        <Radio
                          value="anthropic"
                          label="🧠 Claude (Cloud - Premium)"
                          size="sm"
                        />
                      </Stack>
                    </Radio.Group>
                  </Stack>
                </Group>

              {/* Quick Actions */}
              <Group gap="xs">
                {quickActions.map((action, idx) => (
                  <Button
                    key={idx}
                    size="xs"
                    variant="light"
                    onClick={() => handleQuickAction(action.query)}
                  >
                    {action.label}
                  </Button>
                ))}
              </Group>

              <Divider />

              {/* Messages */}
              <ScrollArea style={{ flex: 1 }} viewportRef={scrollAreaRef}>
                <Stack gap="md">
                  {messages.map((msg, idx) => (
                    <Paper
                      key={idx}
                      p="md"
                      withBorder
                      style={{
                        backgroundColor: msg.role === "user" ? "#f8f9fa" : "#e7f5ff",
                        marginLeft: msg.role === "user" ? "auto" : 0,
                        marginRight: msg.role === "assistant" ? "auto" : 0,
                        maxWidth: "80%",
                      }}
                    >
                      <Group gap="xs" mb="xs">
                        {msg.role === "user" ? <IconUser size={16} /> : <IconRobot size={16} />}
                        <Text size="sm" fw={500}>
                          {msg.role === "user" ? "You" : "Assistant"}
                        </Text>
                        {/* Show which model was used */}
                        {msg.model_used && (
                          <Badge size="xs" variant="light">
                            {msg.model_used}
                          </Badge>
                        )}
                      </Group>
                      <div
                        dangerouslySetInnerHTML={{
                          __html: marked(msg.content),
                        }}
                        style={{ fontSize: "0.875rem" }}
                      />

                      {/* Show RAG Knowledge Sources (Wiki.js style) */}
                      {msg.sources && msg.sources.length > 0 && (
                        <Paper p="xs" mt="sm" bg="gray.0" radius="sm" withBorder>
                          <Group gap={4} mb={4}>
                            <IconBook size={14} />
                            <Text size="xs" fw={600}>Knowledge Sources:</Text>
                          </Group>
                          <Stack gap={4}>
                            {msg.sources.map((src, srcIdx) => (
                              <Text key={srcIdx} size="xs" c="dimmed" style={{ paddingLeft: 18 }}>
                                • <strong>{src.source}</strong> - {src.section}
                                {src.page && ` (p.${src.page})`}
                                <Badge size="xs" variant="light" ml={4}>
                                  {(src.relevance * 100).toFixed(0)}%
                                </Badge>
                              </Text>
                            ))}
                          </Stack>
                        </Paper>
                      )}
                    </Paper>
                  ))}
                  {loading && (
                    <Group justify="center">
                      <Loader size="sm" />
                    </Group>
                  )}
                </Stack>
              </ScrollArea>

              {/* Input */}
              <Group gap="xs" align="flex-end">
                <Textarea
                  placeholder="Ask a question about this analysis..."
                  value={inputText}
                  onChange={(e) => setInputText(e.currentTarget.value)}
                  onKeyDown={handleKeyPress}
                  minRows={2}
                  maxRows={4}
                  style={{ flex: 1 }}
                  disabled={loading || !analysis}
                />
                <ActionIcon
                  size="lg"
                  variant="filled"
                  onClick={sendMessage}
                  disabled={loading || !inputText.trim() || !analysis}
                >
                  <IconSend size={18} />
                </ActionIcon>
              </Group>

              {/* Done with Analysis Button */}
              {analysis && (
                <Button
                  onClick={handleCompleteAnalysis}
                  loading={generatingReport}
                  leftSection={<IconCheck size={18} />}
                  size="lg"
                  color="green"
                  fullWidth
                  disabled={analysisComplete}
                  variant={analysisComplete ? "light" : "filled"}
                >
                  {analysisComplete
                    ? "✅ Analysis Complete - Report Generated"
                    : "Complete Analysis & Generate Report"}
                </Button>
              )}
            </Stack>
          </Paper>
          </Grid.Col>
        </Grid>
      </Stack>
    </Container>
  );
}

