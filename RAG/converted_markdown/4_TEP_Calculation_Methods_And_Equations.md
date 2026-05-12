# 4_TEP_Calculation_Methods_And_Equations
*Converted from: 4_TEP_Calculation_Methods_And_Equations.docx*

---

TEP Calculation Methods and Equations

Physics, Chemistry, and Numerical Methods

Chemical Reaction Kinetics (Arrhenius equations)

Mass and Energy Balances (differential equations)

Thermodynamic Properties (vapor-liquid equilibrium, enthalpy)

Equipment Models (reactor, separator, stripper, compressor)

Numerical Integration (likely Euler or Runge-Kutta methods)

**Table of Contents**

[Chemical Reactions and Kinetics](#1-chemical-reactions-and-kinetics)

[Thermodynamic Properties](#2-thermodynamic-properties)

[Equipment Models and Equations](#3-equipment-models-and-equations)

[Mass and Energy Balances](#4-mass-and-energy-balances)

[Numerical Integration Methods](#5-numerical-integration-methods)

[Calculation Sequence](#6-calculation-sequence)

[Key Equations Summary](#7-key-equations-summary)

1. Chemical Reactions and Kinetics

1.1 Reaction Scheme

The TEP involves 4 main reactions occurring in the gas-phase reactor:

Primary Reactions (desired products):

Reaction 1:  A(g) + C(g) + D(g) → G(liq)    (Product G)
Reaction 2:  A(g) + C(g) + E(g) → H(liq)    (Product H)

Side Reactions (byproducts):

Reaction 3:  A(g) + E(g) → F(liq)           (Byproduct F)
Reaction 4:  3D(g) → 2F(liq)                (Side reaction)

Additional Reactions (inerts and purge):

Component B: Inert (does not react, accumulates in recycle)
Component C: Reactant (participates in Reactions 1 and 2)

1.2 Reaction Kinetics (Arrhenius Equations)

Each reaction rate is calculated using the Arrhenius equation:

r_i = k_i * exp(-E_i / (R * T)) * ∏(C_j^n_ij)

r_i = Reaction rate for reaction i [kmol/(m³·h)]

k_i = Pre-exponential factor (frequency factor) [varies by reaction]

E_i = Activation energy [kJ/kmol]

R= Universal gas constant = 8.314 [kJ/(kmol·K)]

T = Reactor temperature [K]

C_j = Concentration of component j [kmol/m³]

n_ij = Reaction order for component j in reaction i

1.3 Reaction Rate Constants

Typical Values (from TEP literature):

Activation energies: E_i ~ 40,000 - 80,000 kJ/kmol

Pre-exponential factors: k_i ~ 10^6 - 10^12 [varies by units]

Reaction orders: n_ij = 1 (first-order in each reactant)

2. Thermodynamic Properties

2.1 Vapor-Liquid Equilibrium (VLE)

The separator and stripper use flash calculations to determine vapor-liquid split:

Raoult's Law (ideal solution assumption):

y_i * P = x_i * P_i^sat(T)

y_i = Mole fraction of component i in vapor phase

x_i = Mole fraction of component i in liquid phase

P = Total pressure [kPa]

P_i^sat(T) = Vapor pressure of pure component i at temperature T [kPa]

Antoine Equation (vapor pressure):

log10(P_i^sat) = A_i - B_i / (T + C_i)

A_i, B_i, C_i = Antoine constants for component i

T = Temperature [°C]

P_i^sat = Vapor pressure [kPa]

2.2 Enthalpy Calculations

Vapor Enthalpy:

H_vap = ∫ Cp_vap dT + ΔH_vap

Liquid Enthalpy:

H_liq = ∫ Cp_liq dT

Cp_vap = Heat capacity of vapor [kJ/(kmol·K)]

Cp_liq = Heat capacity of liquid [kJ/(kmol·K)]

ΔH_vap = Heat of vaporization [kJ/kmol]

Heat Capacity (temperature-dependent):

Cp(T) = a + b*T + c*T^2 + d*T^3

Where a, b, c, d are component-specific constants.

2.3 Density and Molecular Weight

Ideal Gas Law (for gas phase):

ρ_gas = (P * MW) / (R * T)

ρ_gas = Gas density [kg/m³]

MW = Molecular weight [kg/kmol]

P = Pressure [kPa]

R = Gas constant = 8.314 [kPa·m³/(kmol·K)]

T = Temperature [K]

Liquid Density (empirical correlation):

ρ_liq = ρ_0 * (1 - α * (T - T_0))

ρ_0= Reference density at T_0 [kg/m³]

α = Thermal expansion coefficient [1/K]

3. Equipment Models and Equations

3.1 Reactor (CSTR)

Perfect mixing (uniform composition and temperature)

Gas-phase reactions

Liquid products removed continuously

Exothermic reactions (heat generation)

Component Mass Balance:

V_R * dC_i/dt = F_in * C_i,in - F_out * C_i + V_R * Σ(ν_ij * r_j)

V_R = Reactor volume [m³]

C_i = Concentration of component i [kmol/m³]

F_in = Inlet volumetric flow rate [m³/h]

F_out = Outlet volumetric flow rate [m³/h]

ν_ij = Stoichiometric coefficient of component i in reaction j

r_j = Reaction rate for reaction j [kmol/(m³·h)]

Energy Balance:

ρ * V_R * Cp * dT/dt = F_in * ρ * Cp * (T_in - T) + V_R * Σ(ΔH_rxn,j * r_j) - Q_cool

ρ = Density [kg/m³]

Cp = Heat capacity [kJ/(kg·K)]

T = Reactor temperature [K]

ΔH_rxn,j = Heat of reaction j [kJ/kmol] (negative for exothermic)

Q_cool = Cooling duty [kJ/h]

Cooling Duty:

Q_cool = U * A * (T - T_cool)

U = Overall heat transfer coefficient [kJ/(h·m²·K)]

A = Heat transfer area [m²]

T_cool = Cooling water temperature [K]

3.2 Separator (Flash Drum)

Flash Calculation (Rachford-Rice equation):

Σ[ z_i * (K_i - 1) / (1 + V/F * (K_i - 1)) ] = 0

z_i = Overall mole fraction of component i

K_i = Equilibrium constant = y_i / x_i = P_i^sat / P

V/F = Vapor fraction (0 to 1)

Solved iteratively to find V/F, then:

x_i = z_i / (1 + V/F * (K_i - 1))
y_i = K_i * x_i

Energy Balance:

H_feed = (V/F) * H_vapor + (1 - V/F) * H_liquid

3.3 Stripper (Distillation Column)

Purpose: Separate products G and H from light components

Simplified Model (equilibrium stages):

Multiple theoretical stages (typically 10-20)

Reboiler (steam heating)

Condenser (cooling water)

Component Balance per Stage:

dM_i,n/dt = L_n+1 * x_i,n+1 + V_n-1 * y_i,n-1 - L_n * x_i,n - V_n * y_i,n

M_i,n = Holdup of component i on stage n [kmol]

L_n = Liquid flow rate from stage n [kmol/h]

V_n = Vapor flow rate from stage n [kmol/h]

x_i,n = Liquid mole fraction of component i on stage n

y_i,n = Vapor mole fraction of component i on stage n

Equilibrium Relationship:

y_i,n = K_i,n * x_i,n

3.4 Compressor

Compressor Work:

W_comp = (γ / (γ - 1)) * R * T_in * [(P_out / P_in)^((γ-1)/γ) - 1] / η

W_comp = Compressor work [kJ/kmol]

γ = Heat capacity ratio (Cp / Cv) ≈ 1.4 for gases

R= Gas constant [kJ/(kmol·K)]

T_in = Inlet temperature [K]

P_out = Outlet pressure [kPa]

P_in = Inlet pressure [kPa]

η = Compressor efficiency (typically 0.7-0.8)

Temperature Rise:

T_out = T_in * (P_out / P_in)^((γ-1)/γ)

4. Mass and Energy Balances

4.1 Overall Mass Balance

Total Mass:

dM_total/dt = Σ(F_in) - Σ(F_out)

Component Mass:

dM_i/dt = Σ(F_in * C_i,in) - Σ(F_out * C_i) + Σ(ν_ij * r_j * V)

4.2 Overall Energy Balance

Energy Accumulation:

dE/dt = Σ(F_in * H_in) - Σ(F_out * H_out) + Q_heat - Q_cool + W_shaft

E = Total energy [kJ]

H = Enthalpy [kJ/kmol]

Q_heat = Heat input (steam, etc.) [kJ/h]

Q_cool = Heat removal (cooling water) [kJ/h]

W_shaft = Shaft work (compressor, agitator) [kJ/h]

5. Numerical Integration Methods

5.1 Differential-Algebraic Equations (DAEs)

The TEP simulation solves a system of DAEs:

Differential Equations (dynamic states):

dx/dt = f(x, y, u, t)

Algebraic Equations (constraints):

0 = g(x, y, u, t)

x = State variables (levels, temperatures, compositions)

y = Algebraic variables (flow rates, pressures)

u= Control inputs (XMV values)

t = Time

5.2 Numerical Integration Method

Euler Method (first-order explicit):

x(t + Δt) = x(t) + Δt * f(x(t), y(t), u(t), t)

Alternative: Runge-Kutta Method (fourth-order):

k1 = f(x, y, u, t)
k2 = f(x + Δt/2 * k1, y, u, t + Δt/2)
k3 = f(x + Δt/2 * k2, y, u, t + Δt/2)
k4 = f(x + Δt * k3, y, u, t + Δt)
x(t + Δt) = x(t) + Δt/6 * (k1 + 2*k2 + 2*k3 + k4)

5.3 Time Step Selection

From Code Analysis:

Internal Fortran Time Step: 1 second (for accurate physics)

Sampling Interval: 180 seconds (3 minutes)

Total Simulation: NPTS = Nsamples × 3 × 60 seconds

Using ultra start is 1/50 secs per time step

6. Key Equations Summary

6.1 Reaction Kinetics

r_i = k_i * exp(-E_i / (R * T)) * ∏(C_j^n_ij)

6.2 Mass Balance (Reactor)

V * dC_i/dt = F_in * C_i,in - F_out * C_i + V * Σ(ν_ij * r_j)

6.3 Energy Balance (Reactor)

ρ * V * Cp * dT/dt = F_in * ρ * Cp * (T_in - T) + V * Σ(ΔH_rxn,j * r_j) - Q_cool

6.4 Flash Calculation (Separator)

Σ[ z_i * (K_i - 1) / (1 + V/F * (K_i - 1)) ] = 0

6.5 Compressor Work

W_comp = (γ / (γ - 1)) * R * T_in * [(P_out / P_in)^((γ-1)/γ) - 1] / η

6.6 Numerical Integration (Euler)

x(t + Δt) = x(t) + Δt * f(x, y, u, t)

7. Thermodynamic Property Estimation

7.1 Component Properties

8 Components (A, B, C, D, E, F, G, H):

7.2 Vapor Pressure Correlations

Antoine Equation (each component):

log10(P_sat) = A - B / (T + C)

7.3 Heat Capacity Correlations

Polynomial Form:

Cp(T) = a + b*T + c*T^2 + d*T^3

Units: kJ/(kmol·K)

8. Disturbance Variables (IDV) Effects

IDV(1): A/C Feed Ratio

Modifies feed composition

Affects reaction stoichiometry

Changes product G/H ratio

IDV(2): B Composition

Increases inert concentration

Reduces reactor efficiency

Requires higher purge rate

IDV(3): D Feed Temperature

Changes feed enthalpy

Affects reactor energy balance

Impacts cooling duty

IDV(4): Reactor Cooling Water Inlet Temperature

Reduces cooling capacity

Increases reactor temperature

Accelerates reaction rates

IDV(5): Condenser Cooling Water Inlet Temperature

Affects separator temperature

Changes vapor-liquid equilibrium

Impacts recycle composition

9. Limitations and Assumptions

9.1 Model Assumptions

Ideal Gas Behavior: Gas phase follows ideal gas law

Ideal Solutions: Raoult's law for VLE

Perfect Mixing: CSTR assumption for reactor

Equilibrium Stages: Stripper uses equilibrium model

Constant Properties: Some properties assumed constant

9.2 Known Limitations

No Fouling: Heat exchangers don't foul over time

No Catalyst Deactivation: Reaction rates constant

No Equipment Degradation: No wear and tear

Simplified Hydraulics: Pressure drops simplified

No Startup/Shutdown: Model for continuous operation

**Summary**

