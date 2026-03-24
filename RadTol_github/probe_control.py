"""
Modified from Zahaab's code for use in RadTol experiment

Check / Notes :
- Check true minimum of scope compared to config file
- In my language, Z_SLOPE = multiplication factor & Z_OFFSET = theoretical 0mm distance
  (done this way to input relative measurements since commands are given relative to absolute 0 which doesn't actually exist)
- Distance mm is human coord and um is internal Probe Station coord

On startup:
- Check IP address of Probe Station is correct
- Load sample as normal - Bias top plate
- Make sure chuck height is maximum
- Make note of RAD and AWAY sites and add to config file
- Test everything moves as expected

To add
- Could have this as a child of ProberController class potentially ?
"""

import time
from Config import (MAX_STANDOFF_MM, MIN_STANDOFF_MM, SIMULATION_MODE, Z_OFFSET, Z_SLOPE, PROBER_IP,
                    AWAY_XCOORD, AWAY_YCOORD, RAD_XCOORD, RAD_YCOORD)
from Classes import ProberController

def test_probe_control(pc_obj):

    sites = ["AWAY", "RAD", "AWAY", "RAD", "AWAY"]
    site_coords = [[AWAY_XCOORD, AWAY_YCOORD], [RAD_XCOORD, RAD_YCOORD]]

    print("\n------------------- Starting Probe Control Test -------------------- ")

    for site in enumerate(sites):
        if site == "AWAY":
            site_coord = site_coords[0]
        if site == "RAD":
            site_coord = site_coords[1]
        pc_obj.move_to_site(site)
        x, y = pc_obj.get_probe_xy()
        if (x != site_coord[0]) & (y != site_coord[1]):
            print(f"Coordinate mismatch in moving to site '{site}' - moved to ({x:.3f}, {y:.3f}) instead of "
                  f"({site_coord[0]:.3f}, {site_coord[1]:.3f})")
        time.sleep(5)

    heights = [1.5, 4.5, 7.5, 10.5, 13.5]
    for height in heights:
        pc.move_z_mm(height)
        z = pc.get_probe_z()
        if z != height:
            print(f"Height mismatch - moved to {z:.3f} instead of {height:.3f}")
        time.sleep(5)

    pc.move_to_site("AWAY")
    pc.move_z_mm(1.5)

    print("\n------------------- Tests Complete, No Issues Found -------------------- ")

def standoff_measurement(pc_obj, height_set):

    if height_set == 1:
        heights = [1.5, 3, 4.5]
        end_height = 4.5
    elif height_set == 2:
        heights = [6, 7.5, 9]
        end_height = 9
    elif height_set == 3:
        heights = [10.5, 12, 13.5]
        end_height = 1.5
    else:
        heights = []
        end_height = MIN_STANDOFF_MM
        print("Invalid input, please enter 1 (1.5 mm, 3 mm, 4.5 mm), 2 (6 mm, 7.5 mm, 9 mm) or 3 (10 mm, 12.5 mm, 13.5 mm)")

    print("\n------------------- Starting Standoff Variation Script -------------------- ")
    print("(Check field is set to +/- 1V/um (based on thickness in Dektak))")

    for height in heights:
        pc_obj.move_to_site("AWAY")
        time.sleep(20)
        pc_obj.move_z_mm(height)
        time.sleep(24)
        pc_obj.move_to_site("RAD")
        time.sleep(44)

    pc_obj.move_to_site("AWAY")
    time.sleep(44)
    pc_obj.move_z_mm(end_height)

    print("\n------------------- Standoff Variation Script Complete -------------------- ")

def dynamics_measurement(pc_obj, standoff=1.5):

    pc.move_z_mm(standoff)
    pc_obj.move_to_site("AWAY")

    print("\n------------------- Starting Time Dynamics Script -------------------- ")

    time.sleep(29)
    pc.move_to_site("RAD")
    time.sleep(29)
    pc_obj.move_to_site("AWAY")
    time.sleep(29)
    pc.move_to_site("RAD")
    time.sleep(29)
    pc_obj.move_to_site("AWAY")

    print("\n------------------- Time Dynamics Complete -------------------- ")


try:
    pc = ProberController(PROBER_IP)
    pc.connect()
    # pc._build_site_map()
    print(f"Prober IP: {pc.ip}")
    print(f"Site Map: {pc.site_map}")

    # Ask for user input on what to run and keep running until quit

    while True:

        measurement_type = input("\nMeasurement type : (standoff / dynamics) (q to quit)")
        measurement_type = measurement_type.lower()

        # Quit : q
        # Standoff : standoff 1, standoff 2, standoff 3
        # Dynamic : dynamic, dynamic 1.5, dynamic 2.0, etc...

        if measurement_type == "q":
            print("Program Quit")
            break
        elif "standoff" in measurement_type:
            standoff_type = measurement_type.split(' ')[1]
            standoff_measurement(pc, standoff_type)
        elif "dynamics" in measurement_type:
            try:
                dynamics_standoff = measurement_type.split(' ')[1]
            except IndexError:
                dynamics_standoff = 1.5
            dynamics_measurement(pc, dynamics_standoff)
        else:
            print("Invalid input")
except KeyboardInterrupt:
    print("Interrupted by user, program quit.")
