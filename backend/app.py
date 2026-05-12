# imports
from openai import OpenAI
from fastapi import FastAPI, HTTPException, UploadFile, File
from typing import List
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import json
import base64
import matplotlib
from datetime import datetime
from pathlib import Path

# Load environment variables first
load_dotenv()
import pandas as pd
import asyncio

matplotlib.use("Agg")

from prompts import EXPLAIN_PROMPT, EXPLAIN_ROOT, SYSTEM_MESSAGE
from multi_llm_client import MultiLLMClient
from independent_llm_manager import IndependentLLMSystem
from ai_agent_service import AIAgentKnowledgeService, enhance_analysis_with_ai_agent
from enhanced_md_saver import enhanced_md_saver, save_analysis_to_md
from knowledge_manager import EnhancedKnowledgeManager

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load and validate configuration
def load_config(file_path):
    with open(file_path, "r") as config_file:
        config = json.load(config_file)

    # Validate models configuration
    if "models" not in config:
        raise ValueError("Missing 'models' configuration")

    # Check enabled models in both 'models' section and 'lmstudio' section
    enabled_models = [name for name, cfg in config["models"].items() if cfg.get("enabled", False)]

    # Also check LMStudio
    if config.get("lmstudio", {}).get("enabled", False):
        enabled_models.append("lmstudio")

    # Soft check: warn but do not crash if no multi_llm_client provider is
    # enabled. The new Live Copilot path uses NAT with its own LLM config
    # (see backend/nat_workflows/tep_rca_workflow.yml + agent_models.py),
    # which is independent of this multi_llm_client. Hard-failing here
    # would break the new path just because the user disabled all of the
    # legacy /explain providers.
    if not enabled_models:
        print(
            "⚠️ No multi_llm_client providers enabled (legacy /explain path "
            "will be unavailable). The new NAT Live Copilot path still works "
            "via its own LLM config — see backend/agent_models.py."
        )

    # Validate fault_trigger_consecutive_step
    if not isinstance(config["fault_trigger_consecutive_step"], int) or config["fault_trigger_consecutive_step"] < 1:
        raise ValueError(
            f"Invalid fault_trigger_consecutive_step: {config['fault_trigger_consecutive_step']}. "
            f"Must be an integer >= 1."
        )

    # Validate topkfeatures
    if not isinstance(config["topkfeatures"], int) or not (1 <= config["topkfeatures"] <= 20):
        raise ValueError(
            f"Invalid topkfeatures: {config['topkfeatures']}. "
            f"Must be an integer between 1 and 20."
        )

    # Validate prompt
    valid_prompts = ["explain", "explain root"]
    if config["prompt"] not in valid_prompts:
        raise ValueError(f"Invalid prompt: {config['prompt']}. Must be one of {valid_prompts}.")

    return config
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "..", "config", "config.json")
    # Load the configuration
    config = load_config(config_path)

    PROMPT_SELECT = EXPLAIN_PROMPT if config["prompt"] == "explain" else EXPLAIN_ROOT
    fault_trigger_consecutive_step = config["fault_trigger_consecutive_step"]

    # Initialize Multi-LLM Client
    multi_llm_client = MultiLLMClient(config)

    print("✅ Config loaded and Multi-LLM client initialized")
    print(f"📊 Enabled models: {multi_llm_client.enabled_models}")

    # Initialize Independent LLM System
    independent_llm_system = IndependentLLMSystem(multi_llm_client)
    print("🔧 Independent LLM System initialized")

    # Initialize AI Agent Knowledge Service
    ai_agent_service = AIAgentKnowledgeService()
    print("🚀 AI Agent Knowledge Service initialized")
    print(f"📚 Knowledge base documents: {len(ai_agent_service.knowledge_base)}")

    # Register shutdown callback to stop simulation when premium models auto-shutdown
    def simulation_shutdown_callback():
        """Callback to stop simulation when premium models are auto-disabled"""
        global _simulation_auto_stopped
        _simulation_auto_stopped = True
        logger.warning("🛡️ TEP simulation auto-stopped due to premium model shutdown")
        # Note: The actual simulation stopping will be handled by the unified control panel
        # This just sets a flag that can be checked via API

    multi_llm_client.register_shutdown_callback(simulation_shutdown_callback)

except Exception as e:
    print("❌ Error loading config:", e)
    raise
# === Live ingestion setup: PCA model and state ===
from typing import Optional, Dict, Any, List
from collections import deque
from fastapi import Body
import hashlib

from model import FaultDetectionModel

