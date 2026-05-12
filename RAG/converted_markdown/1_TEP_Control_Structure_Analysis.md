# 1_TEP_Control_Structure_Analysis
*Converted from: 1_TEP_Control_Structure_Analysis.docx*

---

Tennessee Eastman Process (TEP) - Control Structure Analysis

** Summary**

The Fortran implementation contains:

11 Manipulated Variables (XMV) - Valve positions and control outputs

41 Process Measurements (XMEAS) - Sensor readings

20 Disturbance Variables (IDV) - Fault injection points

20 Control Setpoints (SETPT) - Controller targets

Multiple Control Loops - Including cascade, feedback, and feedforward control

**1. MANIPULATED VARIABLES (XMV) - 11 Total**

Control outputs (valve positions, flow rates) that operators can adjust:

Note: All XMV values are continuous (0.0-100.0%)

**2. PROCESS MEASUREMENTS (XMEAS) - 41 Total**

Sensor readings:

**2.1 Flow Measurements (10 variables)**

**2.2 Pressure Measurements (3 variables)**

**2.3 Level Measurements (3 variables)**

**2.4 Temperature Measurements (4 variables)**

**2.5 Composition Measurements (19 variables)**

Stream 6 (Reactor Feed) - XMEAS(23-28):

Component A, B, C, D, E, F (mole %)

Stream 9 (Purge) - XMEAS(29-36):

Component A, B, C, D, E, F, G, H (mole %)

Stream 11 (Stripper Product) - XMEAS(37-41):

Component D, E, F, G, H (mole %)

**2.6 Other Measurements**

**3. CONTROL LOOPS STRUCTURE**

Based on the Fortran code analysis, the TEP contains multiple control loops:

**3.1 Primary Control Loops **

Total Confirmed Control Loops: 11 primary loops

**4. CASCADE CONTROL STRUCTURES**

**4.1 Reactor Temperature Cascade Control**

Outer Loop (Primary):

CV: Reactor Temperature (XMEAS 9)

SP: ~120-135°C

Output: Setpoint for inner loop

Inner Loop (Secondary):

CV: Reactor Cooling Water Outlet Temperature (XMEAS 21)

SP: SETPT(10) = 94.6°C (from outer loop)

MV: Reactor Cooling Water Flow (XMV 10)

Purpose: Provides faster disturbance rejection and prevents cooling water valve saturation.

**4.2 Production Rate Cascade **

Outer Loop:

CV: Product composition or production rate

SP: Operator-defined production target

Output: Feed flow setpoints

Inner Loops:

CV: Individual feed flows (XMEAS 1, 2, 3, 4)

MV: Feed valves (XMV 1, 2, 3, 4)

**5. P&ID CONTROL ELEMENTS**

**5.1 Major Equipment Units**

Reactor (CSTR - Continuous Stirred Tank Reactor)

- Pressure control (PC)

- Level control (LC)

- Temperature control (TC - cascade)

- Agitator speed control

Product Separator (Flash Drum)

- Pressure control (PC)

- Level control (LC)

- Temperature indication (TI)

Stripper Column (Distillation)

- Level control (LC)

- Temperature control (TC)

- Pressure indication (PI)

- Steam flow control (FC)

Compressor

- Work/power monitoring

- Recycle flow control

Condenser

- Cooling water flow control (FC)

- Temperature control (TC)

**5.2 Control Instrumentation**

Total Control Loops: 11 controllers

Total Measurements: 41 transmitters

Overall: 52 Features

**6. CONTROL SETPOINTS (SETPT Array)**

The Fortran code contains a SETPT array with 20 elements:

Note: It looks like the Fortran code has 20 setpoint slots, but only 3 are actively used in the base control configuration.

**7. KEY OPERATING PARAMETERS**

**7.1 Normal Operating Conditions**

**7.2 Feed Composition Ranges**

Stream 4 (A and C Feed):

Component A: 30-50 mole %

Component C: 50-70 mole %

Stream 2 (D Feed):

Pure D component

Stream 3 (E Feed):

Pure E component

**8. SUMMARY STATISTICS**

