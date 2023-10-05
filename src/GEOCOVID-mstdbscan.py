#GEOCOVID-mstdbscan.py

#WARNING: results will not be the same as in the paper (Louvain algorithm)

#LIBRARIES
#Basic
import pandas as pd
import calendar
import os
from datetime import date, timedelta
import math
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import patches as mpatches
import matplotlib.dates as mdates
from matplotlib.dates import MO
#Database
import getpass
from sqlalchemy import create_engine
import psycopg2 as ps
#Spatial
import geopandas as gpd
import pysda

output_path='outputs/COVID_MSTDBSCAN/ByDays_1km/'

#CONNECT TO DB WITH user=aladoy
pw=getpass.getpass() #Ask for user password
engine=create_engine("postgresql+psycopg2://aladoy:{}@localhost/geocovid".format(pw)) #Create SQLAlchemy engine
conn=ps.connect("dbname='geocovid' user='aladoy' host='localhost' password='{}'".format(pw)) #Create a connection object
cursor=conn.cursor() #Create a cursor object

#Read COVID tests data for canton of VD
covid=gpd.read_postgis('SELECT * FROM covid_tests_vd',conn,geom_col='geometry',crs=2056)
#Check if we can consider date_reception as the date of testing
cursor.execute('SELECT * FROM covid_tests_vd WHERE date_prelevement <> date_reception')
cursor.fetchall()

#Extract COVID daily stats for the whole time period
sql='SELECT date_reception as date, count(*) as Ntests, sum(res_cov) as Ncases FROM covid_tests_vd GROUP BY date_reception'
covid_stats=pd.read_sql(sql,conn)
#Plot COVID tests statistics
plt.style.use('ggplot')
ax = plt.gca()
covid_stats.plot(kind='line',x='date',y='ntests',ax=ax,figsize=(20,10),color='black')
covid_stats.plot(kind='line',x='date',y='ncases', color='red', ax=ax)
plt.title('COVID tests in the canton of Vaud for the whole time period')
plt.savefig(output_path+'covid_statistics.png',dpi = 180,bbox_inches = 'tight')
plt.show()


#MST-DBSCAN

#Select cases
sql='SELECT id_demande, date_reception as date, geometry FROM covid_tests_vd WHERE res_cov=1'
cases=gpd.read_postgis(sql,conn, geom_col='geometry')
cases.head()

#Convert date to string
cases['date']=cases['date'].dt.strftime('%Y-%m-%d')
#Import data for pysda package
pysda_data = pysda.data.readGDF(cases, timeColumn="date", timeUnit="day")
#Initialize instance
mst = pysda.MSTDBSCAN(pysda_data)

#Set params MSTDBSCAN
eps_spatial = 1000 #spatial search radius
eps_temporalLow = 0 #min value temporal window
eps_temporalHigh = 14 #max value temporal window
min_pts = 3 #min neighbors for a point to become a core
movingRatio = 0.1 #threshold value to check whether a cluster's center moves
areaRatio = 0.1 #threshold value to check whether a cluster's area changes
mst.setParams(eps_spatial, eps_temporalLow, eps_temporalHigh, min_pts, movingRatio, areaRatio)

#Start clustering
mst.run()
result = mst.result
#Get results
clusterGDF = result.clusters

#GET DIFFUSION ZONES

#Load polygon data for plotting
#polygonGDF=gpd.read_postgis("SELECT uuid, name, geometry FROM municipalities WHERE canton_num=22 AND name NOT LIKE 'Lac %'",conn,geom_col='geometry')
polygonGDF=gpd.read_postgis("SELECT DISTINCT n.LCID,n.locality,n.geometry FROM npa n, (SELECt * FROM cantons where name='Vaud') c WHERE ST_Overlaps(n.geometry, c.geometry) OR ST_Within(n.geometry,c.geometry)", conn, geom_col='geometry')


#Add polygon data to determine diffusion zones
result.setPolygons(polygonGDF)
#Convert DZ to category
polygonGDF['DZ']=polygonGDF['DZ'].astype('category')

#Get results by polygons
polygonResultGDF = result.polygons
polygonResultGDF.head(10)

