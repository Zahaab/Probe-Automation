"""
Modified from Zahaab's code for Probe control and Divij's code for Keithley control for use in RadTol experiment

Check / Notes :
- In my language, Z_SLOPE = multiplication factor & Z_OFFSET = theoretical 0mm distance
  (done this way to input relative measurements since commands are given relative to absolute 0 which doesn't actually exist)
- Distance mm is human coord and um is internal Probe Station coord

On startup:
- Load sample as normal - Bias bottom plate
- Make sure chuck height is maximum
- Make note of RAD and AWAY sites and add to config file
- Test everything moves as expected

- Check filename and structure of how data is stored
"""

import time
import pyvisa
import numpy as np
import matplotlib.pyplot as plt
import winsound
from Config import (MAX_STANDOFF_MM, MIN_STANDOFF_MM, Z_OFFSET, Z_SLOPE, PROBER_IP, KEITHLEY_RESOURCE,
                    AWAY_XCOORD, AWAY_YCOORD, RAD_XCOORD, RAD_YCOORD)
from Classes import ProberController
from measurement_funcs import (configure_CVIV, standoff_measurement, dynamics_measurement, iv_measurement)

full_time_start = time.perf_counter()

try:

    pc = ProberController(PROBER_IP)
    pc.connect()
    pc._build_site_map()
    print(f"Prober IP: {pc.ip}")
    print(f"Site Map: {pc.site_map}")

    rm = pyvisa.ResourceManager('@py')
    instrument = rm.open_resource(KEITHLEY_RESOURCE)
    # instrument.timeout = 60_000
    instrument.write_termination = '\0'
    instrument.read_termination = '\0'

    configure_CVIV(instrument)

    device_name = "DG030"
    pads = [1, 2, 3, 4]
    thicknesses = [12.60, 12.89, 12.83, 12.87]
    standoff_height_sets = [[1.5, 3.0, 4.5], [6.0, 7.5, 9.0], [10.5, 12.0, 13.5]]
    standoff_voltages = [round(i * 1, 1) for i in thicknesses]
    dynamics_voltages_positive = [1, 3, 5, 10, 30, 100]
    dynamics_voltages_negative = [-i for i in dynamics_voltages_positive]
    dynamics_voltages_all = [dynamics_voltages_positive, dynamics_voltages_negative]
    dynamics_standoff1 = 1.5
    dynamics_standoff2 = 12

    chosen_pad = 2
    chosen_pad_ind = pads.index(chosen_pad)

    file_name_base = f'ProbeStation/{device_name}/{device_name}-{chosen_pad}'

    # Printing device name for sanity check
    print(f'[MAIN] Device: {device_name}-{chosen_pad}')
    user_check = input("Press q to quit or any key to continue")
    if user_check == "q":
        raise KeyboardInterrupt

    # Re-open KXCI to purge everything
    # Run IV first to see what dark currents are bad

    start_time = time.perf_counter()
    voltages_base = np.array([0, 1, 3, 5, 10, 30, 100])
    voltages = np.concatenate([np.repeat(a, np.where(a == 0, 1, 3))
                               for a in (voltages_base, voltages_base[::-1][1:], -voltages_base[1:], (-voltages_base)[::-1][1:])])
    pc.move_to_site("AWAY")
    pc.move_z_mm(1.5)
    iv_measurement(instrument, voltages, file_name=f'{file_name_base}_IV')
    end_time = time.perf_counter()
    print(f"Time taken : {end_time - start_time:.2f} seconds")

    # user_check = input("Press q to quit or any key to continue")
    # if user_check == "q":
    #     raise KeyboardInterrupt

    # test_dc_measurement(instrument, 1, 'TestFile/test_dc_resistor_1V')
    # test_dc_measurement(instrument, 0.5, 'TestFile/test_dc_resistor_0.5V')

    for standoff_height_set in standoff_height_sets:
        start_time = time.perf_counter()
        standoff_voltage = standoff_voltages[chosen_pad_ind]
        standoff_measurement(pc, instrument, standoff_height_set, standoff_voltage,
                             file_name=f'{file_name_base}_standoffs_set{standoff_height_set}mm_{standoff_voltage}V')
        end_time = time.perf_counter()
        print(f"Time taken : {end_time - start_time:.2f} seconds")

    # user_check = input("Press q to quit or any key to continue")
    # if user_check == "q":
    #     raise KeyboardInterrupt

    count = 0
    mac_count = len(dynamics_voltages_all) - 1

    for dynamics_voltages in dynamics_voltages_all:

        for dynamics_voltage in dynamics_voltages:
            start_time = time.perf_counter()
            dynamics_measurement(pc, instrument, dynamics_voltage, dynamics_standoff1, dynamics_standoff2,
                                 file_name=f'{file_name_base}_dynamics_{dynamics_voltage}V_{dynamics_standoff1}mm_{dynamics_standoff2}mm')
            end_time = time.perf_counter()
            print(f"Time taken : {end_time - start_time:.2f} seconds")

        if count < mac_count:
            dynamics_measurement(pc, instrument, 0, dynamics_standoff1, dynamics_standoff2,
                                 file_name=f'{file_name_base}_dynamics_0V_{dynamics_standoff1}mm_short')
            count += 1

        

except KeyboardInterrupt:
    print("Interrupted by user, program quit.")
finally:
    instrument.close()                          # Closes the connection to the instrument
    rm.close()

full_time_end = time.perf_counter()
print(f"Total time taken for {device_name}-{chosen_pad} : {full_time_end - full_time_start:.2f} seconds")

# Play a sound when the code is done running - need to fix!
winsound.Beep(1000, 500)
