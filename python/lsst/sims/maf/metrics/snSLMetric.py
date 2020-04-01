import numpy as np
import lsst.sims.maf.metrics as metrics
import healpy as hp
from lsst.sims.maf.stackers import snStacker
import numpy.lib.recfunctions as rf

__all__ = ['SNSLMetric']


class SNSLMetric(metrics.BaseMetric):
    def __init__(self, metricName='SNSLMetric',
                 mjdCol='observationStartMJD', RaCol='fieldRA', DecCol='fieldDec',
                 filterCol='filter', exptimeCol='visitExposureTime',
                 nightCol='night', obsidCol='observationId', nexpCol='numExposures',
                 vistimeCol='visitTime', m5Col='fiveSigmaDepth', season=[-1], coadd=False,
                 uniqueBlocks=False, **kwargs):
        """
        Strongly Lensed SN metric

        The number of is given by:

        N (lensed SNe Ia with well measured time delay) = 45.7 * survey_area /
        (20000 deg^2) * cumulative_season_length / (2.5 years) / (2.15 *
        exp(0.37 * gap_median_all_filter))

        where:
        survey_area: survey area (in deg2)
        cumulative_season_length: cumulative season length (in years)
        gap_median_all_filter: median gap (all filters)

        Parameters
        --------------
        metricName : str, opt
         metric name
         Default : SNCadenceMetric
        mjdCol : str, opt
         mjd column name
         Default : observationStartMJD,
        RaCol : str,opt
         Right Ascension column name
         Default : fieldRa
        DecCol : str,opt
         Declinaison column name
         Default : fieldDec
        filterCol : str,opt
         filter column name
         Default: filter
        exptimeCol : str,opt
         exposure time column name
         Default : visitExposureTime
        nightCol : str,opt
         night column name
         Default : night
        obsidCol : str,opt
         observation id column name
         Default : observationId
        nexpCol : str,opt
         number of exposure column name
         Default : numExposures
        vistimeCol : str,opt
         visit time column name
         Default : visitTime
        season: int (list) or -1, opt
         season to process (default: -1: all seasons)


        """
        self.mjdCol = mjdCol
        self.filterCol = filterCol
        self.RaCol = RaCol
        self.DecCol = DecCol
        self.exptimeCol = exptimeCol
        self.nightCol = nightCol
        self.obsidCol = obsidCol
        self.nexpCol = nexpCol
        self.vistimeCol = vistimeCol
        self.seasonCol = 'season'
        self.m5Col = m5Col

        cols = [self.nightCol, self.filterCol, self.mjdCol, self.obsidCol,
                self.nexpCol, self.vistimeCol, self.exptimeCol]

        super(SNSLMetric, self).__init__(
            col=cols, metricName=metricName, units='N SL', **kwargs)
        self.badVal = 0
        self.season = season
        self.bands = 'ugrizy'

        # stacker
        self.stacker = None
        if coadd:
            self.stacker = snStacker.CoaddStacker(mjdCol=self.mjdCol,
                                                  RaCol=self.RaCol, DecCol=self.DecCol,
                                                  m5Col=self.m5Col, nightCol=self.nightCol,
                                                  filterCol=self.filterCol, numExposuresCol=self.nexpCol,
                                                  visitTimeCol=self.vistimeCol, visitExposureTimeCol='visitExposureTime')

    def run(self, dataSlice, slicePoint=None):
        """
        Runs the metric for each dataSlice

        Parameters
        ---------------
        dataSlice: simulation data
        slicePoint:  slicePoint(default None)

        Returns
        -----------
        number of SL time delay supernovae

        """

        # get the pixel area
        area = hp.nside2pixarea(slicePoint['nside'], degrees=True)

        if len(dataSlice) == 0:
            return self.badVal

        dataSlice = self.seasonCalc(dataSlice)
        # stack data (if necessary)
        if self.stacker is not None:
            dataSlice = self.stacker._run(dataSlice)

        seasons = self.season

        if self.season == [-1]:
            seasons = np.unique(dataSlice[self.seasonCol])

        # get infos on seasons
        info_season = self.seasonInfo(dataSlice, seasons)
        if info_season is None:
            return self.badVal

        # get the cumulative season length

        r = []
        names = []
        season_length = np.sum(info_season['season_length'])
        r.append(season_length)
        names.append('cumul_season_length')

        # get gaps
        r.append(np.mean(info_season['gap_median']))
        names.append('gap_median')
        r.append(np.mean(info_season['gap_max']))
        names.append('gap_max')

        r.append(area)
        names.append('area')

        res = np.rec.fromrecords([r], names=names)

        # estimate the number of lensed supernovae
        cumul_season = res['cumul_season_length']/(12.*30.)

        if cumul_season <= 0:
            print('problem here', cumul_season)
        N_lensed_SNe_Ia = 45.7 * res['area'] / 20000. * cumul_season /\
            2.5 / (2.15 * np.exp(0.37 * res['gap_median']))

        res = N_lensed_SNe_Ia.item()
        if res <= 0 or np.isnan(res):
            print('Problem here', cumul_season, res)

        return res

    def seasonInfo(self, dataSlice, seasons):
        """
        Get info on seasons for each dataSlice

        Parameters
        ---------------
        dataSlice: array
          array of observations
        Returns
        -----------
        recordarray with the following fields:
        season, cadence, season_length, MJDmin, MJDmax, Nvisits
        gap_median, gap_max for each band
        """

        rv = []
        for season in seasons:
            idx = (dataSlice[self.seasonCol] == season)
            slice_sel = dataSlice[idx]

            if len(slice_sel) < 5:
                continue
            slice_sel.sort(order=self.mjdCol)
            mjds_season = slice_sel[self.mjdCol]
            cadence = mjds_season[1:]-mjds_season[:-1]
            mjd_min = np.min(mjds_season)
            mjd_max = np.max(mjds_season)
            season_length = mjd_max-mjd_min
            Nvisits = len(slice_sel)
            median_gap = np.median(cadence)
            mean_gap = np.mean(cadence)
            max_gap = np.max(cadence)

            rg = [float(season), np.mean(cadence), season_length,
                  mjd_min, mjd_max, Nvisits, median_gap, mean_gap, max_gap]

            rv.append(tuple(rg))

        info_season = None
        names = ['season', 'cadence', 'season_length',
                 'MJD_min', 'MJD_max', 'Nvisits']
        names += ['gap_median', 'gap_mean', 'gap_max']

        if len(rv) > 0:
            info_season = np.rec.fromrecords(
                rv, names=names)

        return info_season

    def seasonCalc(self, obs, season_gap=80., mjdCol='observationStartMJD'):
        """
        Method to estimate seasons

        Parameters
        --------------
       obs: numpy array
          array of observations
        season_gap: float, opt
          minimal gap required to define a season (default: 80 days)
        mjdCol: str, opt
          col name for MJD infos (default: observationStartMJD)

        Returns
        ----------
        original numpy array with season appended

        """

        # check wether season has already been estimated
        if 'season' in obs.dtype.names:
            return obs

        obs.sort(order=mjdCol)

        if len(obs) == 1:
            obs = np.atleast_1d(obs)
            obs = rf.append_fields([obs], 'season', [1.])
            return obs
        diff = obs[mjdCol][1:]-obs[mjdCol][:-1]

        flag = np.argwhere(diff > season_gap)
        if len(flag) > 0:
            seas = np.zeros((len(obs),), dtype=int)
            flag += 1
            seas[0:flag[0][0]] = 1
            for iflag in range(len(flag)-1):
                seas[flag[iflag][0]:flag[iflag+1][0]] = iflag+2
            seas[flag[-1][0]:] = len(flag)+1
            obs = rf.append_fields(obs, 'season', seas)
        else:
            obs = rf.append_fields(obs, 'season', [1]*len(obs))

        return obs
