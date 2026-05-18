import pyvisa
import time
import threading
import csv
import os
import datetime
import numpy as np
from sentio_prober_control.Sentio.ProberSentio import SentioProber
from sentio_prober_control.Sentio.Enumerations import SnapshotType, SnapshotLocation, CameraMountPoint
from sentio_prober_control.Sentio.Enumerations import XyReference, ZReference
from Config import MAX_STANDOFF_MM, MIN_STANDOFF_MM, SIMULATION_MODE, Z_OFFSET, Z_SLOPE, RAD_XCOORD, RAD_YCOORD, AWAY_XCOORD, AWAY_YCOORD, PROBER_IP

# ==============================================================================
# 2. HELPER CLASS: DATA SAVER
# ==============================================================================

class DataManager:
    def __init__(self, base_output_dir):
        self.base_dir = base_output_dir
        if not os.path.exists(self.base_dir):
            raise FileNotFoundError(f"The specified output directory does not exist: {self.base_dir}")
        print(f"[DATA] Outputting to: {self.base_dir}")

    def get_standoff_dir(self, standoff_mm):
        folder_name = f"{standoff_mm}mm_Standoff"
        full_path = os.path.join(self.base_dir, folder_name)
        if not os.path.exists(full_path):
            os.makedirs(full_path)
            print(f"[DATA] Created subdirectory: {full_path}")
        return full_path

    def generate_filename(self, test_type, dut_name, standoff, site, run_params):
        save_dir = self.get_standoff_dir(standoff)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"{test_type}_{dut_name}_{standoff}mm_{site}_{run_params}_{timestamp}.csv"
        return os.path.join(save_dir, fname)

    def save_data(self, filepath, header, data_rows):
        if SIMULATION_MODE:
            print(f"[DATA] Simulating save to: {filepath}")
            return
        try:
            with open(filepath, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(data_rows)
            print(f"[DATA] Saved: {os.path.basename(filepath)}")
        except Exception as e:
            print(f"[DATA] ERROR Saving file: {e}")

# ==============================================================================
# 3. CLASS: KEITHLEY CONTROLLER 
# ==============================================================================

class KeithleyController:
    def __init__(self, resource_str):
        self.resource_str = resource_str
        self.inst = None
        self.rm = None
        self.connected = False
        self.smu_map = {"SMU1": 1, "SMU2": 2, "SMU3": 3, "SMU4": 4}

    def connect(self):
        if SIMULATION_MODE:
            print(f"[KEITHLEY] Simulated Connection to {self.resource_str}")
            self.connected = True
            return

        try:
            self.rm = pyvisa.ResourceManager('@py')
            self.inst = self.rm.open_resource(self.resource_str)
            self.inst.write_termination = '\0'
            self.inst.read_termination = '\0'
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Keithley: {e}")
    
    def wait_completion(self, print_output=False):
        """
        This is a loop to check the status of the test. The SP command returns :
        - 0 or 1 when the test is done running
        - 16 while the test is running (busy)
        These are bit wise according to page 3-3 of the manual

        Makes sure that any further actions (eg reading data) are undertaken after all data running is finished
        """
        while True:
            status = self.inst.query("SP")

            # Continues loop until the test is complete
            # Casting the status string to int makes the comparison simpler since it ignores the termination characters
            if int(status) in [0, 1]:
                print("Completed task.")
                break

            # Continuously prints the status of the test every second to the terminal
            if print_output:
                print(f"Status: {status}")
            time.sleep(10)
    
    def configure_CVIV(self):
        """
        To configure channels to SMU. Example given in manual page 4-13.
        """

        self.inst.write('UL')                            # Set into user library mode for user modules on KULT
        _ = self.inst.read()                             # 'eats' the ACK to remove it from the buffer

        self.inst.query("EX cvivulib cviv_configure(CVIV1, 1, 1, 1, 0, 0, Bias, Gnd, :(, :(, IV, )")
        self.wait_completion()
        print("CVIV configure complete.")

        # Can use this to print the details of any package / module in KULT - see manual page 4-9
        # cviv_config_description = self.inst.query("GD cvivulib cviv_configure")
        # print(cviv_config_description)

    def measurement_dc_helper(self, v_bias):

        self.inst.query("BC")  # Clear buffer
        # self.inst.query("ERRORLASTCLEAR")
        self.inst.query("RST")  # Full instrument reset (SMUs, PGUs, PMUs, CVUs)
        self.inst.query("*CLS")
        time.sleep(0.5)
        self.inst.query("DE")  # Enter channel definition page
        self.inst.query("CH1")  # Disable ALL channels first (safety)
        self.inst.query("CH2")  # Handles 4+ SMU systems too
        time.sleep(0.1)  # Let reset settle

        self.inst.query("DE")
        # Channel 1. Voltage Name = AV, Current Name = AI, Voltage Source Mode, Constant source function
        self.inst.query("CH 1, 'AV', 'AI', 1, 3")
        # Channel 2. Voltage Name = BV, Current Name = BI, Voltage Source Mode, Constant source function
        self.inst.query("CH 2, 'BV', 'BI', 1, 3")

        self.inst.query("SS")
        # Constant voltage, SMU channel 1, 10 V output value, 100 mA current compliance
        self.inst.query(f"VC 1, {v_bias}, 1e-8")
        # Constant voltage, SMU channel 2, 0 V output value, 100 mA current compliance
        self.inst.query("VC 2, 0, 0.1")
        self.inst.query("HT 0")
        self.inst.query("DT 0")
        self.inst.query("IT 2")
        self.inst.query("RS 5")
        self.inst.query("RG 1, 10e-9")                # 1e-12
        # self.inst.query("RG 2, 1e-7")

        self.inst.query("SM DM2")
        self.inst.query("LI 'AV', 'AI'")
        # self.inst.query("IN 0.01")  # Interval time - equivalent to 'interval' on Clarius
        self.inst.query("NR 4096")  # Number of points - equivalent to 'number of samples' on Clarius

        # self.inst.query("DM 2")

        # inst.query("DM 1")
        # # Configures the x-axis of the graph to plot time domain values from 0 to 300 seconds
        # inst.query("XT 0, 300")
        # # Configures the y1-axis of the graph to Channel 1 Voltage, minimum value of 0 V, maximum value of 15 mV
        # inst.query("YA 'AI', 1, 0, 1e-9")
        
    def retrieve_data(self, variables):
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
                data = self.inst.query(f"RD '{variable}', {index}")      # Retrieve data
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
# ==============================================================================
# 4. CLASS: SENTIO PROBER CONTROLLER
# ==============================================================================

class ProberController:
    def __init__(self, ip_address):
        self.ip = ip_address
        self.prober = None
        self.site_map = {} 

    def connect(self):
        if SIMULATION_MODE:
            print(f"[PROBER] Simulated Connection to {self.ip}")
            self.site_map = {"RAD": (RAD_XCOORD, RAD_YCOORD), "AWAY": (AWAY_XCOORD, AWAY_YCOORD)}
            return

        try:
            self.prober = SentioProber.create_prober("tcpip", self.ip)
            self._build_site_map()
            print("[PROBER] Connected and Site Map Built.")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Sentio: {e}")

    def _build_site_map(self):
        """
        Builds a mapping of site names to coordinates. In a real implementation, 
        this might read from a config file or be set up through a calibration routine.
        For now, we hardcode based on Config.py constants.
        """
        if SIMULATION_MODE: return
        # Placeholder: Update indices `0` and `1` to match your actual map file.
        self.site_map = {"RAD": (RAD_XCOORD, RAD_YCOORD), "AWAY": (AWAY_XCOORD, AWAY_YCOORD)}

    def move_z_mm(self, mm_distance):
        """
        Converts mm standoff to machine microns and moves Scope Z.
        """
        if not (MIN_STANDOFF_MM <= mm_distance <= MAX_STANDOFF_MM):
            raise ValueError(f"Standoff {mm_distance}mm out of range ({MIN_STANDOFF_MM}-{MAX_STANDOFF_MM})")

        # Linear Calibration Calculation
        target_microns = (Z_SLOPE * mm_distance) + Z_OFFSET
        
        if SIMULATION_MODE:
            print(f"[PROBER] Moving Scope Z to {mm_distance}mm ({target_microns:.2f} um)")
            return

        # Move Z-axis to target microns
        start_Z_um = self.prober.get_scope_z()
        start_Z_mm = (start_Z_um - Z_OFFSET) / Z_SLOPE
        print(f"[PROBER] Moving Scope Z from to {start_Z_mm:.2f}mm ({start_Z_um:.2f} um) to {mm_distance}mm ({target_microns:.2f} um)")
        self.prober.move_scope_z(ZReference.Zero, target_microns)

    def move_to_site(self, site_name):
        if site_name not in self.site_map:
            raise ValueError(f"Site name '{site_name}' not defined in site_map.")
        
        site_coords = self.site_map[site_name]
        
        if SIMULATION_MODE:
            print(f"[PROBER] Moving to Site '{site_name}' (Coordinates {site_coords})")
            return

        start_x, start_y = self.prober.get_scope_xy()
        print(f"[PROBER] Moving from ({start_x:.2f}, {start_y:.2f}) to Site '{site_name}' at ({site_coords[0]}, {site_coords[1]})")
        self.prober.move_scope_xy(XyReference.Zero, site_coords[0], site_coords[1])
    
    def move_chuck_xy(self, x, y):
        """Moves the chuck stage to absolute X, Y coordinates (microns)."""
        if SIMULATION_MODE:
            print(f"[SIM] Moving Chuck to X:{x}, Y:{y}")
            return
            
        # Move chuck in main coordinate system
        self.prober.move_chuck_xy(XyReference.Zero, x, y)
        print(f"[PROBER] Chuck moved to {x}, {y}")
        
    def set_camera_zoom(self, zoom_index):
        """BROKEN! Sets the microscope zoom level."""
        if SIMULATION_MODE:
            print(f"[SIM] Setting Zoom to Index {zoom_index}")
            return

        # Try 'vis:lens_zoom_level' should work.
        self.prober.vision.set_lens_zoom_level(zoom_index)
        
        print(f"[VISION] Zoom set to {zoom_index}")
        
    def auto_focus(self):
        """BROKEN! Triggers the Vision Auto Focus."""
        if SIMULATION_MODE:
            print("[SIM] Autofocusing...")
            return

        print("[VISION] Starting Autofocus...")
        # Execute AF and wait for completion
        self.prober.vision.auto_focus()
        print("[VISION] Autofocus Complete.")
        
    def snap_image_remote(self, snap_path, gain=1, exposure=10, brightness=300, snapshot_type=SnapshotType.CameraRaw, snapshot_location=SnapshotLocation.Prober):
        """
        Tells the Prober to save an image to 'snap_path'.
        snap_path must be a valid path on the Prober's PC.
        NOTE: SnapshotLocation.Local should be a valid
        method for saving directly to the local machine, 
        but it is currently unreliable. snapshot_type
        can be changed to add filters.
        """
        # Ensure path uses forward slashes (works best for Sentio remote commands)
        clean_path = snap_path.replace("\\", "/")

        if SIMULATION_MODE:
            print(f"[SIM] Snap Image -> {clean_path}")
            return
        if brightness:
            self.prober.vision.switch_light(CameraMountPoint.Scope, True)
            self.prober.vision.camera.set_light(CameraMountPoint.Scope, brightness)
        if exposure:
            self.prober.vision.camera.set_exposure(CameraMountPoint.Scope, exposure)
        if gain:
            self.prober.vision.camera.set_gain(CameraMountPoint.Scope, gain)
        self.prober.vision.snap_image(snap_path, 
            what=snapshot_type, where=snapshot_location)
        print(f"[VISION] Saved: {clean_path}")

    def get_probe_xy(self):

        x, y = self.prober.get_scope_xy()

        return x, y

    def get_probe_z(self):

        z = self.prober.get_scope_z()
        z = (z - Z_OFFSET) / Z_SLOPE

        return z