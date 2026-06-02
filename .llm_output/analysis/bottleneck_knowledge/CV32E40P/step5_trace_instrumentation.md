# CV32E40P Step 5 Trace Instrumentation: Memory-Port / LSU Structural Wait

## Summary

Implemented Step 5 memory-port / LSU structural wait instrumentation for the base CV32E40P backend timing trace.

This step does not add cache hit/miss modeling. CV32E40P is treated here as using the existing generated LSU/DPort schedule only. The new trace fields expose modeled structural wait caused by the existing `WB_stage` serialization before DPort read/write access.

## Files Modified

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/include/CV32E40P_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_PerformanceModel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_SchedulingFunction.cpp`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step5_trace_instrumentation.md`

No `CV32E40P_CORE`, `CV32E40P_LLM`, `CV32E40P_QWEN_1`, cache model, monitor, or external model files were modified for this step.

## Functions Modified

- `CV32E40P_PerformanceModel::getPrintHeader`
- `CV32E40P_PerformanceModel::getPipelineStream`
- `CV32E40P_PerformanceModel::setMemoryPortInstrumentation`
- CV32E40P scheduling lambdas for:
  - stores: `sb`, `sh`, `sw` type IDs `35-37`
  - loads: `lw`, `lh`, `lhu`, `lb`, `lbu` type IDs `38-42`

## New Fields Added

The following columns were appended after the Step 4 branch fields in `CV32E40P_timing_*.csv`:

- `memory_port_wait_cycles`
- `memory_port_kind`

## Source of Each Field

- `memory_port_wait_cycles`: computed in the base CV32E40P generated scheduler as:
  - `perfModel->WB_stage > n_LSU ? perfModel->WB_stage - n_LSU : 0`
  - This measures the delay between LSU readiness and the current serialized `WB_stage` availability used before DPort access.
- `memory_port_kind`: set in the scheduler:
  - `DPort_W` for store instructions `sb`, `sh`, `sw`
  - `DPort_R` for load instructions `lw`, `lh`, `lhu`, `lb`, `lbu`
  - `none` for all non-memory rows after the per-row reset in `getPipelineStream`

## Relevant Bottleneck

- Category: `memory` / `structural_resource`
- Mechanism: LSU/DPort structural serialization through the modeled `WB_stage`.
- This field is a modeled wait proxy, not a full de-overlapped bottleneck contribution.

## Test Result

Rebuild commands run:

```bash
cmake --build etiss-perf-sim/etiss/build_dir --target install -- -j2
cmake --build etiss-perf-sim/simulator/build -- -j2
```

Validation command run:

```bash
./scripts/run.sh em:ud cv32e40p -ta=.llm_output/analysis/bottleneck_knowledge/CV32E40P/test -tp=.llm_output/analysis/bottleneck_knowledge/CV32E40P/test
```

Representative files inspected:

- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/test/asm_trace_0000.txt`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/test/CV32E40P_trace_0000.csv`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/test/CV32E40P_timing_0000.csv`

Representative timing CSV header:

```text
IF_stage,ID_stage,EX_stage,WB_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,rs2_data,divider_delay_cycles,multiplier_delay_cycles,uses_rs1,uses_rs2,uses_rd,raw_wait_cycles,raw_blocking_reg,raw_blocking_ready_cycle,branch_is_control,branch_taken,branch_mispredict,branch_redirect_cycles,memory_port_wait_cycles,memory_port_kind
```

Trace validation summary across generated timing CSV files:

- Timing CSV files inspected: `6`
- Total timing rows: `923462`
- `memory_port_kind = DPort_W`: `123481` rows
- `memory_port_kind = DPort_R`: `283175` rows
- `memory_port_kind = none`: `516806` rows
- Store type IDs classified as `DPort_W`: `35`, `36`, `37`
- Load type IDs classified as `DPort_R`: `38`, `39`, `40`, `42` observed in `em:ud`
- Maximum observed `memory_port_wait_cycles`: `0`

Example rows:

```text
kind     instr_id  type_id  pc     IF  ID  EX  WB  memory_port_wait_cycles
none     0         10       256    1   2   3   0   0
DPort_W  46        37       28788  50  51  52  53  0
DPort_R  65        38       28896  71  72  73  74  0
```

The new fields are printed correctly. The `em:ud` run exercised loads and stores, but did not activate a positive memory-port structural wait in this model run.

## Uncertainty

- `memory_port_wait_cycles` measures only the modeled structural wait from `WB_stage` serialization before DPort access.
- It does not represent cache latency, memory latency, hit/miss behavior, or a fully de-overlapped bottleneck contribution.
- The tested `em:ud` run produced load/store rows but no `memory_port_wait_cycles > 0` rows.
- `CV32E40P_SchedulingFunction.cpp` is generated-style code and may be overwritten by future CorePerfDSL/code-generation runs.

## Next Recommended Step

Add contribution post-processing that combines the Step 1-5 fields into per-category summaries:

- RAW wait from `raw_wait_cycles`
- branch/control-flow redirect from `branch_redirect_cycles`
- divider delay from `divider_delay_cycles`
- multiplier delay from `multiplier_delay_cycles`
- memory-port structural wait from `memory_port_wait_cycles`

Then validate each category with targeted microbenchmarks that intentionally activate the relevant wait mechanism.
