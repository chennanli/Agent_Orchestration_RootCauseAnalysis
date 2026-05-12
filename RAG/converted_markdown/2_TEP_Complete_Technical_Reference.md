# 2_TEP_Complete_Technical_Reference
*Converted from: 2_TEP_Complete_Technical_Reference.docx*

---

TEP Complete Technical Reference for Lanny

Table of Contents

[TEP Process Overview](#1-tep-process-overview)

[Control Structure](#2-control-structure)

[Process Variables and Parameters](#3-process-variables-and-parameters)

[How Parameters Are Calculated](#4-how-parameters-are-calculated)

[Plant Control Strategy](#5-plant-control-strategy)

[Anomaly Detection System](#6-anomaly-detection-system)

[System Architecture](#7-system-architecture)

[Quick Reference Tables](#8-quick-reference-tables)

1. TEP Process Overview

1.1 What is TEP?

The Tennessee Eastman Process (TEP) is a realistic industrial chemical plant simulation originally developed by Eastman Chemical Company in 1993. It simulates a complete chemical production process with:

5 Major Equipment Units: Reactor, Separator, Compressor, Condenser, Stripper

8 Chemical Components: A, B, C, D, E (reactants), F (byproduct), G, H (products)

52 Process Variables: 41 measurements + 11 manipulated variables

20 Fault Types: Realistic industrial disturbances (IDV_1 to IDV_20)

1.2 Chemical Reactions

The TEP simulates the following reactions:

A(g) + C(g) + D(g) → G(liq)    (Product G)
A(g) + C(g) + E(g) → H(liq)    (Product H)
A(g) + E(g) → F(liq)           (Byproduct F)
3D(g) → 2F(liq)                (Side reaction)

Key Points:

Reactions occur in a CSTR (Continuous Stirred Tank Reactor)

Exothermic reactions (release heat) → requires cooling

Gas-phase reactants → Liquid-phase products

Byproduct F is undesirable but unavoidable

1.3 Process Flow

Feed Streams (A, D, E, A+C)
    ↓
Reactor (CSTR) → Exothermic reactions
    ↓
Product Separator (Flash) → Separate gas/liquid
    ↓ (gas)              ↓ (liquid)
Compressor           Stripper Column
    ↓                    ↓
Condenser            Product (G+H)
    ↓
Recycle to Reactor

2. Control Structure

2.1 Total Control Loops: **11 Controllers**

2.2 Cascade Control Structure

Reactor Temperature Cascade Control (Most Important):

┌─────────────────────────────────────────┐
│ OUTER LOOP (Primary Controller)        │
│ CV: Reactor Temperature (XMEAS 9)      │
│ SP: 120-135°C                           │
│ Output: Setpoint for inner loop        │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ INNER LOOP (Secondary Controller)      │
│ CV: Cooling Water Outlet (XMEAS 21)    │
│ SP: SETPT(10) = 94.6°C (from outer)    │
│ MV: Reactor Cooling Water Flow (XMV 10)│
└─────────────────────────────────────────┘

2.3 P&ID Instrumentation Summary

Total: 11 controllers, 41 transmitters

3. Process Variables and Parameters

3.1 Manipulated Variables (XMV) - 11 Total

Notes:

All XMV values are continuous (0.0-100.0%), not discrete

Theoretically, changing XMV values affects process dynamics; however, in reality, seems not very responsible.

3.2 Process Measurements (XMEAS) - 41 Total

##### **Group 1: Flow Measurements (10 variables)**

##### **Group 2: Pressure Measurements (3 variables)**

Safety Critical: Reactor pressure must stay below 3000 kPa to prevent vessel rupture!

##### **Group 3: Level Measurements (3 variables)**

Safety Critical: Levels below 30% risk pump cavitation; above 80% risk overflow

##### **Group 4: Temperature Measurements (5 variables)**

Safety Critical: Reactor temperature above 140°C risks thermal runaway!

##### **Group 5: Composition Measurements (19 variables)**

Stream 6 (Reactor Feed) - XMEAS(23-28): Components A, B, C, D, E, F (6 variables)

Stream 9 (Purge) - XMEAS(29-36): Components A, B, C, D, E, F, G, H (8 variables)

Stream 11 (Stripper Product) - XMEAS(37-41): Components D, E, F, G, H (5 variables)

Total: 6 + 8 + 5 = 19 composition measurements

##### **Group 6: Other Measurements**

4. How Parameters Are Calculated

4.1 Fortran Simulation Engine

The TEP simulation uses compiled Fortran code (temain_mod.so) that implements:

Mass Balance Equations: Conservation of mass for each component

Energy Balance Equations: Heat generation/removal calculations

Reaction Kinetics: Arrhenius equations for reaction rates

Thermodynamic Properties: Vapor-liquid equilibrium (VLE)

Equipment Models: Reactor, separator, compressor, stripper dynamics

Controller Tuning (inferred from stable operation):

Level controllers: Slow integral action (Ti = 10-20 min)

Pressure controllers: Moderate gain (Kc = 1-5)

Temperature controllers: PID with derivative filtering (Td = 1-5 min)

Flow controllers: Fast PI response (Ti = 1-3 min)

4.4 Anomaly Detection Calculation

# From backend/app.py

# Step 1: Collect 52 features (XMEAS 1-41 + XMV 1-11)
features = [XMEAS_1, XMEAS_2, ..., XMEAS_41, XMV_1, ..., XMV_11]

# Step 2: Standardize features (zero mean, unit variance)
features_scaled = (features - mean) / std

# Step 3: Project onto principal components
scores = features_scaled @ principal_components

# Step 4: Calculate T² statistic (Hotelling's T²)
T2 = scores @ inv(covariance) @ scores.T

# Step 5: Compare to threshold
if T2 > threshold:
    anomaly_detected = True

Threshold: Default = 0.055 (calibrated from normal operation data)

5. Plant Control Strategy

5.1 Control Objectives

5.2 Normal Operating Conditions

5.3 Fault Response Strategy

When a fault (IDV) is introduced:

1. Sensors detect deviation (XMEAS values change)
   ↓
2. Controllers respond (XMV values adjust)
   ↓
3. PCA detects anomaly (T² > threshold)
   ↓
4. LLM analyzes root cause
   ↓
5. Operator takes corrective action

6. Anomaly Detection System

6.1 PCA-Based Detection

Why PCA?

Reduces 52 dimensions to ~10 principal components

Captures 95%+ of process variance

Detects multivariate anomalies (not just single-variable alarms)

How It Works:

Training Phase: Collect 100+ samples of normal operation

Build Model: Calculate principal components from normal data

Monitoring Phase: Project new data onto principal components

Anomaly Score: Calculate T² statistic

Alarm: Trigger if T² > threshold

6.2 Feature Importance

All 52 features are used

XMEAS 1-22: Basic process measurements (22 features)

XMEAS 23-41: Composition measurements (19 features) ← Critical for fault detection!

XMV 1-11: Manipulated variables (11 features) ← Shows controller response!

Why 52 features?

Composition changes are key indicators of many faults (IDV 1, 4, 8, 11)

XMV values show how controllers are responding to disturbances

More features = better fault coverage (not overfitting due to PCA dimensionality reduction)

7. System Architecture

7.1 Software Stack

┌─────────────────────────────────────────┐
│ Frontend (React + TypeScript)           │
│ - Real-time charts (Recharts)          │
│ - Mantine UI components                │
│ - Port: 5173                            │
└──────────────┬──────────────────────────┘
               ↓ HTTP/WebSocket
┌─────────────────────────────────────────┐
│ Backend API (FastAPI + Python)          │
│ - Multi-LLM integration                 │
│ - RAG knowledge base                    │
│ - Port: 8000                            │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ Unified Console (Flask + Python)        │
│ - TEP simulation control               │
│ - Anomaly detection (PCA)              │
│ - Port: 9002                            │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ TEP Simulation (Fortran)                │
│ - temain_mod.so (compiled binary)      │
│ - tep2py.py (Python wrapper)           │
└─────────────────────────────────────────┘

7.2 Data Flow

TEP Fortran Simulation
    ↓ (every 3 minutes)
CSV File (data/live_tep_data.csv)
    ↓ (every 6 minutes)
PCA Anomaly Detection
    ↓ (if anomaly detected)
Multi-LLM Analysis (Gemini, Claude, LMStudio)
    ↓
Markdown Reports (RCA_Results/)
    ↓
Interactive RCA Chat (with RAG context)

8. Quick Reference Tables

8.1 Control Setpoints

8.2 Fault Types (IDV)

8.3 System Timing

