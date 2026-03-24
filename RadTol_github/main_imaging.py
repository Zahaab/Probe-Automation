import time
from pathlib import Path
from sentio_prober_control.Sentio.Enumerations import SnapshotType, SnapshotLocation, CameraMountPoint, AutoFocusCmd
from sentio_prober_control.Sentio.ProberSentio import SentioProber

from Config import PROBER_IP
from Classes import ProberController

def take_device_images(pc_obj, x0, y0, device_name, brightness, autofocus=True):

    coords = [2, 6, 10, 14, 18]
    xy_full = []
    for i in coords:
        for j in coords:
            xy_full.append([i*1000, j*1000])

    for x, y in xy_full:
        pc_obj.move_chuck_xy(x0 - x, y0 - y)
        time.sleep(0.5)
        # if autofocus:
        #     pc_obj.prober.vision.auto_focus()
        # calibration = pc_obj.vision.camera.get_calib(CameraMountPoint.Scope)
        pc_obj.prober.vision.snap_image(f'{device_name}/int{brightness}/{x}_{y}.jpg', 
            what=SnapshotType.CameraRaw, where=SnapshotLocation.Prober)

pc = ProberController(PROBER_IP)
pc.connect()
prober = pc.prober

prober.vision.switch_light(CameraMountPoint.Scope, True)
# prober.vision.set_lens_zoom_level(1)
prober.vision.camera.set_light(CameraMountPoint.Scope, 120)
prober.vision.camera.set_exposure(CameraMountPoint.Scope, 10)
prober.vision.camera.set_gain(CameraMountPoint.Scope, 1)

x_abs, y_abs = pc.get_chuck_xy()
# pc.move_chuck_xy(x_abs-10000, y_abs-10000)
# time.sleep(0.5)
# # prober.vision.auto_focus(af_cmd=AutoFocusCmd.Focus)
# pc.move_chuck_xy(x_abs, y_abs)
# time.sleep(0.5)

try:
    device = 'DG039'
    prober.vision.camera.set_light(CameraMountPoint.Scope, 120)
    take_device_images(pc, x_abs, y_abs, device, 120)

    pc.move_chuck_xy(x_abs, y_abs)
    time.sleep(0.5)

    prober.vision.camera.set_light(CameraMountPoint.Scope, 300)
    take_device_images(pc, x_abs, y_abs, device, 300)

    with open(f'Imaging/{device}.txt', 'w') as f:
        print(prober.vision.camera.get_calib(CameraMountPoint.Scope), file=f)
        print(prober.vision.camera.get_exposure(CameraMountPoint.Scope), file=f)
        # print(prober.vision.camera.get_focus_value(CameraMountPoint.Scope, ))
        print(prober.vision.camera.get_gain(CameraMountPoint.Scope), file=f)
        print(prober.vision.camera.get_image_size(CameraMountPoint.Scope), file=f)
        print(prober.vision.camera.get_light(CameraMountPoint.Scope), file=f)

except Exception:
    pc.move_chuck_xy(x_abs, y_abs)
    time.sleep(0.5)
    raise


# coordinate (x, y), calibration, filename
