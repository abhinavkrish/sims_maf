# cumulative one dimensional movie slicer
import numpy as np
import matplotlib.pyplot as plt
from functools import wraps
import warnings
from lsst.sims.maf.utils import percentileClipping, optimalBins, ColInfo
from .baseSlicer import BaseSlicer
import subprocess
import os

class MovieSlicer(BaseSlicer):
    """movie Slicer."""
    def __init__(self, sliceColName=None, sliceColUnits=None, 
                 bins=None, binMin=None, binMax=None, binsize=None,
                 verbose=True, badval=0, cumulative=True):
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
        self.cumulative = cumulative
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
        print 'this is the length of sliceCol: ', len(sliceCol)
        # Set bin min/max values.
        if self.binMin is None:
            self.binMin = sliceCol.min()
        if self.binMax is None:
            self.binMax = sliceCol.max()
        print self.binMin, self.binMax
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
            print 'I think self.bins is being set here: ', len(self.bins)
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
        print 'this is the number of bins total in left: ', len(self.left), self.left
        # Set up _sliceSimData method for this class.
        if self.cumulative:
            @wraps(self._sliceSimData)
            def _sliceSimData(islice):
                """
                Slice simData on oneD sliceCol, to return relevant indexes for slicepoint.
                """
                #this is the important part. The ids here define the pieces of data that get 
                #passed on to subsequent slicers
                #cumulative version of 1D slicing
                idxs = self.simIdxs[0:self.left[islice+1]]
                return {'idxs':idxs,
                        'slicePoint':{'sid':islice, 'binLeft':0, 'binRight':self.bins[islice+1]}}
            setattr(self, '_sliceSimData', _sliceSimData)      
        else:
            @wraps(self._sliceSimData)
            def _sliceSimData(islice):
                """
                Slice simData on oneD sliceCol, to return relevant indexes for slicepoint.
                """
                idxs = self.simIdxs[self.left[islice]:self.left[islice+1]]
                return {'idxs':idxs,
                        'slicePoint':{'sid':islice, 'binLeft':self.bins[islice], 'binRight':self.bins[islice+1]}}
            setattr(self, '_sliceSimData', _sliceSimData)
            
    def __eq__(self, otherSlicer):
        """
        Evaluate if slicers are equivalent.
        """
        if isinstance(otherSlicer, MovieSlicer):
            return np.all(otherSlicer.slicePoints['bins'] == self.slicePoints['bins'])
        else:
            return False

    def plotMovie(self, outfileroot, sliceformat, plotType, figformat, outDir='Output', ips=10.0, fps=10.0):
        """
        Takes in metric and slicer metadata and calls ffmpeg to stitch together output files.
        """
        if not os.path.isdir(outDir):
            raise Exception('Cannot find output directory %s with movie input files.' %(outDir))
        print 'HERE!!!!!!!!!!!!!!!!!!'
        #make video
        p = subprocess.check_call(['ffmpeg', '-r', str(ips), '-i',
                         '%s/%s_%s_%s.%s' %(outDir, outfileroot, sliceformat, plotType, figformat), 
                         '-c:v', 'libx264', '-r', 
                         str(fps), '-pix_fmt', 'yuv420p',
                         '%s/%s_%s_%s_%s.mp4' %(outDir, outfileroot, plotType, str(ips), str(fps))])
        print 'NOW IM HERE!!!!!!!!!!!!!!!!'
        #make thumbnail gif
        p2 = subprocess.check_call(['ffmpeg','-i', '%s/%s_%s_%s_%s.mp4' %(outDir, outfileroot, plotType, str(ips), str(fps)),
                        '-vf', 'scale=%s:%s' %(str(320),str(-1)), '-t', str(10), '-r', str(10), 
                        '%s/%s_%s_%s_%s.gif' %(outDir, outfileroot, plotType, str(ips), str(fps))])


