#!/usr/bin/env python3

import argparse
import os
import pathlib
import sys
import time

# Read input arguments
argParser = argparse.ArgumentParser()
argParser.add_argument("targetSW", help="Path to target software ELF file")
argParser.add_argument("-boot", "--bootrom", help="Path to bootrom ELF file")
argParser.add_argument("-c", "--core", help="Simulated core. [cv32e40p | cva6]")
argParser.add_argument("-m", "--mode", help="Mode of the simulation. [vrtl | etiss]")
argParser.add_argument("-o", "--out", help="Path to out directory")
args = argParser.parse_args()

# Check input arguments
if args.core is None:
    sys.exit("FATAL: Called FIVP run_helper.py without specifying a core")
core = args.core

if args.mode is None:
    print("INFO: Called FIVP run_helper without specifyin a mode. Use vrtl as default!")
    mode = "vrtl"
else:
    mode = args.mode

if args.out is None:
    outDir = os.getcwd()
else:
    outDir = str(pathlib.Path(args.out).resolve())
    
# Resolve pathes
# vpDir = str(pathlib.Path(__file__).resolve().parent / "fivp")
vpDir = "/home/yang/program/project/Performance_Estimator_workspace_2/PerformanceEstimator_workspace/simulators/fivp/fivp"
iniDir = vpDir + "/ini/" + core
targetSW = str(pathlib.Path(args.targetSW).resolve())
print("targetSW path:", targetSW)
# exit()

# Set arguments for exe call
vp_args = " --vp " + iniDir + "/vp.ini"
vp_args += " --etiss " + iniDir + "/etiss.ini"
vp_args += " --elfs '" + targetSW
if args.bootrom is not None:
    vp_args += "," + str(pathlib.Path(args.bootrom).resolve())
vp_args += "'"
vp_args += " --pf " + iniDir + "/vrtl.ini"
vp_args += " --out " + outDir

# Execute VP
vp_exe = vpDir + "/build/build_" + core + "_" + mode + "/fivp-" + core + "-" + mode
startTime = time.time()
os.system(vp_exe + vp_args)
endTime = time.time()
print("")
print("Total execution time: " + str(float(endTime - startTime)) + "s")
