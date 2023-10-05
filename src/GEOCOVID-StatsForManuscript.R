#GEOCOVID-StatsForManuscript.R

# LIBRARIES ---------------------------------------------------------------
# Basic
library(tidyverse)
library(sf)
library(here)
library(ggpubr)
# Spatial
library(sf)

#DIRECTORIES
dir_mstdbscan<-"../outputs/COVID_MSTDBSCAN/ByDays_1km/"
dir_satscan<-"../outputs/COVID_satscan/ByRELI/ByDays/"

# ABSTRACT ----------------------------------------------------------------



#import significant satscan clusters
unclust=st_read(paste0(dir_satscan,'unique_clusters.gpkg'))

#1. median & IQR (Q1, Q3) of clusters duration 
summary(unclust$duration)

#2. median & IQR (Q1, Q3) of within-clusters cases 
summary(unclust$observed)

#3. median of infected persons for clusters having at least one person with a viral load above 1 billion copies/ml

#create two groups for clusters having at least one above 1 billion copies/ml and for the ones below 1 million
unclust_2cat <- unclust %>% filter(category %in% c("all below 1 million" ,"at least one between 1 billion and 10 billions","at least one above 10 billions"))
unclust_2cat <- unclust_2cat %>% mutate(category2=if_else(category=="all below 1 million","all below 1 million","at least one above 1 billion"))

group_by(unclust_2cat, category2) %>%
  summarise(
    count = n(),
    median_cases = median(observed, na.rm = TRUE),
    IQR_cases = IQR(observed, na.rm = TRUE),
    median_duration = median(duration, na.rm = TRUE),
    IQR_duration = IQR(duration, na.rm = TRUE)
  )

wilcox.test(observed ~ category2, data = unclust_2cat) #p-value <0.001
wilcox.test(duration ~ category2, data = unclust_2cat)

#4. median of infected persons for clusters having all individuals below 1 million and at least one above

#create two groups for clusters having all below 1 million and at least one above
unclust_2catbis <- unclust %>% mutate(category2=if_else(category=="all below 1 million","all below 1 million","at least one above 1 million"))

group_by(unclust_2catbis, category2) %>%
  summarise(
    count = n(),
    median_cases = median(observed, na.rm = TRUE),
    IQR_cases = IQR(observed, na.rm = TRUE),
    median_duration = median(duration, na.rm = TRUE),
    IQR_duration = IQR(duration, na.rm = TRUE)
  )

wilcox.test(observed ~ category2, data = unclust_2catbis)

#5. median of infected persons for clusters green and blue

unclust_2catter <- unclust %>% filter(category %in% c("all below 1 million" ,"at least one between 1 million and 10 millions"))

group_by(unclust_2catter, category) %>%
  summarise(
    count = n(),
    median_cases = median(observed, na.rm = TRUE),
    IQR_cases = IQR(observed, na.rm = TRUE),
    median_duration = median(duration, na.rm = TRUE),
    IQR_duration = IQR(duration, na.rm = TRUE)
  )

wilcox.test(observed ~ category, data = unclust_2catter)


levels(unclust$category)


vary='unclust$duration'
varx='unclust$category'
file_name<-'tukeyTest_category_duration'
model=lm(as.formula(paste0(vary,'~',varx)))
anova=aov(model)
tukey<- TukeyHSD(x=anova, varx, conf.level=0.95)
png(paste0(here(dir_satscan),file_name,'.png'),dpi=200,width=100,height=90, units='mm')
plot(tukey , las=1 , col="brown",cex.axis=0.6) 
dev.off()
