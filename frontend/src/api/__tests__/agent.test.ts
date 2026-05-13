/**
 * API client smoke tests.
 *
 * We don't care that fetch *works* (the browser does that). We care that
 * the request body and URL the API client sends are what the backend
 * expects — every time we touch agent.ts there's a chance a key gets
 * renamed and silently breaks the contract.
 *
 * Strategy: stub `globalThis.fetch`, capture the args, assert on them.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  diagnoseFault,
  diagnoseLive,
  followup,
  bakeoff,
  exportRunMarkdownUrl,
  emailRun,
} from "../agent";

function mockFetch(jsonBody: unknown, status = 200) {
  const fn = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(""),
    json: () => Promise.resolve(jsonBody),
  });
  // @ts-expect-error — we're deliberately replacing the global
  globalThis.fetch = fn;
  return fn;
}

describe("agent API client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("diagnoseFault posts the fault_id, question, model_id, api_key", async () => {
    const fetchSpy = mockFetch({
      run_id: "run_x",
      fault_id: "fault1",
      started_at: "now",
    });
    await diagnoseFault("fault1", { model_id: "nim-llama-3.3-70b", api_key: "k" });
    expect(fetchSpy).toHaveBeenCalledOnce();
    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe("/api/agent/diagnose");
    expect(init.method).toBe("POST");
    const body = JSON.parse(init.body as string);
    expect(body).toMatchObject({
      fault_id: "fault1",
      model_id: "nim-llama-3.3-70b",
      api_key: "k",
    });
    expect(body.question).toMatch(/Diagnose/);
  });

  it("diagnoseLive uses points (not fault_id) and defaults to 200", async () => {
    const fetchSpy = mockFetch({ run_id: "r", fault_id: "live_x", started_at: "now" });
    await diagnoseLive(undefined as unknown as number, {});
    const body = JSON.parse(fetchSpy.mock.calls[0][1].body as string);
    expect(body.points).toBe(200);
    expect(body.fault_id).toBeUndefined();
  });

  it("followup forwards model_id and api_key in the body", async () => {
    const fetchSpy = mockFetch({ q: "?", a: "!", ts: "now" });
    await followup("run_abc", "why?", { model_id: "gemini-2.5-pro", api_key: "k2" });
    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe("/api/agent/runs/run_abc/followup");
    const body = JSON.parse(init.body as string);
    expect(body).toEqual({
      question: "why?",
      model_id: "gemini-2.5-pro",
      api_key: "k2",
    });
  });

  it("followup sends nulls (not undefined) when opts is missing", async () => {
    const fetchSpy = mockFetch({ q: "?", a: "!", ts: "now" });
    await followup("run_abc", "why?");
    const body = JSON.parse(fetchSpy.mock.calls[0][1].body as string);
    // Backend's Pydantic schema accepts None — we must not send `undefined`,
    // because JSON.stringify drops it and the field becomes missing, which
    // is a different validation path.
    expect(body.model_id).toBeNull();
    expect(body.api_key).toBeNull();
  });

  it("bakeoff hits the right URL with body", async () => {
    const fetchSpy = mockFetch({ naive: {}, agent: {} });
    await bakeoff("run_X", { model_id: "nim-llama-3.3-70b" });
    expect(fetchSpy.mock.calls[0][0]).toBe("/api/agent/runs/run_X/bakeoff");
    const body = JSON.parse(fetchSpy.mock.calls[0][1].body as string);
    expect(body.model_id).toBe("nim-llama-3.3-70b");
  });

  it("exportRunMarkdownUrl returns a stable URL pattern", () => {
    expect(exportRunMarkdownUrl("run_abc-123")).toBe(
      "/api/misc/runs/run_abc-123/markdown",
    );
  });

  it("emailRun posts recipient + subject", async () => {
    const fetchSpy = mockFetch({ sent: true });
    await emailRun("r", "ops@example.com", "Re: anomaly");
    const body = JSON.parse(fetchSpy.mock.calls[0][1].body as string);
    expect(body.recipient).toBe("ops@example.com");
    expect(body.subject).toBe("Re: anomaly");
  });
});
