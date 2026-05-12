import { useState, useEffect } from 'react';
import { useDataPoints } from '../App';
import {
  Container,
  Title,
  Tabs,
  Card,
  Text,
  Grid,
  Badge,
  Group,
  Stack,
  Box,
  Button,
  NumberInput,
  ActionIcon,
  Notification,
} from '@mantine/core';
import {
  IconChartLine,
  IconPlayerPlay,
  IconPlayerStop,
  IconRefresh,
  IconAlertCircle,
} from '@tabler/icons-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface DisturbanceData {
  time: number;
  setpoint: number;
  control: number;
  measurement: number;
}

interface DisturbanceTest {
  id: string;
  name: string;
  description: string;
  setpoint_var: string;
  control_var: string;
  measurement_var: string;
  original_value: number;
  test_value: number;
  unit: string;
  status: 'idle' | 'running' | 'completed';
}

const DISTURBANCE_TESTS: DisturbanceTest[] = [
  {
    id: 'level1-1',
    name: 'Reactor Cooling',
    description: 'Reactor Cooling Water Temperature Setpoint SETPT_10',
    setpoint_var: 'SETPT_10',
    control_var: 'XMV_10',
    measurement_var: 'XMEAS_9',
    original_value: 94.6,
    test_value: 100.0,
    unit: '°C',
    status: 'idle',
  },
  {
    id: 'level1-2',
    name: 'Stripper Level',
    description: 'Stripper Level Control SETPT_8',
    setpoint_var: 'SETPT_8',
    control_var: 'XMV_8',
    measurement_var: 'XMEAS_13',
    original_value: 50.0,
    test_value: 60.0,
    unit: '%',
    status: 'idle',
  },
  {
    id: 'level1-3',
    name: 'Product Separator',
    description: 'Product Separator Level SETPT_7',
    setpoint_var: 'SETPT_7',
    control_var: 'XMV_7',
    measurement_var: 'XMEAS_12',
    original_value: 50.0,
    test_value: 60.0,
    unit: '%',
    status: 'idle',
  },
];

