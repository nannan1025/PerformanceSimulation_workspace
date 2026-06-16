# CVA6 Step 7 EX Subpipe / Resource Wait Trace Instrumentation

## Summary

Implemented Step 7 EX subpipe/resource wait instrumentation for the base `CVA6` timing trace. The new fields are appended to `CVA6_timing_*.csv` after the Step 6 RAW fields.

The measured wait is isolated to EX subpipe readiness terms in the generated scheduler. It does not use broad stage deltas such as `IS_stage - ID_stage` or `EX_stage - IS_stage`.

The main formula is:

```text
issue_ready_base = max(issue, clobber if present, source readiness if present)
ex_subpipe_wait_cycles = max(0, selected_EX_subpipe_ready_cycle - issue_ready_base)
```

This excludes RAW wait, clobber wait, issue readiness, branch/frontend wait, cache model delay, divider model latency, EX output-buffer capacity pressure, commit wait, and normal functional-unit latency.

Simulator timing behavior is unchanged. The validation run still reports `1,384,912` instructions, `2,129,817` estimated processor cycles, and CPI `1.53787`.

## Files Modified

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/include/CVA6_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_PerformanceModel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_SchedulingFunction.cpp`

No `CVA62`, `CVA6_QWEN_1`, monitor, branch predictor, cache model, divider model, clobber model, or shared register model code was modified.

## Functions Modified

- `CVA6_PerformanceModel::getPrintHeader`
- `CVA6_PerformanceModel::getPipelineStream`
- `CVA6_PerformanceModel::setEXSubpipeInstrumentation`
- `CVA6_PerformanceModel::recordEXSubpipeReady`
- base CVA6 scheduling lambdas whose `n_IS_stage` depends on EX subpipe readiness
- base CVA6 multiply/load/store scheduler internals where subpipe stages serialize on the next substage

## New Fields Added

```text
ex_subpipe_wait_cycles
ex_subpipe_kind
ex_blocking_resource
ex_blocking_ready_cycle
```

## Source of Each Field

- `ex_subpipe_wait_cycles`: largest positive wait from an EX subpipe ready cycle relative to the current instruction's issue-ready base.
- `ex_subpipe_kind`: instruction-side subpipe class: `ALU`, `MUL`, `DIV`, `DIVU`, `LOAD`, `STORE`, or `none`.
- `ex_blocking_resource`: concrete EX substage or subpipe readiness term that caused the largest wait.
- `ex_blocking_ready_cycle`: ready cycle of that blocking EX subpipe resource.

Rows without isolated EX subpipe wait emit:

```text
0,none,none,0
```

## Implementation Details

The CVA6 CorePerfDSL defines:

```text
EX_subpipe_alu   (EX_substage_alu)
EX_subpipe_mul   [blocks: EX_subpipe_alu] (EX_substage_mul_i -> EX_substage_mul_o)
EX_subpipe_div   [blocks: {EX_subpipe_alu, EX_subpipe_mul}] (EX_substage_div)
EX_subpipe_load  (EX_substage_lCtrl -> EX_substage_dCache -> EX_substage_lUnit)
EX_subpipe_store (EX_substage_sCtrl -> EX_substage_sUnit)
```

The generated scheduler was instrumented at the existing EX subpipe readiness max terms:

- ALU/default/branch/jump rows: `EX_substage_alu`, `EX_substage_mul_o`, `EX_substage_div`
- multiply rows: `EX_substage_mul_i`, `EX_substage_div`, plus internal `EX_substage_mul_o` serialization
- divider rows: `EX_substage_div`
- load rows: `EX_substage_lCtrl`, plus internal `EX_substage_dCache` and `EX_substage_lUnit` serialization
- store rows: `EX_substage_sCtrl`, plus internal `EX_substage_sUnit` serialization

`perfModel->EX_stage.get(8)` is intentionally excluded because it represents EX-stage output-buffer/capacity pressure, not a specific EX subpipe wait. Later `EX_stage.get(1)` and `COM_stage.get(2)` are also excluded because they are output/commit-side waits.

## Relevant Bottleneck

This supports CVA6 structural-resource bottleneck attribution for:

- ALU subpipe conflicts
- multiply subpipe serialization
- divider subpipe occupancy
- load subpipe serialization
- store subpipe serialization

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
PC_stage,IF_stage,IQ_stage,ID_stage,IS_stage,EX_stage,COM_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,imm,rs1_data,rs2_data,addr,uses_rs1,uses_rs2,uses_rd,divider_delay_cycles,divider_extra_cycles,icache_miss,icache_delay_cycles,icache_extra_cycles,frontend_wait_cycles,frontend_extra_cycles,dcache_miss,dcache_not_cacheable,dcache_delay_cycles,dcache_extra_cycles,memory_wait_cycles,branch_is_control,branch_taken,branch_predicted_taken,branch_mispredict,branch_predicted_target,branch_actual_target,branch_redirect_cycles,branch_predict_path_cycles,branch_predictor_component,branch_redirect_source_pc,branch_redirect_source_type_id,branch_redirect_source_component,raw_wait_cycles,raw_blocking_reg,raw_blocking_ready_cycle,raw_blocking_operand,ex_subpipe_wait_cycles,ex_subpipe_kind,ex_blocking_resource,ex_blocking_ready_cycle
```

