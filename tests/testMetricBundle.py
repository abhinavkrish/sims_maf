import unittest
import matplotlib
matplotlib.use("Agg")

import lsst.sims.maf.metrics as metrics
import lsst.sims.maf.slicers as slicers
import lsst.sims.maf.metricBundles as metricBundles
import lsst.sims.maf.db as db
import glob
import os
import shutil
import lsst.utils.tests


class TestMetricBundle(unittest.TestCase):

    def setUp(self):
        self.outDir = 'TMB'

    def testOut(self):
        """
        Check that the metric bundle can generate the expected output
        """
        slicer = slicers.HealpixSlicer(nside=8)
        metric = metrics.MeanMetric(col='airmass')
        sql = 'filter="r"'

        metricB = metricBundles.MetricBundle(metric, slicer, sql)
        filepath = os.path.join(os.getenv('SIMS_MAF_DIR'), 'tests/pontus_1074.db')

        database = os.path.join(filepath, '')
        opsdb = db.OpsimDatabase(database=database)
        resultsDb = db.ResultsDb(outDir=self.outDir)

        bgroup = metricBundles.MetricBundleGroup({0: metricB}, opsdb, outDir=self.outDir, resultsDb=resultsDb)
        bgroup.runAll()
        bgroup.plotAll()
        bgroup.writeAll()

        outThumbs = glob.glob(os.path.join(self.outDir, 'thumb*'))
        outNpz = glob.glob(os.path.join(self.outDir, '*.npz'))
        outPdf = glob.glob(os.path.join(self.outDir, '*.pdf'))

        # By default, make 3 plots for healpix
        assert(len(outThumbs) == 3)
        assert(len(outPdf) == 3)
        assert(len(outNpz) == 1)

    def tearDown(self):
        if os.path.isdir(self.outDir):
            shutil.rmtree(self.outDir)


class TestMemory(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()
