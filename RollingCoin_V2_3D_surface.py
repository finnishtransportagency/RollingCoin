# -*- coding: utf-8 -*-
# Python2

# Part of FTA Depth contour production automation tests
# Finnish Transport Agency, Hydrographic Office

# This V2 proof-of-concept script reads in (GeoTIFF-) depth models, creates:
#   1. "Rolling Coin" generalized surface (exported)
#       - Shoal buffering with 3 x 3 cell max filter
#       - Rolls Coin to create a manipulated 2.5D surface for contour creation

# Depends on:
# 1. GDAL (see http://www.gdal.org/)
# 2. NumPy (see http://www.numpy.org/)

# # # # # # # # #
#   Imports:    #
# # # # # # # # #

try:
    import numpy
    import math
    from osgeo import gdal, osr
    from gdalconst import *

except Exception:
    print "Dependencies not installed? Make sure GDAL and NumPy are installed. Exiting."
    exit()


#
# Buffers shoals by one cell in all directions
# (Simply put: Focal 3 x 3 max filter)
#
def buffer_shoals(src_array, nodata):
    rows = src_array.shape[0]               # Number of rows
    columns = src_array.shape[1]            # Number of columns

    max_elev = -99999.0                     # Placeholder for shoalest depth
    placeholder = max_elev                  # Original value (-99999.0)

    temp_array = src_array.copy()           # Copy original data array:

    # Loop trough cells:
    for row in range(rows):
        for col in range(columns):

            # Reset max elevation to placeholder value
            max_elev = placeholder

            if(row == 0):                   # Top row
                if(col == 0):               # Top-left corner - 3 directions
                    max_elev = max(temp_array[row, col + 1], 
                                    temp_array[row + 1, col], 
                                    temp_array[row + 1, col + 1])
                elif(col == columns - 1):   # Top-right corner - 3 directions
                    max_elev = max(temp_array[row, col - 1], 
                                    temp_array[row + 1, col], 
                                    temp_array[row + 1, col -1])
                else:                       # Top row, in between corners - 5 directions
                    max_elev = max(temp_array[row, col - 1], 
                                    temp_array[row, col + 1], 
                                    temp_array[row + 1, col], 
                                    temp_array[row + 1, col - 1], 
                                    temp_array[row + 1, col + 1])

            elif(row == rows - 1):          # Bottom row
                if(col == 0):               # Bottom-left corner - 3 directions
                    max_elev = max(temp_array[row, col + 1], 
                                    temp_array[row - 1, col], 
                                    temp_array[row - 1, col + 1])

                elif(col == columns - 1):   # Bottom-right corner - 3 directions
                    max_elev = max(temp_array[row, col - 1], 
                                    temp_array[row - 1, col], 
                                    temp_array[row - 1, col - 1])

                else:                       # Bottom row, in between corners - 5 directions
                    max_elev = max(temp_array[row, col - 1], 
                                    temp_array[row, col + 1], 
                                    temp_array[row - 1, col], 
                                    temp_array[row - 1, col - 1], 
                                    temp_array[row - 1, col + 1])

            else:                           # Row in between top and bottom rows
                if(col == 0):               # Left edge - 5 directions
                    max_elev = max(temp_array[row, col + 1], 
                                    temp_array[row + 1, col], 
                                    temp_array[row - 1, col], 
                                    temp_array[row - 1, col + 1], 
                                    temp_array[row + 1, col + 1])

                elif(col == columns - 1):   # Right edge - 5 directions
                    max_elev = max(temp_array[row, col - 1], 
                                    temp_array[row + 1, col], 
                                    temp_array[row - 1, col], 
                                    temp_array[row - 1, col - 1], 
                                    temp_array[row + 1, col - 1])

                else:                       # In the middle - 8 directions
                    max_elev = max( temp_array[row - 1, col - 1], 
                                    temp_array[row - 1, col], 
                                    temp_array[row - 1, col + 1], 
                                    temp_array[row, col - 1], 
                                    temp_array[row, col + 1],
                                    temp_array[row + 1, col - 1],
                                    temp_array[row + 1, col],
                                    temp_array[row + 1, col + 1])

            # Update cell value:
            if(max_elev > placeholder and src_array[row, col] != nodata):
                if(max_elev > src_array[row, col]):     # If neighbor is shoaler
                    src_array[row, col] = max_elev      # Update cell

    del temp_array  # Remove unnecessary array variable
    return          # Return


#
# Creates and returns a "Coin".
# Coin is a boolean 2D array and can be of any shape - this example approximates round coins.
# Trimming removes extreme edges --> smoother contour limits and faster processing.
#
def create_coin(radius, trim_flag):
    y, x = numpy.mgrid[-radius : radius + 1, -radius : radius + 1]
    ret = x**2 + y**2 <= radius**2

    if(trim_flag == True):  
        return ret[1:-1, 1:-1]      # Return trimmed coin (removes extreme rows and columns)

    else:
        return ret                  # Return coin as is (no trimming)


