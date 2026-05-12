import {
  AppShell,
  Burger,
  Group,
  NavLink,
  Text,
  Title,
  Badge,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconLayoutDashboard,
  IconBook2,
  IconBolt,
  IconBriefcase,
  IconClipboardCheck,
} from "@tabler/icons-react";
import { Outlet, NavLink as RouterNavLink, useLocation } from "react-router-dom";

// Public navigation. Intentionally short: Live Copilot is the main story.
// /overview, /live, /agent are kept as routes (for backward compatibility
// and shareable URLs) but no longer surfaced in the sidebar — they were
// confusing visitors who thought "Agent Run" was a separate place to
// diagnose, when in fact Live Copilot is the only path they need.
const NAV = [
  { to: "/", label: "Live Copilot", icon: IconBolt, end: true },
  { to: "/wiki", label: "LLM Wiki", icon: IconBook2 },
  { to: "/eval", label: "Evaluation", icon: IconClipboardCheck },
  // Misc tab bundles utilities lifted out of the old demo: per-run
  // export-as-Markdown, share-by-email, operator notes scratchpad, KB
  // upload. Kept off the canvas to avoid distracting from the diagnosis
  // flow, but reachable in one click.
  { to: "/misc", label: "Misc", icon: IconBriefcase },
  // /overview, /live, /agent are intentionally NOT in the sidebar — they're
  // older entry points that confuse first-time visitors. Routes still
  // resolve by URL for engineers / link-sharing.
];

/**
 * The public-facing shell for the TEP Agentic RCA Workbench. Restrained
 * navigation, no marketing decoration, no per-LLM checkboxes in the header.
 * Legacy debug pages are still mounted under /legacy/* by main.tsx for
 * behind-the-scenes use, but they do not appear in this navigation.
 */
export default function PublicApp() {
  const [opened, { toggle }] = useDisclosure();
  const location = useLocation();
  const onLegacy = location.pathname.startsWith("/legacy");

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 220, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="md">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Title order={5} style={{ letterSpacing: "0.02em" }}>
              ⚡ TEP Live Copilot
            </Title>
            <Text size="xs" c="dimmed" visibleFrom="md">
              live Fortran simulation · NAT agentic RCA · industrial advisory
            </Text>
            {onLegacy && (
              <Badge variant="light" color="orange">
                legacy debug view
              </Badge>
            )}
          </Group>
          <Text size="xs" c="dimmed">
            advisory only · human review required
          </Text>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="sm">
        {NAV.map((n) => (
          <RouterNavLink
            key={n.to}
            to={n.to}
            end={n.end}
            style={{ textDecoration: "none" }}
          >
            {({ isActive }) => (
              <NavLink
                active={isActive}
                label={n.label}
                leftSection={<n.icon size={16} />}
                variant="light"
              />
            )}
          </RouterNavLink>
        ))}
        <NavLink
          label="Legacy debug pages"
          leftSection={<IconLayoutDashboard size={16} />}
          variant="subtle"
          mt="md"
          childrenOffset={20}
        >
          <RouterNavLink to="/legacy/plot" style={{ textDecoration: "none" }}>
            {({ isActive }) => (
              <NavLink active={isActive} label="Old DCS / plot" />
            )}
          </RouterNavLink>
          <RouterNavLink to="/legacy/comparative" style={{ textDecoration: "none" }}>
            {({ isActive }) => (
              <NavLink active={isActive} label="Old multi-LLM" />
            )}
          </RouterNavLink>
          <RouterNavLink to="/legacy/assistant" style={{ textDecoration: "none" }}>
            {({ isActive }) => (
              <NavLink active={isActive} label="Old assistant" />
            )}
          </RouterNavLink>
        </NavLink>
      </AppShell.Navbar>
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
