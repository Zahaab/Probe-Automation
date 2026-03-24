import pyvisa
import time
import threading
import csv
import os
import datetime
import numpy as np
from sentio_prober_control.Sentio.ProberSentio import SentioProber
from Config import MAX_VOLTAGE, MAX_STANDOFF_MM, MIN_STANDOFF_MM, SIMULATION_MODE, Z_OFFSET, Z_SLOPE, IMAGING_SITES, IMAGING_OUTPUT_DIR, TARGET_ZOOM_INDEX

# ==============================================================================
# 5. CORE TEST FUNCTIONS
# ==============================================================================

def RunIV(keithley, prober, smu_config, voltage_range, dut_name, standoff, site, data_mgr, test_name="IV"):
    start, stop, step = voltage_range
    if not (abs(start) <= MAX_VOLTAGE and abs(stop) <= MAX_VOLTAGE):
        raise ValueError(f"IV Range {start}-{stop} exceeds limit")

    print(f"\n--- Running {test_name} at {standoff}mm / {site} ---")
    
    # Run Software Sweep to get dual SMU data
    # Data format: [[V_Set, V_Sig, I_Sig, V_Gnd, I_Gnd], ...]
    data = keithley.run_software_sweep(smu_config[0], smu_config[1], start, stop, step)
    
    # Save with Expanded Headers
    header = ["Voltage_Set", f"Voltage_{smu_config[0]}", f"Current_{smu_config[0]}", f"Voltage_{smu_config[1]}", f"Current_{smu_config[1]}"]
    fname = data_mgr.generate_filename(test_name, dut_name, standoff, site, f"{start}to{stop}")
    data_mgr.save_data(fname, header, data)


def RunDynamics(keithley, prober, smu_config, voltage, dut_name, standoff, data_mgr):
    if not (abs(voltage) <= MAX_VOLTAGE):
        raise ValueError(f"Dynamic Voltage {voltage} exceeds limit")

    print(f"\n--- Running Dynamics at {standoff}mm @ {voltage}V ---")
    
    measurements = []
    stop_event = threading.Event()
    
    # Thread now takes both SMUs
    k_thread = threading.Thread(
        target=keithley.start_dynamic_sampling,
        args=(smu_config[0], smu_config[1], voltage, stop_event, measurements)
    )

    k_thread.start()
    
    try:
        cycles = 3
        for i in range(cycles):
            time.sleep(28) 
            prober.move_to_site("RAD")
            time.sleep(30)
            prober.move_to_site("AWAY")
        time.sleep(28)

    except KeyboardInterrupt:
        print("Test Interrupted by User!")
    finally:
        stop_event.set()
        k_thread.join()
        
        # Save with Expanded Headers
        header = ["Time_Sec", f"Voltage_{smu_config[0]}", f"Current_{smu_config[0]}", f"Voltage_{smu_config[1]}", f"Current_{smu_config[1]}"]
        fname = data_mgr.generate_filename("DYNAMIC", dut_name, standoff, "MOVING", f"{voltage}V")
        data_mgr.save_data(fname, header, measurements)
        
# Image Capture Function
