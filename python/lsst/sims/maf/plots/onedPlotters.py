import numpy as np
import matplotlib.pyplot as plt
from lsst.sims.maf.utils import percentileClipping

from .plotHandler import BasePlotter

__all__ = ['OneDBinnedData']

class OneDBinnedData(BasePlotter):
    def __init__(self):
        self.plotType ='BinnedData'
        self.objectPlotters = False
        self.defaultPlotDict = {'title':None, 'label':None, 'xlabel':None, 'ylabel':None,
                                'filled':False, 'alpha':0.5,
                                'logScale':False, 'percentileClip':None,
                                'xMin':None, 'xMax':None, 'yMin':None, 'yMax':None,
                                'color':'b', 'linestyle':'-', 'linewidth':1}

    def __call__(self, metricValues, slicer, userPlotDict, fignum=None):
        """
        Plot a set of oneD binned metric data.
        """
        if slicer.slicerName != 'OneDSlicer':
            raise ValueError('OneDBinnedData plotter is for use with OneDSlicer')
        fig = plt.figure(fignum)
        plotDict = {}
        plotDict.update(self.defaultPlotDict)
        plotDict.update(userPlotDict)
        # Plot the histogrammed data.
        if 'bins' not in slicer.slicePoints:
            raise ValueError('OneDSlicer has to contain bins in slicePoints metadata')
        leftedge = slicer.slicePoints['bins'][:-1]
        width = np.diff(slicer.slicePoints['bins'])
        if plotDict['filled']:
            plt.bar(leftedge, metricValues.filled(), width, label=plotDict['label'],
                    linewidth=0, alpha=plotDict['alpha'], log=plotDict['logScale'],
                    color=plotDict['color'])
        else:
            good = np.where(metricValues.mask == False)
            x = np.ravel(zip(leftedge[good], leftedge[good]+width[good]))
            y = np.ravel(zip(metricValues[good], metricValues[good]))
            if plotDict['logScale']:
                plt.semilogy(x, y, label=plotDict['label'], color=plotDict['color'],
                             linestyle=plotDict['linestyle'], linewidth=plotDict['linewidth'],
                             alpha=plotDict['alpha'])
            else:
                plt.plot(x, y, label=plotDict['label'], color=plotDict['color'],
                         linestyle=plotDict['linestyle'], linewidth=plotDict['linewidth'],
                         alpha=plotDict['alpha'])
        if 'ylabel' in plotDict:
            plt.ylabel(plotDict['ylabel'])
        if 'xlabel' in plotDict:
            plt.xlabel(plotDict['xlabel'])
        # Set y limits (either from values in args, percentileClipping or compressed data values).
        if (plotDict['yMin'] is None) or (plotDict['yMax'] is None):
            if plotDict['percentileClip']:
                plotDict['yMin'], plotDict['yMax'] = percentileClipping(metricValues.compressed(),
                                                                        percentile=plotDict['percentileClip'])
        # Set y and x limits, if provided.
        if 'yMin' in plotDict:
            plt.ylim(ymin=plotDict['yMin'])
        if 'yMax' in plotDict:
            plt.ylim(ymax=plotDict['yMax'])
        if 'xMin' in plotDict:
            plt.xlim(xmin=plotDict['xMin'])
        if 'xMax' in plotDict:
            plt.xlim(xmax=plotDict['xMax'])
        if 'title' in plotDict:
            plt.title(plotDict['title'])
        return fig.number
