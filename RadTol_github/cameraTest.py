from Classes import ProberController
from sentio_prober_control.Sentio.ProberSentio import SentioProber
from sentio_prober_control.Sentio.Enumerations import XyReference, ZReference, SnapshotType, SnapshotLocation, CameraMountPoint
# import sentio_prober_control.Sentio.CommandGroups.VisionCommandGroup as vcg
# import sentio_prober_control.Sentio.CommandGroups.VisionCameraCommandGroup as vcg_camera
from Config import PROBER_IP
import time

# Where is the camera mounted ?

prober_class = ProberController(PROBER_IP)
prober_class.connect()

# print(CameraMountPoint.__doc__)
# print(prober.vision.has_camera(CameraMountPoint.Scope))
# print(prober.vision.has_camera(CameraMountPoint.Scope2))
# print(prober.vision.has_camera(CameraMountPoint.Chuck))
# # print(prober.vision.has_camera(CameraMountPoint.Chuck2))
# print(prober.vision.has_camera(CameraMountPoint.OffAxis))
# # print(prober.vision.has_camera(CameraMountPoint.Angled))
# # print(prober.vision.has_camera(CameraMountPoint.BottomScope))
# print(prober.vision.has_camera(CameraMountPoint.Vce))
# print(prober.vision.has_camera(CameraMountPoint.Vce))

# print(prober.vision.camera)

# prober.vision.auto_focus()

# zoom_current = prober.vision.get_lens_zoom_level()
# print(zoom_current)
# zoom_desired = 1
# prober.vision.set_lens_zoom_level(zoom_desired)
# zoom_current = prober.vision.get_lens_zoom_level()
# print(zoom_current)

# print()

# light_status = prober.vision.get_light_status()
# print(light_status)
# prober.vision.switch_all_lights(True)
# light_status = prober.vision.get_light_status()
# print(light_status)
# prober.vision.switch_all_lights(False)
# light_status = prober.vision.get_light_status()
# print(light_status)

# print()

# camera = prober.vision.has_camera()
# print(camera)

# print()

prober = prober_class.prober

prober.vision.auto_focus()

print(prober.get_project())

prober.vision.switch_light(CameraMountPoint.Scope, True)

prober.vision.snap_image('DG033_test_1.jpg', 
	what=SnapshotType.CameraRaw, where=SnapshotLocation.Prober)

# print(prober.vision.camera.get_calib(CameraMountPoint.Scope))
# print(prober.vision.camera.get_exposure(CameraMountPoint.Scope))
# # print(prober.vision.camera.get_focus_value(CameraMountPoint.Scope, ))
# print(prober.vision.camera.get_gain(CameraMountPoint.Scope))
# print(prober.vision.camera.get_image_size(CameraMountPoint.Scope))
# print(prober.vision.camera.get_light(CameraMountPoint.Scope))

# print(prober.vision.set_lens_zoom_level(10))

x, y = prober_class.get_chuck_xy()
print(x)
print(y)

prober_class.move_chuck_xy(x-4000, y)
time.sleep(0.1)

prober.vision.snap_image('DG033_test_2.jpg', 
	what=SnapshotType.CameraRaw, where=SnapshotLocation.Prober)

# prober = ProberController(PROBER_IP)
# prober.connect()
# # prober.auto_focus()
# prober.snap_image_remote('DG033_test.jpg')

# Pixel size : 2560 x 2560
# Image size : 4000um x 4000um
