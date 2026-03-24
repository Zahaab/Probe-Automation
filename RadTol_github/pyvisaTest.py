"""
Manual can be found at : https://www.tek.com/en/manual/parametric-analyzer/model-4200a-scs-kxci-remote-control-programming-keithley-4200a-scs-parameter-analyzer

This code works in system mode so most work is done by the Keithley4200 itself. This both helps speed things up instead
of manually deeling with loops and removes the need for multithreading if trying to communicate with another instrument

Lost of example code taken from:
https://github.com/tektronix/keithley/blob/main/Instrument_Examples/Model_4200A/KXCI_Examples/SMU/System%20Mode/family_of_curves%20data%20retrival.py
"""

import pyvisa
import time
import numpy as np

from Config import KEITHLEY_RESOURCE

rm = pyvisa.ResourceManager('@py')

# Replace 'GPIB0::14::INSTR' with your instrument's address
instrument = rm.open_resource(KEITHLEY_RESOURCE)
# instrument.timeout = 60_000                     # Can omit, was there just incase of timeout during sleep

instrument.write_termination = '\0'             # Based on the set string terminator in KCon and saves you writing it after every line
instrument.read_termination = '\0'

# # Communicate with the instrument
# print(instrument.query('*IDN?'))              # Request identification
#
# instrument.write('*IDN?')
# print(instrument.read())


# Essentially you have read, write and query (write and read) commands depending on how you want to do things
# - write however leaves the output of the last command in the buffer (which is always atleast 'ACK') and so when you
#   next read or query you have those commands leftover making a mess of everything
# - query will automatically deal with them and won't leave them stuck in the buffer - better in my opinion


def wait_completion(inst):
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
        print(f"Status: {status}")
        time.sleep(1)

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

    np.savetxt(file_name, all_data, delimiter=",", header=",".join(data_names), comments='')
    print(f"Data saved to : {file_name}")


# As a basic overview, commands are structured into different 'modes' (system, user, modeless) as well as different
# 'pages'. To open a command belonging to a mode or page you have to first open that page and then give the command.
# An overview of all commands is given at the start of section 5 in the manual as well as this way of working.


def test_IV_resistor(inst):
    """Commands to take an IV sweep. Test was done with a 10k ohm resistor."""

    voltage_array = np.linspace(-1, 1, 50)
    voltage_list = ",".join([f"{v:.5f}" for v in voltage_array])

    inst.query("BC")                        # Clear all readings from the buffer
    inst.query("*RST")                      # Reset instruments to default settings - doesn't reset CVIV!

    inst.query("DE")                        # Access the SMU channel definition page
    # Channel 1. Voltage Name = AV, Current Name = AI, Voltage Source Mode, VAR1 sweep source function
    inst.query("CH 1, 'AV', 'AI', 1, 1")
    # Channel 2. Voltage Name = BV, Current Name = BI, Voltage Source Mode, Constant source function
    inst.query("CH 2, 'BV', 'BI', 1, 3")

    inst.query("SS")                        # Access the source setup page
    # Setup VAR1 source function, linear sweep, -1 V to 1 V, 40 mV steps, 100 mA current compliance
    inst.query(f"VL 1, 1, 100e-3, {voltage_list}")
    # Configure constant voltage, SMU channel 2, 0 V output value, 100 mA current compliance
    inst.query("VC 2, 0, 100e-3")
    inst.query("HT 0")                      # Hold time - equivalent to 'hold time' on Clarius
    inst.query("DT 0")                      # Delay time - how long between voltage on and measurement taken
    inst.query("IT 2")                      # Integration time - 2 is equivilant to 'normal' speed on Clarius (
    inst.query("RS 5")                      # Sets the measurement resolution to 5 digits
    inst.query("RG 1, 100e-6")              # Set the lowest current range to be used on SMU 1 to 100 nA
    inst.query("RG 2, 100e-6")              # Set the lowest current range to be used on SMU 2 to 100 nA

    inst.query("SM")                        # Access the measurement setup page
    inst.query("LI 'AV', 'AI'")             # Defines which parameters are measured / logged during a run
    inst.query("NR 51")

    inst.query("DM1")                       # Selects the graphics display mode for displaying graphs
    # Configures x-axis of the graph to Channel 1 Voltage, minimum value of -1 V, maximum value of 1 V
    inst.query("XN 'AV', 1, -1, 1")
    # Configures y-axis of the graph to Channel 1 Current, minimum value of -100 nA, maximum value of 100 nA
    inst.query("YA 'AI', 1, -100e-6, 100e-6")
    # inst.query("NR 51")

    # Could not get this to work, doesnt really matter since its a display. Can only have either table or graph shown
    # instrument.query("DM2")                 # Selects the table displace mode for displaying tables
    # instrument.query("LI 'AV','AI','BV','BI'")

    inst.query("MD")                        # Access the measurement control page
    inst.query("ME 1")                      # Maps channel 1 (runs the sweep)

    wait_completion(inst)                   # Wait of the sweep to finish

    # Reads, parses and saves the data
    data_full = retrieve_data(inst, ["CH1T", "AV", "AI"])
    save_data('test_iv_output.csv', data_full, ["Time", "AV", "AI"])

