# The base class for all spatial binners.
# Binners are 'data slicers' at heart; spatial binners slice data by RA/Dec and 
#  return the relevant indices in the simData to the metric. 
# The primary things added here are the methods to slice the data (for any spatial binner)
#  as this uses a KD-tree built on spatial (RA/Dec type) indexes. 

import numpy as np
import matplotlib.cm as cm
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse   
from matplotlib.ticker import FuncFormatter

try:
    # Try cKDTree first, as it's supposed to be faster.
    from scipy.spatial import cKDTree as kdtree
    #current stack scipy has a bad version of cKDTree.  
    if not hasattr(kdtree,'query_ball_point'): 
        from scipy.spatial import KDTree as kdtree
except:
    # But older scipy may not have cKDTree.
    from scipy.spatial import KDTree as kdtree

from .baseBinner import BaseBinner

class BaseSpatialBinner(BaseBinner):
    """Base binner object, with added slicing functions for spatial binner."""
    def __init__(self, verbose=True, spatialkey1='fieldRA', spatialkey2='fieldDec'):
        """Instantiate the base spatial binner object."""
        super(BaseSpatialBinner, self).__init__(verbose=verbose)
        self.binnertype = 'SPATIAL'
        self.spatialkey1 = spatialkey1
        self.spatialkey2 = spatialkey2
        self.columnsNeeded = [spatialkey1,spatialkey2]
        self.binner_init={'spatialkey1':spatialkey1, 'spatialkey2':spatialkey2}
        

    def setupBinner(self, simData, leafsize=100, radius=1.8):
        """Use simData['spatialkey1'] and simData['spatialkey2']
        (in radians) to set up KDTree.

        spatialkey1 = ra, spatialkey2 = dec, typically: but must match order in binpoint.
        'leafsize' is the number of RA/Dec pointings in each leaf node of KDtree
        'radius' (in degrees) is distance at which matches between
        the simData KDtree 
        and binpoint RA/Dec values will be produced."""
        self._buildTree(simData[self.spatialkey1], simData[self.spatialkey2], leafsize)
        self._setRad(radius)
        self.binner_setup = {'leafsize':leafsize,'radius':radius}
    
    def _treexyz(self, ra, dec):
        """Calculate x/y/z values for ra/dec points, ra/dec in radians."""
        # Note ra/dec can be arrays.
        x = np.cos(dec) * np.cos(ra)
        y = np.cos(dec) * np.sin(ra)
        z = np.sin(dec)
        return x, y, z
    
    def _buildTree(self, simDataRa, simDataDec, 
                  leafsize=100):
        """Build KD tree on simDataRA/Dec and set radius (via setRad) for matching.

        simDataRA, simDataDec = RA and Dec values (in radians).
        leafsize = the number of Ra/Dec pointings in each leaf node."""
        if np.any(simDataRa > np.pi*2.0) or np.any(simDataDec> np.pi*2.0):
            raise Exception('Expecting RA and Dec values to be in radians.')
        x, y, z = self._treexyz(simDataRa, simDataDec)
        data = zip(x,y,z)
        if np.size(data) > 0:
            self.opsimtree = kdtree(data, leafsize=leafsize)
        else:
            self.opsimtree = []

    def _setRad(self, radius=1.8):
        """Set radius (in degrees) for kdtree search.
        
        kdtree queries will return pointings within rad."""        
        x0, y0, z0 = (1, 0, 0)
        x1, y1, z1 = self._treexyz(np.radians(radius), 0)
        self.rad = np.sqrt((x1-x0)**2+(y1-y0)**2+(z1-z0)**2)
    
    def sliceSimData(self, binpoint):
        """Return indexes for relevant opsim data at binpoint
         (binpoint=spatialkey1/spatialkey2 value .. usually ra/dec)."""
        binx, biny, binz = self._treexyz(binpoint[1], binpoint[2])
        # If there is no data, there is no tree to query, return an empty list
        if self.opsimtree == []:
            return []
        # If we were given more than one binpoint, try multiple query against the tree.
        if isinstance(binx, np.ndarray):
            indices = self.opsimtree.query_ball_point(zip(binx, biny, binz), 
                                                      self.rad)
        # If we were given one binpoint, do a single query against the tree.
        else:
            indices = self.opsimtree.query_ball_point((binx, biny, binz), 
                                                      self.rad)
        return indices

    ## Plot histogram (base spatial binner method).
        
    def plotHistogram(self, metricValue, title=None, xlabel=None, ylabel=None,
                      fignum=None, legendLabel=None, addLegend=False, legendloc='upper left',
                      bins=100, cumulative=False, histRange=None, ylog=False, flipXaxis=False,
                      scale=1.0, yaxisformat='%.3f'):
        """Plot a histogram of metricValue, labelled by metricLabel.

        title = the title for the plot (default None)
        fignum = the figure number to use (default None - will generate new figure)
        legendLabel = the label to use for the figure legend (default None)
        addLegend = flag for whether or not to add a legend (default False)
        legendloc = location for legend (default 'upper left')
        bins = bins for histogram (numpy array or # of bins) (default 100)
        cumulative = make histogram cumulative (default False)
        histRange = histogram range (default None, set by matplotlib hist)
        flipXaxis = flip the x axis (i.e. for magnitudes) (default False)
        scale = scale y axis by 'scale' (i.e. to translate to area)"""
        # Histogram metricValues. 
        fig = plt.figure(fignum)
        # Need to only use 'good' values in histogram,
        # but metricValue is masked array (so bad values masked when calculating max/min).
        if metricValue.min() >= metricValue.max():
            if histRange is None:
                histRange = [metricValue.min() , metricValue.min() + 1]
                raise warnings.warn('Max (%f) of metric Values was less than or equal to min (%f). Using (min value/min value + 1) as a backup for histRange.' 
                                    % (metricValue.max(), metricValue.min()))
        n, b, p = plt.hist(metricValue.compressed(), bins=bins, histtype='step', log=ylog,
                           cumulative=cumulative, range=histRange, label=legendLabel)        
        # Option to use 'scale' to turn y axis into area or other value.
        def mjrFormatter(y,  pos):        
            return yaxisformat % (y * scale)
        ax = plt.gca()
        ax.yaxis.set_major_formatter(FuncFormatter(mjrFormatter))
        # There is a bug in histype='step' that can screw up the ylim.  Comes up when running allBinner.Cfg.py
        if plt.axis()[2] == max(n):
            plt.ylim([n.min(),n.max()]) 
        if xlabel != None:
            plt.xlabel(xlabel)
        if ylabel != None:
            plt.ylabel(ylabel)
        if flipXaxis:
            # Might be useful for magnitude scales.
            x0, x1 = plt.xlim()
            plt.xlim(x1, x0)
        if addLegend:
            plt.legend(fancybox=True, prop={'size':'smaller'}, loc=legendloc)
        if title!=None:
            plt.title(title)
        # Return figure number (so we can reuse this if desired).         
        return fig.number
            
    ### Generate sky map (base spatial binner methods, using ellipses for each RA/Dec value)
    ### a healpix binner will not have self.ra / self.dec functions, but plotSkyMap is overriden.
    
    def _plot_tissot_ellipse(self, longitude, latitude, radius, ax=None, **kwargs):
        """Plot Tissot Ellipse/Tissot Indicatrix
        
        Parameters
        ----------
        longitude : float or array_like
        longitude of ellipse centers (radians)
        latitude : float or array_like
        latitude of ellipse centers (radians)
        radius : float or array_like
        radius of ellipses
        ax : Axes object (optional)
        matplotlib axes instance on which to draw ellipses.
        
        Other Parameters
        ----------------
        other keyword arguments will be passed to matplotlib.patches.Ellipse.

        # The code in this method adapted from astroML, which is BSD-licensed. 
        # See http://github.com/astroML/astroML for details.
        """
        # Code adapted from astroML, which is BSD-licensed. 
        # See http://github.com/astroML/astroML for details.
        ellipses = []
        if ax is None:
            ax = plt.gca()            
        for long, lat, rad in np.broadcast(longitude, latitude, radius*2.0):
            el = Ellipse((long, lat), rad / np.cos(lat), rad)
            ellipses.append(el)
        return ellipses

        
    def plotSkyMap(self, metricValue, title=None, projection='aitoff',
                   clims=None, ylog=False, cbarFormat=None, cmap=cm.jet, fignum=None, units=''):
        """Plot the sky map of metricValue."""
        from matplotlib.collections import PatchCollection
        from matplotlib import colors
        if fignum is None:
            fig = plt.figure()
        ax = plt.subplot(111,projection=projection)        
        # other projections available include 
        # ['aitoff', 'hammer', 'lambert', 'mollweide', 'polar', 'rectilinear']
        radius = 1.75 * np.pi / 180.
        ellipses = self._plot_tissot_ellipse((self.ra - np.pi), self.dec, radius, ax=ax)
        if ylog:
            norml = colors.LogNorm()
            p = PatchCollection(ellipses, cmap=cmap, alpha=1, linewidth=0, edgecolor=None,
                                norm=norml)
        else:
            p = PatchCollection(ellipses, cmap=cmap, alpha=1, linewidth=0, edgecolor=None)
        p.set_array(metricValue.filled(self.badval))
        ax.add_collection(p)
        if clims != None:
            p.set_clim(clims)
        cb = plt.colorbar(p, aspect=25, extend='both', orientation='horizontal', format=cbarFormat)
        cb.set_label(units)
        if title != None:
            plt.text(0.5, 1.09, title, horizontalalignment='center', transform=ax.transAxes)
        ax.grid()
        return fig.number
