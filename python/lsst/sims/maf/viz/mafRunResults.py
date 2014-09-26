import os
from collections import OrderedDict
import numpy as np
from numpy.lib.recfunctions import rec_join, merge_arrays
import lsst.sims.maf.db as db

class MafRunResults(object):
    """
    Class to read MAF's resultsDb_sqlite.db and organize the output for display on web pages.

    Deals with a single MAF run (one output directory, one resultsDb) only. """
    def __init__(self, outDir, resultsDbAddress=None):
        """
        Instantiate the (individual run) layout visualization class.

        This class provides methods used by our jinja2 templates to help interact
        with the outputs of MAF. 
        """
        self.outDir = os.path.relpath(outDir, '.')

        self.configSummary = os.path.join(self.outDir, 'configSummary.txt')
        if not os.path.isfile(self.configSummary):
            self.configSummary = 'Config Summary Not Available'
            self.runName = 'RunName Not Available'
        else:
            with open (self.configSummary, "r") as myfile:
                config=myfile.read().replace('\n', '')
            spot = config.find('RunName')
            self.runName = config[spot:spot+300].split(' ')[1]

        self.configDetails = os.path.join(self.outDir, 'configDetails.txt')
        if not os.path.isfile(self.configDetails):
            self.configDetails = 'Config Details Not Available.'


        # Read in the results database.
        if resultsDbAddress is None:
            sqlitefile = os.path.join(outDir, 'resultsDb_sqlite.db')
            resultsDbAddress = 'sqlite:///'+sqlitefile
        database = db.Database(resultsDbAddress, longstrings=True,
                               dbTables={'metrics':['metrics','metricID'] ,
                                         'displays':['displays', 'displayId'],
                                         'plots':['plots','plotId'],
                                         'stats':['summarystats','statId']})
        # Just pull all three tables.
        # Below, we provide some methods to interface between the numpy rec arrays returned
        #  by these queries and what the templates need. 
        # The idea being that this should make the template code & presentation layer more
        #  easily maintainable in the future.
        self.metrics = database.queryDatabase('metrics', 'select * from metrics')        
        self.displays = database.queryDatabase('displays', 'select * from displays')
        # Combine metrics and displays arrays (these are one-to-one).
        self.metrics = rec_join('metricId', self.metrics, self.displays)
        # Add base metric names (to keep order for reduce methods).
        baseNames = np.empty(len(self.metrics), dtype=[('baseMetricNames', '|S20')])
        for i, m in enumerate(self.metrics):
            baseNames['baseMetricNames'][i] = m['metricName'].split('_')[0]            
        self.metrics = merge_arrays([self.metrics, baseNames], flatten=True, usemask=False)
        self.metrics = self.sortMetrics(self.metrics)
        del self.displays
        # Get plot and summary stat info.
        self.plots = database.queryDatabase('plots', 'select * from plots')
        self.stats = database.queryDatabase('stats', 'select * from summarystats')

        # Remove metrics which have no summary stats or plots.

        # Make empty arrays if there was nothing in the database
        if len(self.plots) == 0:
            self.plots = np.zeros(0, dtype=[('metricId',int), ('plotFile', '|S10')])
        if len(self.stats) == 0:
            self.stats = np.zeros(0, dtype=[('metricId',int), ('summaryName', '|S10'), ('summaryValue', float)])

        # Replace summary stat names "Identity" with a blank string
        match = (self.stats['summaryName'] == 'Identity')
        self.stats['summaryName'][match] = ' '
                    
        # Pull up the names of the groups and subgroups. 
        groups = sorted(list(np.unique(self.metrics['displayGroup'])))
        self.groups = OrderedDict()
        for g in groups:
            self.groups[g] = set()
        for metric in self.metrics:
            self.groups[metric['displayGroup']].add(metric['displaySubgroup'])
        for g in self.groups:
            self.groups[g] = sorted(list(self.groups[g]))

        self.summaryStatOrder = ['Identity', 'Count', 'Mean', 'Median', 'Rms', 'RobustRms', 
                                 'm3Sigma', 'p3Sigma']
        # Add in the table fraction sorting.  
        tableFractions = list(set([name for name in self.stats['summaryName'] if 'TableFraction' in name]))
        if len(tableFractions) > 0:
            tableFractions.remove('TableFraction 0 == P')
            tableFractions.remove('TableFraction 1 == P')
            tableFractions.remove('TableFraction 1 < P')
            tableFractions = sorted(tableFractions)
            self.summaryStatOrder.append('TableFraction 0 == P')
            for tableFrac in tableFractions:
                self.summaryStatOrder.append(tableFrac)
            self.summaryStatOrder.append('TableFraction 1 == P')
            self.summaryStatOrder.append('TableFraction 1 < P')
        
        self.plotOrder = ['SkyMap', 'Histogram', 'PowerSpectrum']

        
    ## Methods to deal with metricIds
                
    def convertSelectToMetrics(self, groupList, metricIdList):
        """
        Convert the lists of values returned by 'select metrics' template page 
        into an appropriate numpy recarray of metrics (in sorted order).
        """
        metricIds = set()    
        for group_subgroup in groupList:
            group = group_subgroup.split('_')[0]
            subgroup = group_subgroup.split('_')[-1].replace('+', ' ')
            mIds = self.metricIdsInSubgroup(group, subgroup)
            for mId in mIds:
                metricIds.add(mId)
        for mId in metricIdList:
            mId = int(mId)
            metricIds.add(mId)
        metrics = self.metricIdsToMetrics(metricIds)
        return self.sortMetrics(metrics)

    def metricIdsInSubgroup(self, group, subgroup):
        """
        Return the metricIds within a given group/subgroup.
        """
        metrics = self.metricsInSubgroup(group, subgroup)
        metricIds = metrics['metricId']
        return list(metricIds)
    
    def metricIdsToMetrics(self, metricIds):
        """
        Return an ordered numpy recarray of metrics matching metricIds.
        """
        metrics = np.empty(len(metricIds), dtype=self.metrics.dtype)
        for i, mId in enumerate(metricIds):
            match = (self.metrics['metricId'] == mId)
            metrics[i] = self.metrics[match]
        return metrics
            
    ## Methods to deal with metrics in numpy recarray.
        
    def sortMetrics(self, metrics, order=['displayGroup', 'displaySubgroup',
                                          'baseMetricNames', 'slicerName', 'displayOrder', 
                                          'metricMetadata']):
        """
        Sort the metrics by group, subgroup, base metric name (pre '_'), order, slicer, and then finally metadata. 
        """
        return np.sort(metrics, order=order)    

    def metricsInGroup(self, group, metrics=None):
        """
        Given a group, return the metrics belonging to this group, in display order.
        """
        if metrics is None:
            metrics = self.metrics
        match = (metrics['displayGroup'] == group)
        return self.sortMetrics(metrics[match])
        
    def metricsInSubgroup(self, group, subgroup, metrics=None):
        """
        Given a group and subgroup, return the metrics belonging to these group/subgroups, in display order.

        If 'metrics' is provided, then only consider this subset of metrics.
        """
        metrics = self.metricsInGroup(group, metrics)
        match = (metrics['displaySubgroup'] == subgroup)
        metrics = metrics[match]
        return self.sortMetrics(metrics)

    def metricsToSubgroups(self, metrics):
        """
        Given a recarray of metrics, return an ordered dict of their group/subgroups.
        """
        metrics = self.sortMetrics(metrics)
        grouplist= sorted(list(np.unique(metrics['displayGroup'])))
        groups = OrderedDict()
        for g in grouplist:
            groups[g] = set()
        for metric in metrics:
            groups[metric['displayGroup']].add(metric['displaySubgroup'])
        for g in groups:
            groups[g] = sorted(list(groups[g]))
        return groups

    def metricsWithPlotType(self, plotType='SkyMap', metrics=None):
        """
        Return metrics with skymaps in this group/subgroup (optional, metric subset).
        """
        if metrics is None:
            metrics = self.metrics
        hasplot = np.zeros(len(metrics))
        for i, m in enumerate(metrics):
            match = (self.plots['metricId'] == m['metricId'])
            matchType = (self.plots['plotType'][match] == plotType)
            if len(metrics[matchType]) > 0:
                hasplot[i] = 1
        metrics = metrics[np.where(hasplot > 0)]
        return metrics

    def metricNames(self, metrics=None, baseonly=True):
        """
        Return a list of the unique metric names.
        """
        if metrics is None:
            metrics = self.metrics
        metricNames = set()
        for m in self.sortMetrics(metrics):
            if baseonly:
                metricNames.add(m['baseMetricNames'])
            else:
                metricNames.add(m['metricName'])
        return metricNames

    def metricsWithMetricName(self, metricName, metrics=None, baseonly=True):
        """
        Return all metrics which match metricName.
        """
        if metrics is None:
            metrics = self.metrics
        if baseonly:
            match = (metrics['baseMetricNames'] == metricName)
        else:
            match = (metrics['metricName'] == metricName)
        return metrics[match]
                
    def metricInfo(self, metric, withDataFile=False):
        """
        Return a dict with the metric info we want to show on the webpages.

        Currently : MetricName / Slicer/ Metadata / datafile (for download)
        """
        # Provides a way to easily modify what we show on all webpages without
        #  significantly altering the templates. Or provides an abstraction layer 
        #  in case the resultsDB column names change.
        metricInfo = OrderedDict()
        metricInfo['MetricName'] = metric['metricName']
        metricInfo['Slicer'] = metric['slicerName']
        metricInfo['Metadata'] = metric['metricMetadata']
        if withDataFile:
            metricInfo['Datafile'] = metric['metricDataFile']
        return metricInfo

    def captionForMetric(self, metric):
        """
        Return the caption for a given metric.
        """
        return metric['displayCaption']

    ## Methods for plots.
    
    def plotsForMetric(self, metric):
        """
        Return an ordered dict with the plots matching a given metric.
        """
        plotDict = OrderedDict()
        match = (self.plots['metricId'] == metric['metricId'])
        matchPlots = self.plots[match]
        plotTypes = list(matchPlots['plotType'])
        for o in self.plotOrder:
            if o in plotTypes:
                plotDict[o] = matchPlots[np.where(matchPlots['plotType'] == o)][0]
                plotTypes.remove(o)
        for p in plotTypes:
            plotDict[p] = matchPlots[np.where(matchPlots['plotType'] == p)][0]
        return plotDict

    def getThumbfile(self, plot):
        """
        Return the thumbnail file name for a given plot.
        """
        thumbname =  'thumb.' + ''.join(plot['plotFile'].split('.')[:-1]) + '.png'
        thumbfile = os.path.join(self.outDir, thumbname)
        return thumbfile

    def getPlotfile(self, plot):
        """
        Return the filename for a given plot.
        """
        return os.path.join(self.outDir, plot['plotFile'])

    def getSkyMaps(self, metrics=None):
        """
        Return a list of the skymaps, optionally for subset of metrics.
        """
        if metrics is None:
            metrics = self.metrics
        skymatchPlots = []
        for m in metrics:
            match = (self.plots['metricId'] == m['metricId'])
            matchPlots = self.plots[match]
            if len(matchPlots) > 0 :
                match = (matchPlots['plotType'] == 'SkyMap')
                for skymatch in matchPlots[match]:
                    skymatchPlots.append(skymatch)
        return skymatchPlots

    
    ## Set of methods to deal with stats.
    
    def statsForMetric(self, metric):
        """
        Return the summary statistics which match a given metric.
        """
        match = (self.stats['metricId'] == metric['metricId'])        
        return self.stats[match]
    
    def statDict(self, stats):
        """
        Returns an ordered dictionary with statName/statValue for numpy recarray of stats.

        Note that if you pass 'stats' from multiple metrics with the same summary names, they
         will be overwritten in the resulting dictionary! So just use stats from one metric.
        """
        # Result = dict with key == summary stat name, value = summary stat value. 
        sdict = OrderedDict()
        statnames = self.orderStatNames(stats)
        for n in statnames:
            match = (stats['summaryName'] == n)
            sdict[stats['summaryName'][match][0]] = stats['summaryValue'][match][0]
        return sdict
            
    def orderStatNames(self, stats):
        """
        For a recarray of stats, return a list containing all the unique 'summaryNames'         
        in a default ordering (identity-count-mean-median-rms..).
        """
        names = set()
        for stat in stats:
            names.add(stat['summaryName'])
        # Add some default sorting:
        namelist = []
        for nord in self.summaryStatOrder:
            if nord in names:
                namelist.append(nord)
                names.remove(nord)
        for remaining in names:
            namelist.append(remaining)
        return namelist

    def allStatNames(self, metrics):
        """
        For a recarray of metrics, return a list containing all the unique 'summaryNames'
        in a default ordering. 
        """
        names = set()
        for metric in metrics:
            stats = self.statsForMetric(metric)            
            for stat in stats:
                names.add(stat['summaryName'])
        # Add some default sorting.
        namelist = []
        for nord in self.summaryStatOrder:
            if nord in names:
                namelist.append(nord)
                names.remove(nord)
        for remaining in names:
            namelist.append(remaining)
        return namelist    
