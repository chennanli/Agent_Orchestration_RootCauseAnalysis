import React, { useState, useEffect, useRef } from "react";
import {
  ScrollArea,
  Text,
  Card,
  SimpleGrid,
  Badge,
  Table,
  Accordion,
  Group,
  Stack,
  Paper,
  Progress,
  Alert,
  Button,
  ActionIcon,
  Tooltip,
} from "@mantine/core";
import { IconClock, IconRobot, IconAlertCircle, IconCheck, IconHeartbeat, IconPlayerPause, IconPlayerPlay } from "@tabler/icons-react";
import { marked } from "marked";

interface LLMAnalysis {
  analysis: string;
  response_time: number;
  status: string;
}

interface ComparativeResults {
  timestamp: string;
  feature_analysis: string;
  llm_analyses: Record<string, LLMAnalysis>;
  performance_summary: Record<string, { response_time: number; word_count: number }>;
}

interface ComparativeLLMResultsProps {
  results: ComparativeResults | null;
  isLoading: boolean;
}

// Independent model results interface
interface IndependentModelResult {
  model: string;
  analysis: string;
  status: 'analyzing' | 'displaying' | 'idle';
  timestamp?: string;
  response_time?: number;
  word_count?: number;
}

interface ModelCardProps {
  modelName: string;
  analysis: LLMAnalysis;
  performance?: any;
  onFreeze?: (modelName: string) => void;
  onUnfreeze?: (modelName: string) => void;
  isFrozen?: boolean;
}

const ModelCard: React.FC<ModelCardProps> = ({
  modelName,
  analysis,
  performance,
  onFreeze,
  onUnfreeze,
  isFrozen = false,
}) => {
  const getModelIcon = () => {
    return <IconRobot size={16} />;
  };

  // Map backend model names to display names
  const getDisplayName = (backendName: string) => {
    const nameMap: Record<string, string> = {
      'anthropic': 'Claude',
      'gemini': 'Gemini',
      'lmstudio': 'Local Model',
      'mistral': 'Local LLM (Disabled)',
      'fastllm': 'Local LLM'
    };
    return nameMap[backendName.toLowerCase()] || backendName;
  };

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Group justify="space-between" mb="md">
        <Group>
          {getModelIcon()}
          <Text fw={600} size="lg" tt="capitalize">
            {getDisplayName(modelName)}
          </Text>
        </Group>
        <Group>
          <Badge
            color={analysis.status === "success" ? "green" : "red"}
            variant="light"
            leftSection={analysis.status === "success" ? <IconCheck size={12} /> : <IconAlertCircle size={12} />}
          >
            {analysis.status}
          </Badge>
          {analysis.response_time > 0 && (
            <Badge color="gray" variant="light" leftSection={<IconClock size={12} />}>
              {analysis.response_time}s
            </Badge>
          )}
          {isFrozen && (
            <Badge color="blue" variant="light" leftSection={<IconPlayerPause size={12} />}>
              Frozen
            </Badge>
          )}
          <Tooltip label={isFrozen ? "Unfreeze display" : "Freeze display"}>
            <ActionIcon
              variant="light"
              color={isFrozen ? "orange" : "blue"}
              size="lg"
              onClick={() => isFrozen ? onUnfreeze?.(modelName) : onFreeze?.(modelName)}
            >
              {isFrozen ? <IconPlayerPlay size={24} /> : <IconPlayerPause size={24} />}
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>

      {analysis.status === "success" ? (
        <ScrollArea.Autosize mah={600} offsetScrollbars>
          <div
            dangerouslySetInnerHTML={{
              __html: marked.parse(analysis.analysis),
            }}
            style={{ fontSize: "14px", lineHeight: "1.5" }}
          />
        </ScrollArea.Autosize>
      ) : (
        <Alert color="red" icon={<IconAlertCircle size={16} />}>
          {analysis.analysis}
        </Alert>
      )}

      {performance && (
        <Paper p="xs" mt="md" bg="gray.0">
          <Group justify="space-between">
            <Text size="xs" c="dimmed">
              Words: {performance.word_count}
            </Text>
            <Text size="xs" c="dimmed">
              Speed: {(performance.word_count / performance.response_time).toFixed(1)} words/s
            </Text>
          </Group>
        </Paper>
      )}
    </Card>
  );
};

