#GEOCOVID-chargeVirale.py

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

outdir='outputs/'

#LOAD DATA
#Viral Load
viralLoad=pd.read_csv('data/COVID/201202_Covid-19_VD-V2.csv',delimiter=';',encoding='iso-8859-1')
viralLoad=viralLoad[['ID DEMANDE','CT','QANTIFICATION copies/ml']]
viralLoad.columns=['id_demande','ct','charge_virale']

#Number of info in charge virale
print('Number of id_demande with viral load information: ', viralLoad[~pd.isnull(viralLoad.charge_virale)].shape[0])
#Note: the number of people with viral load in the text file is not the same as covid tests vd because it also includes people outside the canton of Vaud

#CONNECT TO DB WITH user=aladoy
pw=getpass.getpass() #Ask for user password
engine=create_engine("postgresql+psycopg2://aladoy:{}@localhost/geocovid".format(pw)) #Create SQLAlchemy engine
conn=ps.connect("dbname='geocovid' user='aladoy' host='localhost' password='{}'".format(pw)) #Create a connection object
cursor=conn.cursor() #Create a cursor object

#Extract COVID tests VD
covidTests=gpd.read_postgis("SELECT id_demande, res_cov, geometry FROM covid_tests_vd", conn, geom_col='geometry')

#Remove rows with no information about viral load
viralLoad=viralLoad[~pd.isnull(viralLoad.charge_virale)]

#Set <1000 to 100 to allow the conversion in float
viralLoad.loc[viralLoad.charge_virale=='<1.0 E+3', 'charge_virale']='1.0E+2'
viralLoad['charge_virale']=viralLoad.charge_virale.map(float)

#Add viral load information to COVID_tests
covidTests=pd.merge(covidTests,viralLoad, how='left',on='id_demande')

def give_cat_viral_load(df):
    if df['charge_virale'] < 1e5:
        return '< 1e5'
    elif (df['charge_virale'] >=1e5 )& (df['charge_virale'] <1e6):
        return '[1e5-1e6['
    elif (df['charge_virale'] >=1e6 )& (df['charge_virale'] <1e7):
        return '[1e6-1e7['
    elif (df['charge_virale'] >=1e7 )& (df['charge_virale'] <1e8):
        return '[1e7-1e8['
    elif (df['charge_virale'] >=1e8 )& (df['charge_virale'] <1e9):
        return '[1e8-1e9['
    elif df['charge_virale'] >= 1e9:
        return '>= 1e9'

covidTests['cat_charge_virale'] = covidTests.apply(give_cat_viral_load, axis = 1)

print('Has each individual with a viral load (res_cov=1) been assigned a category? ' + str(covidTests[~pd.isnull(covidTests.cat_charge_virale)].shape[0]==covidTests[covidTests.res_cov==1].shape[0]))

#Number of info on viral load in COVID tests VD
print('Number of id_demande with viral load information (for COVID tests VD): ', covidTests[~pd.isnull(covidTests.charge_virale)].shape[0], '(', round(covidTests[~pd.isnull(covidTests.charge_virale)].shape[0]*100/covidTests.shape[0],2),'%)')

#ADD new information in postgres db
rows = zip(covidTests.id_demande, covidTests.ct, covidTests.charge_virale)
cursor.execute("""CREATE TEMP TABLE codelist(id_demande TEXT, ct DOUBLE PRECISION, charge_virale DOUBLE PRECISION) ON COMMIT DROP""")
cursor.executemany("""INSERT INTO codelist(id_demande, ct, charge_virale) VALUES(%s, %s, %s)""", rows)
cursor.execute("""ALTER TABLE covid_tests_vd ADD COLUMN ct DOUBLE PRECISION""")
cursor.execute("""ALTER TABLE covid_tests_vd ADD COLUMN charge_virale DOUBLE PRECISION""")
cursor.execute("""
    UPDATE covid_tests_vd
    SET ct = codelist.ct
    FROM codelist
    WHERE codelist.id_demande = covid_tests_vd.id_demande;
    """)
cursor.execute("""
    UPDATE covid_tests_vd
    SET charge_virale = codelist.charge_virale
    FROM codelist
    WHERE codelist.id_demande = covid_tests_vd.id_demande;
    """)

#ADD viral load categories in postgres db
rows = zip(covidTests.id_demande, covidTests.cat_charge_virale)
cursor.execute("""CREATE TEMP TABLE catChargeVirale(id_demande TEXT, cat_charge_virale TEXT) ON COMMIT DROP""")
cursor.executemany("""INSERT INTO catChargeVirale (id_demande, cat_charge_virale) VALUES(%s, %s)""", rows)
cursor.execute("""ALTER TABLE covid_tests_vd ADD COLUMN cat_charge_virale TEXT""")
cursor.execute("""
    UPDATE covid_tests_vd
    SET cat_charge_virale = catChargeVirale.cat_charge_virale
    FROM catChargeVirale
    WHERE catChargeVirale.id_demande = covid_tests_vd.id_demande;
    """)

conn.commit()
cursor.close()
conn.close()
