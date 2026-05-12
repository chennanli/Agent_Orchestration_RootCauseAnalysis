#!/usr/bin/env python3
"""
Unified TEP Control Panel
- Single interface to control all components
- Dynamic simulation → FaultExplainer integration
- Proper timing: 3min → 6min → 12min
- Uses original FaultExplainer backend/frontend
- Correct IDV ranges (0-1) and threshold (0.01)
"""

import os
import sys
import time
import threading
import subprocess
import signal
import json
import csv
import re
from collections import deque
import numpy as np
from flask import Flask, render_template, jsonify, request, redirect, url_for, send_from_directory, Response, stream_with_context
from flask_cors import CORS
import requests
import queue

# --- Helpers: resolve tools cross-platform and venv-aware ---

def resolve_venv_python():
    """Use local venv in TEP_control folder. Return absolute python path for current OS."""
    # Get the current script directory (TEP_control/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cwd = script_dir
    if sys.platform.startswith('win'):
        venv_python = os.path.join(cwd, '.venv', 'Scripts', 'python.exe')
    else:
        venv_python = os.path.join(cwd, '.venv', 'bin', 'python')

    if os.path.exists(venv_python):
        return venv_python
    # Fallback to current interpreter
    return sys.executable


def resolve_npm_cmd():
    return 'npm.cmd' if sys.platform.startswith('win') else 'npm'

