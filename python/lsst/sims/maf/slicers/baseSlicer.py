# Base class for all 'Slicer' objects.
#

import os
import inspect
from StringIO import StringIO
import json
import warnings
import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt
from lsst.sims.maf.utils import getDateVersion

__all__ = ['SlicerRegistry', 'BaseSlicer']

class SlicerRegistry(type):
    """
    Meta class for slicers, to build a registry of slicer classes.
    """
    def __init__(cls, name, bases, dict):
        super(SlicerRegistry, cls).__init__(name, bases, dict)
        if not hasattr(cls, 'registry'):
            cls.registry = {}
        modname = inspect.getmodule(cls).__name__ + '.'
        if modname.startswith('lsst.sims.maf.slicers'):
            modname = ''
        slicername = modname + name
        if slicername in cls.registry:
            raise Exception('Redefining metric %s! (there are >1 slicers with the same name)' %(slicername))
        if slicername not in ['BaseSlicer', 'BaseSpatialSlicer']:
            cls.registry[slicername] = cls
    def getClass(cls, slicername):
        return cls.registry[slicername]
    def list(cls, doc=False):
        for slicername in sorted(cls.registry):
            if not doc:
                print slicername
            if doc:
                print '---- ', slicername, ' ----'
                print inspect.getdoc(cls.registry[slicername])



