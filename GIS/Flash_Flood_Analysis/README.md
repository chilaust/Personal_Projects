# Flash Flood Analysis Tool

## Introduction:
This tool was built specifically for Southern Utah to predict if flash floods would be likely in desert canyons. I am an avid canyoneer and one of the highest risks that is often completely avoidable is flash floods. This tool was built to model the flood path of a flash flood and record the deepest water depth.

## Included Files
1. ### [canyon_flood_tool.py](https://github.com/chilaust/Personal_Projects/blob/c1f24d312f85513c527bb3ecaa9280826a217201/GIS/Flash_Flood_Analysis/canyon_flood_tool.py)
    1. This is the entire file that should in theory run when all packages are downloaded and you upload the tool through ArcPro. 
    2. Unfortunately due to some hardware constraints this approach ended up not working for me, but I learned a valuable lesson to always test along the way and iterate. I could not get ArcPro to work with landlab's overland flow library. This is because they are built on two different versions of python and do not communicate well. There is a work around detailed below with the other files.
2. ### [export_storm_inputs.py](https://github.com/chilaust/Personal_Projects/blob/c1f24d312f85513c527bb3ecaa9280826a217201/GIS/Flash_Flood_Analysis/export_storm_inputs.py)
    1. This is the tool part of the entire project. This allows you to build a tool in ArcPro.
    2. Inputs: 
        1. output folder (file path)
        2. area of interest (an extent)
        3. storm center
        4. storm radius in meters
        5. storm duration in minutes
        6. storm severity from 1 - 10
    3. Outputs: 
        1. JSON file (see commented code for what is included)
    
3. ### [storm_engine_mac.py](https://github.com/chilaust/Personal_Projects/blob/c1f24d312f85513c527bb3ecaa9280826a217201/GIS/Flash_Flood_Analysis/storm_engine_mac.py)
    1. This takes in the JSON file and runs the actual simulation. Note that I could only get it to work on my mac but it should run anywhere if you have the correct libraries installed. 
    2. Inputs:
        1. JSON file (see commented code for what is included)
    3. Outputs:
        1.  A raster file with all of the flooded areas highlighted by depth of water at peak flood period.

4. ### [import_storm_outputs.py](https://github.com/chilaust/Personal_Projects/blob/c1f24d312f85513c527bb3ecaa9280826a217201/GIS/Flash_Flood_Analysis/import_storm_outputs.py)
    1. This tool is another tool to import the raster file back into ArcPro and overlay ontop of the base map. Honestly this is redundant and I ended up not using it. It is much easier to just import the raster yourself.
    

## [Working Example](https://github.com/chilaust/Personal_Projects/blob/c1f24d312f85513c527bb3ecaa9280826a217201/GIS/Flash_Flood_Analysis/Flooding_Project_Final.pptx)
This is an area in Zion National Park called Pine Creek. It is a tight slot canyon. You can see the inputs on the tool and the ultimate output at the end. 

*Note: I think that the original DEM was not granular enough and so when the canyon was really tight in the DEM I worry that it made an effective 'dam' to the water resulting in the odd flow pattern at the end.*

### Tool Inputs
![Tool Inputs](https://github.com/chilaust/Personal_Projects/blob/3297c7b86107cc26d33fe33acea93b62c36b87dd/GIS/Flash_Flood_Analysis/Flash_flood_tool.png?raw=true)

### Final Predicted Flood Path
![Flash Flood Path](https://github.com/chilaust/Personal_Projects/blob/ca8da23b9ba0677073a0e1cdcdb1dfc1bfe85b9c/GIS/Flash_Flood_Analysis/Flash_flood_output.png?raw=true)
