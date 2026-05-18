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
from Config import KEITHLEY_RESOURCE, PROBER_IP, SIMULATION_MODE, DUT, DYNAMIC_VOLTAGES, Standoffs
from Classes import DataManager, KeithleyController, ProberController
from MeasurementF import dynamics_measurement

# If reading this for the first time, please follow the numbered comments through the code!
# Order is: 1. Main CONFIGURATION, 2-4. Classes, 5. Measurement Functions, 6. Main Execution

# ==============================================================================
# 6. MAIN EXECUTION
# ==============================================================================


def main_Dynamic():
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
        
        for standoff in Standoffs:
            pc.move_z_mm(standoff)
            for voltage in DYNAMIC_VOLTAGES:
                print(f"\n\nStarting Dynamic measurement at standoff {standoff} mm and voltage {voltage} V")
                pc.move_to_site("AWAY")
                start_time = time.perf_counter()
                dynamics_measurement(kc, voltage, standoff1=standoff, standoff2=standoff, file_name=f'{file_name_base}Dynamic_{standoff}mm_{voltage}V')
                end_time = time.perf_counter()
                print(f"Time taken for standoff {standoff} mm and voltage {voltage} V: {end_time - start_time:.2f} seconds")
                
    except KeyboardInterrupt:
        print("Interrupted by user, program quit.")
    finally:
        kc.inst.close()                          # Closes the connection to the Keithley controller
        kc.rm.close()                          # Closes the connection to the Prober controller
    
    full_time_end = time.perf_counter()
    print(f"Total time taken for all measurements: {full_time_end - full_time_start:.2f} seconds")
    winsound.Beep(1000, 500)