## Representative EX Subpipe Rows

Selected rows from `.llm_output/analysis/bottleneck_knowledge/CVA6/test/CVA6_timing_0000.csv`:

| instr_id | type_id | ID_stage | IS_stage | EX_stage | wait | kind | blocking_resource | ready_cycle | raw_wait | divider_extra | dcache_extra |
|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|
| 78 | 1 | 210 | 211 | 212 | 1 | ALU | EX_substage_alu | 211 | 0 | 0 | 0 |
| 82 | 37 | 219 | 220 | 221 | 1 | ALU | EX_substage_alu | 220 | 0 | 0 | 0 |
| 114 | 60 | 341 | 341 | 349 | 5 | LOAD | EX_substage_dCache | 347 | 0 | 0 | 0 |
| 115 | 60 | 342 | 347 | 356 | 5 | LOAD | EX_substage_lCtrl | 347 | 0 | 0 | 6 |
| 116 | 60 | 347 | 348 | 357 | 6 | LOAD | EX_substage_dCache | 355 | 0 | 0 | 0 |
| 267 | 1 | 794 | 795 | 796 | 1 | ALU | EX_substage_alu | 795 | 0 | 0 | 0 |

These rows show that EX subpipe wait is reported separately from RAW, divider, and D-cache fields.

## Aggregate Validation Scan

CSV scan across all `16` timing files in the validation trace directory:

```text
rows: 1384912
ex_subpipe_nonzero_rows: 196900
bad_nonzero_rows: 0
bad_ready_rows: 0
zero_rows_bad_defaults: 0
kind_counts: {'ALU': 170178, 'LOAD': 20809, 'STORE': 2, 'MUL': 5911}
resource_counts: {'EX_substage_alu': 119930, 'EX_substage_dCache': 76, 'EX_substage_lCtrl': 20733, 'EX_substage_sCtrl': 2, 'EX_substage_div': 28078, 'EX_substage_mul_o': 28081}
top_types: [(34, 50281), (6, 20810), (60, 20803), (23, 20689), (39, 17733), (12, 13304), (22, 13302), (35, 10346), (18, 10342), (1, 8876), (42, 5911), (40, 4456)]
```

The scan confirmed:

- all nonzero rows have a valid `ex_subpipe_kind`
- all nonzero rows have a valid `ex_blocking_resource`
- all nonzero rows have `ex_blocking_ready_cycle > 0`
- zero-wait rows use the default `0,none,none,0`
- estimated cycle count stayed `2,129,817`, so the change is attribution-only

## Uncertainty

- This step intentionally excludes `EX_stage.get(8)` output-buffer/capacity pressure. If that pressure matters, add a separate `ex_capacity_wait_cycles` field later.
- EX subpipe wait can overlap conceptually with producer latency, cache delay, or later commit pressure; additive totals should not be treated as a de-overlapped CPI stack.
- Load/store internal subpipe waits are recorded when later load/store substages serialize the current row's subpipe progression. D-cache model latency itself remains reported through `dcache_extra_cycles`.
- Generated backend scheduler edits may be overwritten by future CorePerfDSL/code-generation runs.

## Next Recommended Step

Add CVA6 clobber/commit wait instrumentation or EX-stage output-buffer/capacity instrumentation, keeping them separate from the EX subpipe fields added here.
