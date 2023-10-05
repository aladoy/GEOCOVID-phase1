#GEOCOVID-satscanAnalysis.R


# LIBRARIES ---------------------------------------------------------------
# Basic
library(tidyverse)
library(RPostgreSQL)
# Spatial
library(sf)
library(rsatscan)


# IMPORT DATA --------------------------------------------------------------------

dir <- paste0('../outputs/COVID_satscan/ByRELI/ByDays/')
cases_all <- read_delim(paste0(dir,'cases.csv'),',',col_names=TRUE) %>% mutate(date=format(date, "%Y/%m/%d")) %>% select(reli, ncov_cases, date)
pop_all <- read_delim(paste0(dir,'population.csv'),',',col_names=TRUE) %>% select(reli, date, b19btot)
geo <- read.csv(paste0(dir,'geo_reli_satscan.csv'),header=TRUE) %>% select(reli,y,x)

# INITIAL PARAMS ------------------------------------------------------
ssenv <<- new.env(parent=emptyenv())

x=c("[Input]",";case data filename",
"CaseFile=",
";control data filename",
"ControlFile=",
";time precision (0=None, 1=Year, 2=Month, 3=Day, 4=Generic)",
"PrecisionCaseTimes=3",
";study period start date (YYYY/MM/DD)",
"StartDate=2020/3/1",
";study period end date (YYYY/MM/DD)",
"EndDate=2020/3/31",
";population data filename",
"PopulationFile=",
";coordinate data filename",
"CoordinatesFile=",
";use grid file? (y/n)",
"UseGridFile=n",
";grid data filename",
"GridFile=",
";coordinate type (0=Cartesian, 1=latitude/longitude)",
"CoordinatesType=1",
"",
"[Analysis]",
";analysis type (1=Purely Spatial, 2=Purely Temporal, 3=Retrospective Space-Time, 4=Prospective Space-Time, 5=Spatial Variation in Temporal Trends, 6=Prospective Purely Temporal, 7=Seasonal Temporal)",
"AnalysisType=4",
";model type (0=Discrete Poisson, 1=Bernoulli, 2=Space-Time Permutation, 3=Ordinal, 4=Exponential, 5=Normal, 6=Continuous Poisson, 7=Multinomial)",
"ModelType=0",
";scan areas (1=High Rates(Poison,Bernoulli,STP); High Values(Ordinal,Normal); Short Survival(Exponential); Higher Trend(Poisson-SVTT), 2=Low Rates(Poison,Bernoulli,STP); Low Values(Ordinal,Normal); Long Survival(Exponential); Lower Trend(Poisson-SVTT), 3=Both Areas)",
"ScanAreas=1",
";time aggregation units (0=None, 1=Year, 2=Month, 3=Day, 4=Generic)",
"TimeAggregationUnits=3",
";time aggregation length (Positive Integer)",
"TimeAggregationLength=1",
"",
"[Output]",
";analysis main results output filename",
"ResultsFile=",
";output Google Earth KML file (y/n)",
"OutputGoogleEarthKML=n",
";output shapefiles (y/n)",
"OutputShapefiles=y",
";output cartesian graph file (y/n)",
"OutputCartesianGraph=y",
";output cluster information in ASCII format? (y/n)",
"MostLikelyClusterEachCentroidASCII=n",
";output cluster information in dBase format? (y/n)",
"MostLikelyClusterEachCentroidDBase=y",
";output cluster case information in ASCII format? (y/n)",
"MostLikelyClusterCaseInfoEachCentroidASCII=n",
";output cluster case information in dBase format? (y/n)",
"MostLikelyClusterCaseInfoEachCentroidDBase=n",
";output location information in ASCII format? (y/n)",
"CensusAreasReportedClustersASCII=n",
";output location information in dBase format? (y/n)",
"CensusAreasReportedClustersDBase=n",
";output risk estimates in ASCII format? (y/n)",
"IncludeRelativeRisksCensusAreasASCII=n",
";output risk estimates in dBase format? (y/n)",
"IncludeRelativeRisksCensusAreasDBase=n",
";output simulated log likelihoods ratios in ASCII format? (y/n)",
"SaveSimLLRsASCII=n",
";output simulated log likelihoods ratios in dBase format? (y/n)",
"SaveSimLLRsDBase=n",
"",
"[Multiple Data Sets]",
"; multiple data sets purpose type (0=Multivariate, 1=Adjustment)",
"MultipleDataSetsPurposeType=0",
"",
"[Data Checking]",
";study period data check (0=Strict Bounds, 1=Relaxed Bounds)",
"StudyPeriodCheckType=0",
";geographical coordinates data check (0=Strict Coordinates, 1=Relaxed Coordinates)",
"GeographicalCoordinatesCheckType=0",
"",
"[Spatial Neighbors]",
";use neighbors file (y/n)",
"UseNeighborsFile=n",
";neighbors file",
"NeighborsFilename=",
";use meta locations file (y/n)",
"UseMetaLocationsFile=n",
";meta locations file",
"MetaLocationsFilename=",
";multiple coordinates type (0=OnePerLocation, 1=AtLeastOneLocation, 2=AllLocations)",
"MultipleCoordinatesType=0",
"",
"[Spatial Window]",
";maximum spatial size in population at risk (<=50%)",
"MaxSpatialSizeInPopulationAtRisk=10",
";restrict maximum spatial size - max circle file? (y/n)",
"UseMaxCirclePopulationFileOption=n",
";maximum spatial size in max circle population file (<=50%)",
"MaxSpatialSizeInMaxCirclePopulationFile=50",
";maximum circle size filename",
"MaxCirclePopulationFile=",
";restrict maximum spatial size - distance? (y/n)",
"UseDistanceFromCenterOption=n",
";maximum spatial size in distance from center (positive integer)",
"MaxSpatialSizeInDistanceFromCenter=1",
";include purely temporal clusters? (y/n)",
"IncludePurelyTemporal=n",
";window shape (0=Circular, 1=Elliptic)",
"SpatialWindowShapeType=0",
";elliptic non-compactness penalty (0=NoPenalty, 1=MediumPenalty, 2=StrongPenalty)",
"NonCompactnessPenalty=1",
";isotonic scan (0=Standard, 1=Monotone)",
"IsotonicScan=0",
"",
"[Temporal Window]",
";minimum temporal cluster size (in time aggregation units)",
"MinimumTemporalClusterSize=2",
";how max temporal size should be interpretted (0=Percentage, 1=Time)",
"MaxTemporalSizeInterpretation=1",
";maximum temporal cluster size (<=90%)",
"MaxTemporalSize=14",
";include purely spatial clusters? (y/n)",
"IncludePurelySpatial=n",
";temporal clusters evaluated (0=All, 1=Alive, 2=Flexible Window)",
"IncludeClusters=1",
";flexible temporal window start range (YYYY/MM/DD,YYYY/MM/DD)",
"IntervalStartRange=2000/1/1,2000/12/31",
";flexible temporal window end range (YYYY/MM/DD,YYYY/MM/DD)",
"IntervalEndRange=2000/1/1,2000/12/31",
"",
"[Cluster Restrictions]",
";risk limit high clusters (y/n)",
"RiskLimitHighClusters=n",
";risk threshold high clusters (1.0 or greater)",
"RiskThresholdHighClusters=1",
";risk limit low clusters (y/n)",
"RiskLimitLowClusters=n",
";risk threshold low clusters (0.000 - 1.000)",
"RiskThresholdLowClusters=1",
";minimum cases in low rate clusters (positive integer)",
"MinimumCasesInLowRateClusters=3",
";minimum cases in high clusters (positive integer)",
"MinimumCasesInHighRateClusters=3",
"",
"[Space and Time Adjustments]",
";time trend adjustment type (0=None, 1=Nonparametric, 2=LogLinearPercentage, 3=CalculatedLogLinearPercentage, 4=TimeStratifiedRandomization, 5=CalculatedQuadraticPercentage)",
"TimeTrendAdjustmentType=0",
";time trend adjustment percentage (>-100)",
"TimeTrendPercentage=0",
";time trend type - SVTT only (Linear=0, Quadratic=1)",
"TimeTrendType=0",
";adjust for weekly trends, nonparametric",
"AdjustForWeeklyTrends=n",
";spatial adjustments type (0=No Spatial Adjustment, 1=Spatially Stratified Randomization)",
"SpatialAdjustmentType=0",
";use adjustments by known relative risks file? (y/n)",
"UseAdjustmentsByRRFile=n",
";adjustments by known relative risks file name (with HA Randomization=1)",
"AdjustmentsByKnownRelativeRisksFilename=",
"",
"[Inference]",
";p-value reporting type (Default p-value=0, Standard Monte Carlo=1, Early Termination=2, Gumbel p-value=3) ",
"PValueReportType=0",
";early termination threshold",
"EarlyTerminationThreshold=50",
";report Gumbel p-values (y/n)",
"ReportGumbel=n",
";Monte Carlo replications (0, 9, 999, n999)",
"MonteCarloReps=999",
";adjust for earlier analyses(prospective analyses only)? (y/n)",
"AdjustForEarlierAnalyses=n",
";prospective surveillance start date (YYYY/MM/DD)",
"ProspectiveStartDate=2020/03/1",
";perform iterative scans? (y/n),",
"IterativeScan=n",
";maximum iterations for iterative scan (0-32000)",
"IterativeScanMaxIterations=10",
";max p-value for iterative scan before cutoff (0.000-1.000)",
"IterativeScanMaxPValue=0.05",
"",
"[Border Analysis]",
";calculate Oliveira's F",
"CalculateOliveira=n",
";number of bootstrap replications for Oliveira calculation (minimum=100, multiple of 100)",
"NumBootstrapReplications=1000",
";p-value cutoff for cluster's in Oliveira calculation (0.000-1.000)",
"OliveiraPvalueCutoff=0.05",
"",
"[Power Evaluation]",
";perform power evaluation - Poisson only (y/n)",
"PerformPowerEvaluation=n",
";power evaluation method (0=Analysis And Power Evaluation Together, 1=Only Power Evaluation With Case File, 2=Only Power Evaluation With Defined Total Cases)",
"PowerEvaluationsMethod=0",
";total cases in power evaluation",
"PowerEvaluationTotalCases=600",
";critical value type (0=Monte Carlo, 1=Gumbel, 2=User Specified Values)",
"CriticalValueType=0",
";power evaluation critical value .05 (> 0)",
"CriticalValue05=0",
";power evaluation critical value .001 (> 0)",
"CriticalValue01=0",
";power evaluation critical value .001 (> 0)",
"CriticalValue001=0",
";power estimation type (0=Monte Carlo, 1=Gumbel)",
"PowerEstimationType=0",
";number of replications in power step",
"NumberPowerReplications=1000",
";power evaluation alternative hypothesis filename",
"AlternativeHypothesisFilename=",
";power evaluation simulation method for power step (0=Null Randomization, 1=N/A, 2=File Import)",
"PowerEvaluationsSimulationMethod=0",
";power evaluation simulation data source filename",
"PowerEvaluationsSimulationSourceFilename=",
";report power evaluation randomization data from power step (y/n)",
"ReportPowerEvaluationSimulationData=n",
";power evaluation simulation data output filename",
"PowerEvaluationsSimulationOutputFilename=",
"",
"[Spatial Output]",
";automatically launch map viewer - gui only (y/n)",
"LaunchMapViewer=y",
";create compressed KMZ file instead of KML file (y/n)",
"CompressKMLtoKMZ=n",
";whether to include cluster locations kml output (y/n)",
"IncludeClusterLocationsKML=y",
";threshold for generating separate kml files for cluster locations (positive integer)",
"ThresholdLocationsSeparateKML=1000",
";report hierarchical clusters (y/n)",
"ReportHierarchicalClusters=y",
";criteria for reporting secondary clusters(0=NoGeoOverlap, 1=NoCentersInOther, 2=NoCentersInMostLikely,  3=NoCentersInLessLikely, 4=NoPairsCentersEachOther, 5=NoRestrictions)",
"CriteriaForReportingSecondaryClusters=0",
";report gini clusters (y/n)",
"ReportGiniClusters=n",
";gini index cluster reporting type (0=optimal index only, 1=all values)",
"GiniIndexClusterReportingType=0",
";spatial window maxima stops (comma separated decimal values[<=50%] )",
"SpatialMaxima=1,2,3,4,5,6,8,10,12,15,20,25,30,40,50",
";max p-value for clusters used in calculation of index based coefficients (0.000-1.000)",
"GiniIndexClustersPValueCutOff=0.05",
";report gini index coefficents to results file (y/n)",
"ReportGiniIndexCoefficents=n",
";restrict reported clusters to maximum geographical cluster size? (y/n)",
"UseReportOnlySmallerClusters=y",
";maximum reported spatial size in population at risk (<=50%)",
"MaxSpatialSizeInPopulationAtRisk_Reported=1",
";restrict maximum reported spatial size - max circle file? (y/n)",
"UseMaxCirclePopulationFileOption_Reported=n",
";maximum reported spatial size in max circle population file (<=50%)",
"MaxSizeInMaxCirclePopulationFile_Reported=50",
";restrict maximum reported spatial size - distance? (y/n)",
"UseDistanceFromCenterOption_Reported=n",
";maximum reported spatial size in distance from center (positive integer)",
"MaxSpatialSizeInDistanceFromCenter_Reported=1",
";generate Google Maps output (y/n)",
"OutputGoogleMaps=n",
"",
"[Temporal Output]",
";output temporal graph HTML file (y/n)",
"OutputTemporalGraphHTML=n",
";temporal graph cluster reporting type (0=Only most likely cluster, 1=X most likely clusters, 2=Only significant clusters)",
"TemporalGraphReportType=0",
";number of most likely clusters to report in temporal graph (positive integer)",
"TemporalGraphMostMLC=1",
";significant clusters p-value cutoff to report in temporal graph (0.000-1.000)",
"TemporalGraphSignificanceCutoff=0.05",
"",
"[Other Output]",
";report critical values for .01 and .05? (y/n)",
"CriticalValue=n",
";report cluster rank (y/n)",
"ReportClusterRank=y",
";print ascii headers in output files (y/n)",
"PrintAsciiColumnHeaders=n",
";user-defined title for results file",
"ResultsTitle=",
"",
"[Elliptic Scan]",
";elliptic shapes - one value for each ellipse (comma separated decimal values)",
"EllipseShapes=1.5,2,3,4,5",
";elliptic angles - one value for each ellipse (comma separated integer values)",
"EllipseAngles=4,6,9,12,15",
"",
"[Power Simulations]",
";simulation methods (0=Null Randomization, 1=N/A, 2=File Import)",
"SimulatedDataMethodType=0",
";simulation data input file name (with File Import=2)",
"SimulatedDataInputFilename=",
";print simulation data to file? (y/n)",
"PrintSimulatedDataToFile=n",
";simulation data output filename",
"SimulatedDataOutputFilename=",
"",
"[Run Options]",
";number of parallel processes to execute (0=All Processors, x=At Most X Processors)",
"NumberParallelProcesses=0",
";suppressing warnings? (y/n)",
"SuppressWarnings=n",
";log analysis run to history file? (y/n)",
"LogRunToHistoryFile=n",
";analysis execution method  (0=Automatic, 1=Successively, 2=Centrically)",
"ExecutionType=0",
"[System]",";system setting - do not modify","Version=9.2.0")

