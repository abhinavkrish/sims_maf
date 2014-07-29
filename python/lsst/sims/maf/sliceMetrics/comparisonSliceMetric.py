import os
import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt
import warnings

import lsst.sims.maf.slicers as slicers
import lsst.sims.maf.metrics as metrics
from lsst.sims.maf.db import ResultsDb
from .baseSliceMetric import BaseSliceMetric

import time
def dtime(time_prev):
   return (time.time() - time_prev, time.time())


class ComparisonSliceMetric(BaseSliceMetric):
    """
    ComparisonSliceMetric couples slicers and metric data (one slicer per metric data)
    to allow creation of plots using data created by multiple metrics. Each metric data array
    can also be accompanied by the metric object which created it, although this is not necessary
    (but provides a easy way to set plotting parameters).
    
    The ComparisonSliceMetric tracks metadata about each metric, including the opsim run name,
    the sql constraint that produced the original metric data, and the slicer 
    which generated the data. 
    """

    def addMetricData(self, metricValues, metricName, slicer, simDataName, 
                      sqlconstraint, metadata, displayDict=None, plotParams=None, metricId=None):
        """
        Add a set of metricValues/slicer/plotParams/metricName/simDataName/sqlconstraint/metadata directly.

        Another option is to use 'readMetricData' to read metric data from a file.
        """
        iid = self.iid_next
        self.iid_next += 1
        if plotParams is None:
          self.plotParams[iid] = {}
        self.metricValues[iid] = metricValues
        self.metricNames[iid] = metricName
        self.slicers[iid] = slicer
        self.simDataNames[iid] = simDataName
        self.sqlconstraints[iid] = sqlconstraints
        self.metadatas[iid] = metadatas
        if displayDict is None:
           displayDict = {'group':'Ungrouped', 
                          'subgroup':'NULL',
                          'order':0, 
                          'caption':'NULL'}
        self.displayDicts[iid] = displayDict
        if metricId is not None:
            self.metricIds[iid] = metricId

    def uniqueMetricNames(self, iids=None):
        """
        Examine metric names and return the set of unique metric names 
        (optionally, for only 'iids'.).
        """
        uniqueMetrics = set()
        if iids is None:
           iids = self.metricNames.keys()
        for iid in iids:
           uniqueMetrics.add(self.metricNames[iid])
        return uniqueMetrics

    def uniqueMetadata(self, iids=None):
        """
        Examine metadatas and return the set of unique metadata values 
        (optionally, for only iids)
        """
        uniqueMetadata = set()
        if iids is None:
           iids = self.metadatas.keys()
        for iid in iids:
           uniqueMetadata.add(self.metadatas[iid])
        return uniqueMetadata

    def uniqueSimDataNames(self, iids=None):
        """
        Examine simDataNames and return the set of unique simDataNames 
        (optionally, for only iids)
        """
        uniqueSimDataNames = set()
        if iids is None:
           iids = self.simDataNames.keys()
        for iid in iids:
           uniqueSimDataNames.add(self.simDataNames[iid])
        return uniqueSimDataNames

    def uniqueSlicerNames(self, iids=None):
        """
        Examine slicerNames and return the set of unique values. 
        (optionally, for only iids).
        """
        uniqueSlicerNames = set()
        if iids is None:
            iids = self.slicers.keys()
        for iid in iids:
            uniqueSlicerNames.add(self.slicers[iid].slicerName)
        return uniqueSlicerNames                        

    def splitPlottable(self, iids):
        slicers = set()
        for iid in iids:
            slicers.add(self.slicers[iid].slicerName)
        outIids = []
        for s in slicers:
            oiids = []
            for i in iids:
                if self.slicers[i].slicerName == s:
                    ooids.append(i)
            outIids.append(ooids)
        return outIids


    def _buildPlotTitle(self, iids):
        """
        Build a plot title from the simDataName, metadata and metric names of the 'iids'.
        """
        usimDataNames = self.uniqueSimDataNames(iids)
        umetadatas = self.uniqueMetadata(iids)        
        umetricNames = self.uniqueMetricNames(iids)
        # Create a plot title from the unique parts of the simData/metadata/metric names.
        plotTitle = ''
        if len(usimDataNames) == 1:
            plotTitle += ' ' + list(usimDataNames)[0]
        if len(umetadatas) == 1:
            plotTitle += ' ' + list(umetadatas)[0]
        if len(umetricNames) == 1:
            plotTitle += ' ' + list(umetricNames)[0]        
        if plotTitle == '':
            # If there were more than one of everything above, just join metricNames with commas. 
            plotTitle = ', '.join(umetricNames)
        else:
           plotTitle = plotTitle[1:]
        return plotTitle
    
    
    def _buildXlabel(self, iids):
        xlabel = set()
        for iid in iids:
            if hasattr(self.slicers[iid], 'plotHistogram'):
                xlabel.add(self.metricNames[iid])
            if hasattr(self.slicers[iid], 'plotBinnedData'):
                xlabel.add(self.slicers[iid].sliceColName)
        xlabel = list(xlabel)
        xlabel = ', '.join(xlabel)
        return xlabel
    
    def _buildYlabel(self, iids):
        ylabel = None
        for iid in iids:
            # For spatial slicers, the y label will be set automatically by plotHistogram.
            if hasattr(self.slicers[iid], 'plotHistogram'):
                pass
            # For OneD slicers though, the y label should be set by the metric.
            if hasattr(self.slicers[iid], 'plotBinnedData'):
                # Most of the time it will be 'count', so let's use that for now.
                ylabel = 'Count'
        return ylabel            
        
    def _buildLegendLabels(self, iids):
        # Determine what is common among all iids
        usimDataNames = self.uniqueSimDataNames(iids)
        umetadatas = self.uniqueMetadata(iids)        
        umetricNames = self.uniqueMetricNames(iids)
        labels = []
        for iid in iids:
            label = ''
            if len(usimDataNames) > 1:
                label += self.simDataNames[iid]
            if len(umetadatas) > 1:
                label += ' ' + self.metadatas[iid]
            if len(umetricNames) > 1:
                label += ' ' + self.metricNames[iid]
            labels.append(label)
        return labels

    def _checkPlottable(self, iids):
        for iid in iids:
            if iid not in self.metricValues:
                iids.remove(iid)
        for iid in iids:
            if iid not in self.slicers:
                iids.remove(iid)
        for iid in iids:
            if self.metricValues[iid].dtype == 'object':
                iids.remove(iid)
        return iids

    
    def plotHistograms(self, iids, 
                        bins=100, xMin=None, xMax=None, yMin=None, yMax=None,
                        title=None, xlabel=None, color=None, labels=None,
                        legendloc='upper left', alpha=1.0,
                        savefig=False,  outfileRoot=None, ylabel=None, plotkwargs=None):
        """
        Create a plot containing the histograms from metrics in iids (assuming their slicers
        have histogram-like capability).

        plotkwargs is a list of dicts with plotting parameters that override the defaults.
        """
        iids = self._checkPlottable(iids)
        # Check if the slicer has a histogram type visualization.
        for iid in iids:
            slicer = self.slicers[iid]
            if (not hasattr(slicer, 'plotBinnedData')) and (not hasattr(slicer, 'plotHistogram')):
                iids.remove(iid)
        if len(iids) == 0:
            warnings.warn('Removed all iids')
            return
        if title is None:
            title = self._buildPlotTitle(iids)
        if xlabel is None:
            xlabel = self._buildXlabel(iids)
        if ylabel is None:
            ylabel = self._buildYlabel(iids)
        if labels is None:
            labels = self._buildLegendLabels(iids)
        # Plot the data.
        fignum = None
        addLegend = False
        for i, iid in enumerate(iids):
            # If we're at the end of the list, add the legend.
            if i == len(iids) - 1:
                addLegend = True
            label = labels[i]
            # Plot data using 'plotBinnedData' if that method available (oneDSlicer)
            if hasattr(self.slicers[iid], 'plotBinnedData'):
                plotParams = {'xlabel':xlabel, 'title':title, 'alpha':alpha,\
                              'label':label, 'addLegend':addLegend, 'legendloc':legendloc,\
                              'color':color, 'ylabel':ylabel, 'xMin':xMin, 'xMax':xMax,  \
                              'yMin':yMin,'yMax':yMax}
                if plotkwargs is not None:
                    plotParams.update(plotkwargs[i])
                fignum = self.slicers[iid].plotBinnedData(self.metricValues[iid], fignum=fignum, **plotParams)
            # Plot data using 'plotHistogram' if that method available (any spatial slicer)
            if hasattr(self.slicers[iid], 'plotHistogram'):
                plotParams = {'xlabel':xlabel, 'bins':bins, 'title':title, 'label':label, \
                              'addLegend':addLegend, 'legendloc':legendloc, 'color':color, \
                              'ylabel':ylabel, 'xMin':xMin, 'xMax':xMax, \
                              'yMin':yMin,'yMax':yMax}
                if plotkwargs is not None:
                    plotParams.update(plotkwargs[i])
                fignum = self.slicers[iid].plotHistogram(self.metricValues[iid], fignum=fignum, **plotParams)
        if savefig:
            if outfileRoot is not None:
                outroot = outfileRoot + title
            else:
                outroot = title
            outfile = self._buildOutfileName(self.iid_next, outfileRoot=outroot, plotType='hist')
            plt.savefig(os.path.join(self.outDir, outfile), figformat=self.figformat, dpi=self.dpi)
            if self.thumbnail:
               thumbfile = os.path.join(self.outDir, outfile[:-4]).split('/')
               thumbfile[-1] = 'thumb.'+thumbfile[-1]
               thumbfile = '/'.join(thumbfile)
               plt.savefig(thumbfile+'.png', dpi=72)
            if self.resultsDb:
              # Don't have a metricID corresonding to this combo of metrics, add to metric db table.
              metricNames = ''.join(list(self.uniqueMetricNames(iids)))              
              slicerNames = ''.join(list(self.uniqueSlicerNames(iids)))
              simDataNames = ''.join(list(self.uniqueSimDataNames(iids)))
              metadata = ''.join(list(self.uniqueMetadata(iids)))              
              # Use first iid in iids to determine display group.
              metricId = self.resultsDb.addMetric(metricNames, slicerNames, simDataNames, 'NULL', metadata,
                                                  'NULL', self.displayDicts[iids[0]])
              self.resultsDb.addPlot(metricId, 'ComboHistogram', outfile)
        else:
            outfile = 'NULL'
        return fignum, title, outfile

    def plotPowerSpectra(self, iids, maxl=500., removeDipole=True,
                         title=None, legendloc='upper left', color=None, labels=None,
                         savefig=False,  outfileRoot=None, plotkwargs=None):
        """
        Create a plot containing the power spectrum visualization for 'iids'.
        """
        iids = self._checkPlottable(iids)
        # Check if the slicer has a power spectrum visualization.
        for iid in iids:
            slicer = self.slicers[iid]
            if (not hasattr(slicer, 'plotPowerSpectrum')):
                iids.remove(iid)
        if len(iids) == 0:
            warnings.warn('Removed all iids')
            return
        # Build a plot title.
        if title is None:
            title = self._buildPlotTitle(iids)
        if labels is None:
            labels = self._buildLegendLabels(iids)
        # Plot the data.
        fignum = None
        addLegend = False
        for i, iid  in enumerate(iids):
            # If we're at the end of the list, add the legend.
            if i == len(iids) - 1:
                addLegend = True
            label = labels[i]
            # Set up plotParams.
            plotParams = {'title':title, 'label':label, 'addLegend':addLegend,
                          'legendloc':legendloc, 'color':color, 'maxl':maxl,
                          'removeDipole':removeDipole}
            if plotkwargs is not None:
                    plotParams.update(plotkwargs[i])
            # Plot data.
            fignum = self.slicers[iid].plotPowerSpectrum(self.metricValues[iid],\
                                                         fignum=fignum, **plotParams)
        if savefig:
            if outfileRoot is not None:
                outroot = outfileRoot + title
            else:
                outroot = title
            outfile = self._buildOutfileName(self.iid_next, outfileRoot=outroot + title, plotType='ps')
            plt.savefig(os.path.join(self.outDir, outfile), figformat=self.figformat, dpi=self.dpi)
            if self.thumbnail:
               thumbfile = os.path.join(self.outDir, outfile[:-4]).split('/')
               thumbfile[-1] = 'thumb.'+thumbfile[-1]
               thumbfile = '/'.join(thumbfile)
               plt.savefig(thumbfile+'.png', dpi=72)
            if self.resultsDb:
                # Don't have a metricID corresonding to this combo of metrics, add to metric table.
                metricNames = ''.join(list(self.uniqueMetricNames(iids)))
                slicerNames = ''.join(list(self.uniqueSlicerNames(iids)))
                simDataNames = ''.join(list(self.uniqueSimDataNames(iids)))
                metadata = ''.join(list(self.uniqueMetadata(iids)))
                metricId = self.resultsDb.addMetric(metricNames, slicerNames, simDataNames, 'NULL', metadata,
                                                    'NULL', self.displayDicts[iids[0]])
                self.resultsDb.addPlot(metricId, 'ComboPowerSpectrum', outfile)
        else:
            outfile = 'NULL'
        return fignum, title, outfile
    

    def plotSkyMaps(self, iids, units=None, title=None,
                    clims=None, cmap=None, cbarFormat='%.2g', 
                    savefig=False, outDir=None, outfileRoot=None):
        """
        Create a skymap plot of the difference between two iids.
        """
        if len(iids) > 2:
           raise Exception('Only two iids to create a sky map difference')
        iids  = self._checkPlottable(iids)
        if self.slicers[iid[0]] != self.slicers[iid[1]]:
           raise Exception('Slicers must be equal')
        slicer = self.slicers[iid[0]]
        # Check if the slicer has a histogram type visualization.
        for iid in iids:
           if (not hasattr(slicer, 'plotSkyMap')):
              iids.remove(iid)
        if len(iids) != 2:
           raise Exception('Removed one or more of the iids due to object data or wrong slicer')
        # Make plot title.
        if plotTitle is None:
            plotTitle = self._buildPlotTitle(iids)
        # Plot the data.
        fignum = None
        addLegend = False
        # Mask areas where either metric has bad data values, take difference elsewhere.
        mask = self.metricValues[iid[0]].mask
        mask = np.where(self.metricValues[iid[1]].mask == True, True, mask)
        diff = ma.MaskedArray(data = (self.metricValues[iid[0]] - self.metricValues[iid[1]]), mask=mask,
                                      filled_value = slicer.badval)            
        # Make color bar label.
        if units is None:
            mname0 = self.metricNames[iid[0]]
            mname1 = self.metricNames[iid[1]]
            if (mname0 == mname1):
               units = (mname0 + ' (' + self.metadatas[iid[0]] + ' - ' + self.metadatas[iid[1]])                
            else:
               units = mname0 + ' - ' + mname1
        # Plot data.
        fignum = slicer.plotSkyMap(diff, units=units, title=title, clims=clims, cmap=cmap, cbarFormat=cbarFormat)
        if savefig:
            if outfileRoot is not None:
                outroot = outfileRoot + title
            else:
                outroot = title
            outfile = self._buildOutfileName(self.iid_next, outfileRoot=outroot, plotType='sky')
            plt.savefig(os.path.join(self.outDir, outfile), figformat=self.figformat, dpi=self.dpi)
            if self.thumbnail:
               thumbfile = os.path.join(self.outDir, outfile[:-4]).split('/')
               thumbfile[-1] = 'thumb.'+thumbfile[-1]
               thumbfile = '/'.join(thumbfile)
               plt.savefig(thumbfile+'.png', dpi=72)
            if self.resultsDb:
                # Don't have a metricID corresonding to this combo of metrics.
                metricNames = ''.join(list(self.uniqueMetricNames(iids)))
                slicerNames = ''.join(list(self.uniqueSlicerNames(iids)))
                simDataNames = ''.join(list(self.uniqueSimDataNames(iids)))
                metadata = ''.join(list(self.uniqueMetadata(iids)))
                metricId = self.resultsDb.addMetric(metricNames, slicerNames, simDataNames, 'NULL', metadata,
                                                    'NULL', self.displayDicts[iids[0]])
                self.resultsDb.addPlot(metricId, 'DifferenceSkyMap', outfile)
        else:
            outfile = 'NULL'
        return fignum, title, outfile
