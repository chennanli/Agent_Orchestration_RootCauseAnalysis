import React, { useState, useEffect, useRef, createContext, useContext } from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import Papa from "papaparse";
import {
  ActionIcon,
  AppShell,
  Box,
  Burger,
  Group,
  NavLink,
  Select,
  Slider,
  Text,
  Button,
  Switch,
  Badge,
  Tooltip,
  Progress,
  Checkbox,
  Divider,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import intro_image from "./assets/intro.json";
import {
  IconPlayerPauseFilled,
  IconPlayerPlayFilled,
  IconChartHistogram,
  IconRobot,
  IconReport,
  IconBrain,
  IconChartLine,
  IconMessageChatbot,
} from "@tabler/icons-react";
// import { fetchEventSource } from "@microsoft/fetch-event-source";

// CONSTANTS
const fileId2fileName = [
  "./fault0.csv",
  "./fault1.csv",
  "./fault2.csv",
  "./fault3.csv",
  "./fault4.csv",
  "./fault5.csv",
  "./fault6.csv",
  "./fault7.csv",
  "./fault8.csv",
  "./fault9.csv",
  "./fault10.csv",
  "./fault11.csv",
  "./fault12.csv",
  "./fault13.csv",
  "./fault14.csv",
  "./fault15.csv",
  "./fault16.csv",
  "./fault17.csv",
  "./fault18.csv",
  "./fault19.csv",
  "./fault20.csv",
];

const fault_name = [
  "Normal Operation",
  "Step change in A/C feed ratio, B composition constant (stream 4)",
  "Step change in B composition, A/C ratio constant (stream 4)",
  "Step change in D feed temperature (stream 2)",
  "Step change in Reactor cooling water inlet temperature",
  "Step change in Condenser cooling water inlet temperature",
  "Step change in A feed loss (stream 1)",
  "Step change in C header pressure loss-reduced availability (stream 4)",
  "Random variation in A, B, C feed composition (stream 4)",
  "Random variation in D feed temperature (stream 2)",
  "Random variation in C feed temperature (stream 4)",
  "Random variation in Reactor cooling water inlet temperature",
  "Random variation in Condenser cooling water inlet temperature",
  "Slow drift in Reaction kinetics",
  "Sticking Reactor cooling water valve",
  "Sticking Condenser cooling water valve",
  "Unknown (16)",
  "Unknown (17)",
  "Unknown (18)",
  "Unknown (19)",
  "Unknown (20)",
  // 'Constant position for the valve for stream 4',
];

// eslint-disable-next-line react-refresh/only-export-components
export const columnFilter: string[] = [
  // "time",
  "A Feed",
  "D Feed",
  "E Feed",
  "A and C Feed",
  "Recycle Flow",
  "Reactor Feed Rate",
  "Reactor Pressure",
  "Reactor Level",
  "Reactor Temperature",
  "Purge Rate",
  "Product Sep Temp",
  "Product Sep Level",
  "Product Sep Pressure",
  "Product Sep Underflow",
  "Stripper Level",
  "Stripper Pressure",
  "Stripper Underflow",
  "Stripper Temp",
  "Stripper Steam Flow",
  "Compressor Work",
  "Reactor Coolant Temp",
  "Separator Coolant Temp",
  "Component A to Reactor",
  "Component B to Reactor",
  "Component C to Reactor",
  "Component D to Reactor",
  "Component E to Reactor",
  "Component F to Reactor",
  "Component A in Purge",
  "Component B in Purge",
  "Component C in Purge",
  "Component D in Purge",
  "Component E in Purge",
  "Component F in Purge",
  "Component G in Purge",
  "Component H in Purge",
  "Component D in Product",
  "Component E in Product",
  "Component F in Product",
  "Component G in Product",
  "Component H in Product",
  "D feed load",
  "E feed load",
  "A feed load",
  "A and C feed load",
  "Compressor recycle valve",
  "Purge valve",
  "Separator liquid load",
  "Stripper liquid load",
  "Stripper steam valve",
  "Reactor coolant load",
  "Condenser coolant load",
];

// eslint-disable-next-line react-refresh/only-export-components
export const columnFilterUnits: Record<string, string> = {
  // time: "min",
  "A Feed": "kscmh",
  "D Feed": "kg/hr",
  "E Feed": "kg/hr",
  "A and C Feed": "kscmh",
  "Recycle Flow": "kscmh",
  "Reactor Feed Rate": "kscmh",
  "Reactor Pressure": "kPa gauge",
  "Reactor Level": "%",
  "Reactor Temperature": "Deg C",
  "Purge Rate": "kscmh",
  "Product Sep Temp": "Deg C",
  "Product Sep Level": "%",
  "Product Sep Pressure": "kPa gauge",
  "Product Sep Underflow": "m3/hr",
  "Stripper Level": "%",
  "Stripper Pressure": "kPa gauge",
  "Stripper Underflow": "m3/hr",
  "Stripper Temp": "Deg C",
  "Stripper Steam Flow": "kg/hr",
  "Compressor Work": "kW",
  "Reactor Coolant Temp": "Deg C",
  "Separator Coolant Temp": "Deg C",
  "Component A to Reactor": "mole %",
  "Component B to Reactor": "mole %",
  "Component C to Reactor": "mole %",
  "Component D to Reactor": "mole %",
  "Component E to Reactor": "mole %",
  "Component F to Reactor": "mole %",
  "Component A in Purge": "mole %",
  "Component B in Purge": "mole %",
  "Component C in Purge": "mole %",
  "Component D in Purge": "mole %",
  "Component E in Purge": "mole %",
  "Component F in Purge": "mole %",
  "Component G in Purge": "mole %",
  "Component H in Purge": "mole %",
  "Component D in Product": "mole %",
  "Component E in Product": "mole %",
  "Component F in Product": "mole %",
  "Component G in Product": "mole %",
  "Component H in Product": "mole %",
  "D feed load": "mole %",
  "E feed load": "mole %",
  "A feed load": "mole %",
  "A and C feed load": "mole %",
  "Compressor recycle valve": "mole %",
  "Purge valve": "mole %",
  "Separator liquid load": "mole %",
  "Stripper liquid load": "mole %",
  "Stripper steam valve": "mole %",
  "Reactor coolant load": "mole %",
  "Condenser coolant load": "mole %",
};

console.log("columnFilter: ", columnFilter);
console.log("columnFilterUnits: ", columnFilterUnits);

const importanceFilter: string[] = [
  "t2_A Feed",
  "t2_D Feed",
  "t2_E Feed",
  "t2_A and C Feed",
  "t2_Recycle Flow",
  "t2_Reactor Feed Rate",
  "t2_Reactor Pressure",
  "t2_Reactor Level",
  "t2_Reactor Temperature",
  "t2_Purge Rate",
  "t2_Product Sep Temp",
  "t2_Product Sep Level",
  "t2_Product Sep Pressure",
  "t2_Product Sep Underflow",
  "t2_Stripper Level",
  "t2_Stripper Pressure",
  "t2_Stripper Underflow",
  "t2_Stripper Temp",
  "t2_Stripper Steam Flow",
  "t2_Compressor Work",
  "t2_Reactor Coolant Temp",
  "t2_Separator Coolant Temp",
  "t2_Component A to Reactor",
  "t2_Component B to Reactor",
  "t2_Component C to Reactor",
  "t2_Component D to Reactor",
  "t2_Component E to Reactor",
  "t2_Component F to Reactor",
  "t2_Component A in Purge",
  "t2_Component B in Purge",
  "t2_Component C in Purge",
  "t2_Component D in Purge",
  "t2_Component E in Purge",
  "t2_Component F in Purge",
  "t2_Component G in Purge",
  "t2_Component H in Purge",
  "t2_Component D in Product",
  "t2_Component E in Product",
  "t2_Component F in Product",
  "t2_Component G in Product",
  "t2_Component H in Product",
  "t2_D feed load",
  "t2_E feed load",
  "t2_A feed load",
  "t2_A and C feed load",
  "t2_Compressor recycle valve",
  "t2_Purge valve",
  "t2_Separator liquid load",
  "t2_Stripper liquid load",
  "t2_Stripper steam valve",
  "t2_Reactor coolant load",
  "t2_Condenser coolant load",
];

const intro = `The process produces two products from four reactants. Also present are an inert and a byproduct making a total of eight components:
A, B, C, D, E, F, G, and H. The reactions are:

A(g) + C(g) + D(g) - G(liq): Product 1,

A(g) + C(g) + E(g) - H(liq): Product 2,

A(g) + E(g) - F(liq): Byproduct,

3D(g) - 2F(liq): Byproduct.

All the reactions are irreversible and exothermic. The reaction rates are a function of temperature through an Arrhenius expression.
The reaction to produce G has a higher activation energy resulting in more sensitivity to temperature.
Also, the reactions are approximately first-order with respect to the reactant concentrations.

The process has five major unit operations: the reactor, the product condenser, a vapor-liquid separator, a recycle compressor and a product stripper.
Figure showing a diagram of the process is attached.

The gaseous reactants are fed to the reactor where they react to form liquid products. The gas phase reactions are catalyzed by a nonvolatile catalyst dissolved
in the liquid phase. The reactor has an internal cooling bundle for removing the heat of reaction. The products leave the reactor as vapors along with the unreacted feeds.
The catalyst remains in the reactor. The reactor product stream passes through a cooler for condensing the products and from there to a vapor-liquid separator.
Noncondensed components recycle back through a centrifugal compressor to the reactor feed.
Condensed components move to a product stripping column to remove remaining reactants by stripping with feed stream number 4.
Products G and H exit the stripper base and are separated in a downstream refining section which is not included in this problem.
The inert and byproduct are primarily purged from the system as a vapor from the vapor-liquid separator.`;

// Read and parse the config.json file
// const configPath = path.resolve(__dirname, '../config.json');
// const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

// // Extract the postFaultThreshold value
// const postFaultThreshold: number = config.fault_trigger_consecutive_step-1;
// const topkfeatures: number = config.topkfeatures;
const postFaultThreshold: number = 2; // trigger earlier in Live mode
const topkfeatures: number = 6;

// TYPES
type RowType = { [key: string]: string };
type CSVType = RowType[];
type Image = { image: string; name: string };
export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  images: Image[];
  explanation: boolean;
};
export type DataPointsId = { [key: string]: number[] };
type ChatContextId = {
  conversation: ChatMessage[];
  setConversation: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
};
export type StatContextId = {
  t2_stat: number;
  anomaly: boolean;
  time?: string; // Legacy field (optional)
  cumulativeTime?: number; // 🔧 FIX: Cumulative data point counter for accurate time tracking
};

