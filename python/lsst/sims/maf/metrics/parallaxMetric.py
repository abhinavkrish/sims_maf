import numpy as np
from .baseMetric import BaseMetric
from .properMotionMetric import m52snr, astrom_precision

class ParallaxMetric(BaseMetric):
    """Calculaute the uncertainty in a parallax measure
    given a serries of observations"""

    def __init__(self, metricName='parallax', m5col='5sigma_modified',
                 mjdcol='expMJD', units = 'mas',
                 filtercol='filter', seeingcol='finSeeing', u=20.,
                 g=20., r=20., i=20., z=20., y=20., badval= -666,
                 stellarType=None, atm_err=0.01, normalize=False,**kwargs):
        
        """ Instantiate metric.

        m5col = column name for inidivual visit m5
        mjdcol = column name for exposure time dates
        filtercol = column name for filter
        seeingcol = column name for seeing (assumed FWHM)
        u,g,r,i,z = mag of fiducial star in each filter
        atm_err = centroiding error due to atmosphere in arcsec
        normalize = divide by the uncertainty if the 

        return uncertainty in mas.
        """
        cols = [m5col, mjdcol,filtercol,seeingcol, 'ra_pi_amp', 'dec_pi_amp']
        if normalize:
            units = 'ratio'
        super(ParallaxMetric, self).__init__(cols, metricName=metricName, units=units, **kwargs)
        # set return type
        self.m5col = m5col
        self.seeingcol = seeingcol
        self.filtercol = filtercol
        self.metricDtype = 'float'
        self.units = units
        self.mags={'u':u, 'g':g,'r':r,'i':i,'z':z,'y':y}
        self.badval = badval
        self.atm_err = atm_err
        self.normalize = normalize
        if stellarType != None:
            raise NotImplementedError('Spot to add colors for different stars')

    def _final_sigma(self, position_errors, ra_pi_amp, dec_pi_amp):
        sigma_A = position_errors/ra_pi_amp
        sigma_B = position_errors/dec_pi_amp
        sigma_ra = np.sqrt(1./np.sum(1./sigma_A**2))
        sigma_dec = np.sqrt(1./np.sum(1./sigma_B**2))
        sigma = np.sqrt(1./(1./sigma_ra**2+1./sigma_dec**2))*1e3 #combine RA and Dec uncertainties, convert to mas
        return sigma
        
    def run(self, dataslice):
        filters = np.unique(dataslice[self.filtercol])
        snr = np.zeros(len(dataslice), dtype='float')
        for filt in filters:
            good = np.where(dataslice[self.filtercol] == filt)
            snr[good] = m52snr(self.mags[filt], dataslice[self.m5col][good])
        position_errors = np.sqrt(astrom_precision(dataslice[self.seeingcol], snr)**2+self.atm_err**2)
        sigma = self._final_sigma(position_errors,dataslice['ra_pi_amp'],dataslice['dec_pi_amp'] )
        if self.normalize:
            sigma = self._final_sigma(position_errors,dataslice['ra_pi_amp']*0+1.,dataslice['dec_pi_amp']*0+1. )/sigma
        return sigma
        
