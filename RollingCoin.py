# -*- coding: utf-8 -*-
# Python2

# Part of FTA Depth contour production automation tests
# Finnish Transport Agency, Hydrographic Office

# This proof-of-concept script reads in (GeoTIFF-) depth models, creates:
#	1. Go/NoGo areas (Shoals) (not exported)
#	2. Expanded shoals (buffered/expanded 1 cell in all directions) (not exported)
#	3. "Rolling Coin" generalized contour limit surface (exported)

# Depends on:
# 1. GDAL (see http://www.gdal.org/)
# 2. NumPy (see http://www.numpy.org/)

# # # # # # # # #
#	Imports:	#
# # # # # # # # #

try:
	import os
	import time
	import numpy
	import math
	from osgeo import gdal, osr
	from gdalconst import *

except Exception:
	print "Dependencies not installed? Make sure GDAL and NumPy are installed. Exiting."
	exit()


# # # # # # # # # # # # # # #
# 	Function definitions: 	#
# # # # # # # # # # # # # # #

#
# Parses contour depth limits based on nominal contour value (VALDCO)
# IHO Chart contour limits 3.09 ... 20.09, 30.49, 50.99 ..
#
def parseDepthLimit(valdco):
    ret = abs(valdco)
    if (valdco == 0):
		return 0
    elif (ret < 30):
        ret += 0.09
    elif (ret == 30): # 30 m contour --> 30.49
        ret += 0.49
    else: # valdco > 30
        ret += 0.99
    return -1 * ret # Negate


#
# Returns a new NumPy array with cell values of either 0 or 1 based on depth limit parameter.
# Shoal = 0, Safe = 1. Data type is 16-bit integer.
#
def array_to_binaryarray(src_array, depth_limit, nodata, new_nodata):
	rows = src_array.shape[0]
	columns = src_array.shape[1]

	# Create new array with (filled with nodata as default):
	dest_array = numpy.full((src_array.shape[0], src_array.shape[1]), new_nodata, dtype = numpy.int16, order = 'C')

	# Loop trough cells:
	for i in range(rows):
		for j in range(columns):
			if(src_array[i][j] == nodata): # NoData -values
				dest_array[i][j] = new_nodata
			elif(src_array[i][j] > depth_limit): # Shoal --> 0
				dest_array[i][j] = 0
			else:
				dest_array[i][j] = 1

	return dest_array # Cell values either 0 (shoal), 1 (safe) or new_nodata


#
# Returns a new NumPy array with 'no go' areas buffered by 1 cell in all directions.
# Cell data type is 16-bit integer.
#
def buffer_shoals(src_array, new_nodata):
	rows = src_array.shape[0]
	columns = src_array.shape[1]

	# Create new array with identical dimensions (filled with ones as default):
	dest_array = numpy.full((src_array.shape[0], src_array.shape[1]), 1, dtype = numpy.int16, order = 'C')

	# Calculate max indexes:
	colmax = columns - 1
	rowmax = rows - 1

	# Loop trough cells:
	for i in range(rows):
		for j in range(columns):
			if(src_array[i][j] == 0): # Shoal: expand
				dest_array[i][j] = 0 # Current cell

				if(i == 0): # Top row
					if(j == 0): # Top-left corner - 3 directions
						dest_array[i][j+1] = 0
						dest_array[i+1][j] = 0
						dest_array[i+1][j+1] = 0
					elif(j == colmax): # Top-right corner - 3 directions
						dest_array[i][j-1] = 0
						dest_array[i+1][j] = 0
						dest_array[i+1][j-1] = 0
					else: # Top row, in between corners - 5 directions
						dest_array[i][j-1] = 0
						dest_array[i][j+1] = 0
						dest_array[i+1][j] = 0
						dest_array[i+1][j-1] = 0
						dest_array[i+1][j+1] = 0

				elif(i > 0 and i < rowmax): # Row in between top and bottom rows
					if(j == 0): # Left edge - 5 directions
						dest_array[i][j+1] = 0
						dest_array[i+1][j] = 0
						dest_array[i-1][j] = 0
						dest_array[i-1][j+1] = 0
						dest_array[i+1][j+1] = 0
					elif(j == colmax): # Right edge - 5 directions
						dest_array[i][j-1] = 0
						dest_array[i+1][j] = 0
						dest_array[i-1][j] = 0
						dest_array[i-1][j-1] = 0
						dest_array[i+1][j-1] = 0
					else: # In the middle - 8 directions
						dest_array[i-1][j-1] = 0
						dest_array[i-1][j] = 0
						dest_array[i-1][j+1] = 0
						dest_array[i][j-1] = 0
						dest_array[i][j+1] = 0
						dest_array[i+1][j-1] = 0
						dest_array[i+1][j] = 0
						dest_array[i+1][j+1] = 0

				elif(i == rowmax): # Bottom row
					if(j == 0): # Bottom-left corner - 3 directions
						dest_array[i][j+1] = 0
						dest_array[i-1][j] = 0
						dest_array[i-1][j+1] = 0
					elif(j == colmax): # Bottom-right corner - 3 directions
						dest_array[i][j-1] = 0
						dest_array[i-1][j] = 0
						dest_array[i-1][j-1] = 0
					else: # Bottom row, in between corners - 5 directions
						dest_array[i][j-1] = 0
						dest_array[i][j+1] = 0
						dest_array[i-1][j] = 0
						dest_array[i-1][j-1] = 0
						dest_array[i-1][j+1] = 0

			if(src_array[i][j] == new_nodata): # NoData remains
				dest_array[i][j] = new_nodata

	# Restore original NoData after buffering:
	for i in range(rows):
		for j in range(columns):
			if(src_array[i][j] == new_nodata):
				dest_array[i][j] = new_nodata

	return dest_array


