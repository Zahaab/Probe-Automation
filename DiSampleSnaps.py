from Classes import ProberController
from Config import PROBER_IP
from MeasurementF import RunImagingSequence
from sentio_prober_control.Sentio.Enumerations import SnapshotType, SnapshotLocation, CameraMountPoint
import time

# ================================================================================
# IMAGING Main Function - Separate from Main.py for separate execution and testing
# ================================================================================

def get_snap_data():
    #Code taht defines list of coordinates to snap at, and device names for that position.
    return snap_data_list

def RunImagingSequence(prober_controller, snap_data_list):
    # In one of the old logs, someone said to use sleep with vision commands to avoid "overloading" the prober. 
    # This is a bit vague, but I added small sleeps between moves and snaps just in case.
    print(f"Starting Imaging Sequence: {len(snap_data_list)} sites.")
    print(f"Target Folder (Prober PC): {IMAGING_OUTPUT_DIR}")

    pc = ProberController(PROBER_IP)
    pc.connect()
    for snap_data in snap_data_list:
        try:
            x, y, device_name = snap_data
            print(f"\nMoving to {device_name} at ({x}, {y})...")
            pc.move_chuck_xy(x, y)
            time.sleep(0.5)

            print(f"Snapping at brightness 120...")
            pc.snap_image_remote(f'{device_name}/brightness_120.jpg', brightness=120,
                what=SnapshotType.CameraRaw, where=SnapshotLocation.Prober)
            time.sleep(0.5)

            print(f"Snapping at brightness 300...")
            pc.snap_image_remote(f'{device_name}/brightness_300.jpg', brightness=300,
                what=SnapshotType.CameraRaw, where=SnapshotLocation.Prober)
            time.sleep(0.5)

            with open(f'Imaging/{device_name}.txt', 'w') as f:
                print(pc.prober.vision.camera.get_calib(CameraMountPoint.Scope), file=f)
                print(pc.prober.vision.camera.get_exposure(CameraMountPoint.Scope), file=f)
                # print(pc.prober.vision.camera.get_focus_value(CameraMountPoint.Scope, ))
                print(pc.prober.vision.camera.get_gain(CameraMountPoint.Scope), file=f)
                print(pc.prober.vision.camera.get_image_size(CameraMountPoint.Scope), file=f)
                print(pc.prober.vision.camera.get_light(CameraMountPoint.Scope), file=f)
        except Exception:
            pc.move_chuck_xy(x, y)
            time.sleep(0.5)
            raise

    print("Sequence Complete.")



def main_imaging():
    # Initialize
    pc = ProberController(PROBER_IP)
    pc.connect()
    
    # Run
    try:
        get_snap_data_list = get_snap_data()
        RunImagingSequence(pc, get_snap_data_list)
    except KeyboardInterrupt:
        print("Sequence stopped by user.")

main_imaging()