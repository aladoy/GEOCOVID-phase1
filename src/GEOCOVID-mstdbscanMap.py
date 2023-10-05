#GEOCOVID-mstdbscanMap.py
import json
from pandas import json_normalize
import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import os
import math
import getpass
from sqlalchemy import create_engine
import psycopg2 as ps
from folium.plugins import TimestampedGeoJson
import calendar
from datetime import date
from shapely.geometry import mapping
import branca.colormap as cm
from folium.plugins import FloatImage
from folium import IFrame
import base64

outdir='outputs/COVID_MSTDBSCAN/ByDays_1km/'
resdir='supplementary_materials_paper/supp_mat_6/'

#Open clusterGDF file
data=gpd.read_file(outdir+'clusterGDF.gpkg',driver='GPKG')
#Convert to lat/lon
data=data.to_crs({'init': 'epsg:4326'})

#Open diffusionZones
zones=gpd.read_file(outdir+'diffusionZones.gpkg',driver='GPKG')
#Convert to lat/lon
zones=zones.to_crs({'init': 'epsg:4326'})


#Convert to_datetime
data['mstDate']=pd.to_datetime(data.mstDate,format='%Y-%m-%d')

#CONNECT TO DB WITH user=aladoy
pw=getpass.getpass() #Ask for user password
engine=create_engine("postgresql+psycopg2://aladoy:{}@localhost/geocovid".format(pw)) #Create SQLAlchemy engine
conn=ps.connect("dbname='geocovid' user='aladoy' host='localhost' password='{}'".format(pw)) #Create a connection object
cursor=conn.cursor() #Create a cursor object


#TESTS / CASES
tests=gpd.read_postgis("SELECT id_demande, date_reception, charge_virale, ST_X(ST_TRANSFORM(geometry,4326)) AS lon, ST_Y(ST_TRANSFORM(geometry, 4326)) AS lat, geometry FROM covid_tests_vd WHERE res_cov=0",conn,geom_col='geometry')
cases=gpd.read_postgis("SELECT id_demande, date_reception, charge_virale, ST_X(ST_TRANSFORM(geometry,4326)) AS lon, ST_Y(ST_TRANSFORM(geometry, 4326)) AS lat, geometry FROM covid_tests_vd WHERE res_cov=1",conn,geom_col='geometry')


#Extract Lat/Lon corresponding to the center of the canton
cursor.execute("SELECT ST_X(ST_Transform(ST_Centroid(ST_Union(geometry)),4326)) FROM cantons WHERE name='Vaud'")
x=cursor.fetchone()[0]
cursor.execute("SELECT ST_Y(ST_Transform(ST_Centroid(ST_Union(geometry)),4326)) FROM cantons WHERE name='Vaud'")
y=cursor.fetchone()[0]
print(x,y)

#Create dic for colors
colors={'Emerge':'#fb9a99','Growth':"#e31a1c", 'Steady':"#33a02c", 'Merge':"#ffffb3", 'Move':"#fdb462", 'Split':"#bebada", 'Reduction':"#1f78b4"}
data['colorHEX'] = data['type'].map(colors)

def create_geojson_features(df):
    features = []
    for idx, row in df.iterrows():
        feature = {
            'type': 'Feature',
            'geometry': {
                'type':'Polygon',
                'coordinates':mapping(df.loc[idx].geometry)['coordinates']
            },
            'properties': {
                'time': pd.to_datetime(row['mstDate'], unit='D').__str__(),
                'style': {'color' : row['colorHEX'], 'opacity':0.7, 'fillOpacity':0.7},
                'popup': 'Cluster ID: ' + str(row['clusterID']) + '<br> Type: ' + row['type']
                }
            }
        features.append(feature)
    return features

#Define colors for diffusion zones
colors = {'1':'#A0CF8D', '2':'#FFC04C', '3':'#B0E0E6', 'no clusters':'#cccccc'}
zones['color']=zones['DZ'].map(colors)

#Map
def make_map(features):
    coords_vd=[y, x]
    mstdbscan_map = folium.Map(location=coords_vd, control_scale=True, zoom_start=9,tiles='cartodbpositron')

    folium.GeoJson(
    zones,
    style_function = lambda x: {"weight":0.5,
                            'color':'#cccccc',
                            'fillColor':x['properties']['color'],
                            'fillOpacity':0.4}).add_to(mstdbscan_map)

    # for i in range(0, len(tests)):
    #     folium.Circle(
    #     location=[tests.iloc[i]['lat'], tests.iloc[i]['lon']],
    #     radius=1,
    #     color='#000000',
    #     fill=True,
    #     fillColor='#000000'
    #     ).add_to(mstdbscan_map)

    # for i in range(0, len(cases)):
    #     folium.Circle(
    #     location=[cases.iloc[i]['lat'], cases.iloc[i]['lon']],
    #     radius=1,
    #     color='#66b266',
    #     fill=True,
    #     fillColor='#66b266',
    #     popup=cases.iloc[i]['date_reception']
    #     ).add_to(mstdbscan_map)

    TimestampedGeoJson(
        {'type': 'FeatureCollection',
        'features': features}
        , period='P1D'
        , duration = 'PT23H'
        , transition_time=1000
        , add_last_point=True
        , auto_play=False
        , loop=False
        , max_speed=1
        , loop_button=True
        , time_slider_drag_update=True
    ).add_to(mstdbscan_map)

    #image=outdir+'legend_interactive_map.png'
    #encoded = base64.b64encode(open(image, 'rb').read())
    #ADD title
    html="<div id='maplegend' class='maplegend' style='position: absolute; z-index:9999; border:0px; background-color:rgba(0, 0, 0, 0.5); border-radius:6px; padding: 10px; font-size:15px; right: 0px; top: 0px;'> \
    <div class='legend-scale'> \
      <img src='legend_interactive_map.png'> \
      </div> </div> </div>"
    mstdbscan_map.get_root().html.add_child(folium.Element(html))

    print('> Done.')
    return mstdbscan_map

features = create_geojson_features(data)
mstdbscan_map=make_map(features)
mstdbscan_map.save(resdir+'Supp_Mat_6.html')
