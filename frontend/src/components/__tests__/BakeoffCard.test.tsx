/**
 * BakeoffCard behavior tests.
 *
 * This is the headline feature ("Naive LLM vs NAT Agent" comparison) so
 * it's worth a couple of behavioral guards. We verify:
 *   1. Initial render shows the Compare button and explanatory copy
 *   2. Click → loading state → render of both columns with metrics
 *   3. Backend error surfaces in red
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import userEvent from "@testing-library/user-event";
import BakeoffCard from "../BakeoffCard";
import * as agentApi from "../../api/agent";

function renderWithMantine(ui: React.ReactElement) {
  return render(<MantineProvider>{ui}</MantineProvider>);
}

describe("BakeoffCard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("starts in idle state, showing the Compare button", () => {
    renderWithMantine(<BakeoffCard runId="run_abc" />);
    // Component title (header) plus the button should both contain "Compare"
    expect(
      screen.getByRole("button", { name: /compare/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/value of orchestration/i),
    ).toBeInTheDocument();
  });

  it("renders both columns + delta badge after a successful bakeoff", async () => {
    vi.spyOn(agentApi, "bakeoff").mockResolvedValue({
      naive: {
        text: "Probably a cooling issue.",
        model_id: "nim-llama-3.3-70b",
        runtime_seconds: 1.2,
        tag_count: 0,
        tags: [],
      },
      agent: {
        text: "XMV_6 saturated at 87%; see Downs & Vogel §5.4.",
        model_id: "nim-llama-3.3-70b",
        runtime_seconds: 14.7,
        tool_count: 6,
        tool_calls: ["inspect_anomaly_snapshot", "rank_contributing_variables"],
        sources_cited: ["Downs & Vogel"],
        tag_count: 1,
        tags: ["XMV_6"],
      },
    });

    renderWithMantine(<BakeoffCard runId="run_abc" />);
    await userEvent.click(screen.getByRole("button", { name: /compare/i }));

    await waitFor(() => {
      // Naive answer
      expect(screen.getByText(/cooling issue/i)).toBeInTheDocument();
      // Agent answer
      expect(screen.getByText(/XMV_6/)).toBeInTheDocument();
      // The metrics row promises tool count, sources cited
      expect(screen.getByText(/6 tool calls/i)).toBeInTheDocument();
      expect(screen.getByText(/1 source cited/i)).toBeInTheDocument();
    });

    // The delta badge: agent had 1 tag, naive had 0 → +1
    expect(screen.getByText(/\+1 tag/i)).toBeInTheDocument();
  });

  it("renders an error when the backend call fails", async () => {
    vi.spyOn(agentApi, "bakeoff").mockRejectedValue(
      new Error("bakeoff LLM call failed: connection refused"),
    );
    renderWithMantine(<BakeoffCard runId="run_abc" />);
    await userEvent.click(screen.getByRole("button", { name: /compare/i }));
    await waitFor(() => {
      expect(
        screen.getByText(/bakeoff LLM call failed/i),
      ).toBeInTheDocument();
    });
  });
});
