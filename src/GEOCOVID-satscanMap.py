#GEOCOVID-satscanMap.py

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

outdir='outputs/COVID_satscan/ByRELI/ByDays/'
resdir='supplementary_materials_paper/supp_mat_5/'

#Concatenate all results in a single dataframe
data = pd.DataFrame(columns=['CLUSTER','LOC_ID','LATITUDE','LONGITUDE','RADIUS','START_DATE','END_DATE','NUMBER_LOC','LLR','P_VALUE','OBSERVED','EXPECTED','REL_RISK','POPULATION']) # creates an empty df with the desired structure
for root, dirs, filenames in os.walk(outdir):
    for f in filenames:
        if f.endswith('.geojson'):
            df_temp = gpd.read_file(root + '/' + f)
            data = pd.concat([data, df_temp])

#Convert column names to lower cases
data.columns=data.columns.str.lower()
#Convert to_datetime
data['start_date']=pd.to_datetime(data.start_date,format='%Y/%m/%d')
data['end_date']=pd.to_datetime(data.end_date,format='%Y/%m/%d')
data=data.reset_index(drop=True)
data=gpd.GeoDataFrame(data,crs="EPSG:4326", geometry='geometry')

#Unique clusters with category
#data=gpd.read_file(outdir+'unique_clusters.gpkg')


#Keep only significant clusters (P.value <=0.05)
#data=data[data.p_value<=0.05]

#CONNECT TO DB WITH user=aladoy
pw=getpass.getpass() #Ask for user password
engine=create_engine("postgresql+psycopg2://aladoy:{}@localhost/geocovid".format(pw)) #Create SQLAlchemy engine
conn=ps.connect("dbname='geocovid' user='aladoy' host='localhost' password='{}'".format(pw)) #Create a connection object
cursor=conn.cursor() #Create a cursor object

#Extract Lat/Lon corresponding to the center of the canton
cursor.execute("SELECT ST_X(ST_Transform(ST_Centroid(ST_Union(geometry)),4326)) FROM cantons WHERE name='Vaud'")
x=cursor.fetchone()[0]
cursor.execute("SELECT ST_Y(ST_Transform(ST_Centroid(ST_Union(geometry)),4326)) FROM cantons WHERE name='Vaud'")
y=cursor.fetchone()[0]
print(x,y)

#NPA
npa=gpd.read_postgis("SELECT DISTINCT n.LCID,n.locality,n.ptot,st_transform(n.geometry,4326) as geometry FROM npa n, (SELECt * FROM cantons where name='Vaud') c WHERE ST_Overlaps(n.geometry, c.geometry) OR ST_Within(n.geometry,c.geometry)", conn, geom_col='geometry')

#TESTS / CASES
tests=gpd.read_postgis("SELECT id_demande, date_reception, charge_virale, ST_X(ST_TRANSFORM(geometry,4326)) AS lon, ST_Y(ST_TRANSFORM(geometry, 4326)) AS lat, geometry FROM covid_tests_vd WHERE res_cov=0",conn,geom_col='geometry')
cases=gpd.read_postgis("SELECT id_demande, date_reception, charge_virale, ST_X(ST_TRANSFORM(geometry,4326)) AS lon, ST_Y(ST_TRANSFORM(geometry, 4326)) AS lat, geometry FROM covid_tests_vd WHERE res_cov=1",conn,geom_col='geometry')


# def give_color(x):
#     if x.categorie=='all below 1 million':
#         color=3
#         colorHEX='#4f5bd5'
#     elif x.categorie=='at least one between 1 million and 1 billion':
#         color=2
#         colorHEX='#962fbf'
#     elif x.categorie=='at least three between 1 million and 1 billion':
#         color=1
#         colorHEX='#d62976'
#     elif x.categorie=='at least one above 1 billion':
#         color=0
#         colorHEX='#fa7e1e'
#     return color, colorHEX
# data['color'],data['colorHEX']=zip(*data.apply(lambda row:give_color(row),axis=1))
# #Sort values to plot significant points above
# data=data.sort_values('color')

def give_color(x):
    if x.p_value<=0.01:
        color=2
        colorHEX='#ff0000'
    elif x.p_value<=0.05:
        color=1
        colorHEX='#ff8181'
    else: #if not significant
        color=0
        colorHEX='#b2b2b2'
    return color, colorHEX
