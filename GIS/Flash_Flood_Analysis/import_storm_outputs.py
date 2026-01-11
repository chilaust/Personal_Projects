# import_storm_outputs.py
import os
import arcpy


def main():
    folder = arcpy.GetParameterAsText(0)  # folder with peak_flood_depth.asc & CSV

    peak_asc = os.path.join(folder, "peak_flood_depth.asc")
    csv_points = os.path.join(folder, "peak_flood_points.csv")

    if not os.path.exists(peak_asc):
        arcpy.AddError(f"Missing {peak_asc}")
        raise SystemExit(1)

    # ASCII to raster
    peak_raster = os.path.join(folder, "peak_flood_depth.tif")
    arcpy.conversion.ASCIIToRaster(
        in_ascii_file=peak_asc,
        out_raster=peak_raster,
        data_type="FLOAT",
    )

    # Add raster to the current map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = aprx.activeMap
    m.addDataFromPath(peak_raster)

    # CSV to point FC (if present)
    if os.path.exists(csv_points):
        event_layer = "peak_flood_points_layer"

        # Use the raster's spatial reference for the XY event layer
        raster_sr = arcpy.Describe(peak_raster).spatialReference

        arcpy.management.MakeXYEventLayer(
            in_table=csv_points,
            in_x_field="x",
            in_y_field="y",
            out_layer=event_layer,
            spatial_reference=raster_sr,
        )

        # Create results.gdb if needed
        gdb = os.path.join(folder, "results.gdb")
        if not arcpy.Exists(gdb):
            arcpy.management.CreateFileGDB(folder, "results.gdb")

        out_fc = os.path.join(gdb, "peak_flood_points")
        arcpy.management.CopyFeatures(event_layer, out_fc)
        m.addDataFromPath(out_fc)
    else:
        arcpy.AddWarning(f"No CSV file found at {csv_points}")


if __name__ == "__main__":
    main()
