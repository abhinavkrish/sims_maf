from builtins import zip
import numpy as np
import healpy as hp
import matplotlib.pyplot as plt

import lsst.sims.maf.metrics as metrics

from .plotHandler import BasePlotter

__all__ = ['FOPlot', 'SummaryHistogram']

class FOPlot(BasePlotter):
    """
    Special plotter to generate and label fO plots.
    """
    def __init__(self):
        self.plotType = 'FO'
        self.objectPlotter = False
        self.defaultPlotDict = {'title': None, 'xlabel': 'Number of visits',
                                'ylabel': 'Area (1000s of square degrees)',
                                'scale': None, 'Asky': 18000., 'Nvisits': 825,
                                'xMin': None, 'xMax': None, 'yMin': None, 'yMax': None,
                                'linewidth': 2, 'reflinewidth': 2}

    def __call__(self, metricValue, slicer, userPlotDict, fignum=None):
        """
        Parameters
        ----------
        metricValue : numpy.ma.MaskedArray
            The metric values calculated with the 'Count' metric and a healpix slicer.
        slicer : lsst.sims.maf.slicers.HealpixSlicer
        userPlotDict: dict
            Dictionary of plot parameters set by user (overrides default values).
            Note that Asky and Nvisits values set here and in the slicer should be consistent,
            for plot labels and summary statistic values to be consistent.
        fignum : int
            Matplotlib figure number to use (default = None, starts new figure).

        Returns
        -------
        int
           Matplotlib figure number used to create the plot.
        """
        if not hasattr(slicer, 'nside'):
            raise ValueError('FOPlot to be used with healpix or healpix derived slicers.')
        fig = plt.figure(fignum)
        plotDict = {}
        plotDict.update(self.defaultPlotDict)
        plotDict.update(userPlotDict)

        if plotDict['scale'] is None:
            plotDict['scale'] = (hp.nside2pixarea(slicer.nside, degrees=True) / 1000.0)

        # Expect metricValue to be something like number of visits
        cumulativeArea = np.arange(1, metricValue.compressed().size + 1)[::-1] * plotDict['scale']
        plt.plot(np.sort(metricValue.compressed()), cumulativeArea, 'k-',
                 linewidth=plotDict['linewidth'], zorder=0)
        # This is breaking the rules and calculating the summary stats in two places.
        # Could just calculate summary stats and pass in labels.
        rarr = np.array(list(zip(metricValue.compressed())),
                        dtype=[('fO', metricValue.dtype)])
        fOArea = metrics.fOArea(col='fO', Asky=plotDict['Asky'], norm=False,
                                nside=slicer.nside).run(rarr)
        fONv = metrics.fONv(col='fO', Nvisit=plotDict['Nvisits'], norm=False,
                            nside=slicer.nside).run(rarr)

        plt.axvline(x=plotDict['Nvisits'], linewidth=plotDict['reflinewidth'], color='b')
        plt.axhline(y=plotDict['Asky'] / 1000., linewidth=plotDict['reflinewidth'], color='r')
        # Check if things passed
        calc_passed = True
        if isinstance(fONv, int):
            calc_passed = False
        elif np.max(fONv['value']) == -666:
            calc_passed = False
        if isinstance(fOArea, int):
            calc_passed = False
        elif np.max(fOArea) != -666:
            calc_passed = False
        if calc_passed:
            Nvis_median = fONv['value'][np.where(fONv['name'] == 'MedianNvis')]
            plt.axhline(y=Nvis_median / 1000., linewidth=plotDict['reflinewidth'], color='b',
                        alpha=.5, label=r'f$_0$ Median Nvisits=%.3g' % Nvis_median)
            plt.axvline(x=fOArea, linewidth=plotDict['reflinewidth'], color='r',
                        alpha=.5, label='f$_0$ Area=%.3g' % fOArea)
        plt.legend(loc='lower left', fontsize='small', numpoints=1)

        plt.xlabel(plotDict['xlabel'])
        plt.ylabel(plotDict['ylabel'])
        plt.title(plotDict['title'])

        xMin = plotDict['xMin']
        xMax = plotDict['xMax']
        yMin = plotDict['yMin']
        yMax = plotDict['yMax']
        if (xMin is not None) or (xMax is not None):
            plt.xlim([xMin, xMax])
        if (yMin is not None) or (yMax is not None):
            plt.ylim([yMin, yMax])
        return fig.number