data['color'],data['colorHEX']=zip(*data.apply(lambda row:give_color(row),axis=1))

#Sort values to plot significant points above
data=data.sort_values('color')

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
                'time': pd.to_datetime(row['end_date'], unit='D').__str__(),
                'style': {'color' : row['colorHEX'], 'opacity':0.9, 'fillOpacity':0.6, 'fill':True},
                'popup': 'Cluster ID: ' + str(row['cluster']) + '<br> Start date: ' + row['start_date'].strftime('%Y/%m/%d') + '<br> End date: ' + row['end_date'].strftime('%Y/%m/%d') + '<br>Nb of hectares in cluster: ' + str(row['number_loc']) + '<br>Observed: ' + str(row['observed']) + '<br>Expected: ' + str(row['expected']) + '<br>Relative Risk: ' + str(row['rel_risk']) + '<br>Population: ' + str(row['population']) + '<br>Pvalue: ' +str(row['p_value'])
                }
            }
        features.append(feature)
    return features


#use period P7D and duration P6D for By2WeeksOverlap
def make_map(features):
    coords_vd=[y, x]
    satscan_map = folium.Map(location=coords_vd, control_scale=True, zoom_start=9,tiles='cartodbpositron')

    folium.GeoJson(
    npa,
    style_function=lambda feature: {
        'fillColor': '#cccccc',
        'color' : '#cccccc',
        'weight' : 1,
        'fillOpacity' : 0.3,
        }
    ).add_to(satscan_map)

    # for i in range(0, len(tests)):
    #     folium.Circle(
    #     location=[tests.iloc[i]['lat'], tests.iloc[i]['lon']],
    #     radius=1,
    #     color='#000000',
    #     fill=True,
    #     fillColor='#000000'
    #     ).add_to(satscan_map)
    #
    # for i in range(0, len(cases)):
    #     folium.Circle(
    #     location=[cases.iloc[i]['lat'], cases.iloc[i]['lon']],
    #     radius=1,
    #     color='#66b266',
    #     fill=True,
    #     fillColor='#66b266',
    #     popup=cases.iloc[i]['date_reception']
    #     ).add_to(satscan_map)

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
    ).add_to(satscan_map)


    #ADD title
    html="<div id='maplegend' class='maplegend' style='position: absolute; z-index:9999; border:0px; background-color:rgba(0, 0, 0, 0.5); border-radius:6px; padding: 10px; font-size:15px; right: 0px; top: 0px;'> \
    <div class='legend-scale'> \
      <img src='legend_interactive_map.png'> \
      </div> </div> </div>"
    # html="<div id='maplegend' class='maplegend' style='position: absolute; z-index:9999; border:0px; background-color:rgba(255, 255, 255, 0.8); border-radius:6px; padding: 10px; font-size:15px; right: 0px; top: 0px;'> \
    # <div class='legend-title'>Emerging space-time clusters of COVID-19</div> \
    # <div class='legend-scale'> \
    #   <ul class='legend-labels'> \
    #     <li><span></span>Heavy Red: P<0.01</li> \
    #     <li><span></span>Light Red: P<0.05</li> \
    #     <li><span></span>Grey: Not significant</li> \
    #   </ul></div> </div> </div>"
    # html="<div id='maplegend' class='maplegend' style='position: absolute; z-index:9999; border:0px; background-color:rgba(255, 255, 255, 0.8); border-radius:6px; padding: 10px; font-size:15px; right: 0px; top: 0px;'> \
    # <div class='legend-title'>Emerging space-time clusters of COVID-19</div> \
    # <div class='legend-scale'> \
    #   <ul class='legend-labels'> \
    #     <li><span></span>Blue: all below 1 million</li> \
    #     <li><span></span>Purple: at least one between 1 million and 1 billion</li> \
    #     <li><span></span>Pink: at least three between 1 million and 1 billion</li> \
    #     <li><span></span>Orange: at least one above 1 billion</li> \
    #   </ul></div> </div> </div>"
    satscan_map.get_root().html.add_child(folium.Element(html))

    print('> Done.')
    return satscan_map


features = create_geojson_features(data)
satscan_map=make_map(features)
satscan_map.save(resdir+'Supp_Mat_5.html')
#satscan_map.save(outdir+'satscan_map_cluster_category.html')
