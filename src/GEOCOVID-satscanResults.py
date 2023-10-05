#GEOCOVID-satscanR.py

import json
import geopandas as gpd
import numpy as np
import pandas as pd
import os
import math
import getpass
from sqlalchemy import create_engine
import psycopg2 as ps
import calendar
from datetime import date
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.dates as mdates
from matplotlib.dates import MO

outdir='/mnt/data/GEOSAN/RESEARCH PROJECTS/GEOCOVID @ CHUV/GEOCOVID-phase1/results/COVID_satscan/ByRELI/ByDays/'

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


print('Total number of clusters: ', data.shape[0])
print('Total number of significant clusters: ', data[data.p_value<=0.05].shape[0])

#Add clusters duration (in days)
data['duration']=data['end_date']-data['start_date']
data['duration']=data['duration'].apply(lambda x: x / np.timedelta64(1,'D'))+1 #convert timedelta to integer

#CONNECT TO DB WITH user=aladoy
pw=getpass.getpass() #Ask for user password
engine=create_engine("postgresql+psycopg2://aladoy:{}@localhost/geosan".format(pw)) #Create SQLAlchemy engine
conn=ps.connect("dbname='geosan' user='aladoy' host='localhost' password='{}'".format(pw)) #Create a connection object
cursor=conn.cursor() #Create a cursor object
#Read RELI used in satscan analysis
ha=gpd.read_postgis("SELECT DISTINCT s.reli,s.b19btot,st_transform(s.geometry,4326) as geometry FROM statpop_centroid s,  (SELECT geometry FROM cantons where name='Vaud') vd WHERE ST_Intersects(vd.geometry, s.geometry)", conn, geom_col='geometry')

#Add fields for significancy + unique ID before importing into DB
data['significant']=np.where(data['p_value']<=0.05, True, False)
data.reset_index(drop=False,inplace=True)
data.rename(columns = {'index':'id'}, inplace = True)
data=data.to_crs({'init': 'epsg:2056'}) #change CRS

#ADD SATSCAN CLUSTERS TO DB
data.to_postgis('satscan_clusters_firstvague', engine,schema='geocovid',if_exists='replace') #Add to postgis
conn.commit()
data.to_postgis('s1_satscan_clusters', engine,schema='geocovid',if_exists='replace') #Add to postgis
conn.commit()
cursor.execute("SELECT COUNT(*) FROM satscan_clusters_firstvague")
print("Number of rows in the table :", cursor.fetchone()) #Check that the result is 1684
cursor.execute("ALTER TABLE satscan_clusters_firstvague ADD PRIMARY KEY(id);") #Add PK
conn.commit()
cursor.execute("CREATE INDEX idx_geom_satscan_clusters_firstvague ON satscan_clusters_firstvague USING GIST(geometry);")
conn.commit()

#PLOTS

plt.style.use('ggplot')
plt.rcParams['axes.grid.which']='both'

#NUMBER OF CLUSTERS
#Significant + non significant
fig, ax = plt.subplots(figsize=(12,5))
ax=sns.lineplot(data.groupby(['end_date']).count()['cluster'].index, data.groupby(['end_date']).count()['cluster'].values, color='#2323B2',marker='o', label='All clusters')
ax=sns.lineplot(data[data.p_value>0.05].groupby(['end_date']).count()['cluster'].index, data[data.p_value>0.05].groupby(['end_date']).count()['cluster'].values, color='#999999',marker='o', label='Non significant clusters')
ax=sns.lineplot(data[data.p_value<=0.05].groupby(['end_date']).count()['cluster'].index, data[data.p_value<=0.05].groupby(['end_date']).count()['cluster'].values, color='#E71919',marker='o', label='Significant clusters')
plt.xlabel('Date')
plt.ylabel('Number of case clusters')
ax.axvline(pd.to_datetime('2020-03-16'), color='black', linestyle=':', lw=2, label='Lockdown period (March 16 - April 27)')
ax.axvline(pd.to_datetime('2020-04-27'), color='black', linestyle=':', lw=2)
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=MO,interval=2))
ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=MO,interval=1))
xmin_fig1_2, xmax_fig1_2 = ax.get_xlim()
#plt.title('Number of COVID-19 case clusters',fontsize=18)
plt.legend()
plt.savefig(outdir+"tot_case_clusters.svg",bbox_inches='tight')

