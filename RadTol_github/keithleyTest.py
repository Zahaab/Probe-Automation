import time
import numpy as np
import matplotlib.pyplot as plt
import pyvisa
from measurement_funcs import wait_completion, save_data, retrieve_data, plot_IV, plot_It, configure_CVIV
from Config import KEITHLEY_RESOURCE

def measurement_dc_helper(inst_obj, v_bias):
    """Can't directly import this - since some parameters are likely to change"""

    inst_obj.query("BC")  # Clear buffer
    # inst_obj.query("ERRORLASTCLEAR")
    inst_obj.query("RST")  # Full instrument reset (SMUs, PGUs, PMUs, CVUs)
    inst_obj.query("*CLS")
    time.sleep(0.5)
    inst_obj.query("DE")  # Enter channel definition page
    inst_obj.query("CH1")  # Disable ALL channels first (safety)
    inst_obj.query("CH2")  # Handles 4+ SMU systems too
    time.sleep(0.1)  # Let reset settle

    inst_obj.query("DE")
    # Channel 1. Voltage Name = AV, Current Name = AI, Voltage Source Mode, Constant source function
    inst_obj.query("CH 1, 'AV', 'AI', 1, 3")
    # Channel 2. Voltage Name = BV, Current Name = BI, Voltage Source Mode, Constant source function
    inst_obj.query("CH 2, 'BV', 'BI', 1, 3")

    inst_obj.query("SS")
    # Constant voltage, SMU channel 1, 10 V output value, 100 mA current compliance
    inst_obj.query(f"VC 1, {v_bias}, 1e-8")
    # Constant voltage, SMU channel 2, 0 V output value, 100 mA current compliance
    inst_obj.query("VC 2, 0, 0.1")
    inst_obj.query("HT 0")
    inst_obj.query("DT 0")
    inst_obj.query("IT 2")
    inst_obj.query("RS 5")
    inst_obj.query("RG 1, 10e-9")                # 1e-12
    # inst_obj.query("RG 2, 1e-7")

    inst_obj.query("SM DM2")
    inst_obj.query("LI 'AV', 'AI'")
    # inst_obj.query("IN 0.01")  # Interval time - equivalent to 'interval' on Clarius
    inst_obj.query("NR 4096")  # Number of points - equivalent to 'number of samples' on Clarius

    # inst_obj.query("DM 2")

    # inst.query("DM 1")
    # # Configures the x-axis of the graph to plot time domain values from 0 to 300 seconds
    # inst.query("XT 0, 300")
    # # Configures the y1-axis of the graph to Channel 1 Voltage, minimum value of 0 V, maximum value of 15 mV
    # inst.query("YA 'AI', 1, 0, 1e-9")

def test_dc_measurement(inst_obj, v_bias, file_name):

    time.sleep(1)
    measurement_dc_helper(inst_obj, v_bias)

    try:

        inst_obj.query("MD")
        inst_obj.query("ME 1")  # Start measurement

        while True:
            query = inst_obj.query("SP")  # Check measurement is running, should return 16 = busy
            if int(query) >= 16:
                break
            print(query)

        print(f"\n------------------- Starting Resistor Test (voltage = {v_bias}) -------------------- ")

        time.sleep(10)

        query = inst_obj.query("SP")  # Check measurement is running, should return 16 = busy
        if int(query) < 16:
            print('Measurement stopped unexpectedly, possible error')

        # Data has to be taken in this order for timed measurements since closing the measurement (ME 4) clears the buffer
        # so no data can be read out. This is why the index_final flag is needed in the retrieve_data function.
        data_full = retrieve_data(inst_obj, ["CH1T", "AV", "AI"])

        print("\n------------------- Resistor Test Complete -------------------- ")

    except KeyboardInterrupt:
        print("Interrupted by user, program quit")

    finally:
        # Mainly only useful in debugging mode so that the connection is closed and data isn't being fed into the buffer
        inst_obj.query("ME 4")  # Abort / Close measurement

    wait_completion(inst_obj)  # Should be redundant since measurement is finished but just incase

    save_data(file_name, data_full, ["Time", "AV", "AI"])
    plot_It(file_name, data_full, save_fig=True)


