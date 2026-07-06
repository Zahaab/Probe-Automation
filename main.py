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
import os
import numpy as np
import json
from Config import PARAMS
from Config import PROBER_IP, KEITHLEY_RESOURCE
from Classes import DataManager, KeithleyController, ProberController
from MeasurementF import dynamics_measurement, iv_measurement, generate_voltages_step, generate_voltages_sweep


# If reading this for the first time, please follow the numbered comments through the code!
# Order is: 1. Main CONFIGURATION, 2-4. Classes, 5. Measurement Functions, 6. Main Execution

# ==============================================================================
# 6. MAIN EXECUTION
# ==============================================================================


def main():
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

        # Printing device name for sanity check & move away for safety
        file_name_base = f'ProbeStation/{PARAMS["DUT"]}'
        os.makedirs(file_name_base, exist_ok=True)
        print(f'[MAIN] Device File Path: {file_name_base}')

        estimated_time = 0

        if PARAMS["RUN_PV"]:

            if len(PARAMS["PV_IV_Range"]) == 2:
                pv_voltages = generate_voltages_step(PARAMS["PV_IV_Range"][0], no_repeats=PARAMS["PV_IV_Range"][1], dual_sweep=True)
            elif len(PARAMS["PV_IV_Range"])  == 3:
                pv_voltages = generate_voltages_sweep(PARAMS["PV_IV_Range"], dual_sweep=True)
            else:
                print(f'[MAIN] Invalid PV_IV Range : {PARAMS["PV_IV_Range"]}')
                raise KeyboardInterrupt

            # print(f'[MAIN] pv_voltages : {pv_voltages}')
            print(f'\n[MAIN] Voltages PV_IV : {PARAMS["PV_IV_Range"]}')
            print(f'[MAIN] Standoffs PV_IV : {PARAMS["PV_IV_Range"]}')

            estimated_time += len(pv_voltages) * 7 * len(PARAMS["PV_IV_Range"])

        if PARAMS["RUN_IV"]:

            if len(PARAMS["IV_RANGE"]) == 2:
                iv_voltages = generate_voltages_step(PARAMS["IV_RANGE"][0], no_repeats=PARAMS["IV_RANGE"][1], dual_sweep=True)
            elif len(PARAMS["IV_RANGE"]) == 3:
                iv_voltages = generate_voltages_sweep(PARAMS["IV_RANGE"], dual_sweep=True)
            else:
                print(f'[MAIN] Invalid IV Range : {PARAMS["IV_RANGE"]}')
                raise KeyboardInterrupt

            # print(f'[MAIN] iv_voltages : {iv_voltages}')
            print(f'\n[MAIN] Voltages IV : {PARAMS["IV_RANGE"]}')
            print(f'[MAIN] Standoffs IV : {PARAMS["IV_STANDOFFS"]}')
            print(f'[MAIN] IV Type : {PARAMS["IV_TYPE"]}')

            if PARAMS["IV_TYPE"].lower() == 'both':
                iv_time_mult = 2
            elif PARAMS["IV_TYPE"].lower() == 'away' or PARAMS["IV_TYPE"].lower() == 'rad':
                iv_time_mult = 1
            else:
                print(f'[MAIN] Invalid IV Type : {PARAMS["IV_TYPE"]}. Choose from "away", "rad" or "both"')
                raise KeyboardInterrupt

            estimated_time += len(iv_voltages) * 7 * len(PARAMS["IV_STANDOFFS"]) * iv_time_mult

        if PARAMS["RUN_TD_VOLTAGE"]:

            if PARAMS["TD_VOLTAGE_TYPE"].lower() == 'forward':
                dynamic_voltages = PARAMS["TD_VOLTAGE_VOLTAGES"]
            elif PARAMS["TD_VOLTAGE_TYPE"].lower() == 'reverse':
                dynamic_voltages = [-i for i in PARAMS["TD_VOLTAGE_VOLTAGES"]]
            elif PARAMS["TD_VOLTAGE_TYPE"].lower() == 'both':
                if 0 in PARAMS["TD_VOLTAGE_VOLTAGES"]:
                    dynamic_voltages = [i for i in PARAMS["TD_VOLTAGE_VOLTAGES"] if i != 0]
                    voltage_buffer = 0
                else:
                    dynamic_voltages = PARAMS["TD_VOLTAGE_VOLTAGES"]
                    voltage_buffer = np.nan
                dynamic_voltages = dynamic_voltages + [voltage_buffer] + [-i for i in dynamic_voltages]
            else:
                print(f'[MAIN] Invalid Time Dynamics type : {PARAMS["TD_VOLTAGE_TYPE"]}. Choose from : "forward", "reverse" or "both"')
                raise KeyboardInterrupt

            print(f'\n[MAIN] Voltage Scans :')
            print(f'[MAIN] Voltages : {dynamic_voltages}')
            print(f'[MAIN] Standoffs : {PARAMS["TD_VOLTAGE_STANDOFFS"]}')
            print(f'[MAIN] TD Repeats : {PARAMS["TD_REPEATS"]}')

            number_nan = np.count_nonzero(np.isnan(dynamic_voltages))
            estimated_time += ((len(dynamic_voltages) - number_nan) * (30 + 60*PARAMS["TD_REPEATS"]) + 30*number_nan) * len(PARAMS["TD_VOLTAGE_STANDOFFS"])

        if PARAMS["RUN_TD_STANDOFF"]:

            print(f'\n[MAIN] Standoff Scans :')
            print(f'[MAIN] Standoffs : {PARAMS["TD_STANDOFF_STANDOFFS"]}')
            print(f'[MAIN] Voltages : {PARAMS["TD_STANDOFF_VOLTAGES"]}')
            print(f'[MAIN] TD Repeats : {PARAMS["TD_REPEATS"]}')

            estimated_time += len(PARAMS["TD_STANDOFF_STANDOFFS"]) * (30 + 60*PARAMS["TD_REPEATS"]) * len(PARAMS["TD_STANDOFF_VOLTAGES"])

        pc.move_to_site("AWAY")
        print(f'\n[MAIN] Estimated Completion Time : {estimated_time:.2f} seconds / '
              f'{estimated_time/60:.2f} minutes / {estimated_time/3600:.2f} hours')

        user_check = input("\nPress q to quit or any key to continue (with enter)")
        if user_check == "q":
            raise KeyboardInterrupt
        print()

        if PARAMS["RUN_PV"]:
            pc.move_to_site("RAD")
            for standoff in PARAMS["PV_IV_STANDOFFS"]:

                pc.move_z_mm(standoff)
                print(f"\n----- Starting PV_IV measurement at standoff {standoff} mm (RAD) -----")
                start_time = time.perf_counter()
                iv_measurement(kc, pv_voltages, file_name=f'{file_name_base}/PV_IV_{standoff}mm_rad')
                end_time = time.perf_counter()
                print(f"Time taken for standoff {standoff} mm (RAD): {end_time - start_time:.2f} seconds")

            pc.move_to_site("AWAY")

        if PARAMS["RUN_IV"]:
            pc.move_to_site("AWAY")

            if PARAMS["IV_TYPE"].lower() == 'away':
                print(f"\n----- Starting IV measurement (AWAY) -----")
                start_time = time.perf_counter()
                iv_measurement(kc, iv_voltages, file_name=f'{file_name_base}/IV_away')
                end_time = time.perf_counter()
                print(f"Time taken (AWAY): {end_time - start_time:.2f} seconds")

            for standoff in PARAMS["IV_STANDOFFS"]:

                pc.move_z_mm(standoff)

                if PARAMS["IV_TYPE"].lower() == 'both':
                    print(f"\n----- Starting IV measurement at standoff {standoff} mm (AWAY) -----")
                    start_time = time.perf_counter()
                    pc.move_to_site("AWAY")
                    iv_measurement(kc, iv_voltages, file_name=f'{file_name_base}/IV_{standoff}mm_away')
                    end_time = time.perf_counter()
                    print(f"Time taken for standoff {standoff} mm (AWAY): {end_time - start_time:.2f} seconds")

                if PARAMS["IV_TYPE"].lower() == 'rad' or PARAMS["IV_TYPE"].lower() == 'both':
                    print(f"\n----- Starting IV measurement at standoff {standoff} mm (RAD) -----")
                    start_time = time.perf_counter()
                    pc.move_to_site("RAD")
                    iv_measurement(kc, iv_voltages, file_name=f'{file_name_base}/IV_{standoff}mm_rad')
                    end_time = time.perf_counter()
                    print(f"Time taken for standoff {standoff} mm (RAD): {end_time - start_time:.2f} seconds")

            pc.move_to_site("AWAY")

        if PARAMS["RUN_TD_VOLTAGE"]:
            pc.move_to_site("AWAY")
            for standoff in PARAMS["TD_VOLTAGE_STANDOFFS"]:
                pc.move_z_mm(standoff)
                for voltage in dynamic_voltages:

                    print(f"\n----- Starting Dynamic measurement at voltage {voltage} V and standoff {standoff} mm -----")
                    start_time = time.perf_counter()
                    dynamics_measurement(pc, kc, voltage, standoff=standoff, repeats=PARAMS["TD_REPEATS"], time_delay=PARAMS["TD_TIME"],
                                         file_name=f'{file_name_base}/dynamic_voltages_{voltage}V_{standoff}mm')
                    end_time = time.perf_counter()
                    print(f"Time taken for voltage {voltage} V standoff {standoff} mmk: {end_time - start_time:.2f} seconds")

        if PARAMS["RUN_TD_STANDOFF"]:
            pc.move_to_site("AWAY")
            for voltage in PARAMS["TD_STANDOFF_VOLTAGES"]:
                for standoff in PARAMS["TD_STANDOFF_STANDOFFS"]:

                    pc.move_z_mm(standoff)
                    print(f"\n----- Starting Dynamic measurement at voltage {voltage} V and standoff {standoff} mm -----")
                    start_time = time.perf_counter()
                    dynamics_measurement(pc, kc, voltage, standoff=standoff, repeats=PARAMS["TD_REPEATS"], time_delay=PARAMS["TD_TIME"],
                                         file_name=f'{file_name_base}/dynamic_standoffs_{voltage}V_{standoff}mm')
                    end_time = time.perf_counter()
                    print(f"Time taken for voltage {voltage} V at standoff {standoff} mm: {end_time - start_time:.2f} seconds")

    except KeyboardInterrupt:
        print("\n[MAIN] Interrupted by user, program quit")
        return
    finally:
        kc.inst.close()  # Closes the connection to the Keithley controller
        kc.rm.close()  # Closes the connection to the Prober controller

    full_time_end = time.perf_counter()
    actual_time = full_time_end - full_time_start
    print(f"\n[MAIN] Total time taken for all measurements : {actual_time:.2f} seconds")
    print(f'([MAIN] Difference : Actual - Estimated = {actual_time - estimated_time:.2f}seconds)')

    config = {
        "output_directory": f'ProbeStation/{PARAMS["DUT"]}',  # Add data output directory here
        "device_name": PARAMS["DUT"],
        "run_iv": PARAMS["RUN_IV"],
        "run_pv": PARAMS["RUN_PV"],
        "run_td_voltage": PARAMS["RUN_TD_VOLTAGE"],
        "run_td_standoff": PARAMS["RUN_TD_STANDOFF"],
        "iv_range": PARAMS["IV_RANGE"],
        "iv_standoffs": PARAMS["IV_STANDOFFS"],
        "iv_type": PARAMS["IV_TYPE"].lower(),
        "pv_iv_range": PARAMS["PV_IV_RANGE"],
        "pv_iv_standoffs": PARAMS["PV_IV_STANDOFFS"],
        "td_repeats": PARAMS["TD_REPEATS"],
        "td_time_delay": PARAMS["TD_TIME"],
        "td_voltage_standoffs": PARAMS["TD_VOLTAGE_STANDOFFS"],
        "td_voltage_voltages": dynamic_voltages,
        "td_standoff_voltages": PARAMS["TD_STANDOFF_VOLTAGES"],
        "td_standoff_standoffs": PARAMS["TD_STANDOFF_STANDOFFS"],
        "measurement_error" : 10e-15                                        # Change this at some point !!
    }
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

    winsound.Beep(1000, 500)

if __name__ == '__main__':
    main()