#NUMBER OF CASES
nb_cases=pd.read_sql_query("SELECT date_reception, SUM(res_cov) AS nb_cases, SUM(res_cov)*100/COUNT(res_cov) as taux_pos FROM covid_tests_vd GROUP BY date_reception", conn)
nb_cases=nb_cases[nb_cases.date_reception>='2020-03-02'] #Start with the first case
fig, ax = plt.subplots(figsize=(12,5))
ax=sns.lineplot(data=nb_cases, x='date_reception', y='nb_cases',color='#011f4b')
ax.set_xlabel("Date")
ax.set_ylabel("New cases", color='#011f4b')
ax2=ax.twinx()
ax2=sns.lineplot(data=nb_cases, x='date_reception', y='taux_pos',color='#6497b1')
ax2.set_ylabel('Percent positive', color='#6497b1')
ax.axvline(pd.to_datetime('2020-03-16'), color='black', linestyle=':', lw=2, label='Lockdown period (March 16 - April 27)')
ax.axvline(pd.to_datetime('2020-04-27'), color='black', linestyle=':', lw=2)
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=MO,interval=2))
ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=MO,interval=1))
plt.xlim([xmin_fig1_2,xmax_fig1_2]) #align with other figures of panel 1 #align with other figures of panel 1
plt.savefig(outdir+"cases_percent_pos.svg",bbox_inches='tight')


#RELATIVE RISK
#Significant (keep only clusters with > 10 cases)
fig, ax = plt.subplots(figsize=(12,5))
ax=sns.lineplot(data=data[(data.p_value<=0.05) & (data.observed>=8)], x='end_date', y='rel_risk',color='#5bc0de', marker='o',label='Clusters with > 8 cases')
ax=sns.lineplot(data=data[(data.p_value<=0.05) & (data.observed>=10)], x='end_date', y='rel_risk',color='#5cb85c', marker='o',label='Clusters with > 10 cases')
ax=sns.lineplot(data=data[(data.p_value<=0.05) & (data.observed>=12)], x='end_date', y='rel_risk',color='#d9534f', marker='o',label='Clusters with > 12 cases')
plt.xlabel('Date')
plt.ylabel('Relative risk')
ax.axvline(pd.to_datetime('2020-03-16'), color='black', linestyle=':', lw=2, label='Lockdown period (March 16 - April 27)')
ax.axvline(pd.to_datetime('2020-04-27'), color='black', linestyle=':', lw=2)
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=MO,interval=2))
ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=MO,interval=1))
plt.xlim([xmin_fig1_2,xmax_fig1_2]) #align with other figures of panel 1
plt.legend(loc=4)
#plt.title('Average relative risk (RR) in significant COVID-19 case clusters',fontsize=18)
plt.savefig(outdir+"rr_case_clusters_significant_05.svg",bbox_inches='tight')

#POPULATION IN CLUSTERS
fig, ax = plt.subplots(figsize=(12,5))
ax=sns.lineplot(data=data[data.p_value>0.05], x='end_date', y='population',color='#999999', marker='o',label='Non significant clusters') #non significant
ax=sns.lineplot(data=data[data.p_value<=0.05], x='end_date', y='population',color='#E71919', marker='o', label='Significant clusters') #significant
plt.axhline(y=sum(ha.b19btot)*0.005, linestyle='-',color='black',label='Maximum cluster size')
plt.xlabel('Date')
plt.ylabel('Within-clusters population')
ax.axvline(pd.to_datetime('2020-03-16'), color='black', linestyle=':', lw=2, label='Lockdown period (March 16 - April 27)')
ax.axvline(pd.to_datetime('2020-04-27'), color='black', linestyle=':', lw=2)
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=MO,interval=2))
ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=MO,interval=1))
# ax.annotate('no significant clusters',
#             xy=(pd.to_datetime('2020-05-26'), 400), xycoords='data',
#             xytext=(0, 30), textcoords='offset points',
#             fontsize=10, ha='center', va='center',
#             arrowprops=dict(arrowstyle='-[, widthB=14.5, lengthB=1.2', lw=2.0,color='black'))
plt.legend(loc=1)
#plt.title('Population within significant COVID-19 case clusters',fontsize=18)
plt.savefig(outdir+"avg_population_case_clusters.svg",bbox_inches='tight')