def iv_measurement(inst_obj, voltage_array, file_name):

    voltage_list = ",".join([f"{v:.5f}" for v in voltage_array])

    inst_obj.query("BC")  # Clear buffer
    # inst_obj.query("ERRORLASTCLEAR")
    inst_obj.query("RST")  # Full instrument reset (SMUs, PGUs, PMUs, CVUs)
    inst_obj.query("*CLS")
    time.sleep(0.1)
    inst_obj.query("DE")  # Enter channel definition page
    inst_obj.query("CH1")  # Disable ALL channels first (safety)
    inst_obj.query("CH2")  # Handles 4+ SMU systems too
    time.sleep(0.1)  # Let reset settle

    inst_obj.query("DE")  # Access the SMU channel definition page
    # Channel 1. Voltage Name = AV, Current Name = AI, Voltage Source Mode, VAR1 sweep source function
    inst_obj.query("CH 1, 'AV', 'AI', 1, 1")
    # Channel 2. Voltage Name = BV, Current Name = BI, Voltage Source Mode, Constant source function
    inst_obj.query("CH 2, 'BV', 'BI', 1, 3")

    inst_obj.query("SS")  # Access the source setup page
    # Setup VAR1 source function, linear sweep, -1 V to 1 V, 40 mV steps, 100 mA current compliance
    inst_obj.query(f"VL 1, 1, 1e-8, {voltage_list}")
    # Configure constant voltage, SMU channel 2, 0 V output value, 100 mA current compliance
    inst_obj.query("VC 2, 0, 0.1")
    inst_obj.query("HT 0")  # Hold time - equivalent to 'hold time' on Clarius
    inst_obj.query("DT 6.5")  # Delay time - how long between voltage on and measurement taken
    inst_obj.query("IT 2")  # Integration time - 2 is equivilant to 'normal' speed on Clarius (
    inst_obj.query("RS 5")  # Sets the measurement resolution to 5 digits
    inst_obj.query("RG 1, 10e-9")  # Set the lowest current range to be used on SMU 1 to 100 nA
    # inst_obj.query("RG 2, 100e-6")  # Set the lowest current range to be used on SMU 2 to 100 nA

    inst_obj.query("SM")  # Access the measurement setup page
    inst_obj.query("LI 'AV', 'AI'")  # Defines which parameters are measured / logged during a run

    # inst_obj.query("DM1")  # Selects the graphics display mode for displaying graphs
    # # Configures x-axis of the graph to Channel 1 Voltage, minimum value of -1 V, maximum value of 1 V
    # inst_obj.query("XN 'AV', 1, -1, 1")
    # # Configures y-axis of the graph to Channel 1 Current, minimum value of -100 nA, maximum value of 100 nA
    # inst_obj.query("YA 'AI', 1, -100e-6, 100e-6")

    # Could not get this to work, doesnt really matter since its a display. Can only have either table or graph shown
    # instrument.query("DM2")                 # Selects the table displace mode for displaying tables
    # instrument.query("LI 'AV','AI','BV','BI'")

    try:

        inst_obj.query("MD")
        inst_obj.query("ME 1")  # Start measurement

        print(f"\n------------------- Starting IV Test -------------------- ")

        wait_completion(inst_obj)  # Wait of the sweep to finish

        data_full = retrieve_data(inst_obj, ["AI", "AV"])

        print("\n------------------- IV Test Complete -------------------- ")

    except KeyboardInterrupt:
        print("Interrupted by user, program quit")

    finally:
        # Mainly only useful in debugging mode so that the connection is closed and data isn't being fed into the buffer
        inst_obj.query("ME 4")  # Abort / Close measurement

    save_data(file_name, data_full, ["AI", "AV"])
    plot_IV(file_name, data_full, save_fig=True)

    return


try:
    rm = pyvisa.ResourceManager('@py')
    instrument = rm.open_resource(KEITHLEY_RESOURCE)
    # instrument.timeout = 60_000
    instrument.write_termination = '\0'
    instrument.read_termination = '\0'

    configure_CVIV(instrument)

    # Re-open KXCI to purge everything
    # Run IV first to see what dark currents are bad

    start_time = time.perf_counter()
    voltages_base = np.array([0, 1, 3, 5, 10, 30, 100])
    voltages = np.concatenate([np.repeat(a, np.where(a == 0, 1, 3))
                               for a in (voltages_base, voltages_base[::-1][1:], -voltages_base[1:],
                                         (-voltages_base)[::-1][1:])])
    iv_measurement(instrument, voltages, file_name=f'TestFile/test_resistor_iv')

    end_time = time.perf_counter()
    print(f"Time taken : {end_time - start_time:.2f} seconds")


except KeyboardInterrupt:
    print("Interrupted by user, program quit.")
finally:
    instrument.close()  # Closes the connection to the instrument
    rm.close()

