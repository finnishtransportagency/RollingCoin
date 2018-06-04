# RollingCoin
Rolling Coin is a bathymetric surface manipulation method develped to help automated depth contour generation. Currently there are two different versions of the method:

### Rolling Coin V1:
This version of the method takes depth model as input and exports an abstraction of the original depth model surface that contains only the depth contour limits. Optionally creates also raw (vector-) contours. Raw contours will most likely need post-processing (not included).

### Rolling Coin V2:
This version manipulates the depth model surface in 2.5D. The method is navigationally safe – generalized surface is never deeper than the original surface. The modified surface can be used to automatically create vector contours or user can choose to continue to apply other surface smoothing procedures in order to be able to create even better quality contours from the surface.

### Notes:
- Written in Python (Python2)
- Provided scripts are simple proof-of-concept scripts, not fully developed production line tools.
- There is no user interface and the scripts are not quaranteed to work.
- User should read the script sources carefully to get familiar with the method and the lines that one needs to modify.

### Dependencies:
1. GDAL (see www.gdal.org)
  * File I/O
  * Contouring (optional, V1 only)
2. NumPy (see www.numpy.org)
  * Provides 2D arrays to store grid data
3. (Optional, in V1 only: GeoPandas (see http://geopandas.org))


ReadMe is still work in progress.
