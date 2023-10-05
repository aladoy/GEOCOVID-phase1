#GEOCOVID-MultinomialAssignment.R


# LIBRARIES ---------------------------------------------------------------
library(tidyverse)
library(sf)
library(RPostgreSQL)
library(stats) #multinomial distribution
library(nngeo) #nearest-neighbors algorithm


# IMPORT DATA -------------------------------------------------------------

#Connect to GEOCOVID DB
con <- dbConnect(drv=RPostgreSQL::PostgreSQL(),host = "localhost",user= rstudioapi::askForPassword("Database user"),rstudioapi::askForPassword("Database password"),dbname="geocovid")


# HANDLE COVID TESTS GEOCODED AT NPA CENTROIDS (MULTINOMIAL DISTRIBUTION) ----------------------------

#List of distinct NPA which contain non geocoded individuals
sql="SELECT DISTINCT lcid FROM npa n, (SELECT id_demande,geometry FROM covid_tests_vd WHERE note_geocoding LIKE 'Geocoded at NPA%') c WHERE ST_contains(n.geometry, c.geometry)"
npa=read_sf(con,query=sql)
npa=as.vector(npa$lcid)

#Go through each NPA, assign COVID-19 tests to RELI based on multinomial distribution, append results in a single dataframe
nogeo = NULL

#For loop on NPA
for (lcid in npa) {
  
  #Inhabited hectares (RELI) that overlapped the NPA
  sql_ha=paste0("SELECT s.reli, s.b19btot, st_expand(s.geometry,50) as geometry FROM statpop_centroid s, (SELECT * FROM npa WHERE lcid=",lcid,") n WHERE st_within(s.geometry, n.geometry)")
  ha <- read_sf(con,query=sql_ha)
  
  #Non geocoded COVID-tests that are contained in the NPA
  sql_nogeo=paste0("SELECT c.* FROM covid_tests_vd c, (SELECT * FROM npa WHERE lcid=",lcid,") n WHERE st_within(c.geometry, n.geometry) AND note_geocoding LIKE 'Geocoded at NPA%'")
  nogeo_npa <- read_sf(con,query=sql_nogeo)
  
  #For each non geocoded test, assign to a RELI based on multinomial distribution
  res<-nogeo_npa %>% rowwise() %>% mutate(reli=sum(rmultinom(1,1,as.vector(ha$b19btot)) * ha$reli))
  
  #Append to the dataframe
  nogeo=rbind(nogeo,res)
}

nogeo <- nogeo %>% select(-geometry)

# HANDLE COVID TESTS NOT CONTAINED IN A RELI (NEAREST NEIGHBOR RELI)------------------------------

#Extract COVID tests that are geocoded but do not fall inside a RELI 
sql_noreli="SELECT c.* FROM covid_tests_vd c LEFT JOIN 
(SELECT s.reli, st_expand(s.geometry,50) as geometry FROM statpop_centroid s, (SELECt geometry FROM cantons where name='Vaud') vd WHERE ST_Intersects(vd.geometry, s.geometry)) r
ON ST_Within(c.geometry, r.geometry)
WHERE c.note_geocoding NOT LIKE 'Geocoded at NPA%'
AND r.reli IS NULL"
noreli=read_sf(con,query=sql_noreli)

#Extract all the inhabited hectares in the canton of Vaud
sql_ha_vd="SELECT s.reli, s.b19btot, st_expand(s.geometry,50) as geometry FROM statpop_centroid s, (SELECt geometry FROM cantons where name='Vaud') vd WHERE ST_Intersects(vd.geometry, s.geometry)"
ha_vd=read_sf(con,query=sql_ha_vd)
#Add new column in ha corresponding to rownames
ha_vd_df <- ha_vd %>% st_drop_geometry() %>% rownames_to_column() %>% mutate(rowname=as.integer(rowname)) #Here, we could also use OBJECTID which already correspond to rownames
  
#Find closest reli for each row in the dataframe
nearest<- st_nn(noreli,ha_vd,k=1,returnDist = F) 
  
#Add the nearest neighbor (rowname) to dataframe
noreli <- noreli %>% mutate(nearest=sapply(nearest , "[[", 1)) #Add rownames of nearest RELI to subset.sfframe
  
#Add the corresponding RELI
noreli <- noreli %>% st_drop_geometry() %>% left_join(ha_vd_df, by=c('nearest'='rowname')) %>% select(-c(nearest,b19btot))


# HANDLE OTHER COVID TESTS (BASIC SPATIAL JOIN) ---------------------------

#Bind the two dataframes
first_part <- rbind(nogeo,noreli)

#Extract all COVID tests
sql_alltests="SELECT c.*, r.reli FROM covid_tests_vd c LEFT JOIN 
(SELECT s.reli, st_expand(s.geometry,50) as geometry FROM statpop_centroid s, (SELECT geometry FROM cantons where name='Vaud') vd WHERE ST_Intersects(vd.geometry, s.geometry)) r
ON ST_Within(c.geometry, r.geometry)"
others=read_sf(con, query=sql_alltests)

#Select COVID tests that didn't have been handled before
others <- others %>% filter(! id_demande %in% first_part$id_demande) %>% st_drop_geometry()

#Bind all dataframes in a single one
covid_tests_ha <- rbind(first_part, others)


# UPDATE TABLE IN POSTGIS ----------------------------------------------

#Add new columns
dbGetQuery(con, "ALTER TABLE covid_tests_vd ADD COLUMN corresponding_reli BIGINT")

#Function to update Postgres table
update_postgres_table <- function(id_demande, corresponding_reli){
  sql<-sqlInterpolate(con, "UPDATE covid_tests_vd SET corresponding_reli = ?new_col WHERE id_demande = ?id",new_col=corresponding_reli,id=id_demande)
  dbExecute(con,sql)
  }

#Map for every rows (Normal if an error appears, still working)
map2_df(covid_tests_ha$id_demande, covid_tests_ha$reli, update_postgres_table)

