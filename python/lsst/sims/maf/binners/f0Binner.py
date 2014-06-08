# Class for computing the f_0 metric.  Nearly identical 
# to HealpixBinner, but with an added plotting method

import numpy as np
import matplotlib.pyplot as plt
from .healpixBinner import HealpixBinner
import healpy as hp
from lsst.sims.maf.metrics.summaryMetrics import f0Area, f0Nv

class f0Binner(HealpixBinner):
    """f0 spatial binner"""
    def __init__(self, nside=128, spatialkey1 ='fieldRA' , spatialkey2='fieldDec', verbose=True):
        super(f0Binner, self).__init__(verbose=verbose, spatialkey1=spatialkey1, spatialkey2=spatialkey2,
                                        nside=nside)
        # Override base plotFuncs dictionary, because we don't want to create plots from Healpix
        #  binner (skymap, power spectrum, and histogram) -- only f0 plot -- when using 'plotData'.
        self.plotFuncs = {'plotF0':self.plotF0}
    
    
    def plotF0(self, metricValue, title=None, xlabel='Number of Visits',
               ylabel='Area (1000s of square degrees)', fignum=None,
               scale=None, Asky=18000., Nvisit=825, 
               xMin=None, xMax=None, yMin=None, yMax=None, **kwargs):
        """ 
        Note that Asky and Nvisit need to be set for both the binner and the summary statistic
          for the plot and returned summary stat values to be consistent!"""
        plottype = 'f0'
        colorlinewidth = 2
        if scale is None:
            scale = (hp.nside2pixarea(hp.npix2nside(metricValue.size), degrees=True)  / 1000.0)
        if fignum:
            fig = plt.figure(fignum)
        else:
            fig = plt.figure()
        # Expect metricValue to be something like number of visits
        cumulativeArea = np.arange(1,metricValue.compressed().size+1)[::-1]*scale
        plt.plot(np.sort(metricValue.compressed()), cumulativeArea,'k-', linewidth=2, zorder = 0)
        # This is breaking the rules and calculating the summary stats in two places.
        # One way to possibly clean this up in the future would be to change the order
        # things are done in the driver so that summary stats get computed first and passed along to the plotting.
        f0Area_value = f0Area(None,Asky=Asky, norm=False, nside=self.nside).run(np.array(metricValue.compressed(),
                                                                                         dtype=[('f0', metricValue.dtype)]))
        f0Nv_value = f0Nv(None,Nvisit=Nvisit, norm=False, nside=self.nside).run(np.array(metricValue.compressed(),
                                                                                         dtype=[('f0', metricValue.dtype)]))
        f0Area_value_n = f0Area(None,Asky=Asky, norm=True, nside=self.nside).run(np.array(metricValue.compressed(),
                                                                                          dtype=[('f0', metricValue.dtype)]))
        f0Nv_value_n = f0Nv(None,Nvisit=Nvisit, norm=True, nside=self.nside).run(np.array(metricValue.compressed(),
                                                                                          dtype=[('f0', metricValue.dtype)]))

        plt.axvline(x=Nvisit, linewidth=colorlinewidth, color='b')
        plt.axhline(y=Asky/1000., linewidth=colorlinewidth,color='r')
        
        plt.axhline(y=f0Nv_value/1000., linewidth=colorlinewidth, color='b', 
                    alpha=.5, label=r'f$_0$ Nvisits=%.3g'%f0Nv_value_n)
        plt.axvline(x=f0Area_value , linewidth=colorlinewidth,color='r', 
                    alpha=.5, label='f$_0$ Area=%.3g'%f0Area_value_n)
        plt.legend(loc='lower left', fontsize='small', numpoints=1)

        plt.xlabel(xlabel)
        plt.ylabel(ylabel)

        if title is not None:
            plt.title(title)

        if (xMin is not None) & (xMax is not None):
            plt.xlim([xMin,xMax])
        if (yMin is not None) & (yMax is not None):
            plt.ylim([yMin,yMax])
        
        return fig.number