class SummaryHistogram(BasePlotter):
    """
    Special plotter to summarize metrics which return a set of values at each slicepoint,
    such as if a histogram was calculated at each slicepoint
    (e.g. with the lsst.sims.maf.metrics.TgapsMetric).
    Effectively marginalizes the calculated values over the sky, and plots the a summarized
    version (reduced to a single according to the plotDict['metricReduce'] metric).
    """

    def __init__(self):
        self.plotType = 'SummaryHistogram'
        self.objectPlotter = True
        self.defaultPlotDict = {'title': None, 'xlabel': None, 'ylabel': 'Count', 'label': None,
                                'cumulative': False, 'xMin': None, 'xMax': None, 'yMin': None, 'yMax': None,
                                'color': 'b', 'linestyle': '-', 'histStyle': True, 'grid': True,
                                'metricReduce': metrics.SumMetric(), 'bins': None}

    def __call__(self, metricValue, slicer, userPlotDict, fignum=None):
        """
        Parameters
        ----------
        metricValue : numpy.ma.MaskedArray
            Handles 'object' datatypes for the masked array.
        slicer : lsst.sims.maf.slicers
            Any MAF slicer.
        userPlotDict: dict
            Dictionary of plot parameters set by user (overrides default values).
            'metricReduce' (an lsst.sims.maf.metric) indicates how to marginalize the metric values
            calculated at each point to a single series of values over the sky.
            'histStyle' (True/False) indicates whether to plot the results as a step histogram (True)
            or as a series of values (False)
            'bins' (np.ndarray) sets the x values for the resulting plot and should generally match
            the bins used with the metric.
        fignum : int
            Matplotlib figure number to use (default = None, starts new figure).

        Returns
        -------
        int
           Matplotlib figure number used to create the plot.
        """
        fig = plt.figure(fignum)
        plotDict = {}
        plotDict.update(self.defaultPlotDict)
        plotDict.update(userPlotDict)
        # Combine the metric values across all slicePoints.
        if not isinstance(plotDict['metricReduce'], metrics.BaseMetric):
            raise ValueError('Expected plotDict[metricReduce] to be a MAF metric object.')
        # Get the data type
        dt = metricValue.compressed()[0].dtype
        # Change an array of arrays (dtype=object) to a 2-d array of correct dtype
        mV = np.array(metricValue.compressed().tolist(), dtype=[('metricValue', dt)])
        # Make an array to hold the combined result
        finalHist = np.zeros(mV.shape[1], dtype=float)
        metric = plotDict['metricReduce']
        metric.colname = 'metricValue'
        # Loop over each bin and use the selected metric to combine the results
        for i in np.arange(finalHist.size):
            finalHist[i] = metric.run(mV[:, i])
        bins = plotDict['bins']
        if plotDict['histStyle']:
            width = np.diff(bins)
            leftedge = bins[:-1] - width/2.0
            rightedge = bins[:-1] + width/2.0
            #x = np.ravel(list(zip(bins[:-1], bins[1:])))
            x = np.ravel(list(zip(leftedge, rightedge)))
            y = np.ravel(list(zip(finalHist, finalHist)))
        else:
            # Could use this to plot things like FFT
            x = bins[:-1]
            y = finalHist
        # Make the plot.
        plt.plot(x, y, linestyle=plotDict['linestyle'],
                 label=plotDict['label'], color=plotDict['color'])
        # Add labels.
        plt.xlabel(plotDict['xlabel'])
        plt.ylabel(plotDict['ylabel'])
        plt.title(plotDict['title'])
        plt.grid(plotDict['grid'], alpha=0.3)
        # Set y and x limits, if provided.
        if plotDict['xMin'] is not None:
            plt.xlim(xmin=plotDict['xMin'])
        elif bins[0] == 0:
            plt.xlim(xmin=0)
        if plotDict['xMax'] is not None:
            plt.xlim(xmax=plotDict['xMax'])
        if plotDict['yMin'] is not None:
            plt.ylim(ymin=plotDict['yMin'])
        elif finalHist.min() == 0:
            plotDict['yMin'] = 0
        if plotDict['yMax'] is not None:
            plt.ylim(ymax=plotDict['yMax'])

        return fig.number
