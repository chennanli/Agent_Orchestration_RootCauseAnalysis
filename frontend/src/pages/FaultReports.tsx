import { useStatState, useConversationState } from "../App";
import {
  ScrollArea,
  Text,
  Accordion,
  Space,
  Card,
  Image,
  SimpleGrid,
} from "@mantine/core";
import { marked } from "marked";
import { AreaChart } from "@mantine/charts";

export default function HistoryPage() {
  const conversation = useConversationState().conversation;
  const t2_stat = useStatState();

  // Debug: Log data updates
  console.log(`[T2 Chart] Data points: ${t2_stat.length}, Latest:`, t2_stat.slice(-3));

  const transformedData = t2_stat.map((item) => {
    // Cap T² values at 100 for display, but keep original for tooltip
    const cappedT2 = Math.min(item.t2_stat, 100);

    // Fixed: Show normal data when no anomaly, anomaly data when anomaly detected
    const normalData = item.anomaly ? 0 : cappedT2;
    const anomalyData = item.anomaly ? cappedT2 : 0;

    // 🔧 FIX: Use cumulative time from data instead of array index
    const cumulativeInt = Math.round(item.cumulativeTime || 0); // Round to integer
    const simulationMinutes = cumulativeInt * 3;
    const hours = Math.floor(simulationMinutes / 60);
    const minutes = simulationMinutes % 60;
    const timeLabel = hours > 0 ? `${hours}h${minutes.toString().padStart(2, '0')}m` : `${minutes}m`;

    return {
      ...item,
      time: timeLabel,          // Real simulation time based on cumulative data points
      t2_stat: parseFloat(normalData.toFixed(1)),      // 🔧 FIX: Round to 1 decimal - Green area (normal)
      anomaly: parseFloat(anomalyData.toFixed(1)),     // 🔧 FIX: Round to 1 decimal - Red area (anomaly)
      original_t2: parseFloat(item.t2_stat.toFixed(1)), // 🔧 FIX: Round original value
      simulation_minutes: simulationMinutes, // For tooltip
    };
  });
  return (
    <ScrollArea h={`calc(100vh - 60px - 32px)`}>
      <Text
        size="xl"
        ta="center"
      >
        Anomaly Score
      </Text>

      <AreaChart
        h={300}
        data={transformedData}
        dataKey="time"
        yAxisProps={{
          domain: [0, 100],
          tickFormatter: (value: number) => value.toFixed(1) // 🔧 FIX: Round Y-axis to 1 decimal
        }}
        yAxisLabel="Anomaly Score (0-100 scale)"
        xAxisLabel="Time (each step = 3 min in reality)"
        xAxisProps={{
          height: 80
        }}
        series={[
          { name: "t2_stat", label: "Normal", color: "green.2" },
          { name: "anomaly", label: "Anomaly", color: "red.4" },
        ]}
        curveType="linear"
        tickLine="x"
        withDots={false}
        withGradient={false}
        fillOpacity={0.8}
        strokeWidth={1}
        withYAxis={true}
        withXAxis={true}
        withTooltip={true}
        tooltipProps={{
          content: ({ label, payload }) => {
            if (!payload || payload.length === 0) return null;
            const data = payload[0]?.payload;
            return (
              <div style={{
                background: 'white',
                border: '1px solid #ccc',
                borderRadius: '4px',
                padding: '8px',
                fontSize: '12px'
              }}>
                <div><strong>Simulation Time:</strong> {label}</div>
                <div><strong>Total Minutes:</strong> {data?.simulation_minutes || 'N/A'}</div>
                <div><strong>T² Value:</strong> {data?.original_t2?.toFixed(2) || 'N/A'}</div>
                <div><strong>Status:</strong> {data?.anomaly > 0 ? 'Anomaly' : 'Normal'}</div>
                {data?.original_t2 > 100 && (
                  <div style={{ color: 'red', fontWeight: 'bold' }}>
                    ⚠️ Value exceeds scale (&gt;100)
                  </div>
                )}
              </div>
            );
          }
        }}
        referenceLines={[
          { y: 55, label: "Anomaly Threshold (55)", color: "red.6" }
        ]}
      />

      <Space h="xl" />
      {/* Fault History Accordion - Hidden to reduce clutter */}
      {/*
      <Accordion variant="separated">
        {conversation.map(
          (msg) =>
            msg.explanation && (
              <Accordion.Item key={msg.id} value={`Fault ${msg.id}`}>
                <Accordion.Control>{msg.id}</Accordion.Control>
                <Accordion.Panel>
                  <Card shadow="sm" padding="lg" radius="md" withBorder>
                    {msg.images && (
                      <Card.Section>
                        <SimpleGrid cols={Math.min(msg.images.length, 3)}>
                          {(() => {
                            return msg.images.map((img, idx) => (
                              <Image
                                key={idx}
                                src={`data:image/png;base64,${img.image}`}
                                alt={`Graph for ${img.name}`}
                                radius="md"
                              />
                            ));
                          })()}
                        </SimpleGrid>
                      </Card.Section>
                    )}
                    {msg.text && (
                      <div
                        dangerouslySetInnerHTML={{
                          __html: marked.parse(msg.text),
                        }}
                      />
                    )}
                  </Card>
                </Accordion.Panel>
              </Accordion.Item>
            )
        )}
      </Accordion>
      */}
    </ScrollArea>
  );
}
