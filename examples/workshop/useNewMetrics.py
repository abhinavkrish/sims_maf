# To use a new metric, make sure the path to the code is in your
#PYTHONPATH environement variable.  For example:
#setenv PYTHONPATH $PYTHONPATH':/some/path/here/'

from lsst.sims.maf.driver.mafConfig import configureMetric, configureSlicer, makeDict

root.outputDir = 'Out'
root.dbAddress = {'dbAddress':'sqlite:///opsimblitz1_1131_sqlite.db'}
root.opsimName = 'opsimblitz1_1131'

root.modules = ['exampleNewMetrics']

metric = configureMetric('exampleNewMetrics.SimplePercentileMetric', args=['airmass'])
slicer = configureSlicer('UniSlicer', metricDict=makeDict(metric), constraints=['filter="r"'])

root.slicers = makeDict(slicer)
