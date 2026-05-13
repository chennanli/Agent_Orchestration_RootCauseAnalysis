/**
 * Global test setup.
 *
 * - Adds RTL's custom matchers (`toBeInTheDocument`, `toHaveTextContent`,
 *   etc.) to vitest's `expect`.
 * - Stubs `window.matchMedia` because Mantine reads it on first render and
 *   jsdom doesn't ship a real implementation.
 * - Stubs `EventSource` so components that open SSE streams in
 *   useEffect (useAgentStream) don't blow up under jsdom.
 */
import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Mantine queries the media query for dark/light mode on mount.
// Use a plain function (not vi.fn) so vi.restoreAllMocks() in test
// beforeEach hooks can't reset it — the stub must survive across tests.
function stubMatchMedia(query: string) {
  return {
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  };
}
Object.defineProperty(window, "matchMedia", {
  writable: true,
  configurable: true,
  value: stubMatchMedia,
});

// Minimal EventSource stub so useAgentStream's `new EventSource(...)` doesn't
// throw `ReferenceError: EventSource is not defined` in jsdom.
class FakeEventSource {
  url: string;
  readyState = 0;
  CONNECTING = 0;
  OPEN = 1;
  CLOSED = 2;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  onopen: ((e: Event) => void) | null = null;
  constructor(url: string) {
    this.url = url;
  }
  addEventListener() {}
  removeEventListener() {}
  close() {
    this.readyState = this.CLOSED;
  }
}
// @ts-expect-error — we're deliberately replacing the global
globalThis.EventSource = FakeEventSource;