#Change diffusion zones to start at 1
polygonResultGDF['DZ'] +=1

#Change value of DZ to "no clusters" if no clusters for the entire period
polygonResult=pd.DataFrame(polygonResultGDF.iloc[:,5:polygonResultGDF.shape[1]])
polygonResultGDF.loc[polygonResult[polygonResult.apply(pd.Series.nunique,axis=1)==1].index,'DZ']='no cluster'

#Print unique diffusion zones
print('Number of unique DZ (including "no cluster"): ' + str(polygonResultGDF.DZ.unique().shape[0]))
print('List of DZ: ' + str(polygonResultGDF.DZ.unique()))

#Plot diffusion zones
#Define colors for diffusion zones
colors_dz = {1:'#A0CF8D', 2:'#FFC04C', 3:'#B0E0E6','no cluster':'#cccccc'}
dz1_patch = mpatches.Patch(color="#A0CF8D", label='Zone 1')
dz2_patch = mpatches.Patch(color="#FFC04C", label='Zone 2')
dz3_patch = mpatches.Patch(color="#B0E0E6", label='Zone 3')
dznoclust_patch=mpatches.Patch(color="#cccccc", label='No cluster')
fig, ax = plt.subplots(figsize=(12,12))
polygonResultGDF.plot(color=polygonResultGDF['DZ'].map(colors_dz), linewidth=.6, edgecolor='0.2', legend=True, ax=ax)
ax.legend(handles=[dz1_patch,dz2_patch,dz3_patch,dznoclust_patch])
plt.axis('off')
plt.savefig(output_path+"diffusion_zones_npa.png",bbox_inches='tight')
plt.show()

# 4:'#b266b2' dz4_patch = mpatches.Patch(color='#b266b2', label='Zone 4')

#PLOT EVOLUTION TYPE FOR EACH DIFFUSION ZONE
plt.style.use('ggplot')
plt.rcParams['axes.grid.which']='both'


for dz in polygonResultGDF.DZ.unique():
    d=polygonResultGDF[polygonResultGDF.DZ==dz].iloc[:,4:polygonResultGDF.shape[1]] #Select only rows for given diffusion zone
    d=pd.melt(d) #Reshape dataframe
    d.columns=['time','Evolution type']
    d=d[d['Evolution type']!='no cluster'] #Remove no cluster evolution type
    #Compute frequency for each evolution type by day
    d_stats=d.groupby(['time', 'Evolution type']).size().reset_index(name='evolution_count')
    s = d['Evolution type'].value_counts()
    d_stats['evolution_count'] = d_stats['evolution_count'].div(d_stats['Evolution type'].map(s))
    d_stats['time']=pd.to_datetime(d_stats.time,format='%Y/%m/%d-%H:%M:%S') #Convert time to datetime

    #Plot
    fig, ax = plt.subplots(figsize=(10,6))
    ax=sns.lineplot(data=d_stats, x='time', y='evolution_count',hue='Evolution type')
    ax.set(ylim=(0, 0.15))
    plt.xlabel('Date')
    plt.ylabel('Mean frequency of evolution types for postal codes')
    ax.set_xlim(pd.Timestamp('2020-03-04'), pd.Timestamp('2020-06-30'))
    ax.axvline(pd.to_datetime('2020-03-16'), color='black', linestyle=':', lw=2, label='Lockdown period (March 16 - April 27)')
    ax.axvline(pd.to_datetime('2020-04-27'), color='black', linestyle=':', lw=2)
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=MO,interval=2))
    ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=MO,interval=1))
    plt.xlim([pd.to_datetime('2020-02-29'),pd.to_datetime('2020-07-03')])
    #plt.title('Evolution type, Diffusion Zone ' + str(dz),fontsize=18)
    plt.legend(prop={'size': 14})
    plt.savefig(output_path+"evolution_type_dz"+str(dz)+".png",bbox_inches='tight')


