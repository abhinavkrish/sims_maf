#! /usr/bin/env python
import os, sys, argparse
import matplotlib
matplotlib.use('Agg') # May want to change in the future if we want to display plots on-screen

import lsst.sims.maf.driver as driver
from lsst.sims.maf.driver.mafConfig import MafConfig

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Python script to interpret MAF configuration files and feed them to the driver.')
    parser.add_argument("configFile", type=str, help="Name of the configuration file (a pex_config python script) ")
    parser.add_argument("--runName", type=str, default='', help='Root name of the sqlite dbfile (i.e. filename minus _sqlite.db). If provided, then configuration file is expected to contain a "mafconfig" method to define the configuration parameters. If not, then configuration file is expected to be a pex_config python script - a "one-off" configuration file, without this method.')
    parser.add_argument("--filepath", type=str, default='.', help='Directory containing the sqlite dbfile.')
    parser.add_argument("--outputDir", type=str, default='./Out', help='Output directory for MAF outputs.')
    parser.add_argument("--binnerName", type=str, default='HealpixBinner', help='BinnerName, for configuration methods that use this.')

    args = parser.parse_args()

    # Set up configuration parameters.
    config = MafConfig()
    if args.runName == '':
        config.load(args.configFile)
        print 'Finished loading config file: %s' %(args.configFile)
    else:
        # If a full pathname was specified to configFile, pull out the path and filename
        path, name = os.path.split(args.configFile)
        # And strip off an extension (.py, for example)
        name = os.path.splitext(name)[0]
        # Add the path to the configFile to the sys.path
        if len(path) > 0:
            sys.path.append(path)
        else:
            sys.path.append(os.getcwd())
        # Then import the module.
        conf = __import__(name)

        
        config = conf.mafconfig(config, runName=args.runName, dbFilepath=args.filepath, outputDir=args.outputDir, 
                                binnerName=args.binnerName)
        print 'Finished loading config from %s.mafconfig' %(args.configFile)

    # Run MAF driver.
    drive = driver.MafDriver(config)
    drive.run()
