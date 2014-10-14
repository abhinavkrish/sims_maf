import numpy as np
import healpy as hp
from .baseMetric import BaseMetric
from scipy.spatial import cKDTree as kdtree

class LinkedMetric(BaseMetric):
    """Calculate how many other healpixels a given observation is linked to.  This is a fairly crude measure of how well the observations are linked for self-calibration pruposes.  An even better metric would look at the chip level since that's how large calibration patches will be.

    Maybe even better would be to find the common co-added depth of a pixel with all it's neighboring healpixels!  Maybe a complex metric with min and max reduce functions...Do I grab the 4 nearest pixels or 8?"""

    def __init__(self, metricName='linked', raCol='fieldRA', decCol='fieldDec',
                 nside=128, fovRad=1.8, **kwargs):
        """nside = healpixel nside
           fovRad = radius of the field of view in degrees"""
        cols = [raCol, decCol]
        self.needRADec = True #flag so binMetric will pass ra,dec of point
        super(LinkedMetric, self).__init__(col=cols, metricName=metricName, **kwargs)
        self.raCol = raCol
        self.decCol = decCol

        #build a kdtree for healpixel look-up

    def run(self, dataSlice, slicePoint):
        ra = slicePoint['ra']
        dec = slicePoint['dec']
        # Cut down to the unique set of ra,dec combinations

        pixlist=[]
        # For each ra,dec pointing, find the healpixels they overlap and append to the list

        pixlist = list(set(pixlist))
        return len(pixlist)
