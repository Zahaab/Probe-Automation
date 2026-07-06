# ==============================================================================
# 1. CONFIGURATION & SAFETY CONSTANTS
# ==============================================================================

# Set this to False to actually control hardware. 
# Set to True to print commands to console only (safe testing).
SIMULATION_MODE = False 

# Hardware Addresses (Update these!)!!!!!!!!!!LOOK AT ME!!!!!!!!!!!!!!!!
KEITHLEY_RESOURCE = 'TCPIP0::192.168.1.20::911::SOCKET' # Example KXCI socket
PROBER_IP = '192.168.1.50:53333' # Example Prober IP

# Safety Limits - NOTE CHUCK IS AT MAX HIGHT AND DUT is 1mm thick*
# CHECK BEFORE USING NON STANDARD DEVICE
MIN_STANDOFF_MM = 1.5
MAX_STANDOFF_MM = 13.5
MAX_VOLTAGE = 210.0 # Absolute value limit

#Radiaation Site
RAD_XCOORD, RAD_YCOORD = -20117, -13301   # Example coordinates for RAD site

#Away Site
AWAY_XCOORD, AWAY_YCOORD = 24500, 24500

# Z-Axis Calibration (Linear Interpolation)
# Do a 2-point calibration to convert mm to um for Z-axis movement
# Point 1: 1.5mm = -142000 um
# Point 2: 13.7mm = -129800 um
Z_CAL_P1 = (1.5, -142000)
Z_CAL_P2 = (13.5, -130000)

# Calculate slope (m) and intercept (c) for y = mx + c
# m = (y2 - y1) / (x2 - x1)
Z_SLOPE = (Z_CAL_P2[1] - Z_CAL_P1[1]) / (Z_CAL_P2[0] - Z_CAL_P1[0])
Z_OFFSET = Z_CAL_P1[1] - (Z_SLOPE * Z_CAL_P1[0])

# ==============================================================================
# RUN MAIN SEQUENCE IF THIS FILE IS EXECUTED DIRECTLY
# CHANGE PARAMETERS AS NEEDED

PARAMS = {
    "DUT" : "Device_A1",                                          # Update this for file naming
    "RUN_IV" : True,
    "IV_RANGE" : [[0, 1, 3, 5, 10, 15, 30, 50, 100], 3],          # voltages_base, no_repeats
    "IV_STANDOFFS" : [3, 7, 13],
    "IV_TYPE" : 'both',                                           # 'both' for RAD and AWAY measurements, 'rad' or 'away' for just one of them
    "RUN_PV": False,
    "PV_IV_Range" : [-1, 3, 0.02],                                # start, stop, step
    "PV_IV_STANDOFFS" : [3, 7, 13],
    "TD_REPEATS" : 3,
    "TD_TIME" : 30,
    "RUN_TD_VOLTAGE" : True,
    "TD_VOLTAGE_STANDOFFS" : [3, 6, 9, 12],                                 # Voltage scans : what standoffs to loop over
    "TD_VOLTAGE_VOLTAGES" : [0, 1, 3, 5, 10, 30, 100],                      # Voltages scans : what voltages
    "TD_VOLTAGE_TYPE" : 'both',                                             # 'both' for forward and reverse, 'forward' for +ve and 'reverse' for -ve
    "RUN_TD_STANDOFF": False,
    "TD_STANDOFF_VOLTAGES" : [1, 5, 10, 100],                               # Standoff scans : what voltages to loop over
    "TD_STANDOFF_STANDOFFS" : [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]      # Standoff scans : what standoffs
}

# Length of ON times ?


# Notes :
#   - Both PV_IV and IV are templates and can be interchanged (sweep vs step measurement type)
#   - Although very similar, both options are explicitly given depending on what needs to be done if different parameters
#       want to be run at once and there isn't an overlap.

# ==============================================================================
# IMAGING CONFIGURATION
# ==============================================================================

# ensure this path is valid for the machine running the Sentio software.
IMAGING_OUTPUT_DIR = r"C:\Sentio_Images\Batch_1"

# Camera Settings
# "Maximum" zoom corresponds to the smallest Field of View (FOV) in the API.
# Check the lens, but 200um is often a specific index or FOV value.
# You might need to adjust this index (0-3 usually) or exact FOV value based on your setup.
TARGET_ZOOM_INDEX = 3  # Example: 3 might be max zoom
# OR
TARGET_FOV = 200 # microns

# The Chunk Site Map
# Format: "Site_Name": (X_Microns, Y_Microns)
# These are CHUCK coordinates (where the chuck moves to put the device under the camera)
IMAGING_SITES = {
    "Device_1": (10000, 10000),
    "Device_2": (15000, 10000),
    "Device_3": (20000, 10000),
    # ... Add all 350 sites here ...
}