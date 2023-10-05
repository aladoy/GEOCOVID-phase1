#GEOCOVID-analysisResults.R

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

#Connect to GEOCOVID DB
con <- dbConnect(drv=RPostgreSQL::PostgreSQL(),host = "localhost",user= rstudioapi::askForPassword("Database user"),rstudioapi::askForPassword("Database password"),dbname="geocovid")

#Extract COVID cases in VD (geocoded at residential address or NPA centroid)
sql='SELECT id_demande, age, ct, charge_virale, geometry FROM covid_tests_vd WHERE res_cov=1'
cases=read_sf(con, query=sql)

#Extract COVID tests in VD (geocoded at residential address or NPA centroid)
tests=read_sf(con, query='SELECT * FROM covid_tests_vd')

#Diffusion zones
dz=st_read(paste0(dir_mstdbscan,'diffusionZones.gpkg')) %>% select(lcid, locality, DZ, geom)

#NPA
sql_npa="SELECT DISTINCT n.LCID,n.locality,n.ptot,n.geometry FROM npa n, (SELECt * FROM cantons where name='Vaud') c WHERE ST_Overlaps(n.geometry, c.geometry) OR ST_Within(n.geometry,c.geometry)"
npa=read_sf(con, query=sql_npa)

#Unique clusters
unclust=st_read(paste0(dir_satscan,'unique_clusters.gpkg'))

#Clusters cases 
clustCases=st_read(paste0(dir_satscan,'cluster_cases.gpkg'))

#First 3 cases
firstCases=st_read(paste0(dir_satscan,'firstCases.gpkg'))

# map_instance ------------------------------------------------------------

theme_map <- theme(
  panel.background=element_rect(fill="transparent"),
  plot.background=element_rect(fill="transparent",color="NA"),
  #plot.margin(25,25,25,25,unit='cm'),
  panel.grid.major=element_line(colour="transparent"),
  panel.grid.minor=element_blank(),
  panel.border = element_rect(colour = "black", fill=NA, size=0.5),
  legend.background=element_blank(),
  #legend.box.margin=margin(10,10,10,10),
  legend.box.background=element_rect(size=0,colour=NA,fill=NA),
  legend.position=c(0.15,0.91),
  #legend.key.size=unit(2,'cm'),
  legend.spacing.x = unit(0.2, 'cm'),
  legend.key=element_rect(colour=NA,fill=NA),
  legend.title=element_text(size=28), #element_blank(),
  #legend.background = element_rect(colour = NA),
  legend.text=element_text(size=25),
  axis.text=element_blank(),axis.title=element_blank(),
  axis.ticks=element_blank())


#Include or remove an extra area of the map
xmin_extra <- -100
xmax_extra <- 100
ymin_extra <- -300
ymax_extra <- 500
#Size of the points
points_size <- 1.5
#scale bar distance
scale_dist <- 1.5
#location of the scale bar
scale_location <- "bottomright"
#Include or remove an extra margin area for the scale bar
scalexmin_extra <- 0
scalexmax_extra <- -500
scaleymin_extra <- 900
scaleymax_extra <- 0
#legend margins for Moran
themex_margin <- 0.21
themey_margin <- 0.89
#Legend margins for Getis
themegx_margin <- 0.21
themegy_margin <- 0.9055
#Text color of the scale bar
scale_color <- "black"
#Colors  of the scale bar
box_color1 <- "black"
box_color2 <- "white"
#Text size of the scale bar
scale_text_size <- 7


# PLOTS -------------------------------------------------------------------

#(DONE IN QGIS NOW)
# map_dz<-ggplot() +
#   geom_sf(data=dz, aes(fill=DZ), lwd=0.1) +
#   scale_colour_manual(values=c('1'='#A0CF8D', '2'='#FFC04C', '3'='#B0E0E6', 'no clusters'='#cccccc')) +
#   scale_fill_manual(
#     name='Diffusion zones',
#     breaks=c("1","2","3","no clusters"),
#     values=c("1"='#A0CF8D','2'='#FFC04C','3'='#B0E0E6', 'no clusters'='#cccccc'),
#     labels=c("Zone 1", "Zone 2", "Zone 3", "No clusters")) +
#   #geom_sf(data=tests, size=0.3, color='#323232') +
#   #geom_sf(data=tests %>% filter(res_cov==1), size=0.3, color='red') +
#   labs(title=NULL,x=NULL,y=NULL)+
#   theme_map
# ggsave(file=paste0(dir_mstdbscan,'dz_cases.png'),plot=map_dz,width=20,height=20,units="in",dpi=90,bg="white")

