import pyvisa
import time
import threading
import csv
import os
import datetime
import numpy as np
from sentio_prober_control.Sentio.ProberSentio import SentioProber
from sentio_prober_control.Sentio.Enumerations import XyReference, ZReference
from Config import MAX_STANDOFF_MM, MIN_STANDOFF_MM, SIMULATION_MODE, Z_OFFSET, Z_SLOPE, PROBER_IP
from Classes import ProberController

# This is a test file for the probe functions.

# # These just test communication
# prober = SentioProber.create_prober("tcpip", PROBER_IP)
# x, y = prober.get_scope_xy()
# print(f"Current Scope Position: X={x} µm, Y={y} µm")

# z = prober.get_scope_z()
# print(f"Current Z-Axis Position: {z} µm")

# # Now with movment functions you need a ref! That is ScopeXYReference.
# # ScopeXYReference.Zero	Absolute Move. Moves to a specific coordinate on the stage.
# # ScopeXYReference.Relative	Relative Move. Shifts the scope by the given amount from its current location.
# # ScopeXYReference.Home	Home Referenced. Moves to a position relative to the defined "Home" position.
# # FOR CLARITY: When using .Zero it will move directly from its current position to the specified position (5000 µm). It will not go to zero first.
# prober.move_scope_xy(XyReference.Zero, -5000, -5000)



# prober.move_scope_xy(XyReference.Current, 1000, 1000)
# prober.move_scope_xy(XyReference.Current, -2000, -2000)
# prober.move_scope_xy(XyReference.Current, 0, 2000)


# ScopeZReference works the same way but for Z-axis
# prober.move_scope_z(ZReference.Zero, -140000.0)
# print("Scope moved to absolute height of 500 µm")
# prober.move_scope_z(ZReference.Current, -2000)
# print("Scope moved down by 2000 µm")


# --- Test Class functiuons ---
pc = ProberController(PROBER_IP)
pc.connect()
pc._build_site_map()
print(f"Prober IP: {pc.ip}")
print(f"Site Map: {pc.site_map}")

time.sleep(3)
# # Now test movment! DO NOT RUN THIS UNLESS YOU ARE READY FOR THE PROBE TO MOVE. MAKE SURE CONFIG IS CORRECT AND PROBE IS CLEAR OF ANYTHING IT CAN DAMAGE. 
# # ༼ง=ಠ益ಠ=༽ง
# pc.move_to_site("RAD")
# pc.move_to_site("AWAY")
# pc.move_to_site("RAD")
# pc.move_to_site("AWAY")
# pc.move_to_site("RAD")
# pc.move_to_site("AWAY")
pc.move_z_mm(1.5)
pc.move_z_mm(13)
pc.move_z_mm(5.0)
