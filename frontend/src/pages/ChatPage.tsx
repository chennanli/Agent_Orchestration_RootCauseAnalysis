import { Container, Title, Text, Stack, Paper, List, Divider, Image, Box } from "@mantine/core";

/**
 * Process Description Page - Static TEP Process Information with P&ID Diagram
 *
 * This page displays:
 * 1. TEP Process P&ID diagram (from backend)
 * 2. Static process description
 *
 * NO chat functionality, NO LLM analysis
 * For interactive analysis, use Interactive RCA or Multi-LLM Analysis pages
 */
export default function QuestionsPage() {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

  return (
    <Container size="xl" py="md">
      <Stack gap="lg">
        {/* Header */}
        <div>
          <Title order={1} mb="xs">Tennessee Eastman Process (TEP)</Title>
          <Text size="lg" c="dimmed">
            Industrial Chemical Process Simulation for Fault Diagnosis Research
          </Text>
        </div>

        <Divider />

        {/* P&ID Diagram */}
        <Paper shadow="sm" p="xl" radius="md" withBorder>
          <Title order={2} mb="md">Process Flow Diagram (P&ID)</Title>
          <Box style={{ textAlign: 'center', backgroundColor: '#f8f9fa', padding: '20px', borderRadius: '8px' }}>
            <Image
              src="/images/tep_flowsheet.png"
              alt="Tennessee Eastman Process P&ID"
              fit="contain"
              style={{ maxWidth: '100%', height: 'auto' }}
              fallbackSrc="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='400'%3E%3Crect width='800' height='400' fill='%23f0f0f0'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' fill='%23666' font-size='16'%3EProcess Diagram%3C/text%3E%3C/svg%3E"
            />
            <Text size="sm" c="dimmed" mt="md">
              Tennessee Eastman Process - Complete P&ID Diagram
            </Text>
          </Box>
        </Paper>

        {/* Process Overview */}
        <Paper shadow="sm" p="xl" radius="md" withBorder>
          <Title order={2} mb="md">Process Overview</Title>
          <Text mb="md">
            The process produces two products from four reactants. Also present are an inert and a byproduct making a total of eight components: A, B, C, D, E, F, G, and H. The reactions are:
          </Text>
          <List spacing="sm" mb="md">
            <List.Item>A(g) + C(g) + D(g) → G(liq): Product 1</List.Item>
            <List.Item>A(g) + C(g) + E(g) → H(liq): Product 2</List.Item>
            <List.Item>A(g) + E(g) → F(liq): Byproduct</List.Item>
            <List.Item>3D(g) → 2F(liq): Byproduct</List.Item>
          </List>
          <Text mb="md">
            All the reactions are irreversible and exothermic. The reaction rates are a function of temperature through an Arrhenius expression. The reaction to produce G has a higher activation energy resulting in more sensitivity to temperature. Also, the reactions are approximately first-order with respect to the reactant concentrations.
          </Text>
        </Paper>

        {/* Process Units */}
        <Paper shadow="sm" p="xl" radius="md" withBorder>
          <Title order={2} mb="md">Major Process Units</Title>
          <Text mb="md">
            The process has five major unit operations: the reactor, the product condenser, a vapor-liquid separator, a recycle compressor and a product stripper.
          </Text>
          <List spacing="sm">
            <List.Item>
              <Text fw={600}>Reactor:</Text> The gaseous reactants are fed to the reactor where they react to form liquid products. The gas phase reactions are catalyzed by a nonvolatile catalyst dissolved in the liquid phase. The reactor has an internal cooling bundle for removing the heat of reaction. The products leave the reactor as vapors along with the catalyst remains in the reactor.
            </List.Item>
            <List.Item>
              <Text fw={600}>Product Condenser:</Text> The reactor product stream passes through a cooler for condensing the products and from there to a vapor-liquid separator.
            </List.Item>
            <List.Item>
              <Text fw={600}>Vapor-Liquid Separator:</Text> Noncondensed components recycle back through a centrifugal compressor to the reactor feed. Condensed components move to a product stripping column to remove remaining reactants by stripping with feed stream number 4.
            </List.Item>
            <List.Item>
              <Text fw={600}>Product Stripper:</Text> Products G and H exit the stripper base and are separated in a downstream refining section which is not included in this problem. The inert and byproduct are primarily purged from the system as a vapor from the vapor-liquid separator.
            </List.Item>
          </List>
        </Paper>

        {/* Process Variables */}
        <Paper shadow="sm" p="xl" radius="md" withBorder>
          <Title order={2} mb="md">Process Variables</Title>

          <Title order={3} size="h4" mb="sm">Measurement Variables (XMEAS)</Title>
          <Text size="sm" c="dimmed" mb="md">
            52 process measurements including flows, temperatures, pressures, levels, and compositions
          </Text>
          <List spacing="xs" size="sm" mb="lg">
            <List.Item>XMEAS_1 to XMEAS_22: Primary process measurements</List.Item>
            <List.Item>XMEAS_23 to XMEAS_41: Component compositions</List.Item>
            <List.Item>XMEAS_42 to XMEAS_52: Additional process parameters</List.Item>
          </List>

          <Title order={3} size="h4" mb="sm">Manipulated Variables (XMV)</Title>
          <Text size="sm" c="dimmed" mb="md">
            12 control inputs for process operation
          </Text>
          <List spacing="xs" size="sm" mb="lg">
            <List.Item>XMV_1 to XMV_4: Feed flow rates (D, E, A, A+C)</List.Item>
            <List.Item>XMV_5 to XMV_6: Compressor recycle valve, Purge valve</List.Item>
            <List.Item>XMV_7 to XMV_8: Separator and Stripper liquid product flow</List.Item>
            <List.Item>XMV_9: Stripper steam valve</List.Item>
            <List.Item>XMV_10 to XMV_11: Reactor and Condenser cooling water flow</List.Item>
            <List.Item>XMV_12: Agitator speed</List.Item>
          </List>

          <Title order={3} size="h4" mb="sm">Disturbance Variables (IDV)</Title>
          <Text size="sm" c="dimmed" mb="md">
            20 fault types for testing fault diagnosis algorithms
          </Text>
          <List spacing="xs" size="sm">
            <List.Item>IDV_1 to IDV_8: Feed composition and temperature changes</List.Item>
            <List.Item>IDV_9 to IDV_12: Temperature variations</List.Item>
            <List.Item>IDV_13 to IDV_15: Kinetics and composition drifts</List.Item>
            <List.Item>IDV_16 to IDV_20: Valve and sensor faults</List.Item>
          </List>
        </Paper>

        {/* Control Strategy */}
        <Paper shadow="sm" p="xl" radius="md" withBorder>
          <Title order={2} mb="md">Control Strategy</Title>
          <Text mb="md">
            The process uses a decentralized control strategy with multiple PID controllers:
          </Text>
          <List spacing="sm">
            <List.Item>Production rate control via A feed (Stream 1)</List.Item>
            <List.Item>Product quality control via D and E feed ratio</List.Item>
            <List.Item>Reactor pressure control via purge valve</List.Item>
            <List.Item>Reactor level control via product draw</List.Item>
            <List.Item>Reactor temperature control via cooling water</List.Item>
            <List.Item>Separator level control via underflow</List.Item>
            <List.Item>Stripper level control via base product flow</List.Item>
          </List>
        </Paper>

        {/* Research Applications */}
        <Paper shadow="sm" p="xl" radius="md" withBorder>
          <Title order={2} mb="md">Research Applications</Title>
          <Text mb="md">
            The Tennessee Eastman Process is widely used in process control and fault diagnosis research for:
          </Text>
          <List spacing="sm">
            <List.Item>Testing fault detection and diagnosis algorithms</List.Item>
            <List.Item>Evaluating process monitoring techniques</List.Item>
            <List.Item>Benchmarking machine learning models for industrial processes</List.Item>
            <List.Item>Training operators on complex process dynamics</List.Item>
            <List.Item>Developing advanced process control strategies</List.Item>
          </List>
        </Paper>
      </Stack>
    </Container>
  );
}