#OBSERVED CASES IN CLUSTERS
#COVID tests (cases data)
sql="SELECT c.date_reception as date, CAST(sum(c.res_cov) AS Integer) as Ncov_cases FROM covid_tests_vd c INNER JOIN statpop_centroid s ON s.reli=c.corresponding_reli WHERE res_cov=1 GROUP BY c.date_reception"
cases=pd.read_sql(sql,conn)
cases['cumsum_ncov_cases']=cases.ncov_cases.cumsum() #Cumulative sum

fig, ax = plt.subplots(figsize=(12,5))
ax=sns.lineplot(data=data[data.p_value>0.05], x='end_date', y='observed',color='#999999', marker='o',label='Non significant clusters') #non significant
ax=sns.lineplot(data=data[data.p_value<=0.05], x='end_date', y='observed',color='#E71919', marker='o', label='Significant clusters')
ax.axvline(pd.to_datetime('2020-03-16'), color='black', linestyle=':', lw=2, label='Lockdown period (March 16 - April 27)')
ax.axvline(pd.to_datetime('2020-04-27'), color='black', linestyle=':', lw=2)
# ax.annotate('no significant clusters',
#             xy=(pd.to_datetime('2020-05-26'), 6.5), xycoords='data',
#             xytext=(0, 30), textcoords='offset points',
#             fontsize=10, ha='center', va='center',
#             arrowprops=dict(arrowstyle='-[, widthB=14.5, lengthB=1.2', lw=2.0,color='black'))
plt.xlabel('Date')
plt.ylabel('Within-clusters cases')
plt.legend()
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=MO,interval=2))
ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=MO,interval=1))
#plt.title('COVID-19 cases within significant clusters',fontsize=18)
plt.savefig(outdir+"observed_case_clusters.svg",bbox_inches='tight')


# #peak of within-cluster cases for significant clusters
# a=data[data.p_value<=0.05].groupby(['end_date']).mean()['observed']
# max(a)
# a.idxmax()
# data[data.p_value<=0.05].loc[data[data.p_value<=0.05].observed.idxmax()]
#
# #peak of within-cluster cases for non significant clusters
# b=data[data.p_value>0.05].groupby(['end_date']).mean()['observed']
# max(b)
# b.idxmax()
# data[data.p_value>0.05].loc[data[data.p_value>0.05].observed.idxmax()]
# a.head(35)

#CLUSTERS DURATION

#Significant
fig, ax = plt.subplots(figsize=(12,5))
ax=sns.lineplot(data=data[data.p_value>0.05], x='end_date', y='duration',color='#999999', marker='o',label='Non significant clusters') #non significant
ax=sns.lineplot(data=data[data.p_value<=0.05], x='end_date', y='duration',color='#E71919', marker='o', label='Significant clusters')
plt.xlabel('Date')
plt.ylabel('Cluster duration [days]')
ax.axvline(pd.to_datetime('2020-03-16'), color='black', linestyle=':', lw=2, label='Lockdown period (March 16 - April 27)')
ax.axvline(pd.to_datetime('2020-04-27'), color='black', linestyle=':', lw=2)
# ax.annotate('no significant clusters',
#             xy=(pd.to_datetime('2020-05-26'),12), xycoords='data',
#             xytext=(0, -30), textcoords='offset points',
#             fontsize=10, ha='center', va='center',
#             arrowprops=dict(arrowstyle='-[, widthB=14.5, lengthB=1.2', lw=2.0,color='black'))
#plt.legend()
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=MO,interval=2))
ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=MO,interval=1))
#plt.title('Average duration of significant COVID-19 case clusters',fontsize=18)
plt.savefig(outdir+"average_duration_case_clusters.svg",bbox_inches='tight')


#AVERAGE CLUSTERS RADIUS
data["radius"] = data.to_crs('EPSG:2056')['geometry'].apply(lambda x: np.sqrt(x.area/math.pi))
# #Significant
# fig, ax = plt.subplots(figsize=(17,10))
# ax=sns.lineplot(data=data[data.p_value<=0.05], x='end_date', y='radius',color='#E71919')
# plt.xlabel('Date',fontsize=14)
# plt.ylabel('Radius [m]',fontsize=14)
# ax.axvline(pd.to_datetime('2020-03-19'), color='black', linestyle='-', lw=2, label='Lockdown')
# ax.axvline(pd.to_datetime('2020-04-27'), color='black', linestyle='-', lw=2)
# plt.legend()
# plt.title('Average radius of significant COVID-19 case clusters',fontsize=18)
# plt.savefig(outdir+"avg_radius_case_clusters_significant_05.png",bbox_inches='tight')

