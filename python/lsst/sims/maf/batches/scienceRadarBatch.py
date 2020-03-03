import healpy as hp
import lsst.sims.maf.metrics as metrics
import lsst.sims.maf.slicers as slicers
import lsst.sims.maf.stackers as stackers
import lsst.sims.maf.plots as plots
import lsst.sims.maf.metricBundles as mb
from lsst.sims.maf.batches import intraNight, interNight
from .colMapDict import ColMapDict
from .srdBatch import fOBatch, astrometryBatch, rapidRevisitBatch
import numpy as np
from lsst.sims.utils import hpid2RaDec, angularSeparation

__all__ = ['scienceRadarBatch']


def scienceRadarBatch(colmap=None, runName='', extraSql=None, extraMetadata=None, nside=64,
                      benchmarkArea=18000, benchmarkNvisits=825, DDF=True):
    """A batch of metrics for looking at survey performance relative to the SRD and the main
    science drivers of LSST.

    Parameters
    ----------

    """
    # Hide dependencies
    from mafContrib.LSSObsStrategy.galaxyCountsMetric_extended import GalaxyCountsMetric_extended
    from mafContrib import Plasticc_metric, plasticc_slicer, load_plasticc_lc

    if colmap is None:
        colmap = ColMapDict('opsimV4')

    if extraSql is None:
        extraSql = ''
    if extraSql == '':
        joiner = ''
    else:
        joiner = ' and '

    bundleList = []
    filters = 'ugrizy'

    healslicer = slicers.HealpixSlicer(nside=nside)
    subsetPlots = [plots.HealpixSkyMap(), plots.HealpixHistogram()]

    # Load up the plastic light curves
    models = ['SNIa-normal', 'KN']
    plasticc_models_dict = {}
    for model in models:
        plasticc_models_dict[model] = list(load_plasticc_lc(model=model).values())

    #########################
    # SRD, DM, etc
    #########################
    f0b = fOBatch(runName=runName, colmap=colmap, extraSql=extraSql, extraMetadata=extraMetadata,
                  benchmarkArea=benchmarkArea, benchmarkNvisits=benchmarkNvisits)
    astromb = astrometryBatch(runName=runName, colmap=colmap, extraSql=extraSql, extraMetadata=extraMetadata)
    rapidb = rapidRevisitBatch(runName=runName, colmap=colmap, extraSql=extraSql, extraMetadata=extraMetadata)

    # loop through and modify the display dicts if needed
    temp_list = []
    for key in f0b:
        temp_list.append(f0b[key])
    for key in astromb:
        temp_list.append(astromb[key])
    for key in rapidb:
        temp_list.append(rapidb[key])
    for metricb in temp_list:
        metricb.displayDict['subgroup'] = metricb.displayDict['group']
        metricb.displayDict['group'] = 'SRD'
    bundleList.extend(temp_list)

    displayDict = {'group': 'SRD', 'subgroup': 'Coverage', 'order': 0, 'caption': 'Number of years with observations.'}
    slicer = slicers.HealpixSlicer(nside=nside)
    metric = metrics.CoverageMetric()
    plotDict = {'colorMin': 7, 'colorMax': 10}
    for filtername in filters:
        sql = 'filter="%s"' % filtername
        bundleList.append(mb.MetricBundle(metric, slicer, sql, plotDict=plotDict))

    #########################
    # Solar System
    #########################

    # XXX -- may want to do Solar system seperatly

    # XXX--fraction of NEOs detected (assume some nominal size and albido)
    # XXX -- fraction of MBAs detected
    # XXX -- fraction of KBOs detected
    # XXX--any others? Planet 9s? Comets? Neptune Trojans?

    #########################
    # Cosmology
    #########################

    displayDict = {'group': 'Cosmology', 'subgroup': 'galaxy counts', 'order': 0, 'caption': None}
    plotDict = {'percentileClip': 95.}
    sql = extraSql + joiner + 'filter="i"'
    metric = GalaxyCountsMetric_extended(filterBand='i', redshiftBin='all', nside=nside)
    summary = [metrics.AreaSummaryMetric(area=18000, reduce_func=np.sum, decreasing=True, metricName='N Galaxies (WFD)')]
    summary.append(metrics.SumMetric(metricName='N Galaxies (all)'))
    # make sure slicer has cache off
    slicer = slicers.HealpixSlicer(nside=nside, useCache=False)
    bundle = mb.MetricBundle(metric, slicer, sql, plotDict=plotDict,
                             displayDict=displayDict, summaryMetrics=summary,
                             plotFuncs=subsetPlots)
    bundleList.append(bundle)
    displayDict['order'] += 1

    # let's put Type Ia SN in here
    displayDict['subgroup'] = 'SNe Ia'
    metadata = ''
    # XXX-- use the light curves from PLASTICC here
    displayDict['caption'] = 'Fraction of normal SNe Ia'
    sql = ''
    slicer = plasticc_slicer(plcs=plasticc_models_dict['SNIa-normal'], seed=42, badval=0)
    metric = Plasticc_metric(metricName='SNIa')
    # Set the maskval so that we count missing objects as zero.
    summary_stats = [metrics.MeanMetric(maskVal=0)]
    plotFuncs = [plots.HealpixSkyMap()]
    bundle = mb.MetricBundle(metric, slicer, sql, runName=runName, summaryMetrics=summary_stats,
                             plotFuncs=plotFuncs, metadata=metadata, displayDict=displayDict)
    bundleList.append(bundle)
    displayDict['order'] += 1

    # XXX--need some sort of metric for weak lensing and camera rotation.

    #########################
    # Variables and Transients
    #########################
    displayDict = {'group': 'Variables and Transients', 'subgroup': 'Periodic Stars',
                   'order': 0, 'caption': None}
    periods = [0.1, 0.5, 1., 2., 5., 10., 20.]  # days
    amplitudes = [.05]*len(periods)
    starMags = [20]*len(periods)

    plotDict = {}
    metadata = ''
    sql = extraSql
    displayDict['caption'] = 'Measure if a periodic signal can be detected for an r=%i star with amplitude of %.2f mags and variety of periods' % (max(starMags), max(amplitudes))

    summary = metrics.MeanMetric()
    metric = metrics.PeriodicDetectMetric(periods=periods, starMags=starMags, amplitudes=amplitudes)
    bundle = mb.MetricBundle(metric, healslicer, sql, metadata=metadata,
                             displayDict=displayDict, plotDict=plotDict,
                             plotFuncs=subsetPlots, summaryMetrics=summary)
    bundleList.append(bundle)
    displayDict['order'] += 1

    # XXX add some PLASTICC metrics for kilovnova and tidal disruption events.
    displayDict['subgroup'] = 'KN'
    displayDict['caption'] = 'Fraction of Kilonova (from PLASTICC)'
    sql = ''
    slicer = plasticc_slicer(plcs=plasticc_models_dict['KN'], seed=43, badval=0)
    metric = Plasticc_metric(metricName='KN')
    summary_stats = [metrics.MeanMetric(maskVal=0)]
    plotFuncs = [plots.HealpixSkyMap()]
    bundle = mb.MetricBundle(metric, slicer, sql, runName=runName, summaryMetrics=summary_stats,
                             plotFuncs=plotFuncs, metadata=metadata,
                             displayDict=displayDict)
    bundleList.append(bundle)

    displayDict['order'] += 1

    # XXX -- would be good to add some microlensing events, for both MW and LMC/SMC.

    #########################
    # Milky Way
    #########################

    displayDict = {'group': 'Milky Way', 'subgroup': '',
                   'order': 0, 'caption': None}

    #########################
    # DDF
    #########################
    ddf_time_bundleDicts = []
    if DDF:
        # Hide this import to avoid adding a dependency.
        from lsst.sims.featureScheduler.surveys import generate_dd_surveys
        ddf_surveys = generate_dd_surveys()
        # For doing a high-res sampling of the DDF for co-adds
        ddf_radius = 1.8  # Degrees
        ddf_nside = 512

        ra, dec = hpid2RaDec(ddf_nside, np.arange(hp.nside2npix(ddf_nside)))

        displayDict = {'group': 'DDF depths', 'subgroup': None,
                       'order': 0, 'caption': None}

        for survey in ddf_surveys:
            displayDict['subgroup'] = survey.survey_name
            # Crop off the u-band only DDF
            if survey.survey_name[0:4] != 'DD:u':
                dist_to_ddf = angularSeparation(ra, dec, np.degrees(survey.ra), np.degrees(survey.dec))
                goodhp = np.where(dist_to_ddf <= ddf_radius)
                slicer = slicers.UserPointsSlicer(ra=ra[goodhp], dec=dec[goodhp], useCamera=False)
                for filtername in ['u', 'g', 'r', 'i', 'z', 'y']:
                    metric = metrics.Coaddm5Metric(metricName=survey.survey_name+', ' + filtername)
                    summary = [metrics.MedianMetric(metricName='median depth ' + survey.survey_name+', ' + filtername)]
                    sql = extraSql + joiner + 'filter = "%s"' % filtername
                    bundle = mb.MetricBundle(metric, slicer, sql, metadata=metadata,
                                             displayDict=displayDict, summaryMetrics=summary,
                                             plotFuncs=[])
                    bundleList.append(bundle)
                    displayDict['order'] += 1

        displayDict = {'group': 'DDF Transients', 'subgroup': None,
                       'order': 0, 'caption': None}
        for survey in ddf_surveys:
            displayDict['subgroup'] = survey.survey_name
            if survey.survey_name[0:4] != 'DD:u':
                slicer = plasticc_slicer(plcs=plasticc_models_dict['SNIa-normal'], seed=42,
                                         ra_cen=survey.ra, dec_cen=survey.dec, radius=np.radians(3.), useCamera=False)
                metric = Plasticc_metric(metricName=survey.survey_name+' SNIa')
                sql = ''
                summary_stats = [metrics.MeanMetric(maskVal=0)]
                plotFuncs = [plots.HealpixSkyMap()]
                bundle = mb.MetricBundle(metric, slicer, sql, runName=runName, summaryMetrics=summary_stats,
                                         plotFuncs=plotFuncs, metadata=metadata,
                                         displayDict=displayDict)
                bundleList.append(bundle)

    displayDict['order'] += 1

    for b in bundleList:
        b.setRunName(runName)

    bundleDict = mb.makeBundlesDictFromList(bundleList)

    for ddf_time in ddf_time_bundleDicts:
        bundleDict.update(ddf_time)

    return bundleDict
