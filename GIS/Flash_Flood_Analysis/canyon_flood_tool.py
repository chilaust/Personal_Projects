import landlab
import numpy as np
import os
import arcpy

from landlab.components import OverlandFlow
from landlab.io import esri_ascii


def raster_clip(input_raster, output_clipped_raster, extent):
    """Clip large raster to only needed space to optimize simulation.

    Parameters:
    input_raster (filepath): the large original raster (ie all of southern Utah)
    output_clipped_raster (filepath): the clipped small raster matching the input highlighted area
    extent (str): user-drawn extent "xmin ymin xmax ymax"
    """
    workspace = arcpy.env.scratchGDB

    arcpy.management.Clip(
        input_raster,
        extent,
        output_clipped_raster,
        "#",
        "NoData",
        "NONE",
        "MAINTAIN_EXTENT"
    )


def storm_simulation(
    output_clipped_raster,
    storm_center_x,
    storm_center_y,
    storm_radius_m,
    storm_severity,
    storm_duration_hours,
    output_folder,
):
    base_intensity_m_per_hr_for_severity_1 = 0.01

    with open(output_clipped_raster) as fp:
        mg = esri_ascii.load(fp, name="topographic_elevation", at="node")

    z = mg.at_node["topographic_elevation"]

    # Boundary conditions
    mg.status_at_node[mg.nodes_at_right_edge] = mg.BC_NODE_IS_FIXED_VALUE
    mg.status_at_node[np.isclose(z, -9999.0)] = mg.BC_NODE_IS_CLOSED

    # =========================
    # BUILD CUSTOM STORM FIELD
    # =========================

    # Add rainfall__flux field (m/h), initialize to 0 everywhere
    if "rainfall__flux" not in mg.at_node:
        mg.add_zeros("rainfall__flux", at="node")
    else:
        mg.at_node["rainfall__flux"].fill(0.0)

    x = mg.node_x
    y = mg.node_y

    # Circular storm mask around storm center
    r2 = (x - storm_center_x) ** 2 + (y - storm_center_y) ** 2
    mask = r2 <= storm_radius_m ** 2

    # Compute intensity from severity (linear scaling)
    storm_intensity_m_per_hr = (
        base_intensity_m_per_hr_for_severity_1 * storm_severity
    )

    # Assign intensity inside the storm, 0 outside
    mg.at_node["rainfall__flux"][mask] = storm_intensity_m_per_hr

    # Use output_folder for rainfall directory
    rainfall_dir = os.path.join(output_folder, "rainfall")
    if not os.path.exists(rainfall_dir):
        os.makedirs(rainfall_dir)

    rainfall_asc = os.path.join(rainfall_dir, "rainfall.asc")
    with open(rainfall_asc, "w") as fp:
        esri_ascii.dump(mg, fp, name="rainfall__flux", at="node")

    # =========================
    # RUN OVERLANDFLOW: STORM + RECESSION (time-varying rainfall)
    # =========================

    # Reset rainfall__flux from file
    with open(rainfall_asc) as fp:
        esri_ascii.load(fp, name="rainfall__flux", at="node", out=mg)

    # ⚡ Fix surface_water__depth initialization
    if "surface_water__depth" not in mg.at_node:
        mg.add_zeros("surface_water__depth", at="node")
    mg.at_node["surface_water__depth"].fill(1.0e-12)

    of = OverlandFlow(mg, steep_slopes=True)

    total_mins_to_plot = 120.0
    plot_interval_mins = 3.0
    min_tstep_val = 1.0

    storm_elapsed_time = 0.0
    total_elapsed_time = 0.0
    last_storm_loop_tracker = 0.0

    # Track peak depth at each node
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

        # Update peak depth
        peak_depth = np.maximum(peak_depth, mg.at_node["surface_water__depth"])

        storm_loop_tracker = total_elapsed_time % (plot_interval_mins * 60.0)
        last_storm_loop_tracker = storm_loop_tracker

    # Write peak flood depth to ASCII grid
    mg.at_node["peak_flood__depth"] = peak_depth
    peak_asc = os.path.join(output_folder, "peak_flood_depth.asc")
    with open(peak_asc, "w") as fp:
        esri_ascii.dump(mg, fp, name="peak_flood__depth", at="node")

    # Export peak flood depth as point shapefile for ArcGIS Pro
    shp_path = os.path.join(output_folder, "peak_flood_points.shp")

    # Create shapefile
    spatial_ref = arcpy.Describe(output_clipped_raster).spatialReference
    arcpy.management.CreateFeatureclass(
        os.path.dirname(shp_path),
        os.path.basename(shp_path),
        "POINT",
        spatial_reference=spatial_ref,
    )

    # Add field for peak depth
    arcpy.management.AddField(shp_path, "peak_depth", "DOUBLE")

    # Insert points with peak depth attribute
    with arcpy.da.InsertCursor(shp_path, ["SHAPE@XY", "peak_depth"]) as cursor:
        for node_id in range(mg.number_of_nodes):
            depth_val = float(peak_depth[node_id])
            # Optionally skip zero-depth cells (unflooded)
            if depth_val <= 0.0:
                continue
            cursor.insertRow(
                [
                    (float(mg.node_x[node_id]), float(mg.node_y[node_id])),
                    depth_val,
                ]
            )




# Parameters from Arcpy Tool
output_folder = arcpy.GetParameterAsText(0)                     # Output folder for outputs
extent = arcpy.GetParameterAsText(1)                            # User-drawn extent "xmin ymin xmax ymax"
storm_center = arcpy.GetParameter(2)                            # User-selected point as a Feature Set
storm_radius_m = float(arcpy.GetParameterAsText(3))             # Size of storm (meters)
storm_duration_minutes = float(arcpy.GetParameterAsText(4))     # Duration of storm (minutes)
storm_severity = int(arcpy.GetParameterAsText(5))               # Severity of storm (1 light - 10 severe)

# Standard Parameters
input_raster = r"C:/Users/chilaust/Documents/GIS/GisPro/Personal_Practice/Southern_Utah_Combined.asc"
output_clipped_raster = os.path.join(output_folder, "Clipped_S_UT.asc")

# Clip the raster
raster_clip(input_raster, output_clipped_raster, extent)

# Ensure spatial reference match
sr_raster = arcpy.Describe(output_clipped_raster).spatialReference

# Get storm center as a point projected into the raster's CRS
with arcpy.da.SearchCursor(storm_center, ["SHAPE@"]) as cur:
    for geom in cur:
        geom_on_raster = geom[0].projectAs(sr_raster)
        pt = geom_on_raster.firstPoint
        storm_x, storm_y = pt.X, pt.Y
        break

# Convert storm duration to hours
storm_duration = storm_duration_minutes / 60.0

# Run simulation 
storm_simulation(
    output_clipped_raster,
    storm_x,
    storm_y,
    storm_radius_m,
    storm_severity,
    storm_duration,
    output_folder,
)