class BaseSlicer(object):
    """
    Base class for all slicers: sets required methods and implements common functionality.
    """
    __metaclass__ = SlicerRegistry

    def __init__(self, verbose=True, badval=-666, plotFuncs='all'):
        """
        Instantiate the base slicer object.

        After first init with a 'blank' slicer: slicer should be ready for setupSlicer to
        define slicePoints.
        After init after a restore: everything necessary for using slicer for plotting or
        saving/restoring metric data should be present (although slicer does not need to be able to
        slice data again and generally will not be able to).

        The sliceMetric has a 'memo-ize' functionality that can save previous indexes & return
        metric data value calculated for same set of previous indexes, if desired.
        CacheSize = 0 effectively turns this off, otherwise cacheSize should be set by the slicer.
        (Most useful for healpix slicer, where many healpixels may have same set of LSST visits).

        Minimum set of __init__ kwargs:
        verbose: True/False flag to send extra output to screen
        badval: the value the Slicer uses to fill masked metric data values
        plotFuncs:  default value of 'all' means the slicer will use all methods that start with 'plot'
                    to generate plots.  Could be a string or list specifying specific methods that should
                    be called when plotting.
        """
        self.verbose = verbose
        self.badval = badval
        # Set cacheSize : each slicer will be able to override if appropriate.
        # Currently only the healpixSlice actually uses the cache: this is set in 'useCache' flag.
        #  If other slicers have the ability to use the cache, they should add this flag and set the
        #  cacheSize in their __init__ methods.
        self.cacheSize = 0
        # Set length of Slicer.
        self.nslice = None
        self.slicePoints = {}
        self.slicerName = self.__class__.__name__
        self.columnsNeeded = []
        # Set if the slicer should try to plot objects
        self.plotObject = False
        # Add dictionary of plotting methods for each slicer.
        self.plotFuncs = {}
        plotNames=[]
        if plotFuncs is not None:
            # Add every method that starts with 'plot'
            for  p in inspect.getmembers(self, predicate=inspect.ismethod):
                if p[0].startswith('plot'):
                    self.plotFuncs[p[0]] = p[1]
                    plotNames.append(p[0])
            # Remove plotData method if it exists
            if 'plotData' in self.plotFuncs.keys():
                del self.plotFuncs['plotData']
            # If the plotFuncs kwarg is set, only include those plotting methods
            if (plotFuncs != 'all') & (plotFuncs is not None):
                for key in self.plotFuncs.keys():
                    if key not in plotFuncs:
                        del self.plotFuncs[key]
        # Raise warning if plotFuncs was specified but didn't match anything
        if (plotFuncs != 'all') & (plotFuncs is not None) & (len(self.plotFuncs) == 0):
            warnings.warn('No plotting method matched %s.  Options are: %s'%(plotFuncs,plotNames))

      # Create a dict that saves how to re-init the slicer.
        #  This may not be the whole set of args/kwargs, but those which carry useful metadata or
        #   are absolutely necesary for init.
        # Will often be overwritten by individual slicer slicer_init dictionaries.
        self.slicer_init = {'badval':badval,'plotFuncs':plotFuncs }

    def _runMaps(self, maps):
        """
        Add map metadata to slicePoints.
        """
        if maps is not None:
            for m in maps:
                self.slicePoints = m.run(self.slicePoints)

    def setupSlicer(self, simData, maps=None):
        """
        Set up Slicer for data slicing.

        Set up internal parameters necessary for slicer to slice data and generates indexes on simData.
        Also sets _sliceSimData for a particular slicer.
        """
        # Typically args will be simData, but opsimFieldSlicer also uses fieldData.
        raise NotImplementedError()


    def getSlicePoints(self):
        """
        Return the slicePoint metadata, for all slice points.
        """
        return self.slicePoints

    def __len__(self):
        """
        Return nslice, the number of slicePoints in the slicer.
        """
        return self.nslice

    def __iter__(self):
        """Iterate over the slices.
        """
        self.islice = 0
        return self

    def next(self):
        """
        Returns results of self._sliceSimData when iterating over slicer.

        Results of self._sliceSimData should be dictionary of
           {'idxs' - the data indexes relevant for this slice of the slicer,
           'slicePoint' - the metadata for the slicePoint .. always includes ['sid'] key for ID of slicePoint.}
        """
        if self.islice >= self.nslice:
            raise StopIteration
        islice = self.islice
        self.islice += 1
        return self._sliceSimData(islice)

    def __getitem__(self, islice):
        return self._sliceSimData(islice)

    def __eq__(self, otherSlicer):
        """Evaluate if two slicers are equivalent."""
        raise NotImplementedError()

    def _sliceSimData(self, slicePoint):
        """
        Slice the simulation data appropriately for the slicer.

        Given the identifying slicePoint metadata
        The slice of data returned will be the indices of the numpy rec array (the simData)
        which are appropriate for the metric to be working on, for that slicePoint.
        """
        raise NotImplementedError('This method is set up by "setupSlicer" - run that first.')

    def writeData(self, outfilename, metricValues, metricName='',
                  simDataName ='', sqlconstraint='', metadata='', plotDict=None, displayDict=None):
        """
        Save metric values along with the information required to re-build the slicer.

        outfilename: the output file
        metricValues: the metric values to save to disk
        """
        header = {}
        header['metricName']=metricName
        header['sqlconstraint'] = sqlconstraint
        header['metadata'] = metadata
        header['simDataName'] = simDataName
        date, versionInfo = getDateVersion()
        header['dateRan'] = date
        if displayDict is None:
            displayDict = {'group':'Ungrouped'}
        header['displayDict'] = displayDict
        header['plotDict'] = plotDict
        for key in versionInfo.keys():
            header[key] = versionInfo[key]
        if hasattr(metricValues, 'mask'): # If it is a masked array
            data = metricValues.data
            mask = metricValues.mask
            fill = metricValues.fill_value
        else:
            data = metricValues
            mask = None
            fill = None
        # npz file acts like dictionary: each keyword/value pair below acts as a dictionary in loaded NPZ file.
        np.savez(outfilename,
                 header = header, # header saved as dictionary
                 metricValues = data, # metric data values
                 mask = mask, # metric mask values
                 fill = fill, # metric badval/fill val
                 slicer_init = self.slicer_init, # dictionary of instantiation parameters
                 slicerName = self.slicerName, # class name
                 slicePoints = self.slicePoints, # slicePoint metadata saved (is a dictionary)
                 slicerNSlice = self.nslice)

    def outputJSON(self, metricValues, metricName='',
                  simDataName ='', metadata='', plotDict=None):
        """
        Send metric data to JSON streaming API, along with a little bit of metadata.

        Output is
           header dictionary with 'metricName/metadata/simDataName/slicerName' and plot labels from plotDict (if provided).
           then data for plot:
             if oneDSlicer, it's [ [bin_left_edge, value], [bin_left_edge, value]..].
             if a spatial slicer, it's [ [lon, lat, value], [lon, lat, value] ..].
        This method will only work for non-complex metrics (i.e. metrics where the metric value is a float or int),
        as JSON will not interpret more complex data properly. These values can't be plotted anyway though.
        """
        # Bail if this is not a good data type for JSON.
        if not (metricValues.dtype == 'float') or (metricValues.dtype == 'int'):
            warnings.warn('Cannot generate JSON.')
            io = StringIO()
            json.dump(['Cannot generate JSON for this file.'], io)
            return None
        # Else put everything together for JSON output.
        if plotDict is None:
            plotDict = {}
            plotDict['units'] = ''
        # Preserve some of the metadata for the plot.
        header = {}
        header['metricName'] = metricName
        header['metadata'] = metadata
        header['simDataName'] = simDataName
        header['slicerName'] = self.slicerName
        header['slicerLen'] = int(self.nslice)
        # Set some default plot labels if appropriate.
        if 'title' in plotDict:
            header['title'] = plotDict['title']
        else:
            header['title'] = '%s %s: %s' %(simDataName, metadata, metricName)
        if 'xlabel' in plotDict:
            header['xlabel'] = plotDict['xlabel']
        else:
            if hasattr(self, 'sliceColName'):
                header['xlabel'] = '%s (%s)' %(self.sliceColName, self.sliceColUnits)
            else:
                header['xlabel'] = '%s' %(metricName)
                if 'units' in plotDict:
                    header['xlabel'] += ' (%s)' %(plotDict['units'])
        if 'ylabel' in plotDict:
            header['ylabel'] = plotDict['ylabel']
        else:
            if hasattr(self, 'sliceColName'):
                header['ylabel'] = '%s' %(metricName)
                if 'units' in plotDict:
                    header['ylabel'] += ' (%s)' %(plotDict['units'])
            else:
                # If it's not a oneDslicer and no ylabel given, don't need one.
                pass
        # Bundle up slicer and metric info.
        metric = []
        # If metric values is a masked array.
        if hasattr(metricValues, 'mask'):
            if 'ra' in self.slicePoints:
                # Spatial slicer. Translate ra/dec to lon/lat in degrees and output with metric value.
                for ra, dec, value, mask in zip(self.slicePoints['ra'], self.slicePoints['dec'],
                                                metricValues.data, metricValues.mask):
                    if not mask:
                        lon = ra * 180.0/np.pi
                        lat = dec * 180.0/np.pi
                        metric.append([lon, lat, value])
            elif 'bins' in self.slicePoints:
                # OneD slicer. Translate bins into bin/left and output with metric value.
                for i in range(len(metricValues)):
                    binleft = self.slicePoints['bins'][i]
                    value = metricValues.data[i]
                    mask = metricValues.mask[i]
                    if not mask:
                        metric.append([binleft, value])
                    else:
                        metric.append([binleft, 0])
                metric.append([self.slicePoints['bins'][i+1], 0])
            elif self.slicerName == 'UniSlicer':
                metric.append([metricValues[0]])
        # Else:
        else:
            if 'ra' in self.slicePoints:
                for ra, dec, value in zip(self.slicePoints['ra'], self.slicePoints['dec'], metricValues):
                        lon = ra * 180.0/np.pi
                        lat = dec * 180.0/np.pi
                        metric.append([lon, lat, value])
            elif 'bins' in self.slicePoints:
                for i in range(len(metricValues)):
                    binleft = self.slicePoints['bins'][i]
                    value = metricValues[i]
                    metric.append([binleft, value])
                metric.append(self.slicePoints['bins'][i+1][0])
            elif self.slicerName == 'UniSlicer':
                metric.append([metricValues[0]])
        # Write out JSON output.
        io = StringIO()
        json.dump([header, metric], io)
        return io

    def readData(self, infilename):
        """
        Read metric data from disk, along with the info to rebuild the slicer (minus new slicing capability).

        infilename: the filename containing the metric data.
        """
        import lsst.sims.maf.slicers as slicers
        restored = np.load(infilename)
        # Get metric data set
        if restored['mask'][()] is None:
            metricValues = ma.MaskedArray(data=restored['metricValues'])
        else:
            metricValues = ma.MaskedArray(data=restored['metricValues'],
                                          mask=restored['mask'],
                                          fill_value=restored['fill'])
        # Get Metadata & other simData info.
        header = restored['header'][()]  # extra brackets restore dictionary to dictionary status.
        # Get slicer instantiated.
        slicer_init = restored['slicer_init'][()]
        # Backwards compatibility issue - map 'spatialkey1/spatialkey2' to 'lonCol/latCol'.
        if 'spatialkey1' in slicer_init:
            slicer_init['lonCol'] = slicer_init['spatialkey1']
            del(slicer_init['spatialkey1'])
        if 'spatialkey2' in slicer_init:
            slicer_init['latCol'] = slicer_init['spatialkey2']
            del(slicer_init['spatialkey2'])
        slicer = getattr(slicers, str(restored['slicerName']))(**slicer_init)
        # Restore slicePoint metadata.
        slicer.nslice = restored['slicerNSlice']
        slicer.slicePoints = restored['slicePoints'][()]
        return metricValues, slicer, header

    def plotData(self, metricValues, figformat='pdf', dpi=600, filename='fig',
                 savefig=True, thumbnail=True, plotFunc=None, **kwargs):
        """
        Call all available plotting methods.

        The __init__ for each slicer builds a dictionary of the individual slicer's plotting methods.
        This method calls each of the plotting methods in that dictionary, and optionally
        saves the resulting figures.

        metricValues: the metric values to plot.
        """
        # If passed metric data which is not a simple data type, return without plotting.
        # (thus - override this method if your slicer requires plotting complex 'object' data.
        filenames=[]
        filetypes=[]
        figs={}
        if not self.plotObject:
            if not (metricValues.dtype == 'float') or (metricValues.dtype == 'int'):
                warnings.warn('Metric data type not float or int. No plots generated.')
                return {'figs':figs, 'filenames':filenames, 'filetypes':filetypes}
        # Otherwise, plot.
        if plotFunc is not None:
            if plotFunc in self.plotFuncs:
                plotFuncs = {plotFunc:self.plotFuncs[plotFunc]}
            else:
                raise ValueError('plotFunc specified as %s, but not a slicer method.' %(plotFunc))
        else:
            plotFuncs = self.plotFuncs
        for p in plotFuncs:
            plottype = p.replace('plot', '')
            figs[plottype] = self.plotFuncs[p](metricValues, **kwargs)
            if savefig:
                outfile = filename + '_' + plottype + '.' + figformat
                plt.savefig(outfile, figformat=figformat, dpi=dpi)
                if thumbnail:
                    filepath, thumbname = os.path.split(outfile)
                    thumbname = ''.join(thumbname.split('.')[:-1])
                    thumbname = 'thumb.' + thumbname + '.png'
                    thumbfile = os.path.join(filepath, thumbname)
                    plt.savefig(thumbfile, dpi=72)
                filenames.append(outfile)
                filetypes.append(plottype)
            else:
                filenames.append('NULL')
                filetypes.append('NULL')
        return {'figs':figs, 'filenames':filenames, 'filetypes':filetypes}
