# oneDSlicer - slices based on values in one data column in simData.

import numpy as np
import matplotlib.pyplot as plt
from functools import wraps
import warnings
from lsst.sims.maf.utils import percentileClipping, optimalBins, ColInfo
from .baseSlicer import BaseSlicer
import subprocess

class MovieSlicer(BaseSlicer):
    """movie Slicer."""
    def __init__(self, sliceColName=None, sliceColUnits=None, 
                 bins=None, binMin=None, binMax=None, binsize=None,
                 verbose=True, badval=0):
        """
        The 'movieSlicer' acts similarly to the OneDSlicer (slices on one data column).
        However, the data slices from the movieSlicer are intended to be fed to another slicer, which then
        (together with a set of Metrics) calculates metric values + plots at each slice created by the movieSlicer.
        The job of the movieSlicer is to track those slices and put them together into a movie.
        
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
        super(MovieSlicer, self).__init__(verbose=verbose, badval=badval)
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
        
    def setupSlicer(self, simData): 
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
            if self.bins is not None:
                warnings.warn('Both binsize and bins have been set; Using binsize %f only.' %(self.binsize))
            self.bins = np.arange(self.binMin, self.binMax+self.binsize/2.0, self.binsize, 'float')
        # Using bins value.
        else:
            # Bins was a sequence (np array or list)
            if hasattr(self.bins, '__iter__'):  
                self.bins = np.sort(self.bins)
            # Or bins was a single value. 
            else:
                if self.bins is None:
                    self.bins = optimalBins(sliceCol, self.binMin, self.binMax)
                nbins = int(self.bins)
                self.binsize = (self.binMax - self.binMin) / float(nbins)
                self.bins = np.arange(self.binMin, self.binMax+self.binsize/2.0, self.binsize, 'float')
        # Set nbins to be one less than # of bins because last binvalue is RH edge only
        self.nslice = len(self.bins) - 1
        # Set slicePoint metadata.
        self.slicePoints['sid'] = np.arange(self.nslice)
        self.slicePoints['bins'] = self.bins
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
            
            #this is the important part. The ids here define the pieces of data that get 
            #passed on to subsequent slicers
            idxs = self.simIdxs[0:self.left[islice+1]]
            return {'idxs':idxs,
                    'slicePoint':{'sid':islice, 'binLeft':0}}
        setattr(self, '_sliceSimData', _sliceSimData)
    
    def __eq__(self, otherSlicer):
        """Evaluate if slicers are equivalent."""
        if isinstance(otherSlicer, OneDSlicer):
            return np.all(otherSlicer.slicePoints['bins'] == self.slicePoints['bins'])
        else:
            return False

    def plotMovie(self, metricList=0, N=0, ips=0, fps=0):
        """Takes in metric and slicer metadata and calls ffmpeg to stitch together output files"""

        #what was the slicer and metric?
        print metricList
        print N

        #look for png files to convert
        #how many are there? -> pass that info into ffmpeg for what numbers to look for.
        #take in parameters for ffmpeg - needs slice number, how many digits total


        #calling ffmpeg
        p = subprocess.Popen(['ffmpeg','-r','1','-i',
                            'opsimblitz2_1060_N_Visits_r_HEAL_%04d_SkyMap.png',
                            '-c:v','libx264','-r','1','-pix_fmt',
                            'yuv420p','NVisits_SkyMap.mp4'])
	    
        p.communicate

        p = subprocess.Popen(['ffmpeg', '-i', 'NVisits_SkyMap.mp4',  '-vcodec', 'copy', 'NVisits_SkyMap.mp4'])


        pass

