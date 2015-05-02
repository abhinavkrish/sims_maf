# oneDSlicer - slices based on values in one data column in simData.

import numpy as np
import matplotlib.pyplot as plt
from functools import wraps
import warnings
from lsst.sims.maf.utils import percentileClipping, optimalBins, ColInfo
from .baseSlicer import BaseSlicer

__all__ = ['OneDSlicer']

class OneDSlicer(BaseSlicer):
    """oneD Slicer."""
    def __init__(self, sliceColName=None, sliceColUnits=None,
                 bins=None, binMin=None, binMax=None, binsize=None,
                 verbose=True, badval=0):
        """
        'sliceColName' is the name of the data column to use for slicing.
        'sliceColUnits' lets the user set the units (for plotting purposes) of the slice column.
        'bins' can be a numpy array with the binpoints for sliceCol or a single integer value
        (if a single value, this will be used as the number of bins, together with data min/max or binMin/Max),
        as in numpy's histogram function.
        If 'binsize' is used, this will override the bins value and will be used together with the data min/max
        or binMin/Max to set the binpoint values.

        Bins work like numpy histogram bins: the last 'bin' value is end value of last bin;
          all bins except for last bin are half-open ([a, b>), the last one is ([a, b]).
        """
        super(OneDSlicer, self).__init__(verbose=verbose, badval=badval)
        self.sliceColName = sliceColName
        self.columnsNeeded = [sliceColName]
        self.bins = bins
        self.binMin = binMin
        self.binMax = binMax
        self.binsize = binsize
        if sliceColUnits is None:
            co = ColInfo()
            self.sliceColUnits = co.getUnits(self.sliceColName)
        self.slicer_init = {'sliceColName':self.sliceColName, 'sliceColUnits':sliceColUnits,
                            'badval':badval}

    def setupSlicer(self, simData, maps=None):
        """
        Set up bins in slicer.
        """
        if self.sliceColName is None:
            raise Exception('sliceColName was not defined when slicer instantiated.')
        sliceCol = simData[self.sliceColName]
        # Set bin min/max values.
        if self.binMin is None:
            self.binMin = sliceCol.min()
        if self.binMax is None:
            self.binMax = sliceCol.max()
        # Give warning if binMin = binMax, and do something at least slightly reasonable.
        if self.binMin == self.binMax:
            warnings.warn('binMin = binMax (maybe your data is single-valued?). '
                          'Increasing binMax by 1 (or 2*binsize, if binsize set).')
            if self.binsize is not None:
                self.binMax = self.binMax + 2 * self.binsize
            else:
                self.binMax = self.binMax + 1
        # Set bins.
        # Using binsize.
        if self.binsize is not None:
            # Add an extra 'bin' to the edge values of the bins (makes plots much prettier).
            self.binMin -= self.binsize
            self.binMax += self.binsize
            if self.bins is not None:
                warnings.warn('Both binsize and bins have been set; Using binsize %f only.' %(self.binsize))
            self.bins = np.arange(self.binMin, self.binMax+self.binsize/2.0, self.binsize, 'float')
        # Using bins value.
        else:
            # Bins was a sequence (np array or list)
            if hasattr(self.bins, '__iter__'):
                self.bins = np.sort(self.bins)
                self.binMin = self.bins[0]
                self.binMax = self.bins[-1]
            # Or bins was a single value.
            else:
                if self.bins is None:
                    self.bins = optimalBins(sliceCol, self.binMin, self.binMax)
                nbins = np.round(self.bins)
                self.binsize = (self.binMax - self.binMin) / float(nbins)
                self.bins = np.arange(self.binMin, self.binMax+self.binsize/2.0, self.binsize, 'float')
        # Set nbins to be one less than # of bins because last binvalue is RH edge only
        self.nslice = len(self.bins) - 1
        # Set slicePoint metadata.
        self.slicePoints['sid'] = np.arange(self.nslice)
        self.slicePoints['bins'] = self.bins
        # Add metadata from map if needed.
        self._runMaps(maps)
        # Set up data slicing.
        self.simIdxs = np.argsort(simData[self.sliceColName])
        simFieldsSorted = np.sort(simData[self.sliceColName])
        # "left" values are location where simdata == bin value
        self.left = np.searchsorted(simFieldsSorted, self.bins[:-1], 'left')
        self.left = np.concatenate((self.left, np.array([len(self.simIdxs),])))
        # Set up _sliceSimData method for this class.
        @wraps(self._sliceSimData)
        def _sliceSimData(islice):
            """Slice simData on oneD sliceCol, to return relevant indexes for slicepoint."""
            idxs = self.simIdxs[self.left[islice]:self.left[islice+1]]
            return {'idxs':idxs,
                    'slicePoint':{'sid':islice, 'binLeft':self.bins[islice]}}
        setattr(self, '_sliceSimData', _sliceSimData)

    def __eq__(self, otherSlicer):
        """Evaluate if slicers are equivalent."""
        match = False
        if isinstance(otherSlicer, OneDSlicer):
            if self.sliceColName == otherSlicer.sliceColName:
                # If slicer restored from disk or setup, then 'bins' in slicePoints dict.
                if 'bins' in self.slicePoints and 'bins' in otherSlicer.slicePoints:
                    match = np.all(otherSlicer.slicePoints['bins'] == self.slicePoints['bins'])
                # Otherwise, try some other things.
                else:
                    if self.bins and otherSlicer.bins: # if these are not None
                        match = np.all(self.bins == otherSlicer.bins)
                    elif self.binsize and self.binMin and self.binMax and\
                        otherSlicer.binsize and otherSlicer.binMin and otherSlicer.binMax:
                        if (self.binsize == otherSlicer.binsize) and\
                          (self.binMin == otherSlicer.binMin) and (self.binMax == otherSlicer.binMax):
                            match = True
        return match

    def plotBinnedData(self, metricValues, fignum=None,
                       title=None, units=None,
                       label=None, addLegend=False,
                       legendloc='upper left',
                       filled=False, alpha=0.5,
                       logScale=False, percentileClip=None,
                       ylabel=None, xlabel=None,
                       xMin=None, xMax=None, yMin=None, yMax=None,
                       color='b', linestyle='-', **kwargs):
        """
        Plot a set of oneD binned metric data.

        metricValues = the values to be plotted at each bin
        title = title for the plot (default None)
        xlabel = x axis label (default None)
        ylabel =  y axis label (default None)
        fignum = the figure number to use (default None - will generate new figure)
        label = the label to use for the figure legend (default None)
        addLegend = flag for whether or not to add a legend (default False)
        legendloc = location for legend (default 'upper left')
        filled = flag to plot histogram as filled bars or lines (default False = lines)
        alpha = alpha value for plot bins if filled (default 0.5).
        logScale = make the y-axis log (default False)
        percentileClip = percentile clip hi/low outliers before setting the y axis limits
        yMin/Max = min/max for y-axis (overrides percentileClip)
        xMin/Max = min/max for x-axis (typically set by bin values though)
        """
        if color is None:
            color = 'b'
        # Plot the histogrammed data.
        fig = plt.figure(fignum)
        leftedge = self.slicePoints['bins'][:-1]
        width = np.diff(self.slicePoints['bins'])
        if filled:
            plt.bar(leftedge, metricValues.filled(), width, label=label,
                    linewidth=0, alpha=alpha, log=logScale, color=color)
        else:
            good = np.where(metricValues.mask == False)
            x = np.ravel(zip(leftedge[good], leftedge[good]+width[good]))
            y = np.ravel(zip(metricValues[good], metricValues[good]))
            if logScale:
                plt.semilogy(x, y, label=label, color=color, linestyle=linestyle, alpha=alpha)
            else:
                plt.plot(x, y, label=label, color=color, linestyle=linestyle, alpha=alpha)
        # The ylabel will always be built by the sliceMetric.
        if ylabel is not None:
            plt.ylabel(ylabel)
        # The xlabel will always be built by the SliceMetric, so this will generally
        #  be ignored, but is provided for users who may be working directly with Slicer.
        if xlabel is None:
            xlabel=self.sliceColName
            if units != None:
                xlabel += ' (' + self.sliceColUnits + ')'
        plt.xlabel(xlabel)
        # Set y limits (either from values in args, percentileClipping or compressed data values).
        if (yMin is None) or (yMax is None):
            if percentileClip:
                yMin, yMax = percentileClipping(metricValues.compressed(), percentile=percentileClip)
        if yMin is not None and yMax is not None:
            plt.ylim(yMin, yMax)
        # Set x limits if given in kwargs.
        if (xMin is not None) or (xMax is not None):
            plt.xlim(xMin, xMax)
        if (addLegend):
            plt.legend(fancybox=True, prop={'size':'smaller'}, loc=legendloc, numpoints=1)
        if (title!=None):
            plt.title(title)
        return fig.number