#
# Creates and returns a 'Coin'.
# Coin is a boolean 2D array. Extreme edges are trimmed for better results.
#
def create_coin(radius):
	y, x = numpy.mgrid[-radius : radius + 1, -radius : radius + 1]
	ret = x**2 + y**2 <= radius**2
	return ret[1:-1, 1:-1] # Cut out outer edges: makes generalized contour limits smoother and processing more efficient


#
# Returns either TRUE or FALSE, depending on the cells tested
# Cell to be tested is always in the middle of the coin.
#
# MISSING: Corners, top & bottom rows (due to edge effects, pad depth models with no data to avoid / develop behaviour on edges).
#
def check_coin(coin, radius, array, index_row, index_col, rows, columns):
	if(index_row >= radius and index_row <= (rows-radius-1) and index_col >= radius and index_col <= (columns-radius-1)): # Inside array:
		for row_coin in range(-radius, radius + 1): # Check the coin area
			for col_coin in range(-radius, radius + 1):
				if(coin[row_coin + radius, col_coin + radius] == False): # Coin indexing - not on coin
					continue # Next cell
				else: # On coin:
					if(array[index_row + row_coin][index_col + col_coin] == 0): # Shoal cell on coin -> return false
						return False
		return True
	else:
		return False


#
# Rolls the coin.
#
def roll_coin(src_array, dest_array, coin, radius, nodata, valdco):
	rows = src_array.shape[0]
	columns = src_array.shape[1]
	isclean = False

	# Start 'rolling':
	try:
		for i in range(rows):
			for j in range(columns):
				isclean = False

				if(src_array[i][j] == 0): # Shoal, move to next cell
					continue 
				elif(src_array[i][j] == nodata): # NoData, move to next cell
					continue

				# Check the coin area for shoals:
				isclean = check_coin(coin, radius, src_array, i, j, rows, columns)

				# If coin is clean, write to destination array:
				if(isclean == True):
					for row_coin in range(-radius, radius + 1):
						for col_coin in range(-radius, radius + 1):
							if(coin[row_coin + radius, col_coin + radius] == False): # Not on coin: move to next cell
								continue
							else: # On the coin, write:
								dest_array[i + row_coin][j + col_coin] = valdco

		# Restore original nodata:
		for i in range(rows):
			for j in range(columns):
				if(src_array[i][j] == nodata): # NoData, move to next cell
					dest_array[i][j] = nodata # Write nodata to destination array

		return True

	except Exception:
		return False


