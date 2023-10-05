#GEOCOVID-MAPS.R

# LIBRARIES ---------------------------------------------------------------
# Basic
library(tidyverse)
library(ggplot2)
library(RPostgreSQL)
library(here)
# Spatial
library(sf)
library(ggspatial)


# IMPORT DATA -------------------------------------------------------------

dir_mstdbscan<-"../outputs/COVID_MSTDBSCAN/ByDays_1km/"
dir_satscan<-"../outputs/COVID_satscan/ByRELI/ByDays/"


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
  legend.position=c(0.20,0.91),
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


dates <- c(as.Date('2020-03-11',format='%Y-%m-%d'), as.Date('2020-03-15',format='%Y-%m-%d'), as.Date('2020-03-19',format='%Y-%m-%d'), as.Date('2020-03-24',format='%Y-%m-%d'), as.Date('2020-03-27',format='%Y-%m-%d'), as.Date('2020-04-01',format='%Y-%m-%d'))


# SATSCAN MAPS ------------------------------------------------------------

#Connect to GEOCOVID DB
con <- dbConnect(drv=RPostgreSQL::PostgreSQL(),host = "localhost",user= rstudioapi::askForPassword("Database user"),rstudioapi::askForPassword("Database password"),dbname="geocovid")

#NPA
sql_npa="SELECT DISTINCT n.LCID,n.locality,n.ptot,n.geometry FROM npa n, (SELECt * FROM cantons where name='Vaud') c WHERE ST_Overlaps(n.geometry, c.geometry) OR ST_Within(n.geometry,c.geometry)"
npa=read_sf(con, query=sql_npa)

#LAKES
lakes=st_read('../data/LAKES/lakes.shp') 

#TESTS
tests=read_sf(con, query="SELECT * FROM covid_tests_vd")

#:length(dates)
for (i in 1) {
  
  #Read satscan clusters for the given day
  satscan_clust<-st_read(paste0(dir_satscan,dates[i],'_results.geojson'))
  
  #Reproject to 2056
  satscan_clust<-satscan_clust %>% st_set_crs(4326) %>% st_transform("+init=epsg:2056")
  
  #Add classes for significance level
  satscan_clust$SIGN <- cut(satscan_clust$P_VALUE, breaks = c(-Inf, 0.01,0.05, Inf), 
                            labels = c('p<0.01', 'p<0.05','not significant'), right = FALSE)
  

  map_satscan<-ggplot() +
    geom_sf(data=npa, fill='#e5e5e5',alpha=1,lwd=0.1) +
    geom_sf(data=lakes, fill='#b4c8dd', alpha=1, lwd=0.1, colour='#6498d2')+
    geom_sf(data=tests, fill='#333333',size=0.01)+
    geom_sf(data=satscan_clust,aes(fill=SIGN, color=SIGN),lwd=0.9,alpha=0.7, show.legend=FALSE) + 
    scale_fill_manual(
      aesthetics = c("colour", "fill"),
      name=paste0(dates[i]),
      breaks=c('p<0.01', 'p<0.05','not significant'),
      values=c('p<0.01'='#ff0000', 'p<0.05'='#ff8181', 'not significant'='#b2b2b2'),
      labels=c('p≤0.01', 'p≤0.05','Not significant')) +
    labs(title=NULL,x=NULL,y=NULL)+
    annotation_scale(style='ticks',pad_x=unit(1,'cm'), pad_y =unit(1,'cm'), line_width = 2, text_cex = 1.5)+
    theme_map
  ggsave(file=paste0(dir_satscan,'map_',dates[i],'.png'),plot=map_satscan,width=20,height=20,units="in",dpi=90,bg="white")

}

# MST-DBSCAN MAPS ---------------------------------------------------------
  
  #Diffusion zones
  dz=st_read(paste0(dir_mstdbscan,'diffusionZones.gpkg')) %>% select(lcid, locality, DZ, geom)
  
  #Clusters 
  mstclust=st_read(paste0(dir_mstdbscan,'clusterGDF.gpkg'))
  mstclust <- mstclust %>% mutate(mstDate=as.Date(mstDate))
  
  for (i in 1) {
    
    mstdat <- mstclust %>% filter(mstDate==dates[i])

#Print once in SVG (date 3) for the legend  
    if(i==3){
      map_mst<-ggplot() +
        geom_sf(data=npa, fill='#e5e5e5',alpha=1,lwd=0.1) +
        geom_sf(data=lakes, fill='#b4c8dd', alpha=1, lwd=0.1, colour='#6498d2')+
        #geom_sf(data=tests, fill='#333333',size=0.01)+
        geom_sf(data=mstdat,aes(fill=type),alpha=0.5, show.legend = FALSE) + #remove show.legend=FALSE to print SVG (for legend item)
        scale_colour_manual(values=c('Emerge'='#fb9a99', 'Growth'='#e31a1c','Steady'='#33a02c', 'Merge'='#ffffb3','Move'='#fdb462','Split'='#bebada','Reduction'='#1f78b4')) +
        scale_fill_manual(
          name=paste0(dates[i]),
          breaks=c('Emerge', 'Growth','Steady','Merge','Move','Split','Reduction'),
          values=c('Emerge'='#fb9a99', 'Growth'='#e31a1c','Steady'='#33a02c', 'Merge'='#ffffb3','Move'='#fdb462','Split'='#bebada','Reduction'='#1f78b4'),
          labels=c('Emerge', 'Growth','Steady','Merge','Move','Split','Reduction')) +
        labs(title=NULL,x=NULL,y=NULL)+
        annotation_scale(style='ticks',pad_x=unit(1,'cm'), pad_y =unit(1,'cm'), line_width = 2, text_cex = 1.5)+
        theme_map 
      #ggsave(file=paste0(dir_mstdbscan,'map_',dates[i],'.svg'),plot=map_mst,width=20,height=20,units="in",dpi=90,bg="white")
      ggsave(file=paste0(dir_mstdbscan,'map_',dates[i],'.png'),plot=map_mst,width=20,height=20,units="in",dpi=90,bg="white")
    }else{
      map_mst<-ggplot() +
        geom_sf(data=npa, fill='#e5e5e5',alpha=1,lwd=0.1) +
        geom_sf(data=lakes, fill='#b4c8dd', alpha=1, lwd=0.1, colour='#6498d2')+
        geom_sf(data=tests, fill='#333333',size=0.01)+
        geom_sf(data=mstdat,aes(fill=type),alpha=0.5,show.legend = FALSE) + 
        scale_colour_manual(values=c('Emerge'='#fb9a99', 'Growth'='#e31a1c','Steady'='#33a02c', 'Merge'='#ffffb3','Move'='#fdb462','Split'='#bebada','Reduction'='#1f78b4')) +
        scale_fill_manual(
          name=paste0(dates[i]),
          breaks=c('Emerge', 'Growth','Steady','Merge','Move','Split','Reduction'),
          values=c('Emerge'='#fb9a99', 'Growth'='#e31a1c','Steady'='#33a02c', 'Merge'='#ffffb3','Move'='#fdb462','Split'='#bebada','Reduction'='#1f78b4'),
          labels=c('Emerge', 'Growth','Steady','Merge','Move','Split','Reduction')) +
        labs(title=NULL,x=NULL,y=NULL)+
        annotation_scale(style='ticks',pad_x=unit(1,'cm'), pad_y =unit(1,'cm'), line_width = 2, text_cex = 1.5)+
        theme_map 
      ggsave(file=paste0(dir_mstdbscan,'map_',dates[i],'.png'),plot=map_mst,width=20,height=20,units="in",dpi=90,bg="white")
    }
  }
  
  
