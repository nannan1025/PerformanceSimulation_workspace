# Shared Mechanisms

This file contains only infrastructure, modeling patterns, and analysis logic shared by both requested processors. Processor-specific mechanisms remain in the CV32E40P and CVA6 reports.

## Common Infrastructure Shared By CV32E40P And CVA6

- CorePerfDSL descriptions live under `code_gen/descriptions/core_perf_dsl/`, not under `code_gen/core_perf_dsl/` in this workspace.
- Generated performance simulator code lives under `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/<processor>/`.
- Generated monitor code lives under `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/monitors/variants/<processor>/`.
- Shared backend APIs and base classes live under:
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/include/api/softwareEval-backends/`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/include/internal/`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/monitors/include/monitors/`
- Both generated performance models expose:
  - `connectChannel(Channel*)`
  - `getCycleCount()`
  - `getPipelineStream()`
  - `getPrintHeader()`

## Common Trace Analyzer Logic

- `README.md:39-45` documents running performance simulation and trace output with `./scripts/run.sh`.
- `README.md:53-59` documents code generation with `./scripts/code_gen.sh`.
- `scripts/trace_analyzer.sh:33-80` runs an external TraceAnalyzer using ISS trace, timing trace, optional pipeline trace, architecture name, and output directory.
- `scripts/trace_analyzer_summary.sh:7-60` extracts benchmark-level summary fields from `performance_report.txt`: instructions, observed cycles, ETISS cycles, CPI values, and cycle-count error.
- These scripts summarize whole-run performance and do not currently provide per-bottleneck attribution fields such as `stall_reason`, `blocking_resource`, or `blocking_instruction_id`.

## Common External Models

- `common::StandardRegisterModel` is shared by both processors:
  - Code: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/common/StandardRegisterModel.h:26-42`
  - Mechanism: maps `rs1` and `rs2` to readiness cycles through `getXa()` and `getXb()`, and updates destination readiness through `setXd()`.
  - Analysis category: RAW/data dependency.
  - Caveat: `StandardRegisterModel.h:35` notes a TODO for `rd = 0`.
- `common::StaticBranchPredictModel` is shared infrastructure but used by base `CV32E40P`, not by base `CVA6`:
  - Code: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/src/common/StaticBranchPredictModel.cpp:23-54`.
- Common branch/cache/no-branch memory headers exist under `externalModels/include/models/common/`; do not assume they are used by a processor unless included in that processor's generated `PerformanceModel.h` or CorePerfDSL.

## Common Bottleneck Categories

Use the same taxonomy for both processors:

- `frontend`: PC/fetch/queue bottlenecks.
- `branch`: prediction, redirect, and target availability bottlenecks.
- `data_dependency`: RAW/source readiness waits.
- `memory`: cache/memory/LSU/load-store port delays.
- `structural_resource`: capacity, subpipe, port, or shared resource conflicts.
- `functional_unit`: ALU/MUL/DIV/FPU unit latency.
- `writeback`: destination writeback port or result availability.
- `commit`: commit bandwidth or commit-dependent release.
- `other`: mechanisms that do not fit above.

## Code Locations Used By Both Processors

- `code_gen/descriptions/core_perf_dsl/`: CorePerfDSL source descriptions.
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CMakeLists.txt`: generated backend variant aggregation.
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/monitors/variants/CMakeLists.txt`: generated monitor variant aggregation.
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/common/StandardRegisterModel.h`: shared RAW readiness model.
- `scripts/code_gen.sh`: code generation wrapper.
- `scripts/run.sh`, `scripts/run2.sh`: simulation wrappers.
- `scripts/trace_analyzer.sh`, `scripts/trace_analyzer_summary.sh`: trace analysis wrappers.

## What Should Not Be Treated As Processor-Specific

- The `StandardRegisterModel` RAW readiness mechanism is shared. Processor-specific reports should describe how each pipeline uses it, but not claim the class itself is CV32E40P-only or CVA6-only.
- The trace analyzer scripts are shared and benchmark-level; they should not be interpreted as evidence that a specific bottleneck occurred.
- Generated base classes, channel/monitor/printer templates, and deployment scripts are shared infrastructure.
- Adjacent variants such as `CV32E40P_CORE`, `CV32E40P_LLM`, `CV32E40P_QWEN_1`, `CVA62`, and `CVA6_QWEN_1` should not be merged into the base `CV32E40P` or base `CVA6` reports unless explicitly selected. They are useful cross-checks but uncertain for the requested base processors.
- Runtime trace outputs in `trace_output/` or benchmark dumps should not be used to claim actual bottlenecks in Step 1.

## Missing Shared Analysis Logic

- No common per-instruction bottleneck attribution schema was found.
- No shared `stall_reason`, `blocking_resource`, `blocking_instruction_id`, or per-mechanism wait-cycle fields were found.
- Current summary script aggregates whole benchmark cycle/error fields, not bottleneck categories.
