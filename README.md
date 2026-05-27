# PerformanceSimulation_workspace
Example workspace for software performance simulation with ETISS-based performance simulator (WiP!)

## Overview
This is an example workspace for the ETISS-based performance simulator. It contains:
- The ETISS-based performance simulator etiss-perf-sim
- The M2-ISA-R-Perf code generator to adjust the performance models
- The Embench benchmark suite, compiled for the CV32E40P (RV32IM) and CVA6 (RV64IM), as a target-software example

## First Time Setup

### Create workspace

Clone this repository and navigate to its top folder. (The given example uses an SSH-based link; adapt if necessary)

      $ git clone git@github.com:tum-ei-eda/PerformanceSimulation_workspace.git <YOUR_WORKSPACE_NAME>
      $ cd <YOUR_WORKSPACE_NAME>

Switch to the latest release version:

      $ git fetch --tags
      $ git checkout tags/v0.2

Initialize required git-submodules:

      $ git submodule update --init --recursive

### Install workspace

Install the workspace by calling:

      $ ./scripts/setup_workspace.sh


## Usage

### Performance Simulation

Example: Run a performance simulation for the embench-crc32 benchmark on the CV32E40P:

      $ ./scripts/run.sh em:crc32 cv32e40p

Example: Run a performance simulation for the embench-ud benchmark on the CVA6 and create a performance-trace:

      $ ./scripts/run.sh em:ud cva6 -tp=<YOUR/TRACE/PATH>

Example: Run an instruction simulation (without performance estimation) for the embench-crc32 benchmark on the CV32E40P:

      $ ./scripts/run.sh em:crc32 cv32e40p -np

### Code Generation

Example: Generate performance estimator from corePerfDsl description, deploy it and re-install ETISS:

      $ ./scripts/code_gen.sh ./code_gen/descriptions/core_perf_dsl/CV32E40P.corePerfDsl

Example: Generate trace printer from monitor description, deploy it and re-install ETISS:

      $ ./scripts/code_gen.sh ./code_gen/descriptions/monitor_descriptions/InstructionTrace_RV64.json

## Version

The latest release version of this repository is v0.2

It is compatible with the following submodule versions:

| Submodule | Version |
| --------- | ------- |
| etiss-perf-sim | v0.10 |
| M2-ISA-R | WiP |
| M2-ISA-R-Perf | v2.0 |
| etiss_arch_riscv | WiP |
| CorePerfDSL-Examples | v2.0 |

## Support Rocket/CV32E40P_LLM/CVA6_LLM
1. Code Generation

      $./scripts/code_gen.sh New_Core_Path/new_core.corePerfDsl

2. Performance Simulation
   
If the core is simple scalar core, like CV32E40P, can use this to set up some configuration. But if the core is superscalar core like CVA6, needs bootroom or others, also can use this scripts, but needs change a little bit.

      $./scripts/sim_gen_simple.sh ROCKET RV64IMACFD    

Run EM benchmark

      $./scripts/runbencha_trace.sh CV32E40P_LLM CV32E40P

the first parameter is the new core, the second parameter is the baseline core(run rtl)

3. Trace Anlayzer

      $./scripts/trace_analyzer.sh CV32E40P_LLM CV32E40P
   

      $./scripts/trace_analyzer_summary.sh CV32E40P_LLM