class TEPDataBridge:
    """Bridge between dynamic TEP simulation and FaultExplainer."""

    def __init__(self):
        # Auto-cleanup before initialization
        self.auto_cleanup_tep_processes()
        self.setup_tep2py()

        # Simulation state
        self.tep_running = False
        self.current_step = 0
        self.idv_values = np.zeros(20)  # 20 IDV inputs (binary for Fortran)
        self.idv_continuous_values = np.zeros(20)  # Store continuous values for future use
        # Maintain a time-series of IDV rows so the simulator advances over time
        # Rather than simulating a single step repeatedly (which yields a constant output)
        from collections import deque as _deque
        self.idv_history = _deque(maxlen=1200)  # ~1 day of 3-min steps

        # Keep persistent simulation instance to avoid re-running entire history
        self.tep_sim_instance = None
        self.last_simulated_step = 0

        # Data queues with proper timing
        self.raw_data_queue = deque(maxlen=1000)  # Every 3 minutes (raw TEP)
        self.pca_data_queue = deque(maxlen=500)   # Every 6 minutes (half speed)
        self.llm_data_queue = deque(maxlen=250)   # Every 12 minutes (quarter speed)

        # Anomaly Detection training mode
        self.pca_training_mode = False
        self.pca_training_data = []
        self.pca_training_target = 15   # Faster demo collection, will merge with original 500 points

        # Stability monitoring for smart Anomaly Detection retraining
        self.stability_buffer = []
        self.stability_window = 20  # Monitor last 20 points for stability
        self.stability_threshold = 0.05  # 5% coefficient of variation threshold
        self.is_stable = False

        # Timing control
        self.last_pca_time = 0
        self.last_llm_time = 0
        self.pca_interval = 6 * 60  # 6 minutes in seconds
        self.llm_interval = 12 * 60  # 12 minutes in seconds
        # Simulation step interval (default: real-time 3 minutes)
        self.step_interval_seconds = 180
        self.speed_mode = 'real'  # 'demo' or 'real'
        self.current_preset = None  # 'demo' or 'real'
        self.speed_factor = 1.0  # New: speed multiplier (0.1x to 10x)

        # Process management
        self.processes = {}

        # Heartbeat and CSV stats
        self.last_loop_at = 0
        self.last_ingest_at = 0
        self.last_ingest_ok = False
        self.csv_rows = 0
        self.csv_bytes = 0
        self.last_saved_step = -1  # Track last saved step to prevent duplicates

        # Cost protection
        self.last_auto_stop_check = 0
        self.auto_stop_check_interval = 60  # Check every minute
        # Diagnostics
        self.last_error = ""
        self.last_ingest_info = {}

        print("✅ TEP Data Bridge initialized")
        print("✅ Timing: TEP(3min) → Anomaly Detection(6min) → LLM(12min)")

    def auto_cleanup_tep_processes(self):
        """Auto-cleanup any existing TEP processes and data files for clean startup."""
        print("🧹 Auto-cleanup: Checking for existing TEP processes...")

        try:
            import psutil

            # Find and terminate existing TEP processes
            tep_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''

                    # Look for other TEP-related processes (but not current one)
                    if any(keyword in cmdline.lower() for keyword in [
                        'unified_tep_control_panel',
                        'tep_bridge',
                        'mvp_dashboard'
                    ]) and proc.info['pid'] != os.getpid():
                        tep_processes.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Terminate found processes
            if tep_processes:
                print(f"🔪 Found {len(tep_processes)} existing TEP processes, terminating...")
                for pid in tep_processes:
                    try:
                        os.kill(pid, signal.SIGTERM)
                        print(f"✅ Terminated PID {pid}")
                    except:
                        pass
                time.sleep(1)  # Give processes time to exit
            else:
                print("✅ No conflicting TEP processes found")

            # Clean up data file for fresh start
            data_file = os.path.join('data', 'live_tep_data.csv')
            if os.path.exists(data_file):
                try:
                    # Keep header only
                    with open(data_file, 'r') as f:
                        header = f.readline()

                    with open(data_file, 'w') as f:
                        f.write(header)

                    print(f"✅ Cleaned data file: {data_file}")
                except Exception as e:
                    print(f"⚠️ Could not clean data file: {e}")

            print("✅ Auto-cleanup completed")

        except ImportError:
            print("⚠️ psutil not available, skipping process cleanup")
        except Exception as e:
            print(f"⚠️ Auto-cleanup error: {e}")

    def setup_tep2py(self):
        """Setup real tep2py simulator."""
        try:
            # Get script directory and build path to local simulation
            script_dir = os.path.dirname(os.path.abspath(__file__))
            tep_path = os.path.join(script_dir, 'backend', 'simulation')
            if tep_path not in sys.path:
                sys.path.insert(0, tep_path)

            import tep2py
            self.tep2py = tep2py
            print("✅ Real tep2py loaded")

        except Exception as e:
            print(f"❌ tep2py setup failed: {e}")
            self.tep2py = None
    def map_to_faultexplainer_features(self, data_point):
        """Map XMEAS_* and XMV_* keys to FaultExplainer friendly feature names required by /ingest.
        EXPANDED: Now includes ALL 52 TEP features (XMEAS 1-41 + XMV 1-11) for complete anomaly detection.
        """
        # XMEAS variables (measurements) - XMEAS 1-22
        xmeas_to_name = {
            1: 'A Feed', 2: 'D Feed', 3: 'E Feed', 4: 'A and C Feed', 5: 'Recycle Flow',
            6: 'Reactor Feed Rate', 7: 'Reactor Pressure', 8: 'Reactor Level', 9: 'Reactor Temperature',
            10: 'Purge Rate', 11: 'Product Sep Temp', 12: 'Product Sep Level', 13: 'Product Sep Pressure',
            14: 'Product Sep Underflow', 15: 'Stripper Level', 16: 'Stripper Pressure', 17: 'Stripper Underflow',
            18: 'Stripper Temp', 19: 'Stripper Steam Flow', 20: 'Compressor Work', 21: 'Reactor Coolant Temp',
            22: 'Separator Coolant Temp',
            # XMEAS 23-41: Component compositions (CRITICAL for fault detection!)
            23: 'Component A to Reactor', 24: 'Component B to Reactor', 25: 'Component C to Reactor',
            26: 'Component D to Reactor', 27: 'Component E to Reactor', 28: 'Component F to Reactor',
            29: 'Component A in Purge', 30: 'Component B in Purge', 31: 'Component C in Purge',
            32: 'Component D in Purge', 33: 'Component E in Purge', 34: 'Component F in Purge',
            35: 'Component G in Purge', 36: 'Component H in Purge',
            37: 'Component D in Product', 38: 'Component E in Product', 39: 'Component F in Product',
            40: 'Component G in Product', 41: 'Component H in Product'
        }

        # XMV variables (manipulated/control variables) - XMV 1-11
        xmv_to_name = {
            1: 'D feed load', 2: 'E feed load', 3: 'A feed load', 4: 'A and C feed load',
            5: 'Compressor recycle valve', 6: 'Purge valve', 7: 'Separator liquid load',
            8: 'Stripper liquid load', 9: 'Stripper steam valve', 10: 'Reactor coolant load',
            11: 'Condenser coolant load'
        }

        row = {}
        # Map XMEAS variables (1-41, ALL 41 measurements including compositions)
        for i, name in xmeas_to_name.items():
            row[name] = float(data_point.get(f'XMEAS_{i}', 0.0))

        # Map XMV variables (1-11, all manipulated variables)
        for i, name in xmv_to_name.items():
            row[name] = float(data_point.get(f'XMV_{i}', 0.0))

        return row

    def send_to_ingest(self, data_point, url=None):
        """Post a single mapped point to FaultExplainer /ingest and record heartbeat.
        Logs backend response to detect ignored vs aggregating vs accepted events.

        Backend URL resolution:
          1. Explicit `url` argument (rare; only used by tests)
          2. BACKEND_INGEST_URL env var (set by docker-compose so the console
             container reaches the `backend` service by name)
          3. Localhost fallback for `python unified_console.py` outside Docker
        """
        if url is None:
            url = os.environ.get(
                "BACKEND_INGEST_URL", "http://127.0.0.1:8000/ingest"
            )
        start = time.time()
        try:
            mapped = self.map_to_faultexplainer_features(data_point)

            # Always check stability for monitoring
            self.check_data_stability(mapped)

            # Check if we're in Anomaly Detection training mode
            if self.pca_training_mode:
                self.pca_training_data.append(mapped)
                print(f"📊 Anomaly Detection Training: Collected {len(self.pca_training_data)}/{self.pca_training_target} data points")

                if len(self.pca_training_data) >= self.pca_training_target:
                    print("🎯 Anomaly Detection Training: Target reached, retraining model...")
                    self.retrain_pca_model()
                    self.pca_training_mode = False
                    print("✅ Anomaly Detection Training: Complete, resuming normal operation")

                # Don't send to ingest during training - just record heartbeat
                self.last_ingest_at = time.time()
                self.last_ingest_ok = True
                self.last_ingest_info = {"status": "training", "collected": len(self.pca_training_data)}
                return

            import requests
            r = requests.post(url, json={"data_point": mapped}, timeout=60)
            self.last_ingest_at = time.time()
            if r.status_code == 404:
                # MultiLLM backend does not expose /ingest; treat as connected and continue
                self.last_ingest_ok = True
                self.last_ingest_info = {"status": "no_ingest_endpoint", "detail": "MultiLLM backend uses anomaly-triggered /explain"}
                print(f"ℹ️ Backend has no /ingest endpoint (404). Using live CSV + periodic analysis instead.")
                return
            self.last_ingest_ok = (r.status_code == 200)
            if not self.last_ingest_ok:
                print(f"⚠️ /ingest HTTP {r.status_code}: {r.text[:160]}")
                return
            dt = self.last_ingest_at - start
            try:
                info = r.json()
            except Exception:
                info = {"raw": r.text[:160]}
            status = info.get('status')
            if status == 'ignored':
                reason = info.get('reason','')
                present = info.get('present')
                print(f"⚠️ /ingest ignored in {dt:.2f}s reason={reason} present={len(present) if present else 0}")
                return
            if info.get('aggregating'):
                have = info.get('have')
                need = info.get('need')
                print(f"⏳ /ingest aggregating in {dt:.2f}s (have={have}, need={need})")
                return
            # Accepted point with t2/anomaly
            print(f"✅ /ingest OK in {dt:.2f}s (t2={info.get('t2_stat','-')}, anomaly={info.get('anomaly')}, idx={info.get('aggregated_index')})")
            if info.get('llm', {}).get('status') == 'triggered':
                print("🤖 LLM triggered (live)")
        except Exception as e:
            self.last_ingest_ok = False
            self.last_ingest_info = {"error": str(e)}
            print(f"❌ Failed to POST /ingest: {e}")

    def retrain_pca_model(self):
        """Retrain Anomaly Detection model by merging new stable data with original baseline."""
        try:
            import pandas as pd
            import requests

            # Load original baseline data from local backend (500 points)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            original_file = os.path.join(script_dir, "backend", "data", "fault0.csv")
            original_df = pd.read_csv(original_file)
            if "time" in original_df.columns:
                original_df = original_df.drop(columns=["time"])
            print(f"📊 Loaded original baseline: {len(original_df)} data points")

            # Convert new training data to DataFrame
            new_df = pd.DataFrame(self.pca_training_data)
            print(f"📊 Collected new stable data: {len(new_df)} data points")

            # Merge original + new data
            merged_df = pd.concat([original_df, new_df], ignore_index=True)
            print(f"🔗 Merged dataset: {len(merged_df)} total data points ({len(original_df)} original + {len(new_df)} new)")

            # Save merged training data to local backend data
            training_file = os.path.join(script_dir, "backend", "data", "live_fault0.csv")
            os.makedirs(os.path.dirname(training_file), exist_ok=True)
            merged_df.to_csv(training_file, index=False)
            print(f"💾 Saved merged training data to {training_file}")

            # Send retrain request to FaultExplainer
            retrain_url = "http://127.0.0.1:8000/retrain"
            payload = {"training_file": "live_fault0.csv"}

            response = requests.post(retrain_url, json=payload, timeout=120)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Anomaly Detection model retrained successfully")
                print(f"   - Components: {result.get('n_components', 'N/A')}")
                print(f"   - Threshold: {result.get('t2_threshold', 'N/A'):.2f}")
            else:
                print(f"❌ Anomaly Detection retrain failed: {response.status_code} {response.text}")

        except Exception as e:
            print(f"❌ Anomaly Detection retrain error: {e}")

    def check_data_stability(self, data_point):
        """Check if recent data is stable enough for Anomaly Detection retraining."""
        # Add current data point to stability buffer
        key_vars = ['A Feed', 'Reactor Pressure', 'Reactor Level', 'Reactor Temperature']
        stability_values = []

        for var in key_vars:
            if var in data_point:
                stability_values.append(data_point[var])

        if stability_values:
            avg_value = sum(stability_values) / len(stability_values)
            self.stability_buffer.append(avg_value)

            # Keep only recent points
            if len(self.stability_buffer) > self.stability_window:
                self.stability_buffer.pop(0)

            # Check stability if we have enough points
            if len(self.stability_buffer) >= self.stability_window:
                import numpy as np
                values = np.array(self.stability_buffer)
                mean_val = np.mean(values)
                std_val = np.std(values)
                cv = std_val / mean_val if mean_val != 0 else 1.0

                self.is_stable = bool(cv < self.stability_threshold)
                return self.is_stable

        return False

    def start_pca_training(self):
        """Start Anomaly Detection training mode."""
        self.pca_training_mode = True
        self.pca_training_data = []
        print(f"🎯 Anomaly Detection Training: Started, will collect {self.pca_training_target} stable data points")

    def set_idv(self, idv_num, value):
        """Set IDV value (1-20, continuous range -5.0 to +5.0 for realistic disturbances)."""
        if 1 <= idv_num <= 20:
            # Allow continuous values for realistic disturbance modeling
            float_value = float(value)
            # Reasonable safety limits to prevent simulation instability
            if -5.0 <= float_value <= 5.0:
                # Store the continuous value for our own use
                self.idv_continuous_values[idv_num - 1] = float_value

                # For now, still pass binary to Fortran until we fix compilation
                if float_value > 0:
                    self.idv_values[idv_num - 1] = 1.0
                else:
                    self.idv_values[idv_num - 1] = 0.0

                if float_value == 0:
                    status = "NORMAL"
                elif float_value > 0:
                    status = f"POSITIVE DISTURBANCE (+{float_value:.2f}) -> Fortran: 1"
                else:
                    status = f"NEGATIVE DISTURBANCE ({float_value:.2f}) -> Fortran: 0"
                print(f"🔧 Set IDV_{idv_num} = {float_value:.2f} ({status})")
                return True
        return False

    def set_xmv(self, xmv_num, value):
        """Set XMV value (1-11, continuous 0.0-100.0% as per original TEP paper)."""
        if 1 <= xmv_num <= 11:
            # Convert to float (0.0-100.0) as per original TEP specification
            float_value = float(value)
            if 0.0 <= float_value <= 100.0:
                # Initialize XMV values if not exists (TEP requires exactly 11 values for XMV(1) to XMV(11))
                if not hasattr(self, 'xmv_values'):
                    self.xmv_values = np.array([63.0, 53.0, 24.0, 61.0, 22.0, 40.0, 38.0, 46.0, 47.0, 41.0, 18.0])

                self.xmv_values[xmv_num - 1] = float_value
                print(f"🎛️ Set XMV_{xmv_num} = {float_value:.1f}%")
                return True
        return False

    def set_setpoint(self, setpoint_num, value):
        """Set control setpoint value - CRITICAL MISSING METHOD!

        This method was missing, causing all setpoint controls to be ignored!
        Now properly implemented to pass setpoints to TEP Fortran simulation.
        """
        if 1 <= setpoint_num <= 20:  # TEP supports 20 setpoints
            # Initialize setpoint values array if not exists
            if not hasattr(self, 'setpoint_values'):
                # Default TEP setpoint values
                self.setpoint_values = np.array([
                    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 50.0, 50.0, 0.0, 94.6,  # SETPT_1-10
                    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0      # SETPT_11-20
                ])

            # Update the specific setpoint value (convert to 0-based index)
            self.setpoint_values[setpoint_num - 1] = float(value)

            # Map setpoint names for logging
            setpoint_names = {
                7: "Product Separator Level", 8: "Stripper Level", 10: "Reactor Cooling Water Temperature"
            }
            name = setpoint_names.get(setpoint_num, f"Setpoint {setpoint_num}")
            unit = "°C" if setpoint_num == 10 else "%"

            print(f"🎯 Set SETPT_{setpoint_num} ({name}) = {value}{unit}")
            print(f"🔄 This will affect TEP control system in next simulation step")
            return True
        return False

    def run_tep_simulation_step(self):
        """Run one TEP simulation step (3 minutes) - GENUINE FORTRAN SIMULATION."""
        try:
            if not self.tep2py:
                return None

            # Append current IDV to history
            self.idv_history.append(self.idv_values.copy())
            current_step = len(self.idv_history)

            # REAL TEP SIMULATION: Always run fresh simulation with current history
            # This ensures we get genuine dynamic data, not artificial stability
            import numpy as _np2

            # Create simulation matrix with current IDV history
            # Include some pre-run steps for stability, then actual history
            prerun_steps = 10  # Reduced for faster simulation
            prerun_matrix = _np2.zeros((prerun_steps, 20), dtype=_np2.float64)  # No faults during pre-run

            # Convert IDV history to proper format (FLOAT, not INT!)
            if len(self.idv_history) > 0:
                actual_matrix = _np2.array(list(self.idv_history), dtype=_np2.float64).reshape(-1, 20)
                full_matrix = _np2.vstack([prerun_matrix, actual_matrix])
            else:
                # If no history yet, just use prerun matrix
                full_matrix = prerun_matrix

            print(f"🔄 Running REAL TEP simulation: {prerun_steps} pre-run + {current_step} actual steps (Speed: {self.speed_factor}x)")
            print(f"🎛️ Current XMV values: {self.xmv_values if hasattr(self, 'xmv_values') else 'Not set'}")
            print(f"🎯 Current SETPOINT values: {self.setpoint_values if hasattr(self, 'setpoint_values') else 'Not set'}")

            # Create and run fresh simulation - this gives us REAL dynamic data
            user_xmv = self.xmv_values if hasattr(self, 'xmv_values') else None
            user_setpoints = self.setpoint_values if hasattr(self, 'setpoint_values') else None
            # ✅ FIXED: tep2py now supports user_setpoints via Fortran COMMON block access!
            tep_sim = self.tep2py.tep2py(full_matrix, speed_factor=self.speed_factor, user_xmv=user_xmv, user_setpoints=user_setpoints)
            tep_sim.simulate()

            # Extract the LATEST data point (corresponds to current step)
            if hasattr(tep_sim, 'process_data') and len(tep_sim.process_data) > 0:
                # Get the last data point (most recent simulation result)
                latest = tep_sim.process_data.iloc[-1]
                data_length = len(tep_sim.process_data)

                print(f"📊 Using REAL Fortran simulation data (total points: {data_length}, using latest)")

                # Extract XMEAS and XMV columns
                xmeas_cols = [col for col in tep_sim.process_data.columns if 'XMEAS' in col]
                xmv_cols = [col for col in tep_sim.process_data.columns if 'XMV' in col]

                # Create data point with REAL simulation results
                data_point = {
                    'timestamp': time.time(),
                    'step': current_step - 1,  # Use current_step from idv_history, 0-indexed
                    'idv_values': self.idv_values.copy(),
                }

                # Add XMEAS data (process measurements)
                for i, col in enumerate(xmeas_cols):
                    if col in latest.index:
                        data_point[f'XMEAS_{i+1}'] = float(latest[col])
                    else:
                        data_point[f'XMEAS_{i+1}'] = 0.0

                # Add XMV data (manipulated variables)
                for i, col in enumerate(xmv_cols):
                    if col in latest.index:
                        data_point[f'XMV_{i+1}'] = float(latest[col])
                    else:
                        data_point[f'XMV_{i+1}'] = 0.0

                # Debug: Compare set XMV vs actual XMV
                if hasattr(self, 'xmv_values'):
                    print(f"🔍 XMV Comparison:")
                    for i in range(min(len(self.xmv_values), 5)):  # Show first 5
                        set_val = self.xmv_values[i]
                        actual_val = data_point.get(f'XMV_{i+1}', 0)
                        print(f"   XMV_{i+1}: Set={set_val:.1f}%, Actual={actual_val:.1f}%")

                # Log some key values to verify real data
                xmeas_1 = data_point.get('XMEAS_1', 0)
                xmeas_7 = data_point.get('XMEAS_7', 0)
                print(f"📈 REAL data - XMEAS_1: {xmeas_1:.6f}, XMEAS_7: {xmeas_7:.6f}")

                return data_point
            else:
                print(f"❌ No simulation data generated")
                return None

        except Exception as e:
            print(f"❌ TEP simulation step failed: {e}")
            return None

    def save_data_for_faultexplainer(self, data_point):
        """Save data in FaultExplainer format."""
        try:
            # Prevent duplicate saves
            current_step = data_point['step']
            if current_step <= self.last_saved_step:
                print(f"⏭️ Skipping duplicate step {current_step} (last saved: {self.last_saved_step})")
                return True

            # Create CSV file path
            csv_path = os.path.join('data', 'live_tep_data.csv')
            os.makedirs('data', exist_ok=True)

            # Prepare row data
            row_data = [data_point['timestamp'], data_point['step']]

            # Add XMEAS values (41 variables)
            for i in range(1, 42):
                key = f'XMEAS_{i}'
                row_data.append(data_point.get(key, 0.0))

            # Add XMV values (11 variables)
            for i in range(1, 12):
                key = f'XMV_{i}'
                row_data.append(data_point.get(key, 0.0))

            # Add IDV values (20 variables)
            for i in range(20):
                row_data.append(data_point['idv_values'][i])

            # Write to CSV
            file_exists = os.path.exists(csv_path)
            with open(csv_path, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                # Write header if new file
                if not file_exists:
                    header = ['timestamp', 'step']
                    header.extend([f'XMEAS_{i}' for i in range(1, 42)])
                    header.extend([f'XMV_{i}' for i in range(1, 12)])
                    header.extend([f'IDV_{i}' for i in range(1, 21)])
                    writer.writerow(header)
                writer.writerow(row_data)

            # Update simple CSV stats and track last saved step
            try:
                self.csv_rows += 1
                self.csv_bytes = os.path.getsize(csv_path)
                self.last_saved_step = current_step  # Update last saved step
            except Exception:
                pass

            print(f"💾 Saved data point {current_step} to {csv_path}")
            return True

        except Exception as e:
            print(f"❌ Failed to save data: {e}")
            return False


    def simulation_loop(self):
        """Main simulation loop with proper timing and heartbeats."""
        print("🚀 Starting TEP simulation loop")

        while self.tep_running:
            try:
                loop_start = time.time()
                self.last_loop_at = loop_start
                print(f"⏱️ Step {self.current_step} start (interval={self.step_interval_seconds}s, mode={self.speed_mode})")

                # Run TEP simulation step (every 3 minutes)
                data_point = self.run_tep_simulation_step()

                if data_point:
                    # Add to raw data queue
                    self.raw_data_queue.append(data_point)

                    # Save for FaultExplainer
                    if self.save_data_for_faultexplainer(data_point):
                        pass

                    # Also send to live /ingest for real-time Anomaly Detection+LLM
                    print("➡️ Posting /ingest...")
                    self.send_to_ingest(data_point)

                    # Check if time for Anomaly Detection analysis (every 6 minutes)
                    current_time = time.time()
                    if current_time - self.last_pca_time >= self.pca_interval:
                        self.pca_data_queue.append(data_point)
                        self.last_pca_time = current_time
                        print(f"📊 Anomaly Detection data point added (step {self.current_step})")

                        # Check if time for LLM analysis (every 12 minutes)
                        if current_time - self.last_llm_time >= self.llm_interval:
                            self.llm_data_queue.append(data_point)
                            self.last_llm_time = current_time
                            print(f"🤖 LLM data point added (step {self.current_step})")

                    # Update current_step to match the actual simulation step
                    self.current_step = len(self.idv_history)

                # Check for auto-shutdown signal (cost protection)
                current_time = time.time()
                if current_time - self.last_auto_stop_check > self.auto_stop_check_interval:
                    self.last_auto_stop_check = current_time
                    if self.check_auto_shutdown_signal():
                        print("🛡️ AUTO-SHUTDOWN: Premium model session expired - stopping simulation")
                        self.tep_running = False
                        break

                # Wait for next step (demo or real-time)
                print("💤 Sleeping for next step...")
                time.sleep(self.step_interval_seconds)

            except Exception as e:
                self.last_error = f"loop: {e}"
                print(f"❌ Simulation loop error: {e}")
                time.sleep(10)

        print("🛑 TEP simulation loop stopped")

    def check_auto_shutdown_signal(self):
        """Check if backend has signaled for auto-shutdown due to cost protection"""
        try:
            response = requests.get("http://127.0.0.1:8000/simulation/auto_stop_status", timeout=5)
            if response.status_code == 200:
                result = response.json()
                if result.get('auto_stopped', False):
                    # Reset the flag so it doesn't trigger again
                    requests.post("http://127.0.0.1:8000/simulation/reset_auto_stop", timeout=5)
                    return True
            return False
        except Exception as e:
            print(f"⚠️ Could not check auto-shutdown status: {e}")
            return False

    def start_tep_simulation(self):
        """Start TEP simulation."""
        if self.tep_running:
            return False, "TEP simulation already running"

        # Reset rolling state at (re)start
        try:
            self.idv_history.clear()
        except Exception:
            pass
        self.tep_running = True
        self.simulation_thread = threading.Thread(target=self.simulation_loop, daemon=True)
        self.simulation_thread.start()
        return True, "TEP simulation started"

    def restart_tep_simulation(self):
        """Restart TEP simulation safely: stop thread, reset counters and queues, start again."""
        try:
            # Stop if running
            if self.tep_running:
                self.tep_running = False
                # Allow thread to exit
                time.sleep(min(2, self.step_interval_seconds))
            # Reset state
            self.current_step = 0
            self.raw_data_queue.clear()
            self.pca_data_queue.clear()
            self.llm_data_queue.clear()
            try:
                self.idv_history.clear()
            except Exception:
                pass
            # Reset simulation instance
            self.tep_sim_instance = None
            self.last_simulated_step = 0
            self.last_pca_time = 0
            self.last_llm_time = 0
            self.last_loop_at = 0
            self.last_ingest_at = 0
            self.last_ingest_ok = False
            self.csv_rows = 0
            self.csv_bytes = 0
            self.last_saved_step = -1  # Reset duplicate prevention

            # Ensure IDV values are reset to steady state (all zeros)
            self.idv_values = np.zeros(20)

            print("🏭 TEP Restart: Pre-running to steady state...")
            print("   • IDV values: All zeros (no faults)")
            print("   • Pre-run: 25 steps to reach steady state")
            print("   • Data: Only steady-state data will be used")

            # Pre-run to steady state
            if not self.prerun_to_steady_state():
                return False, "Failed to reach steady state"

            # Start fresh with steady-state simulation
            self.tep_running = True
            self.simulation_thread = threading.Thread(target=self.simulation_loop, daemon=True)
            self.simulation_thread.start()
            return True, "TEP simulation restarted with true steady-state conditions"
        except Exception as e:
            return False, f"Failed to restart TEP: {e}"

    def prerun_to_steady_state(self):
        """Pre-run TEP simulation to reach steady state before actual data collection."""
        try:
            print("🔄 Pre-running TEP simulation to steady state...")

            # Create a longer IDV matrix for pre-run (25 steps should be enough)
            prerun_steps = 25
            idv_matrix = np.zeros((prerun_steps, 20))  # All zeros = no faults

            # Create temporary simulation instance for pre-run
            temp_sim = self.tep2py.tep2py(idv_matrix, speed_factor=1.0)  # Use normal speed for stability
            temp_sim.simulate()

            if hasattr(temp_sim, 'process_data'):
                data = temp_sim.process_data

                # Check if we reached steady state
                if len(data) >= 20:
                    # Analyze last 5 steps for stability
                    reactor_pressure = data['XMEAS(7)'].values[-5:]
                    reactor_temp = data['XMEAS(9)'].values[-5:]

                    pressure_std = np.std(reactor_pressure)
                    temp_std = np.std(reactor_temp)

                    print(f"   📊 Steady state check:")
                    print(f"      Reactor Pressure: {np.mean(reactor_pressure):.1f} ± {pressure_std:.1f} kPa")
                    print(f"      Reactor Temperature: {np.mean(reactor_temp):.1f} ± {temp_std:.1f} °C")

                    # Consider steady if standard deviation is small
                    if pressure_std < 10 and temp_std < 1.0:
                        print("   ✅ Steady state achieved!")

                        # Store steady state values for reference
                        self.steady_state_values = {
                            'pressure': np.mean(reactor_pressure),
                            'temperature': np.mean(reactor_temp),
                            'achieved_at_step': prerun_steps
                        }
                        return True
                    else:
                        print("   ⚠️ Still not fully steady, but proceeding...")
                        return True  # Proceed anyway, it's better than starting from scratch
                else:
                    print("   ⚠️ Insufficient data from pre-run")
                    return False
            else:
                print("   ❌ No data from pre-run simulation")
                return False

        except Exception as e:
            print(f"   ❌ Pre-run failed: {e}")
            return False

    def stop_tep_simulation(self):
        """Stop TEP simulation."""
        self.tep_running = False
        return True, "TEP simulation stopped"

    def kill_port_process(self, port):
        """Kill any process using the specified port."""
        try:
            import psutil
            # Walk processes and check connections safely (avoid 'connections' attr request)
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    for conn in proc.connections(kind='inet'):
                        if conn.laddr and hasattr(conn.laddr, 'port') and conn.laddr.port == port:
                            print(f"🔪 Killing process {proc.pid} using port {port}")
                            proc.kill()
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except ImportError:
            # Fallback using lsof
            try:
                result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
                if result.stdout.strip():
                    pid = result.stdout.strip()
                    subprocess.run(['kill', '-9', pid])
                    print(f"🔪 Killed process {pid} using port {port}")
                    return True
            except:
                pass
        return False

    def start_faultexplainer_backend(self):
        """Start FaultExplainer backend."""
        try:
            # Get script directory and build path to local backend
            script_dir = os.path.dirname(os.path.abspath(__file__))
            backend_path = os.path.join(script_dir, 'backend')

            # Kill existing backend if running
            if 'faultexplainer_backend' in self.processes:
                self.processes['faultexplainer_backend'].terminate()
                del self.processes['faultexplainer_backend']

            # Kill any process using port 8000
            self.kill_port_process(8000)
            time.sleep(1)  # Wait for port to be freed

            # Activate virtual environment and start backend (prefer .venv, support Windows)
            venv_python = resolve_venv_python()

            print(f"🚀 Starting backend: {venv_python} app.py in {backend_path}")

            process = subprocess.Popen(
                [venv_python, 'app.py'],
                cwd=backend_path,
                stdout=None,
                stderr=None,
                env=dict(os.environ, PYTHONPATH=backend_path)
            )

            # Wait a moment and check if process started successfully
            time.sleep(2)
            if process.poll() is None:
                self.processes['faultexplainer_backend'] = process
                print("✅ Backend process started successfully")
                return True, "FaultExplainer backend started on port 8000"
            else:
                stdout, stderr = process.communicate()
                error_msg = stdout.decode() if stdout else "Unknown error"
                print(f"❌ Backend failed to start: {error_msg}")
                return False, f"Backend failed to start: {error_msg[:100]}"

        except Exception as e:
            print(f"❌ Exception starting backend: {e}")
            return False, f"Failed to start backend: {e}"

    def start_faultexplainer_backend_dev(self):
        """Start backend in dev (uvicorn reload) mode."""
        try:
            # Get script directory and build path to local backend
            script_dir = os.path.dirname(os.path.abspath(__file__))
            backend_path = os.path.join(script_dir, 'backend')
            # Kill existing backend
            if 'faultexplainer_backend' in self.processes:
                self.processes['faultexplainer_backend'].terminate()
                del self.processes['faultexplainer_backend']
            self.kill_port_process(8000)
            time.sleep(1)
            venv_python = resolve_venv_python()
            print(f"🚀 Starting backend (dev reload): {venv_python} -m uvicorn app:app --reload")
            process = subprocess.Popen(
                [venv_python, '-m', 'uvicorn', 'app:app', '--host', '0.0.0.0', '--port', '8000', '--reload'],
                cwd=backend_path,
                stdout=None,
                stderr=None,
                env=dict(os.environ, PYTHONPATH=backend_path)
            )
            time.sleep(2)
            if process.poll() is None:
                self.processes['faultexplainer_backend'] = process
                return True, "FaultExplainer backend (dev) started on port 8000"
            return False, "Backend (dev) failed to start"
        except Exception as e:
            return False, f"Failed to start backend dev: {e}"

            print(f"🚀 Starting backend: {venv_python} app.py in {backend_path}")

            process = subprocess.Popen(
                [venv_python, 'app.py'],
                cwd=backend_path,
                stdout=None,
                stderr=None,
                env=dict(os.environ, PYTHONPATH=backend_path)
            )

            # Wait a moment and check if process started successfully
            time.sleep(2)
            if process.poll() is None:
                self.processes['faultexplainer_backend'] = process
                print("✅ Backend process started successfully")
                return True, "FaultExplainer backend started on port 8000"
            else:
                stdout, stderr = process.communicate()
                error_msg = stdout.decode() if stdout else "Unknown error"
                print(f"❌ Backend failed to start: {error_msg}")
                return False, f"Backend failed to start: {error_msg[:100]}"

        except Exception as e:
            print(f"❌ Exception starting backend: {e}")
            return False, f"Failed to start backend: {e}"

    def start_faultexplainer_frontend(self):
        """Start FaultExplainer frontend (Vite on 5173) with robust fallbacks.
        - Prefer launching Vite directly via node_modules/vite/bin/vite.js (avoids broken .bin wrapper on Node 24)
        - Fallback to `npm run dev -- --host 127.0.0.1`
        - Fallback to `yarn dev --host 127.0.0.1`
        """
        try:
            # Resolve paths to local frontend
            script_dir = os.path.dirname(os.path.abspath(__file__))
            frontend_path = os.path.join(script_dir, 'frontend')

            # Kill existing frontend if running and free port 5173
            if 'faultexplainer_frontend' in self.processes:
                try:
                    self.processes['faultexplainer_frontend'].terminate()
                except Exception:
                    pass
                finally:
                    del self.processes['faultexplainer_frontend']

            self.kill_port_process(5173)
            time.sleep(1)

            # Auto-install dependencies if missing (matches Python auto-install behavior)
            node_modules_path = os.path.join(frontend_path, 'node_modules')
            if not os.path.exists(node_modules_path):
                print("📥 Frontend dependencies not found. Installing...")
                print("   This may take a few minutes on first run...")
                try:
                    npm_cmd = resolve_npm_cmd()
                    install_process = subprocess.run(
                        [npm_cmd, 'install'],
                        cwd=frontend_path,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minute timeout
                    )
                    if install_process.returncode != 0:
                        error_msg = install_process.stderr or install_process.stdout
                        print(f"❌ npm install failed: {error_msg[:200]}")
                        return False, f"Failed to install frontend dependencies: {error_msg[:200]}"
                    print("✅ Frontend dependencies installed successfully")
                except subprocess.TimeoutExpired:
                    return False, "npm install timed out after 5 minutes"
                except Exception as e:
                    print(f"❌ Failed to install dependencies: {e}")
                    return False, f"Failed to install frontend dependencies: {e}"

            # 1) Try direct node invocation to bypass broken .bin wrapper on some Node versions
            vite_bin = os.path.join(frontend_path, 'node_modules', 'vite', 'bin', 'vite.js')
            cmds = []
            if os.path.exists(vite_bin):
                cmds.append(['node', vite_bin, '--host', '127.0.0.1'])

            # 2) Fallback to npm script
            cmds.append([resolve_npm_cmd(), 'run', 'dev', '--', '--host', '127.0.0.1'])

            # 3) Fallback to yarn if available
            yarn_cmd = 'yarn.cmd' if sys.platform.startswith('win') else 'yarn'
            cmds.append([yarn_cmd, 'dev', '--host', '127.0.0.1'])

            last_error = None
            for cmd in cmds:
                try:
                    print(f"🚀 Trying to start frontend with: {' '.join(cmd)} (cwd={frontend_path})")
                    process = subprocess.Popen(
                        cmd,
                        cwd=frontend_path,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT
                    )
                    time.sleep(3)
                    if process.poll() is None:
                        self.processes['faultexplainer_frontend'] = process
                        print("✅ Frontend process started successfully")
                        # NOTE: do NOT auto-open the browser here. The new
                        # START_TEP_COPILOT.command launcher already opens
                        # http://localhost:5173/; double-opening produces a
                        # second tab at 127.0.0.1:5173 which confuses users.
                        return True, "FaultExplainer frontend started on port 5173"
                    else:
                        stdout, _ = process.communicate()
                        last_error = (stdout.decode() if stdout else "Unknown error").strip()
                        print(f"⚠️ Attempt failed: {' '.join(cmd)} => {last_error[:200]}")
                except Exception as sub_e:
                    last_error = str(sub_e)
                    print(f"⚠️ Attempt raised: {' '.join(cmd)} => {last_error}")

            # If we reach here, all attempts failed
            print(f"❌ Frontend failed to start after all attempts: {last_error}")
            return False, f"Frontend failed to start: {last_error[:200] if last_error else 'Unknown error'}"

        except Exception as e:
            print(f"❌ Exception starting frontend: {e}")
            return False, f"Failed to start frontend: {e}"

    def stop_faultexplainer_backend(self):
        """Stop FaultExplainer backend."""
        try:
            # Terminate process if tracked
            if 'faultexplainer_backend' in self.processes:
                print("🔪 Terminating backend process...")
                self.processes['faultexplainer_backend'].terminate()
                try:
                    self.processes['faultexplainer_backend'].wait(timeout=3)
                    print("✅ Backend terminated gracefully")
                except subprocess.TimeoutExpired:
                    print("💀 Force killing backend")
                    self.processes['faultexplainer_backend'].kill()
                    self.processes['faultexplainer_backend'].wait()
                del self.processes['faultexplainer_backend']

            # Kill any process using port 8000
            self.kill_port_process(8000)
            print("✅ Backend stopped successfully")
            return True, "FaultExplainer backend stopped"
        except Exception as e:
            print(f"❌ Exception stopping backend: {e}")
            return False, f"Failed to stop backend: {e}"

    def stop_faultexplainer_frontend(self):
        """Stop FaultExplainer frontend."""
        try:
            # Terminate process if tracked
            if 'faultexplainer_frontend' in self.processes:
                print("🔪 Terminating frontend process...")
                self.processes['faultexplainer_frontend'].terminate()
                try:
                    self.processes['faultexplainer_frontend'].wait(timeout=3)
                    print("✅ Frontend terminated gracefully")
                except subprocess.TimeoutExpired:
                    print("💀 Force killing frontend")
                    self.processes['faultexplainer_frontend'].kill()
                    self.processes['faultexplainer_frontend'].wait()
                del self.processes['faultexplainer_frontend']

            # Kill any process using port 5173
            self.kill_port_process(5173)
            print("✅ Frontend stopped successfully")
            return True, "FaultExplainer frontend stopped"
        except Exception as e:
            print(f"❌ Exception stopping frontend: {e}")
            return False, f"Failed to stop frontend: {e}"

    def stop_all_processes(self):
        """Stop all running processes but keep system restartable."""
        print("🛑 STOP ALL: Stopping TEP processes (system remains restartable)...")

        # Stop TEP simulation first
        self.tep_running = False
        print("✅ TEP simulation stopped")

        # Stop all tracked processes (but don't clear the dict!)
        for name, process in list(self.processes.items()):
            try:
                print(f"🔪 Terminating {name} (PID: {process.pid})")
                process.terminate()
                # Wait up to 3 seconds for graceful shutdown
                try:
                    process.wait(timeout=3)
                    print(f"✅ {name} terminated gracefully")
                except subprocess.TimeoutExpired:
                    print(f"💀 Force killing {name}")
                    process.kill()
                    process.wait()

                # Remove terminated process from dict
                del self.processes[name]

            except Exception as e:
                print(f"⚠️ Error stopping {name}: {e}")

        # DON'T kill processes by port - let them terminate gracefully
        # This allows processes to be restarted without conflicts

        # Clean up data files
        try:
            data_file = "data/live_tep_data.csv"
            if os.path.exists(data_file):
                with open(data_file, 'w') as f:
                    f.write("")  # Clear the file
                print("🗑️ Cleared data file")
        except Exception as e:
            print(f"⚠️ Could not clear data file: {e}")

        print("🎉 Emergency stop complete - all processes terminated")

    def check_process_status(self, process_name):
        """Check if a process is actually running."""
        if process_name not in self.processes:
            return False

        process = self.processes[process_name]
        if process.poll() is None:  # Process is still running
            return True
        else:  # Process has terminated
            del self.processes[process_name]
            return False

    def get_status(self):
        """Get current system status (includes backend counters if reachable)."""
        backend_agg = None
        backend_buf = None
        backend_reachable = False
        try:
            import requests
            # Check backend status endpoint
            try:
                r = requests.get('http://127.0.0.1:8000/api/status', timeout=1.5)
                if r.ok:
                    js = r.json()
                    backend_agg = js.get('aggregated_count')
                    backend_buf = js.get('live_buffer')
                    backend_reachable = True
            except Exception:
                pass  # Backend not reachable
        except Exception as e:
            self.last_error = f"backend status: {e}"

        # Get latest TEP data for DisturbanceEffectsPage
        latest_data = {}
        if len(self.raw_data_queue) > 0:
            latest_point = self.raw_data_queue[-1]  # Get most recent data point
            latest_data = {}
            # Convert numpy arrays to lists for JSON serialization
            for key, value in latest_point.items():
                if hasattr(value, 'tolist'):  # numpy array
                    latest_data[key] = value.tolist()
                else:
                    latest_data[key] = value

        # Consider backend running if either we launched it OR it's reachable via HTTP
        backend_running_flag = self.check_process_status('faultexplainer_backend') or backend_reachable

        return {
            'tep_running': self.tep_running,
            'current_step': self.current_step,
            'step_interval_seconds': self.step_interval_seconds,
            'speed_mode': self.speed_mode,
            'current_preset': self.current_preset,
            'speed_factor': getattr(self, 'speed_factor', 1.0),
            'raw_data_points': len(self.raw_data_queue),
            'pca_data_points': len(self.pca_data_queue),
            'llm_data_points': len(self.llm_data_queue),
            'last_loop_at': getattr(self, 'last_loop_at', 0),
            'last_ingest_at': getattr(self, 'last_ingest_at', 0),
            'last_ingest_ok': getattr(self, 'last_ingest_ok', False),
            'csv_rows': getattr(self, 'csv_rows', 0),
            'csv_bytes': getattr(self, 'csv_bytes', 0),
            'last_ingest_info': getattr(self, 'last_ingest_info', {}),
            'last_error': getattr(self, 'last_error', ''),
            'backend_aggregated_count': backend_agg,
            'backend_live_buffer': backend_buf,
            'active_processes': list(self.processes.keys()),
            'backend_running': backend_running_flag,
            'frontend_running': self.check_process_status('faultexplainer_frontend'),
            'bridge_running': self.check_process_status('tep_bridge'),
            'idv_values': self.idv_values.tolist(),
            'latest_data': latest_data  # Add this for DisturbanceEffectsPage
        }

    def system_health_check(self):
        """Comprehensive system health check with detailed diagnostics."""
        status = self.get_status()
        health = {
            'overall_status': 'UNKNOWN',
            'components': {},
            'issues': [],
            'recommendations': []
        }

        # Check TEP Simulation
        simulation_active = (
            status['tep_running'] and
            hasattr(self, 'simulation_thread') and
            self.simulation_thread and
            self.simulation_thread.is_alive() and
            (time.time() - status['last_loop_at'] < max(300, status['step_interval_seconds'] * 2))
        )

        if status['tep_running'] and simulation_active:
            health['components']['tep_simulation'] = '✅ RUNNING'
        elif status['tep_running'] and not simulation_active:
            health['components']['tep_simulation'] = '⚠️ STARTED BUT NOT ACTIVE'
            health['issues'].append('TEP simulation thread may have crashed')
            health['recommendations'].append('Click "⟳ Restart TEP" to fix simulation thread')
        else:
            health['components']['tep_simulation'] = '❌ STOPPED'
            health['issues'].append('TEP simulation not started')
            health['recommendations'].append('Click "▶️ Start TEP" to begin simulation')

        # Check Backend
        if status['backend_running']:
            health['components']['backend'] = '✅ RUNNING'
        else:
            health['components']['backend'] = '❌ STOPPED'
            health['issues'].append('FaultExplainer backend not reachable')
            health['recommendations'].append('Click "▶️ Start Backend" to start analysis engine')

        # Check Data Flow
        data_flow_active = (
            simulation_active and
            status['backend_running'] and
            status['last_ingest_at'] > 0 and
            (time.time() - status['last_ingest_at'] < max(600, status['step_interval_seconds'] * 3))
        )

        if data_flow_active:
            health['components']['data_bridge'] = '✅ ACTIVE'
        else:
            health['components']['data_bridge'] = '❌ INACTIVE'
            health['issues'].append('No data flow between TEP and FaultExplainer')

        # Check Frontend (optional)
        if status['frontend_running']:
            health['components']['frontend'] = '✅ RUNNING'
        else:
            health['components']['frontend'] = '⚠️ STOPPED (Optional)'

        # Overall Status
        critical_issues = len([i for i in health['issues'] if 'TEP' in i or 'backend' in i])
        if critical_issues == 0:
            health['overall_status'] = '✅ READY'
        elif critical_issues == 1:
            health['overall_status'] = '⚠️ PARTIAL'
        else:
            health['overall_status'] = '❌ NOT READY'

        return health

class UnifiedControlPanel:
    """Unified control panel for TEP system."""

    def __init__(self):
        self.app = Flask(__name__)

        # Enable CORS for React frontend (port 5173)
        CORS(self.app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}})

        self.bridge = TEPDataBridge()
        self.baseline_data = None  # Will be loaded when user clicks "Load Baseline"

        # SSE (Server-Sent Events) support for real-time updates
        self.sse_queues = []  # List of queues for multiple clients
        self.sse_lock = threading.Lock()  # Thread-safe queue management

        # 🔧 FIX: XMEAS to descriptive name mapping for MultiLLM backend
        self.xmeas_to_descriptive = {
            'XMEAS_1': 'A Feed',
            'XMEAS_2': 'D Feed',
            'XMEAS_3': 'E Feed',
            'XMEAS_4': 'A and C Feed',
            'XMEAS_5': 'Recycle Flow',
            'XMEAS_6': 'Reactor Feed Rate',
            'XMEAS_7': 'Reactor Pressure',
            'XMEAS_8': 'Reactor Level',
            'XMEAS_9': 'Reactor Temperature',
            'XMEAS_10': 'Purge Rate',
            'XMEAS_11': 'Product Sep Temp',
            'XMEAS_12': 'Product Sep Level',
            'XMEAS_13': 'Product Sep Pressure',
            'XMEAS_14': 'Product Sep Underflow',
            'XMEAS_15': 'Stripper Level',
            'XMEAS_16': 'Stripper Pressure',
            'XMEAS_17': 'Stripper Underflow',
            'XMEAS_18': 'Stripper Temp',
            'XMEAS_19': 'Stripper Steam Flow',
            'XMEAS_20': 'Compressor Work',
            'XMEAS_21': 'Reactor Coolant Temp',
            'XMEAS_22': 'Separator Coolant Temp'
        }

        self.setup_routes()
        print("✅ Unified Control Panel initialized")

    def broadcast_sse(self, event_type, data):
        """Broadcast an SSE event to all connected clients"""
        with self.sse_lock:
            dead_queues = []
            for q in self.sse_queues:
                try:
                    q.put_nowait({
                        'event': event_type,
                        'data': data,
                        'timestamp': time.time()
                    })
                except queue.Full:
                    # Queue is full, client is too slow - disconnect it
                    dead_queues.append(q)

            # Remove dead/slow clients
            for q in dead_queues:
                try:
                    self.sse_queues.remove(q)
                except ValueError:
                    pass

    def convert_xmeas_to_descriptive(self, data_dict):
        """Convert XMEAS_X format to descriptive names for MultiLLM backend"""
        converted = {}
        for key, value in data_dict.items():
            if key in self.xmeas_to_descriptive:
                converted[self.xmeas_to_descriptive[key]] = value
            else:
                converted[key] = value
        return converted

    def setup_routes(self):
        """Setup Flask routes."""

        @self.app.route('/')
        def index():
            # Use timestamp for aggressive cache-busting (Safari compatibility)
            import time
            js_cache_buster = str(int(time.time()))
            return render_template('control_panel.html', js_cache_buster=js_cache_buster)

        @self.app.route('/chat')
        def chat_page():
            """Interactive RCA Chat page"""
            # Read and serve the chat HTML file
            script_dir = os.path.dirname(os.path.abspath(__file__))
            chat_html_path = os.path.join(script_dir, 'templates', 'interactive_chat.html')
            if os.path.exists(chat_html_path):
                with open(chat_html_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return "Chat page not found", 404



        @self.app.route('/static/<path:filename>')
        def static_files(filename):
            response = send_from_directory('.', os.path.join('static', filename))
            # Add no-cache headers for Safari compatibility
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response

        @self.app.route('/stream')
        def stream():
            """Server-Sent Events (SSE) endpoint for real-time updates"""
            def generate():
                # Create a queue for this client
                client_queue = queue.Queue(maxsize=100)

                # Register this client
                with self.sse_lock:
                    self.sse_queues.append(client_queue)

                print(f"✅ SSE client connected (total: {len(self.sse_queues)})")

                try:
                    # Send initial connection event
                    yield f"data: {json.dumps({'event': 'connected', 'message': 'SSE stream established'})}\n\n"

                    # Keep connection alive and send events
                    while True:
                        try:
                            # Wait for events with timeout for heartbeat
                            event = client_queue.get(timeout=30)

                            # Send the event to client
                            event_data = {
                                'event': event.get('event'),
                                'data': event.get('data'),
                                'timestamp': event.get('timestamp')
                            }
                            yield f"data: {json.dumps(event_data)}\n\n"

                        except queue.Empty:
                            # Send heartbeat every 30 seconds to keep connection alive
                            yield f": heartbeat\n\n"

                except GeneratorExit:
                    # Client disconnected
                    print(f"❌ SSE client disconnected")
                finally:
                    # Remove this client's queue
                    with self.sse_lock:
                        try:
                            self.sse_queues.remove(client_queue)
                            print(f"🔄 SSE client removed (remaining: {len(self.sse_queues)})")
                        except ValueError:
                            pass

            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                    'Connection': 'keep-alive'
                }
            )

        @self.app.route('/api/status')
        def get_status():
            import time
            from flask import request

            # DEBUG: Log every request to identify spam source
            current_time = time.strftime('%H:%M:%S', time.localtime())
            user_agent = request.headers.get('User-Agent', 'Unknown')[:50]
            referer = request.headers.get('Referer', 'No-Referer')
            remote_addr = request.remote_addr

            print(f"🔍 [{current_time}] /api/status from {remote_addr} | UA: {user_agent}... | Ref: {referer}")

            return jsonify(self.bridge.get_status())

        @self.app.route('/api/health')
        def health_check():
            return jsonify(self.bridge.system_health_check())

        @self.app.route('/api/ultra_start', methods=['POST'])
        def ultra_start():
            """One-click ultra-fast startup: Start everything at 50x speed"""
            try:
                results = []

                # Step 1: Set ultra speed first (50x)
                results.append("🚀 Setting ultra speed (50x)...")
                self.bridge.speed_factor = 50.0
                self.bridge.step_interval_seconds = 180 / 50.0  # 3.6 seconds
                self.bridge.speed_mode = 'fast_50x'
                results.append(f"✅ Speed set to 50x (interval: {self.bridge.step_interval_seconds:.1f}s)")

                # Step 2: Auto-start FaultExplainer Backend
                results.append("🔧 Starting FaultExplainer backend...")
                backend_available = False
                try:
                    import requests
                    # First check if backend already running
                    try:
                        response = requests.get('http://127.0.0.1:8000/status', timeout=1)
                        if response.status_code == 200:
                            results.append("✅ Backend already running on port 8000")
                            backend_available = True
                    except:
                        # Backend not running, start it
                        backend_success, backend_message = self.bridge.start_faultexplainer_backend()
                        if backend_success:
                            results.append("✅ Backend started successfully")
                            backend_available = True
                            time.sleep(2)  # Wait for backend to initialize
                        else:
                            results.append(f"⚠️ Backend start failed: {backend_message}")
                            results.append("ℹ️  Continuing without external backend (using unified mode)")
                            backend_available = False
                except Exception as e:
                    results.append(f"⚠️ Backend error: {str(e)}")
                    results.append("ℹ️  Continuing without external backend (using unified mode)")
                    backend_available = False

                # Step 3: Start TEP simulation with ultra speed
                import time
                results.append("🏭 Starting TEP simulation at 50x speed...")
                tep_success, tep_message = self.bridge.start_tep_simulation()
                if not tep_success:
                    return jsonify({
                        'success': False,
                        'message': f"❌ TEP failed: {tep_message}"
                    })
                results.append("✅ TEP simulation started at ultra speed")

                # Step 4: Auto-start Bridge (if backend is available)
                if backend_available:
                    results.append("🌉 Starting data bridge...")
                    try:
                        # Check if bridge already running
                        if 'tep_bridge' in self.bridge.processes and self.bridge.check_process_status('tep_bridge'):
                            results.append("✅ Bridge already running")
                        else:
                            # Start bridge
                            import subprocess
                            script_dir = os.path.dirname(os.path.abspath(__file__))
                            venv_python = os.path.join(script_dir, '.venv','bin','python')
                            bridge_script = os.path.join(script_dir, 'backend', 'tep_faultexplainer_bridge.py')

                            # 🔧 FIX: Check if files exist before starting
                            if not os.path.exists(venv_python):
                                results.append(f"⚠️ Bridge start failed: Virtual environment python not found at {venv_python}")
                                results.append(f"💡 Hint: Try using system python or check .venv installation")
                            elif not os.path.exists(bridge_script):
                                results.append(f"⚠️ Bridge start failed: Bridge script not found at {bridge_script}")
                            else:
                                # 🔧 FIX: Open log file for bridge output
                                bridge_log = os.path.join(script_dir, 'bridge.log')
                                log_file = open(bridge_log, 'w')

                                # 🔧 FIX: Start bridge with output to log file (not PIPE)
                                process = subprocess.Popen(
                                    [venv_python, bridge_script],
                                    cwd=script_dir,
                                    stdout=log_file,
                                    stderr=subprocess.STDOUT,
                                    start_new_session=True  # Detach from parent
                                )
                                self.bridge.processes['tep_bridge'] = process
                                results.append(f"✅ Bridge started (PID: {process.pid}) - connecting TEP to FaultExplainer")
                                results.append(f"📋 Bridge logs: {bridge_log}")
                                time.sleep(2)  # Wait longer for bridge to initialize

                                # 🔧 FIX: Check if process is still alive
                                if process.poll() is not None:
                                    results.append(f"⚠️ Bridge process exited immediately (check {bridge_log})")
                                else:
                                    results.append("✅ Bridge is running")
                    except Exception as e:
                        import traceback
                        results.append(f"⚠️ Bridge start failed: {str(e)}")
                        results.append(f"📋 Full error: {traceback.format_exc()}")
                else:
                    results.append("ℹ️  Bridge not started (no external backend)")

                # Step 5: Start frontend (optional)
                results.append("🖥️ Starting FaultExplainer frontend...")
                try:
                    frontend_success, frontend_message = self.bridge.start_faultexplainer_frontend()
                    if frontend_success:
                        results.append("✅ Frontend started")
                    else:
                        results.append("⚠️ Frontend start failed (optional)")
                except:
                    results.append("⚠️ Frontend start failed (optional)")

                # Step 6: Final verification
                time.sleep(1)
                health = self.bridge.system_health_check()

                results.append("🎉 ULTRA-FAST SYSTEM READY!")
                results.append(f"📊 Data points every {self.bridge.step_interval_seconds:.1f} seconds")
                if backend_available:
                    results.append("🤖 External MultiLLM Backend: Connected")
                else:
                    results.append("🤖 Using unified control panel (no external backend)")
                results.append("⚡ 50x speed = 50x faster than real-time!")

                return jsonify({
                    'success': True,
                    'message': '\n'.join(results),
                    'speed_factor': 50.0,
                    'interval_seconds': self.bridge.step_interval_seconds,
                    'health': health
                })

            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f"❌ Ultra start failed: {str(e)}"
                })

        @self.app.route('/api/tep/start', methods=['POST'])
        def start_tep():
            success, message = self.bridge.start_tep_simulation()
            # Handle form submissions by redirecting back to main page
            if request.content_type and 'application/x-www-form-urlencoded' in request.content_type:
                return redirect(url_for('index'))
            return jsonify({'success': success, 'message': message})

        @self.app.route('/api/tep/restart', methods=['POST'])
        def restart_tep():
            success, message = self.bridge.restart_tep_simulation()
            return jsonify({'success': success, 'message': message})

        @self.app.route('/api/tep/stop', methods=['POST'])
        def stop_tep():
            success, message = self.bridge.stop_tep_simulation()
            return jsonify({'success': success, 'message': message})

        @self.app.route('/api/pca/train', methods=['POST'])
        def start_pca_training_api():
            self.bridge.start_pca_training()
            return jsonify({
                'success': True,
                'message': f'Anomaly Detection training started, will collect {self.bridge.pca_training_target} data points',
                'target': self.bridge.pca_training_target
            })

        @self.app.route('/api/pca/status', methods=['GET'])
        def pca_training_status():
            return jsonify({
                'training_mode': bool(self.bridge.pca_training_mode),
                'collected': len(self.bridge.pca_training_data),
                'target': self.bridge.pca_training_target,
                'progress': len(self.bridge.pca_training_data) / self.bridge.pca_training_target * 100,
                'is_stable': bool(self.bridge.is_stable),
                'stability_buffer_size': len(self.bridge.stability_buffer)
            })

        @self.app.route('/api/pca/stabilize', methods=['POST'])
        def stabilize_pca():
            """Smart Anomaly Detection retraining: collect stable data and retrain."""
            if self.bridge.is_stable:
                self.bridge.start_pca_training()
                return jsonify({
                    'success': True,
                    'message': f'Anomaly Detection stabilization started. System is stable, collecting {self.bridge.pca_training_target} data points.',
                    'is_stable': True
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'System is not stable yet. Wait for stability before retraining.',
                    'is_stable': False
                })

        @self.app.route('/api/speed', methods=['POST'])
        def set_speed():
            # Be tolerant to missing/invalid JSON; allow query or form fallback
            data = request.get_json(silent=True) or {}
            mode = data.get('mode') or request.args.get('mode') or request.form.get('mode') or 'demo'
            # Optional: allow specifying demo seconds (1..10)
            try:
                seconds = int(data.get('seconds')) if data.get('seconds') is not None else None
            except Exception:
                seconds = None
            if mode == 'demo':
                self.bridge.speed_mode = 'demo'
                if seconds is None:
                    seconds = getattr(self.bridge, 'step_interval_seconds', 1) or 1
                seconds = max(1, min(10, int(seconds)))
                self.bridge.step_interval_seconds = seconds
            else:
                self.bridge.step_interval_seconds = 180
                self.bridge.speed_mode = 'real'
            return jsonify({'success': True, 'mode': self.bridge.speed_mode, 'step_interval_seconds': self.bridge.step_interval_seconds})

        @self.app.route('/api/speed/factor', methods=['POST'])
        def set_speed_factor():
            """New API endpoint for speed factor control (0.1x to 10x)"""
            try:
                data = request.get_json() or {}
                speed_factor = float(data.get('speed_factor', 1.0))

                # Validate range - Extended to 50x for ultra-fast testing
                speed_factor = max(0.1, min(50.0, speed_factor))

                # Store speed factor for TEP simulation (now implemented in Fortran!)
                self.bridge.speed_factor = speed_factor

                # ✅ IMPLEMENTED: Speed factor now affects actual Fortran physics simulation
                # The speed factor is passed to temain_with_speed() which scales DELTAT
                # Also adjust Python loop timing for consistency
                base_interval = 180  # 3 minutes normal
                new_interval = max(1, int(base_interval / speed_factor))
                self.bridge.step_interval_seconds = new_interval

                # Update mode based on speed
                if speed_factor >= 1.0:
                    self.bridge.speed_mode = f'fast_{speed_factor}x'
                else:
                    self.bridge.speed_mode = f'slow_{speed_factor}x'

                return jsonify({
                    'success': True,
                    'speed_factor': speed_factor,
                    'step_interval_seconds': new_interval,
                    'mode': self.bridge.speed_mode,
                    'description': f'Simulation running at {speed_factor}x speed'
                })

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 400

        @self.app.route('/api/xmv/set', methods=['POST'])
        def set_xmv():
            data = request.get_json()
            xmv_num = data.get('xmv_num')
            value = data.get('value')

            success = self.bridge.set_xmv(xmv_num, value)
            return jsonify({
                'success': success,
                'xmv_num': xmv_num,
                'value': float(value) if success else None,
                'current_xmv_state': self.bridge.xmv_values.tolist() if hasattr(self.bridge, 'xmv_values') else None
            })

        @self.app.route('/api/idv/set', methods=['POST'])
        def set_idv():
            data = request.get_json()
            idv_num = data.get('idv_num')
            value = data.get('value')

            success = self.bridge.set_idv(idv_num, value)

            # Return current IDV state for debugging
            return jsonify({
                'success': success,
                'idv_num': idv_num,
                'value': int(value) if success else None,
                'current_idv_state': self.bridge.idv_values.tolist(),
                'active_faults': [i+1 for i, v in enumerate(self.bridge.idv_values) if v == 1]
            })

        @self.app.route('/api/idv/test', methods=['POST'])
        def test_idv_impact():
            """Test if IDV changes actually affect simulation output."""
            try:
                # Run baseline simulation (all IDV = 0)
                baseline_idv = np.zeros(20)
                self.bridge.idv_values = baseline_idv.copy()
                baseline_data = self.bridge.run_tep_simulation_step()

                # Run with IDV_1 = 1 (A/C Feed Ratio fault)
                test_idv = np.zeros(20)
                test_idv[0] = 1  # IDV_1
                self.bridge.idv_values = test_idv.copy()
                fault_data = self.bridge.run_tep_simulation_step()

                # Compare key measurements
                if baseline_data and fault_data:
                    comparison = {
                        'baseline_reactor_temp': baseline_data.get('XMEAS_9', 'N/A'),
                        'fault_reactor_temp': fault_data.get('XMEAS_9', 'N/A'),
                        'baseline_reactor_pressure': baseline_data.get('XMEAS_7', 'N/A'),
                        'fault_reactor_pressure': fault_data.get('XMEAS_7', 'N/A'),
                        'difference_detected': baseline_data != fault_data,
                        'test_successful': True
                    }
                else:
                    comparison = {'test_successful': False, 'error': 'No simulation data'}

                return jsonify(comparison)

            except Exception as e:
                return jsonify({'test_successful': False, 'error': str(e)})

        @self.app.route('/api/faultexplainer/backend/start', methods=['POST'])
        def start_backend():
            mode = (request.get_json(silent=True) or {}).get('mode', 'prod')
            if mode == 'dev':
                success, message = self.bridge.start_faultexplainer_backend_dev()
            else:
                success, message = self.bridge.start_faultexplainer_backend()
            # Handle form submissions by redirecting back to main page
            if request.content_type and 'application/x-www-form-urlencoded' in request.content_type:
                return redirect(url_for('index'))
            return jsonify({'success': success, 'message': message})

        @self.app.route('/api/faultexplainer/backend/stop', methods=['POST'])
        def stop_backend():
            success, message = self.bridge.stop_faultexplainer_backend()
            return jsonify({'success': success, 'message': message})

        @self.app.route('/api/logs/<name>')
        def get_log(name):
            # Only allow known names
            if name not in ('sse','ingest'):
                return jsonify({'error':'invalid log'}), 400
            # Get script directory and build path to local backend diagnostics
            script_dir = os.path.dirname(os.path.abspath(__file__))
            bdir = os.path.join(script_dir, 'backend','diagnostics')
            path = os.path.join(bdir, f"{name}.log")
            try:
                if not os.path.exists(path):
                    return jsonify({'lines': [f'No log file found: {path}']}), 200
                with open(path,'r',encoding='utf-8',errors='replace') as f:
                    lines = f.readlines()[-200:]
                return jsonify({'lines': lines})
            except Exception as e:
                return jsonify({'lines': [f'Error reading log: {e}']}), 200

        @self.app.route('/api/analysis/history/download/<fmt>')
        def download_history(fmt):
            # Get script directory and build path to local backend diagnostics
            script_dir = os.path.dirname(os.path.abspath(__file__))
            diag_dir = os.path.join(script_dir, 'backend','diagnostics')
            if fmt == 'jsonl':
                path = os.path.join(diag_dir, 'analysis_history.jsonl')
                if not os.path.exists(path):
                    return jsonify({'error':'missing'}), 404
                return self._send_file(path, 'application/json')
            if fmt == 'md':
                path = os.path.join(diag_dir, 'analysis_history.md')
                if not os.path.exists(path):
                    return jsonify({'error':'missing'}), 404
                return self._send_file(path, 'text/markdown')
            return jsonify({'error':'invalid fmt'}), 400

        def _send_file(self, path, mime):
            from flask import send_file
            return send_file(path, mimetype=mime, as_attachment=True)
        @self.app.route('/api/analysis/history/download/bydate/<datestr>')
        def download_history_by_date(datestr):
            # datestr format: YYYY-MM-DD
            # Get script directory and build path to local backend diagnostics
            script_dir = os.path.dirname(os.path.abspath(__file__))
            diag_dir = os.path.join(script_dir, 'backend','diagnostics','analysis_history')
            path = os.path.join(diag_dir, f"{datestr}.md")
            if not os.path.exists(path):
                return jsonify({'error':'missing'}), 404
            return self._send_file(path, 'text/markdown')

        # ========== SNAPSHOT MANAGER ENDPOINTS ==========

        @self.app.route('/api/snapshots/list', methods=['GET'])
        def list_snapshots():
            """List all available snapshots from local file"""
            try:
                limit = int(request.args.get('limit', 50))
                script_dir = os.path.dirname(os.path.abspath(__file__))
                history_file = os.path.join(script_dir, 'backend', 'diagnostics', 'analysis_history.jsonl')

                if not os.path.exists(history_file):
                    return jsonify({'snapshots': [], 'source': 'local_file', 'message': 'No history file found'}), 200

                snapshots = []
                with open(history_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-limit:]:
                        if line.strip():
                            try:
                                snap = json.loads(line)
                                snapshot_meta = {
                                    'id': snap.get('id'),
                                    'timestamp': snap.get('timestamp'),
                                    'time': snap.get('time'),
                                    'name': snap.get('name', f"Analysis {snap.get('id')}"),
                                    'tags': snap.get('tags', []),
                                    'has_llm_analysis': bool(snap.get('llm_analyses')),
                                    'has_ai_enhancement': bool(snap.get('ai_agent_enhancement')),
                                    'llm_models': list(snap.get('llm_analyses', {}).keys()),
                                    'feature_count': len(snap.get('feature_analysis', '').split('\n')) if snap.get('feature_analysis') else 0
                                }
                                snapshots.append(snapshot_meta)
                            except json.JSONDecodeError:
                                continue

                return jsonify({'snapshots': snapshots, 'total': len(snapshots), 'source': 'local_file'}), 200
            except Exception as e:
                return jsonify({'error': str(e), 'snapshots': []}), 500

        @self.app.route('/api/snapshots/get/<int:snapshot_id>', methods=['GET'])
        def get_snapshot(snapshot_id):
            """Get full snapshot data by ID"""
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                history_file = os.path.join(script_dir, 'backend', 'diagnostics', 'analysis_history.jsonl')

                if not os.path.exists(history_file):
                    return jsonify({'error': 'History file not found'}), 404

                with open(history_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                snap = json.loads(line)
                                if snap.get('id') == snapshot_id:
                                    return jsonify({'snapshot': snap, 'source': 'local_file'}), 200
                            except json.JSONDecodeError:
                                continue

                return jsonify({'error': 'Snapshot not found'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/snapshots/rename', methods=['POST'])
        def rename_snapshot():
            """Rename a snapshot"""
            try:
                data = request.get_json()
                snapshot_id = data.get('id')
                new_name = data.get('name')
                tags = data.get('tags', [])

                if not snapshot_id or not new_name:
                    return jsonify({'error': 'id and name are required'}), 400

                script_dir = os.path.dirname(os.path.abspath(__file__))
                history_file = os.path.join(script_dir, 'backend', 'diagnostics', 'analysis_history.jsonl')

                if not os.path.exists(history_file):
                    return jsonify({'error': 'History file not found'}), 404

                snapshots = []
                updated = False
                with open(history_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                snap = json.loads(line)
                                if snap.get('id') == snapshot_id:
                                    snap['name'] = new_name
                                    snap['tags'] = tags
                                    snap['last_modified'] = datetime.now().isoformat()
                                    updated = True
                                snapshots.append(snap)
                            except json.JSONDecodeError:
                                continue

                if not updated:
                    return jsonify({'error': 'Snapshot not found'}), 404

                with open(history_file, 'w', encoding='utf-8') as f:
                    for snap in snapshots:
                        f.write(json.dumps(snap, ensure_ascii=False) + '\n')

                return jsonify({'status': 'success', 'message': 'Snapshot renamed'}), 200
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # ========== ENHANCED CHAT ENDPOINTS ==========

        @self.app.route('/api/chat/enhanced', methods=['POST'])
        def chat_enhanced():
            """Enhanced chat with Claude and RAG integration"""
            try:
                # Proxy to backend if available
                try:
                    import requests
                    r = requests.post('http://127.0.0.1:8000/chat', json=request.get_json(), timeout=30)
                    return jsonify(r.json()), r.status_code
                except:
                    return chat_enhanced_local()
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        def chat_enhanced_local():
            """Local implementation of enhanced chat"""
            data = request.get_json()
            analysis_id = data.get('analysis_id')
            query = data.get('query', '').strip()

            if not query:
                return jsonify({'error': 'query is required'}), 400

            script_dir = os.path.dirname(os.path.abspath(__file__))
            history_file = os.path.join(script_dir, 'backend', 'diagnostics', 'analysis_history.jsonl')

            snapshot = None
            with open(history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            snap = json.loads(line)
                            if snap.get('id') == analysis_id:
                                snapshot = snap
                                break
                        except json.JSONDecodeError:
                            continue

            if not snapshot:
                return jsonify({'error': 'Snapshot not found'}), 404

            answer = f"Based on the snapshot analysis:\n\nQuestion: {query}\n\n"
            answer += "I've reviewed the analysis data. "
            answer += "Please note: Full AI analysis requires the backend to be running on port 8000."

            return jsonify({
                'answer': answer,
                'analysis_id': analysis_id,
                'used_snapshot': True,
                'mode': 'local_fallback'
            }), 200

        @self.app.route('/api/context/ruled_out', methods=['POST'])
        def context_ruled_out():
            """Save ruled-out hypothesis"""
            try:
                try:
                    import requests
                    r = requests.post('http://127.0.0.1:8000/context/ruled_out', json=request.get_json(), timeout=10)
                    return jsonify(r.json()), r.status_code
                except:
                    return jsonify({'ok': True, 'mode': 'local_fallback'}), 200
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/report/generate', methods=['POST'])
        def generate_report():
            """Generate and send RCA report"""
            try:
                data = request.get_json()
                snapshot_id = data.get('snapshot_id')
                conclusion = data.get('conclusion', '')
                email = data.get('email', 'tep-rca-system@example.com')
                chat_history = data.get('chat_history', [])
                ruled_out = data.get('ruled_out', [])

                if not snapshot_id:
                    return jsonify({'error': 'snapshot_id is required'}), 400

                # Convert snapshot_id to int for comparison (IDs are stored as integers)
                try:
                    snapshot_id = int(snapshot_id)
                except (ValueError, TypeError):
                    return jsonify({'error': 'Invalid snapshot_id format'}), 400

                script_dir = os.path.dirname(os.path.abspath(__file__))
                history_file = os.path.join(script_dir, 'backend', 'diagnostics', 'analysis_history.jsonl')

                # Check if history file exists
                if not os.path.exists(history_file):
                    return jsonify({'error': f'Analysis history file not found: {history_file}'}), 404

                # Load snapshot from JSONL
                snapshot = None
                with open(history_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                snap = json.loads(line)
                                # Compare as integers
                                if snap.get('id') == snapshot_id:
                                    snapshot = snap
                                    break
                            except json.JSONDecodeError as e:
                                print(f"⚠️ Failed to parse line in analysis_history.jsonl: {e}")
                                continue

                if not snapshot:
                    return jsonify({'error': f'Snapshot with ID {snapshot_id} not found in history'}), 404

                # Import report generation modules from backend directory
                import sys
                backend_dir = os.path.join(script_dir, 'backend')
                if backend_dir not in sys.path:
                    sys.path.insert(0, backend_dir)

                from report_generator import generate_pdf_report
                from email_sender import send_report_email, generate_report_email_body

                # Generate PDF report (falls back to Markdown if reportlab not installed)
                report_path = generate_pdf_report(snapshot, chat_history, ruled_out, conclusion)
                report_format = 'PDF' if report_path.endswith('.pdf') else 'Markdown'

                # Generate email body
                email_body = generate_report_email_body(
                    snapshot_id=snapshot_id,
                    snapshot_name=snapshot.get('timestamp', f'Analysis {snapshot_id}'),
                    conclusion=conclusion,
                    report_filename=os.path.basename(report_path)
                )

                # Try to send email (will gracefully fail if SMTP not configured)
                email_sent = send_report_email(
                    recipient=email,
                    subject=f"TEP RCA Report - {snapshot.get('timestamp', snapshot_id)}",
                    body_html=email_body,
                    attachments=[report_path]
                )

                return jsonify({
                    'status': 'success' if email_sent else 'saved_locally',
                    'recipient': email,
                    'filename': os.path.basename(report_path),
                    'filepath': report_path,
                    'format': report_format,
                    'email_sent': email_sent,
                    'message': 'Report generated and sent' if email_sent else 'Report generated and saved locally'
                }), 200

            except Exception as e:
                import traceback
                print("❌ Error in /api/report/generate:")
                traceback.print_exc()
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/faultexplainer/frontend/start', methods=['POST'])
        def start_frontend():
            success, message = self.bridge.start_faultexplainer_frontend()
            # Handle form submissions by redirecting back to main page
            if request.content_type and 'application/x-www-form-urlencoded' in request.content_type:
                return redirect(url_for('index'))
            return jsonify({'success': success, 'message': message})

        @self.app.route('/api/faultexplainer/frontend/stop', methods=['POST'])
        def stop_frontend():
            success, message = self.bridge.stop_faultexplainer_frontend()
            return jsonify({'success': success, 'message': message})

        @self.app.route('/api/bridge/start', methods=['POST'])
        def start_bridge():
            # Start external bridge script in background
            try:
                # if already started, return
                if 'tep_bridge' in self.bridge.processes and self.bridge.check_process_status('tep_bridge'):
                    success, message = True, 'Bridge already running'
                else:
                    # Get current TEP_control directory for venv and bridge script
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    venv_python = os.path.join(script_dir, '.venv','bin','python')
                    bridge_script_dir = script_dir  # Bridge script is in TEP_control/backend/ subdirectory
                    process = subprocess.Popen([venv_python, 'backend/tep_faultexplainer_bridge.py'],
                                               cwd=bridge_script_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    self.bridge.processes['tep_bridge'] = process
                    success, message = True, 'Bridge started'
            except Exception as e:
                success, message = False, f'Bridge failed: {e}'

            # Handle form submissions by redirecting back to main page
            if request.content_type and 'application/x-www-form-urlencoded' in request.content_type:
                return redirect(url_for('index'))
            return jsonify({'success': success, 'message': message})

        @self.app.route('/api/bridge/stop', methods=['POST'])
        def stop_bridge():
            try:
                if 'tep_bridge' in self.bridge.processes:
                    self.bridge.processes['tep_bridge'].terminate()
                    del self.bridge.processes['tep_bridge']
                return jsonify({'success': True, 'message': 'Bridge stopped'})
            except Exception as e:
                return jsonify({'success': False, 'message': f'Failed to stop bridge: {e}'})

        # Backend config proxy (avoid CORS by posting from server-side)
        @self.app.route('/api/backend/config/runtime', methods=['POST'])
        def proxy_backend_runtime_config():
            try:
                payload = request.get_json() or {}
                if 'preset' in payload:
                    self.bridge.current_preset = payload['preset']
                    # Remove preset before forwarding
                    payload = {k:v for k,v in payload.items() if k!='preset'}
                r = requests.post('http://127.0.0.1:8000/config/runtime', json=payload, timeout=5)
                return jsonify(r.json()), r.status_code
            except Exception as e:
                return jsonify({'status':'error','error':str(e)}), 500

        @self.app.route('/api/llm/independent-results', methods=['GET'])
        def get_independent_llm_results():
            """Get independent LLM results for split display - Fixed for MultiLLM backend"""
            try:
                # 🔧 FIX: Use MultiLLM backend's /explain endpoint instead of /independent/status
                import requests

                # Check if we have recent analysis results
                if hasattr(self.bridge, 'last_llm_results') and self.bridge.last_llm_results:
                    # Return cached results from recent analysis
                    return jsonify(self.bridge.last_llm_results)

                # If no cached results, return empty state
                results = {
                    'lmstudio': {
                        'status': 'ready',
                        'message': 'LMStudio ready - waiting for anomaly to trigger analysis',
                        'timestamp': None,
                        'analysis': None
                    },
                    'gemini': {
                        'status': 'ready',
                        'message': 'Gemini ready - waiting for anomaly to trigger analysis',
                        'timestamp': None,
                        'analysis': None
                    }
                }

                return jsonify(results)

            except Exception as e:
                print(f"❌ Error getting independent LLM results: {str(e)}")
                # Return safe fallback
                return jsonify({
                    'lmstudio': {'status': 'error', 'message': 'Connection error'},
                    'gemini': {'status': 'error', 'message': 'Connection error'}
                }), 200

        @self.app.route('/api/backend/config/baseline/reload', methods=['POST'])
        def proxy_backend_baseline_reload():
                try:
                    # Load baseline data directly from local CSV file
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    baseline_path = os.path.join(script_dir, 'backend', 'data', 'normal_baseline.csv')

                    if os.path.exists(baseline_path):
                        import pandas as pd
                        baseline_df = pd.read_csv(baseline_path)

                        # Store baseline data for internal use
                        self.baseline_data = baseline_df

                        # Get feature count
                        feature_count = len([col for col in baseline_df.columns if col != 'time'])

                        print(f"✅ Baseline loaded: {len(baseline_df)} samples, {feature_count} features")
                        print(f"   Key values: Pressure={baseline_df['Reactor Pressure'].mean():.1f} kPa, Temp={baseline_df['Reactor Temperature'].mean():.1f}°C")

                        return jsonify({
                            'status': 'ok',
                            'features': feature_count,
                            'samples': len(baseline_df),
                            'message': f'Baseline loaded with {feature_count} features from {len(baseline_df)} samples'
                        }), 200
                    else:
                        return jsonify({
                            'status': 'error',
                            'error': f'Baseline file not found: {baseline_path}'
                        }), 404

                except Exception as e:
                    print(f"❌ Baseline reload error: {e}")
                    return jsonify({'status':'error','error':str(e)}), 500


        @self.app.route('/api/backend/config/alpha', methods=['POST'])
        def proxy_backend_alpha():
            try:
                payload = request.get_json() or {}
                r = requests.post('http://127.0.0.1:8000/config/alpha', json=payload, timeout=5)
                return jsonify(r.json()), r.status_code
            except Exception as e:
                return jsonify({'status':'error','error':str(e)}), 500

        # Backend analysis history proxy
        @self.app.route('/api/backend/analysis/history', methods=['GET'])
        def proxy_backend_analysis_history():
            try:
                limit = request.args.get('limit', '5')
                import requests
                r = requests.get(f'http://127.0.0.1:8000/analysis/history?limit={limit}', timeout=10)
                return jsonify(r.json()), r.status_code
            except Exception as e:
                return jsonify({'status':'error','error':str(e), 'message': 'Backend not reachable on port 8000. Make sure FaultExplainer backend is running.'}), 500

        # Proxy for downloading analysis by date
        @self.app.route('/api/backend/analysis/download/<date>', methods=['GET'])
        def proxy_backend_analysis_download(date):
            try:
                import requests
                r = requests.get(f'http://127.0.0.1:8000/analysis/download/{date}', timeout=10)
                # Return the response as-is (should be a file download)
                return Response(r.content, status=r.status_code, headers=dict(r.headers))
            except Exception as e:
                return jsonify({'status':'error','error':str(e), 'message': f'Backend not reachable or file not found for date {date}'}), 500

        # Download analysis history
        @self.app.route('/api/analysis/history/download/<format>')
        def download_analysis_history(format):
            try:
                limit = request.args.get('limit', '20')
                import requests
                r = requests.get(f'http://127.0.0.1:8000/analysis/history?limit={limit}', timeout=10)
                data = r.json()

                if format == 'jsonl':
                    # JSONL format - one JSON object per line
                    import json
                    lines = []
                    for item in data.get('items', []):
                        lines.append(json.dumps(item))
                    content = '\n'.join(lines)

                    from flask import Response
                    return Response(
                        content,
                        mimetype='application/jsonl',
                        headers={'Content-Disposition': f'attachment; filename=tep_analysis_history.jsonl'}
                    )

                elif format == 'md':
                    # Markdown format
                    lines = ['# TEP Analysis History\n']
                    for i, item in enumerate(data.get('items', []), 1):
                        ts = item.get('timestamp', 'Unknown time')
                        lines.append(f'## Analysis #{i} - {ts}\n')
                        lines.append(f'**Feature Analysis:**\n```\n{item.get("feature_analysis", "N/A")}\n```\n')

                        if 'performance_summary' in item:
                            lines.append('**Performance Summary:**\n')
                            for model, perf in item['performance_summary'].items():
                                lines.append(f'- {model}: {perf.get("response_time", 0):.2f}s, {perf.get("word_count", 0)} words\n')
                        lines.append('\n---\n')

                    content = '\n'.join(lines)
                    from flask import Response
                    return Response(
                        content,
                        mimetype='text/markdown',
                        headers={'Content-Disposition': f'attachment; filename=tep_analysis_history.md'}
                    )
                else:
                    return jsonify({'error': 'Invalid format. Use jsonl or md'}), 400

            except Exception as e:
                return jsonify({'error': str(e), 'message': 'Failed to download analysis history. Make sure backend is running.'}), 500

        @self.app.route('/api/stop/all', methods=['POST'])
        def stop_all():
            self.bridge.stop_tep_simulation()
            self.bridge.stop_all_processes()
            return jsonify({'success': True, 'message': 'All processes stopped'})

        @self.app.route('/api/emergency/shutdown', methods=['POST'])
        def emergency_shutdown():
            """Emergency shutdown - stops all processes immediately."""
            try:
                # Stop TEP simulation first
                try:
                    self.bridge.stop_tep_simulation()
                except Exception as e:
                    print(f"Warning: TEP simulation stop error: {e}")

                # Stop all tracked processes
                try:
                    self.bridge.stop_all_processes()
                except Exception as e:
                    print(f"Warning: Process stop error: {e}")

                # Kill specific ports as backup
                import subprocess
                ports_to_kill = [8000, 5173, 9001]  # Don't kill 9002 (unified console itself)
                for port in ports_to_kill:
                    try:
                        # Get PIDs listening on this port
                        result = subprocess.run(['lsof', '-ti', f':{port}'],
                                              capture_output=True, text=True, timeout=2)
                        pids = result.stdout.strip().split('\n')

                        # Kill each PID
                        for pid in pids:
                            if pid:  # Skip empty strings
                                try:
                                    subprocess.run(['kill', '-9', pid], timeout=2)
                                    print(f"✅ Killed process {pid} on port {port}")
                                except:
                                    pass
                    except:
                        pass

                # 🔧 NEW: Kill TEP Bridge (was missing - caused overnight charges!)
                try:
                    result = subprocess.run(['pkill', '-f', 'tep_faultexplainer_bridge'],
                                          capture_output=True, text=True, timeout=5)
                    print("✅ Killed TEP Bridge process")
                except Exception as e:
                    print(f"⚠️  TEP Bridge kill failed: {e}")

                return jsonify({
                    'success': True,
                    'message': 'Emergency shutdown completed - all processes stopped including bridge'
                })

            except Exception as e:
                print(f"Emergency shutdown error: {e}")
                return jsonify({
                    'success': False,
                    'message': f'Emergency shutdown failed: {str(e)}'
                })

        @self.app.route('/api/open-analysis-folder', methods=['POST'])
        def open_analysis_folder():
            """Open the analysis_history folder in Finder/File Explorer"""
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                analysis_folder = os.path.join(script_dir, 'backend', 'diagnostics', 'analysis_history')

                # Create folder if it doesn't exist
                os.makedirs(analysis_folder, exist_ok=True)

                # Open folder in Finder (macOS) or File Explorer (Windows/Linux)
                import platform
                import subprocess

                system = platform.system()
                if system == 'Darwin':  # macOS
                    subprocess.run(['open', analysis_folder])
                elif system == 'Windows':
                    subprocess.run(['explorer', analysis_folder])
                else:  # Linux
                    subprocess.run(['xdg-open', analysis_folder])

                return jsonify({
                    'success': True,
                    'message': 'Opened analysis history folder',
                    'path': analysis_folder
                })

            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/open-diagnostics-folder', methods=['POST'])
        def open_diagnostics_folder():
            """Open the diagnostics folder (where PDF reports are saved) in Finder/File Explorer"""
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                diagnostics_folder = os.path.join(script_dir, 'backend', 'diagnostics')

                # Create folder if it doesn't exist
                os.makedirs(diagnostics_folder, exist_ok=True)

                # Open folder in Finder (macOS) or File Explorer (Windows/Linux)
                import platform
                import subprocess

                system = platform.system()
                if system == 'Darwin':  # macOS
                    subprocess.run(['open', diagnostics_folder])
                elif system == 'Windows':
                    subprocess.run(['explorer', diagnostics_folder])
                else:  # Linux
                    subprocess.run(['xdg-open', diagnostics_folder])

                return jsonify({
                    'success': True,
                    'message': 'Opened diagnostics folder',
                    'path': diagnostics_folder
                })

            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        # IDV Fault Explanation API
        @self.app.route('/api/idv/explain/<int:idv_number>')
        def explain_idv(idv_number):
            """Explain what a specific IDV fault does physically."""
            explanations = {
                1: {
                    "name": "A/C Feed Ratio Change (Stream 4)",
                    "physical_meaning": "Changes the composition ratio of components A and C in the feed stream while keeping B constant",
                    "what_happens": "Component A decreases by 3% (48.5% → 45.5%), Component C increases by 3% (51.0% → 54.0%)",
                    "industrial_cause": "Feed preparation system malfunction, upstream process changes, feed tank mixing issues, or flow meter calibration drift",
                    "expected_behavior": {
                        "immediate": "Feed composition changes instantly (step change)",
                        "reactor": "Reaction kinetics change due to different A/C ratio",
                        "product": "Product quality affected - less A means lower conversion",
                        "control": "Controllers detect composition change and try to compensate by adjusting flow rates"
                    },
                    "measurements_affected": {
                        "primary": ["XMEAS(23-41): Composition measurements", "XMEAS(6): Reactor feed rate"],
                        "secondary": ["XMEAS(9): Reactor temperature", "XMEAS(7): Reactor pressure"]
                    },
                    "operator_expectations": {
                        "composition_analyzer": "Should show A component dropping from ~48.5% to ~45.5%",
                        "reactor_temperature": "May increase slightly due to different reaction heat",
                        "product_quality": "Product purity may decrease due to lower A conversion",
                        "control_response": "Feed flow controllers will adjust to maintain production rate"
                    },
                    "detection_difficulty": "Easy (95-99% detection rate)",
                    "severity": "Medium - affects product quality but process remains stable",
                    "fortran_implementation": "XST(1,4) = TESUB8(1,TIME) - IDV(1)*0.03D0"
                }
            }

            if idv_number in explanations:
                return jsonify(explanations[idv_number])
            else:
                return jsonify({
                    "error": f"IDV_{idv_number} explanation not available yet",
                    "available": list(explanations.keys())
                }), 404

        # Three-tier control system API endpoints

        @self.app.route('/api/setpoint/set', methods=['POST'])
        def set_setpoint():
            """Level 1: Set control setpoints."""
            try:
                data = request.get_json()
                setpoint_num = data.get('setpoint_num')
                value = data.get('value')

                print(f"🎯 Setting setpoint {setpoint_num} to {value}")

                # Update setpoint in TEP system
                if hasattr(self.bridge, 'set_setpoint'):
                    self.bridge.set_setpoint(setpoint_num, value)

                return jsonify({
                    'success': True,
                    'message': f'Setpoint {setpoint_num} set to {value}',
                    'setpoint_num': setpoint_num,
                    'value': value
                })

            except Exception as e:
                print(f"❌ Setpoint error: {e}")
                return jsonify({'success': False, 'message': str(e)}), 500

        @self.app.route('/api/manual/toggle', methods=['POST'])
        def toggle_manual():
            """Level 1: Toggle manual mode for XMV variables."""
            try:
                data = request.get_json()
                xmv_num = data.get('xmv_num')
                manual_mode = data.get('manual_mode')

                print(f"🔧 Toggle manual mode XMV_{xmv_num}: {manual_mode}")

                # Store manual mode state
                if not hasattr(self.bridge, 'manual_modes'):
                    self.bridge.manual_modes = {}
                self.bridge.manual_modes[xmv_num] = manual_mode

                return jsonify({
                    'success': True,
                    'message': f'XMV_{xmv_num} manual mode: {manual_mode}',
                    'xmv_num': xmv_num,
                    'manual_mode': manual_mode
                })

            except Exception as e:
                print(f"❌ Manual mode error: {e}")
                return jsonify({'success': False, 'message': str(e)}), 500

        @self.app.route('/api/process/composition', methods=['POST'])
        def adjust_composition():
            """Level 2: Adjust feed composition (maps to IDV faults)."""
            try:
                data = request.get_json()
                component = data.get('component')
                stream = data.get('stream')
                value = data.get('value')
                idv_equivalent = data.get('idv_equivalent')
                intensity = data.get('intensity')

                print(f"🧪 Composition adjustment: {component} in stream {stream} to {value}")
                print(f"   Equivalent to IDV_{idv_equivalent} with intensity {intensity}")

                # Map to IDV fault
                if idv_equivalent == 1:  # A/C Feed Ratio
                    self.bridge.set_idv(1, intensity)
                elif idv_equivalent == 2:  # B Composition
                    self.bridge.set_idv(2, intensity)

                return jsonify({
                    'success': True,
                    'message': f'{component} composition adjusted to {value*100:.1f}%',
                    'component': component,
                    'value': value,
                    'idv_equivalent': idv_equivalent
                })

            except Exception as e:
                print(f"❌ Composition adjustment error: {e}")
                return jsonify({'success': False, 'message': str(e)}), 500

        @self.app.route('/api/process/temperature', methods=['POST'])
        def adjust_temperature():
            """Level 2: Adjust process temperatures (maps to IDV faults)."""
            try:
                data = request.get_json()
                system = data.get('system')
                value = data.get('value')
                idv_equivalent = data.get('idv_equivalent')
                intensity = data.get('intensity')

                print(f"🌡️ Temperature adjustment: {system} to {value}°C")
                print(f"   Equivalent to IDV_{idv_equivalent} with intensity {intensity}")

                # Map to IDV fault
                if idv_equivalent == 4:  # Reactor cooling water
                    self.bridge.set_idv(4, intensity)
                elif idv_equivalent == 5:  # Condenser cooling water
                    self.bridge.set_idv(5, intensity)

                return jsonify({
                    'success': True,
                    'message': f'{system} temperature adjusted to {value}°C',
                    'system': system,
                    'value': value,
                    'idv_equivalent': idv_equivalent
                })

            except Exception as e:
                print(f"❌ Temperature adjustment error: {e}")
                return jsonify({'success': False, 'message': str(e)}), 500

        @self.app.route('/api/process/flow', methods=['POST'])
        def adjust_flow():
            """Level 2: Adjust flow availability (maps to IDV faults)."""
            try:
                data = request.get_json()
                component = data.get('component')
                availability = data.get('availability')
                idv_equivalent = data.get('idv_equivalent')
                intensity = data.get('intensity')

                print(f"💧 Flow adjustment: {component} availability to {availability}%")
                print(f"   Equivalent to IDV_{idv_equivalent} with intensity {intensity}")

                # Map to IDV fault
                if idv_equivalent == 6:  # A Feed Loss
                    self.bridge.set_idv(6, intensity)
                elif idv_equivalent == 7:  # C Header Pressure Loss
                    self.bridge.set_idv(7, intensity)

                return jsonify({
                    'success': True,
                    'message': f'{component} feed availability set to {availability}%',
                    'component': component,
                    'availability': availability,
                    'idv_equivalent': idv_equivalent
                })

            except Exception as e:
                print(f"❌ Flow adjustment error: {e}")
                return jsonify({'success': False, 'message': str(e)}), 500

        # Model control proxy endpoints
        @self.app.route('/api/models/status', methods=['GET'])
        def proxy_models_status():
            try:
                import requests
                r = requests.get('http://127.0.0.1:8000/models/status', timeout=10)
                return jsonify(r.json()), r.status_code
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/models/toggle', methods=['POST'])
        def proxy_models_toggle():
            try:
                payload = request.get_json() or {}
                import requests
                r = requests.post('http://127.0.0.1:8000/models/toggle', json=payload, timeout=10)
                return jsonify(r.json()), r.status_code
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    def cleanup_on_exit(self):
        """Cleanup all processes when GUI is closed."""
        print("\n🧹 GUI closed - cleaning up all processes...")
        try:
            # Stop all managed processes
            self.bridge.stop_all_processes()

            # Kill processes by port for comprehensive cleanup
            ports_to_clean = [9001, 8000, 5173, 1234]  # Control panel, backend, frontend, LMStudio
            for port in ports_to_clean:
                try:
                    if self.bridge.kill_port_process(port):
                        print(f"🔪 Freed port {port}")
                except Exception as e:
                    print(f"⚠️ Could not clean port {port}: {e}")

            print("✅ Cleanup completed - all services stopped")
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            print(f"\n🛑 Received signal {signum} - shutting down gracefully...")
            self.cleanup_on_exit()
            sys.exit(0)

        # Handle common termination signals
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination request

        # On macOS/Unix, also handle window close
        try:
            signal.signal(signal.SIGHUP, signal_handler)   # Terminal hangup
        except AttributeError:
            pass  # Not available on Windows

    def run(self, host='0.0.0.0', port=9002, debug=False):
        """Run the control panel.
        If port is already in use by an older instance, kill it first to avoid duplicates.
        """
        print(f"🚀 Starting Unified TEP Control Panel on http://localhost:{port}")
        print("✅ Single interface for all components")
        print("✅ Proper data flow: TEP → FaultExplainer")
        print("✅ Correct timing and values")
        print("✅ Auto-cleanup on GUI close enabled")

        # Setup signal handlers for graceful shutdown
        self.setup_signal_handlers()

        # Proactively free port 9001 from any stale processes before starting
        try:
            if self.bridge.kill_port_process(port):
                print(f"🔪 Freed port {port} from stale process")
        except Exception as e:
            print(f"⚠️ Could not pre-free port {port}: {e}")
        time.sleep(0.5)

        # Do NOT auto-open the browser here. With the new START_TEP_COPILOT.command
        # launcher, the user is sent to http://localhost:5173/ (the new Live
        # Copilot UI). Opening 127.0.0.1:9002 here as well produces a second
        # tab on the legacy Flask UI, which confuses people. Anyone who wants
        # the legacy DCS panel can navigate to :9002 manually.
        print(f"📺 Legacy DCS UI listening on http://127.0.0.1:{port} (open manually if needed)")

        try:
            self.app.run(host=host, port=port, debug=debug)
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt received")
        finally:
            self.cleanup_on_exit()


if __name__ == "__main__":
    panel = UnifiedControlPanel()
    panel.run(debug=False)
