#GEOCOVID-createDB.py

#LIBRARIES
#Basic
import pandas as pd
import os
import subprocess
#Database
import getpass
from sqlalchemy import create_engine
import psycopg2 as ps
#Spatial
import geopandas as gpd
from geoalchemy2 import Geometry, WKTElement
from shapely import wkt
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from shapely.geometry.multipolygon import MultiPolygon

#CREATE DB
#establishing the connection
pw=getpass.getpass()
conn = ps.connect(database="postgres", user='postgres', password=pw, host='127.0.0.1', port= '5432')
conn.autocommit = True
#Creating a cursor object using the cursor() method
cursor = conn.cursor()
try:
  cursor.execute('CREATE database geocovid')
  cursor.execute('GRANT ALL PRIVILEGES ON DATABASE geocovid TO aladoy')
except:
  print("Database already exists")
#Closing the connection
conn.close()

#CONNECT TO DB
pw=getpass.getpass() #Ask for user password
engine=create_engine("postgresql+psycopg2://aladoy:{}@localhost/geocovid".format(pw)) #Create SQLAlchemy engine
conn=ps.connect("dbname='geocovid' user='aladoy' host='localhost' password='{}'".format(pw)) #Create a connection object
cursor=conn.cursor() #Create a cursor object
try:
    cursor.execute('CREATE EXTENSION postgis;') #Add postgis extension to make the db spatial
    conn.commit()
except:
    print("Postgis is already included")

#IMPORT DATA
def import_data(dat, name, pk, type_geom, idx_geom=False):
    print(dat.shape)
    print(dat.crs)
    dat.columns=map(str.lower,dat.columns) #convert columns to lower case
    dat.to_postgis(name, engine,if_exists='replace') #Add to postgis
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM {}".format(name))
    print("Number of rows in the table :", cursor.fetchone())
    cursor.execute("SELECT COUNT(*) FROM information_schema.columns where table_name='{}'".format(name))
    print("Number of columns in the table :", cursor.fetchall())
    if pk!='NULL':
        cursor.execute("ALTER TABLE {} ADD PRIMARY KEY({});".format(name,pk)) #Add PK
        conn.commit()
    if idx_geom==True:
        cursor.execute("CREATE INDEX idx_geom_{} ON {} USING GIST(geometry);".format(name, name)) #Add geometry index
        conn.commit()
    print('TABLE ', name, ' WAS SUCESSFULLY IMPORTED')


#IMPORT STATPOP
#Read Statpop data file (CSV)
statpop=pd.read_csv("data/STATPOP/STATPOP2019.csv",sep=',')
statpop.shape
#Move to RELI centroids
statpop[['X_KOORD','Y_KOORD','E_KOORD','N_KOORD']]=statpop[['X_KOORD','Y_KOORD','E_KOORD','N_KOORD']].applymap(lambda x: x + 50)
#Create a geometry column using Shapely
statpop=statpop.assign(geometry=statpop.apply(lambda row: Point(row.E_KOORD, row.N_KOORD),axis=1))
#Convert to geodataframe
statpop=gpd.GeoDataFrame(statpop, geometry=statpop.geometry, crs={'init': 'epsg:2056'})
#Add lat lon
statpop['lon']=statpop.to_crs({'init': 'epsg:4326'}).geometry.x
statpop['lat']=statpop.to_crs({'init': 'epsg:4326'}).geometry.y
import_data(statpop,'statpop_centroid','reli','POINT',True)

#IMPORT SWISS BOUNDARIES
#Read administrative country boders ESRI shapefile layer
country=gpd.read_file("data/SWISSBOUNDARIES2018/swissBOUNDARIES2D_LANDESGEBIET.shp")
#Rename columns with appropriate names (lowercase)
country.columns=['uuid','date_modif','date_creat','data_yr_creat','data_mth_creat','data_yr_verif','data_mth_verif','modif','source','data_yr_upd','data_mth_upd','admin_level','quality','code','lake_area','name','nb_hab','area','part','geometry']
#Keep only Swiss features
country=country[country.code=='CH']
import_data(country,'country','uuid','POLYGON',True)

