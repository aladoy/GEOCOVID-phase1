#GEOCOVID-satscanUniqueSignifClusters.py

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Polygon
import os
import getpass
from sqlalchemy import create_engine
import psycopg2 as ps

outdir='outputs/COVID_satscan/ByRELI/ByDays/'

#IMPORT SATSCAN RESULTS (same script as in satscan)
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
#Keep only significant clusters
data=data[data.p_value<=0.05]
#Sort values according to end_date
data=data.sort_values('end_date',ascending=True)
#Add clusters duration (in days)
data['duration']=data['end_date']-data['start_date']
data['duration']=data['duration'].apply(lambda x: x / np.timedelta64(1,'D'))+1 #convert timedelta to integer

print('Total number of significant clusters: ', data.shape[0])

#CONNECT TO DB WITH user=aladoy
pw=getpass.getpass() #Ask for user password
engine=create_engine("postgresql+psycopg2://aladoy:{}@localhost/geocovid".format(pw)) #Create SQLAlchemy engine
conn=ps.connect("dbname='geocovid' user='aladoy' host='localhost' password='{}'".format(pw)) #Create a connection object
cursor=conn.cursor() #Create a cursor object

#VIRAL LOAD
cases=gpd.read_postgis("SELECT c.id_demande, c.date_reception, c.age, c.ct, c.charge_virale, st_transform(st_buffer(s.geometry,0.2),4326) as geometry FROM covid_tests_vd c INNER JOIN statpop_centroid s ON s.reli=c.corresponding_reli WHERE res_cov=1",conn, geom_col='geometry')
viral_load=gpd.sjoin(data, cases, how='left', op='intersects') #Spatial join between cases and clusters
#Keep only individuals that are tested during cluster duration
viral_load=viral_load[(viral_load.date_reception>=viral_load.start_date) & (viral_load.date_reception<=viral_load.end_date)]
#Convert age "ND" to nan
viral_load.loc[viral_load.age=='ND','age']=np.nan
viral_load['age']=viral_load.age.astype('float') #Convert to float

#FIRST 3 CASES BY CLUSTER
firstCases=viral_load.sort_values(['cluster','end_date','duration','population','observed','date_reception','p_value'])
firstCases=firstCases.groupby(['cluster','end_date','duration','population','observed','p_value']).head(3).reset_index(drop=True)
firstCases=firstCases.sort_values('end_date',ascending=True) #Sort values by end_date (already done but make sure of it)
firstCases=firstCases.drop_duplicates('id_demande',keep='first')

#CLASSIFY SaTScan CLUSTERS BASED ON VIRAL LOAD CATEGORIES (defined by G.Greub)
unique_clust=firstCases.drop_duplicates(subset=['cluster','end_date'])[['cluster','end_date','p_value']]
unique_clust.shape

for index,row in unique_clust.iterrows(): #non overlapping categories if we use elif

    cluster=firstCases[(firstCases.cluster==unique_clust.loc[index,'cluster']) & (firstCases.end_date==unique_clust.loc[index,'end_date'])]

    if (cluster['charge_virale']<1e6).all():
        unique_clust.loc[index,'category']='all below 1 million'
    if ((cluster['charge_virale']>=1e6) & (cluster['charge_virale']<1e7)).any():
        unique_clust.loc[index,'category']='at least one between 1 million and 10 millions'
    if ((cluster['charge_virale']>=1e7) & (cluster['charge_virale']<1e8)).any():
        unique_clust.loc[index,'category']='at least one between 10 millions and 100 millions'
    if ((cluster['charge_virale']>=1e8) & (cluster['charge_virale']<1e9)).any():
        unique_clust.loc[index,'category']='at least one between 100 millions and 1 billion'
    if ((cluster['charge_virale']>=1e9) & (cluster['charge_virale']<1e10)).any():
        unique_clust.loc[index,'category']='at least one between 1 billion and 10 billions'
    if (cluster['charge_virale']>1e10).any():
        unique_clust.loc[index,'category']='at least one above 10 billions'

#Number of clusters in each category
print('Nb of clusters - all below 1 million :', unique_clust[unique_clust.category=='all below 1 million'].shape[0],'(Significant:', unique_clust[(unique_clust.category=='all below 1 million') & (unique_clust.p_value<=0.05)].shape[0],')')
print('Nb of clusters - at least one between 1 million and 10 millions :', unique_clust[unique_clust.category=='at least one between 1 million and 10 millions'].shape[0],'(Significant:', unique_clust[(unique_clust.category=='at least one between 1 million and 10 millions') & (unique_clust.p_value<=0.05)].shape[0],')')
print('Nb of clusters - at least one between 10 millions and 100 millions :', unique_clust[unique_clust.category=='at least one between 10 millions and 100 millions'].shape[0],'(Significant:', unique_clust[(unique_clust.category=='at least one between 10 millions and 100 millions') & (unique_clust.p_value<=0.05)].shape[0],')')
print('Nb of clusters - at least one between 100 millions and 1 billion :', unique_clust[unique_clust.category=='at least one between 100 millions and 1 billion'].shape[0],'(Significant:', unique_clust[(unique_clust.category=='at least one between 100 millions and 1 billion') & (unique_clust.p_value<=0.05)].shape[0],')')
print('Nb of clusters - at least one between 1 billion and 10 billions :', unique_clust[unique_clust.category=='at least one between 1 billion and 10 billions'].shape[0],'(Significant:', unique_clust[(unique_clust.category=='at least one between 1 billion and 10 billions') & (unique_clust.p_value<=0.05)].shape[0],')')
print('Nb of clusters - at least one above 10 billions :', unique_clust[unique_clust.category=='at least one above 10 billions'].shape[0],'(Significant:', unique_clust[(unique_clust.category=='at least one above 10 billions') & (unique_clust.p_value<=0.05)].shape[0],')')
print('Nb of clusters - NA :', unique_clust[unique_clust.category.isna()].shape[0])

#Merge firstCases with unique clusters info
firstCases=pd.merge(firstCases,unique_clust[['cluster','end_date','category']].reset_index(drop=True),how='inner',on=['cluster','end_date'])

#Convert to geodataframe
firstCases=gpd.GeoDataFrame(firstCases,crs="EPSG:4326", geometry='geometry')

#Save file
if os.path.exists(outdir+'clusters_firstCases.gpkg'):
    print('File already exists. Deleted.')
    os.remove(outdir+'clusters_firstCases.gpkg')
firstCases.to_file(outdir+'clusters_firstCases.gpkg',driver='GPKG')


#Drop duplicated geometries by keeping the first apparition
#data=data.drop_duplicates(subset='geometry',keep='first')



polygons=data.geometry.tolist()

non_overlapping = []
for n, p in enumerate(polygons[:-1], 1):
    if not any(p.overlaps(g) for g in polygons[n:]):
        non_overlapping.append(p)

len(non_overlapping)
data.to_file(outdir+'aa.gpkg',driver='GPKG')
