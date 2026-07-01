# Rocket First-Pass Timing Trace Instrumentation

## 1. Files Inspected Before Implementation

- `.llm_output/correction/rocket_basic_summary.md`
- `.llm_output/correction/rocket_trace_field_instrumentation_plan.md`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/include/ROCKET_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_PerformanceModel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_SchedulingFunction.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/rocket/ICacheModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/rocket/DCacheModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/rocket/BranchPredictionModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/include/CV32E40P_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_PerformanceModel.cpp`
- `scripts/run.sh`
- `scripts/run2.sh`
- `scripts/support/run_helper.py`

## 2. Files Modified

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/include/ROCKET_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_PerformanceModel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_SchedulingFunction.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/rocket/ICacheModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/rocket/DCacheModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/rocket/BranchPredictionModel.h`

No CorePerfDSL file was modified.

## 3. Trace Fields Added

The Rocket timing CSV now prints:

```text
IF,ID,EX,MEM,WB,
instr_id,pc,rs1,rs2,rd,
uses_rs1,uses_rs2,uses_rd,
stage_gap_if_id,stage_gap_id_ex,stage_gap_ex_mem,stage_gap_mem_wb,
raw_wait_cycles,raw_blocking_reg,raw_blocking_ready_cycle,
icache_delay_cycles,icache_miss,
dcache_delay_cycles,dcache_miss,
branch_is_control,branch_mispredict,branch_redirect_cycles,
divider_delay_cycles
```

The first five columns are the original timing columns. The remaining columns are temporary first-pass observability fields.

## 4. Field Sources

| Field | Computed or extracted from |
|---|---|
| `instr_id` | Monotonic counter in `ROCKET_PerformanceModel::getPipelineStream()` |
| `pc` | `ROCKET_Channel::pc`, read at streamed instruction index |
| `rs1` | `ROCKET_Channel::rs1` when `uses_rs1=1`, otherwise `0` |
| `rs2` | `ROCKET_Channel::rs2` when `uses_rs2=1`, otherwise `0` |
| `rd` | `ROCKET_Channel::rd` when `uses_rd=1`, otherwise `0` |
| `uses_rs1` | Set by `ROCKET_PerformanceModel::getRawReadyA()` |
| `uses_rs2` | Set by `ROCKET_PerformanceModel::getRawReadyB()` |
| `uses_rd` | Set by `ROCKET_PerformanceModel::setRegWriteReady()` |
| `stage_gap_if_id` | `ID - IF`, saturated at `0` |
| `stage_gap_id_ex` | `EX - ID`, saturated at `0` |
| `stage_gap_ex_mem` | `MEM - EX`, saturated at `0` |
| `stage_gap_mem_wb` | `WB - MEM`, saturated at `0` |
| `raw_wait_cycles` | Max wait observed by `getRawReadyA/B(baseCycle)` relative to `n_Decoder` |
| `raw_blocking_reg` | `rs1` or `rs2` that caused the max RAW wait, default `-1` |
| `raw_blocking_ready_cycle` | Register-model ready cycle for the max RAW wait |
| `icache_delay_cycles` | Existing `iCacheModel.getDelay()` result minus one, recorded without a second call |
| `icache_miss` | Non-stateful `iCacheModel.getMiss()` after the existing delay call |
| `dcache_delay_cycles` | Existing `dCacheModel.getDelay()` result minus one, recorded without a second call |
| `dcache_miss` | Non-stateful `dCacheModel.getMiss()` after the existing delay call |
| `branch_is_control` | Set in branch, `jal`, and `jalr` scheduling functions |
| `branch_mispredict` | Defaulted to `0` in this first pass |
| `branch_redirect_cycles` | Defaulted to `0` in this first pass |
| `divider_delay_cycles` | Existing divider/divider_u `getDelay()` result minus one, recorded without a second call |

## 5. Reliable Fields

Reliable in the current first-pass implementation:

- `instr_id`
- `pc`
- `rs1`, `rs2`, `rd` together with `uses_rs1`, `uses_rs2`, `uses_rd`
- all four stage-gap fields
- `raw_wait_cycles`, `raw_blocking_reg`, `raw_blocking_ready_cycle`
- `icache_delay_cycles`, `icache_miss`
- `dcache_delay_cycles`, `dcache_miss` for load/store instructions
- `branch_is_control`
- `divider_delay_cycles`, with the important caveat that the current Rocket divider models return delay `1`

