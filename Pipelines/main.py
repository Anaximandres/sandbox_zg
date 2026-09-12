# -*- coding: utf-8 -*-

"""
Created on Mon Sep  7 15:54:38 2020
Updated on November 17, 2025
Updated on March 12, 2026

@author: Manuel Huber.
@author: Martina Natali.

To be used with config.json file.

Geemap is used to make use of Google earth engine and its functions. 
https://pypi.org/project/geemap/

"""


#  All libaries needed for this script
import ee
import geemap
import math
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import geopandas as gpd
import os
from S1ImageCollection import S1ImageCollection

# Set working directory to the script's parent folder
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

Map = geemap.Map()
ee.Initialize()



#%% Function to export Sentinel 1 variables as a csv file for specific fields

def creating_csv_S1(inp, out_path_year, Start, End, year, string,fn_shapefile_fields, project_id, asset_folder, fields_attribute, buffer_roi=-10):

    asset_path = os.path.join(project_id, asset_folder, fn_shapefile_fields)
    brp = ee.FeatureCollection(asset_path) # This asset needs to be uploaded before executing the script!
    
    select = brp.filter(ee.Filter.inList(fields_attribute, inp))
    
    StartDate = Start; # Input start date of Sentinel-1 data acquistion
    print("Start Date:", StartDate)
    EndDate = End; # Input end date of Sentinel-1 data acquisition
    print("End Date:", EndDate)
    
    #******************* SRTM DEM import *******************#
    dataset = ee.Image('USGS/SRTMGL1_003')
    srtm = dataset.select('elevation')
    
    #*********** Create a Buffer around the BRP parcels ************#
    def buffer_field(feature):
      buffer = -1 # -1 # -10 buffer in meters
      return feature.buffer(buffer)
  
    roi_crop_buffer = select.map(buffer_field)
    
    #************** Find Centroid of each Parcel ***********#
    
    def func_qzr(f):
      PolyCentroid = f.geometry().centroid()
    
      # A new property called 'area' will be set on each feature.
      return f.set({'Polygon_Centroid': PolyCentroid})
    
    roi_crop_buffer_new = roi_crop_buffer.map(func_qzr)
    #*** Function to remove border noise/edges and garbage values of 2017 and 2018 data ***#
    
    # Mask out using backscatter value threshold for VV and VH-Pol
    
    def BorderNoisefilter(image):
         im = image.select(['angle'])
         im2 = im.gt(28.) # update 20260312 martinanatali: originally 30
         im3 = im2.lt(47.) # update 20260312 martinanatali: originally 45
         im4 = image.updateMask(im3)
         all_var = image.updateMask(im4.select(['VV']).gt(0.001)) # update 20260312 martinanatali: originally 0.0003(=-35 dB)
         return all_var
    
    #*** Functions to convert S-1 Backscatter in dB/linear scale ***#
    
    def toNatural(i):
      return ee.Image(ee.Image.constant(10.0).pow(i.divide(10.0)).copyProperties(i, ['system:time_start']))
    
    def toDB(i):
      return ee.Image(i.select(0)).log10().multiply(10.0).copyProperties(i, ['system:time_start'])
    
    #** Sentinel-1 GRD data select, import and metadata filtering operations.
    #S1_GRD_FLOAT data is sleced to avoid mathematical operations at logarithmic scale **#
    #S1Pol = ee.ImageCollection('COPERNICUS/S1_GRD_FLOAT') \
    #        .filterBounds(roi_crop_buffer) \
    #        .filterDate(StartDate, EndDate) \
    #        .filter(ee.Filter.listContains('transmitterReceiverPolarisation','VV')) \
    #        .filter(ee.Filter.listContains('transmitterReceiverPolarisation','VH')) \
    #        .filter(ee.Filter.eq('instrumentMode', 'IW')) \
    #        .sort('system:time_start') \
    #        .map(BorderNoisefilter) \
            
    retrieved_collection = S1ImageCollection(roi_crop_buffer, StartDate, EndDate)

    if S1Pol.size().getInfo() != 0:
       
      # get the orbits in the collection
      # we will loop over orbits
      def add_orbit_pass_combo(image):
        orbit = image.get('relativeOrbitNumber_start')
        pass_dir = image.get('orbitProperties_pass')
        combo = ee.String(ee.Number(orbit).format()).cat('_').cat(pass_dir)
        return image.set('orbit_pass_combo', combo)

      S1Pol_with_combo = S1Pol.map(add_orbit_pass_combo)
      orbit_pass_combos = S1Pol_with_combo.aggregate_array('orbit_pass_combo').distinct().getInfo()

      # loop over each orbit
      for combo in orbit_pass_combos:
          parts = combo.split('_')

          # retrieve orbit number and pass type
          rel_orbit = int(float(parts[0]))
          passType = parts[1]
          # get rotation and azimuth values based on pass type
          if passType == 'ASCENDING':
              rotation_val = 360.0
              azimuth_val = 270.0
          elif passType == 'DESCENDING':
              rotation_val = 180.0
              azimuth_val = 180.0

          # filter collection for this orbit and pass type
          S1Pol = S1Pol_with_combo.filter(ee.Filter.eq('orbit_pass_combo', combo))
          S1Pol = S1Pol.map(lambda img: img.select(img.bandNames().remove('orbit_pass_combo'))) # remove the orbit_pass_combo property

          print('Processing Relative Orbit: {}, Pass Type: {}'.format(rel_orbit, passType))
      
          # create folders to store headers and output files
          out_path_relOrbit = os.path.join(out_path_year, f'Orbit_{rel_orbit}')
          out_path_headers = os.path.join(out_path_year, 'Headers')
          os.makedirs(out_path_relOrbit, exist_ok=True)
          os.makedirs(out_path_headers, exist_ok=True)

          # write headers file
          out_file_fn = os.path.join(out_path_headers, f'Headers_Orbit_{rel_orbit}.txt')
          if os.path.exists(out_file_fn):
              os.remove(out_file_fn)
          out_file = open(out_file_fn, "a")
          out_file.write('S1_RO_{}_Pass_{}_Year_{}_{}.csv,\n'.format(rel_orbit, passType[:3],year,string))
          out_file.close()


          S1VV = S1Pol.select('VV')
          S1VH = S1Pol.select('VH')
          #Calculate Cross Pol ratio VH/VV for Sentinel-1 SAR data #
          def CrossPolRatio (image):
              return image.addBands(image.expression(
              'VH/VV', {
                'VH': image.select(['VH']),
                'VV': image.select(['VV'])
              }
                ))
          
          S1var = S1Pol.map(CrossPolRatio)
              
          #======================== Local Incidence Angle (LIA) calculation ==================\
          
          
          def get_angle(image):
              S1angle = image.select('angle')
              #We can use the gradient of the "angle" band of the S1 image to derive the S1 azimuth angle.
              S1_azimuth = ee.Terrain.aspect(S1angle) \
                                      .reduceRegion(ee.Reducer.mean(), S1angle.geometry(), 100) \
                                      .get('aspect')
              # Attention, this is not actually azimuth, but the look direction across range, which is NOT
              # yet corrected for the angle with which s1_inc is rotated relative to North!!!
              # Calculate True azimuth direction for the near range image edge
              def getCorners(f):
                # Get the coords as a transposed array
                coords = ee.Array(f.geometry().coordinates().get(0)).transpose()
                crdLons = ee.List(coords.toList().get(0))
                crdLats = ee.List(coords.toList().get(1))
                minLon = crdLons.sort().get(0)
                maxLon = crdLons.sort().get(-1)
                minLat = crdLats.sort().get(0)
                maxLat = crdLats.sort().get(-1)
                azimuth = ee.Number(crdLons.get(crdLats.indexOf(minLat))).subtract(minLon).atan2(ee.Number(crdLats.get(crdLons.indexOf(minLon))).subtract(minLat)) \
                          .multiply(180.0/math.pi).add(azimuth_val) 
                return ee.Feature(ee.Geometry.LineString([crdLons.get(crdLats.indexOf(minLat)), minLat,
              minLon, crdLats.get(crdLons.indexOf(minLon))]), { 'azimuth': azimuth}).copyProperties(f)
              
              azimuthEdge = getCorners(image)
              
              TrueAzimuth = azimuthEdge.get('azimuth')   # This should be some degree off the North direction, due to Earth rotation
              rotationFromNorth_or_South = ee.Number(TrueAzimuth).subtract(rotation_val) # Use subtract(180.0) for DESCENDING and subtract(360.0) for ASCENDING image.
              
              # Correct the across-range-look direction
              S1_azimuth = ee.Number(S1_azimuth).add(rotationFromNorth_or_South)  
              # Here we derive the terrain slope and aspect
              
              srtm_slope = ee.Terrain.slope(srtm).select('slope')
              srtm_aspect = ee.Terrain.aspect(srtm).select('aspect')
          
              # And finally the local incidence angle
              slope_projected2 = srtm_slope.multiply(ee.Image.constant(TrueAzimuth).subtract(90.0).subtract(srtm_aspect).multiply(math.pi/180).cos())
              lia2 = S1angle.subtract(ee.Image.constant(90).subtract(ee.Image.constant(90).subtract(slope_projected2))).abs()
              angles = lia2.addBands(S1_azimuth) # add azimuth angle to the lia image... this new band is called constant
              angles = angles.select(['angle','constant']).rename(['LIA','AZI']) # Renaming the bands in order to merge it together with the VH and VV datasets (they need to have the same coloumn names)
              return angles
          
          angles_all  = S1var.map(get_angle) # Including the azimuth angle
          
          angles_all_stack  = ee.ImageCollection(angles_all).toBands()
          S1_st_var = ee.ImageCollection(S1var).toBands()
          
          # Determine the scale to perform reduce Region operation #
          scale = S1VV.first().projection().nominalScale()
          
          # Combine the mean and standard deviation reducers.
          reducers = ee.Reducer.mean().combine(
            reducer2=ee.Reducer.stdDev(), sharedInputs=True).combine(
            reducer2=ee.Reducer.count(), sharedInputs=True)
          # Calculate the S1 mean backscatter or pixel values for a given shape file over a period of time #
          
          all_var = S1_st_var.addBands(angles_all_stack)
          all_comb = all_var.reduceRegions(**{'collection': roi_crop_buffer_new, 'reducer': reducers, 'scale': scale, 'tileScale': 8}) # Tilescale 8 is used to reduce the chance of memory error
          all_comb = all_comb.map(func_qzr)
          
          # export
          save = out_path_relOrbit + '/'
          geemap.ee_to_csv(all_comb, '{}S1_RO_{}_Pass_{}_Year_{}_{}.csv'.format(save, rel_orbit, passType[:3], year, string))
          print('wrote summarized image to: {}S1_RO_{}_Pass_{}_Year_{}_{}.csv'.format(save, rel_orbit, passType[:3], year, string))
        
    else:
        print('empty image collection')        


