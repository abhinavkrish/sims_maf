import numpy as np
import matplotlib.pyplot as plt
import lsst.sims.maf.db as db
import lsst.sims.maf.utils as utils
import lsst.sims.maf.metrics as metrics
import lsst.sims.maf.binners as binners
import lsst.sims.maf.binMetrics as binMetrics


oo = db.OpsimDatabase('sqlite:///opsimblitz1_1131_sqlite.db')

cols = ['fieldID', 'fieldRA', 'fieldDec']
simdata = oo.fetchMetricData(cols, '')
fielddata = oo.fetchFieldsFromFieldTable()

# Add dither column
randomdither = utils.RandomDither(maxDither=1.8, randomSeed=42)
simdata = randomdither.run(simdata)

# Add columns showing the actual dither values
# Note that because RA is wrapped around 360, there will be large values of 'radith' near this point
radith = simdata['randomRADither'] - simdata['fieldRA']
decdith = simdata['randomDecDither'] - simdata['fieldDec']
stackIn = np.core.records.fromarrays([radith, decdith], names=['radith', 'decdith'])
simdata = utils.addCols._opsimStack([simdata, stackIn])


metriclist = []
metriclist.append(metrics.MeanMetric('radith'))
metriclist.append(metrics.MeanMetric('decdith'))
metriclist.append(metrics.RmsMetric('radith'))
metriclist.append(metrics.RmsMetric('decdith'))
metriclist.append(metrics.FullRangeMetric('radith'))
metriclist.append(metrics.FullRangeMetric('decdith'))

binner = binners.OpsimFieldBinner()
binner.setupBinner(simdata, fielddata)

gm = binMetrics.BaseBinMetric()
gm.setBinner(binner)
gm.setMetrics(metriclist)
gm.runBins(simdata, 'Dither Test')
gm.plotAll(savefig=False)
plt.show()
