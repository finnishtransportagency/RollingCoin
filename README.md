# Rolling Coin
Rolling Coin is a bathymetric surface manipulation method develped to help automated depth contour generation. Currently there are two different versions of the method:


### Rolling Coin V1:
This version of the method takes depth model as input and exports an abstraction of the original depth model surface containing only the depth contour limits. Optionally also creates raw (vector-) contours. Raw contours will most likely need post-processing in order to get cartographically satisfying results (not included in the script).


### Rolling Coin V2:
This version creates a manipulated 2.5 dimensional depth model surface. The method is navigationally safe – exported surface is never deeper than the original surface. The modified surface can be used to automatically create vector contours or user can choose to continue to apply other surface smoothing methods in order to be able to create even better quality contours from the surface.


### Notes:
- Written in Python (Python 2)
- Provided scripts are simple proof-of-concept scripts, not fully developed production line tools
- There is no user interface and the scripts are not guaranteed to work
- User should read the script sources carefully to get familiar with the method and the source code lines that one needs to modify before use


### Dependencies:
1. GDAL
   - See www.gdal.org
   - File I/O
   - Contouring (optional, V1 only)
2. NumPy
   - See www.numpy.org
   - Provides 2D arrays to store grid data
3. (Optional, in V1 only:) GeoPandas
   - See http://geopandas.org


### Basic functionality (V2):
- *Coin* is a neighborhood matrix and can be of any shape and size
- Script assumes input data to have *negative depths* below vertical reference level
- In order to maintain the desired *Coin* shape it is recommended to have the input data in projected CRS and to use identical spatial resolution in both (x-, y-) directions

Algorithm in a nutshell:
1. Open input depth model, get original *No Data* value, *georeferencing parameters* and save depth model data to a 2D NumPy array
2. Apply a 3 * 3 cell focal maximum filter to expand shoals by one cell to all directions
3. Create another 2D NumPy array (*"export array"*) to hold manipulated surface values and initialize all cell values to 10000 (meters)
4. Create *Coin* (a 2D neighborhood matrix of boolean values)
5. For each cell in original data array:
    1. Find shoalest depth (*Zmax*) of neighborhood (*Coin*)
    2. Write *Zmax* to whole coin area in *export array*. *Note that export array values can only get deeper. The Coin is trying to get maximum depth.*
6. Restore original *No Data* values to export array
7. Export modified surface to a file


### ReadMe is still work in progress.
