import numpy
import lsst.sims.operations.maf.utils.testUtils as tu
import lsst.sims.operations.maf.grids as grids
import lsst.sims.operations.maf.metrics as metrics
import lsst.sims.operations.maf.gridMetrics as gridMetrics
import glob

# set up some test data
simdata = tu.makeSimpleTestSet()

print 'simdata shape', numpy.shape(simdata)
print simdata.dtype.names

# Set up grid.
#gg = grids.GlobalGrid()
gg = grids.HealpixGrid(16)
gg.buildTree(simdata['fieldra'],simdata['fielddec'])

# Set up metrics.
magmetric = metrics.MeanMetric('m5')
seeingmean = metrics.MeanMetric('seeing')
seeingrms = metrics.RmsMetric('seeing')
visitpairs = metrics.VisitPairsMetric('expmjd')

print magmetric.classRegistry

gm = gridMetrics.BaseGridMetric()
gm.setGrid(gg)
#gm.setupRun([magmetric, seeingmean, seeingrms], simdata)
gm.runGrid([magmetric, seeingmean, seeingrms,visitpairs], simdata)
#print gm.metricValues
print gm.metricValues[magmetric.name]
print gm.metricValues[seeingmean.name]
print gm.metricValues[seeingrms.name]

#try to save and restore
#gm.writeMetric([magmetric, seeingmean, seeingrms],outfile_root='savetest')
gm.writeAll(outfileRoot='savetest')
#the fits files that were output
filenames = glob.glob('savetest*.fits')

#new object to restore info into
ack = gridMetrics.BaseGridMetric(None) #can instant with None grid since it will be restored from pickle.
ack.readMetric(filenames)
print ack.metricValues[magmetric.name]
print ack.metricValues[seeingmean.name]
print ack.metricValues[seeingrms.name]



