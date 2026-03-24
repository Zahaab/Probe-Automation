import pyvisa
import time
import threading
import csv
import os
import datetime
import numpy as np
from Config import MAX_STANDOFF_MM, MIN_STANDOFF_MM, SIMULATION_MODE, Z_OFFSET, Z_SLOPE, PROBER_IP, KEITHLEY_RESOURCE

def setup_and_test_keithley(resource_str, smu_name, cviv_port):
    """
    Connects to Keithley, configures CVIV routing, and performs a 0V smoke test.
    
    Args:
        resource_str (str): VISA resource ID (e.g., 'GPIB0::17::INSTR')
        smu_name (str): The SMU key (e.g., 'SMU1')
        cviv_port (int): The output port on the CVIV (1, 2, 3, etc.)
        
    Returns:
        inst (pyvisa.Resource): The open session if successful.
        None: If connection failed.
    """
    smu_map = {"SMU1": 1, "SMU2": 2, "SMU3": 3, "SMU4": 4}
    
    # Input Validation
    if smu_name not in smu_map:
        print(f"[ERROR] Invalid SMU Name: {smu_name}")
        return None

    smu_id = smu_map[smu_name]
    
    try:
        # --- 1. CONNECT ---
        rm = pyvisa.ResourceManager('@py')
        inst = rm.open_resource(resource_str)
        # inst.timeout = 60000  # 60 seconds

        inst.write_termination = '\0'
        inst.read_termination = '\0'
        
        # Initialize
        inst.write('UL')   # Unlock front panel (good practice)
        # inst.write('DR 1') # data transger on (1)
        
        # Verify Identity (The "Are you there?" check)
        # 'ID' is the standard KXCI command to ask "Who are you?"
        try:
            device_id = inst.query("*IDN?")
            print(f"[KEITHLEY] Connected: {device_id.strip()}")
        except:
            print("[KEITHLEY] Connected, but ID query failed (Device might be busy)")

        # --- 2. CONFIGURE CVIV ---
        # We wrap the LPT command in 'EX' (Execute)
        inst.write("EX cvivulib cviv_configure (CVIV1, 1, 1, 1, 0, 0, Bias, Gnd, :(, :(, IV, )")
        # time.sleep(2)`
        # inst.write('EX cvivulib cviv_display_power(0)')
        # print(f"[KEITHLEY] Routing {smu_name} -> CVIV Port {cviv_port}...")
        # cmd = f'EX "cviv_connect({smu_id}, {cviv_port})"'
        # inst.write(cmd)
        
        # Wait for relay settling 
        # time.sleep(2)

        # # --- 3. SMU HEALTH CHECK (The "Test") ---
        # # We will Force 0V and Measure Voltage.
        # # This is safe regardless of what is connected (Open, Short, or DUT).
        #
        # print(f"[KEITHLEY] Verifying {smu_name} response...")
        #
        # inst.write(f'CN {smu_id}')               # Enable SMU
        # inst.write(f'DV {smu_id}, 0, 0, 100e-3') # Force 0V, Range 0 (Auto), Compliance 100mA
        # time.sleep(0.1)                          # Settling time
        #
        # # Measure Voltage
        # measured_v = float(inst.query(f'MV {smu_id}'))
        #
        # # Turn it off immediately
        # inst.write(f'DV {smu_id}, 0, 0, 100e-3') # Zero out
        # inst.write(f'CL {smu_id}')               # Disable SMU
        #
        # print(f"[KEITHLEY] Health Check Passed. Measured Offset: {measured_v:.4e} V")
        #
        # return inst

    except pyvisa.VisaIOError as e:
        print(f"[CRITICAL] VISA/Connection Error: {e}")
        return None
    except Exception as e:
        print(f"[CRITICAL] General Error: {e}")
        return None

    inst.close()
    rm.close()

setup_and_test_keithley(KEITHLEY_RESOURCE, "SMU1", 1)

