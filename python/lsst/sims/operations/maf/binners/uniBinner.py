# UniBinner class.
# This binner simply returns the indexes of all data points. No slicing done at all.

import numpy as np
import matplotlib.pyplot as plt
import warnings

from .baseBinner import BaseBinner

class UniBinner(BaseBinner):
    """UniBinner."""
    def __init__(self, simData, verbose=True):
        """Instantiate and set up unibinner. 

        Uses simData to know length of indexes that should be returned."""
        super(UniBinner, self).__init__(verbose=verbose)
        self.binnertype = 'UNI'
        self.nbins = 1
        simDataCol = simData.dtype.names[0]
        self.indices = np.where(simDataCol)

    def __iter__(self):
        """Iterate over the binpoints."""
        self.ipix = 0
        return self

    def next(self):
        """Set the binpoints to return when iterating over binner."""
        if self.ipix >= self.nbins:
            raise StopIteration
        ipix = self.ipix
        self.ipix += 1
        return ipix

    def __getitem__(self, ipix):
        return ipix
    
    def __eq__(self, otherBinner):
        """Evaluate if binners are equivalent."""
        if isinstance(otherBinner, UniBinner):
            return True
        else:
            return False
            
    def sliceSimData(self, binpoint):
        """Return all indexes in simData. """
        return self.indices