interface SimulatorInterface {
  csvFile: string;
  interval: number;
  setCurrentRow: (row: RowType | null) => void;
  pause: boolean;
}

// CONTEXTS
const DataPointsContext = createContext<DataPointsId>({} as DataPointsId);
const ConservationContext = createContext<ChatContextId>({} as ChatContextId);
const StatContext = createContext<StatContextId[]>({} as StatContextId[]);
const ComparativeResultsContext = createContext<{
  results: any;
  isAnalyzing: boolean;
}>({ results: null, isAnalyzing: false });

function Simulator({
  csvFile,
  interval,
  setCurrentRow,
  pause,
}: SimulatorInterface) {
  const [data, setData] = useState<CSVType>([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    console.log("Simulator component mounted or csvFile changed");
    if (csvFile) {
      setCurrentIndex(0);
      console.log("inside simulator useEffect", csvFile);

      // 🔍 Performance monitoring
      const startTime = performance.now();
      console.log("⏱️ Starting CSV parse...");

      Papa.parse<RowType>(csvFile, {
        complete: (result) => {
          const endTime = performance.now();
          const duration = (endTime - startTime).toFixed(2);
          console.log(`✅ CSV file parsed in ${duration}ms - ${result.data.length} rows`);
          setData(result.data);
        },
        header: true,
        download: true,
        skipEmptyLines: "greedy",
        transformHeader: (header) => header.trim(),
        transform: (value) => value.trim(),
      });
    }
  }, [csvFile]);

  useEffect(() => {
    if (data.length > 0 && !pause) {
      // console.log('Starting interval to update current row');
      const timer = setInterval(() => {
        setCurrentRow(data[currentIndex]);
        setCurrentIndex((prevIndex) => (prevIndex + 1) % data.length);
      }, interval);

      return () => {
        // console.log('Clearing interval');
        clearInterval(timer);
      }; // Cleanup interval on component unmount
    }
  }, [data, currentIndex, interval, setCurrentRow, pause]);

  return null; // This component doesn't render anything
}

  function LiveSubscriber({ onRow, onConnect, onDisconnect, onMessage }:
    { onRow: (row: any) => void; onConnect?: () => void; onDisconnect?: () => void; onMessage?: () => void; }) {
    const onRowRef = useRef(onRow);
    const onConnectRef = useRef(onConnect);
    const onDisconnectRef = useRef(onDisconnect);
    const onMessageRef = useRef(onMessage);

    // Keep refs updated without re-subscribing
    useEffect(() => {
      onRowRef.current = onRow;
      onConnectRef.current = onConnect;
      onDisconnectRef.current = onDisconnect;
      onMessageRef.current = onMessage;
    });

    useEffect(() => {
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
      let es: EventSource | null = null;
      let reconnectTimeout: NodeJS.Timeout | null = null;
      let isUnmounted = false;

      const connect = () => {
        if (isUnmounted) return;

        console.log("[Live] Connecting to SSE stream...");
        es = new EventSource(`${apiBaseUrl}/stream`);

        es.onopen = () => {
          console.log("[Live] ✅ SSE connection established");
          onConnectRef.current && onConnectRef.current();
        };

        es.onerror = () => {
          console.warn("[Live] ⚠️ SSE error/closed - will reconnect in 5s");
          onDisconnectRef.current && onDisconnectRef.current();

          // Close current connection
          es?.close();

          // Auto-reconnect after 5 seconds
          if (!isUnmounted) {
            reconnectTimeout = setTimeout(() => {
              console.log("[Live] 🔄 Attempting to reconnect...");
              connect();
            }, 5000);
          }
        };

        es.onmessage = (evt) => {
          try {
            const row = JSON.parse(evt.data);
            onRowRef.current && onRowRef.current(row);
            onMessageRef.current && onMessageRef.current();
          } catch (e) {
            console.error("[Live] ❌ Parse error:", e);
          }
        };
      };

      // Initial connection
      connect();

      // Cleanup on unmount
      return () => {
        console.log("[Live] 🛑 Component unmounting, closing SSE");
        isUnmounted = true;
        if (reconnectTimeout) clearTimeout(reconnectTimeout);
        es?.close();
        onDisconnectRef.current && onDisconnectRef.current();
      };
    }, []); // subscribe once
    return null;
  }


