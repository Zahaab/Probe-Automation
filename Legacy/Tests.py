import pyvisa
import time
import threading
import csv
import os
import datetime
import numpy as np
from sentio_prober_control.Sentio.ProberSentio import SentioProber
from Classes import KeithleyController, ProberController, DataManager
from MeasurementF import RunIV, RunDynamics
from Config import KEITHLEY_RESOURCE, PROBER_IP, SIMULATION_MODE
# ==============================================================================
# INDEPENDENT TEST FUNCTIONS
# ==============================================================================

def test_iv_only(output_dir):
    print("\n>>> TESTING IV FUNCTION ONLY (Dual SMU Mode) <<<")
    
    # 1. Initialize Data Manager
    try:
        dm = DataManager(output_dir)
    except FileNotFoundError as e:
        print(f"Test Aborted: {e}")
        return

    # 2. Connect Hardware
    kc = KeithleyController(KEITHLEY_RESOURCE)
    pc = ProberController(PROBER_IP)
    kc.connect()
    
    # 3. Configure CVIV (Crucial Step!)
    kc.configure_cviv_routing("SMU1", 1) # Signal -> Port 1
    kc.configure_cviv_routing("SMU2", 2) # Ground -> Port 2
    
    # 4. Define Parameters
    # Note: We must pass BOTH SMUs to the function now
    smus = ["SMU1", "SMU2"] 
    rng = (-5, 5, 1) # Start, Stop, Step
    
    # 5. Run the Test
    # This will now use 'run_software_sweep' internally and save 4 columns of data
    RunIV(kc, pc, smus, rng, "TEST_DEVICE", 1.5, "TEST_SITE", dm)
    print(">>> IV Test Complete. Check output directory. <<<")

def test_dynamics_only(output_dir):
    print("\n>>> TESTING DYNAMICS FUNCTION ONLY (Dual SMU Mode) <<<")
    
    # 1. Initialize Data Manager
    try:
        dm = DataManager(output_dir)
    except FileNotFoundError as e:
        print(f"Test Aborted: {e}")
        return

    # 2. Connect Hardware
    kc = KeithleyController(KEITHLEY_RESOURCE)
    pc = ProberController(PROBER_IP)
    kc.connect()
    
    # Only connect prober if we are not in simulation mode 
    # (or if you want to test the movement logic too)
    if not SIMULATION_MODE: 
        pc.connect()
    
    # 3. Configure CVIV
    kc.configure_cviv_routing("SMU1", 1)
    kc.configure_cviv_routing("SMU2", 2)
    
    # 4. Define Parameters
    smus = ["SMU1", "SMU2"]
    voltage_setpoint = 10 # Volts
    
    # 5. Run the Test
    # This will now record V and I for BOTH SMUs while managing the threads
    RunDynamics(kc, pc, smus, voltage_setpoint, "TEST_DEVICE", 1.5, dm)
    print(">>> Dynamics Test Complete. Check output directory. <<<")