# ----------------------------------------------------------------------
#%% Main script

print(os.getcwd())
config_path = 'config.json'
import json
with open(config_path, 'r') as f:
    config = json.load(f)

# Configuration file inputs
years_list = config['years']
root_data_path = config['paths']['root_data_path']
os.makedirs(root_data_path, exist_ok=True)
folder_shapefile = config['paths']['folder_shapefile']
fn_shapefile_fields = config['paths']['fn_shapefile_fields']
path_shapefile_fields = os.path.join(folder_shapefile, fn_shapefile_fields+'.shp')
fn_shapefile_regions = config['paths']['fn_shapefile_regions']
path_shapefile_regions = os.path.join(folder_shapefile, fn_shapefile_regions+'.shp')
batch_size = config['processing']['batch_size']
fields_attribute = config['shapefile']['fields_attribute']
regions_attribute = config['shapefile']['regions_attribute']
project_id = config['GEE_user']['project_id']
asset_folder = config['GEE_user']['asset_folder']


# shapefiles
# The following shape file needs to be uploaded on Gooogle Earth Engine in the assets folder with the same name as the shp name (for example BRP_Proj_2020)
fields = gpd.read_file(path_shapefile_fields)
# Path to store the intermidiate shp files // Hence this needs to be created
# Those shp files are needed to structure the mining process
regions = gpd.read_file(path_shapefile_regions)
polygons_gem = regions['geometry']

