# Class for opsim field based binner.

import numpy as np
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import pyfits as pyf
from .baseBinner import BaseBinner

from .baseSpatialBinner import BaseSpatialBinner

class OpsimFieldBinner(BaseSpatialBinner):
    """Opsim Field based binner."""
    def __init__(self, ra, dec, verbose=True):
        """Set up opsim field binner object."""
        super(OpsimFieldBinner, self).__init__(verbose=verbose)
        self.ra = ra
        self.dec = dec
        self.npix = len(self.ra)
        return

    def readRADecFromFile(self, filename):
        pass

    def readRADecFromDB(self):
        pass

    ## Should this binner slice on fieldID rather than RA/Dec values?
    
    def __iter__(self):
        """Iterate over the binpoints."""
        self.ipix = 0
        return self
    
    def next(self):
        """Return RA/Dec values when iterating over binpoints."""
        # This returns RA/Dec (in radians) of points in the grid. 
        if self.ipix >= self.npix:
            raise StopIteration
        radec = self.ra[self.ipix], self.dec[self.ipix]
        self.ipix += 1
        return radec

    def __getitem__(self, ipix):
        radec = self.ra[self.ipix], self.dec[self.ipix]
        return radec

    def __eq__(self, otherBinner):
        """Evaluate if two grids are equivalent."""
        if isinstance(otherBinner, OpsimFieldBinner):
            return ((np.all(otherBinner.ra == self.ra)) 
                    and (np.all(otherBinner.dec == self.dec)))
        else:
            return False

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
        import numpy as np
        from matplotlib.patches import Ellipse   
        ellipses = []
        if ax is None:
            ax = plt.gca()            
        for long, lat, rad in np.broadcast(longitude, latitude, radius):
            el = Ellipse((long, lat), radius / np.cos(lat), radius, **kwargs)
            ellipses.append(el)
        return ellipses

        
    def plotSkyMap(self, metricValue, metricLabel, title=None, projection='aitoff',
                   clims=None, cbarFormat='%.2g', cmap=cm.jet, fignum=None):
        """Plot the sky map of metricValue."""
        from matplotlib.collections import PatchCollection
        if fignum==None:
            fig = plt.figure()
        ax = plt.subplot(projection=projection)
        # other projections available include 
        # ['aitoff', 'hammer', 'lambert', 'mollweide', 'polar', 'rectilinear']
        radius = 3.5 * np.pi / 180.
        ellipses = self._plot_tissot_ellipse(self.ra, self.dec, radius,
                                             ax=ax, linewidth=0)
        p = PatchCollection(ellipses, cmap=cmap, alpha=0.3)
        p.set_array(metricValue)
        ax.add_collection(p)
        if clims != None:
            p.set_clim(clims)
        cb = plt.colorbar(p, orientation='horizontal', format=cbarFormat)
        if title != None:
            plt.title(title)
        return fig.number
   

    def writeMetricData(self, outfilename, metricValues,
                        comment='', metricName='',
                        simDataName='', metadata='', 
                        int_badval=-666, badval=-666., dt=np.dtype('float64')):
        """Write metric data and bin data in a fits file """

        header_dict = dict(comment=comment, metricName=metricName,
                           simDataName=simDataName,
                           metadata=metadata, binnertype=self.binnertype,
                           dt=dt.name, badval=badval, int_badval=int_badval)
        base = BaseBinner()
        base.writeMetricDataGeneric(outfilename=outfilename,
                        metricValues=metricValues,
                        comment=comment, metricName=metricName,
                        simDataName=simDataName, metadata=metadata, 
                        int_badval=int_badval, badval=badval, dt=dt)
        #update the header
        hdulist = pyf.open(outfilename, mode='update')
        for key in header_dict.keys():
            hdulist[0].header[key] = header_dict[key]
        hdulist.close()

        #append the bins
        hdulist = pyf.open(outfilename, mode='append')
        raHDU = pyf.PrimaryHDU(data=self.ra)
        decHDU =  pyf.PrimaryHDU(data=self.dec)
        hdulist.append(raHDU)
        hdulist.append(decHDU)
        hdulist.flush()
        hdulist.close()
        
        return outfilename

    def readMetricData(self, infilename):
        """Read metric values back in and restore the binner"""

        #restore the bins first
        hdulist = pyf.open(infilename)
        if hdulist[0].header['binnertype'] != self.binnertype:
             raise Exception('Binnertypes do not match.')
        
        ra = hdulist[1].data.copy()
        dec = hdulist[2].data.copy()        
        base = BaseBinner()
        metricValues, header = base.readMetricDataGeneric(infilename)
        
        binner = OpsimFieldBinner(ra, dec)
       
        binner.badval = header['badval'.upper()]
        binner.int_badval = header['int_badval']
                
        return metricValues, binner,header
