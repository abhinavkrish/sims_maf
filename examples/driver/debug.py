# A MAF config that replicates the SSTAR plots
from lsst.sims.maf.driver.mafConfig import *

# Setup Database access
root.outputDir ='./StarOut_Fields'

small = True # Use the small database included in the repo

if small:
    root.dbAddress ={'dbAddress':'sqlite:///../opsim_small.sqlite'}
    root.opsimNames = ['opsim_small']
    propids = [186,187,188,189]
    WFDpropid = 188
    DDpropid = 189 #?
else:
    root.dbAddress ={'dbAddress':'sqlite:///opsim.sqlite'}
    root.opsimNames = ['opsim']
    propids = [215, 216, 217, 218, 219]
    WFDpropid = 217
    DDpropid = 219

filters = ['u','g','r','i','z','y']
colors={'u':'m','g':'b','r':'g','i':'y','z':'r','y':'k'}
#filters=['r']

# 10 year Design Specs
nvisitBench={'u':56,'g':80, 'r':184, 'i':184, 'z':160, 'y':160} 
nVisits_plotRange = {'all': 
                     {'u':[25, 75], 'g':[50,100], 'r':[150, 200], 'i':[150, 200], 'z':[100, 250], 'y':[100,250]},
                     'DDpropid': 
                     {'u':[6000, 10000], 'g':[2500, 5000], 'r':[5000, 8000], 'i':[5000, 8000],  'z':[7000, 10000], 'y':[5000, 8000]},
                     '216':
                     {'u':[20, 40], 'g':[20, 40], 'r':[20, 40], 'i':[20, 40], 'z':[20, 40], 'y':[20, 40]}}
mag_zpoints={'u':26.1,'g':27.4, 'r':27.5, 'i':26.8, 'z':26.1, 'y':24.9}
sky_zpoints = {'u':21.8, 'g':22., 'r':21.3, 'i':20.0, 'z':19.1, 'y':17.5}
seeing_norm = {'u':0.77, 'g':0.73, 'r':0.7, 'i':0.67, 'z':0.65, 'y':0.63}

binList=[]




    

# Completeness and Joint Completeness
m1 = makeMetricConfig('CompletenessMetric', plotDict={'xlabel':'# visits (WFD only) / (# WFD Requested)','units':'# visits (WFD only)/ # WFD','plotMin':.5, 'plotMax':1.5, 'histBins':50}, kwargs={'u':56., 'g':80., 'r':184., 'i':184.,"z":160.,"y":160.}, summaryStats={'TableFractionMetric':{},'ExactCompleteMetric':{}})
# For just WFD proposals
binner = makeBinnerConfig('OpsimFieldBinner', metricDict=makeDict(m1), metadata='WFD', constraints=["propID = %d" %(WFDpropid)])
binList.append(binner)
# For all Observations
m1 = makeMetricConfig('CompletenessMetric', plotDict={'xlabel':'# visits (all) / (# WFD Requested)','units':'# visits (all) / # WFD','plotMin':.5, 'plotMax':1.5, 'histBins':50}, kwargs={'u':56., 'g':80., 'r':184., 'i':184.,"z":160.,"y":160.}, summaryStats={'TableFractionMetric':{},'ExactCompleteMetric':{}})
binner = makeBinnerConfig('OpsimFieldBinner',metricDict=makeDict(m1),constraints=[""])
binList.append(binner)




root.binners=makeDict(*binList)