def test_DC(inst):
    """
    Commands to take a constant DC current measurement. Test was done with a 10k ohm resistor.

    (Uncommented commands are identical to the ones above, comments omitted for readability)
    """

    inst.query("BC")
    inst.query("*RST")

    # print(inst.query("ERRORLASTGET?"))      # Returns the last error in buffer (if there is one)

    inst.query("DE")
    # Channel 1. Voltage Name = AV, Current Name = AI, Voltage Source Mode, VAR1 sweep source function
    inst.query("CH 1, 'AV', 'AI', 1, 3")
    # Channel 2. Voltage Name = BV, Current Name = BI, Voltage Source Mode, Constant source function
    inst.query("CH 2, 'BV', 'BI', 1, 3")

    inst.query("SS")
    # Setup VAR1 source function, linear sweep, -1 V to 1 V, 40 mV steps, 100 mA current compliance
    inst.query("VC 1, 1, 1e-3")
    # Configure constant voltage, SMU channel 2, 0 V output value, 100 mA current compliance
    inst.query("VC 2, 0, 1e-3")
    inst.query("HT 0")
    inst.query("DT 0")
    inst.query("IT 2")
    inst.query("RS 5")
    inst.query("RG 1, 100e-7")
    inst.query("RG 2, 100e-7")

    inst.query("SM")
    inst.query("LI 'AV', 'AI'")
    # inst.query("IN 0.01")                   # Interval time - equivalent to 'interval' on Clarius
    inst.query("NR 4096")                   # Number of points - equivalent to 'number of samples' on Clarius

    inst.query("DM 2")

    # inst.query("DM 1")
    # # Configures the x-axis of the graph to plot time domain values from 0 to 10 seconds
    # inst.query("XT 0, 2")
    # # Configures the y1-axis of the graph to Channel 1 Voltage, minimum value of 0 V, maximum value of 15 mV
    # inst.query("YA 'AI', 1, 0, 2e-4")

    try:

        inst.query("MD")
        inst.query("ME 1")                      # Start measurement

        print(inst.query("SP"))                 # Check measurement is running, should return 16 = busy
        time.sleep(5)
        print(inst.query("SP"))                 # Check measurement is running, should return 16 = busy

        # Data has to be taken in this order for timed measurements since closing the measurement (ME 4) clears the buffer
        # so no data can be read out. This is why the index_final flag is needed in the retrieve_data function.
        data_full = retrieve_data(inst, ["CH1T", "AV", "AI"])
        save_data('test_dc_output.csv', data_full, ["Time", "AV", "AI"])

    except KeyboardInterrupt:
        print("Interrupted by user, program quit")

    finally:
        # Mainly only useful in debugging mode so that the connection is closed and data isn't being fed into the buffer
        inst.query("ME 4")                      # Abort / Close measurement

    wait_completion(inst)                       # Should be redundant since measurement is finished but just incase

# Note on how to structure commands:
# - if using specified voltages or specified number of points, use wait_completion() THEN read the data
# - if using specified time, read data THEN abort measurement (wait_completion() isn't needed but doesnt hurt)

try:
    # configure_CVIV(instrument)
    test_IV_resistor(instrument)
    # test_DC(instrument)
except KeyboardInterrupt:
    print("Interrupted by user, program quit")
finally:
    instrument.close()                          # Closes the connection to the instrument
    rm.close()
