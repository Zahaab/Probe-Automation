import pyvisa
import time
import numpy as np
import matplotlib.pyplot as plt
# ==============================================================================
# 5. CORE TEST FUNCTIONS
# ==============================================================================

def save_data(file_name, all_data, data_names):
    """
    Saves data from numpy file into csv with custom names
    """

    np.savetxt(f'{file_name}.csv', all_data, delimiter=",", header=",".join(data_names), comments='')
    print(f"Data saved to : {file_name}.csv")


def plot_It(file_name, data, save_fig=False):

    fig = plt.figure(figsize=(8,6))
    ax = fig.add_subplot(111)

    ax.scatter(data[:,0], data[:, 1]*1e12, color='red',s=1)
    ax.ticklabel_format(axis='y', style='plain', useOffset=False)
    ax.set_xlabel(f'Time (s)')
    ax.set_ylabel(f'Current (pA)')
    ax.set_title(file_name.split('/')[-1])

    if save_fig:
        plt.savefig(f"{file_name}_fig.png")
        print(f"Figure saved to : {file_name}_fig.png")

    # plt.show()


def plot_IV(file_name, data, save_fig=False):

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111)
    ax.scatter(data[:, 1], data[:, 0]*1e12, color='red', s=1)
    ax.ticklabel_format(axis='y', style='plain', useOffset=False)
    ax.set_xlabel(f'Voltage (V)')
    ax.set_ylabel(f'Current (pA)')
    ax.set_title(file_name.split('/')[-1])

    if save_fig:
        plt.savefig(f"{file_name}_fig.png")
        print(f"Figure saved to : {file_name}_fig.png")

    # plt.show()


def dynamics_measurement(pc_obj, kei_obj, v_bias, standoff, file_name, repeats=3, time_delay=30):
    """Runs measurement for 1 bias voltage at 1 standoff - 2 on/off with 30 sec intervals"""

    pc_obj.move_to_site("AWAY")
    pc_obj.move_z_mm(standoff)
    time.sleep(1)

    if v_bias == np.nan:
        kei_obj.measurement_dc_helper(0)
    else:
        kei_obj.measurement_dc_helper(v_bias)

    try:

        kei_obj.inst.query("MD")
        kei_obj.inst.query("ME 1")  # Start measurement

        while True:
            query = kei_obj.inst.query("SP")  # Check measurement is running, should return 16 = busy
            if int(query) >= 16:
                break
            print(query)

        if v_bias == np.nan:
            time.sleep(time_delay)
            print("Waiting 30s to reset voltage measurements")
        else:
            pc_obj.move_to_site("AWAY")
            time.sleep(time_delay-2)
            for _ in range(repeats):
                pc_obj.move_to_site("RAD")
                time.sleep(time_delay-1)
                pc_obj.move_to_site("AWAY")
                time.sleep(time_delay-2)

        query = kei_obj.inst.query("SP")  # Check measurement is running, should return 16 = busy
        if int(query) < 16:
            print('Measurement stopped unexpectedly, possible error')

        # Data has to be taken in this order for timed measurements since closing the measurement (ME 4) clears the buffer
        # so no data can be read out. This is why the index_final flag is needed in the retrieve_data function.
        data_full = kei_obj.retrieve_data(["CH1T", "AI", "AV"])

        # print("\n------------------- Time Dynamics Complete -------------------- ")

    except KeyboardInterrupt:
        print("Interrupted by user, program quit")

    finally:
        # Mainly only useful in debugging mode so that the connection is closed and data isn't being fed into the buffer
        kei_obj.inst.query("ME 4")  # Abort / Close measurement

    # kei_obj.wait_completion()  # Should be redundant since measurement is finished but just incase

    save_data(file_name, data_full, ["Time", "AI", "AV"])
    plot_It(file_name, data_full, save_fig=True)

    return

def generate_voltages_sweep(sweep_params, dual_sweep=False):

    start, stop, step = sweep_params
    forward_sweep = np.arange(start, stop + (step / 2), step)
    if not dual_sweep:
        return forward_sweep
    else:
        backward_sweep = forward_sweep[::-1][1:]
        return np.concatenate((forward_sweep, backward_sweep))

