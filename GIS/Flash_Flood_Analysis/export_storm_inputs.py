# Tool
import os
import json
import arcpy


def raster_clip(input_raster, output_clipped_raster, extent):
    arcpy.management.Clip(
        in_raster=input_raster,
        rectangle=extent,            # "xmin ymin xmax ymax"
        out_raster=output_clipped_raster,
        in_template_dataset="#",
        nodata_value="NoData",
        clipping_geometry="NONE",
        maintain_clipping_extent="MAINTAIN_EXTENT",
    )


def main():
    # Tool parameters
    output_folder = arcpy.GetParameterAsText(0)
    extent = arcpy.GetParameterAsText(1)          # "xmin ymin xmax ymax"
    storm_center = arcpy.GetParameter(2)          # Feature Set
    storm_radius_m = float(arcpy.GetParameterAsText(3))
    storm_duration_minutes = float(arcpy.GetParameterAsText(4))
    storm_severity = int(arcpy.GetParameterAsText(5))

    # Your big DEM on Windows
    input_raster = r"C:/Users/chilaust/Documents/GIS/GisPro/Personal_Practice/Southern_Utah_Combined.tif"

    os.makedirs(output_folder, exist_ok=True)

    clipped_raster = os.path.join(output_folder, "clipped_dem.tif")
    clipped_ascii = os.path.join(output_folder, "clipped_dem.asc")
    config_json = os.path.join(output_folder, "storm_config.json")

    # Clip DEM
    arcpy.AddMessage("Clipping DEM...")
    raster_clip(input_raster, clipped_raster, extent)

    # Convert clipped raster to ASCII grid (for Landlab)
    arcpy.AddMessage("Converting clipped DEM to ASCII...")
    arcpy.conversion.RasterToASCII(clipped_raster, clipped_ascii)

    # Get storm center in raster CRS
    sr_raster = arcpy.Describe(clipped_raster).spatialReference
    with arcpy.da.SearchCursor(storm_center, ["SHAPE@"]) as cur:
        for (geom,) in cur:
            geom_on_raster = geom.projectAs(sr_raster)
            pt = geom_on_raster.firstPoint
            storm_x, storm_y = pt.X, pt.Y
            break

    storm_duration_hours = storm_duration_minutes / 60.0

    # Write config JSON for Landlab on Mac
    cfg = {
        "dem_ascii": "clipped_dem.asc",   # relative path inside the folder
        "storm_center_x": storm_x,
        "storm_center_y": storm_y,
        "storm_radius_m": storm_radius_m,
        "storm_severity": storm_severity,
        "storm_duration_hours": storm_duration_hours,
    }

    with open(config_json, "w") as f:
        json.dump(cfg, f, indent=2)

    arcpy.AddMessage("Inputs written to folder:")
    arcpy.AddMessage(output_folder)
    arcpy.AddMessage("Copy this folder to your Mac and run Landlab there.")


if __name__ == "__main__":
    main()
