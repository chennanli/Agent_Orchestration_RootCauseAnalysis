#!/usr/bin/env python3
"""
TEP Data Bridge Module
- Handles TEP simulation execution
- Manages data flow to FaultExplainer
- Controls timing and anomaly detection
"""

import os
import sys
import time
import threading
import subprocess
import signal
import json
import csv
from collections import deque
import numpy as np
import requests


def resolve_venv_python():
    """Use local venv in TEP_control folder. Return absolute python path for current OS."""
    # Get TEP_control directory (parent of backend)
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    tep_control_dir = os.path.dirname(backend_dir)

    if sys.platform.startswith('win'):
        venv_python = os.path.join(tep_control_dir, 'venv', 'Scripts', 'python.exe')
    else:
        venv_python = os.path.join(tep_control_dir, 'venv', 'bin', 'python')

    if os.path.exists(venv_python):
        return venv_python
    # Fallback to current interpreter
    return sys.executable


def resolve_npm_cmd():
    return 'npm.cmd' if sys.platform.startswith('win') else 'npm'


class TEPDataBridge:
    """Bridge between dynamic TEP simulation and FaultExplainer."""

    def __init__(self):
        self.setup_tep2py()
        self.simulation_thread = None
        self.stop_simulation = False
        self.current_step = 0
        self.idv_values = np.zeros(20)  # IDV_1 to IDV_20
        self.simulation_mode = 'real'  # 'demo', 'balanced', 'real'
        self.simulation_interval = 180  # seconds (3 minutes default)
        
        # Data storage
        self.recent_data = deque(maxlen=100)
        
        print("✅ TEP Data Bridge initialized")
        print("✅ Timing: TEP(3min) → Anomaly Detection(6min) → LLM(12min)")

    def setup_tep2py(self):
        """Load the TEP simulation module."""
        try:
            # Add the current directory to Python path for tep2py import
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            import tep2py
            self.tep = tep2py
            print("✅ Real tep2py loaded")
        except ImportError as e:
            print(f"❌ Failed to import tep2py: {e}")
            print("📁 Current directory:", os.getcwd())
            print("📁 Python path:", sys.path[:3])
            raise

    def set_idv(self, idv_number, value):
        """Set IDV value (1-based indexing)."""
        if 1 <= idv_number <= 20:
            self.idv_values[idv_number - 1] = float(value)
            print(f"🔧 Set IDV_{idv_number} = {value:.2f}")
            return True
        return False

    def get_simulation_data(self):
        """Run one step of TEP simulation and return data."""
        try:
            # Run simulation with current IDV values
            result = self.tep.tep(self.idv_values)
            
            # Extract the data (result is typically a tuple or array)
            if isinstance(result, (list, tuple, np.ndarray)):
                data_point = np.array(result).flatten()
            else:
                data_point = np.array([result]).flatten()
            
            # Create data record
            record = {
                'step': self.current_step,
                'timestamp': time.time(),
                'idv_values': self.idv_values.tolist(),
                'measurements': data_point.tolist(),
                'mode': self.simulation_mode
            }
            
            self.recent_data.append(record)
            return record
            
        except Exception as e:
            print(f"❌ Simulation error: {e}")
            return None

    def save_data_point(self, data_point):
        """Save data point to CSV file."""
        try:
            os.makedirs('data', exist_ok=True)
            csv_file = 'data/live_tep_data.csv'
            
            # Create header if file doesn't exist
            file_exists = os.path.exists(csv_file)
            
            with open(csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                
                if not file_exists:
                    # Write header
                    header = ['step', 'timestamp', 'mode'] + [f'idv_{i+1}' for i in range(20)] + [f'measurement_{i+1}' for i in range(len(data_point['measurements']))]
                    writer.writerow(header)
                
                # Write data
                row = [data_point['step'], data_point['timestamp'], data_point['mode']] + data_point['idv_values'] + data_point['measurements']
                writer.writerow(row)
                
            print(f"💾 Saved data point {data_point['step']} to {csv_file}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save data: {e}")
            return False

    def post_to_faultexplainer(self, data_point):
        """Post data to FaultExplainer backend."""
        try:
            # Prepare data in FaultExplainer format
            payload = {
                'timestamp': data_point['timestamp'],
                'measurements': data_point['measurements'],
                'idv_values': data_point['idv_values'],
                'step': data_point['step']
            }
            
            print("➡️ Posting /ingest...")
            response = requests.post(
                'http://localhost:8000/ingest',
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                t2_value = result.get('t2_statistic', 0)
                anomaly = result.get('anomaly_detected', False)
                idx = result.get('data_index', 0)
                
                if anomaly:
                    print(f"✅ /ingest OK in {response.elapsed.total_seconds():.2f}s (t2={t2_value}, anomaly={anomaly}, idx={idx})")
                    print("🤖 LLM triggered (live)")
                else:
                    print(f"⏳ /ingest aggregating in {response.elapsed.total_seconds():.2f}s (have={idx+1}, need=4)")
                
                return True
            else:
                print(f"❌ /ingest failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to post to FaultExplainer: {e}")
            return False

    def simulation_loop(self):
        """Main simulation loop."""
        print("🚀 Starting TEP simulation loop")
        
        while not self.stop_simulation:
            try:
                print(f"⏱️ Step {self.current_step} start (interval={self.simulation_interval}s, mode={self.simulation_mode})")
                
                # Run simulation
                data_point = self.get_simulation_data()
                if data_point:
                    # Save to CSV
                    self.save_data_point(data_point)
                    
                    # Post to FaultExplainer
                    self.post_to_faultexplainer(data_point)
                    
                    self.current_step += 1
                
                # Sleep for next iteration
                print("💤 Sleeping for next step...")
                for i in range(self.simulation_interval):
                    if self.stop_simulation:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                print(f"❌ Simulation loop error: {e}")
                time.sleep(5)  # Brief pause before retry

    def start_simulation(self):
        """Start the simulation in a background thread."""
        if self.simulation_thread and self.simulation_thread.is_alive():
            print("⚠️ Simulation already running")
            return False
            
        self.stop_simulation = False
        self.current_step = 0
        self.simulation_thread = threading.Thread(target=self.simulation_loop, daemon=True)
        self.simulation_thread.start()
        print("✅ TEP simulation started")
        return True

    def stop_simulation(self):
        """Stop the simulation."""
        self.stop_simulation = True
        if self.simulation_thread:
            self.simulation_thread.join(timeout=5)
        print("🛑 TEP simulation loop stopped")
        return True

    def get_status(self):
        """Get current simulation status."""
        return {
            'running': self.simulation_thread and self.simulation_thread.is_alive() and not self.stop_simulation,
            'current_step': self.current_step,
            'mode': self.simulation_mode,
            'interval': self.simulation_interval,
            'idv_values': self.idv_values.tolist(),
            'recent_data_count': len(self.recent_data)
        }

    def set_simulation_mode(self, mode):
        """Set simulation mode and corresponding interval."""
        mode_intervals = {
            'demo': 4,      # 4 seconds for demo
            'balanced': 60, # 1 minute for balanced
            'real': 180     # 3 minutes for real
        }
        
        if mode in mode_intervals:
            self.simulation_mode = mode
            self.simulation_interval = mode_intervals[mode]
            print(f"🎛️ Set simulation mode: {mode} (interval: {self.simulation_interval}s)")
            return True
        return False