# BOXPLOT OF VIRAL LOAD FOR COVID-19 CONFIRMED CASES ----------------------

#Extract diffusion zones for COVID-19 confirmed cases
cases_dz <- st_join(cases, dz,join=st_intersects, left=TRUE) %>% st_drop_geometry()

#With log10 transformation of the y-axis
cases_dz_plot<-ggplot(cases_dz, aes(x=DZ, y=charge_virale, color=DZ)) +
  geom_boxplot(show.legend=FALSE) +  scale_y_continuous(trans='log10',breaks=c(10^3, 10^6, 10^9))  +
  #geom_jitter(color="black", size=0.1, alpha=0.6) +
  scale_colour_manual(values=c('1'='#A0CF8D', '2'='#FFC04C', '3'='#B0E0E6', 'no clusters'='#cccccc')) +
  scale_fill_manual(
    name='Diffusion zones',
    breaks=c("1","2","3","no clusters"),
    values=c("1"='#A0CF8D','2'='#FFC04C','3'='#B0E0E6', 'no clusters'='#cccccc'),
    labels=c("Zone 1", "Zone 2", "Zone 3", "No cluster")) +
  labs(y='Viral load [copy numbers / ml]', x='Diffusion zones') + theme(text = element_text(size = 11)) +
  ggsave(paste0(here(dir_mstdbscan),'boxplot_viralLoad_DZ_log10.png'),dpi=200,width=170,height=105, units='mm')


# BOXPLOTS FOR CLUSTER CATEGORY ----------------------

unclust$clust_cat_label<-factor(unclust$clust_cat_label, levels=c('all below 1 million (n=33, 31.13%)', 'at least one between 1 million and 10 millions (n=23, 17.97%)', 'at least one between 10 millions and 100 millions (n=13, 10.4%)', 'at least one between 100 millions and 1 billion (n=128, 19.42%)', 'at least one between 1 billion and 10 billions (n=251, 39.47%)', 'at least one above 10 billions (n=9, 30.0%)'))
clustCases$category<-factor(clustCases$category, levels=c('all below 1 million', 'at least one between 1 million and 10 millions', 'at least one between 10 millions and 100 millions', 'at least one between 100 millions and 1 billion', 'at least one between 1 billion and 10 billions', 'at least one above 10 billions'))

#Within-cluster cases
clust_observed_plot<-ggplot(unclust, aes(x=clust_cat_label, y=observed, color=clust_cat_label)) +
  geom_boxplot(show.legend=TRUE) +
  scale_colour_manual(name='Case cluster viral load categories',values=c('all below 1 million (n=33, 31.13%)'='#66b266','at least one between 1 million and 10 millions (n=23, 17.97%)'='#4f5bd5','at least one between 10 millions and 100 millions (n=13, 10.4%)'='#962fbf','at least one between 100 millions and 1 billion (n=128, 19.42%)'='#fa7e1e','at least one between 1 billion and 10 billions (n=251, 39.47%)'='#ffa7b6','at least one above 10 billions (n=9, 30.0%)'='#ff1919')) +
  scale_fill_manual(
    breaks=c('all below 1 million (n=33, 31.13%)', 'at least one between 1 million and 10 millions (n=23, 17.97%)', 'at least one between 10 millions and 100 millions (n=13, 10.4%)', 'at least one between 100 millions and 1 billion (n=128, 19.42%)', 'at least one between 1 billion and 10 billions (n=251, 39.47%)', 'at least one above 10 billions (n=9, 30.0%)'),
    values=c('all below 1 million (n=33, 31.13%)'='#66b266','at least one between 1 million and 10 millions (n=23, 17.97%)'='#4f5bd5','at least one between 10 millions and 100 millions (n=13, 10.4%)'='#962fbf','at least one between 100 millions and 1 billion (n=128, 19.42%)'='#fa7e1e','at least one between 1 billion and 10 billions (n=251, 39.47%)'='#ffa7b6','at least one above 10 billions (n=9, 30.0%)'='#ff1919'))+
  labs(y='Within-cluster cases', x='') + theme(axis.text.x = element_blank()) +
  ggsave(paste0(here(dir_satscan),'boxplot_signif_cluster_observed.svg'),dpi=200,width=200,height=90, units='mm')