#Convert results (same category as David D. Ridder)
clusterGDF['mstDate'] = pd.to_datetime(clusterGDF['mstDate'])
clusterGDF.loc[clusterGDF['type'] == 'Directional growth','type'] = 'Growth'
clusterGDF.loc[clusterGDF['type'] == 'Directional reduction','type'] = 'Reduction'
clusterGDF.loc[clusterGDF['type'] == 'SplitMerge','type'] = 'Move'
colors_cl = {'Emerge':'#fb9a99', 'Growth':'#e31a1c','Steady':'#33a02c', 'Merge':'#ffffb3','Move':'#fdb462','Split':'#bebada','Reduction':'#1f78b4'}
hfont = {'fontname':'Helvetica'}
###LEGEND PATCHES###
emerge_patch = mpatches.Patch(color="#fb9a99", label='Emerge')
growth_patch = mpatches.Patch(color="#e31a1c", label='Growth')
steady_patch = mpatches.Patch(color="#33a02c", label='Steady')
merge_patch = mpatches.Patch(color="#ffffb3", label='Merge')
move_patch = mpatches.Patch(color="#fdb462", label='Move')
split_patch = mpatches.Patch(color="#bebada", label='Split')
reduction_patch = mpatches.Patch(color="#1f78b4", label='Reduction')

startDate=min(clusterGDF.mstDate)
endDate=max(clusterGDF.mstDate)

theDate=startDate
while theDate <= endDate:
    part=clusterGDF[clusterGDF["mstDate"] == theDate]

    try:
        fig, ax = plt.subplots(figsize=(15,20))
        fig.patch.set_facecolor('white')
        ax.set_aspect("equal")
        ax.set_title("MST-DBSCAN clusters of COVID-19 confirmed cases in the canton of Vaud on {}".format(part.mstDate.values[0]),size=18)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_axis_off()
        ax.legend(handles=[emerge_patch, growth_patch, steady_patch,reduction_patch, merge_patch,move_patch,split_patch])
        mun.plot(ax=ax, color="#e5e5e5", edgecolor='#b2b2b2')
        part.plot(color = part['type'].map(colors_cl),ax = ax,alpha = 0.8,linewidth = 0.5,legend = True,zorder=1)
        plt.savefig(output_path+'mstdbscan_clusters_'+str(theDate)+'.png',dpi = 180,bbox_inches = 'tight',facecolor=fig.get_facecolor())
        plt.show()
    except:
        print(theDate)

    theDate=theDate+timedelta(days=1)

#Save clusters
if os.path.exists(output_path+'clusterGDF.gpkg'):
    print('File already exists. Deleted.')
    os.remove(output_path+'clusterGDF.gpkg')
clusterGDF.to_file(output_path+'clusterGDF.gpkg',driver='GPKG')
#Save diffusion zone
if os.path.exists(output_path+'diffusionZones.gpkg'):
    print('File already exists. Deleted.')
    os.remove(output_path+'diffusionZones.gpkg')
polygonResultGDF.to_file(output_path+'diffusionZones.gpkg',driver='GPKG')


# #FOR WEEKS
# clusterGDF['week']=clusterGDF.mstDate.dt.isocalendar().week.astype('int')
# for i in range(min(clusterGDF.week),max(clusterGDF.week)+1,1):
#     part=clusterGDF[clusterGDF["week"] == i]
#     fig, ax = plt.subplots(figsize=(15,20))
#     fig.patch.set_facecolor('white')
#     ax.set_aspect("equal")
#     ax.set_title("MST-DBSCAN clusters of COVID-19 confirmed cases in the canton of Vaud in the week starting from {}".format(part.mstDate.values[0]),size=18)
#     ax.set_xticks([])
#     ax.set_yticks([])
#     ax.set_axis_off()
#     ax.legend(handles=[emerge_patch, growth_patch, steady_patch,reduction_patch, merge_patch,move_patch,split_patch])
#     mun.plot(ax=ax, color="#e5e5e5", edgecolor='#b2b2b2')
#     part.plot(color = part['type'].map(colors_cl),ax = ax,alpha = 0.8,linewidth = 0.5,legend = True,zorder=1)
#     plt.savefig(output_path+'mstdbscan_clusters_week'+str(i)+'.png',dpi = 180,bbox_inches = 'tight',facecolor=fig.get_facecolor())
#     plt.show()
