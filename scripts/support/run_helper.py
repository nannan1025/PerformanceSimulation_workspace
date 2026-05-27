#!/usr/bin/env python3
import argparse
import os
import sys

# Read input arguments
argParser = argparse.ArgumentParser()
argParser.add_argument("targetSW", help="Target software handle (e.g.: dhry, em:cubic)")
argParser.add_argument("-c", "--core", help="Target core architecture [cv32e40p | cva6]")
args, args_passThrough = argParser.parse_known_args()

sim_args = ""
sim_args_rtl = ""
# Resolve CORE
if args.core is None:
   sys.exit("FATAL: Called support-script run_helper.py without specifying a core")
else:
   sim_args += " --core " + args.core

if args.core is None:
   sys.exit("FATAL: Called support-script run_helper.py without specifying a core")
elif args.core == "CVA62":
   sim_args_rtl += " --core cva6"
elif args.core == "CVA6_QWEN_1":
   sim_args_rtl += " --core cva6"
else:
   sim_args_rtl += " --core cv32e40p"

# Resolve TARGET_SW
targetSW_failed = False
targetSW_prefix = "PSW_TARGETSW_" + args.core.upper() + "_"
if len(split:=args.targetSW.split(":")) == 1:
   if split[0] == "dhry":
      targetSW = os.environ.get(targetSW_prefix + "DHRYSTONE_DEFAULT")
   else:
      targetSW_failed = True
elif len(split:=args.targetSW.split(":")) == 2:
   if split[0] == "em":
      targetSW = os.environ.get(targetSW_prefix + "EMBENCH") + "/" + split[1]
   elif split[0] == "dhry":
      targetSW = os.environ.get(targetSW_prefix + "DHRYSTONE_OFFSET") + "-" + split[1]
   else:
      targetSW_failed = True
else:
   targetSW_failed = True
   
if targetSW_failed:
   sys.exit("FATAL: Target-SW handle \"" + args.targetSW + "\" is not supported!")

# Resolve BOOTROM (if applicable)
if args.core == "cva6":
   sim_args += " --bootrom " + os.environ.get(targetSW_prefix + "BOOTROM")
   sim_args_rtl +=  " --bootrom " +  os.environ.get(targetSW_prefix + "BOOTROM")
if args.core == "CVA62":
   sim_args += " --bootrom " + os.environ.get(targetSW_prefix + "BOOTROM") 
   sim_args_rtl += " --bootrom " + os.environ.get("PSW_TARGETSW_CVA6_BOOTROM")
if args.core == "CVA6_QWEN_1":
   sim_args += " --bootrom " + os.environ.get(targetSW_prefix + "BOOTROM") 
   sim_args_rtl += " --bootrom " + os.environ.get("PSW_TARGETSW_CVA6_BOOTROM")
# Execute
simulator = os.environ.get("PSW_PERF_SIM")
exe = simulator + "/run_simulator.py " + targetSW + sim_args
for arg_i in args_passThrough:
   exe += " " + arg_i

os.system(exe)
# sim_args_rtl += " -m vrtl"
# sim_args_rtl += " -o /home/yang/program/project/Performance_Simulator_workspace_3/PerformanceSimulation_workspace/trace_output/"+args.core+ "/"+args.targetSW.split(":")[1]+"/rtl"  #TODO

# simulator_rtl = os.environ.get("PSW_FIVP_SIM")
# exe_rtl = os.environ.get("PSW_SCRIPTS_SUPPORT") + "/rtl_run_helper.py " + targetSW + " " + sim_args_rtl
# print(exe_rtl)
# os.system(exe_rtl)