# #NUMBER OF HECTARES IN CLUSTERS
# #Significant
# fig, ax = plt.subplots(figsize=(17,10))
# ax=sns.lineplot(data=data, x='end_date', y='number_loc',color='#E71919')
# plt.xlabel('Date',fontsize=14)
# plt.ylabel('Count',fontsize=14)
# plt.title('Number of hectares within significant COVID-19 case clusters',fontsize=18)
# plt.savefig(outdir+"nb_ha_case_clusters_significant_05.png",bbox_inches='tight')

# #PER REGION
# #Vallée-de-Joux
# vj=gpd.read_postgis("SELECT lcid, locality, mdname, st_transform(geometry,4326) as geometry FROM npa WHERE mdname='Vallée-de-Joux'",conn, geom_col='geometry')
# data_vj=gpd.sjoin(data, vj, how='inner', op='intersects')
# data_vj['region']='Vallée-de-Joux'
# #Lausanne
# l=gpd.read_postgis("SELECT lcid, locality, mdname, st_transform(geometry,4326) as geometry FROM npa WHERE mdname='Lausanne Ville'",conn, geom_col='geometry')
# data_l=gpd.sjoin(data, l, how='inner', op='intersects')
# data_l['region']='Lausanne'
# #Mézières/ Les Cullayes
# m=gpd.read_postgis("SELECT lcid, locality, mdname, st_transform(geometry,4326) as geometry FROM npa WHERE locality='Les Cullayes' OR locality='Mézières VD'",conn, geom_col='geometry')
# data_m=gpd.sjoin(data, m, how='inner', op='intersects')
# data_m['region']='Mézières'
# data_regions=data_vj.append(data_l).append(data_m)
# fig, ax = plt.subplots(figsize=(17,10))
# ax=sns.histplot(data=data_regions[data_regions.p_value<=0.05],x='duration', hue='region',element="step")
# # ax=sns.displot(data[data.p_value<=0.05]['duration'], color="#000000", label='VD')
# # ax=sns.displot(data_m[data_m.p_value<=0.05]['duration'], color="#f37736", label='Mézières / Les Cullayes')
# # ax=sns.displot(data_vj[data_vj.p_value<=0.05]['duration'], color="#0392cf", label='Vallée de Joux')
# # ax=sns.displot(data_l[data_l.p_value<=0.05]['duration'], color="#ee4035", label='Lausanne')
# plt.xlabel('Duration [days]')
# plt.ylabel('Cases [-]')
# plt.savefig(outdir+"distribution_case_cluster_duration_region.png",bbox_inches='tight')
#

#VIRAL LOAD
cases=gpd.read_postgis("SELECT c.id_demande, c.date_reception, c.age, c.ct, c.charge_virale, st_transform(st_buffer(s.geometry,0.2),4326) as geometry FROM covid_tests_vd c INNER JOIN statpop_centroid s ON s.reli=c.corresponding_reli WHERE res_cov=1",conn, geom_col='geometry')
viral_load=gpd.sjoin(data, cases, how='left', op='intersects') #Spatial join between cases and clusters
#Keep only individuals that are tested during cluster duration
viral_load=viral_load[(viral_load.date_reception>=viral_load.start_date) & (viral_load.date_reception<=viral_load.end_date)]
#Convert age "ND" to nan
viral_load.loc[viral_load.age=='ND','age']=np.nan
viral_load['age']=viral_load.age.astype('float') #Convert to float

# t=pd.DataFrame(viral_load.groupby(['cluster','end_date','observed']).size()).reset_index()
# t.columns=['cluster','end_date','observed','nb_points']
# t[(t.observed==t.nb_points)==False] #We choose a buffer value that minimize the number of rows


#CLASSIFY SaTScan CLUSTERS BASED ON VIRAL LOAD CATEGORIES (defined by G.Greub)
unique_clust=viral_load.drop_duplicates(subset=['cluster','end_date']) #List of unique clusters (should be equal to 1684)
unique_clust.shape

