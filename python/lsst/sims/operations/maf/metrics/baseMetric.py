# Base class for metrics - defines methods which must be implemented.
# If a metric calculates a vector or list at each gridpoint, then there
#  should be additional 'reduce_*' functions defined, to convert the vector
#  into scalar (and thus plottable) values at each gridpoint.
# The philosophy behind keeping the vector instead of the scalar at each gridpoint
#  is that these vectors may be expensive to compute; by keeping/writing the full
#  vector we permit multiple 'reduce' functions to be executed on the same data.
import numpy

# ClassRegistry adds some extras to a normal dictionary.
class ClassRegistry(dict):
    @staticmethod
    def makeColArr(cols):
        #Promote scalar to array.  Solution from:
        #http://stackoverflow.com/questions/12653120/how-can-i-make-a-numpy-function-that-accepts-a-numpy-array-an-iterable-or-a-sc
        return numpy.array(cols, copy=False, ndmin=1)

    # Contents of the dictionary look like {metricClassName: 'set' of [simData columns]}
    def __str__(self):
        # Print the contents of the registry nicely.
        retstr = "----------------------------\n"
        retstr += "Registry Contents\n"
        for k in self:
            retstr += "%s: %s\n"%(k, ",".join([str(el) for el in self[k]]))
        retstr += "-----------------------------\n"
        return retstr
    def __setitem__(self, i, y):
        if not hasattr(y, '__iter__'):
            raise TypeError("Can only contain iterable types")
        super(ClassRegistry, self).__setitem__(i,y)
    def uniqueCols(self):
        colset = set()
        for k in self.keys():
            for col in self[k]:
                colset.add(col)
        return colset    
    

class BaseMetric(object):
    """Base class for the metrics."""
    # Add ClassRegistry to keep track of columns needed for metrics. 
    classRegistry = ClassRegistry()
    
    def __init__(self, cols, metricName=None, *args, **kwargs):
        """Instantiate metric. """
        # Turn cols 
        self.colNameList = ClassRegistry.makeColArr(cols)
        # Register the columns in the classRegistry.
        self.registerCols(self.colNameList)
        # Save a name for the metric + the data it's working on, so we
        #  can identify this later.
        # If passed the value:
        if metricName:
            self.name = metricName
        else:
            # Else construct our own name from the class name and the data columns.
            self.name = self.__class__.__name__.rstrip('Metric') + '_' + self.colNameList[0]

    def registerCols(self, cols):
        """Add cols to the column registry. """
        # Set myName to be name of the metric class.
        myName = self.__class__.__name__
        if myName not in self.classRegistry:
            #Add a set to the registry if the key doesn't exist.
            self.classRegistry[myName] = set()
        # Add the columns to the registry.
        for col in cols:
            self.classRegistry[myName].add(col)

    def validateData(self, simData):
        """Check that simData has necessary columns for this particular metric."""
        ## Note that we can also use the class registry to find the list of all columns.
        for col in self.colNameList:
            try:
                simData[col]
            except KeyError:
                raise KeyError('Could not find data column for metric: %s' %(col))
    
    def run(self, dataSlice):
        raise NotImplementedError('Please implement your metric calculation.')
