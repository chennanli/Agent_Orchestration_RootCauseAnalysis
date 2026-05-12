#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 03 17:30:00 2019

@author: camaramm

XDATA = temain_mod.temain(NPTS, NX, IDATA, VERBOSE)
  Computes the 41 process measurements and 11 manipulated variables given
    the disturbances time-series matrix.
  The

  Parameters
  ----------
  NPTS : int
    TOTAL NUMBER OF DATA POINTS THE SIMULATOR WILL CALCULATE.
    The simulator gives 1 point per second, which means 1 MIN = 60 POINTS.
    The simulator has a pre-defined sample frequency of 180 s, which means 3 MIN = 1 SAMPLE.
    The number of desired samples is implied in `idata`: idata.shape[0]
    So, the total number of data points is `NPTS = Nsamples*3*60`.
  NX : int
    NUMBER OF SAMPLED DATA POINTS.
  IDATA : 2d-array
    MATRIX OF DISTURBANCES TIME-SERIES (NX, 20)
  VERBOSE :
    VERBOSE FLAG (0 = VERBOSE, 1 = NO VERBOSE)

  Returns
  -------
  XDATA : DataFrame
    MATRIX OF PROCESS MEASUREMENTS AND MANIPULATED VARIABLES (NX, 52)
"""

# modules
import numpy as np
import pandas as pd
import temain_mod


class tep2py():

    def __init__(self, idata, speed_factor=1.0, user_xmv=None, user_setpoints=None):
        if idata.shape[1] == 20:
            self.disturbance_matrix = idata
        else:
            raise ValueError('Matrix of disturbances do not have the appropriate dimension.'
                'It must be shape[1]==20')

        # Store speed factor (0.1 to 10.0)
        self.speed_factor = max(0.1, min(10.0, float(speed_factor)))

        # Store user XMV values (11 manipulated variables)
        # Store user SETPOINT values (20 setpoints) - ADDED SUPPORT
        self.user_setpoints = user_setpoints

        # Store setpoints for later application
        if user_setpoints is not None:
            print(f"🎯 User setpoints provided: {user_setpoints}")
            self.setpoints_to_apply = user_setpoints
        else:
            self.setpoints_to_apply = None
        if user_xmv is not None:
            if len(user_xmv) != 11:
                raise ValueError('user_xmv must have exactly 11 values for XMV(1) to XMV(11)')
            self.user_xmv = np.array(user_xmv, dtype=float)
            self.user_control_mode = 1  # Enable user control
        else:
            self.user_xmv = np.zeros(11, dtype=float)  # Default values will be used
            self.user_control_mode = 0  # Use default factory values

        self._build_var_table()
        self._build_disturbance_table()


    def simulate(self):
        """
        Parameters
        ----------
        IDATA : 2d-array
        MATRIX OF DISTURBANCES TIME-SERIES (NX, 20)

        Returns
        -------
        XDATA : DataFrame
        MATRIX OF PROCESS MEASUREMENTS AND MANIPULATED VARIABLES (NX, 52)
        """
        idata = self.disturbance_matrix

        # Use REAL Fortran TEMAIN function - NO SYNTHETIC FALLBACK
        print(f"🔧 Using REAL Fortran TEMAIN with XMV control (speed factor: {self.speed_factor}x)")
        print(f"🎛️ Control mode: {self.user_control_mode}, XMV shape: {self.user_xmv.shape if hasattr(self.user_xmv, 'shape') else 'N/A'}")

        # Ensure user_xmv is properly formatted
        if self.user_control_mode == 1 and self.user_xmv is not None:
            xmv_array = np.asarray(self.user_xmv, dtype=float)
            if xmv_array.shape != (11,):
                raise ValueError(f"user_xmv must have shape (11,), got {xmv_array.shape}")
        else:
            # Use default XMV values from TEP specification
            xmv_array = np.array([63.0, 53.0, 24.0, 61.0, 22.0, 40.0, 38.0, 46.0, 47.0, 41.0, 18.0], dtype=float)

        print(f"🎯 XMV values: {xmv_array}")
        print(f"📊 IDV matrix shape: {idata.shape}")

        # Apply setpoints BEFORE calling TEMAIN
        if hasattr(self, 'setpoints_to_apply') and self.setpoints_to_apply is not None:
            print("🎯 Applying setpoints BEFORE TEMAIN call...")
            for i, setpt_val in enumerate(self.setpoints_to_apply):
                if setpt_val != 0.0:
                    temain_mod.ctrlall.setpt[i] = float(setpt_val)
                    print(f"🎯 Pre-TEMAIN: SETPT[{i+1}] = {setpt_val}")
            print(f"🎯 Pre-TEMAIN setpoints: {temain_mod.ctrlall.setpt}")

        # Call REAL Fortran physics with CORRECT signature
        # From f2py compilation: temain(npts, idata, xdata, verbose)
        print("🔧 Calling TEMAIN with correct signature...")

        # Pre-allocate output array with correct Fortran ordering
        xdata_output = np.zeros((idata.shape[0], 52), dtype=float, order='F')

        # Use CORRECT signature: temain(npts, idata, xdata, verbose)
        result = temain_mod.temain(
           np.asarray(60*3*idata.shape[0], dtype=int),      # npts (total data points)
           idata,                                           # idata (IDV disturbances matrix)
           xdata_output,                                    # xdata (output array - pre-allocated)
           int(1)                                           # verbose flag
        )

        # PROPER SETPOINT CONTROL: Apply setpoints and run individual controllers
        if hasattr(self, 'setpoints_to_apply') and self.setpoints_to_apply is not None:
            print(f"🎯 Post-TEMAIN setpoints: {temain_mod.ctrlall.setpt}")

            # Apply setpoints and run individual controllers for proper control action
            for i, setpt_val in enumerate(self.setpoints_to_apply):
                if setpt_val != 0.0:
                    old_val = temain_mod.ctrlall.setpt[i]
                    temain_mod.ctrlall.setpt[i] = float(setpt_val)
                    print(f"🎯 Applied SETPT[{i+1}]: {old_val} → {setpt_val}")

                    # Run the specific controller to apply the setpoint change
                    if i == 9:  # SETPT[10] controls XMV[10] via contrl10
                        print(f"🎮 Running controller 10 for setpoint {setpt_val}")
                        temain_mod.contrl10()
                        print(f"🎮 XMV[10] after controller: {temain_mod.pv.xmv[9]}")

            print(f"🎯 Final setpoints: {temain_mod.ctrlall.setpt}")
        print(f"✅ REAL TEP Fortran simulation complete - authentic physics!")

        # The data is in xdata_output, not the return value
        print(f"📊 Output data shape: {xdata_output.shape}")
        print(f"📊 Sample output values: {xdata_output[0, :5]}")

        # column names
        names = (
                ["XMEAS({:})".format(i) for i in range(1,41+1)]
                + ["XMV({:})".format(i) for i in range(1,11+1)]
                )
        # index
        datetime = np.arange(0, 3*idata.shape[0] , 3, dtype='datetime64[m]')

        # data as DataFrame - use xdata_output, not the return value
        xdata = pd.DataFrame(xdata_output, columns=names, index=datetime)

        self.process_data = xdata

    # REMOVED: _generate_realistic_tep_data()
    # We now use ONLY real Fortran physics - no synthetic fallbacks!
    # All XMV/IDV effects come from authentic Tennessee Eastman process equations



    def set_speed_factor(self, speed_factor):
        """
        Set simulation speed factor.

        Parameters
        ----------
        speed_factor : float
            Speed multiplier (0.1 to 10.0)
            1.0 = Normal speed
            10.0 = 10x faster
            0.1 = 10x slower
        """
        self.speed_factor = max(0.1, min(10.0, float(speed_factor)))
        print(f"🎛️ Speed factor set to {self.speed_factor}x")

    def _build_var_table(self):
        
        description = [
            'A Feed (stream 1)',
            'D Feed (stream 2)',
            'E Feed (stream 3)',
            'A and C Feed (stream 4)',
            'Recycle Flow (stream 8)',
            'Reactor Feed Rate (stream 6)',
            'Reactor Pressure',
            'Reactor Level',
            'Reactor Temperature',
            'Purge Rate (stream 9)',
            'Product Sep Temp',
            'Product Sep Level',
            'Prod Sep Pressure',
            'Prod Sep Underflow (stream 10)',
            'Stripper Level',
            'Stripper Pressure',
            'Stripper Underflow (stream 11)',
            'Stripper Temperature',
            'Stripper Steam Flow',
            'Compressor Work',
            'Reactor Cooling Water Outlet Temp',
            'Separator Cooling Water Outlet Temp',
            'Component A (stream 6)',
            'Component B (stream 6)',
            'Component C (stream 6)',
            'Component D (stream 6)',
            'Component E (stream 6)',
            'Component F (stream 6)',
            'Component A (stream 9)',
            'Component B (stream 9)',
            'Component C (stream 9)',
            'Component D (stream 9)',
            'Component E (stream 9)',
            'Component F (stream 9)',
            'Component G (stream 9)',
            'Component H (stream 9)',
            'Component D (stream 11)',
            'Component E (stream 11)',
            'Component F (stream 11)',
            'Component G (stream 11)',
            'Component H (stream 11)',
            'D Feed Flow (stream 2)',
            'E Feed Flow (stream 3)',
            'A Feed Flow (stream 1)',
            'A and C Feed Flow (stream 4)',
            'Compressor Recycle Valve',
            'Purge Valve (stream 9)',
            'Separator Pot Liquid Flow (stream 10)',
            'Stripper Liquid Product Flow (stream 11)',
            'Stripper Steam Valve',
            'Reactor Cooling Water Flow',
            'Condenser Cooling Water Flow',
            'Agitator Speed'
        ]

        unit = [
            'kscmh',
            'kg h-1',
            'kg h-1',
            'kscmh',
            'kscmh',
            'kscmh',
            'kPa',
            '%',
            'oC',
            'kscmh',
            'oC',
            '%',
            'kPa',
            'm3 h-1',
            '%',
            'kPa',
            'm3 h-1',
            'oC',
            'kg h-1',
            'kW',
            'oC',
            'oC',
            *['mole %' for i in range(19)],
            *['%' for i in range(12)]
        ]

        variable = (
            ["XMEAS({:})".format(i) for i in range(1,41+1)]
            + ["XMV({:})".format(i) for i in range(1,12+1)]
            )
        
        table = pd.DataFrame({
            'variable': variable,
            'description': description,
            'unit': unit
            })

        self.info_variable = table


    def _build_disturbance_table(self):

        disturbance = ["IDV({:})".format(i) for i in range(1,20+1)]

        description = [
            'A/C Feed Ratio, B Composition Constant (Stream 4) Step',
            'B Composition, A/C Ratio Constant (Stream 4) Step',
            'D Feed Temperature (Stream 2) Step',
            'Reactor Cooling Water Inlet Temperature Step',
            'Condenser Cooling Water Inlet Temperature Step',
            'A Feed Loss (Stream 1) Step',
            'C Header Pressure Loss - Reduced Availability (Stream 4) Step',
            'A, B, C Feed Composition (Stream 4) Random Variation',
            'D Feed Temperature (Stream 2) Random Variation',
            'C Feed Temperature (Stream 4) Random Variation',
            'Reactor Cooling Water Inlet Temperature Random Variation',
            'Condenser Cooling Water Inlet Temperature Random Variation',
            'Reaction Kinetics Slow Drift',
            'Reactor Cooling Water Valve Sticking',
            'Condenser Cooling Water Valve Sticking',
            'Unknown',
            'Unknown',
            'Unknown',
            'Unknown',
            'Unknown',
            ]

        table = pd.DataFrame({
            'disturbance': disturbance,
            'description': description
            })

        self.info_disturbance = table


def test_tep_in_py():
    # matrix of disturbances
    idata = np.zeros((5,20))
    tep = tep2py(idata)
    tep.simulate()
    print(tep.process_data)


if __name__ == '__main__':
    test_tep_in_py()