# loop over years
for year in years_list:

    # period
    StartDate = f"{year}-01-01"
    EndDate   = f"{year}-12-31"

    # Path where to store the data (for the named year per orbit)
    out_path_year = os.path.join(root_data_path, year)
    os.makedirs(out_path_year, exist_ok=True)
    centroidseries = fields['geometry'].centroid
    

    for i in range(len(regions)):
        print(i + 1, f'out of {len(regions)}')
        index = fields[fields_attribute][centroidseries.within(polygons_gem[i])]
        index = index.values
        
        gem = regions[regions_attribute][i]
        
        if len(index) > batch_size:
            arr = list(range(0, len(index)))
            newarr = np.array_split(arr, int(np.round(len(index) / batch_size, 0)))
            
            for j in range(len(newarr)):
                string = f'{j + 1}_out_{len(newarr)}_{gem}'
                inp = index[min(newarr[j]):max(newarr[j]) + 1]
                inp = [int(y) for y in inp]
                save_des = out_path_year + '/'
                creating_csv_S1(inp, save_des, StartDate, EndDate, year, string, fn_shapefile_fields, project_id, asset_folder, fields_attribute)
        else:
            string = f'all_fields_{len(index)}_{gem}'
            inp = index
            inp = [int(y) for y in inp]
            save_des = out_path_year + '/'
            creating_csv_S1(inp, save_des, StartDate, EndDate, year, string, fn_shapefile_fields, project_id, asset_folder, fields_attribute)
      