for index,row in unique_clust.iterrows(): #non overlapping categories if we use elif

    cluster=viral_load[(viral_load.cluster==unique_clust.loc[index,'cluster']) & (viral_load.end_date==unique_clust.loc[index,'end_date'])]

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

#Count nb of clusters (all) in each category
nb_clusters_all= unique_clust.groupby(['category'])['cluster'].size()
nb_clusters_all=pd.DataFrame(nb_clusters_all).reset_index(drop=False)
nb_clusters_all.columns=['category','count_all']
nb_clusters_signif= unique_clust[unique_clust.p_value<=0.05].groupby(['category'])['cluster'].size()
nb_clusters_signif=pd.DataFrame(nb_clusters_signif).reset_index(drop=False)
nb_clusters_signif.columns=['category','count_signif']
nb_clusters=pd.merge(nb_clusters_all,nb_clusters_signif,on='category')
nb_clusters

#Cross join with dates and category
a=pd.DataFrame({'key':pd.Series([1]*len(unique_clust.end_date.unique())),'end_date':pd.Series(unique_clust.end_date.unique())})
b=pd.DataFrame({'key':pd.Series([1]*len(unique_clust.category.unique())),'category':pd.Series(unique_clust.category.unique())})
ab = pd.merge(a, b, on ='key').drop("key", 1)

#Keep only significant unique clusters
unique_clust_signif=unique_clust[unique_clust.p_value<=0.05]
unique_clust_signif['count'] = unique_clust_signif.groupby(['category','count_all'])['cluster'].transform(len)

#Count number of clusters in each category
res=unique_clust_signif.groupby(['end_date','category']).size().reset_index() #only significant clusters
res.columns=['end_date','category','count']
res=pd.merge(ab,res,how='left',on=['end_date','category'])
res['count']=res['count'].fillna(value=0)
res=pd.merge(res,nb_clusters,how='inner',on=['category'])

#Create labels for plot (significant clusters only)
res['clust_cat_label']=res['category']+' (n='+ res['count_signif'].astype('int').astype(str)+', '+round((res['count_signif']*100/res['count_all']),2).astype(str)+'%)'

#PLOT CLUSTER CATEGORY
#  Returns tuple of handles, labels for axis ax, after reordering them to conform to the label order `order`, and if unique is True, after removing entries with duplicate labels.
def reorderLegend(ax=None,order=None,unique=False):
    if ax is None: ax=plt.gca()
    handles, labels = ax.get_legend_handles_labels()
    labels, handles = zip(*sorted(zip(labels, handles), key=lambda t: t[0])) # sort both labels and handles by labels
    if order is not None: # Sort according to a given list (not necessarily complete)
        keys=dict(zip(order,range(len(order))))
        labels, handles = zip(*sorted(zip(labels, handles), key=lambda t,keys=keys: keys.get(t[0],np.inf)))
    if unique:  labels, handles= zip(*unique_everseen(zip(labels,handles), key = labels)) # Keep only the first of each handle
    ax.legend(handles, labels)
    return(handles, labels)
def unique_everseen(seq, key=None):
    seen = set()
    seen_add = seen.add
    return [x for x,k in zip(seq,key) if not (k in seen or seen_add(k))]
#Plot cluster category
color_dict=dict({'all below 1 million (n=33, 31.13%)':'#66b266','at least one between 1 million and 10 millions (n=23, 17.97%)':'#4f5bd5','at least one between 10 millions and 100 millions (n=13, 10.4%)':'#962fbf','at least one between 100 millions and 1 billion (n=128, 19.42%)':'#fa7e1e','at least one between 1 billion and 10 billions (n=251, 39.47%)':'#ffa7b6','at least one above 10 billions (n=9, 30.0%)':'#ff1919'})
#color_dict=dict({'all below 1 million (n=106)':'#66b266','at least one between 1 million and 10 millions (n=128)':'#4f5bd5','at least one between 10 millions and 100 millions (n=125)':'#962fbf','at least one between 100 millions and 1 billion (n=659)':'#fa7e1e','at least one between 1 billion and 10 billions (n=636)':'#ffa7b6','at least one above 10 billions (n=30)':'#ff1919'})
fig, ax = plt.subplots(figsize=(13,8))
sns.lineplot(data=res, x='end_date', y='count', hue='clust_cat_label',palette=color_dict)
ax.axvline(pd.to_datetime('2020-03-16'), color='black', linestyle=':', lw=2,label='Lockdown period (March 16 - April 27)')
ax.axvline(pd.to_datetime('2020-04-27'), color='black', linestyle=':', lw=2)
reorderLegend(ax,['all below 1 million (n=33, 31.13%)', 'at least one between 1 million and 10 millions (n=23, 17.97%)', 'at least one between 10 millions and 100 millions (n=13, 10.4%)', 'at least one between 100 millions and 1 billion (n=128, 19.42%)', 'at least one between 1 billion and 10 billions (n=251, 39.47%)', 'at least one above 10 billions (n=9, 30.0%)','Lockdown period (March 16 - April 27)'])
plt.ylabel('Number of clusters')
plt.xlabel('Date')
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=MO,interval=2))
ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=MO,interval=1))
plt.yticks(np.arange(min(res['count']), max(res['count'])+1, 2.0))
plt.savefig(outdir+"clusters_category.png",bbox_inches='tight')

