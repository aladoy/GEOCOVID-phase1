#GEOCOVID-analysisResults_first3cases.R

# LIBRARIES ---------------------------------------------------------------
# Basic
library(tidyverse)
library(ggplot2)
library(RPostgreSQL)
library(here)
library(multcompView)
# Spatial
library(sf)

# IMPORT DATA -------------------------------------------------------------

dir_mstdbscan<-"../outputs/COVID_MSTDBSCAN/ByDays_1km/"
dir_satscan<-"../outputs/COVID_satscan/ByRELI/ByDays/"

#First 3 cases
firstCases=st_read(paste0(dir_satscan,'clusters_firstCases.gpkg'))

unclust=firstCases %>% distinct(cluster,end_date, .keep_all = TRUE)

statfirstCases <- firstCases %>% group_by(cluster,end_date,observed,p_value) %>%
  summarise(
    max_VL = max(charge_virale, na.rm = TRUE),
    mean_VL = mean(charge_virale, na.rm = TRUE),
  )

#Within-cluster cases
ggplot(unclust, aes(x=category, y=observed, color=category)) + geom_boxplot(show.legend=TRUE)

statfirstCases

#Mean viral load vs. cases
ggplot(statfirstCases, aes(x=observed,y=mean_VL)) +   
  scale_y_continuous(trans='log10',breaks=c(10^4,10^5, 10^6, 10^7, 10^8, 10^9)) + 
  geom_point(aes(color=p_value))  + geom_smooth(method=lm) + 
  labs(y='Mean viral load of the first three cases', x='Cases', color='p-value') 

#Max viral load vs. cases
ggplot(statfirstCases, aes(x=observed,y=max_VL)) +   
  scale_y_continuous(trans='log10',breaks=c(10^4,10^5, 10^6, 10^7, 10^8, 10^9)) + 
  geom_point(aes(color=p_value))  + geom_smooth(method=lm) + 
  labs(y='Maximal viral load of the first three cases', x='Cases', color='p-value')
