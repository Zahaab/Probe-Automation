import time
import pyvisa
import numpy as np
import matplotlib.pyplot as plt


def wait_completion(inst, print_output=False):
    """
    This is a loop to check the status of the test. The SP command returns :
    - 0 or 1 when the test is done running
    - 16 while the test is running (busy)
    These are bit wise according to page 3-3 of the manual

    Makes sure that any further actions (eg reading data) are undertaken after all data running is finished
    """

    while True:
        status = inst.query("SP")

        # Continues loop until the test is complete
        # Casting the status string to int makes the comparison simpler since it ignores the termination characters
        if int(status) in [0, 1]:
            print("Completed task.")
            break

        # Continuously prints the status of the test every second to the terminal
        if print_output:
            print(f"Status: {status}")
        time.sleep(10)

def retrieve_data(inst, variables):
    """
    Helps with reading in data from the instrument and outputs it into a numpy array in a similar style to how data is
    normally outputted using Clarius.

    At the moment this reads line by line as that is what all the examples use. In principle there is a command to read
    out the full dataset 'DO' (manual page 5-38) but I could not get it to output timestamps for whatever reason.
    """

    all_data = []

    # Sets a flag for later. Essentially the way continuous time measurements are controlled the data needs to be read
    # before data taking stops so this makes sure all arrays are of equal length. Otherwise, while variable_1's data is
    # being read, variable_2 has managed to gather some more data and creates a mismatch.
    index_final = None

    for variable in variables:                                  # For each variable you want to output data

        index = 1                                               # Need to read each line by index
        data_list = []
        while True:
            if index == index_final:
                break
            data = inst.query(f"RD '{variable}', {index}")      # Retrieve data
            data = float(data.strip('\r\n'))                    # Format data into machine usable
            if data == 0:                                       # Flag to stop when all measured data is accounted for
                if variable == variables[0]:                    # Flag based on first variable's data parsed (usually time)
                    index_final = index
                break
            data_list.append(float(data))
            index += 1                                          # Increment to get next point

        all_data.append(data_list)

    all_data = np.vstack(all_data).T

    return all_data

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


def configure_CVIV(inst):
    """
    To configure channels to SMU. Example given in manual page 4-13.
    """

    inst.write('UL')                            # Set into user library mode for user modules on KULT
    _ = inst.read()                             # 'eats' the ACK to remove it from the buffer

    inst.query("EX cvivulib cviv_configure(CVIV1, 1, 1, 1, 0, 0, Bias, Gnd, :(, :(, IV, )")
    wait_completion(inst)
    print("CVIV configure complete.")

    # Can use this to print the details of any package / module in KULT - see manual page 4-9
    # cviv_config_description = inst.query("GD cvivulib cviv_configure")
    # print(cviv_config_description)


def measurement_dc_helper(inst_obj, v_bias):

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

def standoff_measurement(pc_obj, inst_obj, heights, v_bias, file_name):
    """Runs measurement for 1 height set (3 heights) - 3 on/off intervals with 45 second intervals"""

    pc_obj.move_to_site("AWAY")
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

        print(f"\n------------------- Starting Standoff Variation (height set = {heights}, voltage = {v_bias}) -------------------- ")
        # print("(Check field is set to +/- 1V/um (based on thickness in Dektak))")

        for height in heights:
            pc_obj.move_to_site("AWAY")
            pc_obj.move_z_mm(height)
            time.sleep(40)

            pc_obj.move_to_site("RAD")
            time.sleep(44)

        pc_obj.move_to_site("AWAY")
        time.sleep(40)

        query = inst_obj.query("SP")  # Check measurement is running, should return 16 = busy
        if int(query) < 16:
            print('Measurement stopped unexpectedly, possible error')

        # Data has to be taken in this order for timed measurements since closing the measurement (ME 4) clears the buffer
        # so no data can be read out. This is why the index_final flag is needed in the retrieve_data function.
        data_full = retrieve_data(inst_obj, ["CH1T", "AI", "AV"])

        print("\n------------------- Standoff Variation Script Complete -------------------- ")

    except KeyboardInterrupt:
        print("Interrupted by user, program quit")

    finally:
        # Mainly only useful in debugging mode so that the connection is closed and data isn't being fed into the buffer
        inst_obj.query("ME 4")  # Abort / Close measurement

    # wait_completion(inst_obj)  # Should be redundant since measurement is finished but just incase

    save_data(file_name, data_full, ["Time", "AI", "AV"])
    plot_It(file_name, data_full, save_fig=True)

    return


def dynamics_measurement(pc_obj, inst_obj, v_bias, standoff1, standoff2, file_name):
    """Runs measurement for 1 bias voltage at 1 standoff - 2 on/off with 30 sec intervals"""

    pc_obj.move_to_site("AWAY")
    pc_obj.move_z_mm(standoff1)
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

        print(f"\n------------------- Starting Time Dynamics (voltage = {v_bias}) -------------------- ")

        if v_bias == 0:
            print("Waiting 30 seconds")
            time.sleep(30)
        else:
            pc_obj.move_to_site("AWAY")
            time.sleep(24)
            pc_obj.move_to_site("RAD")
            time.sleep(29)
            pc_obj.move_to_site("AWAY")
            pc_obj.move_z_mm(standoff2)
            time.sleep(22)
            pc_obj.move_to_site("RAD")
            time.sleep(29)
            pc_obj.move_to_site("AWAY")
            time.sleep(24)

        query = inst_obj.query("SP")  # Check measurement is running, should return 16 = busy
        if int(query) < 16:
            print('Measurement stopped unexpectedly, possible error')

        # Data has to be taken in this order for timed measurements since closing the measurement (ME 4) clears the buffer
        # so no data can be read out. This is why the index_final flag is needed in the retrieve_data function.
        data_full = retrieve_data(inst_obj, ["CH1T", "AI", "AV"])

        print("\n------------------- Time Dynamics Complete -------------------- ")

    except KeyboardInterrupt:
        print("Interrupted by user, program quit")

    finally:
        # Mainly only useful in debugging mode so that the connection is closed and data isn't being fed into the buffer
        inst_obj.query("ME 4")  # Abort / Close measurement

    # wait_completion(inst_obj)  # Should be redundant since measurement is finished but just incase

    save_data(file_name, data_full, ["Time", "AI", "AV"])
    plot_It(file_name, data_full, save_fig=True)

    return

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