#Read administrative cantons borders
cantons=gpd.read_file("data/SWISSBOUNDARIES2018/swissBOUNDARIES2D_KANTONSGEBIET.shp")
#Rename columns with appropriate names (lowercase)
cantons.columns=['uuid','date_modif','date_creat','data_yr_creat','data_mth_creat','data_yr_verif','data_mth_verif','modif','source','data_yr_upd','data_mth_upd','admin_level','quality','country_code','num','lake_area','area','part','name','nb_hab','geometry']
#Keep only Swiss features
cantons=cantons[cantons.country_code=='CH']
import_data(cantons,'cantons','uuid','POLYGON',True)

#Read administrative municipalities borders
municipalities=gpd.read_file("data/SWISSBOUNDARIES2018/swissBOUNDARIES2D_HOHEITSGEBIET.shp")
#Rename columns with appropriate names (lowercase)
municipalities.columns=['uuid','date_modif','date_creat','data_yr_creat','data_mth_creat','data_yr_verif','data_mth_verif','modif','source','data_yr_upd','data_mth_upd','admin_level','district_num','lake_area','quality','name','canton_num','country_code','nb_hab','num','part','area','area_code','geometry']
#Keep only Swiss features
municipalities=municipalities[municipalities.country_code=='CH']
import_data(municipalities,'municipalities','uuid','POLYGON',True)

#IMPORT GEOCOVID tests (change to "append" if we obtain updated data)
covid_vd=gpd.read_file('outputs/covid_vd.gpkg',encoding='utf-8')
#Convert to datetime
covid_vd['date_reception']=pd.to_datetime(covid_vd.date_reception,format='%d.%m.%Y')
covid_vd['date_prelevement']=pd.to_datetime(covid_vd.date_reception,format='%d.%m.%Y')
import_data(covid_vd,'covid_tests_vd','id_demande','POINT','NULL')

#Convert age to int
cursor.execute("UPDATE covid_tests_vd SET age = NULL WHERE age = 'ND';")
cursor.execute("ALTER TABLE covid_tests_vd ALTER COLUMN age TYPE FLOAT USING (age::float);")
conn.commit()

#IMPORT HECTOMETRIC GRID FOR THE CANTON OF VAUD (CREATED IN QGIS)
grid_vd=gpd.read_file('data/ha_grid_vd.gpkg',encoding='utf-8')
#Add RELI to grid
grid_vd['left']=grid_vd.left.astype('string')
grid_vd['bottom']=grid_vd.bottom.astype('string')
grid_vd['reli']=grid_vd.apply(lambda row: row.left[1:5]+row.bottom[1:5],axis=1)
#Cast RELI from string to float
grid_vd['reli']=grid_vd.reli.astype('float')
import_data(grid_vd[['reli','geometry']],'grid_vd','reli','POLYGON',True)

#IMPORT NPA DATA 2019 (MICROGIS)
npa=gpd.read_file('data/NPA/mgis.2019/data/SF_COMPACT_LC_2019.shp')
npa=npa.to_crs(2056) #Convert to EPSG:2056
import_data(npa,'npa','LCID','POLYGON',True)

#Create materialized view of swiss french municipalities
cursor.execute("CREATE MATERIALIZED VIEW swiss_french_municipalities AS SELECT * FROM municipalities WHERE canton_num IN (10,22,23,24,25,26) AND name NOT LIKE 'Lac %'")
conn.commit()

#Create materialized view of VD municipalities
cursor.execute("CREATE MATERIALIZED VIEW vd_municipalities AS SELECT * FROM municipalities WHERE canton_num=22 AND name NOT LIKE 'Lac %'")
conn.commit()

conn.close()