// eslint-disable-next-line react-refresh/only-export-components
export const startTime = new Date();

function getTopKElements(datapoints: DataPointsId, topK: number) {
  // Step 1: Filter the columns based on importance_filter
  const filteredData: DataPointsId = {};
  for (const key of importanceFilter) {
    console.log("Key", key);
    if (datapoints[key]) {
      filteredData[key] = datapoints[key];
    }
  }

  // Step 2: Retrieve the last element of the arrays for the filtered columns
  const lastElements: { [key: string]: number } = {};
  for (const key in filteredData) {
    lastElements[key] = filteredData[key][filteredData[key].length - 1];
    console.log("lastElements", lastElements);
  }

  // Step 3: Find the top K elements based on these last elements
  const sortedKeys = Object.keys(lastElements).sort(
    (a, b) => lastElements[b] - lastElements[a]
  );
  const topKKeys = sortedKeys.slice(0, topK).map((a) => a.slice(3));
  console.log("topKKeys", topKKeys);

  return topKKeys;
}

export default function App() {
  const [opened, { toggle }] = useDisclosure();
  const [selectedFileId, setSelectedFileId] = useState<number>(0);
  const [sliderValue, setSliderValue] = useState(20); // Default to maximum speed (20x)
  const [interval, setPlaybackInterval] = useState(20); // Default to maximum speed (20x)
  // 🔧 FIX: Start with Replay mode to preload baseline data, then auto-switch to Live
  const [dataSource, setDataSource] = useState<'Replay' | 'Live'>('Replay');
  const [currentRow, setCurrentRow] = useState<RowType | null>(null);
  const [dataPoints, setDataPoints] = useState<DataPointsId>({});
  const [pause, setPause] = useDisclosure(false);
  const [t2_stat, setT2_stat] = useState<StatContextId[]>([]);
  const [currentFaultId, setCurrentFaultId] = useState<number | null>(null);
  const [prevFaultId, setPrevFaultId] = useState<number>(0);
  const [postFaultDataCount, setPostFaultDataCount] = useState<number>(0);
  const [liveCount, setLiveCount] = useState<number>(0);
  const [liveDataStarted, setLiveDataStarted] = useState<boolean>(false); // Track when live data starts
  // 🔧 FIX: Track cumulative time (total data points processed)
  const [cumulativeDataPoints, setCumulativeDataPoints] = useState<number>(0);
  // Stabilize flashing: consider connected only after first message within a session.
  const [liveEverReceived, setLiveEverReceived] = useState<boolean>(false);

  const [liveConnected, setLiveConnected] = useState<boolean>(false);
  const location = useLocation();
  const intro_msg: ChatMessage = {
    id: "intro",
    role: "assistant",
    text: intro,
    images: [intro_image],
    explanation: false,
  };
  const [conversation, setConversation] = useState<ChatMessage[]>([intro_msg]);
  const [comparativeResults, setComparativeResults] = useState<any>(null);
  // 🔧 NEW: Global pause state for stopping all auto-refresh timers
  const [globalPause, setGlobalPause] = useState<boolean>(false);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  // const [conversation, setConversation] = useState<ChatMessage[]>([]);

  // Individual model control state. All providers default OFF — user must
  // explicitly opt-in. Avoids accidentally burning paid API keys (Anthropic,
  // Gemini paid tier) on page load.
  const [lmstudioEnabled, setLmstudioEnabled] = useState<boolean>(false);
  const [geminiEnabled, setGeminiEnabled] = useState<boolean>(false);
  const [fastllmEnabled, setFastllmEnabled] = useState<boolean>(false);
  const [claudeEnabled, setClaudeEnabled] = useState<boolean>(false);
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [usageStats, setUsageStats] = useState<any>(null);

  // Cost protection state
  const [sessionStatus, setSessionStatus] = useState<any>(null);
  const [sessionTimer, setSessionTimer] = useState<NodeJS.Timeout | null>(null);

  // 🎯 Smart Analysis: Auto-detection state
  const [autoAnalysisEnabled, setAutoAnalysisEnabled] = useState<boolean>(true);
  const [lastAutoCheckTime, setLastAutoCheckTime] = useState<number>(0);
  const [pendingAnomalyData, setPendingAnomalyData] = useState<{ [key: string]: number[] } | null>(null);

  // 🔧 NEW: Scroll position preservation
  const scrollPositionRef = useRef<number>(0);

  const handleFileChange = (value: string | null) => {
    setSelectedFileId(fault_name.indexOf(value ?? fault_name[0]));
  };

  // UseEffect to log active file path after `selectedFileId` changes
  useEffect(() => {
    console.log("Active file path:", fileId2fileName[selectedFileId]);
  }, [selectedFileId]);

  // 🔧 FIX: Auto-switch from Replay (fault0.csv baseline) to Live mode after 5 seconds
  useEffect(() => {
    console.log("[Auto-Switch] Starting with Replay mode (fault0.csv baseline)");
    const autoSwitchTimer = setTimeout(() => {
      console.log("[Auto-Switch] 5 seconds elapsed, switching to Live mode");
      setDataSource('Live');
      setLiveDataStarted(false); // Will trigger reset on first live data
      // 🔧 FIX: Don't reset cumulative time - continue from preloaded data
      // setCumulativeDataPoints will continue counting from where Replay left off
    }, 5000); // 5 seconds

    return () => clearTimeout(autoSwitchTimer);
  }, []); // Run once on mount

  // 🔧 NEW: Preserve scroll position across re-renders
  useEffect(() => {
    // Save scroll position before potential re-render
    const handleScroll = () => {
      scrollPositionRef.current = window.scrollY;
    };

    window.addEventListener('scroll', handleScroll);

    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  // 🔧 NEW: Restore scroll position after currentRow updates
  useEffect(() => {
    if (scrollPositionRef.current > 0 && !globalPause) {
      // Restore scroll position after React re-renders
      window.scrollTo(0, scrollPositionRef.current);
    }
  }, [currentRow, globalPause]);

  // Load model status on component mount
  useEffect(() => {
    loadModelStatus();
    loadSessionStatus();
    // ❌ Removed: Do not auto-load Claude state from localStorage
    // Users must manually enable Claude each session to avoid unexpected API costs

    // Clear any saved Claude state to prevent auto-enabling
    localStorage.removeItem('claudeEnabled');

    // Start session status polling when Claude is enabled
    if (claudeEnabled) {
      startSessionPolling();
    }
  }, []);

  // Poll session status when Claude is enabled
  useEffect(() => {
    if (claudeEnabled) {
      startSessionPolling();
    } else {
      stopSessionPolling();
    }
  }, [claudeEnabled]);

  // Load model status and sync frontend state on component mount
  useEffect(() => {
    loadModelStatus();
  }, []);

  // Save Claude state to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('claudeEnabled', JSON.stringify(claudeEnabled));
  }, [claudeEnabled]);

  const loadModelStatus = async () => {
    try {
      const response = await fetch('/api/models/status');
      if (response.ok) {
        const status = await response.json();
        setModelStatus(status);
        setUsageStats(status.usage_stats || {});

        // Sync frontend state with backend status (both config and runtime enabled)
        const activeModels = status.active_models || [];
        const runtimeEnabled = status.runtime_enabled || [];

        // A model is enabled if it's either config-enabled or runtime-enabled
        setLmstudioEnabled(activeModels.includes('lmstudio') || runtimeEnabled.includes('lmstudio'));
        setGeminiEnabled(activeModels.includes('gemini') || runtimeEnabled.includes('gemini'));
        setFastllmEnabled(activeModels.includes('fastllm') || runtimeEnabled.includes('fastllm'));
        setClaudeEnabled(activeModels.includes('anthropic') || runtimeEnabled.includes('anthropic'));

        console.log('Model status loaded:', status);
        console.log('Runtime enabled models:', runtimeEnabled);
      }
    } catch (error) {
      console.error('Failed to load model status:', error);
    }
  };

  const toggleModel = async (modelName: string, enabled: boolean) => {
    try {
      const response = await fetch('/api/models/toggle', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model_name: modelName,
          enabled: enabled
        })
      });

      if (response.ok) {
        const result = await response.json();

        // Update local state
        if (modelName === 'anthropic') {
          setClaudeEnabled(enabled);
        } else if (modelName === 'gemini') {
          setGeminiEnabled(enabled);
        } else if (modelName === 'lmstudio') {
          setLmstudioEnabled(enabled);
        } else if (modelName === 'fastllm') {
          setFastllmEnabled(enabled);
        }

        await loadModelStatus(); // Refresh status
        console.log(`${modelName} toggled:`, result);
      } else {
        console.error(`Failed to toggle ${modelName}`);
      }
    } catch (error) {
      console.error(`Error toggling ${modelName}:`, error);
    }
  };

  // Convenience functions for individual models
  const toggleClaude = (enabled: boolean) => toggleModel('anthropic', enabled);
  const toggleGemini = (enabled: boolean) => toggleModel('gemini', enabled);
  const toggleLMStudio = (enabled: boolean) => toggleModel('lmstudio', enabled);
  const toggleFastLLM = (enabled: boolean) => toggleModel('fastllm', enabled);

  const loadSessionStatus = async () => {
    try {
      const response = await fetch('/api/session/status');
      if (response.ok) {
        const status = await response.json();
        setSessionStatus(status);
      }
    } catch (error) {
      console.error('Failed to load session status:', error);
    }
  };

  const startSessionPolling = () => {
    // Clear existing timer
    if (sessionTimer) {
      clearInterval(sessionTimer);
    }

    // Poll every 30 seconds
    const timer = setInterval(() => {
      loadSessionStatus();
    }, 30000);

    setSessionTimer(timer);
  };

  const stopSessionPolling = () => {
    if (sessionTimer) {
      clearInterval(sessionTimer);
      setSessionTimer(null);
    }
  };

  const extendSession = async (additionalMinutes: number = 30) => {
    try {
      const response = await fetch('/api/session/extend', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          additional_minutes: additionalMinutes
        })
      });

      if (response.ok) {
        const result = await response.json();
        await loadSessionStatus(); // Refresh status
        console.log('Session extended:', result);
        return result;
      } else {
        console.error('Failed to extend session');
        return null;
      }
    } catch (error) {
      console.error('Error extending session:', error);
      return null;
    }
  };

  const forceShutdownPremium = async () => {
    try {
      const response = await fetch('/api/session/shutdown', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (response.ok) {
        const result = await response.json();
        setClaudeEnabled(false); // Update UI
        await loadModelStatus(); // Refresh status
        await loadSessionStatus(); // Refresh session
        console.log('Premium models shutdown:', result);
        return result;
      } else {
        console.error('Failed to shutdown premium models');
        return null;
      }
    } catch (error) {
      console.error('Error shutting down premium models:', error);
      return null;
    }
  };


  // 🔍 Check if anomaly state has changed enough to warrant new analysis
  async function checkAnomalyChange(
    fault: { [key: string]: number[] },
    id: string,
    filePath: string
  ): Promise<{ should_analyze: boolean; reason: string }> {
    const payload = {
      data: fault,
      id: id,
      file: filePath,
    };

    try {
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
      const response = await fetch(`${apiBaseUrl}/check_anomaly_change`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const result = await response.json();
        console.log("🔍 Anomaly change check:", result);
        return {
          should_analyze: result.should_analyze,
          reason: result.reason
        };
      } else {
        // On error, default to analyzing
        console.warn("⚠️ Anomaly check failed, defaulting to analyze");
        return { should_analyze: true, reason: "Check failed, analyzing by default" };
      }
    } catch (error) {
      console.error("❌ Error checking anomaly change:", error);
      // On error, default to analyzing
      return { should_analyze: true, reason: "Check error, analyzing by default" };
    }
  }

  async function sendFaultToBackend(
    fault: { [key: string]: number[] },
    id: string,
    filePath: string,
    skipChangeCheck: boolean = false  // Allow manual override
  ) {
    console.log("🔍 Sending fault to backend with file:", filePath);
    console.log("📊 Fault data:", JSON.stringify({ data: fault, id: id, file: filePath }));

    // 🎯 Smart Analysis: Check if state changed before analyzing
    // 🔧 RE-ENABLED to reduce unnecessary LLM calls (saves API costs and reduces LMStudio load)
    if (!skipChangeCheck) {
      const changeCheck = await checkAnomalyChange(fault, id, filePath);
      if (!changeCheck.should_analyze) {
        console.log(`⏭️ Skipping analysis: ${changeCheck.reason}`);
        // Show notification to user
        const skipMessage: ChatMessage = {
          id: `skip-${Date.now()}`,
          role: "assistant",
          text: `ℹ️ **Analysis Skipped**\n\n${changeCheck.reason}\n\nThe anomaly state hasn't changed significantly. Previous analysis results are still valid.`,
          images: [],
          explanation: false,
        };
        setConversation((prevMessages) => [...prevMessages, skipMessage]);
        return; // Don't proceed with analysis
      } else {
        console.log(`✅ Proceeding with analysis: ${changeCheck.reason}`);
      }
    } else {
      console.log("🔧 Smart Analysis check skipped (manual trigger)");
    }

    setIsAnalyzing(true);

    const payload = {
      data: fault,
      id: id,
      file: filePath,
    };

    try {
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
      console.log("🚀 Sending request to /explain...");
      console.log("📦 Payload:", payload);

      const response = await fetch(`${apiBaseUrl}/explain`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      console.log("📡 Response status:", response.status);
      console.log("📡 Response ok:", response.ok);

      if (response.ok) {
        const comparativeData = await response.json();
        console.log("✅ Received comparative analysis:", comparativeData);
        console.log("📊 LLM analyses:", comparativeData.llm_analyses);
        console.log("📊 LLM analyses keys:", Object.keys(comparativeData.llm_analyses || {}));

        // Debug each model's result
        if (comparativeData.llm_analyses) {
          Object.entries(comparativeData.llm_analyses).forEach(([model, data]: [string, any]) => {
            console.log(`📊 ${model}:`, {
              status: data.status,
              hasAnalysis: !!data.analysis,
              analysisLength: data.analysis?.length || 0,
              responseTime: data.response_time
            });
          });
        }

        console.log("🔄 Setting comparative results...");
        setComparativeResults(comparativeData);
        console.log("✅ Comparative results set successfully");

        // Note: Removed automatic addition to conversation to avoid cluttering Assistant page
        // Users can view results in the Multi-LLM Analysis tab and Unified Console
      } else {
        console.error("❌ Error response from server:", response.status);

        // 🔧 NEW: Better error handling for 429 rate limit
        if (response.status === 429) {
          const errorData = await response.json().catch(() => ({}));
          const retryAfter = errorData.retry_after || 30;
          const reason = errorData.reason || "Too many requests";

          console.warn(`⏱️ Rate limit: ${reason} - retry after ${retryAfter}s`);

          const rateLimitMessage: ChatMessage = {
            id: id,
            role: "assistant",
            text: `⏱️ **Analysis Rate Limited**\n\n${reason}\n\nPlease wait ${retryAfter} seconds before next analysis.\n\n💡 Tip: Click "Pause All" button to stop auto-analysis, or disable Smart Analysis checkbox.`,
            images: [],
            explanation: true,
          };

          setConversation((prevMessages) => [...prevMessages, rateLimitMessage]);
          return; // Don't throw, just show message
        }

        throw new Error(`Server error: ${response.status}`);
      }
    } catch (error) {
      console.error("❌ Error sending fault to backend:", error);

      const errorMessage: ChatMessage = {
        id: id,
        role: "assistant",
        text: `❌ **Analysis Failed**\n\nError: ${error}\n\nPlease check that all LLM services are running and try again.`,
        images: [],
        explanation: true,
      };

      setConversation((prevMessages) => [...prevMessages, errorMessage]);
    } finally {
      setIsAnalyzing(false);
    }
  }


  useEffect(() => {
    if (currentRow) {
      // 🔧 FIX: Increment cumulative time counter and update all dependent states
      setCumulativeDataPoints(prev => {
        const newCount = prev + 1;

        // Update data points with new cumulative time
        setDataPoints((prevDataPoints) => {
          const newDataPoints = { ...prevDataPoints };
          for (const [key, value] of Object.entries(currentRow)) {
            // 🔧 FIX: Skip CSV 'time' column - we use cumulative time instead
            if (key === 'time') continue;

            if (!newDataPoints[key]) {
              newDataPoints[key] = [];
            }
            const numValue = parseFloat(value); // Convert the string value to a number
            if (!isNaN(numValue)) {
              // 🔧 FIX: Keep last 300 points (300 * 3min = 900min = 15h)
              newDataPoints[key] = [...newDataPoints[key], numValue].slice(-300);
            }
          }
          // 🔧 FIX: Store cumulative time (keep as number, will format for display)
          if (!newDataPoints['time']) {
            newDataPoints['time'] = [];
          }
          newDataPoints['time'] = [...newDataPoints['time'], newCount].slice(-300);

          return newDataPoints;
        });

        // 🔧 FIX: Update T2 stat INSIDE the same callback to access newCount
        setT2_stat((data) => {
          if ("t2_stat" in currentRow && "anomaly" in currentRow) {
            const anomalyVal = String((currentRow as any).anomaly).toLowerCase() === "true";

            // 🔧 FIX: Keep last 300 data points (same as DCS Screen)
            const newData = [
              ...data,
              {
                t2_stat: Number(currentRow.t2_stat),
                anomaly: anomalyVal,
                cumulativeTime: newCount, // Now correctly accessible
              },
            ].slice(-300);

            return newData;
          } else {
            return data;
          }
        });

        return newCount;
      });

      const isAnomaly = String((currentRow as any).anomaly).toLowerCase() === "true";

      if (isAnomaly) {
        if (currentFaultId == null) {
          setCurrentFaultId(prevFaultId + 1);
          setPostFaultDataCount(0);
        } else {
          setPostFaultDataCount((count) => count + 1);
          if (postFaultDataCount >= postFaultThreshold) {
            setPause.open();
            const topKKeys = getTopKElements(dataPoints, topkfeatures);
            console.log(topKKeys);
            const filteredObject = topKKeys.reduce(
              (acc: Record<string, number[]>, key) => {
                acc[key] = dataPoints[key].map((a) => Number(a));
                return acc;
              },
              {}
            );
            const filePath = fileId2fileName[selectedFileId]; // Get the file path

            // 🎯 Smart Analysis: Store pending data and let auto-check handle it
            if (autoAnalysisEnabled) {
              console.log("🎯 Auto-analysis enabled: Storing anomaly data for smart check");
              setPendingAnomalyData(filteredObject);
            } else {
              // Manual mode: Send immediately without check
              console.log("🎯 Auto-analysis disabled: Sending immediately");
              sendFaultToBackend(filteredObject, `Fault-${currentFaultId}`, filePath, true);
            }
          }
        }
      } else {
        if (currentFaultId !== null) {
          setPrevFaultId(currentFaultId);
          setCurrentFaultId(null);
          setPostFaultDataCount(0);
        }
      }
    }
  }, [currentRow]);

  // 🎯 Smart Analysis: Auto-check anomaly changes every 5 seconds
  useEffect(() => {
    if (!autoAnalysisEnabled || !pendingAnomalyData) {
      return;
    }

    // 🔧 UPDATED: Increased from 5s to 30s to reduce page refresh frequency
    const checkInterval = 30000; // 30 seconds (was 5000)

    // 🔧 NEW: Only run timer if global pause is not active
    if (globalPause) {
      console.log("⏸️ Auto-check paused due to global pause");
      return; // Don't start timer if globally paused
    }

    const timer = setInterval(async () => {
      const currentTime = Date.now();

      // Only check if we have pending data and enough time has passed
      if (pendingAnomalyData && (currentTime - lastAutoCheckTime) >= checkInterval) {
        console.log("🔍 Auto-check: Checking if anomaly state changed...");

        const filePath = fileId2fileName[selectedFileId];
        const changeCheck = await checkAnomalyChange(
          pendingAnomalyData,
          `Fault-${currentFaultId}`,
          filePath
        );

        if (changeCheck.should_analyze) {
          console.log(`✅ Auto-check: State changed, triggering analysis - ${changeCheck.reason}`);
          sendFaultToBackend(
            pendingAnomalyData,
            `Fault-${currentFaultId}`,
            filePath,
            true  // Skip change check since we just did it
          );
          setPendingAnomalyData(null); // Clear pending data after sending
        } else {
          console.log(`⏭️ Auto-check: No significant change - ${changeCheck.reason}`);
        }

        setLastAutoCheckTime(currentTime);
      }
    }, checkInterval);

    return () => clearInterval(timer);
  }, [autoAnalysisEnabled, pendingAnomalyData, lastAutoCheckTime, currentFaultId, selectedFileId, globalPause]);

  return (
    <div>
      <div id="simulator">
        {dataSource === 'Replay' ? (
          <Simulator
            csvFile={fileId2fileName[selectedFileId]}
            interval={1000 / interval}
            setCurrentRow={setCurrentRow}
            pause={pause}
          />
        ) : (
          <LiveSubscriber
            onRow={(row)=>{
              setCurrentRow(row);
              if(!liveEverReceived) setLiveEverReceived(true);
              // 🔧 FIX: Don't reset time - continue from preloaded data
              if (!liveDataStarted) {
                console.log("✅ First live data received - continuing from preloaded data");
                setLiveDataStarted(true);
              }
            }}
            onConnect={() => { console.log("[Live] SSE connection opened (waiting for data...)"); }}
            onDisconnect={() => {
              setLiveConnected(false);
              setLiveEverReceived(false);
              setLiveDataStarted(false);
            }}
            onMessage={() => { setLiveCount((c) => c + 1); setLiveConnected(true); }}
          />
        )}
      </div>
      <div>
        <AppShell
          header={{ height: 60 }}
          navbar={{
            width: 200,
            breakpoint: "sm",
            collapsed: { mobile: !opened },
          }}
          padding="md"

        >
          <AppShell.Header>
            <Group align="center" gap="xs" h="100%" pl="md" wrap="nowrap" justify="space-between">
              {/* Left side: brand + fault selector */}
              <Group align="center" gap="md" wrap="nowrap">
                <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
                <Text fw={700} size="xl">Fault Analysis</Text>
                {/* HIDDEN: Fault selector for static CSV analysis - not needed for live mode */}
                <div style={{display: 'none'}}>
                  <label htmlFor="fileSelect">Fault:</label>
                  <Select
                    id="fileSelect"
                    inputSize="sm"
                    value={fault_name[selectedFileId]}
                    onChange={handleFileChange}
                    data={fault_name}
                    allowDeselect={false}
                  />
                </div>
                {/* Replay speed controls are only for Replay */}
                {dataSource==='Replay' && (
                  <>
                    <ActionIcon variant="subtle" aria-label="Pause/Play" onClick={() => setPause.toggle()}>
                      {pause ? <IconPlayerPlayFilled stroke={1.5} /> : <IconPlayerPauseFilled stroke={1.5} />}
                    </ActionIcon>
                    <Slider min={0} max={20} step={0.0005} value={sliderValue} onChange={setSliderValue} onChangeEnd={setPlaybackInterval} defaultValue={1} miw="100px" />
                  </>
                )}
              </Group>

              {/* Right side: Smart Analysis Toggle */}
              <Group align="center" gap="sm" wrap="nowrap">
                {/* 🎯 Smart Analysis Toggle */}
                <Group align="center" gap="xs" wrap="nowrap">
                  <Checkbox
                    size="sm"
                    checked={autoAnalysisEnabled}
                    onChange={(event) => {
                      const enabled = event.currentTarget.checked;
                      setAutoAnalysisEnabled(enabled);
                      console.log(`🎯 Smart Analysis ${enabled ? 'enabled' : 'disabled'}`);
                      if (!enabled) {
                        setPendingAnomalyData(null); // Clear pending data when disabled
                      }
                    }}
                  />
                  <Text size="sm">Smart Analysis</Text>
                  <Badge size="xs" color={autoAnalysisEnabled ? "blue" : "gray"} variant="light">
                    {autoAnalysisEnabled ? "Auto" : "Manual"}
                  </Badge>
                </Group>

                {/* 🔧 NEW: Global Pause Button - Stops all auto-refresh timers */}
                <Tooltip label={globalPause ? "Resume all updates and auto-refresh timers" : "Pause all updates to read RCA analysis without page jumping"}>
                  <Button
                    onClick={() => {
                      setGlobalPause(!globalPause);
                      console.log(`${!globalPause ? '⏸️ Global pause ON - All updates stopped' : '▶️ Global pause OFF - Updates resumed'}`);
                    }}
                    color={globalPause ? "green" : "orange"}
                    size="sm"
                    variant="filled"
                    leftSection={globalPause ? <IconPlayerPlayFilled size={16} /> : <IconPlayerPauseFilled size={16} />}
                  >
                    {globalPause ? "Resume" : "Pause All"}
                  </Button>
                </Tooltip>

                <Divider orientation="vertical" />

                {/* LLM Model Selection Controls */}
                <Group align="center" gap="md" wrap="nowrap">
                  <Text size="sm" fw={600} c="dimmed">LLM Models:</Text>

                  {/* LMStudio (Local) */}
                  <Group align="center" gap="xs" wrap="nowrap">
                    <Checkbox
                      size="sm"
                      checked={lmstudioEnabled}
                      onChange={(event) => toggleLMStudio(event.currentTarget.checked)}
                    />
                    <Text size="sm">LMStudio</Text>
                    <Badge size="xs" color="green" variant="filled">Local</Badge>
                  </Group>

                  {/* Local LLM (Fast) - HIDDEN: Never worked properly, causes confusion
                  <Divider orientation="vertical" />

                  <Group align="center" gap="xs" wrap="nowrap">
                    <Checkbox
                      size="sm"
                      checked={fastllmEnabled}
                      onChange={(event) => toggleFastLLM(event.currentTarget.checked)}
                    />
                    <Text size="sm">Local LLM</Text>
                    <Badge size="xs" color="teal" variant="filled">⚡ Fast</Badge>
                  </Group>

                  <Divider orientation="vertical" />
                  */}

                  {/* Gemini (Budget) */}
                  <Group align="center" gap="xs" wrap="nowrap">
                    <Checkbox
                      size="sm"
                      checked={geminiEnabled}
                      onChange={(event) => toggleGemini(event.currentTarget.checked)}
                    />
                    <Text size="sm">Gemini</Text>
                    <Badge size="xs" color="teal" variant="filled">Budget</Badge>
                  </Group>

                  {/* Claude (Premium) */}
                  <Group align="center" gap="xs" wrap="nowrap">
                    <Checkbox
                      size="sm"
                      checked={claudeEnabled}
                      onChange={(event) => toggleClaude(event.currentTarget.checked)}
                    />
                    <Text size="sm">Claude</Text>
                    <Badge size="xs" color="orange" variant="filled">Premium</Badge>
                  </Group>
                </Group>

                {/* Session Timer (when Claude is enabled) */}
                {claudeEnabled && sessionStatus?.premium_session_active && (
                  <Group align="center" gap="xs" wrap="nowrap">
                    <Tooltip
                      label={`Auto-shutdown in ${sessionStatus.remaining_time_minutes} min to prevent runaway costs`}
                      position="bottom"
                    >
                      <Badge
                        size="sm"
                        color={sessionStatus.remaining_time_minutes < 5 ? "red" : "yellow"}
                        variant="filled"
                        style={{ cursor: 'help' }}
                      >
                        🛡️ {Math.floor(sessionStatus.remaining_time_minutes)}m
                      </Badge>
                    </Tooltip>

                    <Tooltip label="Extend session by 30 minutes" position="bottom">
                      <Button
                        size="xs"
                        variant="light"
                        color="orange"
                        onClick={() => extendSession(30)}
                      >
                        +30m
                      </Button>
                    </Tooltip>

                    <Tooltip label="Stop premium models now" position="bottom">
                      <Button
                        size="xs"
                        variant="light"
                        color="red"
                        onClick={forceShutdownPremium}
                      >
                        Stop
                      </Button>
                    </Tooltip>
                  </Group>
                )}

                {dataSource==='Live' && (
                  <span style={{marginLeft:8, padding:'4px 10px', borderRadius:14, fontSize:14, fontWeight:800,
                                background: liveConnected? '#2e7d32':'#c62828', color:'#fff'}}>
                    {liveConnected? `Live: ${liveCount}` : 'Live: disconnected'}
                  </span>
                )}

                {/* Model Status Display */}
                {usageStats && (
                  <Group align="center" gap="xs" wrap="nowrap">
                    <Text size="xs" c="dimmed">
                      Calls: {(Object.values(usageStats.usage_stats || {}) as number[]).reduce((a, b) => a + b, 0)}
                    </Text>
                    <Text size="xs" c="dimmed">
                      Cost: ${(Object.values(usageStats.cost_tracking || {}) as number[]).reduce((a, b) => a + b, 0).toFixed(3)}
                    </Text>
                  </Group>
                )}
              </Group>
            </Group>
          </AppShell.Header>

          <AppShell.Navbar>
            <Box>
              <NavLink
                autoContrast
                key={"plot"}
                leftSection={<IconChartHistogram size="1.5rem" />}
                label={<Text size="lg">DCS Screen</Text>}
                component={Link}
                to={"/legacy/plot"}
                variant="filled"
                active={location.pathname === "/legacy/plot"}
              />
              <NavLink
                autoContrast
                key={"chat"}
                leftSection={<IconRobot size="1.5rem" />}
                label={<Text size="lg">Process Description</Text>}
                component={Link}
                to={"/legacy"}
                variant="filled"
                active={location.pathname === "/"}
              />
              <NavLink
                autoContrast
                key={"interactive-rca"}
                leftSection={<IconMessageChatbot size="1.5rem" />}
                label={<Text size="lg">Interactive RCA</Text>}
                component={Link}
                to={"/legacy/assistant"}
                variant="filled"
                active={location.pathname === "/legacy/assistant"}
              />
              <NavLink
                autoContrast
                key={"history"}
                leftSection={<IconReport size="1.5rem" />}
                label={<Text size="lg">Anomaly Detection</Text>}
                component={Link}
                to={"/legacy/history"}
                variant="filled"
                active={location.pathname === "/legacy/history"}
              />
              <NavLink
                autoContrast
                key={"comparative"}
                leftSection={<IconBrain size="1.5rem" />}
                label={<Text size="lg">Multi-LLM Analysis</Text>}
                component={Link}
                to={"/legacy/comparative"}
                variant="filled"
                active={location.pathname === "/legacy/comparative"}
              />
            </Box>
          </AppShell.Navbar>

          <AppShell.Main>
            <StatContext.Provider value={t2_stat}>
              <ConservationContext.Provider
                value={{ conversation, setConversation }}
              >
                <DataPointsContext.Provider value={dataPoints}>
                  <ComparativeResultsContext.Provider
                    value={{ results: comparativeResults, isAnalyzing }}
                  >
                    {currentRow && <Outlet />}
                  </ComparativeResultsContext.Provider>
                </DataPointsContext.Provider>
              </ConservationContext.Provider>
            </StatContext.Provider>
          </AppShell.Main>
        </AppShell>
      </div>
    </div>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useDataPoints() {
  return useContext(DataPointsContext);
}

// eslint-disable-next-line react-refresh/only-export-components
export function useConversationState() {
  return useContext(ConservationContext);
}

// eslint-disable-next-line react-refresh/only-export-components
export function useComparativeResults() {
  return useContext(ComparativeResultsContext);
}

// eslint-disable-next-line react-refresh/only-export-components
export function useStatState() {
  return useContext(StatContext);
}