#Cluster duration
clust_duration_plot<-ggplot(unclust, aes(x=clust_cat_label, y=duration, color=clust_cat_label)) +
  geom_boxplot(show.legend=FALSE) +
  scale_colour_manual(name='Case cluster viral load categories',values=c('all below 1 million (n=33, 31.13%)'='#66b266','at least one between 1 million and 10 millions (n=23, 17.97%)'='#4f5bd5','at least one between 10 millions and 100 millions (n=13, 10.4%)'='#962fbf','at least one between 100 millions and 1 billion (n=128, 19.42%)'='#fa7e1e','at least one between 1 billion and 10 billions (n=251, 39.47%)'='#ffa7b6','at least one above 10 billions (n=9, 30.0%)'='#ff1919')) +
  scale_fill_manual(
    breaks=c('all below 1 million (n=33, 31.13%)', 'at least one between 1 million and 10 millions (n=23, 17.97%)', 'at least one between 10 millions and 100 millions (n=13, 10.4%)', 'at least one between 100 millions and 1 billion (n=128, 19.42%)', 'at least one between 1 billion and 10 billions (n=251, 39.47%)', 'at least one above 10 billions (n=9, 30.0%)'),
    values=c('all below 1 million (n=33, 31.13%)'='#66b266','at least one between 1 million and 10 millions (n=23, 17.97%)'='#4f5bd5','at least one between 10 millions and 100 millions (n=13, 10.4%)'='#962fbf','at least one between 100 millions and 1 billion (n=128, 19.42%)'='#fa7e1e','at least one between 1 billion and 10 billions (n=251, 39.47%)'='#ffa7b6','at least one above 10 billions (n=9, 30.0%)'='#ff1919'))+
  labs(y='Duration [days]', x='') + theme(axis.text.x = element_blank()) +
  ggsave(paste0(here(dir_satscan),'boxplot_signif_cluster_duration.svg'),dpi=200,width=100,height=90, units='mm')

#Age of individuals inside clusters (remove outlier of 120 y/o)
clust_age_plot<-ggplot(clustCases %>% filter(age<120), aes(x=category, y=age, color=category)) +
  geom_boxplot(show.legend=FALSE) +
  scale_colour_manual(name='Case cluster viral load categories',values=c('all below 1 million'='#66b266','at least one between 1 million and 10 millions'='#4f5bd5','at least one between 10 millions and 100 millions'='#962fbf','at least one between 100 millions and 1 billion'='#fa7e1e','at least one between 1 billion and 10 billions'='#ffa7b6','at least one above 10 billions'='#ff1919')) +
  scale_fill_manual(
    breaks=c('all below 1 million', 'at least one between 1 million and 10 millions', 'at least one between 10 millions and 100 millions', 'at least one between 100 millions and 1 billion', 'at least one between 1 billion and 10 billions', 'at least one above 10 billions'),
    values=c('all below 1 million'='#66b266','at least one between 1 million and 10 millions'='#4f5bd5','at least one between 10 millions and 100 millions'='#962fbf','at least one between 100 millions and 1 billion'='#fa7e1e','at least one between 1 billion and 10 billions'='#ffa7b6','at least one above 10 billions'='#ff1919'))+
  labs(y='Mean age of the individuals', x='') + theme(axis.text.x = element_blank()) +
  ggsave(paste0(here(dir_satscan),'boxplot_signif_cluster_meanAge.svg'),dpi=200,width=100,height=90, units='mm')


# FIRST CASES VIRAL LOAD --------------------------------------------------

firstCases$categoryDur <- cut(firstCases$duration, 
                   breaks=c(-Inf, 4, 7, 10, Inf), 
                   labels=c("2-4d","5-7d","8-10d", "11-14d"), include.lowest = FALSE, right=TRUE) 

#ggplot(firstCases, aes(x=categoryDur,y=mean_viralLoad)) + geom_boxplot(show.legend=TRUE) + scale_y_continuous(trans='log10',breaks=c(10^3, 10^6, 10^9))  +  labs(y='Mean viral load of the first three cases', x='Cluster duration') + ggsave(paste0(here(dir_satscan),'boxplot_meanVL_duration.svg'),dpi=200,width=180,height=105, units='mm')
#ggplot(firstCases, aes(x=categoryDur,y=max_viralLoad)) + geom_boxplot(show.legend=TRUE) + scale_y_continuous(trans='log10',breaks=c(10^3, 10^6, 10^9))  + labs(y='Max viral load of the first three cases', x='Cluster duration') + ggsave(paste0(here(dir_satscan),'boxplot_maxVL_duration.svg'),dpi=200,width=180,height=105, units='mm')


