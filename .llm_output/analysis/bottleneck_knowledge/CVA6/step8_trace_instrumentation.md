# CVA6 Step 8 Clobber / Commit Wait Trace Instrumentation

## Summary

Implemented Step 8 clobber/commit wait instrumentation for the base `CVA6` timing trace. The new fields are appended to `CVA6_timing_*.csv` after the Step 7 EX subpipe/resource fields.

The instrumentation keeps clobber, commit, RAW, and EX subpipe attribution separate:

- `clobber_wait_cycles` measures only the destination-register clobber readiness delta from `ClobberModel::getCb_out()` relative to `ID_stage`.
- `commit_backpressure_wait_cycles` measures only the `COM_stage.get(2)` backpressure term used when an instruction leaves `EX_stage`.
- `commit_capacity_wait_cycles` measures only the `COM_stage.get(1)` capacity term used when an instruction enters `COM_stage`.

Simulator timing behavior is unchanged. The validation run still reports `1,384,912` instructions, `2,129,817` estimated processor cycles, and CPI `1.53787`.

## Files Modified

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/include/CVA6_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_PerformanceModel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_SchedulingFunction.cpp`

No `CVA62`, `CVA6_QWEN_1`, monitor, RAW, branch, cache, divider, EX subpipe, or external model behavior was modified.

## Functions Modified

- `CVA6_PerformanceModel::getPrintHeader`
- `CVA6_PerformanceModel::getPipelineStream`
- `CVA6_PerformanceModel::getClobberReady`
- `CVA6_PerformanceModel::recordCommitBackpressure`
- `CVA6_PerformanceModel::recordCommitCapacity`
- base CVA6 scheduling lambdas using `uA_Clobber`, `COM_stage.get(2)`, or `COM_stage.get(1)`

## New Fields Added

```text
clobber_wait_cycles
clobber_blocking_reg
clobber_blocking_ready_cycle
commit_backpressure_wait_cycles
commit_capacity_wait_cycles
commit_wait_cycles
commit_wait_kind
commit_blocking_ready_cycle
commit_base_cycle
```

Rows without clobber/commit wait emit:

```text
0,-1,0,0,0,0,none,0,0
```

## Source of Each Field

- `clobber_wait_cycles`: `max(0, clobberModel.getCb_out() - n_ID_stage)`.
- `clobber_blocking_reg`: current row `rd` when clobber wait is nonzero, else `-1`.
- `clobber_blocking_ready_cycle`: clobber ready cycle when clobber wait is nonzero, else `0`.
- `commit_backpressure_wait_cycles`: `max(0, COM_stage.get(2) - max(EX_substage_ready, EX_stage.get(1)))`.
- `commit_capacity_wait_cycles`: `max(0, COM_stage.get(1) - n_Commit)`.
- `commit_wait_cycles`: sum of commit backpressure and commit capacity wait.
- `commit_wait_kind`: `none`, `backpressure`, `capacity`, or `backpressure+capacity`.
- `commit_blocking_ready_cycle`: ready cycle for the dominant positive commit wait, else `0`.
- `commit_base_cycle`: base cycle for the dominant positive commit wait, else `0`.

## Implementation Details

The generated scheduler clobber pattern:

```cpp
n_uA_Clobber = std::max({n_ID_stage, perfModel->clobberModel.getCb_out()});
```

was changed to:

```cpp
n_uA_Clobber = std::max({n_ID_stage, perfModel->getClobberReady(n_ID_stage)});
```

`getClobberReady()` calls the original `ClobberModel::getCb_out()` exactly once, records the clobber delta, and returns the same ready cycle to preserve timing behavior.

The generated EX-to-commit backpressure pattern:

```cpp
n_EX_stage = std::max({n_EX_substage_*, perfModel->EX_stage.get(1), perfModel->COM_stage.get(2)});
```

was expanded into local captures, followed by:

```cpp
perfModel->recordCommitBackpressure(n_COMBackpressureBase, n_COMBackpressureReady);
```

The generated commit-capacity pattern:

```cpp
n_COM_stage = std::max({n_Commit, perfModel->COM_stage.get(1)});
```

was expanded into local captures, followed by:

```cpp
perfModel->recordCommitCapacity(n_Commit, n_COMCapacityReady);
```

This step does not include RAW/source readiness, issue readiness, EX subpipe readiness, `EX_stage.get(8)` output-buffer pressure, cache delay, branch delay, divider delay, or normal `+1` commit latency.

## Relevant Bottleneck

This supports CVA6 destination clobber and commit-side structural bottleneck attribution:

- destination-register clobber / WAW-style readiness
- EX-to-COM backpressure from commit-side availability
- COM-stage capacity pressure

These fields are attribution signals, not a de-overlapped CPI stack.

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
PC_stage,IF_stage,IQ_stage,ID_stage,IS_stage,EX_stage,COM_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,imm,rs1_data,rs2_data,addr,uses_rs1,uses_rs2,uses_rd,divider_delay_cycles,divider_extra_cycles,icache_miss,icache_delay_cycles,icache_extra_cycles,frontend_wait_cycles,frontend_extra_cycles,dcache_miss,dcache_not_cacheable,dcache_delay_cycles,dcache_extra_cycles,memory_wait_cycles,branch_is_control,branch_taken,branch_predicted_taken,branch_mispredict,branch_predicted_target,branch_actual_target,branch_redirect_cycles,branch_predict_path_cycles,branch_predictor_component,branch_redirect_source_pc,branch_redirect_source_type_id,branch_redirect_source_component,raw_wait_cycles,raw_blocking_reg,raw_blocking_ready_cycle,raw_blocking_operand,ex_subpipe_wait_cycles,ex_subpipe_kind,ex_blocking_resource,ex_blocking_ready_cycle,clobber_wait_cycles,clobber_blocking_reg,clobber_blocking_ready_cycle,commit_backpressure_wait_cycles,commit_capacity_wait_cycles,commit_wait_cycles,commit_wait_kind,commit_blocking_ready_cycle,commit_base_cycle
```