ssenv$.ss.params.defaults = x
ssenv$.ss.params = x

# WHILE LOOP --------------------------------------------------------------

start <- as.Date("2020/03/01",format="%Y/%m/%d")
end <- as.Date(max(cases_all$date), format="%Y/%m/%d")
#end <- as.Date("2020/03/29",format="%Y/%m/%d")
theDate <- as.Date("2020/04/16",format="%Y/%m/%d")
#theDate<-start

while (theDate <= end)
{
   #Filter cases and controls for the given time period
   cases<-cases_all %>% filter(date>=start & date<=theDate) %>% mutate(date=format(as.Date(date),"%Y/%-m/%-d"))
   pop<-pop_all
   
   #Create temporary directory and store csv for satscan
   td = tempdir()
   write.cas(as.data.frame(cases),td, "cases")
   write.pop(as.data.frame(pop),td,"population")
   write.geo(geo, td, "geo")
   
   if(as.numeric(theDate-start, units="days")<=14){
      #Reset parameters
      invisible(ss.options(reset=TRUE))
      #options for satscan can be found here https://rdrr.io/cran/rsatscan/src/R/zzz.R
      ss.options(list(CaseFile="cases.cas",
                      PopulationFile="population.pop",
                      CoordinatesFile="geo.geo",
                      PrecisionCaseTimes="3",#3=Day
                      StartDate=format(as.Date(start),"%Y/%-m/%-d"),EndDate=format(as.Date(theDate),"%Y/%-m/%-d"),
                      CoordinatesType=1, #1=Lat/Lon
                      AnalysisType=4, #4=Prospective Space-Time
                      ModelType=0, #0=Discrete Poisson
                      ScanAreas=1, #1=High rates
                      ResultsFile=paste0(dir,'res.txt'),
                      MaxSpatialSizeInPopulationAtRisk=10, #10%
                      SpatialWindowShapeType=0, #0=Circles
                      MaxTemporalSize=50, #50%
                      MaxTemporalSizeInterpretation=0, #Percentage
                      TimeAggregationUnits=3, #day
                      MaxSpatialSizeInPopulationAtRisk_Reported=0.5, #0.5%
                      OutputTemporalGraphHTML='y',
                      MonteCarloReps=999,
                      AdjustForEarlierAnalyses='n',
                      MinimumCasesInHighRateClusters=3, #Min 3 cases
                      MinimumTemporalClusterSize=2,
                      Version='9.6.0'))
      write.ss.prm(td, "geocovid")
   }else{
      #Reset parameters
      invisible(ss.options(reset=TRUE))
      #options for satscan can be found here https://rdrr.io/cran/rsatscan/src/R/zzz.R
      ss.options(list(CaseFile="cases.cas",
                      PopulationFile="population.pop",
                      CoordinatesFile="geo.geo",
                      PrecisionCaseTimes="3",#3=Day
                      StartDate=format(as.Date(start),"%Y/%-m/%-d"),EndDate=format(as.Date(theDate),"%Y/%-m/%-d"),
                      CoordinatesType=1, #1=Lat/Lon
                      AnalysisType=4, #4=Prospective Space-Time
                      ModelType=0, #0=Discrete Poisson
                      ScanAreas=1, #1=High rates
                      ResultsFile=paste0(dir,'res.txt'),
                      MaxSpatialSizeInPopulationAtRisk=10, #10%
                      SpatialWindowShapeType=0, #0=Circles
                      MaxTemporalSize=14, #14days
                      MaxTemporalSizeInterpretation=1, #Time
                      TimeAggregationUnits=3, #day
                      MaxSpatialSizeInPopulationAtRisk_Reported=0.5, #0.5%
                      OutputTemporalGraphHTML='y',
                      MonteCarloReps=999,
                      AdjustForEarlierAnalyses='n',
                      MinimumCasesInHighRateClusters=3, #Min 3 cases
                      Version='9.6.0'))
      write.ss.prm(td, "geocovid")
   }

   
   tryCatch(
      {
         #Run analysis
         res = satscan(td,"geocovid",sslocation="/home/aladoy/SaTScan")
         
         #Extract clusters shape 
         clusters=st_as_sf(res$shapeclust)
         
         #Save text file
         capture.output(summary(res), file=paste0(dir,theDate,'_results.txt'),append=FALSE)
         
         #Save to shapefile
         st_write(clusters %>% select(-c(RECURR_INT,ODE,GINI_CLUST)),paste0(dir,theDate,'_results.geojson'),driver='GeoJSON')
      },
      
      warning = function(cond) {
         message("Here's the original warning message:")
         message(cond)
         # Choose a return value when such a type of condition occurs
      },
      
      # Handler when an error occurs:
      error = function(cond) {
         message("Here's the original error message:")
         message(cond)
      },
      
      finally = {
      }
      
   )
   
   theDate <- theDate + 1                    
   
}



   

