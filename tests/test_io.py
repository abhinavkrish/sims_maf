import numpy as np
import numpy.ma as ma
import unittest
#from lsst.sims.maf.metrics import SimpleMetrics as sm
import lsst.sims.maf.binners as binners
import healpy as hp
import os


class TestBinners(unittest.TestCase):
    def setUp(self):
        self.filenames=[]

    def test_healpixBinner_obj(self):
        nside = 128
        binner = binners.HealpixBinner(nside=nside)
        metricValues = np.random.rand(hp.nside2npix(nside)).astype('object')
        metricValues = ma.MaskedArray(data=metricValues, mask = np.where(metricValues < .1, True, False), fill_value=binner.badval)
        metricName = 'Noise'
        filename = 'healpix_test.npz'
        self.filenames.append(filename)
        metadata = 'poop'
        binner.writeData(filename, metricValues, metadata=metadata)
        metricValuesBack,binnerBack,header = binner.readData(filename)
        np.testing.assert_almost_equal(metricValuesBack,metricValues)
        assert(binner == binnerBack) 
        assert(metadata == header['metadata'])
        attr2check = ['nside', 'nbins', 'columnsNeeded', 'bins', 'spatialkey1', 'spatialkey2']
        for att in attr2check:
            assert(getattr(binner,att) == getattr(binnerBack,att))
        
    def test_healpixBinner_floats(self):
        nside = 128
        binner = binners.HealpixBinner(nside=nside)
        metricValues = np.random.rand(hp.nside2npix(nside))
        metricName = 'Noise'
        filename = 'healpix_test.npz'
        self.filenames.append(filename)
        binner.writeData(filename, metricValues, metadata='poop')
        metricValuesBack,binnerBack,header = binner.readData(filename)
        np.testing.assert_almost_equal(metricValuesBack,metricValues)
        assert(binner == binnerBack) #I don't think this is the right way to compare
        attr2check = ['nside', 'nbins', 'columnsNeeded', 'bins', 'spatialkey1', 'spatialkey2']
        for att in attr2check:
            assert(getattr(binner,att) == getattr(binnerBack,att))
       
        
    def test_healpixBinner_masked(self):
        nside = 128
        binner = binners.HealpixBinner(nside=nside)
        metricValues = np.random.rand(hp.nside2npix(nside))
        metricValues = ma.MaskedArray(data=metricValues, mask = np.where(metricValues < .1, True, False), fill_value=binner.badval)
        metricName = 'Noise'
        filename = 'healpix_test.npz'
        self.filenames.append(filename)
        binner.writeData(filename, metricValues, metadata='poop')
        metricValuesBack,binnerBack,header = binner.readData(filename)

        np.testing.assert_almost_equal(metricValuesBack,metricValues)
        assert(binner == binnerBack) #I don't think this is the right way to compare
        attr2check = ['nside', 'nbins', 'columnsNeeded', 'bins', 'spatialkey1', 'spatialkey2']
        for att in attr2check:
            assert(getattr(binner,att) == getattr(binnerBack,att))


    def test_oneDBinner(self):
        binner=binners.OneDBinner(sliceDataColName='poop')
        dataValues = np.zeros(10000, dtype=[('poop','float')])
        dataValues['poop'] = np.random.rand(10000)
        binner.setupBinner(dataValues)
        filename = 'oned_test.npz'
        self.filenames.append(filename)
        binner.writeData(filename, dataValues[:100])

        dataBack,binnerBack,header = binner.readData(filename)
        assert(binner == binnerBack)
        assert(np.all(binner.bins == binnerBack.bins))
        #np.testing.assert_almost_equal(dataBack,dataValues[:100])
        attr2check = ['nbins', 'columnsNeeded', 'bins']
        for att in attr2check:
            if type(getattr(binner,att)).__module__ == 'numpy':
                np.testing.assert_almost_equal(getattr(binner,att), getattr(binnerBack,att))
            else:
                assert(getattr(binner,att) == getattr(binnerBack,att))

    def test_opsimFieldBinner(self):
        binner=binners.OpsimFieldBinner(np.arange(100))
        names=['fieldRA','fieldDec','fieldID',]
        dt = ['float','float','int']
        metricValues = np.random.rand(100)
        fieldData = np.zeros(100, dtype=zip(names,dt))
        fieldData['fieldRA'] = np.random.rand(100)
        fieldData['fieldDec'] = np.random.rand(100)
        fieldData['fieldID'] = np.arange(100)
        names=['data1','data2','fieldID',]
        simData = np.zeros(100, dtype=zip(names,dt))
        simData['data1'] = np.random.rand(100)
        simData['fieldID'] = np.arange(100)
        binner.setupBinner(simData,fieldData)
        filename = 'opsimbinner_test.npz'
        self.filenames.append(filename)
        binner.writeData(filename, metricValues)
        metricBack, binnerBack,header = binner.readData(filename)
        assert(binner == binnerBack)
        np.testing.assert_almost_equal(metricBack,metricValues)
        attr2check = ['nbins', 'columnsNeeded', 'bins', 'spatialkey1', 'spatialkey2','simDataFieldIdColName']
        for att in attr2check:
            if type(getattr(binner,att)).__name__ == 'dict':
                for key in getattr(binner,att).keys():
                    np.testing.assert_almost_equal(getattr(binner,att)[key], getattr(binnerBack,att)[key])
            else:
                assert(getattr(binner,att) == getattr(binnerBack,att))

    def test_unibinner(self):
        binner = binners.UniBinner()
        data = np.zeros(1, dtype=[('poop','float')])
        data[:] = np.random.rand(1)
        binner.setupBinner(data)
        filename='unibinner_test.npz'
        self.filenames.append(filename)
        metricValue=np.array([25.])
        binner.writeData(filename, metricValue)
        dataBack, binnerBack,header = binner.readData(filename)
        assert(binner == binnerBack)
        np.testing.assert_almost_equal(dataBack,metricValue)
        attr2check = ['nbins', 'columnsNeeded', 'bins']
        for att in attr2check:
            assert(getattr(binner,att) == getattr(binnerBack,att))


    def test_complex(self):
        """Test case where there is a complex metric """
        nside = 32
        binner = binners.HealpixBinner(nside=nside)
        data = np.zeros(binner.nbins, dtype='object')
        for i,ack in enumerate(data):
            n_el = np.random.rand(1)*4 # up to 4 elements
            data[i] = np.arange(n_el)
        filename = 'heal_complex.npz'
        self.filenames.append(filename)
        binner.writeData(filename,data)
        dataBack,binnerBack,header = binner.readData(filename)
        assert(binner == binnerBack)
        # This is a crazy slow loop!  
        for i, ack in enumerate(data):
            np.testing.assert_almost_equal(dataBack[i],data[i])
        
#    def test_nDBinner(self):
#        colnames = ['ack1','ack2','poop']
#        types = ['float','float','int']
#        data = np.zeros(1000, dtype=zip(colnames,types))
#        binner = binners.NDBinner()
#        binner.setupBinner([data['ack1'], data['ack2'], data['poop']])
#        filename = 'nDBInner_test.npz'
#        binner.writeData(filename,data)
#        dataBack,binnerBack,header = binner.readData(filename)
#        assert(binner == binnerBack)
#        np.testing.assert_almost_equal(dataBack,data)
       

    def tearDown(self):
        for filename in self.filenames:
            os.remove(filename)
    
if __name__ == '__main__':
    unittest.main()
 
