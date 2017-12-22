from builtins import zip
from builtins import range
from builtins import object
import os
import warnings
import numpy as np
import pandas as pd
from lsst.sims.maf.db import ResultsDb
from lsst.sims.maf.db import OpsimDatabase
import lsst.sims.maf.metricBundles as mb
import lsst.sims.maf.plots as plots

__all__ = ['RunComparison']


class RunComparison(object):
    """
    Class to read multiple results databases, find requested summary metric comparisons,
    and stores results in DataFrames in class.

    Set up the runs to compare and opens connections to all resultsDb_sqlite directories under
    baseDir/runlist[1-N] and their subdirectories.
    Expects a directory structure like:
    baseDir -> run1  -> subdirectory1 (e.g. 'scheduler', containing a resultsDb_sqlite.db file)
    ................ -> subdirectoryN
    ....... -> runN -> subdirectoryX

    Parameters
    ----------
    baseDir : str
        The root directory containing all of the underlying runs and their subdirectories.
    runlist : list
        A list of runs to compare.
    rundirs : list
        A list of directories (relative to baseDir) where the runs in runlist reside.
        Optional - if not provided, assumes directories are simply the names of runlist.
    """
    def __init__(self, baseDir, runlist, rundirs=None, verbose=False):
        self.baseDir = baseDir
        self.runlist = runlist
        self.verbose = verbose
        if rundirs is not None:
            self.rundirs = rundirs
        else:
            self.rundirs = runlist
        self._connect_to_results()
        # Class attributes to store the stats data:
        self.parameters = None        # Config parameters varied in each run
        self.summaryStats = None      # summary stats
        self.normalizedStats = None   # normalized (to baselineRun) version of the summary stats
        self.baselineRun = None       # name of the baseline run

    def _connect_to_results(self):
        """
        Open access to all the results database files.
        Sets nested dictionary of results databases:
        .. dictionary[run1][subdirectory1] = resultsDb
        .. dictionary[run1][subdirectoryN] = resultsDb ...
        """
        # Open access to all results database files in any subdirectories under 'runs'.
        self.runresults = {}
        for r, rdir in zip(self.runlist, self.rundirs):
            self.runresults[r] = {}
            if not os.path.isdir(os.path.join(self.baseDir, r)):
                warnings.warn('Warning: could not find a directory containing analysis results at %s'
                              % (os.path.join(self.baseDir, r)))
            else:
                sublist = os.listdir(os.path.join(self.baseDir, r))
                for s in sublist:
                    if os.path.isfile(os.path.join(self.baseDir, r, s, 'resultsDb_sqlite.db')):
                        self.runresults[r][s] = ResultsDb(outDir=os.path.join(self.baseDir, r, s))
        # Remove any runs from runlist which we could not find results databases for.
        for r in self.runlist:
            if len(self.runresults[r]) == 0:
                warnings.warn('Warning: could not find any results databases for run %s'
                              % (os.path.join(self.baseDir, r)))
                self.runlist.remove(r)

    def close(self):
        """
        Close all connections to the results database files.
        """
        self.__del__()

    def __del__(self):
        for r in self.runresults:
            for s in self.runresults[r]:
                self.runresults[r][s].close()

    def variedParameters(self, paramNameLike=None, dbDir=None):
        """
        Query the opsim configuration table for a set of user defined
        configuration parameters for a set of runs.

        Parameters
        ----------
        paramNameLike : list, opt
            A list of of opsim configuration parameters to pull out of the
            configuration table.
        Results
        -------
        pandas DataFrame
            A pandas dataframe containing a column for each of the configuration
            parameters given in paramName like. The resulting dataframe is
            indexed the name of the opsim runs.
            runName      parameter1         parameter2
            <run_123>   <parameterValues1>  <parameterValues1>

        Notes
        -----
        This method will use the sqlite 'like' function to query the
        configuration table. Below is an example of how the items in
        paramNameLike need to be formatted:
        ["%WideFastDeep%hour_angle_bonus%", "%WideFastDeep%airmass_bonus%"].
        """
        if paramNameLike is None:
            paramNameLike = ["%WideFastDeep%airmass_bonus%",
                             "%WideFastDeep%hour_angle_bonus%"]
        sqlconstraints = []
        parameterNames = []
        for p in paramNameLike:
            name = p.rstrip('%').lstrip('%').replace('%', ' ')
            parameterNames.append(name)
            sql = 'paramName like "%s"' % (p)
            sqlconstraints.append(sql)

        # Connect to original databases and grab configuration parameters.
        opsdb = {}
        for r in self.runlist:
            # Check if file exists XXXX
            if dbDir is None:
                opsdb[r] = OpsimDatabase(os.path.join(r, 'data', r + '.db'))
            else:
                opsdb[r] = OpsimDatabase(os.path.join(dbDir, r + '.db'))
                # try also sqlite.db
        parameterValues = {}
        for i, r in enumerate(self.runlist):
            parameterValues[r] = {}
            for pName, sql in zip(parameterNames, sqlconstraints):
                val = opsdb[r].query_columns('Config', colnames=['paramValue'],
                                             sqlconstraint=sql)
                if len(val) > 1.0:
                    warnings.warn(sql + ' returned more than one value.' +
                                  ' Add additional information such as the proposal name' +
                                  '\n' + 'Example: ' + '%WideFastDeep%hour_angle_bonus%')
                    parameterValues[r][pName] = -666
                else:
                    parameterValues[r][pName] = val['paramValue'][0]
                if self.verbose:
                    print('Queried Config Parameters with: ' + sql +
                          '\n' + 'found value: ' + str(parameterValues[r][pName]))
        tempDFList = []
        for r in self.runlist:
            tempDFList.append(pd.DataFrame(parameterValues[r], index=[r]))
        # Concatenate dataframes for each run.
        if self.parameters is None:
            self.parameters = pd.concat(tempDFList)
        else:
            self.parameters = self.parameters.join(tempDFList)

    def buildMetricDict(self, subdir):
        """Build a metric dictionary based on a subdirectory (i.e. a subset of metrics).

        Pulls all summary stats from the results DB in a given subdirectory, for all runs.

        Parameters
        ----------
        subdir: str
           Name of a subdirectory to search for resultsDb

        Returns
        -------
        Dict
           Key = self-created metric 'name', value = [metricName, metricMetadata, slicerName, None]
        """
        mDict = {}
        for r in self.runlist:
            if subdir in os.path.join(r, subdir):
                mIds = self.runresults[r][subdir].getAllMetricIds()
                for mId in mIds:
                    info = self.runresults[r][subdir].getMetricDisplayInfo(mId)
                    metricName = info['metricName'][0]
                    metricMetadata = info['metricMetadata'][0]
                    slicerName = info['slicerName'][0]
                    name = self._buildSummaryName(metricName, metricMetadata, slicerName, None)
                    mDict[name] = [metricName, metricMetadata, slicerName, None]
        return mDict

    def _buildSummaryName(self, metricName, metricMetadata, slicerName, summaryStatName):
        if metricMetadata is None:
            metricMetadata = ''
        if slicerName is None:
            slicerName = ''
        sName = summaryStatName
        if sName == 'Identity' or sName == 'Id' or sName == 'Count' or sName is None:
            sName = ''
        slName = slicerName
        if slName == 'UniSlicer':
            slName = ''
        name = ' '.join([sName, metricName, metricMetadata, slName]).rstrip(' ').lstrip(' ')
        name.replace(',', '')
        return name

    def _findSummaryStats(self, metricName, metricMetadata=None, slicerName=None, summaryName=None,
                          colName=None):
        """
        Look for summary metric values matching metricName (and optionally metricMetadata, slicerName
        and summaryName) among the results databases for each run.

        Parameters
        ----------
        metricName : str
            The name of the original metric.
        metricMetadata : str, opt
            The metric metadata specifying the metric desired (optional).
        slicerName : str, opt
            The slicer name specifying the metric desired (optional).
        summaryName : str, opt
            The name of the summary statistic desired (optional).
        colName : str, opt
            Name of the column header for the dataframe. If more than one summary stat is
            returned from the database, then this will be ignored.

        Results
        -------
        Pandas Dataframe
            <index>   <metricName>  (possibly additional metricNames - multiple summary stats or metadata..)
             runName    value
        """
        summaryValues = {}
        summaryNames = {}
        for r in self.runlist:
            summaryValues[r] = {}
            summaryNames[r] = {}
            # Check if this metric/metadata/slicer/summary stat name combo is in
            # this resultsDb .. or potentially in another subdirectory's resultsDb.
            for s in self.runresults[r]:
                mId = self.runresults[r][s].getMetricId(metricName=metricName,
                                                        metricMetadata=metricMetadata,
                                                        slicerName=slicerName)
                # Note that we may have more than one matching summary metric value per run.
                if len(mId) > 0:
                    # And we may have more than one summary metric value per resultsDb
                    stats = self.runresults[r][s].getSummaryStats(mId, summaryName=summaryName)
                    if len(stats['summaryName']) == 1 and colName is not None:
                        name = colName
                        summaryValues[r][name] = stats['summaryValue'][0]
                        summaryNames[r][name] = stats['summaryName'][0]
                    else:
                        for i in range(len(stats['summaryName'])):

                            name = self._buildSummaryName(metricName, metricMetadata, slicerName,
                                                          stats['summaryName'][i])
                            summaryValues[r][name] = stats['summaryValue'][i]
                            summaryNames[r][name] = stats['summaryName'][i]
            if len(summaryValues[r]) == 0:
                warnings.warn("Warning: Found no metric results for %s %s %s %s in run %s"
                              % (metricName, metricMetadata, slicerName, summaryName, r))
        # Make DataFrame.
        # First determine list of all summary stats pulled from all databases.
        unique_stats = set()
        for r in self.runlist:
            for name in summaryNames[r]:
                unique_stats.add(name)
        # Make sure every runName (key) in summaryValues dictionary has a value for each stat.
        for s in unique_stats:
            for r in self.runlist:
                try:
                    summaryValues[r][s]
                except KeyError:
                    summaryValues[r][s] = np.nan
        # Create data frames for each run (because pandas).
        tempDFList = []
        for r in self.runlist:
            tempDFList.append(pd.DataFrame(summaryValues[r], index=[r]))
        # Concatenate dataframes for each run.
        stats = pd.concat(tempDFList)
        return stats

    def addSummaryStats(self, metricDict):
        """
        Combine the summary statistics of a set of metrics into a pandas
        dataframe that is indexed by the opsim run name.

        Parameters
        ----------
        metricDict: dict
            A dictionary of metrics with all of the information needed to query
            a results database.  The metric/metadata/slicer/summary values referred to
            by a metricDict value could be unique but don't have to be.

        Returns
        -------
        pandas DataFrame
            A pandas dataframe containing a column for each of the configuration
            parameters given in paramName like and a column for each of the
            dictionary keys in the metricDict. The resulting dataframe is
            indexed the name of the opsim runs.
              index      metric1         metric2
            <run_123>    <metricValue1>  <metricValue2>
            <run_124>    <metricValue1>  <metricValue2>
        """
        for mName, metric in metricDict.items():
            tempDF = self._findSummaryStats(metricName=metric[0], metricMetadata=metric[1],
                                            slicerName=metric[2], summaryName=metric[3],
                                            colName=mName)
            if self.summaryStats is None:
                self.summaryStats = tempDF
            else:
                self.summaryStats = self.summaryStats.join(tempDF)

    def normalizeRun(self, baselineRun):
        """
        Normalize the summary metric values in the dataframe
        resulting from combineSummaryStats based on the values of a single
        baseline run.

        Parameters
        ----------
        baselineRun : str
            The name of the opsim run that will serve as baseline.

        Results
        -------
        pandas DataFrame
            A pandas dataframe containing a column for each of the configuration
            parameters given in paramNamelike and a column for each of the
            dictionary keys in the metricDict. The resulting dataframe is
            indexed the name of the opsim runs.
            index        metric1               metric2
            <run_123>    <norm_metricValue1>  <norm_metricValue2>
            <run_124>    <norm_metricValue1>  <norm_metricValue2>

        Notes:
        ------
        The metric values are normalized in the following way:

        norm_metric_value(run) = metric_value(run) - metric_value(baselineRun) / metric_value(baselineRun)
        """
        self.normalizedStats = self.summaryStats.copy(deep=True)
        self.normalizedStats = self.normalizedStats - self.summaryStats.loc[baselineRun]
        self.normalizedStats /= self.summaryStats.loc[baselineRun]
        self.baselineRun = baselineRun

    def getFileNames(self, metricName, metricMetadata=None, slicerName=None):
        """For each of the runs in runlist, get the paths to the datafiles for a given metric.

        Parameters
        ----------
        metricName : str
            The name of the original metric.
        metricMetadata : str, opt
            The metric metadata specifying the metric desired (optional).
        slicerName : str, opt
            The slicer name specifying the metric desired (optional).

        Returns
        -------
        Dict
            Keys: runName, Value: path to file
        """
        filepaths = {}
        for r in self.runlist:
            for s in self.runresults[r]:
                mId = self.runresults[r][s].getMetricId(metricName=metricName,
                                                        metricMetadata=metricMetadata,
                                                        slicerName=slicerName)
                if len(mId) > 0 :
                    if len(mId) > 1:
                        warnings.warn("Found more than one metric data file matching ",
                                      "metricName %s metricMetadata %s and slicerName %s"
                                      % (metricName, metricMetadata, slicerName),
                                      ' Skipping this combination.')
                    else:
                        filename = self.runresults[r][s].getMetricDataFiles(metricId=mId)
                        filepaths[r] = os.path.join(r, s, filename[0])
        return filepaths

    def plotSummaryStats(self):
        # We'll fix this asap
        pass

    # Plot actual metric values (skymaps or histograms or power spectra) (values not stored in class).
    def readMetricData(self, metricName, metricMetadata, slicerName):
        # Get the names of the individual files for all runs.
        # Dictionary, keyed by run name.
        filenames = self.getFileNames(metricName, metricMetadata, slicerName)
        mname = self._buildSummaryName(metricName, metricMetadata, slicerName, None)
        bundleDict = {}
        for r in filenames:
            bundleDict[r] = mb.createEmptyMetricBundle()
            bundleDict[r].read(filenames[r])
        return bundleDict, mname

    def plotMetricData(self, bundleDict, plotFunc, mname=None, runlist=None, userPlotDict=None,
                       layout=None, outDir=None, savefig=False):
        if runlist is None:
            runlist = self.runlist

        ph = plots.PlotHandler(outDir=outDir, savefig=savefig)
        bundleList = []
        for r in runlist:
            bundleList.append(bundleDict[r])
        ph.setMetricBundles(bundleList)

        plotDicts = [{} for r in runlist]
        # Depending on plotFunc, overplot or make many subplots.
        if plotFunc.plotType == 'SkyMap':
            # Note that we can only handle 9 subplots currently due
            # to how subplot identification (with string) is handled.
            if len(runlist) > 9:
                raise ValueError('Please try again with < 9 subplots for skymap.')
            # Many subplots.
            if 'colorMin' not in userPlotDict:
                colorMin = 100000000
                for b in bundleDict:
                    tmp = bundleDict[b].metricValues.compressed().min()
                    colorMin = min(tmp, colorMin)
                userPlotDict['colorMin'] = colorMin
            if 'colorMax' not in userPlotDict:
                colorMax = -100000000
                for b in bundleDict:
                    tmp = bundleDict[b].metricValues.compressed().max()
                    colorMax = max(tmp, colorMax)
                userPlotDict['colorMax'] = colorMax
            for i, pdcit in enumerate(plotDicts):
                # Add user provided dictionary.
                pdcit.update(userPlotDict)
                # Set subplot information.
                if layout is None:
                    ncols = int(np.ceil(np.sqrt(len(runlist))))
                    nrows = int(np.ceil(len(runlist) / float(ncols)))
                else:
                    ncols = layout[0]
                    nrows = layout[1]
                pdcit['subplot'] = str(nrows) + str(ncols) + str(i + 1)
                pdcit['title'] = runlist[i]
                if 'suptitle' not in userPlotDict:
                    pdcit['suptitle'] = ph._buildTitle()
        else:
            # Put everything on one plot.
            if 'xMin' not in userPlotDict:
                xMin = 100000000
                for b in bundleDict:
                    tmp = bundleDict[b].metricValues.compressed().min()
                    xMin = min(tmp, xMin)
                userPlotDict['xMin'] = xMin
            if 'xMax' not in userPlotDict:
                xMax = -100000000
                for b in bundleDict:
                    tmp = bundleDict[b].metricValues.compressed().max()
                    xMax = max(tmp, xMax)
                userPlotDict['xMax'] = xMax
            for i, pdcit in enumerate(plotDicts):
                pdcit.update(userPlotDict)
                pdcit['subplot'] = '111'
                # Legend and title will automatically be ok, I think.
        ph.plot(plotFunc, plotDicts=plotDicts)