const PerformanceComparison: React.FC<{ performance: Record<string, any> }> = ({ performance }) => {
  const models = Object.keys(performance);
  const maxTime = Math.max(...models.map(m => performance[m].response_time));

  // Map backend model names to display names
  const getDisplayName = (backendName: string) => {
    const nameMap: Record<string, string> = {
      'anthropic': 'Claude',
      'gemini': 'Gemini',
      'lmstudio': 'LM Studio',
      'mistral': 'Local LLM',
      'fastllm': 'Local LLM'
    };
    return nameMap[backendName.toLowerCase()] || backendName;
  };

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Text fw={600} size="lg" mb="md">
        Performance Comparison
      </Text>
      
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Model</Table.Th>
            <Table.Th>Response Time</Table.Th>
            <Table.Th>Word Count</Table.Th>
            <Table.Th>Words/Second</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {models.map((model) => {
            const perf = performance[model];
            const wordsPerSecond = (perf.word_count / perf.response_time).toFixed(1);
            const timePercentage = (perf.response_time / maxTime) * 100;
            
            return (
              <Table.Tr key={model}>
                <Table.Td>
                  <Text tt="capitalize" fw={500}>{getDisplayName(model)}</Text>
                </Table.Td>
                <Table.Td>
                  <Group>
                    <Progress value={timePercentage} size="sm" w={60} />
                    <Text size="sm">{perf.response_time}s</Text>
                  </Group>
                </Table.Td>
                <Table.Td>{perf.word_count}</Table.Td>
                <Table.Td>{wordsPerSecond}</Table.Td>
              </Table.Tr>
            );
          })}
        </Table.Tbody>
      </Table>
    </Card>
  );
};

