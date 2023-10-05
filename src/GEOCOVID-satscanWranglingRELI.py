#LIBRARIES
#Basic
import pandas as pd
import matplotlib.pyplot as plt
import calendar
import os
from datetime import date
#Database
import getpass
from sqlalchemy import create_engine
import psycopg2 as ps
#Spatial
import geopandas as gpd

#Choose the software you'll use for analysis (rsatscan requires that population data contain dates while satscan does not)
soft='rsatscan' #or satscan

#CONNECT TO DB WITH user=aladoy
pw=getpass.getpass() #Ask for user password
engine=create_engine("postgresql+psycopg2://aladoy:{}@localhost/geocovid".format(pw)) #Create SQLAlchemy engine
conn=ps.connect("dbname='geocovid' user='aladoy' host='localhost' password='{}'".format(pw)) #Create a connection object
cursor=conn.cursor() #Create a cursor object

#EXTRACT DATA
#RELI geometry + population (control data)
ha=gpd.read_postgis("SELECT DISTINCT s.reli,s.b19btot,st_transform(s.geometry,4326) as geometry FROM statpop_centroid s,  (SELECT geometry FROM cantons where name='Vaud') vd WHERE ST_Intersects(vd.geometry, s.geometry)", conn, geom_col='geometry')

#COVID tests (cases data)
sql="SELECT s.reli, c.date_reception as date, CAST(sum(c.res_cov) AS Integer) as Ncov_cases, count(*) as Ncov_tests FROM covid_tests_vd c INNER JOIN statpop_centroid s ON s.reli=c.corresponding_reli GROUP BY s.reli ,c.date_reception"
covid=pd.read_sql(sql,conn)


if soft=='rsatscan':
    # #CROSS JOIN BETWEEN RELI + COVID (FOR RSATSCAN)
    ha_j=pd.DataFrame(ha)
    ha_j['key']=1
    date=pd.Series(covid.date.unique()).to_frame(name='date')
    date['key']=1
    ha_date = pd.merge(ha_j, date, on ='key').drop("key", 1)
    # #Add covid data
    satscan=pd.merge(ha_date,covid,on=['reli','date'],how='left')
    satscan['ncov_tests']=satscan.ncov_tests.fillna(value=0)
    satscan['ncov_cases']=satscan.ncov_cases.fillna(value=0)
    satscan=satscan.convert_dtypes() #Convert to float to int
    satscan['month']=satscan.date.dt.month #Add month
    satscan['week']=satscan.date.dt.isocalendar().week
    satscan=gpd.GeoDataFrame(satscan,crs="EPSG:4326", geometry='geometry')
    satscan['x']=satscan.geometry.x
    satscan['y']=satscan.geometry.y

    #Add month / week information to covid data
    covid['month']=covid.date.dt.month #Add month
    covid['week']=covid.date.dt.isocalendar().week #Add week

    #Add lat / lon to ha
    ha['x']=ha.geometry.x
    ha['y']=ha.geometry.y

    #Split date between cases,at-risk population and geo
    cases=satscan[satscan.ncov_cases>0][['reli','date','ncov_cases','month','week']]
    population=satscan[['reli','date','b19btot']]
    geo=ha[['reli','x','y']]

else:
    #Add month / week information to covid data
    covid['month']=covid.date.dt.month #Add month
    covid['week']=covid.date.dt.isocalendar().week #Add week

    #Add lat / lon to ha
    ha['x']=ha.geometry.x
    ha['y']=ha.geometry.y

    #Split date between cases,at-risk population and geo
    cases=covid[covid.ncov_cases>0][['reli','date','ncov_cases','month','week']]
    population=ha[['reli','b19btot']]
    geo=ha[['reli','x','y']]


#SAVE FOR ENTIRE PERIOD
path_all='outputs/COVID_satscan/ByRELI/ByDays/'
geo.to_csv(path_all+'geo_reli_satscan.csv', index=False) #Save geographical coordinates (same for all the days)
cases.to_csv(path_all+'cases.csv', index=False)
population.to_csv(path_all+'population.csv', index=False)
