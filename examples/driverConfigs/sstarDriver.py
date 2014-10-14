# A MAF config that replicates the SSTAR plots

import os
from lsst.sims.maf.driver.mafConfig import configureSlicer, configureMetric, makeDict
import lsst.sims.maf.utils as utils


def mConfig(config, runName, dbDir='.', outputDir='Out', slicerName='HealpixSlicer',
            benchmark='design', **kwargs):
    """
    A MAF config for SSTAR-like analysis of an opsim run.

    runName must correspond to the name of the opsim output
        (minus '_sqlite.db', although if added this will be stripped off)

    dbDir is the directory the database resides in

    outputDir is the output directory for MAF

    Uses 'slicerName' for metrics which have the option of using
      [HealpixSlicer, OpsimFieldSlicer, or HealpixSlicerDither] 
      (dithered healpix slicer uses ditheredRA/dec values).

    Uses 'benchmark' (which can be design or stretch) to scale plots of number of visits and coadded depth.
    """

    # Setup Database access
    config.outputDir = outputDir
    if runName.endswith('_sqlite.db'):
        runName = runName.replace('_sqlite.db', '')
    sqlitefile = os.path.join(dbDir, runName + '_sqlite.db')
    config.dbAddress ={'dbAddress':'sqlite:///'+sqlitefile}
    config.opsimName = runName
    config.figformat = 'pdf'

    #### Set up parameters for configuring plotting dictionaries and identifying WFD proposals.

    # Connect to the database to fetch some values we're using to help configure the driver.
    opsimdb = utils.connectOpsimDb(config.dbAddress)

    # Fetch the proposal ID values from the database
    propids, WFDpropid, DDpropid = opsimdb.fetchPropIDs()

    # Construct a WFD SQL where clause so multiple propIDs can query by WFD:
    wfdWhere = ''
    if len(WFDpropid) == 1:
        wfdWhere = "propID = %d" %(WFDpropid[0])
    else: 
        for i,propid in enumerate(WFDpropid):
            if i == 0:
                wfdWhere = wfdWhere+'('+'propID = %d ' %(propid)
            else:
                wfdWhere = wfdWhere+'or propID = %d ' %(propid)
        wfdWhere = wfdWhere+')'


    # Fetch the total number of visits (to create fraction for number of visits per proposal)
    totalNVisits = opsimdb.fetchNVisits()

    # Filter list, and map of colors (for plots) to filters.
    filters = ['u','g','r','i','z','y']
    colors={'u':'m','g':'b','r':'g','i':'y','z':'r','y':'k'}
    filtorder = {'u':1,'g':2,'r':3,'i':4,'z':5,'y':6}

    # Set up benchmark values for Stretch and Design, scaled to length of opsim run.
    runLength = opsimdb.fetchRunLength()
    design, stretch = utils.scaleStretchDesign(runLength)

    # Set zeropoints and normalization values for plots (and range for nvisits plots).
    if benchmark == 'stretch':
        sky_zpoints = stretch['skybrightness']
        seeing_norm = stretch['seeing']
        mag_zpoints = stretch['coaddedDepth']
        nvisitBench = stretch['nvisits']
    else:
        sky_zpoints = design['skybrightness']
        seeing_norm = design['seeing']
        mag_zpoints = design['coaddedDepth']
        nvisitBench = design['nvisits']
    # make sure nvisitBench not zero
    for key in nvisitBench.keys():
        if nvisitBench[key] == 0:
            print 'Changing nvisit benchmark value to not be zero.'
            nvisitBench[key] = 1
            
    # Set range of values for visits plots.
    
    nVisits_plotRange = {'all':
                         {'u':[25, 75], 'g':[50,100], 'r':[150, 200], 'i':[150, 200],
                          'z':[100, 250], 'y':[100,250]},
                         'DDpropid':
                         {'u':[6000, 10000], 'g':[2500, 5000], 'r':[5000, 8000], 'i':[5000, 8000],
                          'z':[7000, 10000], 'y':[5000, 8000]}}

    # Set slicer name and kwargs, so that we can vary these from the command line.
    slicerNames = ['HealpixSlicer', 'HealpixSlicerDither', 'OpsimFieldSlicer']
    if slicerName == 'HealpixSlicer':
        slicerName = 'HealpixSlicer'
        nside = 128
        slicerkwargs = {'nside':nside}
        slicermetadata = ''
    elif slicerName == 'HealpixSlicerDither':
        slicerName = 'HealpixSlicer'
        nside = 128
        slicerkwargs = {'nside':nside, 'spatialkey1':'ditheredRA', 'spatialkey2':'ditheredDec'}
        slicermetadata = ' dithered'
    elif slicerName == 'OpsimFieldSlicer':
        slicerName = 'OpsimFieldSlicer'
        slicerkwargs = {}
        slicermetadata = ''
    else:
        raise ValueError('Do not understand slicerName %s: looking for one of %s' %(slicerName, slicerNames))
    print 'Using slicer %s for generic metrics over the sky.' %(slicerName)

    ####

    # Configure some standard summary statistics dictionaries to apply to appropriate metrics.

    # Note there's a complication here, you can't configure multiple versions of a summary metric since that makes a
    # dict with repeated keys.  One kinda workaround is to add blank space (or even more words) to one of
    # the keys that gets stripped out when the object is instatiated.
    standardStats={'MeanMetric':{}, 'RmsMetric':{}, 'MedianMetric':{}, 'CountMetric':{},
                   'NoutliersNsigma 1':{'metricName':'p3Sigma', 'nSigma':3.},
                   'NoutliersNsigma 2':{'metricName':'m3Sigma', 'nSigma':-3.}}
    percentileStats={'PercentileMetric 1':{'metricName':'25th%ile', 'percentile':25},
                     'PercentileMetric 2':{'metricName':'50th%ile', 'percentile':50},
                     'PercentileMetric 3':{'metricName':'75th%ile', 'percentile':75}}
    allStats = standardStats.copy()
    allStats.update(percentileStats)
    ####
    # Start specifying metrics and slicers for MAF to run.

    slicerList=[]
    histNum = 0

    ## Metrics calculating values over the sky (healpix or opsim slicer)
    # Loop over a set of standard analysis metrics, for All Proposals together and for WFD only.
    startNum = histNum
    for i, prop in enumerate(['All Props', 'WFD']):
        startNum += 100
        for f in filters:
            # Set some per-proposal information.
            if prop == 'All Props':
                propCaption = ' for all proposals'
                metadata = '%s band all proposals' %(f) + slicermetadata
                sqlconstraint = ['filter = "%s"' %(f)]
            if prop == 'WFD':
                propCaption = ' for WFD only'
                metadata = '%s band WFD only' %(f) + slicermetadata
                sqlconstraint = ['filter = "%s" and %s' %(f, wfdWhere)]
            # Reset histNum (for merged histograms, merged over all filters).
            histNum = startNum
            # Configure the metrics to run for this sql constraint (all proposals/wfd and filter combo).
            metricList = []
            # Count the total number of visits.
            metricList.append(configureMetric('CountMetric',
                                              kwargs={'col':'expMJD', 'metricName':'Nvisits'},
                                              plotDict={'units':'Number of Visits',
                                                'xMin':nVisits_plotRange['all'][f][0],
                                                'xMax':nVisits_plotRange['all'][f][1]},
                                            summaryStats=standardStats,
                                            displayDict={'group':'2: Nvisits', 'subgroup':prop, 'order':filtorder[f],
                                            'caption':'Number of visits in filter %s, %s.' %(f, propCaption)},
                                            histMerge={'histNum':histNum, 'color':colors[f], 'label':'%s'%(f),
                                                       'binsize':5, 'xMin':nVisits_plotRange['all'][f][0],
                                                       'xMax':nVisits_plotRange['all'][f][1],
                                                       'legendloc':'upper right'}))
            histNum += 1
            # Count the number of visits as a ratio against a benchmark value.
            metricList.append(configureMetric('CountRatioMetric',
                                              kwargs={'col':'expMJD', 'normVal':nvisitBench[f], 'metricName':'NVisitsRatio'},
                                            plotDict={ 'binsize':0.05,'cbarFormat':'%2.2f',
                                                        'xMin':0.5, 'xMax':1.5,
                                                'units':'Number of Visits/Benchmark (%d)' %(nvisitBench[f])},
                                        displayDict={'group':'2: Nvisits', 'subgroup':'%s, ratio' %(prop), 'order':filtorder[f],
                                                'caption': 'Number of visits in filter %s divided by %s value (%d), %s.'
                                                %(f, benchmark, nvisitBench[f], propCaption)},
                                        histMerge={'histNum':histNum, 'color':colors[f], 'label':'%s'%(f),
                                                   'xlabel':'Number of visits / benchmark',
                                                   'binsize':.05, 'xMin':0.5, 'xMax':1.5, 'legendloc':'upper right'}))
            histNum += 1
            # Calculate the median individual visit five sigma limiting magnitude.
            metricList.append(configureMetric('MedianMetric', kwargs={'col':'fiveSigmaDepth'},
                                summaryStats=standardStats,
                                displayDict={'group':'Single Visit Depth', 'subgroup':prop, 'order':filtorder[f],
                                            'caption':'Median single visit depth in filter %s, %s.' %(f, propCaption)}))
            # Calculate the coadded five sigma limiting magnitude (normalized to a benchmark).
            metricList.append(configureMetric('Coaddm5Metric',
                                              plotDict={'zp':mag_zpoints[f],
                                                        'percentileClip':95.,
                                                        'units':'coadded m5 - %.1f' %mag_zpoints[f]},
                                                summaryStats=allStats,
                                                histMerge={'histNum':histNum, 'legendloc':'upper right',
                                                        'color':colors[f], 'label':'%s' %f, 'binsize':.02},
                                                displayDict={'group':'3: CoaddDepth', 'subgroup':prop, 'order':filtorder[f],
                                                            'caption':
                                                'Coadded depth in filter %s, with %s value subtracted (%.1f), %s.'
                                                %(f, benchmark, mag_zpoints[f], propCaption)}))
            histNum += 1
            # Calculate the median individual visit sky brightness (normalized to a benchmark).
            metricList.append(configureMetric('MedianMetric',
                                              kwargs={'col':'filtSkyBrightness'},
                                            plotDict={'zp':sky_zpoints[f], 'units':'Skybrightness - %.2f' %(sky_zpoints[f])},
                                            displayDict={'group':'Sky Brightness', 'subgroup':prop, 'order':filtorder[f],
                                            'caption':
                                            'Median Sky Brightness in filter %s with expected zeropoint (%.2f) subtracted, %s.'
                                            %(f, sky_zpoints[f], propCaption)}))
            # Calculate the median delivered seeing.
            metricList.append(configureMetric('MedianMetric', kwargs={'col':'finSeeing'},
                                    plotDict={'normVal':seeing_norm[f],
                                                'units':'Median Seeing/(Expected seeing %.2f)'%(seeing_norm[f])},
                                    displayDict={'group':'Seeing', 'subgroup':prop, 'order':filtorder[f],
                                                'caption':
                                                'Median Seeing in filter %s divided by expected value (%.2f), %s.'
                                                %(f, seeing_norm[f], propCaption)}))
            # Calculate the median airmass.
            metricList.append(configureMetric('MedianMetric',
                                              kwargs={'col':'airmass'},
                                              plotDict={'units':'X'},
                                              displayDict={'group':'Airmass', 'subgroup':prop, 'order':filtorder[f],
                                                        'caption':'Median airmass in filter %s, %s.' %(f, propCaption)}))
            # Calculate the median normalized airmass.
            metricList.append(configureMetric('MedianMetric',
                                              kwargs={'col':'normairmass'},
                                              plotDict={'units':'X'},
                                              displayDict={'group':'Airmass', 'subgroup':prop, 'order':filtorder[f],
                                                        'caption':'Median normalized airmass in filter %s, %s.'
                                                        %(f, propCaption)}))
            # Calculate the maximum airmass.
            metricList.append(configureMetric('MaxMetric',
                                              kwargs={'col':'airmass'},
                                              plotDict={'units':'X'},
                                              displayDict={'group':'Airmass', 'subgroup':prop, 'order':filtorder[f],
                                            'caption':'Max airmass in filter %s, %s.' %(f, propCaption)}))
            metricDict = makeDict(*metricList)
            slicer = configureSlicer(slicerName, kwargs=slicerkwargs, metricDict=metricDict,
                                     constraints=sqlconstraint, metadata=metadata, metadataVerbatim=True)
            slicerList.append(slicer)

    # Count the number of visits per filter for each proposal, over the sky. Uses opsim field slicer.
    propOrder = 0
    for propid in propids:
        # Skip the wfd proposals.
        if propid in WFDpropid:
            continue
        for f in filters:
            # Count the number of visits.
            m1 = configureMetric('CountMetric',
                                kwargs={'col':'expMJD', 'metricName':'NVisits Per Proposal'},
                                summaryStats=standardStats,
                                plotDict={'units':'Number of Visits', 'bins':50},
                                displayDict={'group':'2: Nvisits', 'subgroup':'Per Prop', 'order':filtorder[f] + propOrder,
                                             'caption':'Number of visits per opsim field in %s filter, for propID %d'
                                             %(f, propid)},
                                histMerge={'histNum':histNum, 'legendloc':'upper right', 'color':colors[f],
                                           'label':'%s' %f, 'binsize':2, 'xMin':0,
                                           'xMax':nVisits_plotRange['all'][f][1]})
            metricDict = makeDict(m1)
            sqlconstraint = ['filter = "%s" and propID = %s' %(f, propid)]
            slicer = configureSlicer('OpsimFieldSlicer',
                                     metricDict=metricDict,
                                     constraints=sqlconstraint,
                                     metadata='%s band and %s proposal' %(f, propid),
                                     metadataVerbatim=True)
            slicerList.append(slicer)
        histNum += 1
        propOrder += 100
    # Run for WFD prop.
    for f in filters:
        m1 = configureMetric('CountMetric',
                             kwargs={'col':'expMJD', 'metricName':'NVisits Per Proposal'},
                             summaryStats=standardStats,
                             plotDict={'units':'Number of Visits', 'bins':50},
                             displayDict={'group':'2: Nvisits', 'subgroup':'Per Prop', 'order':filtorder[f] + propOrder,
                                          'caption':'Number of visits per opsim field in %s filter, for WFD.' %(f)},
                             histMerge={'histNum':histNum, 'legendloc':'upper right',
                                        'color':colors[f], 'label':'%s' %f, 'binsize':2, 'xMin':0,
                                        'xMax':nVisits_plotRange['all']['%s' %f][1]})
        metricDict = makeDict(m1)
        sqlconstraint = ['filter = "%s" and %s' %(f, wfdWhere)]
        slicer = configureSlicer('OpsimFieldSlicer', metricDict=metricDict, constraints=sqlconstraint,
                                 metadata='%s band and WFD proposal' %(f), metadataVerbatim=True)
        slicerList.append(slicer)
    histNum += 1

    # Calculate the Completeness and Joint Completeness for all proposals and WFD only.
    for prop in ('All Props', 'WFD'):
        if prop == 'All Props':
            metadata = 'all proposals'
            sqlconstraint = ['']
            xlabel = '# visits (WFD only) / (# WFD %s value)' %(benchmark)
        if prop == 'WFD':
            metadata = 'WFD only'
            sqlconstraint = ['%s' %(wfdWhere)]
            xlabel = '# visits (All Props) / (# WFD %s value)' %(benchmark)
        # Configure completeness metric.
        m1 = configureMetric('CompletenessMetric',
                            plotDict={'xlabel':xlabel,
                                        'units':xlabel,
                                        'xMin':0.5, 'xMax':1.5, 'bins':50},
                            kwargs={'u':nvisitBench['u'], 'g':nvisitBench['g'], 'r':nvisitBench['r'],
                                    'i':nvisitBench['i'], 'z':nvisitBench['z'], 'y':nvisitBench['y']},
                            summaryStats={'TableFractionMetric':{}},
                            displayDict={'group':'4: Completeness', 'subgroup':prop})
        metricDict = makeDict(m1)
        slicer = configureSlicer('OpsimFieldSlicer', metricDict=metricDict,
                                constraints=sqlconstraint, metadata=metadata, metadataVerbatim=True)
        slicerList.append(slicer)


    # Calculate the fO metrics for all proposals and WFD only.
    fOnside = 64
    for prop in ('All Prop', 'WFD only'):
        if prop == 'All Prop':
            metadata = 'all proposals'
            sqlconstraint = ['']
        if prop == 'WFD only':
            metadata = 'WFD only'
            sqlconstraint = ['%s' %(wfdWhere)]
        # Configure the count metric which is what is used for f0 slicer.
        m1 = configureMetric('CountMetric',
                            kwargs={'col':'expMJD', 'metricName':'fO'},
                            plotDict={'units':'Number of Visits',
                                      'xMin':0,
                                      'xMax':1500},
                            summaryStats={'fOArea':{'nside':fOnside},
                                            'fONv':{'nside':fOnside}},
                            displayDict={'group':'Technical', 'subgroup':'F0', 'caption':
                                        'FO metric: evaluates the overall efficiency of observing.'})
        slicer = configureSlicer('fOSlicer', kwargs={'nside':fOnside},
                                 metricDict=makeDict(m1), constraints=sqlconstraint, metadata=metadata, metadataVerbatim=True)
        slicerList.append(slicer)

    ## End of all-sky metrics.

    ## Hourglass metric.

    # Calculate Filter Hourglass plots per year (split to make labelling easier).
    yearDates = range(0,int(round(365*runLength))+365,365)
    for i in range(len(yearDates)-1):
        constraints = ['night > %i and night <= %i'%(yearDates[i],yearDates[i+1])]
        m1=configureMetric('HourglassMetric',
                           displayDict={'group':'Hourglass', 'order':i})
        slicer = configureSlicer('HourglassSlicer', metricDict=makeDict(m1), constraints=constraints,
                                 metadata='Year %i-%i' %(i, i+1), metadataVerbatim=True)
        slicerList.append(slicer)

    ## Histograms. (one-d slicers).

    # Histograms per filter for WFD only (generally used to produce merged histograms).
    startNum = histNum
    for f in filters:
        metadata = '%s band WFD only' %(f)
        # Reset histNum to starting value (to combine filters).
        histNum = startNum
        # Histogram the individual visit five sigma limiting magnitude.
        m1 = configureMetric('CountMetric',
                             kwargs={'col':'fiveSigmaDepth', 'metricName':'Single Visit Depth Histogram'},
                             histMerge={'histNum':histNum, 'legendloc':'upper right',
                                       'color':colors[f], 'label':'%s'%f},
                            displayDict={'group':'Single Visit Depth', 'subgroup':'WFD', 'order':filtorder[f],
                                         'caption':'Histogram of the single visit depth in %s band, WFD only.' %(f)})
        histNum += 1
        slicer = configureSlicer('OneDSlicer', kwargs={'sliceColName':'fiveSigmaDepth', 'binsize':0.05},
                                metricDict=makeDict(m1), constraints=["filter = '%s' and %s" %(f, wfdWhere)],
                                metadata=metadata, metadataVerbatim=True)
        slicerList.append(slicer)
        # Histogram the individual visit sky brightness.
        m1 = configureMetric('CountMetric', kwargs={'col':'filtSkyBrightness', 'metricName':'Sky Brightness Histogram'},
                            histMerge={'histNum':histNum, 'legendloc':'upper right',
                                       'color':colors[f], 'label':'%s'%f},
                            displayDict={'group':'Sky Brightness', 'subgroup':'WFD', 'order':filtorder[f],
                                         'caption':'Histogram of the sky brightness in %s band, WFD only.' %(f)})
        histNum += 1
        slicer = configureSlicer('OneDSlicer', kwargs={'sliceColName':'filtSkyBrightness', 'binsize':0.1,
                                                       'binMin':16, 'binMax':23},
                                metricDict=makeDict(m1), constraints=["filter = '%s' and %s"%(f, wfdWhere)],
                                metadata=metadata, metadataVerbatim=True)
        slicerList.append(slicer)
        # Histogram the individual visit seeing.
        m1 = configureMetric('CountMetric', kwargs={'col':'finSeeing', 'metricName':'Seeing Histogram'},
                            histMerge={'histNum':histNum, 'legendloc':'upper right',
                                       'color':colors[f],'label':'%s'%f},
                            displayDict={'group':'Seeing', 'subgroup':'WFD', 'order':filtorder[f],
                                         'caption':'Histogram of the seeing in %s band, WFD only.' %(f)} )
        histNum += 1
        slicer = configureSlicer('OneDSlicer', kwargs={'sliceColName':'finSeeing', 'binsize':0.02},
                                metricDict=makeDict(m1), constraints=["filter = '%s' and %s"%(f, wfdWhere)],
                                metadata=metadata, metadataVerbatim=True)
        slicerList.append(slicer)
        # Histogram the individual visit airmass values.
        m1 = configureMetric('CountMetric', kwargs={'col':'airmass', 'metricName':'Airmass Histogram'},
                             histMerge={'histNum':histNum, 'legendloc':'upper right',
                                       'color':colors[f], 'label':'%s'%f, 'xMin':1.0, 'xMax':2.0},
                            displayDict={'group':'Airmass', 'subgroup':'WFD', 'order':filtorder[f],
                                         'caption':'Histogram of the airmass in %s band, WFD only.' %(f)})
        histNum += 1
        slicer = configureSlicer('OneDSlicer', kwargs={'sliceColName':'airmass', 'binsize':0.01},
                                metricDict=makeDict(m1), constraints=["filter = '%s' and %s"%(f, wfdWhere)],
                                metadata=metadata, metadataVerbatim=True)
        slicerList.append(slicer)

   # Slew histograms (time and distance).
    m1 = configureMetric('CountMetric', kwargs={'col':'slewTime', 'metricName':'Slew Time Histogram'},
                         plotDict={'logScale':True, 'ylabel':'Count'},
                         displayDict={'group':'Technical', 'subgroup':'Slew',
                                      'caption':'Histogram of slew times for all visits.'})
    slicer = configureSlicer('OneDSlicer', kwargs={'sliceColName':'slewTime', 'binsize':5},
                              metricDict=makeDict(m1), constraints=[''])
    slicerList.append(slicer)
    m1 = configureMetric('CountMetric', kwargs={'col':'slewDist', 'metricName':'Slew Distance Histogram'},
                         plotDict={'logScale':True, 'ylabel':'Count'},
                         displayDict={'group':'Technical', 'subgroup':'Slew',
                                      'caption':'Histogram of slew distances for all visits.'})
    slicer = configureSlicer('OneDSlicer', kwargs={"sliceColName":'slewDist', 'binsize':.05},
                              metricDict=makeDict(m1), constraints=[''])
    slicerList.append(slicer)

    # Plots per night -- the number of visits and the open shutter time fraction.
    m1 = configureMetric('CountMetric', kwargs={'col':'expMJD'},
                          summaryStats=standardStats,
                          displayDict={'group':'Technical', 'subgroup':'Obs Time',
                                       'caption':'Number of visits per night.'})
    m2 = configureMetric('OpenShutterFractionMetric', 
                         summaryStats=standardStats,
                         displayDict={'group':'Technical', 'subgroup':'Obs Time',
                                      'caption':'Open shutter fraction per night.'})
    slicer = configureSlicer('OneDSlicer', kwargs={'sliceColName':'night','binsize':1},
                             metricDict=makeDict(m1, m2),
                             constraints=[''])
    slicerList.append(slicer)

    ## Unislicer (single number) metrics.

    # Calculate some basic summary info about run, per filter, per proposal and for all proposals.
    propOrder = 0
    props = propids + ['All Props'] + ['WFD']
    for i, propid in enumerate(props):
        propOrder += 100
        order = propOrder
        for f in filters:
            if propid in WFDpropid:
                # Skip individual WFD propids (do in 'WFD')
                continue
            if propid == 'All Props':
                subgroup = 'All Props'
                sqlconstraint = ['filter = "%s"' %(f)]
                metadata = '%s band, all props' %(f)
            elif propid == 'WFD':
                subgroup = 'WFD'
                sqlconstraint = ['filter = "%s" and %s' %(f, wfdWhere)]
                metadata = '%s band and WFD only' %(f)
            else:
                subgroup = 'Per Prop'
                sqlconstraint = ['filter = "%s" and propId=%d' %(f, propid)]
                metadata = '%s band and propId=%d' %(f, propid)
            metricList = []
            cols = ['finSeeing', 'filtSkyBrightness', 'airmass', 'fiveSigmaDepth']
            groups = ['Seeing', 'Sky Brightness', 'Airmass', 'Single Visit Depth']
            for col, group in zip(cols, groups):
                metricList.append(configureMetric('MedianMetric', kwargs={'col':col},
                                                displayDict={'group':group, 'subgroup':subgroup, 'order':order}))
                order += 1
                metricList.append(configureMetric('MeanMetric', kwargs={'col':col},
                                                    displayDict={'group':group, 'subgroup':subgroup,
                                                                'order':order}))
                order += 1
                metricList.append(configureMetric('RmsMetric', kwargs={'col':col},
                                                    displayDict={'group':group, 'subgroup':subgroup, 'order':order}))
                order += 1
                metricList.append(configureMetric('NoutliersNsigma',
                                                    kwargs={'col':col, 'metricName':'p3Sigma %s' %(col)},
                                                    displayDict={'group':group, 'subgroup':subgroup, 'order':order}))
                order += 1
                metricList.append(configureMetric('NoutliersNsigma',
                                                  kwargs={'col':col, 'metricName':'m3Sigma %s' %(col)},
                                                  displayDict={'group':group, 'subgroup':subgroup, 'order':order}))
                order += 1
                metricList.append(configureMetric('CountMetric', kwargs={'col':col, 'metricName':'Count %s' %(col)},
                                                  displayDict={'group':group, 'subgroup':subgroup, 'order':order}))
                order += 1
                metricList.append(configureMetric('PercentileMetric',
                                                    kwargs={'col':col, 'percentile':25},
                                                    displayDict={'group':group, 'subgroup':subgroup,
                                                                'order':order}))
                order += 1
                metricList.append(configureMetric('PercentileMetric',
                                                    kwargs={'col':col, 'percentile':50},
                                                    displayDict={'group':group, 'subgroup':subgroup,
                                                                'order':order}))
                order += 1
                metricList.append(configureMetric('PercentileMetric',
                                                    kwargs={'col':col, 'percentile':75},
                                                    displayDict={'group':group, 'subgroup':subgroup,
                                                                'order':order}))
                order += 1
            slicer = configureSlicer('UniSlicer', metricDict=makeDict(*metricList),
                                    constraints=sqlconstraint, metadata=metadata, metadataVerbatim=True)
            slicerList.append(slicer)


    # Some other summary statistics over all filters and all proposals.
    # Calculate the mean and median slewtime.
    m1 = configureMetric('MeanMetric', kwargs={'col':'slewTime'},
                         displayDict={'group':'Technical', 'subgroup':'Slew'})
    m2 = configureMetric('MedianMetric', kwargs={'col':'slewTime'},
                         displayDict={'group':'Technical', 'subgroup':'Slew'})
    # Calculate the total number of visits.
    m3 = configureMetric('CountMetric', kwargs={'col':'expMJD', 'metricName':'TotalNVisits'},
                         summaryStats={'IdentityMetric':{'metricName':'Count'}},
                         displayDict={'group':'1: Summary', 'subgroup':'NVisits', 'order':0})
    # Calculate the total open shutter time.
    m4 = configureMetric('SumMetric', kwargs={'col':'visitExpTime', 'metricName':'Open Shutter Time'},
                         summaryStats={'IdentityMetric':{'metricName':'Time (s)'}},
                         displayDict={'group':'1: Summary', 'subgroup':'On-sky Time'})
    metricDict = makeDict(m1, m2, m3, m4)
    slicer = configureSlicer('UniSlicer', metricDict=metricDict, constraints=[''], metadata='All Visits',
                             metadataVerbatim=True)
    slicerList.append(slicer)

    # Count the number of visits per proposal, for all proposals, as well as the ratio of number of visits
    #  for each proposal compared to total number of visits.
    for propid in propids:
        # Skip the wfd proposals.
        if propid in WFDpropid:
            continue
        sqlconstraint = ['propID = %s' %(propid)]
        m1 = configureMetric('CountMetric', kwargs={'col':'expMJD', 'metricName':'NVisits Per Proposal'},
                             summaryStats={'IdentityMetric':{'metricName':'Count'},
                                           'NormalizeMetric':{'normVal':totalNVisits, 'metricName':'Fraction of total'}},
                            displayDict={'group':'1: Summary', 'subgroup':'NVisits'})
        slicer = configureSlicer('UniSlicer', metricDict=makeDict(m1), constraints=sqlconstraint)
        slicerList.append(slicer)
    # Count visits in WFD (as well as ratio of number of visits compared to total number of visits).
    sqlconstraint = ['%s' %(wfdWhere)]
    slicer = configureSlicer('UniSlicer', metricDict=makeDict(m1),
                            constraints=sqlconstraint, metadata='WFD only', metadataVerbatim=True)
    slicerList.append(slicer)

    config.slicers=makeDict(*slicerList)
    return config