export default function ComparativeLLMResults({ results, isLoading }: ComparativeLLMResultsProps) {
  const [lmstudioHealth, setLmstudioHealth] = useState<any>(null);
  const [checkingHealth, setCheckingHealth] = useState(false);
  const [frozenModels, setFrozenModels] = useState<Set<string>>(new Set());
  const [frozenAnalyses, setFrozenAnalyses] = useState<Record<string, LLMAnalysis>>({});
  const [lastResults, setLastResults] = useState<ComparativeResults | null>(null);
  const [polledResults, setPolledResults] = useState<ComparativeResults | null>(null);

  // 🔧 FIX: Use refs to access latest frozen state in polling callback
  const frozenModelsRef = useRef(frozenModels);
  const frozenAnalysesRef = useRef(frozenAnalyses);

  // Keep refs in sync
  useEffect(() => {
    frozenModelsRef.current = frozenModels;
    frozenAnalysesRef.current = frozenAnalyses;
  }, [frozenModels, frozenAnalyses]);

  // 🔧 CRITICAL FIX: Only poll when NOT frozen, and respect backend LLM interval
  useEffect(() => {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
    let lastTimestamp = "";
    let intervalId: NodeJS.Timeout | null = null;

    // Fetch backend config to get actual LLM interval
    const fetchBackendConfig = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/independent/status`);
        if (response.ok) {
          const data = await response.json();
          const configInterval = data.llm_min_interval_seconds || 60;
          const pollingInterval = configInterval * 1000; // Convert to milliseconds
          console.log(`📊 Backend LLM interval: ${configInterval}s, polling every ${pollingInterval/1000}s`);
          return pollingInterval;
        }
      } catch (error) {
        console.warn("⚠️ Could not fetch backend config, using default 60s interval");
      }
      return 60000; // Default 60s
    };

    const pollLatestAnalysis = async () => {
      // 🔧 CRITICAL FIX: Don't poll if ANY model is frozen (prevents scroll jump)
      if (frozenModelsRef.current.size > 0) {
        console.log(`❄️ Skipping poll - ${frozenModelsRef.current.size} model(s) frozen`);
        return;
      }

      const pollTime = new Date().toLocaleTimeString();
      console.log(`🔄 [${pollTime}] Polling latest analysis...`);

      try {
        const response = await fetch(`${apiBaseUrl}/analysis/latest`);
        if (response.ok) {
          const data = await response.json();
          // 🔧 CRITICAL: Only update if timestamp changed (avoid unnecessary re-renders)
          if (data.llm_analyses && Object.keys(data.llm_analyses).length > 0) {
            if (data.timestamp && data.timestamp !== lastTimestamp) {
              console.log(`✅ [${pollTime}] Polled NEW analysis:`, data.timestamp);
              lastTimestamp = data.timestamp;

              setPolledResults(data);
            } else {
              console.log(`⏭️ [${pollTime}] Skipping update - same timestamp:`, data.timestamp);
            }
          }
        }
      } catch (error) {
        console.error(`❌ [${pollTime}] Failed to poll latest analysis:`, error);
      }
    };

    // Initialize: fetch config and start polling
    fetchBackendConfig().then((pollingInterval) => {
      // Initial poll
      pollLatestAnalysis();

      // 🔧 FIX: Poll at backend's LLM interval (not fixed 10s)
      intervalId = setInterval(pollLatestAnalysis, pollingInterval);
    });

    // 🔧 CRITICAL FIX: Proper cleanup to stop polling
    return () => {
      if (intervalId) {
        console.log("🛑 Stopping polling interval");
        clearInterval(intervalId);
      }
    };
  }, []);

  // 保存上次成功的结果，避免显示"SKIPPED"
  useEffect(() => {
    if (results && results.llm_analyses && Object.keys(results.llm_analyses).length > 0) {
      // 检查是否有真实结果（不是skipped）
      const hasRealResults = Object.values(results.llm_analyses).some(
        analysis => analysis.status !== "skipped"
      );
      if (hasRealResults) {
        setLastResults(results);
      }
    }
  }, [results]);

  const handleFreeze = (modelName: string) => {
    // 🔧 CLIENT-SIDE FREEZE: Save current analysis to frozen state
    const currentAnalysis = displayResults?.llm_analyses[modelName];
    if (currentAnalysis) {
      console.log(`❄️ Freezing ${modelName} display at current analysis`);
      setFrozenAnalyses(prev => ({
        ...prev,
        [modelName]: currentAnalysis
      }));
      setFrozenModels(prev => new Set([...prev, modelName]));
    }
  };

  const handleUnfreeze = (modelName: string) => {
    // 🔧 CLIENT-SIDE UNFREEZE: Remove from frozen state, resume live updates
    console.log(`🔓 Unfreezing ${modelName} display`);
    setFrozenModels(prev => {
      const newSet = new Set(prev);
      newSet.delete(modelName);
      return newSet;
    });
    setFrozenAnalyses(prev => {
      const newAnalyses = { ...prev };
      delete newAnalyses[modelName];
      return newAnalyses;
    });
  };

  // 🔧 NEW: Prioritize polled results (from ULTRA START mode) over context results
  // Priority: polledResults > lastResults > results
  const displayResults = polledResults || lastResults || results;

  const checkLMStudioHealth = async () => {
    setCheckingHealth(true);
    try {
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
      const response = await fetch(`${apiBaseUrl}/health/lmstudio`);
      const health = await response.json();
      setLmstudioHealth(health);
    } catch (error) {
      setLmstudioHealth({ status: "error", error: "Cannot connect to backend" });
    } finally {
      setCheckingHealth(false);
    }
  };

  if (isLoading) {
    return (
      <ScrollArea h={`calc(100vh - 60px - 32px)`}>
        <Stack align="center" justify="center" h="50vh">
          <Text size="lg">🤖 Analyzing with multiple LLMs...</Text>
          <Progress size="lg" value={100} striped animated />
        </Stack>
      </ScrollArea>
    );
  }

  if (!displayResults) {
    return (
      <ScrollArea h={`calc(100vh - 60px - 32px)`}>
        <Stack align="center" justify="center" h="50vh">
          <Text size="lg" c="dimmed">No analysis results available</Text>
          <Text size="sm" c="dimmed">Run a fault analysis to see comparative LLM results</Text>
        </Stack>
      </ScrollArea>
    );
  }

  const models = Object.keys(displayResults.llm_analyses);

  return (
    <ScrollArea h={`calc(100vh - 60px - 32px)`}>
      <Stack gap="lg" p="md">
        {/* Header */}
        <Paper p="md" bg="blue.0">
          <Group justify="space-between">
            <Text size="xl" fw={700}>
              🔍 Multi-LLM Fault Analysis Comparison
            </Text>
            <Group>
              <Button
                size="sm"
                variant="light"
                leftSection={<IconHeartbeat size={16} />}
                onClick={checkLMStudioHealth}
                loading={checkingHealth}
              >
                Check LMStudio
              </Button>
              <Text size="sm" c="dimmed">
                Individual freeze controls on each model
              </Text>
              <Text size="sm" c="dimmed">
                {displayResults.timestamp}
              </Text>
            </Group>
          </Group>
        </Paper>

        {/* LMStudio Health Status */}
        {lmstudioHealth && (
          <Alert
            color={lmstudioHealth.status === "healthy" ? "green" : "red"}
            icon={lmstudioHealth.status === "healthy" ? <IconCheck size={16} /> : <IconAlertCircle size={16} />}
            title={`LMStudio Status: ${lmstudioHealth.status.toUpperCase()}`}
            withCloseButton
            onClose={() => setLmstudioHealth(null)}
          >
            {lmstudioHealth.status === "healthy" ? (
              <Text size="sm">
                ✅ {lmstudioHealth.models_available} models available
              </Text>
            ) : (
              <Text size="sm">
                ❌ {lmstudioHealth.error}
                <br />
                💡 Try restarting LMStudio server or run: <code>./lmstudio_quick_check.sh --fix</code>
              </Text>
            )}
          </Alert>
        )}

        {/* Feature Analysis */}
        <Accordion defaultValue="features">
          <Accordion.Item value="features">
            <Accordion.Control>
              <Text fw={600}>📊 Feature Analysis</Text>
            </Accordion.Control>
            <Accordion.Panel>
              <Paper p="md" bg="gray.0">
                <pre style={{ whiteSpace: "pre-wrap", fontSize: "14px" }}>
                  {displayResults.feature_analysis}
                </pre>
              </Paper>
            </Accordion.Panel>
          </Accordion.Item>
        </Accordion>

        {/* Performance Comparison */}
        {Object.keys(displayResults.performance_summary).length > 0 && (
          <PerformanceComparison performance={displayResults.performance_summary} />
        )}

        {/* LLM Analyses */}
        <Text size="xl" fw={600} mt="lg">
          🤖 LLM Analysis Results
        </Text>

        <SimpleGrid cols={{ base: 1, md: 2, lg: models.length > 2 ? 3 : 2 }}>
          {models.map((modelName) => {
            // 🔧 FIX: Use frozen analysis if model is frozen, otherwise use live analysis
            const isFrozen = frozenModels.has(modelName);
            const analysis = isFrozen && frozenAnalyses[modelName]
              ? frozenAnalyses[modelName]
              : displayResults.llm_analyses[modelName];

            return (
              <ModelCard
                key={modelName}
                modelName={modelName}
                analysis={analysis}
                performance={displayResults.performance_summary[modelName]}
                onFreeze={handleFreeze}
                onUnfreeze={handleUnfreeze}
                isFrozen={isFrozen}
              />
            );
          })}
        </SimpleGrid>
      </Stack>
    </ScrollArea>
  );
}
