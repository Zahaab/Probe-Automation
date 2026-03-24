# ==============================================================================
# 1. CONFIGURATION & SAFETY CONSTANTS
# ==============================================================================

# Set this to False to actually control hardware. 
# Set to True to print commands to console only (safe testing).
SIMULATION_MODE = False 

# Hardware Addresses (Update these!)!!!!!!!!!!LOOK AT ME!!!!!!!!!!!!!!!!
KEITHLEY_RESOURCE = '' # Example KXCI socket
PROBER_IP = '' # Example Prober IP

# Safety Limits - NOTE CHUCK IS AT MAX HIGHT AND DUT is 1mm thick*
# CHECK BEFORE USING NON STANDARD DEVICE
MIN_STANDOFF_MM = 1.5
MAX_STANDOFF_MM = 13.5
MAX_VOLTAGE = 210.0 # Absolute value limit

#Radiaation Site
RAD_XCOORD, RAD_YCOORD = 20000, 20000 # Example coordinates for RAD site

#Away Site
AWAY_XCOORD, AWAY_YCOORD = -20000, -20000

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
parameters = {
    "Output_Directory": "", #Add data output directory here
    "DUT_Name": "Device_A1",
    "Scope_Sites": ["RAD", "AWAY"],
    "Standoffs": [1.5, 5.0, 13.0], 
    "SMUs": ["SMU1", "SMU2"], 
    "IV_Range": (-5, 5, 0.5), 
    "PV_IV_Range": (-10, 10, 0.5),
    "Dynamic_Voltages": [5, 10] 
}

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