## Representative Rows

Selected rows from `.llm_output/analysis/bottleneck_knowledge/CVA6/test/CVA6_timing_0000.csv`.

### Clobber Rows

| instr_id | type_id | ID_stage | IS_stage | rd | clobber_wait | clobber_reg | clobber_ready | raw_wait | ex_subpipe_wait |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 74 | 6 | 201 | 202 | 5 | 1 | 5 | 202 | 0 | 0 |
| 77 | 6 | 209 | 210 | 2 | 1 | 2 | 210 | 0 | 0 |
| 81 | 6 | 218 | 219 | 27 | 1 | 27 | 219 | 0 | 0 |
| 90 | 6 | 248 | 249 | 18 | 1 | 18 | 249 | 0 | 0 |
| 99 | 6 | 281 | 282 | 18 | 1 | 18 | 282 | 0 | 0 |

Each nonzero clobber row satisfies:

```text
clobber_wait_cycles == clobber_blocking_ready_cycle - ID_stage
clobber_blocking_reg == rd
```

### Commit Rows

| instr_id | type_id | EX_stage | COM_stage | backpressure | capacity | total | kind | ready | base | ex_subpipe_wait |
|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|
| 106 | 6 | 301 | 302 | 1 | 0 | 1 | backpressure | 301 | 300 | 0 |
| 118 | 41 | 358 | 359 | 1 | 0 | 1 | backpressure | 358 | 357 | 0 |
| 140 | 65 | 424 | 425 | 1 | 0 | 1 | backpressure | 424 | 423 | 0 |
| 149 | 6 | 443 | 444 | 1 | 0 | 1 | backpressure | 443 | 442 | 0 |
| 151 | 6 | 444 | 445 | 1 | 0 | 1 | backpressure | 444 | 443 | 0 |

Each nonzero commit row satisfies:

```text
commit_wait_cycles == commit_backpressure_wait_cycles + commit_capacity_wait_cycles
commit_blocking_ready_cycle > commit_base_cycle
```

## Aggregate Validation Scan

CSV scan across all `18` timing files in the validation trace directory:

```text
rows: 1384912
clobber_nonzero_rows: 338562
commit_backpressure_nonzero_rows: 13436
commit_capacity_nonzero_rows: 0
commit_nonzero_rows: 13436
bad_clobber_formula: 0
bad_clobber_reg: 0
bad_commit_sum: 0
bad_commit_kind: 0
bad_commit_ready: 0
zero_rows_bad_defaults: 0
commit_kind_counts: {'backpressure': 13436}
top_clobber_types: [(22, 104947), (12, 81277), (42, 65023), (23, 42856), (60, 25124), (47, 10345), (6, 4482), (18, 4444), (25, 11), (9, 11), (56, 7), (26, 6)]
top_commit_types: [(34, 2960), (12, 2955), (6, 1538), (41, 1511), (23, 1481), (22, 1480), (18, 1478), (65, 13), (40, 7), (0, 3), (35, 2), (1, 2)]
```

The scan confirmed:

- clobber formula checks passed for all nonzero clobber rows
- clobber blocking register matches `rd` for all nonzero clobber rows
- commit total equals backpressure plus capacity for all nonzero commit rows
- commit kind classification matches the positive wait components
- zero-wait rows use the default `0,-1,0,0,0,0,none,0,0`
- estimated cycle count stayed `2,129,817`, so the change is attribution-only

## Uncertainty

- This step reports clobber wait separately from RAW, but clobber and RAW can still both constrain the same instruction before `IS_stage`; additive totals should not be treated as de-overlapped CPI.
- `COM_stage.get(2)` is treated as commit-side backpressure because it is used directly in the generated `EX_stage` max. `EX_stage.get(1)` remains excluded as EX output-buffer pressure.
- No commit-capacity rows were activated by the `em:ud` validation trace; the field and formula are present, but this workload did not produce nonzero `commit_capacity_wait_cycles`.
- The validation directory contained `18` timing CSV files after this run because trace rotation/file history is present in the output directory.
- Generated backend scheduler edits may be overwritten by future CorePerfDSL/code-generation runs.

## Next Recommended Step

Add a separate `ex_capacity_wait_cycles` field for `EX_stage.get(8)` output-buffer pressure, or update the CVA6 contribution analyzer to include Step 1-8 fields while keeping the categories separate.