vary='firstCases$mean_viralLoad'
varx='firstCases$categoryDur'
file_name<-'tukeyTest_meanVL_duration'
model=lm(as.formula(paste0(vary,'~',varx)))
anova=aov(model)
tukey<- TukeyHSD(x=anova, varx, conf.level=0.95)
png(paste0(here(dir_satscan),file_name,'.png'),dpi=200,width=100,height=90, units='mm')
plot(tukey , las=1 , col="brown",cex.axis=0.6) 
dev.off()

tukey('firstCases$mean_viralLoad','firstCases$categoryDur','tukeyTest_meanVL_duration')

#Mean viral load vs. cases
ggplot(firstCases, aes(x=observed,y=mean_viralLoad)) +   
  scale_y_continuous(trans='log10',breaks=c(10^4,10^5, 10^6, 10^7, 10^8, 10^9)) + 
  geom_point(aes(color=p_value))  + geom_smooth(method=lm) + 
  labs(y='Mean viral load of the first three cases', x='Cases', color='p-value') + 
  ggsave(paste0(here(dir_satscan),'mean_viralLoad_pop.svg'),dpi=200,width=180,height=90, units='mm')

#Max viral load vs. cases
ggplot(firstCases, aes(x=observed,y=max_viralLoad)) +   
  scale_y_continuous(trans='log10',breaks=c(10^4,10^5, 10^6, 10^7, 10^8, 10^9)) + 
  geom_point(aes(color=p_value))  + geom_smooth(method=lm) + 
  labs(y='Maximal viral load of the first three cases', x='Cases', color='p-value') + 
  ggsave(paste0(here(dir_satscan),'max_viralLoad_pop.svg'),dpi=200,width=180,height=90, units='mm')


# AGE VS VIRAL LOAD -------------------------------------------------------

cases$categoryAge <- cut(cases$age, 
                              breaks=c(-Inf, 20, 30, 40, 50, 60, 70, 80, 90, Inf), 
                              labels=c("≤20","21-30","31-40", "41-50", "51-60", "61-70", "71-80", "81-90", ">90"), include.lowest = FALSE, right=TRUE) 

#Boxplot of viral load between age groups
ggplot(cases %>% filter(!is.na(age)), aes(x=categoryAge,y=charge_virale)) + 
  geom_boxplot(show.legend=TRUE) + 
  scale_y_continuous(trans='log10')  + 
  labs(y='Viral load [copy numbers / ml]', x='Age of individuals tested positive [years]') + 
  ggsave(paste0(here('../outputs/'),'age_vs_viralLoad.png'),dpi=200,width=180,height=90, units='mm')

#Tukey HSD test for comparisons between different groups
tukey <- function(vary, varx, file_name){
  model=lm(as.formula(paste0(vary,'~',varx)))
  anova=aov(model)
  tukey<- TukeyHSD(x=anova, varx, conf.level=0.95)
  png(paste0(here('../outputs/'),file_name,'.png'),width=100,height=90, units='mm',res=200)
  plot(tukey , las=1 , col="brown",cex.axis=0.3)
  dev.off()
}

#Tukey test on age groups & viral load
tukey('cases$charge_virale','cases$categoryAge','tukeyTest_viralLoad_age')

# #Line plot 
# ggplot(cases, aes(x=age, y=charge_virale)) +
#   scale_y_continuous(trans='log10') +
#   geom_point() + geom_smooth(method=lm) +
#   labs(y='Viral load [copy numbers / ml]', x='Age')+
#   ggsave(paste0(here('../outputs/'),'age_vs_viralLoad.png'),dpi=200,width=180,height=90, units='mm')

# DISTRIBUTION OF VIRAL LOAD IN COVID-19 CONFIRMED CASES ------------------

ggplot(data=cases) +
  geom_histogram(aes(x=charge_virale),fill='white',color='grey') +
  scale_x_log10() +
  labs(x='Viral load [copy numbers / ml]', y='Count')+
  ggsave(paste0(here(dir_satscan),'distribution_viralLoad_log10.png'),dpi=200,width=148,height=105, units='mm')