#
# Returns shoalest depth on coin area, depending on the cells tested
#
# MISSING: Corners, top & bottom rows and extreme columns (due to edge effects, pad depth models with no data to avoid / develop behaviour on edges).
#
def check_coin(coin, radius, array, index_row, index_col, rows, columns):
    shoalest = -99999.0  # Placeholder and initial value

    if(index_row >= radius and index_row <= (rows-radius-1) and index_col >= radius and index_col <= (columns-radius-1)): # Inside data array
        
        for row_coin in range(-radius, radius + 1): # Check the coin area
            for col_coin in range(-radius, radius + 1):
                
                if(coin[row_coin + radius, col_coin + radius] == True):                # Cell on the coin
                    if(array[index_row + row_coin][index_col + col_coin] > shoalest):  # Get shoalest value from coin area
                        shoalest = array[index_row + row_coin][index_col + col_coin]

        if(shoalest != -99999.0):
            return True, shoalest   # Return True & shoalest cell depth
        else:
            return False, 0         # Return False & 0

    else:
        return False, 0             # Return False & 0


#
# Rolls the coin.
#
def roll_coin(src_array, dest_array, coin, radius, nodata):
    rows = src_array.shape[0]
    columns = src_array.shape[1]
    coin_ok = False

    # Start "rolling":
    for row in range(rows):
        for col in range(columns):
            coin_ok = False

            # Check the coin area for shoals:
            coin_ok, shoalest = check_coin(coin, radius, src_array, row, col, rows, columns)

            # If coin is ok, write to destination array:
            if(coin_ok == True):
                for row_coin in range(-radius, radius + 1):
                    for col_coin in range(-radius, radius + 1):
                        if(coin[row_coin + radius, col_coin + radius] == True): # On coin
                            if(dest_array[row + row_coin][col + col_coin] > shoalest and src_array[row + row_coin][col + col_coin] != nodata):
                                dest_array[row + row_coin][col + col_coin] = shoalest

    # Restore original nodata values:
    for row in range(rows):
        for col in range(columns):
            if(src_array[row, col] == nodata):
                dest_array[row, col] = nodata

    return


#
# "Main method":
#
def main(inpath, outpath, radius, trim):

    #
    # # Read in the data and get original nodata value and depth min/max:
    #
    try:
        data = gdal.Open(inpath, GA_ReadOnly)   # Open dataset in read-only mode (GDAL)
        band = data.GetRasterBand(1)            # Get elevation band
        nodata = band.GetNoDataValue()          # Get NoData value

        # Fetch data to a NumPy array:
        data_array = numpy.array(data.GetRasterBand(1).ReadAsArray())

        # Create a new NumPy array to hold smooth surface:
        dest_array = numpy.full((data_array.shape[0], data_array.shape[1]), 0, dtype = numpy.float32, order = "C")
    
    except Exception:
        print "Error loading the data. Exiting."
        exit()


    #
    # # Create Coin:
    #
    try:
        coin_radius = radius
        trimflag = trim
        coin = create_coin(coin_radius, trimflag)
        print "\nCoin OK, radius = " + str(coin_radius) + ", Trim =", trimflag 
    
    except Exception:
        print "Error in coin creation. Exiting."
        exit()


    #
    # # Start rolling the coin:
    #
    try:
        print "\nBuffering shoals.."
        buffer_shoals(data_array, nodata)
        print "Rolling coin.."
        roll_coin(data_array, dest_array, coin, coin_radius - 1, nodata)
    
    except Exception:
        print "Error in surface manipulation. Exiting."
        exit()
    
    #
    # # Write surface using GDAL:
    #
    try:
        print "\n\nExporting surface.."
        driver = gdal.GetDriverByName("GTiff")
        outdata = driver.Create(outpath, dest_array.shape[1], dest_array.shape[0], 1, gdal.GDT_Float32)
        outband = outdata.GetRasterBand(1)
        outband.SetNoDataValue(nodata)
        outband.WriteArray(dest_array)
        outdata.SetGeoTransform(data.GetGeoTransform())
        outdata.SetProjection(data.GetProjection())
        outdata = None # Close dataset
        print "Done.\n"
    
    except Exception:
        print "Error exporting the surface. Exiting."
        exit()



#                       #
#   Start the process:  #
#                       #

trim = True     # Coin trim flag
radius = 5     # Coin radius

depth_model = R"C:\Users\L165912\Desktop\DEV_roll\Pietarsaari.tif"
output_path = R"C:\Users\L165912\Desktop\DEV_roll\Pietarsaari_R5T.tif"

main(depth_model, output_path, radius, trim)