def generate_voltages_step(voltages_base, no_repeats=3, dual_sweep=False):

    if type(voltages_base) == list:
        voltages_base = np.array(voltages_base)

    voltages_forward = np.concatenate([np.repeat(a, no_repeats)
        for a in (voltages_base, voltages_base[::-1][1:], -voltages_base[1:], (-voltages_base)[::-1][1:])])
    if dual_sweep:
        voltages_reverse = np.concatenate([np.repeat(a, no_repeats)
            for a in (-voltages_base[1:], (-voltages_base)[::-1][1:])])
        voltages = np.concatenate((voltages_forward, voltages_reverse))
    else:
        voltages = voltages_forward

    return voltages

def iv_measurement(kei_obj, voltage_array, file_name):

    voltage_list = ",".join([f"{v:.5f}" for v in voltage_array])

    kei_obj.inst.query("BC")  # Clear buffer
    # kei_obj.inst.query("ERRORLASTCLEAR")
    kei_obj.inst.query("RST")  # Full instrument reset (SMUs, PGUs, PMUs, CVUs)
    kei_obj.inst.query("*CLS")
    time.sleep(0.1)
    kei_obj.inst.query("DE")  # Enter channel definition page
    kei_obj.inst.query("CH1")  # Disable ALL channels first (safety)
    kei_obj.inst.query("CH2")  # Handles 4+ SMU systems too
    time.sleep(0.1)  # Let reset settle

    kei_obj.inst.query("DE")  # Access the SMU channel definition page
    # Channel 1. Voltage Name = AV, Current Name = AI, Voltage Source Mode, VAR1 sweep source function
    kei_obj.inst.query("CH 1, 'AV', 'AI', 1, 1")
    # Channel 2. Voltage Name = BV, Current Name = BI, Voltage Source Mode, Constant source function
    kei_obj.inst.query("CH 2, 'BV', 'BI', 1, 3")

    kei_obj.inst.query("SS")  # Access the source setup page
    # Setup VAR1 source function, linear sweep, -1 V to 1 V, 40 mV steps, 100 mA current compliance
    kei_obj.inst.query(f"VL 1, 1, 1e-8, {voltage_list}")
    # Configure constant voltage, SMU channel 2, 0 V output value, 100 mA current compliance
    kei_obj.inst.query("VC 2, 0, 0.1")
    kei_obj.inst.query("HT 0")  # Hold time - equivalent to 'hold time' on Clarius
    kei_obj.inst.query("DT 6.5")  # Delay time - how long between voltage on and measurement taken
    kei_obj.inst.query("IT 2")  # Integration time - 2 is equivilant to 'normal' speed on Clarius (
    kei_obj.inst.query("RS 5")  # Sets the measurement resolution to 5 digits
    kei_obj.inst.query("RG 1, 10e-9")  # Set the lowest current range to be used on SMU 1 to 100 nA
    # kei_obj.inst.query("RG 2, 100e-6")  # Set the lowest current range to be used on SMU 2 to 100 nA

    kei_obj.inst.query("SM")  # Access the measurement setup page
    kei_obj.inst.query("LI 'AV', 'AI'")  # Defines which parameters are measured / logged during a run

    # kei_obj.inst.query("DM1")  # Selects the graphics display mode for displaying graphs
    # # Configures x-axis of the graph to Channel 1 Voltage, minimum value of -1 V, maximum value of 1 V
    # kei_obj.inst.query("XN 'AV', 1, -1, 1")
    # # Configures y-axis of the graph to Channel 1 Current, minimum value of -100 nA, maximum value of 100 nA
    # kei_obj.inst.query("YA 'AI', 1, -100e-6, 100e-6")

    # Could not get this to work, doesnt really matter since its a display. Can only have either table or graph shown
    # kei_obj.inst.query("DM2")                 # Selects the table displace mode for displaying tables
    # kei_obj.inst.query("LI 'AV','AI','BV','BI'")

    try:

        kei_obj.inst.query("MD")
        kei_obj.inst.query("ME 1")  # Start measurement

        kei_obj.wait_completion()  # Wait of the sweep to finish

        data_full = kei_obj.retrieve_data(["AI", "AV"])

    except KeyboardInterrupt:
        print("Interrupted by user, program quit")

    finally:
        # Mainly only useful in debugging mode so that the connection is closed and data isn't being fed into the buffer
        kei_obj.inst.query("ME 4")  # Abort / Close measurement

    save_data(file_name, data_full, ["AI", "AV"])
    plot_IV(file_name, data_full, save_fig=True)

    return