## 6. Defaulted Fields

The following fields are intentionally left at default values in this first pass:

- `branch_mispredict=0`
- `branch_redirect_cycles=0`

Reason: Rocket branch prediction evaluates misprediction state through `getPc_mp()` while scheduling the following instruction. Recording that result on the original branch row would require either calling a stateful branch model method twice or adding delayed row patching. Both would violate the conservative first-pass constraints.

## 7. Run Command Result

The exact requested command was run:

```text
./scripts/run.sh em:ud.riscv ROCKET -ta=.llm_output/correction/test -tp=.llm_output/correction/test
```

It did not run the simulator. It printed:

```text
No valid core specified!
```

The reason is that `scripts/run.sh` currently recognizes only lowercase `cv32e40p` and `cva6` as valid core arguments. It does not recognize `ROCKET`.

For validation, the existing Rocket-capable runner was used:

```text
./scripts/run2.sh em:ud.riscv ROCKET -ta=.llm_output/correction/test -tp=.llm_output/correction/test
```

This run completed successfully after rebuilding and installing the `SoftwareEval` plugin.

Build/installation commands used:

```text
cmake --build etiss-perf-sim/etiss/build_dir --target SWEVAL_BACKENDS_LIB
cmake --build etiss-perf-sim/etiss/build_dir --target SoftwareEval
cmake --build etiss-perf-sim/etiss/build_dir --target install
```

## 8. Generated Trace Files Inspected

Representative files inspected:

- `.llm_output/correction/test/ROCKET_timing_0000.csv`
- `.llm_output/correction/test/ROCKET_trace_0000.csv`
- `.llm_output/correction/test/asm_trace_0000.txt`

The output directory contains the expected trace file families:

- `asm_trace_*.txt`
- `ROCKET_timing_*.csv`
- `ROCKET_trace_*.csv`

## 9. Timing CSV Validation

The fresh timing CSV contains the new fields correctly. Representative header:

```text
IF,ID,EX,MEM,WB,instr_id,pc,rs1,rs2,rd,uses_rs1,uses_rs2,uses_rd,stage_gap_if_id,stage_gap_id_ex,stage_gap_ex_mem,stage_gap_mem_wb,raw_wait_cycles,raw_blocking_reg,raw_blocking_ready_cycle,icache_delay_cycles,icache_miss,dcache_delay_cycles,dcache_miss,branch_is_control,branch_mispredict,branch_redirect_cycles,divider_delay_cycles
```

Column-count validation on `.llm_output/correction/test/ROCKET_timing_0000.csv`:

```text
header_fields=28
row2_fields=28
checked_rows=177708
```

Representative first data row:

```text
22,23,24,25,26,0,2147483648,0,0,1,1,0,1,1,1,1,1,0,-1,0,21,1,0,0,0,0,0,0
```

The first row PC `2147483648` is `0x80000000`, matching both:

- `ROCKET_trace_0000.csv`
- `asm_trace_0000.txt`

Stage gap validation for the first row:

```text
IF=22 ID=23 EX=24 MEM=25 WB=26
gaps=1,1,1,1
expected=1,1,1,1
```

Sample non-default observations:

- ICache cold miss: `icache_delay_cycles=21`, `icache_miss=1`
- RAW dependency example: `raw_wait_cycles=2`, `raw_blocking_reg=0`, `raw_blocking_ready_cycle=101`
- DCache miss example: `dcache_delay_cycles=38`, `dcache_miss=1`
- Control-flow marking example: `branch_is_control=1`

## 10. Limitations And Follow-Up Work

- This is temporary manual instrumentation in generated Rocket backend files. It can be overwritten by regeneration.
- `branch_mispredict` and `branch_redirect_cycles` remain defaulted because conservative row-local extraction is not reliable with the current branch predictor timing.
- `divider_delay_cycles` currently reflects the existing model behavior. Rocket divider `getDelay()` still returns `1`, so extra divider delay is normally `0`.
- `scripts/run.sh` does not recognize `ROCKET`; use `scripts/run2.sh` or update `scripts/run.sh` separately if exact command compatibility is required.
- The simulator uses the installed plugin under `etiss-perf-sim/etiss/build_dir/installed`, so after backend edits the plugin must be rebuilt and installed before traces reflect source changes.
- Future permanent support should move stable fields into the generator/CorePerfDSL flow rather than maintaining manual generated-code edits.