#FIRST 3 CASES BY CLUSTER
firstCases=viral_load[viral_load.p_value<=0.05].sort_values(['cluster','end_date','duration','population','observed','date_reception','p_value'])
firstCases=firstCases.groupby(['cluster','end_date','duration','population','observed','p_value']).head(3).reset_index(drop=True)
firstCases=pd.merge(firstCases,unique_clust[unique_clust.p_value<=0.05][['cluster','end_date','category']].reset_index(drop=True).reset_index(),how='inner',on=['cluster','end_date'])

#Save first 3 cases for each significant clusters (send to G. Greub)
firstCasesGG=firstCases[['index','cluster','start_date','end_date','category','duration','observed','expected','rel_risk','population','p_value','id_demande','date_reception','age','ct','charge_virale','latitude','longitude']]
firstCasesGG.columns=['clusterID','clusterID2','startDate','endDate','category','duration','observedCases','expectedCases','RR','popInside','clusterPvalue','id_demande','date_reception','age','ct','charge_virale','clusterLatitude','clusterLongitude']
firstCasesGG.to_csv(outdir+'first3cases_significantClusters.csv',index=False)
#Save cases that are not in clusters
allCases=gpd.read_postgis('SELECT * FROM covid_tests_vd WHERE res_cov=1',conn, geom_col='geometry')
allCases[~allCases.id_demande.isin(viral_load.id_demande.unique())].to_csv(outdir+'cases_notInClusters.csv',index=False)

firstCases=firstCases.groupby(['cluster','end_date','duration','population','observed','p_value'])['charge_virale'].agg(['mean','max']).reset_index().sort_values(['end_date','cluster'])
firstCases=pd.merge(firstCases, unique_clust[['cluster','end_date','geometry']], how='inner',on=['cluster','end_date'])
firstCases.columns=['cluster','end_date','duration','population','observed','p_value','mean_viralLoad','max_viralLoad','geometry']
firstCases=gpd.GeoDataFrame(firstCases,crs="EPSG:4326", geometry='geometry')
#Save file
if os.path.exists(outdir+'firstCases.gpkg'):
    print('File already exists. Deleted.')
    os.remove(outdir+'firstCases.gpkg')
firstCases.to_file(outdir+'firstCases.gpkg',driver='GPKG')


#SAVE SIGNIFICANT UNIQUE CLUSTERS FOR R PLOTS
if os.path.exists(outdir+'unique_clusters.gpkg'):
    print('File already exists. Deleted.')
    os.remove(outdir+'unique_clusters.gpkg')
unique_clust=pd.merge(unique_clust, res.drop_duplicates(subset=['category','clust_cat_label'])[['category','clust_cat_label']],how='left',on=['category'])
unique_clust[unique_clust.p_value<=0.05].to_file(outdir+'unique_clusters.gpkg',driver='GPKG')


#SAVE CLUSTER CASES
#Add viral load category
viral_load=pd.merge(viral_load,unique_clust[['cluster','end_date','category']],how='inner',on=['cluster','end_date'])
if os.path.exists(outdir+'cluster_cases.gpkg'):
    print('File already exists. Deleted.')
    os.remove(outdir+'cluster_cases.gpkg')
viral_load[viral_load.p_value<=0.05][['cluster','start_date','end_date','category','id_demande','date_reception','age','ct','charge_virale','geometry']].to_file(outdir+'cluster_cases.gpkg',driver='GPKG')

conn.close()
