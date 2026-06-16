# CVA6 Step 6 RAW Wait Trace Instrumentation

## Summary

Implemented Step 6 RAW/source-readiness instrumentation for the base `CVA6` timing trace. The new fields are appended to `CVA6_timing_*.csv` after the Step 5 branch source-link fields.

The RAW wait is isolated from clobber, commit, issue, EX resource, cache, branch, and normal pipeline latency by measuring only the register-readiness connector delta:

```text
raw_wait_cycles = max(0, reg_ready_cycle - ID_stage)
```

This matches the generated CVA6 source-read timing shape:

```cpp
n_uA_OF_A = std::max({n_ID_stage, perfModel->getRawReadyA(n_ID_stage)});
n_uA_OF_B = std::max({n_ID_stage, perfModel->getRawReadyB(n_ID_stage)});
```

Simulator timing behavior is unchanged. The validation run still reports `1,384,912` instructions, `2,129,817` estimated processor cycles, and CPI `1.53787`.

## Files Modified

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/include/CVA6_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_PerformanceModel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_SchedulingFunction.cpp`

No `CVA62`, `CVA6_QWEN_1`, monitor, branch predictor, cache, divider, clobber, or shared `StandardRegisterModel` code was modified.

## Functions Modified

- `CVA6_PerformanceModel::getPrintHeader`
- `CVA6_PerformanceModel::getPipelineStream`
- `CVA6_PerformanceModel::recordRawReady`
- `CVA6_PerformanceModel::getRawReadyA`
- `CVA6_PerformanceModel::getRawReadyB`
- base CVA6 scheduling lambdas whose source-read timing used `regModel.getXa()` or `regModel.getXb()`

## New Fields Added

```text
raw_wait_cycles
raw_blocking_reg
raw_blocking_ready_cycle
raw_blocking_operand
```

## Source of Each Field

- `raw_wait_cycles`: maximum wait from `regModel.getXa()` or `regModel.getXb()` readiness relative to `n_ID_stage`.
- `raw_blocking_reg`: `rs1` or `rs2` register index for the source with the maximum RAW wait, else `-1`.
- `raw_blocking_ready_cycle`: register ready cycle for the blocking source, else `0`.
- `raw_blocking_operand`: `rs1`, `rs2`, or `none`.

Source register `x0`/`0` is not counted as an architectural RAW dependency for attribution. The helper still returns the original register-model ready cycle, so scheduler behavior is unchanged.

## Implementation Details

The base generated scheduler had `59` direct `regModel.getXa()` calls and `35` direct `regModel.getXb()` calls. They were mechanically replaced with:

```cpp
perfModel->getRawReadyA(n_ID_stage)
perfModel->getRawReadyB(n_ID_stage)
```

The wrappers call the original register model exactly once, record the attribution fields, and return the same ready cycle to the scheduler.

RAW is measured against `n_ID_stage` because CVA6 source-readiness microactions `uA_OF_A` and `uA_OF_B` are scheduled from `ID_stage` into `IS_stage`. This avoids using `IS_stage - ID_stage`, which would also include clobber, issue, EX capacity, and EX subpipe/resource waits.

## Relevant Bottleneck

This supports CVA6 RAW/source-readiness bottleneck attribution:

- producer-consumer ALU chains
- load-use chains
- multiplier/divider result consumers
- branch/store/load source operand dependencies

The fields are attribution signals, not a de-overlapped CPI stack.

## Validation Command and Result

Rebuild commands run:

```sh
cmake --build etiss-perf-sim/etiss/build_dir --target install -- -j2
cmake --build etiss-perf-sim/simulator/build -- -j2
```

Validation command run:

```sh
./scripts/run.sh em:ud cva6 -ta=.llm_output/analysis/bottleneck_knowledge/CVA6/test -tp=.llm_output/analysis/bottleneck_knowledge/CVA6/test
```

Result:

```text
Number of instructions: 1384912
Estimated number of processor cycles: 2129817
Estimated average number of processor cycles per instruction: 1.53787
```

Representative output files found:

- `.llm_output/analysis/bottleneck_knowledge/CVA6/test/asm_trace_0000.txt`
- `.llm_output/analysis/bottleneck_knowledge/CVA6/test/CVA6_trace_0000.csv`
- `.llm_output/analysis/bottleneck_knowledge/CVA6/test/CVA6_timing_0000.csv`

## Representative Header

```text
PC_stage,IF_stage,IQ_stage,ID_stage,IS_stage,EX_stage,COM_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,imm,rs1_data,rs2_data,addr,uses_rs1,uses_rs2,uses_rd,divider_delay_cycles,divider_extra_cycles,icache_miss,icache_delay_cycles,icache_extra_cycles,frontend_wait_cycles,frontend_extra_cycles,dcache_miss,dcache_not_cacheable,dcache_delay_cycles,dcache_extra_cycles,memory_wait_cycles,branch_is_control,branch_taken,branch_predicted_taken,branch_mispredict,branch_predicted_target,branch_actual_target,branch_redirect_cycles,branch_predict_path_cycles,branch_predictor_component,branch_redirect_source_pc,branch_redirect_source_type_id,branch_redirect_source_component,raw_wait_cycles,raw_blocking_reg,raw_blocking_ready_cycle,raw_blocking_operand
```

## Representative RAW Rows

Selected rows from `.llm_output/analysis/bottleneck_knowledge/CVA6/test/CVA6_timing_0000.csv`:

| instr_id | type_id | ID_stage | IS_stage | rs1 | rs2 | uses_rs1 | uses_rs2 | raw_wait_cycles | raw_blocking_reg | raw_blocking_ready_cycle | raw_blocking_operand |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 100 | 23 | 282 | 284 | 18 | 8 | 1 | 1 | 1 | 18 | 283 | rs1 |
| 107 | 41 | 299 | 300 | 15 | 0 | 1 | 0 | 1 | 15 | 300 | rs1 |
| 179 | 6 | 516 | 524 | 15 | 0 | 1 | 0 | 8 | 15 | 524 | rs1 |
| 191 | 26 | 548 | 556 | 12 | 13 | 1 | 1 | 8 | 12 | 556 | rs1 |
| 192 | 22 | 556 | 558 | 15 | 13 | 1 | 1 | 1 | 15 | 557 | rs1 |

For each nonzero row above:

```text
raw_wait_cycles == raw_blocking_ready_cycle - ID_stage
```

## Aggregate Validation Scan

CSV scan across all `15` timing files in the validation trace directory:

```text
rows: 1384912
raw_nonzero_rows: 340333
bad_formula: 0
bad_operand: 0
bad_reg: 0
x0_nonzero: 0
zero_rows_bad_defaults: 0
operand_counts: {'rs1': 162819, 'rs2': 177514}
top_regs: [(10, 85710), (28, 79800), (6, 59112), (13, 44344), (12, 20698), (21, 8869), (16, 7391), (8, 5944), (23, 5914), (22, 5912)]
top_types: [(23, 87192), (22, 73897), (42, 56161), (12, 41375), (60, 35467), (65, 26621), (47, 19211), (35, 113), (62, 102), (34, 75)]
```

The scan confirmed:

- all nonzero RAW rows satisfy `raw_wait_cycles == raw_blocking_ready_cycle - ID_stage`
- `raw_blocking_operand` is always `rs1` or `rs2` when RAW wait is nonzero
- `raw_blocking_reg` matches the selected source register column
- zero-wait rows use the default `0,-1,0,none`
- no source register `0` row is attributed as nonzero RAW wait
- estimated cycle count stayed `2,129,817`, so the change is attribution-only

## Uncertainty

- No producer instruction ID is available because Step 6 does not extend `StandardRegisterModel`.
- RAW wait can overlap conceptually with earlier producer latency such as divider, multiplier, or load latency; additive totals should not be treated as a de-overlapped CPI stack.
- The shared register model still stores readiness for `rd = 0`; Step 6 ignores source `x0` for attribution but does not change timing behavior.
- Generated backend scheduler edits may be overwritten by future CorePerfDSL/code-generation runs.

## Next Recommended Step

Add CVA6 clobber/commit wait instrumentation or EX subpipe/resource wait instrumentation. Those should use isolated connector/resource deltas, similar to Step 5 and Step 6, rather than broad stage deltas such as `IS_stage - ID_stage` or `EX_stage - IS_stage`.
