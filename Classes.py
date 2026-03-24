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
        self.connected = False
        self.smu_map = {"SMU1": 1, "SMU2": 2, "SMU3": 3, "SMU4": 4}

    def connect(self):
        if SIMULATION_MODE:
            self.connected = True
            print(f"[KEITHLEY] Simulated Connection")
            return
        try:
            rm = pyvisa.ResourceManager()
            self.inst = rm.open_resource(self.resource_str)
            self.inst.write('UL')
            self.inst.write('DR 1')
            self.inst.timeout = 60000
            self.connected = True
            print(f"[KEITHLEY] Connected")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Keithley: {e}")

    def configure_cviv_routing(self, smu_in_str, port_out_int):
        smu_id = self.smu_map[smu_in_str]
        if SIMULATION_MODE:
            print(f"[KEITHLEY] CVIV: Routing {smu_in_str} -> Port {port_out_int}")
            return
        cmd = f'EX "cviv_connect({smu_id}, {port_out_int})"'
        try:
            self.inst.write(cmd)
            time.sleep(0.1)
        except Exception as e:
            print(f"[KEITHLEY] Error configuring CVIV: {e}")

    def _get_compliance(self, voltage_limit):
        if abs(voltage_limit) > 20: return 10e-3
        return 100e-3

    def setup_measurement_mode(self, smu_name):
        """Enable channel and set to measure Current/Voltage."""
        if SIMULATION_MODE: return
        smu_id = self.smu_map[smu_name]
        self.inst.write(f'CN {smu_id}')
        # Set to Measure Current (standard mode)
        # We can query Voltage later using MV
        self.inst.write(f'SM {smu_id}, I') 

    def measure_spot(self, smu_name):
        """Returns (Voltage, Current) for a single SMU."""
        smu_id = self.smu_map[smu_name]
        if SIMULATION_MODE:
            return (5.0, 1.2e-6) # Fake data

        # MV = Measure Voltage, MI = Measure Current
        # Note: 'ME' measures the parameter defined by 'SM' (usually Current)
        # To get both, we specifically query both.
        try:
            v_val = float(self.inst.query(f'MV {smu_id}'))
            i_val = float(self.inst.query(f'MI {smu_id}'))
            return (v_val, i_val)
        except:
            return (0.0, 0.0)

    def run_software_sweep(self, smu_sig, smu_gnd, start_v, stop_v, step_v):
        """
        Iterates voltage in Python to ensure clean data capture from BOTH SMUs.
        """
        smu_sig_id = self.smu_map[smu_sig]
        smu_gnd_id = self.smu_map[smu_gnd]
        
        # Calculate voltage list
        # We use numpy or simple loop to handle float steps accurately
        steps = int(abs(stop_v - start_v) / abs(step_v)) + 1
        voltages = np.linspace(start_v, stop_v, steps)

        compliance = self._get_compliance(max(abs(start_v), abs(stop_v)))
        
        print(f"[KEITHLEY] Software Sweep {smu_sig} ({start_v}V to {stop_v}V)")
        
        results = [] # Stores [V_Set, V1, I1, V2, I2]

        if SIMULATION_MODE:
            time.sleep(0.5)
            # Fake Data: [V_Set, V_Sig, I_Sig, V_Gnd, I_Gnd]
            return [[v, v, v*1e-6, 0, -v*1e-6] for v in voltages]

        # 1. Enable Both
        self.inst.write(f'CN {smu_sig_id}')
        self.inst.write(f'CN {smu_gnd_id}')
        
        # 2. Bias Ground to 0V
        self.inst.write(f'DV {smu_gnd_id}, 0, 0, 0.1')

        # 3. Loop
        for v in voltages:
            # Apply Voltage to Signal SMU
            self.inst.write(f'DV {smu_sig_id}, 0, {v}, {compliance}')
            
            # Small delay for settling (software overhead might be enough, but added for safety)
            # time.sleep(0.01) 
            
            # Measure Both
            # We measure Signal (V, I) and Ground (V, I)
            v1, i1 = self.measure_spot(smu_sig)
            v2, i2 = self.measure_spot(smu_gnd)
            
            results.append([v, v1, i1, v2, i2])

        # 4. Turn off (Bias 0)
        self.inst.write(f'DV {smu_sig_id}, 0, 0, 0.1')
        
        return results

    def start_dynamic_sampling(self, smu_sig, smu_gnd, voltage, stop_event, data_container):
        smu_sig_id = self.smu_map[smu_sig]
        smu_gnd_id = self.smu_map[smu_gnd]
        compliance = self._get_compliance(voltage)
        
        if SIMULATION_MODE:
            start_time = time.time()
            while not stop_event.is_set():
                elapsed = time.time() - start_time
                # Fake: Time, V1, I1, V2, I2
                data_container.append([elapsed, voltage, 1e-6, 0, -1e-6])
                time.sleep(0.1)
            return

        try:
            # Enable Both
            self.inst.write(f'CN {smu_sig_id}')
            self.inst.write(f'CN {smu_gnd_id}')
            
            # Force Voltage
            self.inst.write(f'DV {smu_gnd_id}, 0, 0, 0.1') # Ground
            self.inst.write(f'DV {smu_sig_id}, 0, {voltage}, {compliance}') # Signal
            
            start_time = time.time()
            
            while not stop_event.is_set():
                # Measure Sequence
                v1, i1 = self.measure_spot(smu_sig)
                v2, i2 = self.measure_spot(smu_gnd)
                
                elapsed = time.time() - start_time
                
                # Store: Time, V1, I1, V2, I2
                data_container.append([elapsed, v1, i1, v2, i2])
                
                # Sampling rate control (adjust as needed)
                time.sleep(0.05)
                
        except Exception as e:
            print(f"Error in measurement thread: {e}")
        finally:
            self.inst.write(f'DV {smu_sig_id}, 0, 0, 0.1')
            self.inst.write(f'CL {smu_sig_id}')
            self.inst.write(f'CL {smu_gnd_id}')

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