# === Anomaly State Change Detection ===
class AnomalyStateTracker:
    """Track anomaly state changes to avoid redundant LLM analyses"""

    def __init__(self, check_interval: int = 5, min_llm_interval: int = 10):
        """
        Args:
            check_interval: Minimum seconds between state checks (default: 5)
            min_llm_interval: Minimum seconds between LLM requests (default: 10)
        """
        self.check_interval = check_interval
        self.min_llm_interval = min_llm_interval  # 🔧 NEW: Minimum interval between LLM requests
        self.last_state_hash = None
        self.last_check_time = 0
        self.last_llm_request_time = 0  # 🔧 NEW: Track last LLM request time
        self.last_anomaly_features = []
        self.last_anomaly_data = {}
        self.is_analyzing = False  # 🔧 NEW: Track if LLM analysis is in progress

    def _compute_state_hash(self, anomaly_features: List[str], anomaly_data: Dict[str, Any]) -> str:
        """Compute hash of current anomaly state"""
        # Sort features for consistent hashing
        sorted_features = sorted(anomaly_features)

        # Create a stable representation of the state
        state_repr = {
            'features': sorted_features,
            'feature_count': len(sorted_features),
            # Include key statistics from anomaly data
            'data_summary': {}
        }

        # Add summary statistics for each feature
        for feature in sorted_features:
            if feature in anomaly_data:
                values = anomaly_data[feature]
                if isinstance(values, list) and len(values) > 0:
                    # Use last few values for comparison
                    recent_values = values[-5:] if len(values) >= 5 else values
                    state_repr['data_summary'][feature] = {
                        'mean': round(sum(recent_values) / len(recent_values), 4),
                        'min': round(min(recent_values), 4),
                        'max': round(max(recent_values), 4)
                    }

        # Convert to JSON string and hash
        state_str = json.dumps(state_repr, sort_keys=True)
        return hashlib.md5(state_str.encode()).hexdigest()

    def has_state_changed(self, anomaly_features: List[str], anomaly_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Check if anomaly state has changed since last check

        Returns:
            (has_changed, reason) tuple
            - has_changed: True if state changed or enough time passed
            - reason: Human-readable reason for the decision
        """
        import time
        current_time = time.time()

        # Compute current state hash
        current_hash = self._compute_state_hash(anomaly_features, anomaly_data)

        # First time check
        if self.last_state_hash is None:
            self.last_state_hash = current_hash
            self.last_check_time = current_time
            self.last_anomaly_features = anomaly_features.copy()
            self.last_anomaly_data = anomaly_data.copy()
            return True, "First anomaly detection"

        # Check if enough time has passed since last check
        time_since_last = current_time - self.last_check_time

        # State has changed
        if current_hash != self.last_state_hash:
            # Determine what changed
            new_features = set(anomaly_features) - set(self.last_anomaly_features)
            removed_features = set(self.last_anomaly_features) - set(anomaly_features)

            reason_parts = []
            if new_features:
                reason_parts.append(f"New anomalies: {', '.join(sorted(new_features))}")
            if removed_features:
                reason_parts.append(f"Resolved: {', '.join(sorted(removed_features))}")
            if not new_features and not removed_features:
                reason_parts.append("Anomaly values changed significantly")

            reason = "; ".join(reason_parts)

            # Update state
            self.last_state_hash = current_hash
            self.last_check_time = current_time
            self.last_anomaly_features = anomaly_features.copy()
            self.last_anomaly_data = anomaly_data.copy()

            return True, reason

        # State unchanged but check interval passed
        if time_since_last >= self.check_interval:
            return False, f"No change in {time_since_last:.1f}s (skipping analysis)"

        # State unchanged and within check interval
        return False, f"No change (last check {time_since_last:.1f}s ago)"

    def can_send_llm_request(self) -> tuple[bool, str]:
        """
        Check if enough time has passed since last LLM request

        Returns:
            (can_send, reason): Tuple of boolean and reason string
        """
        import time
        current_time = time.time()
        time_since_last_llm = current_time - self.last_llm_request_time

        if time_since_last_llm < self.min_llm_interval:
            remaining = self.min_llm_interval - time_since_last_llm
            return False, f"Too soon (wait {remaining:.1f}s more, min interval: {self.min_llm_interval}s)"

        return True, f"OK (last request {time_since_last_llm:.1f}s ago)"

    def mark_llm_request_sent(self):
        """Mark that an LLM request was just sent"""
        import time
        self.last_llm_request_time = time.time()

# Initialize anomaly state tracker with configurable minimum LLM interval
llm_min_interval = config.get("llm_min_interval_seconds", 30)  # Default to 30s if not specified
anomaly_state_tracker = AnomalyStateTracker(check_interval=5, min_llm_interval=llm_min_interval)
print(f"✅ Anomaly State Tracker initialized (check interval: 5s, min LLM interval: {llm_min_interval}s)")

# Feature columns to use for PCA - ALL 52 TEP features for complete anomaly detection
# Includes: 22 XMEAS (process measurements) + 19 XMEAS compositions + 11 XMV (manipulated variables)
FEATURE_COLUMNS: List[str] = [
    # XMEAS 1-22: Process measurements
    "A Feed", "D Feed", "E Feed", "A and C Feed", "Recycle Flow",
    "Reactor Feed Rate", "Reactor Pressure", "Reactor Level", "Reactor Temperature",
    "Purge Rate", "Product Sep Temp", "Product Sep Level", "Product Sep Pressure",
    "Product Sep Underflow", "Stripper Level", "Stripper Pressure", "Stripper Underflow",
    "Stripper Temp", "Stripper Steam Flow", "Compressor Work", "Reactor Coolant Temp",
    "Separator Coolant Temp",
    # XMEAS 23-41: Component compositions (critical for fault detection!)
    "Component A to Reactor", "Component B to Reactor", "Component C to Reactor",
    "Component D to Reactor", "Component E to Reactor", "Component F to Reactor",
    "Component A in Purge", "Component B in Purge", "Component C in Purge",
    "Component D in Purge", "Component E in Purge", "Component F in Purge",
    "Component G in Purge", "Component H in Purge",
    "Component D in Product", "Component E in Product", "Component F in Product",
    "Component G in Product", "Component H in Product",
    # XMV 1-11: Manipulated variables (control inputs)
    "D feed load", "E feed load", "A feed load", "A and C feed load",
    "Compressor recycle valve", "Purge valve", "Separator liquid load",
    "Stripper liquid load", "Stripper steam valve", "Reactor coolant load",
    "Condenser coolant load"
]

# Train PCA model on normal operation (fault0.csv) restricted to FEATURE_COLUMNS
import pandas as _pd

try:
    _train_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "fault0.csv")
    _train_df = _pd.read_csv(_train_path)
    if "time" in _train_df.columns:
        _train_df = _train_df.drop(columns=["time"])  # drop timestamp col if present
    missing_cols = [c for c in FEATURE_COLUMNS if c not in _train_df.columns]
    if missing_cols:
        raise RuntimeError(f"Training data missing expected columns: {missing_cols}")
    _train_df = _train_df[FEATURE_COLUMNS]

    pca_model = FaultDetectionModel(n_components=0.9, alpha=config.get("anomaly_threshold", 0.025))
    pca_model.fit(_train_df)
    print("✅ PCA model trained on normal operation (fault0.csv) with", len(FEATURE_COLUMNS), "features")
except Exception as e:
    print("❌ Failed to initialize PCA model:", e)
    raise

# Live state
LIVE_WINDOW_SIZE = int(config.get("pca_window_size", 20))
consecutive_anomalies_required = int(config.get("fault_trigger_consecutive_step", 1))  # 🔧 Changed from 3 to 1 for faster response
# Decimation and LLM rate limit (runtime configurable)
decimation_N = int(config.get("decimation_N", 1))  # 1 = no decimation
llm_min_interval_seconds = int(config.get("llm_min_interval_seconds", 10))  # 🔧 Changed from 60 to 10 seconds for faster LLM trigger
# Feature-shift retrigger controls
feature_shift_jaccard_threshold = float(config.get("feature_shift_jaccard_threshold", 0.6))
feature_shift_min_interval_seconds = int(config.get("feature_shift_min_interval_seconds", 120))

# Cost protection state
_simulation_auto_stopped = False

_consecutive_anomalies = 0
_last_analysis_result: Optional[Dict[str, Any]] = None
_last_llm_trigger_time: float = 0.0
_last_llm_top_features: list[str] = []

# Keep a short history of recent analyses to reduce UI flicker
_analysis_history: deque[Dict[str, Any]] = deque(maxlen=6)

# Buffers
# live_buffer now stores aggregated rows used for PCA/LLM and includes t2/anomaly/time
live_buffer: deque[Dict[str, float]] = deque(maxlen=LIVE_WINDOW_SIZE)
_recent_raw_rows: deque[Dict[str, float]] = deque(maxlen=decimation_N)
_aggregated_count: int = 0

# Helper: build feature comparison text against normal means
import pandas as _pd2

# Auto-load baseline statistics on startup
_normal_stats = None
try:
    _stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats", "features_mean_std.csv")
    _normal_stats = _pd2.read_csv(_stats_path).set_index("feature")
    print(f"✅ Baseline loaded: {len(_normal_stats)} features from {os.path.basename(_stats_path)}")
    print(f"📊 Baseline features: {', '.join(list(_normal_stats.index[:5]))}... (showing first 5)")
except Exception as e:
    print(f"⚠️ Could not load baseline stats for comparison: {e}")
    print("💡 Run 'python generate_baseline.py' to create baseline from fault0.csv")
    _normal_stats = None


def build_live_feature_comparison(feature_series: Dict[str, List[float]]) -> str:
    """
    Build a compact, explicit comparison for the LLM using the preloaded
    baseline (features_mean_std.csv). Always returns up to 6 lines like:
      1. Reactor Temperature: Fault=120.45 | Normal=120.40 | Δ=0.05 (0.04%) | z=2.10
    If baseline is missing, we still provide the latest values with a note.
    """
    lines: list[str] = ["Top 6 Contributing Features (Fault vs Normal):"]
    idx = 1
    for feat, series in feature_series.items():
        if not series:
            continue
        last_val = float(series[-1])
        if _normal_stats is not None and feat in _normal_stats.index:
            norm_mean = float(_normal_stats.loc[feat, "mean"]) if "mean" in _normal_stats.columns else 0.0
            norm_std = float(_normal_stats.loc[feat, "std"]) if "std" in _normal_stats.columns else 0.0
            delta = last_val - norm_mean
            denom = norm_mean if abs(norm_mean) > 1e-9 else 1e-9
            pct = (delta / denom) * 100.0
            z = delta / (norm_std if norm_std > 1e-12 else 1e9)
            lines.append(f"{idx}. {feat}: Fault={last_val:.3f} | Normal={norm_mean:.3f} | Δ={delta:.3f} ({pct:.2f}%) | z={z:.2f}")
        else:
            lines.append(f"{idx}. {feat}: Fault={last_val:.3f} | Normal=NA (baseline not loaded)")
        idx += 1
    return "\n".join(lines)


# --- Lightweight rotating logs (size-limited) ---
import logging
from logging.handlers import RotatingFileHandler

_logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(_logs_dir, exist_ok=True)
_log_path = os.path.join(_logs_dir, "backend.log")
logger = logging.getLogger("faultexplainer")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _h = RotatingFileHandler(_log_path, maxBytes=1_000_000, backupCount=3)
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(_h)
# ------------------------------------------------
# --- Temporary diagnostics (can be removed later) ---
_diag_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagnostics")
os.makedirs(_diag_dir, exist_ok=True)


# Persistent analysis history file
_history_file = os.path.join(_diag_dir, 'analysis_history.jsonl')
# Markdown history file
_history_md_file = os.path.join(_diag_dir, 'analysis_history.md')
# Operator context sidecar (Stage 1 JSONL for chat/notes/ruled_out)
_operator_context_file = os.path.join(_diag_dir, 'operator_context.jsonl')


def _append_operator_context(entry: dict):
    try:
        os.makedirs(os.path.dirname(_operator_context_file), exist_ok=True)
        entry = dict(entry)
        entry["timestamp"] = datetime.now().isoformat()
        with open(_operator_context_file, 'a', encoding='utf-8') as f:
            import json as _json
            f.write(_json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"⚠️ Failed to append operator context: {e}")

# Per-day Markdown history folder
_history_days_dir = os.path.join(_diag_dir, 'analysis_history')
os.makedirs(_history_days_dir, exist_ok=True)



sse_logger = logging.getLogger("diag.sse")
if not sse_logger.handlers:
    _h_sse = RotatingFileHandler(os.path.join(_diag_dir, "sse.log"), maxBytes=500_000, backupCount=1)
    _h_sse.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    sse_logger.addHandler(_h_sse)
sse_logger.setLevel(logging.INFO)

ingest_logger = logging.getLogger("diag.ingest")
if not ingest_logger.handlers:
    _h_ing = RotatingFileHandler(os.path.join(_diag_dir, "ingest.log"), maxBytes=1_000_000, backupCount=1)
    _h_ing.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    ingest_logger.addHandler(_h_ing)
ingest_logger.setLevel(logging.INFO)
# ---------------------------------------------------



# Initialize FastAPI app
app = FastAPI()

# Safari-compatible CORS origins (use 127.0.0.1 instead of localhost)
origins = [
    "http://127.0.0.1:5173",
    "http://127.0.0.1:9002",
    "http://127.0.0.1:8000",
    "http://localhost:5173",  # Fallback for Chrome
    "http://localhost:9002",
    "http://localhost:8000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Knowledge Manager for RAG
try:
    knowledge_manager = EnhancedKnowledgeManager()
    logger.info("✅ Knowledge Manager initialized successfully")
except Exception as e:
    logger.warning(f"⚠️ Knowledge Manager initialization failed: {e}")

# Mount the optional NAT agentic RCA router. Failures are logged but do
# not prevent the legacy demo from starting. We try both qualified and
# unqualified imports so it works whether the app is launched from the
# repo root (python -m backend.app) or from backend/ (python app.py).
nat_router = None
try:
    from backend.nat_api import nat_router as _nat_router_pkg  # type: ignore
    nat_router = _nat_router_pkg
except Exception:
    try:
        # Make the repo root importable for the next attempt.
        _repo_root = Path(__file__).resolve().parent.parent
        if str(_repo_root) not in sys.path:
            sys.path.insert(0, str(_repo_root))
        from backend.nat_api import nat_router as _nat_router_root  # type: ignore
        nat_router = _nat_router_root
    except Exception as e:
        logger.warning(f"⚠️ NAT router not mounted: {e}")
if nat_router is not None:
    app.include_router(nat_router)
    app.include_router(nat_router, prefix="/api")
    logger.info("✅ Mounted NAT agentic RCA router at /api/*")
    knowledge_manager = None

# Live Copilot Phase 1 routers (live snapshot, SSE streaming, follow-up chat,
# anomaly state, sim proxy). Mounted after the legacy NAT router so paths
# under /api/agent/diagnose, /api/agent/runs/{id}/stream, /api/agent/runs/{id}/followup,
# /api/anomaly/state, and /api/sim/* are owned by the new module.
try:
    from backend.nat_api_live import router as nat_api_live_router
    app.include_router(nat_api_live_router)
    logger.info("✅ Mounted Live Copilot NAT router")
except Exception as _exc:  # noqa: BLE001
    logger.warning(f"⚠️ Live Copilot NAT router not mounted: {_exc}")

try:
    from backend.sim_control import router as sim_control_router
    app.include_router(sim_control_router)
    logger.info("✅ Mounted sim control router")
except Exception as _exc:  # noqa: BLE001
    logger.warning(f"⚠️ Sim control router not mounted: {_exc}")


# Define request and response models
class MessageRequest(BaseModel):
    data: list[dict[str, str]]
    id: str


class ExplainationRequest(BaseModel):
    data: dict[str, list[float]]
    id: str
    file: str


class Image(BaseModel):
    image: str
    name: str


class MessageResponse(BaseModel):
    content: str
    images: list[Image] = []
    index: int
    id: str


def ChatModelCompletion(
    messages: list[dict[str, str]], msg_id: str, images: list[str] = None, seed: int = 0, model: str = "gpt-4o"
):
    # Set temperature based on the model
    temperature = 0 if (model != "o1-preview" and model != "o1-mini") else 1  # o1-preview only supports temperature=1

    # Filter out 'system' role messages if using 'o1-preview' model
    if model == "o1-preview" or model == "o1-mini":
        messages = [msg for msg in messages if msg['role'] != 'system']

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        temperature=temperature,
        seed=seed,
    )
    index = 0
    for chunk in response:
        if chunk.choices[0].delta.content:
            response_text = chunk.choices[0].delta.content
            response_data = {
                "index": index,
                "content": response_text,
                "id": msg_id,
                "images": images if index == 0 and images else [],
            }
            yield f"data: {json.dumps(response_data)}\n\n"
            index += 1


def get_full_response(messages: list[dict[str, str]], model: str = "gpt-4o", seed: int = 0):
    temperature = 0 if (model != "o1-preview" and model != "o1-mini") else 1
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        seed=seed,
    )
    full_response = ""
    for choice in response.choices:
        full_response += choice.message.content
    return full_response


import os
import pandas as pd

def generate_feature_comparison(request_data, file_path):
    """
    Build a compact "Top 6 Contributing Features (Fault vs Normal)" comparison string
    for the Multi‑LLM view. Uses the latest value from request_data and compares to
    the precomputed normal means/std in stats/features_mean_std.csv.

    Returns a string like:
      Top 6 Contributing Features (Fault vs Normal):
      1. Reactor Temperature: Fault=120.45 | Normal=120.40 | Δ=0.05 (0.04%) | z=2.10
    """
    try:
        # Load normal baseline
        current_dir = os.path.dirname(os.path.abspath(__file__))
        stats_file_path = os.path.join(current_dir, "stats", "features_mean_std.csv")
        normal_df = pd.read_csv(stats_file_path).set_index("feature")

        # Extract last values from request_data
        rows = []
        for feature, series in (request_data or {}).items():
            try:
                if series is None or len(series) == 0:
                    continue
                last_val = float(series[-1])
                rows.append((feature, last_val))
            except Exception:
                continue

        if not rows:
            return "Top 6 Contributing Features (Fault vs Normal):\n(no features provided)"

        # Compute deltas vs normal mean for features present in baseline
        scored = []
        for feat, val in rows:
            if feat in normal_df.index:
                norm_mean = float(normal_df.loc[feat, "mean"]) if "mean" in normal_df.columns else 0.0
                norm_std = float(normal_df.loc[feat, "std"]) if "std" in normal_df.columns else 0.0
                delta = val - norm_mean
                denom = norm_mean if abs(norm_mean) > 1e-9 else 1e-9
                pct = (delta / denom) * 100.0
                z = delta / (norm_std if norm_std > 1e-12 else 1e9)
                score = abs(pct)  # rank by magnitude of percent change
                scored.append((feat, val, norm_mean, delta, pct, z, score))
            else:
                # Keep but mark missing baseline
                scored.append((feat, val, None, None, None, None, -1))

        # Select top 6 by score (>=0); fall back to any 6 if baseline missing
        with_scores = [s for s in scored if s[-1] >= 0]
        top = sorted(with_scores, key=lambda x: x[-1], reverse=True)[:6]
        if len(top) < 6:
            # pad with remaining entries (baseline unknown)
            remain = [s for s in scored if s not in top]
            top += remain[: 6 - len(top)]

        lines = ["Top 6 Contributing Features (Fault vs Normal):"]
        idx = 1
        for feat, val, norm_mean, delta, pct, z, _ in top:
            if norm_mean is not None:
                lines.append(f"{idx}. {feat}: Fault={val:.3f} | Normal={norm_mean:.3f} | Δ={delta:.3f} ({pct:.2f}%) | z={z:.2f}")
            else:
                lines.append(f"{idx}. {feat}: Fault={val:.3f} | Normal=NA (baseline not loaded)")
            idx += 1
        return "\n".join(lines)
    except Exception as e:
        # Fail safe: minimal message so LLMs still get some context
        return f"Top 6 Contributing Features (Fault vs Normal):\n(error building comparison: {e})"
# === Live ingestion endpoints ===
class IngestRequest(BaseModel):
    data_point: Dict[str, float]  # keys must include FEATURE_COLUMNS subset; may include time/step
    id: Optional[str] = None

@app.post("/ingest")
async def ingest_live_point(req: IngestRequest):
    global _consecutive_anomalies, _last_analysis_result, _recent_raw_rows, _aggregated_count, _last_llm_trigger_time, _last_llm_top_features
    try:
        # Keep only required feature columns for PCA
        raw_row = {k: float(v) for k, v in req.data_point.items() if k in FEATURE_COLUMNS}
        if len(raw_row) != len(FEATURE_COLUMNS):
            ingest_logger.info("ignored missing_features present=%s", list(raw_row.keys()))
            return {"status": "ignored", "reason": "missing_features", "present": list(raw_row.keys())}

        # Decimation/aggregation: collect raw rows and every N rows compute their mean
        _recent_raw_rows.append(raw_row)
        ingest_logger.info("row have=%d need=%d", len(_recent_raw_rows), decimation_N)
        if len(_recent_raw_rows) < max(1, decimation_N):
            # Not enough for an aggregated point yet
            return {"status": "ok", "aggregating": True, "have": len(_recent_raw_rows), "need": decimation_N}

        import numpy as _np
        import pandas as _pd3
        arr = _np.array([[r[c] for c in FEATURE_COLUMNS] for r in list(_recent_raw_rows)])
        mean_vec = arr.mean(axis=0)
        row = {c: float(v) for c, v in zip(FEATURE_COLUMNS, mean_vec)}
        _recent_raw_rows.clear()  # reset for next aggregation window
        _aggregated_count += 1

        df = _pd3.DataFrame([row])
        t2, is_anom = pca_model.process_data_point(df)

        # Maintain live buffer for context (store t2/anomaly too for streaming)
        row_with_stats = {**row,
                           "t2_stat": float(t2),
                           "anomaly": bool(is_anom),
                           "time": _aggregated_count,
                           "threshold": float(pca_model.t2_threshold)}
        live_buffer.append(row_with_stats)

        # Count consecutive anomalies
        if is_anom:
            _consecutive_anomalies += 1
        else:
            _consecutive_anomalies = 0

        result: Dict[str, Any] = {
            "t2_stat": t2,
            "anomaly": bool(is_anom),
            "threshold": float(pca_model.t2_threshold),
            "consecutive_anomalies": _consecutive_anomalies,
            "aggregated_index": _aggregated_count,
        }
        ingest_logger.info("aggregated idx=%d t2=%.4f anomaly=%s", _aggregated_count, t2, bool(is_anom))

        # LLM trigger gating: need enough anomalies, enough context, and respect min interval
        import time as _time
        enough_context = len(live_buffer) >= max(5, int(LIVE_WINDOW_SIZE/2))  # relax for quicker triggers

        # 🔧 FIX: Use AnomalyStateTracker as the ONLY rate limiter (respects slider value)
        if is_anom and _consecutive_anomalies >= max(1, consecutive_anomalies_required) and enough_context:
            # Check if LLM analysis is already in progress
            if anomaly_state_tracker.is_analyzing:
                result["llm"] = {"status": "analyzing_in_progress"}
                logger.info("⏭️ Skipping LLM trigger - analysis already in progress")
            else:
                # 🔧 CRITICAL: Check minimum LLM request interval using AnomalyStateTracker (respects slider)
                can_send, interval_reason = anomaly_state_tracker.can_send_llm_request()
                if not can_send:
                    result["llm"] = {"status": "rate_limited", "reason": interval_reason}
                    logger.info(f"⏱️ Skipping LLM trigger - {interval_reason}")
                else:
                    logger.info(f"✅ LLM request allowed - {interval_reason}")

                    # Calculate top anomalous features
                    buf_df = _pd3.DataFrame(list(live_buffer))
                    deltas = (buf_df.iloc[-1][FEATURE_COLUMNS] - buf_df[FEATURE_COLUMNS].mean()).abs().sort_values(ascending=False)
                    topk = int(config.get("topkfeatures", 6))
                    top_features = list(deltas.index[:topk])

                    feature_series = {feat: buf_df[feat].tail(LIVE_WINDOW_SIZE).tolist() for feat in top_features}
                    comparison = build_live_feature_comparison(feature_series)
                    user_prompt = f"{PROMPT_SELECT}\n\nHere are the top six features with values during the fault and normal operation:\n{comparison}"

                    # 🔧 FIX: Run LLM analysis in background to avoid blocking /stream endpoint
                    import asyncio
                    async def background_llm_analysis():
                        import time
                        analysis_start_time = time.time()
                        try:
                            # 🔧 NEW: Set analyzing flag and mark request time
                            anomaly_state_tracker.is_analyzing = True
                            anomaly_state_tracker.mark_llm_request_sent()  # 🔧 NEW: Mark request time
                            logger.info("🤖 Starting background LLM analysis...")
                            logger.info(f"🔍 Analysis flag set at {time.strftime('%H:%M:%S')}")
                            logger.info(f"⏱️ Next LLM request allowed after {anomaly_state_tracker.min_llm_interval}s")

                            # 🔧 NEW: Add timeout protection (3 minutes max)
                            try:
                                llm_results = await asyncio.wait_for(
                                    multi_llm_client.get_analysis_from_all_models(
                                        system_message=SYSTEM_MESSAGE,
                                        user_prompt=user_prompt,
                                    ),
                                    timeout=180.0  # 3 minutes total timeout
                                )
                                logger.info(f"✅ LLM analysis completed in {time.time() - analysis_start_time:.2f}s")
                            except asyncio.TimeoutError:
                                logger.error(f"❌ LLM analysis timed out after 180 seconds")
                                # Create empty results for timeout
                                llm_results = {}

                            formatted = multi_llm_client.format_comparative_results(results=llm_results, feature_comparison=comparison, sensor_data=feature_series)

                            # 🔧 FIX: 保存原始LLM分析到各自的MD文件
                            # Removed AI Agent enhancement to speed up response time
                            try:
                                llm_analyses = formatted.get("llm_analyses", {})
                                for model_name, analysis_data in llm_analyses.items():
                                    if analysis_data.get("status") == "success":
                                        # 🔧 CRITICAL FIX: 正确的数据结构映射
                                        # analysis_data 结构: {"analysis": "content", "response_time": 13.71, "status": "success"}
                                        # 但 save_standard_analysis 期望: {"response": "content", "analysis_duration": 13.71, "status": "success"}
                                        corrected_data = {
                                            "response": analysis_data.get("analysis", "No response available"),
                                            "analysis_duration": analysis_data.get("response_time", 0),
                                            "status": analysis_data.get("status", "unknown"),
                                            "timestamp": datetime.now().isoformat()
                                        }
                                        enhanced_md_saver.save_standard_analysis(
                                            model_name,
                                            corrected_data,
                                            top_features
                                        )
                                        logger.info(f"✅ Saved {model_name} analysis to MD file")

                                        # 🔧 NEW FIX: Update IndependentLLMSystem with results
                                        try:
                                            # Update the independent model manager's current_result
                                            if model_name in independent_llm_system.managers:
                                                manager = independent_llm_system.managers[model_name]
                                                manager.current_result = corrected_data
                                                manager.result_timestamp = time.time()
                                                logger.info(f"✅ Updated {model_name} independent manager with result")
                                        except Exception as update_error:
                                            logger.warning(f"⚠️ Failed to update {model_name} independent manager: {update_error}")
                            except Exception as save_error:
                                logger.warning(f"⚠️ Failed to save individual LLM analyses to MD: {save_error}")

                            global _last_analysis_result
                            _last_analysis_result = formatted

                            # build a snapshot with an id for persistence
                            snap = {"id": int(time.time()*1000), "time": now, **formatted}
                            _analysis_history.append(snap)
                            # persist to JSONL
                            try:
                                with open(_history_file, 'a') as f:
                                    import json as _json
                                    f.write(_json.dumps(snap) + "\n")
                                # also write Markdown lines (append to cumulative + daily file)
                                try:
                                    ts = snap.get("timestamp") or time.strftime("%Y-%m-%d %H:%M:%S")

                                    # 🔧 FIX: Include LLM analyses in MD file
                                    md_lines = [f"\n## {ts} (id: {snap.get('id')})\n"]
                                    md_lines.append(f"\n### Feature Analysis\n")
                                    md_lines.append(snap.get("feature_analysis") or "")
                                    md_lines.append("\n")

                                    # Add LLM analyses
                                    llm_analyses = snap.get("llm_analyses", {})
                                    if llm_analyses:
                                        md_lines.append("\n### LLM Analyses\n")
                                        for model_name, analysis_data in llm_analyses.items():
                                            md_lines.append(f"\n#### {model_name.upper()}\n")
                                            md_lines.append(f"**Status**: {analysis_data.get('status', 'unknown')}\n")
                                            if analysis_data.get('response_time'):
                                                md_lines.append(f"**Response Time**: {analysis_data.get('response_time'):.2f}s\n")
                                            md_lines.append(f"\n{analysis_data.get('analysis', 'No analysis available')}\n")

                                    md = "".join(md_lines)

                                    with open(_history_md_file, 'a') as mf:
                                        mf.write(md)
                                    day_name = time.strftime("%Y-%m-%d")
                                    day_path = os.path.join(_history_days_dir, f"{day_name}.md")
                                    with open(day_path, 'a') as df:
                                        df.write(md)
                                except Exception as _em:
                                    logger.warning("failed to append md history: %s", _em)
                            except Exception as _e:
                                logger.warning("failed to append history file: %s", _e)
                            total_duration = time.time() - analysis_start_time
                            logger.info(f"✅ Background LLM analysis completed in {total_duration:.2f}s")
                        except asyncio.TimeoutError:
                            logger.error(f"❌ Background LLM analysis timed out after {time.time() - analysis_start_time:.2f}s")
                        except Exception as e:
                            logger.error(f"❌ Background LLM analysis failed: {e}")
                            import traceback
                            logger.error(f"📋 Traceback: {traceback.format_exc()}")
                        finally:
                            # 🔧 CRITICAL: Always clear analyzing flag, no matter what
                            if anomaly_state_tracker.is_analyzing:
                                anomaly_state_tracker.is_analyzing = False
                                flag_duration = time.time() - analysis_start_time
                                logger.info(f"🔓 LLM analysis flag cleared after {flag_duration:.2f}s")
                            else:
                                logger.warning("⚠️ Flag was already cleared (unexpected)")

                    # Start background task without waiting
                    asyncio.create_task(background_llm_analysis())

                    result["llm"] = {"status": "triggered", "top_features": top_features}
                    _consecutive_anomalies = 0
                    _last_llm_trigger_time = now
                    _last_llm_top_features = top_features
        else:
            result["llm"] = {"status": "not_triggered"}

        return result
    except Exception as e:
        logger.exception("ingest error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stream")
async def stream_live_points():
    """Server-Sent Events stream of the latest aggregated live point.
    Previous implementation yielded only when len(live_buffer) grew, which stalls
    once the deque reaches its maxlen. Here we track the 'time' field of the last
    row (which equals aggregated_count) and emit whenever it changes.
    """
    async def event_generator():
        import asyncio as _asyncio
        last_time_seen = None
        sse_logger.info("client connected")
        try:
            while True:
                try:
                    if live_buffer:
                        row = live_buffer[-1]  # has t2_stat, anomaly, threshold, time
                        current_time_val = row.get("time")
                        if current_time_val != last_time_seen:
                            payload = json.dumps(row)
                            sse_logger.info("emit time=%s t2=%.4f anomaly=%s", current_time_val, row.get("t2_stat"), row.get("anomaly"))
                            yield f"data: {payload}\n\n"
                            last_time_seen = current_time_val
                    await _asyncio.sleep(1.0)  # Faster polling: 1s for quicker connection status update
                except Exception as e:
                    sse_logger.warning("generator loop error: %s", e)
                    break
        finally:
            sse_logger.info("client disconnected")
    # Add SSE-friendly headers (and CORS for dev)
    resp = StreamingResponse(event_generator(), media_type="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.post("/config/runtime")
async def update_runtime_config(payload: Dict[str, Any] = Body(...)):
    global LIVE_WINDOW_SIZE, consecutive_anomalies_required, decimation_N, llm_min_interval_seconds, live_buffer, _recent_raw_rows, feature_shift_min_interval_seconds, feature_shift_jaccard_threshold
    changes = {}
    # Update PCA window size and resize live buffer conservatively (preserve latest data)
    if "pca_window_size" in payload:
        LIVE_WINDOW_SIZE = int(payload["pca_window_size"])
        # Rebuild live_buffer to reflect new window size while preserving content
        try:
            prev = list(live_buffer)
        except Exception:
            prev = []
        live_buffer = deque(prev[-LIVE_WINDOW_SIZE:], maxlen=LIVE_WINDOW_SIZE)
        changes["pca_window_size"] = LIVE_WINDOW_SIZE
    # Update consecutive anomalies threshold
    if "fault_trigger_consecutive_step" in payload:
        consecutive_anomalies_required = int(payload["fault_trigger_consecutive_step"])
        changes["fault_trigger_consecutive_step"] = consecutive_anomalies_required
    # Update decimation and resize recent raw rows buffer to avoid starvation when N>1
    if "decimation_N" in payload:
        decimation_N = max(1, int(payload["decimation_N"]))
        try:
            prev_raw = list(_recent_raw_rows)
        except Exception:
            prev_raw = []
        _recent_raw_rows = deque(prev_raw[-decimation_N+1 if decimation_N>1 else 0:], maxlen=decimation_N)
        changes["decimation_N"] = decimation_N
    # Update LLM rate limit
    if "llm_min_interval_seconds" in payload:
        llm_min_interval_seconds = max(0, int(payload["llm_min_interval_seconds"]))
        # 🔧 CRITICAL FIX: Also update AnomalyStateTracker's min_llm_interval
        anomaly_state_tracker.min_llm_interval = llm_min_interval_seconds
        changes["llm_min_interval_seconds"] = llm_min_interval_seconds
        logger.info(f"✅ Updated LLM min interval to {llm_min_interval_seconds}s (both global and AnomalyStateTracker)")
    # Feature shift trigger knobs
    if "feature_shift_jaccard_threshold" in payload:
        feature_shift_jaccard_threshold = float(payload["feature_shift_jaccard_threshold"])
        changes["feature_shift_jaccard_threshold"] = feature_shift_jaccard_threshold
    if "feature_shift_min_interval_seconds" in payload:
        feature_shift_min_interval_seconds = int(payload["feature_shift_min_interval_seconds"])
        changes["feature_shift_min_interval_seconds"] = feature_shift_min_interval_seconds
    return {"status": "ok", "updated": changes}

@app.post("/config/baseline/reload")

@app.get("/config/baseline/reload")
async def reload_baseline_get():
    # Convenience GET to avoid Body disturbed errors from double-read clients
    return await reload_baseline(payload=None)

async def reload_baseline(payload: Dict[str, Any] = Body(None)):
    """Reload baseline means/std from stats/features_mean_std.csv (optionally a specific file).
    Returns the number of features loaded. Does not require server restart.
    """
    try:
        global _normal_stats
        stats_name = None
        if payload and isinstance(payload, dict):
            stats_name = payload.get("filename")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "stats", stats_name) if stats_name else os.path.join(base_dir, "stats", "features_mean_std.csv")
        df = _pd2.read_csv(path).set_index("feature")
        _normal_stats = df
        return {"status": "ok", "filename": os.path.basename(path), "features": int(len(_normal_stats))}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/metrics")
def metrics():
    return {
        "aggregated_count": _aggregated_count,
        "live_buffer": len(live_buffer),
        "decimation_N": decimation_N,
        "pca_window": LIVE_WINDOW_SIZE,
        "consecutive_anomalies_required": consecutive_anomalies_required,
        "llm_min_interval_seconds": llm_min_interval_seconds,
        "baseline_features": (int(len(_normal_stats)) if _normal_stats is not None else 0),
    }

@app.get("/preview/top6")
async def preview_top6():
    """Compute a quick top-6 comparison from the current live_buffer without triggering LLM.
    Returns { text, features } where text is the Top 6... block.
    """
    try:
        import pandas as _pd3
        if len(live_buffer) == 0:
            return {"status":"empty","text":"Top 6 Contributing Features (Fault vs Normal):\n(no live data)","features":[]}
        buf_df = _pd3.DataFrame(list(live_buffer))
        deltas = (buf_df.iloc[-1][FEATURE_COLUMNS] - buf_df[FEATURE_COLUMNS].mean()).abs().sort_values(ascending=False)
        topk = int(config.get("topkfeatures", 6))
        top_features = list(deltas.index[:topk])
        series = {feat: buf_df[feat].tail(LIVE_WINDOW_SIZE).tolist() for feat in top_features}
        text = build_live_feature_comparison(series)
        return {"status":"ok","text": text, "features": top_features}
    except Exception as e:
        return {"status":"error","error": str(e)}


@app.post("/config/alpha")
async def update_alpha(payload: Dict[str, Any] = Body(...)):
    # Update anomaly_threshold (alpha) and recompute T2 threshold without retrain
    try:
        new_alpha = float(payload.get("anomaly_threshold"))
        if not (0 < new_alpha < 1):
            raise ValueError("alpha must be between 0 and 1")
        pca_model.alpha = new_alpha
        pca_model.set_t2_threshold()
        return {"status": "ok", "alpha": new_alpha, "t2_threshold": float(pca_model.t2_threshold)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/retrain")
async def retrain_pca(payload: Dict[str, Any] = Body(...)):
    """Retrain PCA model with new training data."""
    try:
        import pandas as pd
        from model import FaultDetectionModel

        # Get training file path
        training_file = payload.get("training_file", "live_fault0.csv")
        training_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", training_file)

        if not os.path.exists(training_path):
            raise ValueError(f"Training file not found: {training_path}")

        # Load new training data
        train_df = pd.read_csv(training_path)
        if "time" in train_df.columns:
            train_df = train_df.drop(columns=["time"])

        # Validate columns
        missing_cols = [c for c in FEATURE_COLUMNS if c not in train_df.columns]
        if missing_cols:
            raise ValueError(f"Training data missing expected columns: {missing_cols}")

        train_df = train_df[FEATURE_COLUMNS]

        # Create new PCA model
        global pca_model
        new_pca_model = FaultDetectionModel(n_components=0.9, alpha=config.get("anomaly_threshold", 0.01))
        new_pca_model.fit(train_df)

        # Replace global model
        pca_model = new_pca_model

        # Clear live buffer to avoid anomalies from old threshold calculations
        global live_buffer, _consecutive_anomalies, _aggregated_count
        live_buffer.clear()
        _consecutive_anomalies = 0
        # Don't reset _aggregated_count to maintain time continuity

        print(f"✅ PCA model retrained with {len(train_df)} data points from {training_file}")
        print(f"🧹 Cleared live buffer to avoid false anomalies from old threshold")

        return {
            "status": "success",
            "message": f"PCA model retrained with {len(train_df)} data points",
            "n_components": int(pca_model.pca.n_components_),
            "t2_threshold": float(pca_model.t2_threshold),
            "training_file": training_file
        }

    except Exception as e:
        print(f"❌ PCA retrain failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/status")
def status():
    return {"running": True}

@app.get("/analysis/latest")
def get_latest_analysis():
    """Return the most recent LLM analysis result (triggered by /ingest in ULTRA START mode).
    This endpoint allows the frontend to poll for new analysis results without needing to call /explain.
    """
    global _last_analysis_result
    if _last_analysis_result:
        return _last_analysis_result
    else:
        # Return empty structure if no analysis has been run yet
        return {
            "timestamp": "",
            "feature_analysis": "No analysis available yet. Waiting for anomaly detection...",
            "llm_analyses": {},
            "performance_summary": {}
        }

@app.get("/analysis/history")
def analysis_history(limit: int = 10):
    """
    Return last N items with smart loading strategy:
    1. First load from in-memory (real-time, most recent)
    2. If not enough, supplement from disk log (historical)
    3. Combine both to reach requested limit
    """
    import json as _json

    # STEP 1: Get from in-memory queue (most recent, real-time)
    memory_items = list(_analysis_history)  # Max 6 items by default (deque maxlen=6)

    # STEP 2: If we have enough in memory, return them
    if len(memory_items) >= limit:
        logger.info(f"📊 Load History: Returning {limit} items from memory (have {len(memory_items)} total)")
        return {"items": memory_items[-limit:]}

    # STEP 3: Need more items - read from disk to supplement
    disk_items = []
    needed = limit - len(memory_items)

    logger.info(f"📊 Load History: Have {len(memory_items)} in memory, need {needed} more from disk")

    try:
        if os.path.exists(_history_file):
            # Get IDs of items already in memory to avoid duplicates
            memory_ids = {str(item.get('id', '')) for item in memory_items if item.get('id')}

            # Read last (needed * 2) lines from disk to ensure we get enough unique items
            # (multiply by 2 as buffer in case some are duplicates)
            read_limit = needed * 2

            with open(_history_file, 'rb') as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                block = 4096
                buf = b""
                lines = []

                # Read file backwards until we have enough lines
                while size > 0 and len(lines) <= read_limit:
                    step = block if size - block > 0 else size
                    size -= step
                    f.seek(size)
                    buf = f.read(step) + buf
                    lines = buf.split(b"\n")

                raw = [x for x in lines if x.strip()]

                # Parse each line, skip duplicates and malformed entries
                for line in reversed(raw):  # Read newest first
                    if len(disk_items) >= needed:
                        break

                    try:
                        if line.strip():
                            item = _json.loads(line)
                            item_id = str(item.get('id', ''))

                            # Skip if already in memory
                            if item_id and item_id not in memory_ids:
                                disk_items.insert(0, item)  # Insert at beginning to maintain order
                    except _json.JSONDecodeError:
                        continue  # Skip malformed lines

            logger.info(f"📊 Load History: Loaded {len(disk_items)} unique items from disk")
        else:
            logger.info(f"📊 Load History: No disk log file found at {_history_file}")

    except Exception as e:
        logger.warning(f"⚠️ Failed to read disk history: {e}")

    # STEP 4: Combine memory (newest) + disk (older historical)
    # Memory items are already the most recent, disk items supplement from history
    combined = memory_items + disk_items[:needed]

    logger.info(f"📊 Load History: Returning {len(combined)} items ({len(memory_items)} from memory + {len(disk_items[:needed])} from disk)")

    return {"items": combined[-limit:]}

@app.get("/analysis/download/{date}")
def download_analysis_by_date(date: str):
    """
    Download analysis markdown file for a specific date.
    Date format: YYYY-MM-DD
    Returns: FileResponse with markdown file
    """
    try:
        # Construct file path
        history_dir = Path("diagnostics/analysis_history")
        file_path = history_dir / f"{date}.md"

        # Check if file exists
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"No analysis file found for date {date}")

        # Return file
        return FileResponse(
            path=str(file_path),
            media_type="text/markdown",
            filename=f"analysis_{date}.md"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")

@app.post("/reset_lmstudio")
async def reset_lmstudio():
    """
    Reset LMStudio connection and clear rate limiting.
    This endpoint:
    1. Clears rate limiting timer (allows immediate next request)
    2. Logs the reset action
    3. Returns status message
    """
    try:
        logger.info("🔄 LMStudio connection reset requested")

        # Reset rate limiting timer to allow immediate next request
        anomaly_state_tracker.last_llm_request_time = 0
        logger.info("✅ Rate limiting cleared - next request will be allowed immediately")

        # Log current state
        logger.info(f"📊 AnomalyStateTracker state:")
        logger.info(f"   - min_llm_interval: {anomaly_state_tracker.min_llm_interval}s")
        logger.info(f"   - last_llm_request_time reset to: 0")
        logger.info(f"   - check_interval: {anomaly_state_tracker.check_interval}s")

        return {
            "status": "success",
            "message": "LMStudio Connection Reset Complete",
            "details": f"Rate limiting cleared. Next request will be allowed immediately. Min interval: {anomaly_state_tracker.min_llm_interval}s",
            "rate_limit_cleared": True,
            "min_llm_interval": anomaly_state_tracker.min_llm_interval
        }

    except Exception as e:
        logger.error(f"❌ Error resetting LMStudio connection: {e}")
        return {
            "status": "error",
            "message": "Reset Failed",
            "details": str(e)
        }

@app.get("/api/logs/sse")
def get_sse_log(lines: int = 200):
    """Return last N lines of SSE log"""
    try:
        log_file = Path("logs/sse.log")
        if not log_file.exists():
            return {"log": "(SSE log file not found - no streaming events yet)"}

        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            log_content = ''.join(last_lines)

        return {"log": log_content}
    except Exception as e:
        return {"log": f"Error reading SSE log: {str(e)}"}

@app.get("/api/logs/ingest")
def get_ingest_log(lines: int = 200):
    """Return last N lines of ingest log"""
    try:
        log_file = Path("logs/ingest.log")
        if not log_file.exists():
            return {"log": "(Ingest log file not found - no data ingestion yet)"}

        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            log_content = ''.join(last_lines)

        return {"log": log_content}
    except Exception as e:
        return {"log": f"Error reading ingest log: {str(e)}"}

@app.get("/analysis/item/{item_id}")
def analysis_item(item_id: int):
    try:
        # first check memory
        for it in reversed(_analysis_history):
            if int(it.get("id", 0)) == int(item_id):
                return it
        # then scan file
        if os.path.exists(_history_file):
            import json as _json
            with open(_history_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    obj = _json.loads(line)
                    if int(obj.get("id",0)) == int(item_id):
                        return obj
    except Exception as e:
        return {"status":"error","error":str(e)}
    return {"status":"not_found"}


@app.post("/analysis/enhance")
async def enhance_snapshot(payload: dict = Body(...)):
    """
    On-demand enhancement of a saved snapshot using the AI Agent / RAG system.
    Input: { analysis_id: int, force: bool=false }
    Returns: { analysis_id, enhanced_analysis, cached }
    """
    try:
        aid = payload.get("analysis_id")
        if aid is None:
            raise HTTPException(status_code=400, detail="analysis_id is required")
        force = bool(payload.get("force", False))

        # Resolve snapshot (reuse logic similar to analysis_item)
        snap = None
        for it in reversed(_analysis_history):
            if int(it.get("id", 0)) == int(aid):
                snap = it
                break
        if snap is None and os.path.exists(_history_file):
            import json as _json
            with open(_history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    obj = _json.loads(line)
                    if int(obj.get("id", 0)) == int(aid):
                        snap = obj
                        break
        if snap is None:
            raise HTTPException(status_code=404, detail="snapshot not found")

        # If already enhanced and not forced, return cached
        existing = (((snap.get("ai_agent_enhancement") or {}).get("enhanced_analysis")) or "")
        if existing and not force:
            return {"analysis_id": aid, "enhanced_analysis": existing, "cached": True}

        # Build anomaly data as best-effort from snapshot
        import re as _re
        feature_text = snap.get("feature_analysis") or snap.get("feature_comparison") or ""
        factors = []
        try:
            for line in feature_text.splitlines():
                m = _re.match(r"\s*\d+\.\s*([^:]+):", line)
                if m:
                    name = m.group(1).strip()
                    if name:
                        factors.append(name)
            factors = factors[:6]
        except Exception:
            factors = []

        formatted = {
            "timestamp": snap.get("timestamp") or snap.get("time"),
            "feature_analysis": feature_text,
            "llm_analyses": snap.get("llm_analyses") or {}
        }
        anomaly_data = {
            'timestamp': formatted["timestamp"],
            'contributing_factors': factors
        }

        # 🔧 FIX: Removed AI Agent enhancement to speed up response time
        # Return empty enhancement
        enhanced_text = ""
        logger.info("⚠️ AI Agent enhancement disabled for performance")

        return {"analysis_id": aid, "enhanced_analysis": enhanced_text, "cached": False}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("/analysis/enhance error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

# === Pinned Chat and Operator Context (Stage 1 JSONL) ===
from fastapi import Body

@app.post("/chat_simple")  # 🔧 RENAMED: Avoid conflict with enhanced /chat endpoint
async def chat_simple(payload: dict = Body(...)):
    """
    DEPRECATED: Simple pinned chat endpoint (replaced by enhanced /chat endpoint below).
    This endpoint is kept for backward compatibility but should not be used.
    Use /chat endpoint instead which supports RAG, LLM models, and intelligent responses.

    - mode: 'pinned' | 'live' (default 'pinned')
    - analysis_id: required when mode='pinned'
    - query: operator question
    - session_id: optional
    Returns an answer grounded in the referenced snapshot without mutating it.
    """
    try:
        mode = str(payload.get("mode", "pinned")).lower()
        query = (payload.get("query") or "").strip()
        session_id = payload.get("session_id")
        if not query:
            raise HTTPException(status_code=400, detail="query is required")

        # Resolve snapshot
        snap = None
        if mode == "pinned":
            aid = payload.get("analysis_id")
            if aid is None:
                raise HTTPException(status_code=400, detail="analysis_id is required for pinned mode")
            # Reuse analysis_item logic
            try:
                for it in reversed(_analysis_history):
                    if int(it.get("id", 0)) == int(aid):
                        snap = it
                        break
                if snap is None and os.path.exists(_history_file):
                    import json as _json
                    with open(_history_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if not line.strip():
                                continue
                            obj = _json.loads(line)
                            if int(obj.get("id", 0)) == int(aid):
                                snap = obj
                                break
            except Exception as _e:
                pass
            if snap is None:
                raise HTTPException(status_code=404, detail="snapshot not found")
        else:
            # live: get latest
            if len(_analysis_history) > 0:
                snap = _analysis_history[-1]
            elif os.path.exists(_history_file):
                try:
                    with open(_history_file, 'rb') as f:
                        f.seek(0, os.SEEK_END)
                        size = f.tell()
                        block = 4096
                        buf = b""
                        while size > 0:
                            step = block if size - block > 0 else size
                            size -= step
                            f.seek(size)
                            buf = f.read(step) + buf
                            lines = [x for x in buf.split(b"\n") if x.strip()]
                            if len(lines) >= 1:
                                import json as _json
                                snap = _json.loads(lines[-1])
                                break
                except Exception:
                    pass
            if snap is None:
                raise HTTPException(status_code=404, detail="no snapshots available")

        # Build grounded context
        aid = snap.get("id")
        ts = snap.get("timestamp") or snap.get("time")
        feature_text = snap.get("feature_analysis") or snap.get("feature_comparison") or ""
        enhanced = (((snap.get("ai_agent_enhancement") or {}).get("enhanced_analysis")) or "")
        llm_analyses = snap.get("llm_analyses") or {}
        some_llm = None
        for k, v in llm_analyses.items():
            if v and v.get("analysis"):
                some_llm = f"[{k}]\n" + v.get("analysis")
                break

        # Build a chat-style prompt so the answer can adapt to operator feedback
        # Include history if provided
        history = payload.get("history") or []
        history_lines = []
        try:
            for m in history[-8:]:
                role = (m.get('role') or 'user')[:12]
                content = (m.get('content') or '').strip()
                if content:
                    history_lines.append(f"- {role}: {content}")
        except Exception:
            pass
        history_text = "\n".join(history_lines)

        # Concatenate all model analyses (not just the first) for richer grounding
        all_models_text = []
        for mk, mv in llm_analyses.items():
            if mv and mv.get('analysis'):
                all_models_text.append(f"[{mk}]\n{mv.get('analysis')}")
        models_text = "\n\n".join(all_models_text)
        # Trim to keep prompt reasonable
        if len(models_text) > 3000:
            models_text = models_text[:3000] + "\n... (truncated)"

        # Compose user prompt
        prompt_parts = [
            "Role: You are a chemical plant process engineer and also a chemical plant operator specializing in the Tennessee Eastman Process (TEP). "
            "Use rigorous, concise, stepwise reasoning grounded in the snapshot, anomaly signals, and operator feedback.",
            f"Snapshot id {aid} at {ts}.",
        ]
        if feature_text:
            prompt_parts.append("Top features and comparison:\n" + feature_text)
        if enhanced:
            prompt_parts.append("Enhanced analysis (AI agent):\n" + enhanced)
        if models_text:
            prompt_parts.append("Other model analyses:\n" + models_text)
        if history_text:
            prompt_parts.append("Conversation so far:\n" + history_text)
        prompt_parts.append("Operator's new message:\n" + query)
        prompt_parts.append(
            "Task: Update the root cause assessment now. Provide three numbered hypotheses "
            "(Root Cause 1/2/3) with 1-2 sentences each, explain what changed given the operator's "
            "new evidence, and end with a short 'Next checks' bullet list. If the operator ruled out "
            "an item, acknowledge it and propose alternatives.")
        user_prompt = "\n\n".join(prompt_parts)

        # Try a live LLM update (Gemini if available); fall back to deterministic summary
        generated = None
        try:
            if "gemini" in multi_llm_client.clients:
                generated = await multi_llm_client._query_gemini(SYSTEM_MESSAGE, user_prompt)
        except Exception as _e:
            logger.warning("/chat LLM generate failed: %s", _e)
            generated = None

        if generated and isinstance(generated, str) and generated.strip():
            answer = generated.strip()
        else:
            # Fallback deterministic summary
            body_sections = []
            if enhanced:
                body_sections.append(enhanced)
            elif some_llm:
                body_sections.append(some_llm)
            if feature_text:
                body_sections.append("Top features and comparison:\n" + feature_text)
            preface = f"Pinned to snapshot id={aid} at {ts}.\nYour question: {query}\n\n"
            answer = preface + ("\n\n".join(body_sections) or "Context recorded. No detailed analysis text available in this snapshot.")

        # Append operator context (length only; full answer stored on client side)
        _append_operator_context({
            "type": "chat",
            "mode": mode,
            "analysis_id": aid,
            "session_id": session_id,
            "query": query,
            "answer_len": len(answer)
        })

        return {
            "answer": answer,
            "analysis_id": aid,
            "used_snapshot": True,
            "mode": mode
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("/chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/context/ruled_out")
def context_ruled_out(payload: dict = Body(...)):
    try:
        aid = payload.get("analysis_id")
        hyp = payload.get("hypothesis_id")
        reason = payload.get("reason")
        operator = payload.get("operator")
        if aid is None or not hyp:
            raise HTTPException(status_code=400, detail="analysis_id and hypothesis_id are required")
        _append_operator_context({
            "type": "ruled_out",
            "analysis_id": aid,
            "hypothesis_id": hyp,
            "reason": reason,
            "operator": operator
        })
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("/context/ruled_out error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/context/notes")
def context_notes(payload: dict = Body(...)):
    try:
        aid = payload.get("analysis_id")
        note = payload.get("note")
        operator = payload.get("operator")
        session_id = payload.get("session_id")
        if aid is None or not note:
            raise HTTPException(status_code=400, detail="analysis_id and note are required")
        _append_operator_context({
            "type": "note",
            "analysis_id": aid,
            "note": note,
            "operator": operator,
            "session_id": session_id
        })
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("/context/notes error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/last_analysis")
def last_analysis():
    if _last_analysis_result is None:
        return {"status": "none"}
    return _last_analysis_result

# === Model Control Endpoints ===

@app.post("/models/toggle")
async def toggle_model(payload: dict):
    """Toggle a model on/off at runtime"""
    try:
        model_name = payload.get("model_name")
        enabled = payload.get("enabled", False)

        if not model_name:
            raise HTTPException(status_code=400, detail="model_name is required")

        result = multi_llm_client.toggle_model(model_name, enabled)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except Exception as e:
        logger.exception("Model toggle error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/status")
def get_model_status():
    """Get detailed status of all models"""
    try:
        return multi_llm_client.get_model_status()
    except Exception as e:
        logger.exception("Model status error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/models/reset_usage")
def reset_usage_stats():
    """Reset usage statistics"""
    try:
        return multi_llm_client.reset_usage_stats()
    except Exception as e:
        logger.exception("Reset usage error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

# === Cost Protection Endpoints ===

@app.get("/session/status")
def get_session_status():
    """Get current premium session status and remaining time"""
    try:
        return multi_llm_client.get_session_status()
    except Exception as e:
        logger.exception("Session status error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/session/extend")
async def extend_session(payload: dict):
    """Extend premium session by additional minutes"""
    try:
        additional_minutes = payload.get("additional_minutes", 30)
        result = multi_llm_client.extend_premium_session(additional_minutes)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except Exception as e:
        logger.exception("Session extend error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/session/shutdown")
def force_shutdown_premium():
    """Manually force shutdown of premium models"""
    try:
        return multi_llm_client.force_shutdown_premium()
    except Exception as e:
        logger.exception("Force shutdown error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/session/cancel_auto_shutdown")
def cancel_auto_shutdown():
    """Cancel the auto-shutdown timer"""
    try:
        multi_llm_client.cancel_auto_shutdown()
        return {"success": True, "message": "Auto-shutdown cancelled"}
    except Exception as e:
        logger.exception("Cancel auto-shutdown error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/session/set_auto_shutdown")
async def set_auto_shutdown(payload: dict):
    """Enable or disable auto-shutdown feature"""
    try:
        enabled = payload.get("enabled", True)
        multi_llm_client.set_auto_shutdown_enabled(enabled)
        return {"success": True, "auto_shutdown_enabled": enabled}
    except Exception as e:
        logger.exception("Set auto-shutdown error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/simulation/auto_stop_status")
def get_simulation_auto_stop_status():
    """Check if simulation should be auto-stopped due to cost protection"""
    global _simulation_auto_stopped
    return {
        "auto_stopped": _simulation_auto_stopped,
        "message": "Simulation auto-stopped due to premium model shutdown" if _simulation_auto_stopped else "Simulation running normally"
    }

@app.post("/simulation/reset_auto_stop")
def reset_simulation_auto_stop():
    """Reset the simulation auto-stop flag"""
    global _simulation_auto_stopped
    _simulation_auto_stopped = False
    return {"success": True, "message": "Auto-stop flag reset"}


    # Combine all results into a single string
    return "The top feature changes are\n" + "\n".join(comparison_results)


# Health check endpoints
@app.get("/")
def read_root():
    return {"message": "FaultExplainer Multi-LLM API", "status": "running"}

# Static file serving for P&ID diagram
@app.get("/static/tep_flowsheet.png")
async def get_tep_flowsheet():
    """Serve the TEP P&ID flowsheet diagram"""
    file_path = Path(__file__).parent / "tep_flowsheet.png"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="P&ID diagram not found")
    return FileResponse(file_path, media_type="image/png")

@app.get("/health/lmstudio")
async def check_lmstudio_health():
    """Check LMStudio health status"""
    try:
        import requests

        # Quick connection test
        response = requests.get("http://127.0.0.1:1234/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json().get("data", [])
            return {
                "status": "healthy",
                "models_available": len(models),
                "models": [m["id"] for m in models[:3]]  # Show first 3 models
            }
        else:
            return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}

    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/restart/lmstudio")
async def restart_lmstudio_suggestion():
    """Provide LMStudio restart suggestions"""
    return {
        "message": "LMStudio restart required",
        "steps": [
            "1. Open LMStudio application",
            "2. Go to Server tab",
            "3. Stop current server if running",
            "4. Select model and click 'Start Server'",
            "5. Ensure server runs on 127.0.0.1:1234"
        ],
        "health_check_url": "/health/lmstudio"
    }

# === Anomaly State Change Detection Endpoint ===

@app.post("/check_anomaly_change")
async def check_anomaly_change(request: ExplainationRequest):
    """
    Check if anomaly state has changed enough to warrant new LLM analysis

    Returns:
        {
            "should_analyze": bool,
            "reason": str,
            "last_check_time": float,
            "time_since_last": float
        }
    """
    try:
        # Extract anomaly features from request data
        anomaly_features = []
        anomaly_data = {}

        for feature, values in request.data.items():
            if isinstance(values, list) and len(values) > 0:
                anomaly_features.append(feature)
                anomaly_data[feature] = values

        # Check if state has changed
        has_changed, reason = anomaly_state_tracker.has_state_changed(anomaly_features, anomaly_data)

        import time
        current_time = time.time()
        time_since_last = current_time - anomaly_state_tracker.last_check_time

        result = {
            "should_analyze": has_changed,
            "reason": reason,
            "last_check_time": anomaly_state_tracker.last_check_time,
            "time_since_last": round(time_since_last, 2),
            "current_anomaly_count": len(anomaly_features),
            "previous_anomaly_count": len(anomaly_state_tracker.last_anomaly_features)
        }

        logger.info(f"🔍 Anomaly change check: {result}")

        return result

    except Exception as e:
        logger.exception("Anomaly change check error: %s", e)
        return {
            "should_analyze": True,  # Default to analyzing on error
            "reason": f"Error checking state: {str(e)}",
            "error": str(e)
        }

@app.post("/explain", response_model=None)
async def explain(request: ExplainationRequest):
    try:
        logger.info(f"explain start id=%s file=%s - Using LOCAL LLM (Claude Desktop/Codex)", request.id, request.file)

        # 🔧 CRITICAL FIX: Check LLM request frequency limit BEFORE processing
        can_send, reason = anomaly_state_tracker.can_send_llm_request()
        if not can_send:
            logger.warning(f"🚫 LLM request blocked: {reason}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "reason": reason,
                    "retry_after": anomaly_state_tracker.min_llm_interval
                }
            )

        # Mark that we're sending an LLM request
        anomaly_state_tracker.mark_llm_request_sent()
        logger.info(f"✅ LLM request allowed: {reason}")

        # 🔧 REMOVED: Local LLM integration code that was causing delays
        # This code tried to import non-existent claude_desktop_integration module
        # and wasted time on every request. Now directly using multi_llm_client.

        # 🚀 触发独立LLM系统分析
        if independent_llm_system:
            try:
                # 准备异常数据
                anomaly_data = {
                    'data': request.data,
                    'file': request.file,
                    'id': request.id,
                    'timestamp': datetime.now().isoformat(),
                    'anomaly_score': 0.05  # 模拟异常分数
                }

                # 异步触发独立分析（不等待结果）
                asyncio.create_task(independent_llm_system.trigger_analysis(anomaly_data))
                logger.info("🔥 Independent LLM analysis triggered")
            except Exception as e:
                logger.warning(f"⚠️ Failed to trigger independent LLM analysis: {e}")

        # Generate feature comparison
        comparison_result = generate_feature_comparison(request.data, request.file)
        user_prompt = f"{PROMPT_SELECT}\n{comparison_result}"

        logger.info("feature comparison prepared")

        # Extract fault features for RAG enhancement
        fault_features = []
        fault_data = {"file": request.file, "id": request.id}

        # Try to extract feature names from the comparison result
        try:
            # Simple extraction of feature names from comparison text
            import re
            feature_matches = re.findall(r'Feature:\s*([^,\n]+)', comparison_result)
            fault_features = [f.strip() for f in feature_matches[:6]]  # Top 6 features
        except Exception as e:
            logger.warning(f"Could not extract fault features: {str(e)}")

        # Get analysis from all enabled models with RAG enhancement
        llm_results = await multi_llm_client.get_analysis_from_all_models(
            system_message=SYSTEM_MESSAGE,
            user_prompt=user_prompt,
            fault_features=fault_features,
            fault_data=fault_data
        )

        # Format comparative results with sensor data
        formatted_results = multi_llm_client.format_comparative_results(
            results=llm_results,
            feature_comparison=comparison_result,
            sensor_data=request.data  # Include all sensor data in snapshot
        )

        # 🔍 DEBUG: Log formatted results structure
        logger.info(f"📊 Formatted results keys: {formatted_results.keys()}")
        logger.info(f"📊 LLM analyses keys: {formatted_results.get('llm_analyses', {}).keys()}")
        for model_name, analysis_data in formatted_results.get('llm_analyses', {}).items():
            logger.info(f"📊 {model_name} - status: {analysis_data.get('status')}, has_analysis: {bool(analysis_data.get('analysis'))}")

        # 🔧 FIX: 保存原始LLM分析到各自的MD文件 (for /explain endpoint)
        # Removed AI Agent enhancement to speed up response time
        try:
            llm_analyses = formatted_results.get("llm_analyses", {})
            for model_name, analysis_data in llm_analyses.items():
                if analysis_data.get("status") == "success":
                    # 🔧 CRITICAL FIX: 正确的数据结构映射
                    corrected_data = {
                        "response": analysis_data.get("analysis", "No response available"),
                        "analysis_duration": analysis_data.get("response_time", 0),
                        "status": analysis_data.get("status", "unknown"),
                        "timestamp": datetime.now().isoformat()
                    }
                    enhanced_md_saver.save_standard_analysis(
                        model_name,
                        corrected_data,
                        fault_features
                    )
                    logger.info(f"✅ Saved {model_name} analysis to MD file (/explain)")
        except Exception as save_error:
            logger.warning(f"⚠️ Failed to save individual LLM analyses to MD (/explain): {save_error}")

        # 🔧 NEW FIX: Save to analysis history (for "Show Last 5 Analyses" feature)
        try:
            import time
            now = datetime.now().isoformat()
            snap = {
                "id": int(time.time() * 1000),
                "time": now,
                **formatted_results
            }
            _analysis_history.append(snap)

            # Persist to JSONL file
            with open(_history_file, 'a') as f:
                import json as _json
                f.write(_json.dumps(snap) + "\n")

            logger.info(f"✅ Saved analysis to history (id: {snap['id']})")
        except Exception as history_error:
            logger.warning(f"⚠️ Failed to save to analysis history: {history_error}")

        logger.info("multi-llm analysis completed id=%s", request.id)

        # Return JSON response instead of streaming for comparative display
        return JSONResponse(content=formatted_results)

    except Exception as e:
        logger.exception("explain endpoint error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/explain/gemini", response_model=None)
async def explain_gemini(request: ExplainationRequest):
    """Get analysis from Gemini only"""
    try:
        logger.info(f"explain_gemini start id=%s file=%s", request.id, request.file)

        # Generate feature comparison
        comparison_result = generate_feature_comparison(request.data, request.file)
        user_prompt = f"{PROMPT_SELECT}\n{comparison_result}"

        # Get analysis from Gemini only
        if "gemini" in multi_llm_client.enabled_models:
            response = await multi_llm_client._query_gemini(SYSTEM_MESSAGE, user_prompt)
            result = {
                "gemini": {
                    "response": response,
                    "response_time": 0,
                    "status": "success"
                }
            }
        else:
            result = {
                "gemini": {
                    "response": "Gemini is not enabled",
                    "response_time": 0,
                    "status": "disabled"
                }
            }

        formatted_results = multi_llm_client.format_comparative_results(
            results=result,
            feature_comparison=comparison_result,
            sensor_data=request.data  # Include all sensor data in snapshot
        )

        return JSONResponse(content=formatted_results)

    except Exception as e:
        logger.exception("explain_gemini endpoint error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/independent/{model_name}", response_model=None)
async def independent_analysis(model_name: str, request: ExplainationRequest):
    """独立模型分析 - 每个模型管理自己的状态和时间周期"""
    try:
        logger.info(f"independent_{model_name} start id=%s file=%s", request.id, request.file)

        # Generate feature comparison
        comparison_result = generate_feature_comparison(request.data, request.file)
        user_prompt = f"{PROMPT_SELECT}\n{comparison_result}"

        # Extract fault features
        fault_features = []
        try:
            import re
            feature_matches = re.findall(r'Feature:\s*([^,\n]+)', comparison_result)
            fault_features = [f.strip() for f in feature_matches[:6]]
        except Exception as e:
            logger.warning(f"Could not extract fault features: {str(e)}")

        # 使用独立系统进行分析
        result = await independent_llm_system.analyze_with_model(
            model_name=model_name,
            system_message=SYSTEM_MESSAGE,
            user_prompt=user_prompt,
            fault_features=fault_features
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.exception(f"independent_{model_name} endpoint error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/independent/status", response_model=None)
async def get_independent_status():
    """获取所有独立模型的状态 + 包含 llm_min_interval_seconds 供前端轮询使用"""
    try:
        status = independent_llm_system.get_all_status()
        # 🔧 FIX: Add llm_min_interval_seconds to status response for frontend polling
        status["llm_min_interval_seconds"] = llm_min_interval_seconds
        return JSONResponse(content=status)
    except Exception as e:
        logger.exception("get_independent_status error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/independent/{model_name}/freeze", response_model=None)
async def freeze_model_display(model_name: str):
    """冻结指定模型的显示"""
    try:
        independent_llm_system.freeze_model_display(model_name)
        return JSONResponse(content={"status": "frozen", "model": model_name})
    except Exception as e:
        logger.exception(f"freeze_{model_name} error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/independent/{model_name}/unfreeze", response_model=None)
async def unfreeze_model_display(model_name: str):
    """解冻指定模型的显示"""
    try:
        independent_llm_system.unfreeze_model_display(model_name)
        return JSONResponse(content={"status": "unfrozen", "model": model_name})
    except Exception as e:
        logger.exception(f"unfreeze_{model_name} error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send_message", response_model=MessageResponse)
async def send_message(request: MessageRequest):
    try:
        return StreamingResponse(
            ChatModelCompletion(messages=request.data, msg_id=f"reply-{request.id}"),
            media_type="text/event-stream",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# RAG Knowledge Base Management Endpoints

@app.post("/rag/initialize")
async def initialize_rag_knowledge_base(force_reindex: bool = False):
    """Initialize or update the RAG knowledge base"""
    try:
        result = multi_llm_client.initialize_knowledge_base(force_reindex=force_reindex)
        return result
    except Exception as e:
        logger.exception("RAG initialization error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rag/status")
async def get_rag_status():
    """Get RAG system status and statistics"""
    try:
        status = multi_llm_client.get_rag_status()
        return status
    except Exception as e:
        logger.exception("RAG status error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rag/search")
async def search_knowledge_base(query: str, n_results: int = 5):
    """Search the knowledge base for relevant information"""
    try:
        results = multi_llm_client.search_knowledge_base(query, n_results=n_results)
        return results
    except Exception as e:
        logger.exception("RAG search error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

# === AI Agent Knowledge Service Endpoints ===

@app.get("/ai_agent/status")
async def get_ai_agent_status():
    """Get AI Agent Knowledge service status"""
    try:
        return ai_agent_service.get_service_status()
    except Exception as e:
        logger.exception("AI Agent status error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai_agent/test")
async def test_ai_agent_enhancement(payload: dict):
    """Test AI Agent enhancement with sample data - DISABLED for performance"""
    return {
        "status": "disabled",
        "message": "AI Agent enhancement has been disabled to improve response time",
        "recommendation": "Use direct LLM analysis instead"
    }


# === Interactive Chat Endpoints ===

@app.get("/analysis/item/{analysis_id}")
async def get_analysis_item(analysis_id: str):
    """Get specific analysis snapshot by ID for interactive chat"""
    try:
        history_file = Path("diagnostics/analysis_history.jsonl")

        if not history_file.exists():
            raise HTTPException(status_code=404, detail="Analysis history file not found")

        # Search for analysis by ID
        with open(history_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        snapshot = json.loads(line)
                        if str(snapshot.get('id')) == str(analysis_id):
                            logger.info(f"✅ Found analysis snapshot: {analysis_id}")
                            return snapshot
                    except json.JSONDecodeError:
                        continue

        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving analysis {analysis_id}: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat_endpoint(request: dict):
    """Enhanced interactive chat endpoint with RAG, sensor data, and model selection"""
    try:
        mode = request.get('mode', 'live')
        query = request.get('query', '')
        analysis_id = request.get('analysis_id')
        history = request.get('history', [])

        # 🔧 CRITICAL FIX: Use first enabled model from config (not hardcoded lmstudio)
        default_model = multi_llm_client.enabled_models[0] if multi_llm_client.enabled_models else 'anthropic'
        model_choice = request.get('model', default_model)

        logger.info(f"💬 Chat request - Mode: {mode}, Model: {model_choice}, Query: {query[:50]}...")

        # Build context from analysis if pinned
        context = ""
        sensor_data_summary = ""
        snapshot = None

        if mode == "pinned" and analysis_id:
            try:
                # Load analysis snapshot
                snapshot = await get_analysis_item(analysis_id)

                # Build context from snapshot
                context = f"**Analysis ID**: {analysis_id}\n\n"

                # Add timestamp
                if 'timestamp' in snapshot or 'time' in snapshot:
                    timestamp = snapshot.get('timestamp') or snapshot.get('time')
                    context += f"**Timestamp**: {timestamp}\n\n"

                # Add feature analysis
                if 'feature_analysis' in snapshot:
                    context += f"**Feature Analysis**:\n{snapshot['feature_analysis']}\n\n"

                # Add LLM analyses
                if 'llm_analyses' in snapshot:
                    for model, data in snapshot['llm_analyses'].items():
                        if isinstance(data, dict) and 'analysis' in data:
                            context += f"**{model.upper()} Analysis**:\n{data['analysis']}\n\n"

                # Add sensor data summary (if available in snapshot)
                if 'sensor_data' in snapshot:
                    sensor_data_summary = "\n**Sensor Data Summary** (52 sensor features captured at fault time):\n"
                    sensor_data = snapshot['sensor_data']

                    # Show all available sensor variables with statistics
                    sensor_count = 0
                    for var_name, values in sensor_data.items():
                        if isinstance(values, list) and len(values) > 0:
                            avg_val = sum(values) / len(values)
                            min_val = min(values)
                            max_val = max(values)
                            # Show variable with min, avg, max for better context
                            sensor_data_summary += f"- {var_name}: min={min_val:.2f}, avg={avg_val:.2f}, max={max_val:.2f}\n"
                            sensor_count += 1

                    sensor_data_summary += f"\n(Total {sensor_count} sensor features captured)\n"
                    context += sensor_data_summary

                logger.info(f"📋 Loaded context for analysis {analysis_id} ({len(context)} chars)")

            except Exception as e:
                logger.warning(f"⚠️ Could not load analysis {analysis_id}: {e}")
                context = f"Analysis {analysis_id} context unavailable.\n\n"

        # Search RAG knowledge base for relevant information
        rag_context = ""
        knowledge_sources = []
        if knowledge_manager and query:
            try:
                relevant_chunks = knowledge_manager.search_knowledge(query, max_results=3)
                if relevant_chunks:
                    rag_context = "\n**Relevant TEP Knowledge**:\n"
                    for i, chunk in enumerate(relevant_chunks):
                        rag_context += f"\n{i+1}. From {chunk.source_document} - {chunk.section}:\n"
                        rag_context += f"{chunk.content[:300]}...\n"
                        knowledge_sources.append({
                            'source': chunk.source_document,
                            'section': chunk.section,
                            'relevance': chunk.relevance_score
                        })
                    logger.info(f"📚 Found {len(relevant_chunks)} relevant knowledge chunks")
            except Exception as e:
                logger.warning(f"⚠️ RAG search failed: {e}")

        # Use selected model for intelligent response
        answer = ""
        model_used = model_choice

        try:
            # Build enhanced prompt with RAG context (used by all models)
            prompt = f"""You are an expert in Tennessee Eastman Process (TEP) fault diagnosis with access to comprehensive TEP knowledge base.

**TEP Process Overview**:
The Tennessee Eastman Process is a chemical process simulation with 52 process variables (XMEAS_1 to XMEAS_52, XMV_1 to XMV_12) and 20 fault types (IDV_1 to IDV_20). It includes reactor, separator, compressor, condenser, and stripper units.

**Analysis Context**:
{context}

**Relevant Knowledge from TEP Thesis**:
{rag_context if rag_context else 'No specific knowledge retrieved'}

**Conversation History**:
{json.dumps(history[-3:], indent=2) if history else 'No previous conversation'}

**User Question**: {query}

**Instructions**:
1. Use the analysis context and TEP knowledge to provide accurate, specific answers
2. If the user disagrees with a root cause, search the knowledge base for alternative explanations
3. Reference specific variables, equipment, or fault patterns when relevant
4. Be concise but thorough
5. If suggesting alternatives, explain the reasoning based on TEP process knowledge

Provide your response:"""

            # Route to selected model
            if model_choice == 'gemini':
                # Use Gemini via multi_llm_client with FULL prompt
                if multi_llm_client:
                    system_msg = "You are an expert in Tennessee Eastman Process (TEP) fault diagnosis."
                    answer = await multi_llm_client._query_gemini(system_msg, prompt)
                    logger.info("✅ Gemini response generated with FULL RAG context")
                else:
                    raise ValueError("Gemini client not available")

            elif model_choice == 'anthropic':
                # Use Claude via multi_llm_client
                if multi_llm_client:
                    system_msg = "You are an expert in Tennessee Eastman Process (TEP) fault diagnosis."
                    answer = await multi_llm_client._query_claude(system_msg, prompt)
                    logger.info("✅ Claude response generated with RAG context")
                else:
                    raise ValueError("Claude client not available")

            elif model_choice == 'lmstudio':
                # Use LMStudio via multi_llm_client with SHORTENED prompt
                if multi_llm_client:
                    # 🔧 SHORTENED PROMPT for LMStudio only (4K token limit)
                    # Extract just the essential parts
                    shortened_prompt = f"""You are analyzing TEP process faults.

**Analysis Context**:
{context[:500] if context else 'No context'}

**User Question**: {query}

Provide concise root cause analysis."""

                    # Call with empty system message and shortened user prompt
                    answer = await multi_llm_client._query_lmstudio("", shortened_prompt)
                    logger.info("✅ LMStudio response generated with shortened prompt")
                else:
                    raise ValueError("LMStudio client not available")
            else:
                raise ValueError(f"Unknown model: {model_choice}")

        except Exception as e:
            logger.warning(f"⚠️ {model_choice} unavailable ({e}), using RAG-enhanced fallback response")
            model_used = "fallback"

            # RAG-enhanced fallback response
            if "disagree" in query.lower() or "not" in query.lower():
                # Use RAG to find alternative causes
                alternatives_text = ""
                if rag_context:
                    alternatives_text = f"\n**From TEP Knowledge Base**:\n{rag_context}\n"

                answer = f"""I understand your concern about the analysis. Let me suggest some alternative possibilities based on TEP knowledge:

**Alternative Root Causes to Consider**:
1. **Feed composition issues** - Check upstream feed quality and composition
2. **Heat exchanger fouling** - Reduced heat transfer efficiency
3. **Valve malfunction** - Stuck or partially closed control valves
4. **Sensor drift** - Measurement errors affecting control loops
{alternatives_text}
**Next Steps**:
- Which of these alternatives seems most likely based on your experience?
- Are there any recent maintenance activities or process changes?
- What specific symptoms are you observing?

I can help you investigate any of these possibilities in more detail."""

            else:
                knowledge_text = ""
                if rag_context:
                    knowledge_text = f"\n**Relevant TEP Knowledge**:\n{rag_context}\n"

                answer = f"""Based on the analysis context and TEP knowledge base, I can help you explore this further.

**Key Points from Analysis**:
{context[:500] if context else 'No specific analysis loaded'}
{knowledge_text}
**How I Can Help**:
- Explain specific variables or trends
- Suggest diagnostic tests based on TEP knowledge
- Compare with historical fault patterns
- Recommend corrective actions

What specific aspect would you like to discuss?"""

        return {
            "answer": answer,
            "analysis_id": analysis_id,
            "mode": mode,
            "model_used": model_used,  # NEW: Tell frontend which model was used
            "sources": knowledge_sources if knowledge_sources else [],  # NEW: Renamed for consistency
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.exception("Chat endpoint error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rag/search")
async def rag_search(query: str, max_results: int = 5):
    """Search TEP knowledge base using RAG"""
    try:
        if not knowledge_manager:
            raise HTTPException(status_code=503, detail="Knowledge base not available")

        logger.info(f"🔍 RAG search: {query}")

        results = knowledge_manager.search_knowledge(query, max_results=max_results)

        return {
            "query": query,
            "results": [
                {
                    "content": chunk.content,
                    "source": chunk.source_document,
                    "section": chunk.section,
                    "relevance_score": chunk.relevance_score,
                    "keywords": chunk.keywords[:10]  # First 10 keywords
                }
                for chunk in results
            ],
            "total_results": len(results),
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("RAG search error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rag/stats")
async def rag_stats():
    """Get RAG knowledge base statistics"""
    try:
        if not knowledge_manager:
            raise HTTPException(status_code=503, detail="Knowledge base not available")

        stats = knowledge_manager.get_statistics()
        return {
            "statistics": stats,
            "status": "available",
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("RAG stats error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag/upload_build")
async def rag_upload_build(files: list[UploadFile] = File(...)):
    """Upload one or more PDFs, convert them to Markdown, and rebuild KB.
    Returns list of saved PDFs, generated Markdown files, and KB stats.
    """
    try:
        # Use local RAG folder in TEP_control directory
        # Get the parent directory of backend (which is TEP_control)
        backend_dir = Path(__file__).parent
        tep_control_dir = backend_dir.parent

        md_dir = tep_control_dir / "RAG" / "converted_markdown"
        md_dir.mkdir(parents=True, exist_ok=True)
        (md_dir / "images").mkdir(exist_ok=True)

        # Raw PDFs destination
        pdf_dir = tep_control_dir / "RAG" / "materials" / "uploads"
        pdf_dir.mkdir(parents=True, exist_ok=True)

        saved_pdfs = []
        for f in files:
            safe_name = f.filename.replace("..", "_").replace("/", "_")
            target = pdf_dir / safe_name
            content = await f.read()
            with open(target, "wb") as out:
                out.write(content)
            saved_pdfs.append(str(target.resolve()))

        # Convert using existing converter
        try:
            from TEP_control.RAG.pdf_to_markdown_converter import PDFToMarkdownConverter  # type: ignore
        except Exception:
            # Fallback import path when run from backend dir
            from ...RAG.pdf_to_markdown_converter import PDFToMarkdownConverter  # type: ignore

        converter = PDFToMarkdownConverter(output_dir=str(md_dir))
        generated_md = []
        for p in saved_pdfs:
            res = converter.convert_pdf_to_markdown(p)
            if res:
                generated_md.append(res)

        # Rebuild knowledge manager so new docs become searchable
        global knowledge_manager
        try:
            knowledge_manager = EnhancedKnowledgeManager(str(md_dir.resolve()))
            kb_stats = knowledge_manager.get_statistics()
        except Exception as e:
            logger.warning(f"KB reload failed: {e}")
            kb_stats = {"reloaded": False, "error": str(e)}

        return {
            "uploaded": saved_pdfs,
            "generated_markdown": generated_md,
            "kb_stats": kb_stats,
            "markdown_dir": str(md_dir.resolve()),
            "pdf_dir": str(pdf_dir.resolve()),
            "status": "ok"
        }
    except Exception as e:
        logger.exception("RAG upload/build error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag/reindex")
async def rag_reindex():
    """Force reindex the knowledge base from existing Markdown files."""
    try:
        global knowledge_manager

        # Use local RAG folder in TEP_control directory
        backend_dir = Path(__file__).parent
        tep_control_dir = backend_dir.parent
        md_dir = tep_control_dir / "RAG" / "converted_markdown"

        if not md_dir.exists():
            raise HTTPException(status_code=404, detail=f"Markdown directory not found: {md_dir}")

        # Rebuild knowledge manager
        knowledge_manager = EnhancedKnowledgeManager(str(md_dir.resolve()))
        stats = knowledge_manager.get_statistics()

        return {
            "status": "ok",
            "message": "Knowledge base reindexed successfully",
            "markdown_dir": str(md_dir.resolve()),
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("RAG reindex error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))




# ===== Knowledge Base API Endpoints =====
# Add these endpoints to backend/app.py

@app.post("/api/knowledge_base/convert")
async def convert_documents_to_knowledge_base(files: List[UploadFile] = File(...)):
    """
    Upload and convert PDF files to Markdown format for knowledge base.

    Parameters:
    - files: List of uploaded files (PDF, MD, TXT)

    Returns:
    - status: success/error
    - message: Description
    - converted_count: Number of files converted
    - output_dir: Where files were saved
    - files: List of converted filenames
    """
    try:
        # Setup paths
        backend_dir = Path(__file__).parent
        tep_control_dir = backend_dir.parent
        output_dir = tep_control_dir / "RAG" / "converted_markdown"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Temporary upload directory
        temp_dir = backend_dir / "temp_uploads"
        temp_dir.mkdir(exist_ok=True)

        converted_files = []
        errors = []

        for upload_file in files:
            try:
                # Save uploaded file temporarily
                file_extension = Path(upload_file.filename).suffix.lower()
                temp_path = temp_dir / upload_file.filename

                # Save file
                content = await upload_file.read()
                with open(temp_path, "wb") as f:
                    f.write(content)

                # Process based on file type
                if file_extension in [".pdf", ".docx"]:
                    # Import PDF/DOCX converter
                    import sys
                    rag_dir = str(tep_control_dir / "RAG")
                    if rag_dir not in sys.path:
                        sys.path.insert(0, rag_dir)

                    try:
                        from pdf_to_markdown_converter import PDFToMarkdownConverter
                    except ImportError as e:
                        raise ImportError(f"Converter not found. Error: {e}. Install: pip install PyMuPDF python-docx")

                    # Convert PDF or Word
                    converter = PDFToMarkdownConverter(output_dir=str(output_dir))
                    converter.convert_file(str(temp_path))

                    output_filename = Path(upload_file.filename).stem + ".md"
                    converted_files.append(output_filename)

                elif file_extension in [".md", ".txt"]:
                    # Copy markdown/text files directly
                    output_path = output_dir / upload_file.filename
                    with open(output_path, "wb") as f:
                        f.write(content)
                    converted_files.append(upload_file.filename)

                elif file_extension == ".doc":
                    errors.append(f"{upload_file.filename}: .doc format not supported. Please convert to .docx first.")

                else:
                    errors.append(f"{upload_file.filename}: Unsupported format ({file_extension}). Supported: PDF, DOCX, MD, TXT")

                # Clean up temp file
                if temp_path.exists():
                    temp_path.unlink()

            except Exception as e:
                errors.append(f"{upload_file.filename}: {str(e)}")

        # Clean up temp directory
        if temp_dir.exists() and not list(temp_dir.iterdir()):
            temp_dir.rmdir()

        if not converted_files and errors:
            return {
                "status": "error",
                "message": f"Conversion failed: {'; '.join(errors)}",
                "converted_count": 0,
                "errors": errors
            }

        message = f"Successfully converted {len(converted_files)} file(s)"
        if errors:
            message += f" ({len(errors)} error(s))"

        return {
            "status": "success",
            "message": message,
            "converted_count": len(converted_files),
            "output_dir": str(output_dir.relative_to(tep_control_dir)),
            "files": converted_files,
            "errors": errors if errors else None
        }

    except Exception as e:
        logger.exception("Document conversion error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/knowledge_base/reindex")
async def reindex_knowledge_base():
    """
    Rebuild knowledge base index from all markdown files.

    Returns:
    - status: success/error
    - message: Description
    - document_count: Number of documents indexed
    - chunk_count: Number of chunks created
    - last_indexed: Timestamp
    """
    try:
        global knowledge_manager

        # Setup paths
        backend_dir = Path(__file__).parent
        tep_control_dir = backend_dir.parent
        md_dir = tep_control_dir / "RAG" / "converted_markdown"

        if not md_dir.exists():
            md_dir.mkdir(parents=True, exist_ok=True)
            return {
                "status": "success",
                "message": "Knowledge base directory created (empty)",
                "document_count": 0,
                "chunk_count": 0,
                "last_indexed": datetime.now().isoformat()
            }

        # Rebuild knowledge manager
        knowledge_manager = EnhancedKnowledgeManager(str(md_dir.resolve()))

        # Get statistics
        doc_count = len(knowledge_manager.documents)
        chunk_count = len(knowledge_manager.chunks)

        return {
            "status": "success",
            "message": "Knowledge base reindexed successfully",
            "document_count": doc_count,
            "chunk_count": chunk_count,
            "last_indexed": datetime.now().isoformat()
        }

    except Exception as e:
        logger.exception("Knowledge base reindex error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge_base/list")
async def list_knowledge_base_documents():
    """
    List all documents in the knowledge base.

    Returns:
    - status: success/error
    - documents: List of document metadata
    - document_count: Total documents
    - chunk_count: Total chunks
    - last_indexed: Last reindex timestamp
    """
    try:
        backend_dir = Path(__file__).parent
        tep_control_dir = backend_dir.parent
        md_dir = tep_control_dir / "RAG" / "converted_markdown"

        if not md_dir.exists():
            return {
                "status": "success",
                "documents": [],
                "document_count": 0,
                "chunk_count": 0
            }

        documents = []
        for md_file in sorted(md_dir.glob("*.md")):
            stat = md_file.stat()
            documents.append({
                "name": md_file.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })

        # Get chunk count from knowledge manager if available
        chunk_count = len(knowledge_manager.chunks) if knowledge_manager else 0

        return {
            "status": "success",
            "documents": documents,
            "document_count": len(documents),
            "chunk_count": chunk_count,
            "last_indexed": datetime.now().isoformat() if knowledge_manager else None
        }

    except Exception as e:
        logger.exception("Knowledge base list error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge_base/view/{doc_name}")
async def view_knowledge_base_document(doc_name: str):
    """
    View content of a specific document.

    Parameters:
    - doc_name: Document filename

    Returns:
    - status: success/error
    - content: Document content
    - name: Document name
    - size: File size in bytes
    """
    try:
        # Security: Prevent directory traversal
        if ".." in doc_name or "/" in doc_name or "\\" in doc_name:
            raise HTTPException(status_code=400, detail="Invalid document name")

        backend_dir = Path(__file__).parent
        tep_control_dir = backend_dir.parent
        md_dir = tep_control_dir / "RAG" / "converted_markdown"
        doc_path = md_dir / doc_name

        if not doc_path.exists():
            raise HTTPException(status_code=404, detail=f"Document not found: {doc_name}")

        # Read content
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "status": "success",
            "content": content,
            "name": doc_name,
            "size": doc_path.stat().st_size
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Document view error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/knowledge_base/delete/{doc_name}")
async def delete_knowledge_base_document(doc_name: str):
    """
    Delete a document from the knowledge base.

    Parameters:
    - doc_name: Document filename

    Returns:
    - status: success/error
    - message: Confirmation message
    - deleted_file: Name of deleted file
    """
    try:
        # Security: Prevent directory traversal
        if ".." in doc_name or "/" in doc_name or "\\" in doc_name:
            raise HTTPException(status_code=400, detail="Invalid document name")

        backend_dir = Path(__file__).parent
        tep_control_dir = backend_dir.parent
        md_dir = tep_control_dir / "RAG" / "converted_markdown"
        doc_path = md_dir / doc_name

        if not doc_path.exists():
            raise HTTPException(status_code=404, detail=f"Document not found: {doc_name}")

        # Delete file
        doc_path.unlink()

        # Also delete associated images if any
        images_dir = md_dir / "images"
        if images_dir.exists():
            doc_stem = Path(doc_name).stem
            for img_file in images_dir.glob(f"{doc_stem}_*"):
                img_file.unlink()

        return {
            "status": "success",
            "message": f"Document deleted successfully",
            "deleted_file": doc_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Document delete error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SYSTEM SNAPSHOT ENDPOINTS - Save/restore complete TEP system state
# ============================================================================

_snapshot_file = os.path.join(_diag_dir, 'system_snapshots.jsonl')

@app.post("/snapshot/save")
async def save_system_snapshot(payload: dict):
    """Save complete TEP system state snapshot"""
    try:
        import time
        snapshot_id = int(time.time() * 1000)
        timestamp = datetime.now().isoformat()

        # Get current TEP data from live CSV
        live_data_path = os.path.join(os.path.dirname(_diag_dir), "data", "live_tep_data.csv")
        tep_state = {}

        if os.path.exists(live_data_path):
            try:
                df = pd.read_csv(live_data_path)
                if len(df) > 0:
                    latest_row = df.iloc[-1]
                    tep_state = latest_row.to_dict()
            except Exception as e:
                logger.warning(f"Could not read TEP state: {e}")

        snapshot = {
            "id": snapshot_id,
            "name": payload.get("name", f"Snapshot {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
            "timestamp": timestamp,
            "description": payload.get("description", ""),
            "tep_state": tep_state,
            "created_at": time.time()
        }

        with open(_snapshot_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(snapshot) + "\n")

        logger.info(f"✅ Saved snapshot: {snapshot['name']}")
        return {"id": snapshot_id, "success": True, "name": snapshot["name"]}

    except Exception as e:
        logger.exception("Error saving snapshot: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/snapshot/list")
async def list_system_snapshots():
    """Get all saved snapshots"""
    try:
        snapshots = []
        if os.path.exists(_snapshot_file):
            with open(_snapshot_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            snap = json.loads(line)
                            snapshots.append({
                                "id": snap.get("id"),
                                "name": snap.get("name"),
                                "timestamp": snap.get("timestamp"),
                                "description": snap.get("description"),
                                "created_at": snap.get("created_at")
                            })
                        except:
                            continue
        snapshots.reverse()
        return {"items": snapshots}
    except Exception as e:
        logger.exception("Error listing snapshots: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/snapshot/restore")
async def restore_system_snapshot(payload: dict):
    """Restore TEP to saved snapshot (returns data for now)"""
    try:
        snapshot_id = payload.get("id")
        if not snapshot_id:
            raise HTTPException(400, "Missing ID")

        snapshot = None
        if os.path.exists(_snapshot_file):
            with open(_snapshot_file, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            snap = json.loads(line)
                            if snap.get("id") == snapshot_id:
                                snapshot = snap
                                break
                        except:
                            continue

        if not snapshot:
            raise HTTPException(404, f"Snapshot {snapshot_id} not found")

        logger.info(f"📂 Loaded snapshot: {snapshot['name']}")
        return {"success": True, "snapshot": snapshot["name"], "data": snapshot.get("tep_state")}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error restoring snapshot: %s", e)
        raise HTTPException(500, str(e))


@app.delete("/snapshot/delete/{snapshot_id}")
async def delete_system_snapshot(snapshot_id: int):
    """Delete a snapshot"""
    try:
        if not os.path.exists(_snapshot_file):
            raise HTTPException(404, "No snapshots")

        snapshots = []
        found = False
        with open(_snapshot_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        snap = json.loads(line)
                        if snap.get("id") == snapshot_id:
                            found = True
                        else:
                            snapshots.append(snap)
                    except:
                        continue

        if not found:
            raise HTTPException(404, f"Snapshot {snapshot_id} not found")

        with open(_snapshot_file, 'w') as f:
            for snap in snapshots:
                f.write(json.dumps(snap) + "\n")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


if __name__ == "__main__":
    print("🚀 Starting FastAPI server...")
    try:
        import uvicorn
        print("📡 Uvicorn imported successfully")
        print("🌐 Starting server on http://0.0.0.0:8000")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()