export default function DisturbanceEffectsPage() {
  const [activeTab, setActiveTab] = useState<string>('level1-1');
  const [disturbanceData, setDisturbanceData] = useState<Record<string, DisturbanceData[]>>({});
  const [currentSetpoints, setCurrentSetpoints] = useState<Record<string, number>>({});
  const [baselineSetpoints, setBaselineSetpoints] = useState<Record<string, number>>({});
  const [isCollectingData, setIsCollectingData] = useState<boolean>(false);

  // Get live data from the same source as Monitoring page
  const fullDataPoints = useDataPoints();

  // Initialize baseline setpoints
  useEffect(() => {
    const baseline: Record<string, number> = {};
    DISTURBANCE_TESTS.forEach(test => {
      baseline[test.id] = test.original_value;
    });
    setBaselineSetpoints(baseline);
    setCurrentSetpoints(baseline);
  }, []);

  // Auto-detect setpoint changes using live data from useDataPoints
  useEffect(() => {
    if (!fullDataPoints || Object.keys(fullDataPoints).length === 0) return;

    // Check each test for setpoint changes
    DISTURBANCE_TESTS.forEach(test => {
      const setpointData = fullDataPoints[test.setpoint_var];
      if (setpointData && setpointData.length > 0) {
        const currentValue = setpointData[setpointData.length - 1]; // Get latest value
        const baselineValue = baselineSetpoints[test.id];

        // Update current setpoint
        setCurrentSetpoints(prev => ({ ...prev, [test.id]: currentValue }));

        // Check if setpoint changed significantly from baseline
        const threshold = test.unit === '°C' ? 0.5 : 2.0;
        const isDisturbance = Math.abs(currentValue - baselineValue) > threshold;

        if (isDisturbance && !isCollectingData) {
          console.log(`🎯 Disturbance detected for ${test.name}: ${baselineValue}${test.unit} → ${currentValue}${test.unit}`);
          setIsCollectingData(true);
        }
      }
    });
  }, [fullDataPoints, baselineSetpoints, isCollectingData]);

  // Generate chart data using live data from useDataPoints (ALWAYS show data)
  useEffect(() => {
    if (!fullDataPoints || Object.keys(fullDataPoints).length === 0) return;

    // Generate data for all tests using ALL available data points
    DISTURBANCE_TESTS.forEach(test => {
      const setpointData = fullDataPoints[test.setpoint_var];
      const controlData = fullDataPoints[test.control_var];
      const measurementData = fullDataPoints[test.measurement_var];
      const timeData = fullDataPoints.time;

      if (setpointData && controlData && measurementData && timeData &&
          setpointData.length > 0 && controlData.length > 0 && measurementData.length > 0) {

        // Create chart data from ALL available points (not just latest)
        const chartData: DisturbanceData[] = [];
        const dataLength = Math.min(setpointData.length, controlData.length, measurementData.length, timeData.length);

        for (let i = 0; i < dataLength; i++) {
          chartData.push({
            time: timeData[i] || i,
            setpoint: setpointData[i],
            control: controlData[i],
            measurement: measurementData[i]
          });
        }

        // Update the disturbance data with the complete chart data
        setDisturbanceData(prev => ({
          ...prev,
          [test.id]: chartData.slice(-100) // Keep last 100 points
        }));
      }
    });
  }, [fullDataPoints]); // Remove isCollectingData dependency to always show data

  const renderDisturbanceTest = (test: DisturbanceTest) => {
    const data = disturbanceData[test.id] || [];
    const currentValue = currentSetpoints[test.id] || test.original_value;
    const baselineValue = baselineSetpoints[test.id] || test.original_value;
    const isDisturbance = Math.abs(currentValue - baselineValue) > (test.unit === '°C' ? 0.5 : 2.0);

    return (
      <Container size="xl">
        <Stack gap="md">
          {/* Status Header */}
          <Card shadow="sm" padding="md" radius="md" withBorder>
            <Group justify="space-between">
              <div>
                <Title order={3}>{test.name}</Title>
                <Text size="sm" c="dimmed">{test.description}</Text>
              </div>
              <Group gap="md">
                <div>
                  <Text size="xs" c="dimmed">Baseline: {baselineValue}{test.unit}</Text>
                  <Text size="sm" fw={500}>Current: {currentValue}{test.unit}</Text>
                </div>
                <Badge
                  color={isDisturbance ? 'orange' : 'green'}
                  variant="filled"
                >
                  {isDisturbance ? 'Disturbance Active' : 'Normal Operation'}
                </Badge>
                <ActionIcon
                  variant="outline"
                  onClick={() => setDisturbanceData(prev => ({ ...prev, [test.id]: [] }))}
                  title="Clear Chart Data"
                >
                  <IconRefresh size={16} />
                </ActionIcon>
              </Group>
            </Group>
          </Card>

          {/* Three Plots */}
          <Grid>
            <Grid.Col span={12}>
              <Card shadow="sm" padding="lg" radius="md" withBorder>
                <Title order={4} mb="md">
                  Plot 1: {test.setpoint_var} Setpoint
                  <Text span size="sm" c="dimmed" ml="sm">
                    (original {baselineValue}, now {currentValue}), change with time
                  </Text>
                </Title>
                <Box h={200}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" label={{ value: 'Time (s)', position: 'insideBottom', offset: -5 }} />
                      <YAxis label={{ value: test.unit, angle: -90, position: 'insideLeft' }} />
                      <Tooltip />
                      <Line type="monotone" dataKey="setpoint" stroke="#2196F3" strokeWidth={2} name="Setpoint" />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </Card>
            </Grid.Col>

            <Grid.Col span={12}>
              <Card shadow="sm" padding="lg" radius="md" withBorder>
                <Title order={4} mb="md">Plot 2: Controls: {test.control_var} ({test.name})</Title>
                <Box h={200}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" label={{ value: 'Time (s)', position: 'insideBottom', offset: -5 }} />
                      <YAxis label={{ value: '%', angle: -90, position: 'insideLeft' }} />
                      <Tooltip />
                      <Line type="monotone" dataKey="control" stroke="#4CAF50" strokeWidth={2} name="Control Action" />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </Card>
            </Grid.Col>

            <Grid.Col span={12}>
              <Card shadow="sm" padding="lg" radius="md" withBorder>
                <Title order={4} mb="md">Plot 3: Affects: {test.measurement_var}</Title>
                <Box h={200}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" label={{ value: 'Time (s)', position: 'insideBottom', offset: -5 }} />
                      <YAxis label={{ value: test.unit, angle: -90, position: 'insideLeft' }} />
                      <Tooltip />
                      <Line type="monotone" dataKey="measurement" stroke="#FF9800" strokeWidth={2} name="Process Variable" />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </Card>
            </Grid.Col>
          </Grid>
        </Stack>
      </Container>
    );
  };

  return (
    <Container size="xl" py="md">
      <Group justify="space-between" mb="lg">
        <Title order={2}>
          <IconChartLine size={28} style={{ marginRight: 8 }} />
          Disturbance Effects
        </Title>
        <Group gap="sm">
          <Badge color={isCollectingData ? 'green' : 'gray'} variant="filled">
            {isCollectingData ? 'Collecting Data' : 'Monitoring'}
          </Badge>
          <Text size="sm" c="dimmed">
            Auto-detects setpoint changes from Control Panel
          </Text>
        </Group>
      </Group>

      <Tabs value={activeTab} onChange={(value) => setActiveTab(value || 'level1-1')}>
        <Tabs.List>
          <Tabs.Tab value="level1-1">Level 1 -1</Tabs.Tab>
          <Tabs.Tab value="level1-2">Level 1 -2</Tabs.Tab>
          <Tabs.Tab value="level1-3">Level 1 -3</Tabs.Tab>
          <Tabs.Tab value="manual1-1" disabled>Manual 1 -1</Tabs.Tab>
        </Tabs.List>

        {DISTURBANCE_TESTS.map(test => (
          <Tabs.Panel key={test.id} value={test.id} pt="md">
            {renderDisturbanceTest(test)}
          </Tabs.Panel>
        ))}
      </Tabs>
    </Container>
  );
}
