from .baseStacker import BaseStacker

__all__ = ['ColInfo']

class ColInfo(object):
    def __init__(self):
        """Set up the unit and source dictionaries.
        """
        self.defaultDataSource = None
        self.defaultUnit = ''
        self.unitDict = {'fieldId': '#',
                         'filter': 'filter',
                         'seqnNum' : '#',
                         'observationStartMJD': 'MJD',
                         'observationStartLST': 'deg',
                         'visitExposureTime': 's',
                         'slewTime': 's',
                         'slewDist': 'rad',
                         'rotSkyPos': 'deg',
                         'rotTelPos': 'deg',
                         'rawSeeing': 'arcsec',
                         'finSeeing': 'arcsec',
                         'seeingFwhmEff': 'arcsec',
                         'seeingFwhmGeom': 'arcsec',
                         'seeingFwhm500': 'arcsec',
                         'seeing': 'arcsec',
                         'airmass': 'X',
                         'night': 'days',
                         'moonRA': 'rad',
                         'moonDec': 'rad',
                         'moonAlt': 'rad',
                         'dist2Moon': 'rad',
                         'filtSkyBrightness': 'mag/sq arcsec',
                         'skyBrightness': 'mag/sq arcsec',
                         'fiveSigmaDepth':'mag',
                         'solarElong': 'degrees'}
        # Go through the available stackers and add any units, and identify their
        #   source methods.
        self.sourceDict = {}
        for stackerClass in BaseStacker.registry.itervalues():
            stacker = stackerClass()
            for col, units in zip(stacker.colsAdded, stacker.units):
                self.sourceDict[col] = stackerClass
                self.unitDict[col] = units
        # Note that a 'unique' list of methods should be built from the resulting returned
        #  methods, at whatever point the derived data columns will be calculated. (i.e. in the driver)

    def getUnits(self, colName):
        """Return the appropriate units for colName.
        """
        if colName in self.unitDict:
            return self.unitDict[colName]
        else:
            return self.defaultUnit

    def getDataSource(self, colName):
        """
        Given a column name to be added to simdata, identify appropriate source.

        For values which are calculated via a stacker, the returned value is the stacker class.
        For values which do not have a recorded source or are known to be coming from the database, the result
        is self.defaultDataSource.
        """
        if colName in self.sourceDict:
            return self.sourceDict[colName]
        else:
            return self.defaultDataSource
