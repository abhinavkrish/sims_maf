from tornado import ioloop
from tornado import web
from jinja2 import Environment, FileSystemLoader
from collections import OrderedDict
import glob
import lsst.sims.maf.db as db
import numpy as np



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
    return metrics, plots, stats


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
    blocks =[]
    




env = Environment(loader=FileSystemLoader('templates'))
outDir = 'Allslicers'
class MetricGridPageHandler(web.RequestHandler):
    def get(self):
        gridTempl = env.get_template("allOut.html")
        qargs = self.request.query_arguments
        import pdb ; pdb.set_trace()
        self.write(gridTempl.render(metrics=qargs))

class SelectPageHandler(web.RequestHandler):
    def get(self):
        """Load up the files and display """
        metrics, plots, stats = loadResults(outDir)
        
        mainTempl = env.get_template("allOut.html")
        blocks = blockAll(metrics, plots, stats)
        
        self.write(mainTempl.render(metrics=blocks, outDir=outDir))

application = web.Application([
    ("/metricResult", MetricGridPageHandler),
    ("/", SelectPageHandler),
    (r"/"+outDir+"/(.*)", web.StaticFileHandler, {'path':outDir}), 
    (r"/(favicon.ico)", web.StaticFileHandler, {'path':outDir}),
])

if __name__ == "__main__":
    application.listen(8888)
    ioloop.IOLoop.instance().start()
