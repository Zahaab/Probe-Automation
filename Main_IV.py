"""
On startup:
- Load sample as normal - Bias bottom plate
- Make sure chuck height is maximum
- Make note of RAD and AWAY sites and add to config file
- Test everything moves as expected
- Check filename and structure of how data is stored
- Rest should be automated :D
"""

import winsound
import pyvisa
import time
import threading
import csv
import os
import datetime
import numpy as np
from sentio_prober_control.Sentio.ProberSentio import SentioProber
from Config import KEITHLEY_RESOURCE, PROBER_IP, SIMULATION_MODE, DUT, IV_Range, PV_IV_Range, Standoffs
from Classes import DataManager, KeithleyController, ProberController
from MeasurementF import iv_measurement, generate_voltage_sweep

# If reading this for the first time, please follow the numbered comments through the code!
# Order is: 1. Main CONFIGURATION, 2-4. Classes, 5. Measurement Functions, 6. Main Execution

# ==============================================================================
# 6. MAIN EXECUTION
# ==============================================================================


def main_IV():
    full_time_start = time.perf_counter()
    
    try:
        # Initialize Prober Controller
        pc = ProberController(PROBER_IP)
        pc.connect()
        pc._build_site_map()
        print(f"Prober IP: {pc.ip}")
        print(f"Site Map: {pc.site_map}")

        # Initialize Keithley Controller
        kc = KeithleyController(KEITHLEY_RESOURCE)
        kc.connect()
        kc.configure_CVIV()
        
        file_name_base = f'ProbeStation/{DUT}/_'
        print(f'[MAIN] Device File Path: {file_name_base}')
        user_check = input("Press q to quit or any key to continue")
        if user_check == "q":
            raise KeyboardInterrupt
        
        # Re-open KXCI to purge everything
        # Run IV first to see what dark currents are bad

        
        voltages_base = np.array([0, 1, 3, 5, 10, 30])
        voltages = np.concatenate([np.repeat(a, np.where(a == 0, 1, 3))
                                for a in (voltages_base, voltages_base[::-1][1:], -voltages_base[1:], (-voltages_base)[::-1][1:])])
        pc.move_to_site("AWAY")
        pc.move_z_mm(1.5)
        start_time = time.perf_counter()
        iv_measurement(kc, voltages, file_name=f'{file_name_base}TEST_IV')
        end_time = time.perf_counter()
        print(f"Time taken : {end_time - start_time:.2f} seconds")
        
        baseIV = generate_voltage_sweep(IV_Range, dual_sweep=True)
        pvIV = generate_voltage_sweep(PV_IV_Range, dual_sweep=True)
        
        for standoff in Standoffs:
            print(f"\n\nStarting IV measurement at standoff {standoff} mm")
            pc.move_z_mm(standoff)
            pc.move_to_site("AWAY")
            start_time = time.perf_counter()
            iv_measurement(kc, baseIV, file_name=f'{file_name_base}IV_{standoff}mm(AWAY)')
            end_time = time.perf_counter()
            print(f"Time taken for standoff {standoff} mm (Away): {end_time - start_time:.2f} seconds")
            pc.move_to_site("RAD")
            start_time = time.perf_counter()
            iv_measurement(kc, baseIV, file_name=f'{file_name_base}IV_{standoff}mm(RAD)')
            iv_measurement(kc, pvIV, file_name=f'{file_name_base}PV_IV_{standoff}mm(RAD)')
            end_time = time.perf_counter()
            print(f"Time taken for standoff {standoff} mm (RAD): {end_time - start_time:.2f} seconds")
    
    except KeyboardInterrupt:
        print("Interrupted by user, program quit.")
    finally:
        kc.inst.close()                          # Closes the connection to the instrument
        kc.rm.close()
        
    full_time_end = time.perf_counter()
    print(f"Total time taken for {DUT} : {full_time_end - full_time_start:.2f} seconds")

    # Play a sound when the code is done running - need to fix!
    winsound.Beep(1000, 500)