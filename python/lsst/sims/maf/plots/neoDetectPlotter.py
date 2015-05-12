import numpy as np
import matplotlib.pyplot as plt
from .plotHandler import BasePlotter


__all__ = ['NeoDetectPlotter']

class NeoDetectPlotter(BasePlotter):
    def __init__(self):

        self.plotType = 'neoxyPlotter'
        self.objectPlotter = True
        self.defaultPlotDict = {'title':None, 'xlabel':'X (AU)',
                                'ylabel':'Y (AU)'}
        self.filter2color={'u':'purple','g':'blue','r':'green',
                           'i':'cyan','z':'orange','y':'red'}
        self.filterColName = 'filter'

    def __call__(self, metricValue, slicer,userPlotDict, fignum=None):

        fig = plt.figure(fignum)
        ax = fig.add_subplot(111)

        plotDict = {}
        plotDict.update(self.defaultPlotDict)
        plotDict.update(userPlotDict)

        for filterName in self.filter2color:
            good = np.where(metricValue[0].data[self.filterColName] == filterName)
            if np.size(good[0]) > 0:
                ax.plot( metricValue[0].data['NEOX'], metricValue[0].data['NEOY'], 'o',
                            color=self.filter2color[filterName], alpha=0.1, markeredgecolor=None)

        ax.set_xlabel(plotDict['xlabel'])
        ax.set_ylabel(plotDict['ylabel'])
        ax.set_title(plotDict['title'])

        ax.plot([0],[0],marker='o', color='b')
        ax.plot([0],[-1], marker='o', color='y')


        return fig.number
