import time
from Config import (MAX_STANDOFF_MM, MIN_STANDOFF_MM, SIMULATION_MODE, Z_OFFSET, Z_SLOPE, PROBER_IP,
                    AWAY_XCOORD, AWAY_YCOORD, RAD_XCOORD, RAD_YCOORD)
from Classes import ProberController

def test_probe_control(pc_obj):

    sites = ["AWAY", "RAD", "AWAY", "RAD", "AWAY"]
    site_coords = [[AWAY_XCOORD, AWAY_YCOORD], [RAD_XCOORD, RAD_YCOORD]]

    print("\n------------------- Starting Probe Control Test -------------------- ")

    for site in sites:
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
        pc_obj.move_z_mm(height)
        z = pc_obj.get_probe_z()
        if z != height:
            print(f"Height mismatch - moved to {z:.3f} instead of {height:.3f}")
        time.sleep(5)

    pc_obj.move_to_site("AWAY")
    pc_obj.move_z_mm(1.5)

    print("\n------------------- Tests Complete, No Issues Found -------------------- ")

try:
    pc = ProberController(PROBER_IP)
    pc.connect()
    pc._build_site_map()
    print(f"Prober IP: {pc.ip}")
    print(f"Site Map: {pc.site_map}")

    test_probe_control(pc)

except KeyboardInterrupt:
    print("Interrupted by user, program quit.")

