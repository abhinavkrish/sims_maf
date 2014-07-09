# Examples of all the plotting dictionary options

from lsst.sims.maf.driver.mafConfig import configureSlicer, configureMetric, makeDict

root.outputDir = './SimplePlotDict'
root.dbAddress = {'dbAddress':'sqlite:///opsimblitz2_1060_sqlite.db'}
root.opsimName =  'ob2_1060'
nside=16
slicerList=[]

plotDict={ 'title':'A Great New Title',  'xMin':0.5, 'xMax':1.7}

m1 = configureMetric('MeanMetric', params=['finSeeing'], plotDict=plotDict, kwargs={'metricName':'wplotdict'})
m2 = configureMetric('MeanMetric', params=['finSeeing'])

metricDict = makeDict(m1,m2)

slicer = configureSlicer('HealpixSlicer',kwargs={"nside":nside},
                          metricDict = metricDict,constraints=['filter="r"'])
slicerList.append(slicer)
root.slicers=makeDict(*slicerList)
