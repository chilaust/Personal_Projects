# This is the storm simulation

import sys
import os
import json
import numpy as np
from landlab.components import OverlandFlow
from landlab.io import esri_ascii


def storm_simulation_from_config(folder):
    # Read configuration
    config_path = os.path.join(folder, "storm_config.json")
    with open(config_path) as f:
        cfg = json.load(f)

    dem_ascii = os.path.join(folder, cfg["dem_ascii"])
    storm_center_x = float(cfg["storm_center_x"])
    storm_center_y = float(cfg["storm_center_y"])
    storm_radius_m = float(cfg["storm_radius_m"])
    storm_severity = int(cfg["storm_severity"])
    storm_duration_hours = float(cfg["storm_duration_hours"])

    base_intensity_m_per_hr_for_severity_1 = 0.01

    # Load DEM as Landlab grid; field is named "topographic_elevation"
    with open(dem_ascii) as fp:
        mg = esri_ascii.load(fp, name="topographic_elevation", at="node")

    z_old = mg.at_node["topographic_elevation"]
    print("DEM stats:", float(z_old.min()), float(z_old.max()))
    print("Number of nodes:", mg.number_of_nodes)

    mg.add_field("topographic__elevation", z_old.copy(), at="node")


    # Use the correctly named field
    z = mg.at_node["topographic__elevation"]

    # Boundary conditions
    mg.status_at_node[mg.nodes_at_right_edge] = mg.BC_NODE_IS_FIXED_VALUE
    mg.status_at_node[np.isclose(z, -9999.0)] = mg.BC_NODE_IS_CLOSED

    # Rainfall field
    if "rainfall__flux" not in mg.at_node:
        mg.add_zeros("rainfall__flux", at="node")
    else:
        mg.at_node["rainfall__flux"].fill(0.0)

    x = mg.node_x
    y = mg.node_y
    r2 = (x - storm_center_x) ** 2 + (y - storm_center_y) ** 2
    mask = r2 <= storm_radius_m ** 2

    storm_intensity_m_per_hr = (
        base_intensity_m_per_hr_for_severity_1 * storm_severity
    )
    mg.at_node["rainfall__flux"][mask] = storm_intensity_m_per_hr

    # Ensure rainfall directory exists
    rainfall_dir = os.path.join(folder, "rainfall")
    os.makedirs(rainfall_dir, exist_ok=True)

    rainfall_asc = os.path.join(rainfall_dir, "rainfall.asc")
    with open(rainfall_asc, "w") as fp:
        esri_ascii.dump(mg, fp, name="rainfall__flux", at="node")

    # Reload rainfall (keeps pattern consistent)
    with open(rainfall_asc) as fp:
        esri_ascii.load(fp, name="rainfall__flux", at="node", out=mg)

    # Surface water depth
    if "surface_water__depth" not in mg.at_node:
        mg.add_zeros("surface_water__depth", at="node")
    mg.at_node["surface_water__depth"].fill(1.0e-12)

    of = OverlandFlow(mg, steep_slopes=True)

    total_mins_to_plot = 120.0
    min_tstep_val = 1.0

    storm_elapsed_time = 0.0
    total_elapsed_time = 0.0

    peak_depth = mg.at_node["surface_water__depth"].copy()
    storm_duration_s = storm_duration_hours * 3600.0

    while total_elapsed_time < total_mins_to_plot * 60.0:
        dt = of.calc_time_step()
        remaining_total_time = total_mins_to_plot * 60.0 - total_elapsed_time

        if storm_elapsed_time < storm_duration_s:
            remaining_storm_time = storm_duration_s - storm_elapsed_time
            dt = min(dt, remaining_total_time, remaining_storm_time, min_tstep_val)
        else:
            dt = min(dt, remaining_total_time, min_tstep_val)

        of.run_one_step(dt=dt)
        total_elapsed_time += dt
        storm_elapsed_time += dt

        # Add rainfall during the storm only
        if storm_elapsed_time < storm_duration_s:
            mg.at_node["surface_water__depth"] += (
                mg.at_node["rainfall__flux"] * dt / 3600.0
            )

        peak_depth = np.maximum(peak_depth, mg.at_node["surface_water__depth"])

    # Save outputs in the same folder
    mg.at_node["peak_flood__depth"] = peak_depth
    peak_asc = os.path.join(folder, "peak_flood_depth.asc")
    with open(peak_asc, "w") as fp:
        esri_ascii.dump(mg, fp, name="peak_flood__depth", at="node")

    csv_path = os.path.join(folder, "peak_flood_points.csv")
    with open(csv_path, "w") as f:
        f.write("x,y,peak_depth\n")
        for node_id in range(mg.number_of_nodes):
            depth_val = float(peak_depth[node_id])
            if depth_val <= 0.0:
                continue
            f.write(f"{mg.node_x[node_id]},{mg.node_y[node_id]},{depth_val}\n")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python storm_engine_mac.py /path/to/folder")
    folder = sys.argv[1]
    storm_simulation_from_config(folder)


if __name__ == "__main__":
    main()
