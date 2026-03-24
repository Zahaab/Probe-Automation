import pyvisa
import time
import threading
import csv
import os
import datetime
import numpy as np
from sentio_prober_control.Sentio.ProberSentio import SentioProber
from Config import KEITHLEY_RESOURCE, PROBER_IP, SIMULATION_MODE, parameters
from Classes import DataManager, KeithleyController, ProberController
from MeasurementF import RunIV, RunDynamics
from Tests import test_iv_only, test_dynamics_only

# If reading this for the first time, please follow the numbered comments through the code!
# Order is: 1. Main CONFIGURATION, 2-4. Classes, 5. Measurement Functions, 6. Main Execution

# ==============================================================================
# 6. MAIN EXECUTION
# ==============================================================================

def main_sequence(params):
    try:
        dm = DataManager(params['Output_Directory'])
    except FileNotFoundError as e:
        print(f"CRITICAL ERROR: {e}")
        return

    kc = KeithleyController(KEITHLEY_RESOURCE)
    pc = ProberController(PROBER_IP)
    
    try:
        kc.connect()
        pc.connect()
        
        smus = params['SMUs']
        kc.configure_cviv_routing(smus[0], 1)
        kc.configure_cviv_routing(smus[1], 2)
        print("[SETUP] CVIV Switch Matrix Configured.")

        dut = params['DUT_Name']
        
        for dist in params['Standoffs']:
            pc.move_z_mm(dist)
            
            # --- Measurement Sequence ---
            pc.move_to_site("AWAY")
            
            if params['IV_Range']:
                RunIV(kc, pc, smus, params['IV_Range'], dut, dist, "AWAY", dm, "IV")
            if params['PV_IV_Range']:
                RunIV(kc, pc, smus, params['PV_IV_Range'], dut, dist, "AWAY", dm, "PV_IV")
                
            pc.move_to_site("RAD")
            
            if params['IV_Range']:
                RunIV(kc, pc, smus, params['IV_Range'], dut, dist, "RAD", dm, "IV")
            if params['PV_IV_Range']:
                RunIV(kc, pc, smus, params['PV_IV_Range'], dut, dist, "RAD", dm, "PV_IV")
                
            pc.move_to_site("AWAY")
            
            if params['Dynamic_Voltages']:
                for vol in params['Dynamic_Voltages']:
                    RunDynamics(kc, pc, smus, vol, dut, dist, dm)
                    
    except Exception as e:
        print(f"CRITICAL ERROR DURING RUN: {e}")

# MONEY TIME

main_sequence(parameters)

# Test functions
#test_iv_only(parameters['Output_Directory'])
#test_dynamics_only(parameters['Output_Directory'])