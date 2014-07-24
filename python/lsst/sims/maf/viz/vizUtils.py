import lsst.sims.maf.db as db
import numpy as np
import numpy.lib.recfunctions as rfn
import os

def loadResults(sourceDir):
    """Load up the three tables from resultsDb_sqlite.db """
    database = db.Database('sqlite:///'+sourceDir+'/resultsDb_sqlite.db',
                           dbTables={'metrics':['metrics','metricID'] ,
                                     'plots':['plots','plotId'],
                                     'stats':['summarystats','statId']})
    # Hmm, seems like there should be a better way to do this--maybe an outer join or something?
    metrics = database.queryDatabase('metrics', 'select * from metrics')
    plots = database.queryDatabase('plots', 'select * from plots')
    stats = database.queryDatabase('stats', 'select * from summarystats')

    #grab the runName as well
    configFile = os.path.join(sourceDir, 'configSummary.txt' )
    if os.path.isfile(configFile):
        with open (configFile, "r") as myfile:
            config=myfile.read().replace('\n', '')
        spot = config.find('RunName')
        runName = config[spot:spot+300].split(' ')[1]
    else:
        runName = 'No configSummary.txt'
    
    return metrics, plots, stats, runName


def blockAll(metrics, plots, stats):
    """Package up all the MAF results to be displayed"""
    blocks = []
    for mId in metrics['metricId']:
        relevant_plots = plots[np.where(plots['metricId'] == mId)[0]]
        for i in np.arange(relevant_plots.size):
            relevant_plots['plotFile'][i] = relevant_plots['plotFile'][i].replace('.pdf', '.png')
        relevant_stats = stats[np.where(stats['metricId'] == mId)[0] ]
        relevant_metrics = metrics[np.where(metrics['metricId'] == mId)[0] ]
        stat_list = [(i, '%.4g'%j) for i,j in  zip(relevant_stats['summaryName'],
                                                   relevant_stats['summaryValue']) ]  
        blocks.append({'NameInfo': relevant_metrics['metricName'][0]+', '+
                       relevant_metrics['slicerName'][0]
                       + ', ' +  relevant_metrics['sqlConstraint'][0],
                       'plots':relevant_plots['plotFile'].tolist(),
                       'stats':stat_list})

    return blocks


def blockSS(metrics, plots, stats):
    """Group up results to be layed out in SSTAR-like way """
    # Set up lists that will be looped over by template
    blocks =[]
    completenessBlocks = []
    identStats = []
    basicStats = []
    completeStats = []
    etcStats = []

    # Stack on an extra column for the column name so we can sort on it
    # and get "Median Airmass" next to "Rms Airmass", etc.
     
    metrics = rfn.merge_arrays([metrics, np.empty(metrics.size,
                                                  dtype=[('colName','|S256'), ('filt', '|S256')])],
                               flatten=True, usemask=False)
    
    for i in np.arange(metrics.size):
        filt = metrics['metricMetadata'][i].replace(' u ', ' a ')
        filt.replace(' g ', ' b ')
        filt.replace(' r ', ' c ')
        filt.replace(' i ', ' d ')
        filt.replace(' z ', ' e ')
        filt.replace(' y ', ' f ')
        metrics['filt'][i] = filt
        name = metrics['metricName'][i].split(' ')
        if len(name) > 1:
            metrics['colName'][i] = name[1]
        else:
            metrics['colName'][i] = metrics['metricName'][i]
    
    metrics.sort(order=['colName', 'slicerName', 'filt', 'sqlConstraint'])

    for metric in metrics:
        mId = metric['metricId']
        relevant_plots = plots[np.where(plots['metricId'] == mId)[0]]
        for i in np.arange(relevant_plots.size):
            relevant_plots['plotFile'][i] = relevant_plots['plotFile'][i].replace('.pdf', '.png')
        relevant_stats = stats[np.where(stats['metricId'] == mId)[0] ]
        
        relevant_metrics = metrics[np.where(metrics['metricId'] == mId)[0] ]
        stat_list = [(i, '%.4g'%j) for i,j in  zip(relevant_stats['summaryName'],
                                                   relevant_stats['summaryValue']) ]
        statsDict={}
        name = relevant_metrics['metricName'][0]+', '+ \
                             relevant_metrics['slicerName'][0] \
                             + ', ' +  relevant_metrics['sqlConstraint'][0]
        for rel_stat in relevant_stats:
            statsDict[rel_stat['summaryName']] = '%.4g'%rel_stat['summaryValue']

        # Break it down into 4 different summary stat tables,
        # 1) Completeness tables
        # 2) Identity (i.e., unislicer) table
        # 3) "basic" table (mean, RMS, median, p/m 3 sigma...)
        # 4) the etc table for anything left over.
        if statsDict != {} :
            if 'Completeness' in name:
                completeStats.append({'NameInfo':name, 'stats':statsDict} )
            elif 'Identity' in statsDict.keys():
                identStats.append({'NameInfo':name, 'stats':statsDict})
            elif ('Mean' in statsDict.keys()) & ('Rms' in statsDict.keys()):
                basicStats.append({'NameInfo':name, 'stats':statsDict} )
            else:
                etcStats.append({'NameInfo':name, 'stats':statsDict} )
        block = {'NameInfo': relevant_metrics['metricName'][0]+', '+
                       relevant_metrics['slicerName'][0]
                       + ', ' +  relevant_metrics['sqlConstraint'][0],
                       'plots':relevant_plots['plotFile'].tolist(),
                       'stats':stat_list}
        # If it's a completeness metric, pull it out
        if metric['metricName'][0:12] == 'Completeness':
            completenessBlocks.append(block)
        else:
            blocks.append(block)
            
    return {'blocks':blocks, 'completenessBlocks':completenessBlocks,
            'identStats':identStats, 'basicStats':basicStats,
            'completeStats':completeStats, 'etcStats':etcStats}
