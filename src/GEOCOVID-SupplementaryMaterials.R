#GEOCOVID-SupplementaryMaterials.R

# LIBRARIES ---------------------------------------------------------------
# Basic
library(tidyverse)
library(here)
library(ggpubr)
library(RPostgreSQL)
# Spatial
library(sf)

#DIRECTORIES
dir_satscan<-"../outputs/COVID_satscan/ByRELI/ByDays/"


# DATA --------------------------------------------------------------------

#Connect to GEOCOVID DB
con <- dbConnect(drv=RPostgreSQL::PostgreSQL(),host = "localhost",user= rstudioapi::askForPassword("Database user"),rstudioapi::askForPassword("Database password"),dbname="geocovid")

#Extract COVID cases in VD
sql='SELECT * FROM covid_tests_vd WHERE res_cov=1'
cases=read_sf(con, query=sql) %>% st_drop_geometry()

#First 3 cases
firstCases=st_read(paste0(dir_satscan,'firstCases.gpkg'))

#Significant satscan clusters
clustcases=st_read(paste0(dir_satscan,'cluster_cases.gpkg')) %>% st_drop_geometry()

#Unique clusters
unclust=st_read(paste0(dir_satscan,'unique_clusters.gpkg')) %>% st_drop_geometry()


# RESULTS -----------------------------------------------------------------

#1. Distribution of viral loads within significant clusters 

#individuals inside significant clusters
cases_inside <- cases %>% filter(id_demande %in% (clustcases  %>% select(id_demande) %>% distinct()  %>% pull()))
ggplot(cases_inside, aes(x=charge_virale)) + geom_histogram(binwidth=.3, colour="black", fill="white")+ scale_x_log10() + 
  labs(x='Viral load [copy numbers / ml]', y='Frequency', title='Distribution of viral loads for individuals within significant clusters') + 
  theme(plot.title = element_text(size = 12))+
  ggsave(paste0(here(dir_satscan),'viralLoad_distribution_inside.png'),dpi=200,width=170,height=105, units='mm')


#2. Distribution of viral loads outside significant clusters 

#individuals outside clusters or in non significant clusters
cases_outside <- cases %>% filter(!id_demande %in% clustcases)
ggplot(cases_outside, aes(x=charge_virale)) + geom_histogram(binwidth=.3, colour="black", fill="white")+ scale_x_log10() + 
  labs(x='Viral load [copy numbers / ml]', y='Frequency', title='Distribution of viral loads for individuals outside significant clusters') + 
  theme(plot.title = element_text(size = 12))+
  ggsave(paste0(here(dir_satscan),'viralLoad_distribution_outside.png'),dpi=200,width=170,height=105, units='mm')

#Compare the two distributions with Kolmogorov-Smirnov test
ks.test(cases_inside %>% pull(charge_virale), cases_outside %>% pull(charge_virale))

#3. Number of individuals in each category of figure 5A
mean_first <- firstCases %>% st_drop_geometry() %>% select(observed, mean_viralLoad)

mean_first$cases_cat <- cut(mean_first$observed, 
                         breaks=c(-Inf, 5, 10, 15, 20, 25, 30,Inf), 
                         labels=c("<5","5-9","10-14", "15-19", "20-24", "25-29", "≥30"), include.lowest = TRUE, right = FALSE) 

mean_first$vl_cat <- cut(mean_first$mean_viralLoad, 
                        breaks=c(-Inf, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9 ,Inf), 
                        labels=c("<1e4","1e4-1e5","1e5-1e6", "1e6-1e7", "1e7-1e8", "1e8-1e9", "≥1e9"), include.lowest = TRUE, right = FALSE) 

mean_first_res<-mean_first %>% group_by(cases_cat,vl_cat) %>% summarise(n())


#4. Number of individuals in each category of figure 5B

max_first <- firstCases %>% st_drop_geometry() %>% select(observed, max_viralLoad)

max_first$cases_cat <- cut(max_first$observed, 
                            breaks=c(-Inf, 5, 10, 15, 20, 25, 30,Inf), 
                            labels=c("<5","5-9","10-14", "15-19", "20-24", "25-29", "≥30"), include.lowest = TRUE, right = FALSE) 

max_first$vl_cat <- cut(max_first$max_viralLoad, 
                         breaks=c(-Inf, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9 ,Inf), 
                         labels=c("<1e4","1e4-1e5","1e5-1e6", "1e6-1e7", "1e7-1e8", "1e8-1e9", "≥1e9"), include.lowest = TRUE, right = FALSE) 

max_first_res<-max_first %>% group_by(cases_cat,vl_cat) %>% summarise(n())


#3. Number of individuals in each category of figure 5A
allcases <- clustcases %>% select(cluster, end_date,charge_virale) %>% group_by(cluster,end_date) %>% 
  summarise(mean_viralLoad=mean(charge_virale), max_viralLoad=max(charge_virale))
allcases <- inner_join(allcases, unclust %>% select(cluster, end_date, observed), by=c('cluster','end_date'))

allcases$cases_cat <- cut(allcases$observed, 
                            breaks=c(-Inf, 5, 10, 15, 20, 25, 30,Inf), 
                            labels=c("<5","5-9","10-14", "15-19", "20-24", "25-29", "≥30"), include.lowest = TRUE, right = FALSE) 

allcases$vl_mean_cat <- cut(allcases$mean_viralLoad, 
                         breaks=c(-Inf, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9 ,Inf), 
                         labels=c("<1e4","1e4-1e5","1e5-1e6", "1e6-1e7", "1e7-1e8", "1e8-1e9", "≥1e9"), include.lowest = TRUE, right = FALSE) 

allcases$vl_max_cat <- cut(allcases$max_viralLoad, 
                            breaks=c(-Inf, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9 ,Inf), 
                            labels=c("<1e4","1e4-1e5","1e5-1e6", "1e6-1e7", "1e7-1e8", "1e8-1e9", "≥1e9"), include.lowest = TRUE, right = FALSE) 

mean_all_res<-allcases %>% group_by(cases_cat,vl_mean_cat) %>% summarise(n())
max_all_res<-allcases %>% group_by(cases_cat,vl_max_cat) %>% summarise(n())

