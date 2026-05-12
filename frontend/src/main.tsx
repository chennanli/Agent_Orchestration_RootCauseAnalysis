import ReactDOM from "react-dom/client";
import { MantineProvider } from "@mantine/core";
import App, { useComparativeResults } from "./App.tsx";
import PublicApp from "./PublicApp.tsx";
import OperationsDashboardPage from "./pages/OperationsDashboardPage.tsx";
import LiveProcessPage from "./pages/LiveProcessPage.tsx";
import LiveCopilotPage from "./pages/LiveCopilotPage.tsx";
import AgentRunPage from "./pages/AgentRunPage.tsx";
import LLMWikiPage from "./pages/LLMWikiPage.tsx";
import EvaluationPage from "./pages/EvaluationPage.tsx";
import MiscPage from "./pages/MiscPage.tsx";
import QuestionsPage from "./pages/ChatPage.tsx";
import HistoryPage from "./pages/FaultReports.tsx";
import DataPage from "./pages/PlotPage.tsx";
import ComparativeLLMResults from "./pages/ComparativeLLMResults.tsx";
import AssistantPage from "./pages/AssistantPage.tsx";
import ErrorPage from "./error-page.tsx";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import "@mantine/core/styles.css";
import "@mantine/charts/styles.css";

// Wrapper component to pass context data to ComparativeLLMResults
function ComparativeResultsWrapper() {
  const { results, isAnalyzing } = useComparativeResults();
  return <ComparativeLLMResults results={results} isLoading={isAnalyzing} />;
}

const router = createBrowserRouter([
  // New public shell (default).
  {
    path: "/",
    element: <PublicApp />,
    errorElement: <ErrorPage />,
    children: [
      // The new TEP Live Copilot is the default landing page.
      { index: true, element: <LiveCopilotPage /> },
      { path: "overview", element: <OperationsDashboardPage /> },
      { path: "live", element: <LiveProcessPage /> },
      { path: "agent", element: <AgentRunPage /> },
      { path: "wiki", element: <LLMWikiPage /> },
      { path: "eval", element: <EvaluationPage /> },
      { path: "misc", element: <MiscPage /> },
    ],
  },
  // Legacy debug shell, kept for behind-the-scenes access. The original
  // multi-LLM RCA + assistant pages still work here unchanged.
  {
    path: "/legacy",
    element: <App />,
    errorElement: <ErrorPage />,
    children: [
      { path: "plot", element: <DataPage /> },
      { index: true, element: <QuestionsPage /> },
      { path: "history", element: <HistoryPage /> },
      { path: "comparative", element: <ComparativeResultsWrapper /> },
      { path: "assistant", element: <AssistantPage /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <MantineProvider
    defaultColorScheme="dark"
    theme={{
      primaryColor: "violet",
      defaultRadius: "md",
      fontFamilyMonospace:
        "ui-monospace, SFMono-Regular, Menlo, 'JetBrains Mono', monospace",
    }}
  >
    <RouterProvider router={router} />
  </MantineProvider>
);
