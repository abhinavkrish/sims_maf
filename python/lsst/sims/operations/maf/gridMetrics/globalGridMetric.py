# Base class for global grids + metrics.
# Major difference between this gridmetric and the base gridmetric is in the plotting methods,
#  as global grids plot the simdata column rather than the metric data directly for a histogram.
#
# Also, globalGridMetric has a different possibility for calculating a summary statistic. Here,
#  the values don't have to be consolidated over the entire sky, but may (if it was a complex value
#  per grid point) have to be reduced to a single number. 

import os
import numpy as np
import matplotlib.pyplot as plt

from .baseGridMetric import BaseGridMetric

import time
def dtime(time_prev):
   return (time.time() - time_prev, time.time())


class GlobalGridMetric(BaseGridMetric):

    def __init__(self, figformat='png'):
        """Instantiate global gridMetric object and set up (empty) dictionaries."""
        super(GlobalGridMetric, self).__init__(figformat=figformat)
        self.metricHistValues = {}
        self.metricHistBins = {}
        return

        
    def setGrid(self, grid):
        super(GlobalGridMetric, self).setGrid(grid)
        # Check this grid is a spatial type.
        if self.grid.gridtype != 'GLOBAL':
            raise Exception('Gridtype for grid should be GLOBAL, not %s' %(self.grid.gridtype))
        return

    def runGrid(self, metricList, simData, 
                simDataName='opsim', metadata='', sliceCol=None, histbins=100, histrange=None):
        """Run metric generation over global grid and generate histograms

        metricList = list of metric objects
        simData = numpy recarray holding simulated data
        simDataName = identifier for simulated data
        metadata = further information from config files ('WFD', 'r band', etc.)
        sliceCol = column for slicing grid, if needed (default None)
        histbins = histogram bins (default = 100, but could pass number of bins or array)
        histrange = histogram range."""
        super(GlobalGridMetric, self).runGrid(metricList, simData, simDataName=simDataName,
                                              metadata=metadata, sliceCol=sliceCol)
        # Run through all gridpoints and generate histograms 
        #   (could be more efficient by not looping on grid twice, but relatively few
        #    gridpoints in global grid means this shouldn't be too bad).
        for m in self.metrics:
            self.metricHistValues[m.name] = np.zeros(len(self.grid), 'object')
            self.metricHistBins[m.name] = np.zeros(len(self.grid), 'object')
        for i, g in enumerate(self.grid):
            #idxs = self.grid.sliceSimData(g, simData[sliceCol])
            idxs = self.grid.sliceSimData(g, simData) #not sure why the sliceCol screwed things up...
            slicedata = simData[idxs]
            if len(idxs)==0:
                # No data at this gridpoint.
                for m in self.metrics:
                    self.metricHistValues[m.name][i] = self.grid.badval
                    self.metricHistBins[m.name][i] = self.grid.badval
            else:
                for m in self.metrics:
                    self.metricHistValues[m.name][i], self.metricHistBins[m.name][i] = \
                      np.histogram(slicedata[m.colname], bins=histbins, range=histrange)
        return
                      
    # Have to get simdata in here .. but how? (note that it's more than just one simdata - one
    #  column per metric, but could come from different runs)
    
    def plotMetric(self, metricName, 
                   savefig=True, outDir=None, outfileRoot=None):
        """Create all plots for 'metricName' ."""
        # Check that metricName refers to plottable ('float') data.
        if not isinstance(self.metricValues[metricName][0], float):
            raise ValueError('Metric data in %s is not float-type.' %(metricName))
        # Build plot title and label.
        plotTitle = self.simDataName[metricName] + ' ' + self.metadata[metricName]
        plotTitle += ' ' + metricName
        plotLabel = metricName
        # Plot the histogram.
        histfignum = self.grid.plotHistogram(self.metricValues[metricName], 
                                             plotLabel, title=plotTitle)
        if savefig:
            outfile = self._buildOutfileName(metricName, 
                                             outDir=outDir, outfileRoot=outfileRoot, 
                                             plotType='hist')
            plt.savefig(outfile, figformat=self.figformat)
        return

    def plotComparisons(self, metricNameList, 
                        savefig=True, outDir=None, outfileRoot=None):
        """Create comparison plots of all metricValues in metricNameList.

        Will create one histogram with all values from metricNameList, similarly for 
        power spectra if applicable. Will create skymap difference plots if only two metrics."""
        # Check is plottable data.
        for m in metricNameList:
            if not isinstance(self.metricValues[m], float):
                metricNameList.remove(m)
        # Build plot title and label.
        plotTitle = self.simDataName[metricName] + ' ' + self.metadata[metricName]
        plotTitle += ' ' + metricName
        plotLabel = metricName
        # Plot the histogram.
        histfignum = self.grid.plotHistogram(self.metricValues[metricName], 
                                             plotLabel, title=plotTitle)
        if savefig:
            outfile = self._buildOutfileName(metricName, 
                                             outDir=outDir, outfileRoot=outfileRoot, 
                                             plotType='hist')
            plt.savefig(outfile, figformat=self.figformat)        
            
        
        
    def computeSummaryStatistics(self, metricName, summaryMetric=None):
        """Compute summary statistic for metricName, using function summaryMetric.

        Since global grids already are summarized over the sky, this will typically only
        be a 'reduce' function if metricName was a complex metric. Otherwise, the summary
        statistic is the metricValue."""
        if summaryMetric == None:
            summaryNumber = self.metricValues[metricName]
        else:
            summaryNumber = summaryMetric(self.metricValues[metricName])
        return summaryNumber
