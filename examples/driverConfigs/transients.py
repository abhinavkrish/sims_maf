import numpy as np
import os
from lsst.sims.maf.driver.mafConfig import configureSlicer, configureMetric, makeDict

def mConfig(config, runName, dbDir='.', outputDir='Out', slicerName='OpsimFieldSlicer',
            benchmark='design', **kwargs):


    config.outputDir = outputDir
    if runName.endswith('_sqlite.db'):
        runName = runName.replace('_sqlite.db', '')
    sqlitefile = os.path.join(dbDir, runName + '_sqlite.db')
    config.dbAddress ={'dbAddress':'sqlite:///'+sqlitefile}
    config.opsimName = runName
    config.figformat = 'pdf'

    config.getConfig = False

    slicerList=[]

    nside=128

    # Set everything on
    plotDict={'xMin':0.,'xMax':.25}
    stats = {'MeanMetric':{}, 'MedianMetric':{}, 'MinMetric':{}, 'MaxMetric':{}}

    metricList = []
    #metricList.append(configureMetric('TransientMetric', plotDict=plotDict, summaryStats=stats,
    #                                  kwargs={'metricName':'Detect Tophat'}))

    metricList.append(configureMetric('TransientMetric', plotDict=plotDict,summaryStats=stats,
                                      kwargs={'riseSlope':-0.5, 'declineSlope':0.5,'transDuration':20,
                                              'metricName':'Alert'}) )

    # Demand 2 points before tmax before counting the LC as detected
    metricList.append(configureMetric('TransientMetric', plotDict=plotDict,summaryStats=stats,
                         kwargs={'riseSlope':-0.5, 'declineSlope':0.5,'transDuration':20,
                                 'nDetect':2,
                                 'metricName':'Detect on rise'}) )

    # Demand at least 1 filter sample the lightcurve at 3 well-spaced points
    metricList.append( configureMetric('TransientMetric', plotDict=plotDict,summaryStats=stats,
                         kwargs={'riseSlope':-0.5, 'declineSlope':0.5,'transDuration':20,
                                 'nPerLC':3 ,
                                 'metricName':'3ptsPerLC'}))
    # Demand at least 2 filters sample the lightcurve at 3 well-spaced points
    metricList.append( configureMetric('TransientMetric', plotDict=plotDict,summaryStats=stats,
                         kwargs={'riseSlope':-0.5, 'declineSlope':0.5,'transDuration':20,
                                 'nPerLC':3 , 'nFilters':2,
                                 'metricName':'3ptsPerLC2Filt'}))

    # Demand at least 1 filters sample the lightcurve at 6 well-spaced points
    metricList.append( configureMetric('TransientMetric', plotDict=plotDict,summaryStats=stats,
                         kwargs={'riseSlope':-0.5, 'declineSlope':0.5,'transDuration':20,
                                 'nPerLC':6 , 'nFilters':1,
                                 'metricName':'6ptsPerLC'}))



    metricDict = makeDict(*metricList)
    slicer = configureSlicer('HealpixSlicer',kwargs={"nside":nside},
                             metricDict=metricDict, constraints=[''])
    slicerList.append(slicer)

    slicer = configureSlicer('HealpixSlicer',
                             kwargs={"nside":nside,
                                     'spatialkey1':"ditheredRA",
                                     'spatialkey2':"ditheredDec"},
                             metricDict=metricDict, constraints=[''],
                             metadata='dithered')
    slicerList.append(slicer)



    config.slicers=makeDict(*slicerList)
    return config