#
# "Main method":
#
def main(path, outpath, contourpath):
	# Get time stamp, start time:
	start_time = time.ctime() 

	# Define a nodata value for arrays:
	nodata_new = 15000 # "Deep enough"

	# Contour list (current FTA production contours):
	contour_list = [3, 6, 10, 13, 15, 20, 30, 50, 100, 200, 500]

	# Read in data and get original nodata value and depth min/max:
	try:
		data = gdal.Open(path, GA_ReadOnly)
		band = data.GetRasterBand(1)
		nodata = band.GetNoDataValue() # Get NoData value
		min_max_depth = band.ComputeRasterMinMax(0) # Actual, all cells included
		minimum_depth = min_max_depth[1]
		maximum_depth = min_max_depth[0]

		# Create Numpy array from raster data:
		data_array = numpy.array(data.GetRasterBand(1).ReadAsArray())

		# Create new array to hold all contour limits:
		dest_array = numpy.full((data_array.shape[0], data_array.shape[1]), 0, dtype = numpy.int16, order = 'C')

	except Exception:
		print "Error reading the input data. Exiting."
		exit()


	# Create Coin:
	try:
		coin_radius = 10 # Promising results using radius of 10 and 5m spatial resolution
		coin = create_coin(coin_radius)
	except Exception:
		print "Error in Coin creation. Exiting."
		exit()


	# # # # # # # # # # # # # # # # # # #
	# 		Start rolling the coin: 	#
	# # # # # # # # # # # # # # # # # # #

	try:
		for valdco in contour_list:
			# Get true depth limit by valdco:
			deplim = parseDepthLimit(valdco)

			# Skip contours outside data depth range:
			if (math.fabs(deplim) < math.fabs(minimum_depth) or math.fabs(deplim) > math.fabs(maximum_depth)):
				continue

			# Generate depth limits:
			print "\nGenerating contour limits for", valdco, "m contour:"

			# Create/update "binary array":
			print "  1. Creating GO/NOGO array.."
			byte_array = array_to_binaryarray(data_array, deplim, nodata, nodata_new)

			# Buffer shoals create/update:
			print "  2. Expanding shoals to ensure contour safety.."
			buffered_array = buffer_shoals(byte_array, nodata_new)

			# Generalize surface using rolling coin:
			print "  3. Rolling coin.."
			success = roll_coin(buffered_array, dest_array, coin, coin_radius - 1, nodata_new, valdco)
			if (success is False):
				print "Error in Coin Rolling. Exiting."
				exit()

	except Exception:
		print "Error in depth limit surface calculation. Exiting."
		exit()


	# # # # # # # # # # # # # # # # # # # # # #
	# Write contour limit raster using GDAL:  #
	# # # # # # # # # # # # # # # # # # # # # #
	try:
		print "\n\nExporting contour limits surface.."
		driver = gdal.GetDriverByName("GTiff")
		outdata = driver.Create(outpath, dest_array.shape[1], dest_array.shape[0], 1, gdal.GDT_Int16)
		outband = outdata.GetRasterBand(1)
		outband.SetNoDataValue(nodata_new)
		outband.WriteArray(dest_array)
		outdata.SetGeoTransform(data.GetGeoTransform())
		outdata.SetProjection(data.GetProjection())
		outdata = None # Close dataset
	except Exception, e:
		print "Error exporting contour limit surface. Exiting.."
		print e
		exit()

	try:
		print "\nGenerating raw contours.."
		contour_command = 'gdal_contour -f "ESRI Shapefile" -i 1 -a VALDCO -b 1 ' + outpath + " " + contourpath
		os.system(contour_command)
	except Exception:
		print "Error generating raw contours. Contour shapefile not generated."

	# Time stamp, end:
	end_time = time.ctime()

	print "\nProcess started:	", start_time
	print "Process ended:		", end_time


#
# Optional method, does part of the post-processing
# This optional method depends on GeoPandas (see http://geopandas.org/)
#
def filter_contours(raw_contourpath, export_contourpath):
	try:
		import geopandas as gpd
		data = gpd.read_file(raw_contourpath)
		data['VALDCO'] = data['VALDCO'].astype('int')
		product_contours = data.loc[data['VALDCO'].isin([3, 6, 10, 13, 15, 20, 30, 50, 100, 200, 500])] # FTA Production contours
		product_contours.to_file(export_contourpath)
	except Exception:
		print "\nContour filtering failed. Raw contours still available:", raw_contourpath
		return

	try:
		del_command = "del " + raw_contourpath.split(".")[0] + ".*"
		os.system(del_command)
	except Exception:
		"Couldn't delete raw contour file."
		return


# # # # # # # # # # # #
# Start the process:  #
# # # # # # # # # # # #

depth_model = R"C:\Users\User\Path\Depthmodel.tif"
output_path = R"C:\Users\User\Path\Output\Contour_limits.tif"
raw_contours = R"C:\Users\User\Path\Output\RAW_Contours.shp"
filtered_contours = R"C:\Users\User\Path\Output\Contours.shp"

main(depth_model, output_path, raw_contours)
filter_contours(raw_contours, filtered_contours)
