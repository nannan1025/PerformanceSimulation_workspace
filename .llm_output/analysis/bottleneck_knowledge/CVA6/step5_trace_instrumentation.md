# CVA6 Step 5 Branch Prediction/Redirect Trace Instrumentation

## Summary

Implemented and corrected Step 5 branch prediction/redirect instrumentation for the base `CVA6` timing trace.

The original Step 5 redirect proxy used:

```text
branch_redirect_cycles = branch_mispredict ? max(0, EX_stage - IF_stage) : 0
```

That formula was removed because `EX_stage - IF_stage` can include IQ, ID, IS, RAW, clobber, issue, or execution-resource waits. The corrected field now reports the isolated frontend PC-correction wait imposed by the existing branch redirect connector:

```text
branch_redirect_cycles = max(0, n_uA_PcCorrect - n_Enter)
```

This wait is measured immediately after the normal scheduler expression:

```cpp
n_uA_PcCorrect = std::max({n_Enter, perfModel->dynBranchPredModel.getPc_mp()});
```

Simulator timing behavior and branch predictor behavior are unchanged. The validation run still reports `1,384,912` instructions, `2,129,817` estimated processor cycles, and CPI `1.53787`.

## Files Modified

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/include/CVA6_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_PerformanceModel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_SchedulingFunction.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/cva6/BranchPredictionModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/src/cva6/BranchPredictionModel.cpp`

No `CVA62`, `CVA6_QWEN_1`, monitor, cache, divider, or RAW code was modified.

## Functions Modified

- `CVA6_PerformanceModel::getPrintHeader`
- `CVA6_PerformanceModel::getPipelineStream`
- `CVA6_PerformanceModel::setBranchInstrumentation`
- `CVA6_PerformanceModel::setBranchRedirectWait`
- base CVA6 scheduling lambdas in `CVA6_SchedulingFunction.cpp` after each `n_uA_PcCorrect` calculation
- `cva6::BranchPredictionModel::setPc_p`
- `cva6::BranchPredictionModel::setPc_p_j`
- `cva6::BranchPredictionModel::setPc_p_jr`
- `cva6::BranchPredictionModel::getPc_mp`
- `cva6::BranchPredictionModel::clearTraceInfo`

## Fields Added

Step 5 branch fields:

```text
branch_is_control
branch_taken
branch_predicted_taken
branch_mispredict
branch_predicted_target
branch_actual_target
branch_redirect_cycles
branch_predict_path_cycles
branch_predictor_component
branch_redirect_source_pc
branch_redirect_source_type_id
branch_redirect_source_component
```

The final three source-link fields were added by the correction so a redirect wait observed on a later frontend row can be attributed back to the source control-flow instruction.

## Source of Each Field

- `branch_is_control`: set from printed row `type_id`; `1` only for CVA6 control-flow type IDs `34-41`.
- `branch_predicted_taken`: cached in `BranchPredictionModel` from the existing BHT/RAS/BTB/JAL prediction path.
- `branch_predicted_target`: cached predicted target; `0` when no target was predicted.
- `branch_predictor_component`: cached as `BHT`, `JAL`, `JALR`, `RAS`, `BTB`, or `none`.
- `branch_taken`: computed in `CVA6_PerformanceModel::getPipelineStream`; jumps are always taken, conditional branches compare the adjacent channel PC with `brTarget`.
- `branch_mispredict`: computed from predicted versus actual outcome/target.
- `branch_actual_target`: `brTarget` for taken branches/jumps; `pc + 4` for not-taken conditional branches.
- `branch_redirect_cycles`: isolated PC-correction wait from `max(0, n_uA_PcCorrect - n_Enter)`.
- `branch_predict_path_cycles`: existing correctly predicted taken-path proxy, `branch_taken && !branch_mispredict ? max(0, IF_stage - PC_stage) : 0`.
- `branch_redirect_source_pc`: branch PC cached by `BranchPredictionModel` when the normal predictor path detects a redirect.
- `branch_redirect_source_type_id`: source branch type ID cached by `BranchPredictionModel`.
- `branch_redirect_source_component`: source predictor component cached by `BranchPredictionModel`.

## Implementation Notes

The generated base CVA6 scheduler now records redirect wait after every existing PC-correction connector calculation:

```cpp
n_uA_PcCorrect = std::max({n_Enter, perfModel->dynBranchPredModel.getPc_mp()});
perfModel->setBranchRedirectWait(n_uA_PcCorrect > n_Enter ? n_uA_PcCorrect - n_Enter : 0);
```

No extra calls to `BranchPredictionModel::getPc_mp()` or `BranchPredictionModel::getPc_pt()` were added. Those functions mutate predictor state, so the implementation only observes results from calls already present in the scheduler.

The branch predictor was extended with trace-only cache fields and read-only getters. These cache the source branch PC, source branch type ID, and predictor component when the existing predictor logic determines a misprediction redirect. BHT/RAS/BTB behavior is unchanged.

## Relevant Bottleneck

This supports CVA6 branch/control-flow bottleneck attribution:

- dynamic branch predictor misses
- jump-register target prediction misses
- isolated frontend PC-correction wait caused by redirect
- correctly predicted taken path timing proxy

The corrected `branch_redirect_cycles` should be used by additive contribution summaries instead of the old `EX_stage - IF_stage` proxy.

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
PC_stage,IF_stage,IQ_stage,ID_stage,IS_stage,EX_stage,COM_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,imm,rs1_data,rs2_data,addr,uses_rs1,uses_rs2,uses_rd,divider_delay_cycles,divider_extra_cycles,icache_miss,icache_delay_cycles,icache_extra_cycles,frontend_wait_cycles,frontend_extra_cycles,dcache_miss,dcache_not_cacheable,dcache_delay_cycles,dcache_extra_cycles,memory_wait_cycles,branch_is_control,branch_taken,branch_predicted_taken,branch_mispredict,branch_predicted_target,branch_actual_target,branch_redirect_cycles,branch_predict_path_cycles,branch_predictor_component,branch_redirect_source_pc,branch_redirect_source_type_id,branch_redirect_source_component
```

## Representative Redirect Rows

Selected rows from `.llm_output/analysis/bottleneck_knowledge/CVA6/test/CVA6_timing_0000.csv` after the correction:

| instr_id | row_type_id | PC_stage | IF_stage | EX_stage | branch_is_control | branch_mispredict | redirect_cycles | source_pc | source_type_id | source_component | old `EX-IF` |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| 6 | 6 | 38 | 45 | 48 | 0 | 0 | 10 | 65556 | 41 | JALR | 3 |
| 83 | 40 | 221 | 228 | 231 | 1 | 0 | 7 | 2147484076 | 37 | BHT | 3 |
| 96 | 1 | 263 | 270 | 273 | 0 | 0 | 10 | 2147493648 | 34 | BHT | 3 |
| 108 | 2 | 301 | 308 | 311 | 0 | 0 | 7 | 2147493720 | 41 | JALR | 3 |
| 111 | 41 | 318 | 325 | 328 | 1 | 0 | 10 | 2147562176 | 34 | BHT | 3 |

These examples show the corrected behavior: `branch_redirect_cycles` is no longer derived from the printed branch row's `EX_stage - IF_stage`. It is the frontend wait observed at the PC-correction connector, and source-link fields identify the branch that caused it.

## Aggregate Validation Scan

CSV scan across all `13` timing files:

```text
rows: 1384912
control_rows: 128117
control_type_counts: {41: 1586, 40: 6073, 37: 15, 34: 86030, 35: 16542, 39: 17774, 36: 34, 38: 63}
redirect_rows: 62328
redirect_bad_source: 0
redirect_noncontrol_rows: 62288
redirect_matches_old_EX_minus_IF: 0
redirect_differs_old_EX_minus_IF: 62328
source_type_counts: {41: 43, 37: 9, 34: 41487, 35: 7449, 39: 13316, 38: 17, 36: 7}
source_component_counts: {'JALR': 12, 'BHT': 62285, 'RAS': 30, 'BTB': 1}
```

The scan confirmed:

- all rows with `type_id` in `34-41` still have `branch_is_control = 1`
- rows with `branch_redirect_cycles > 0` have nonzero source PC/type/component fields
- redirect-wait rows are often non-control rows, which is expected because the wait is observed when a following instruction tries to enter the frontend
- no redirect row matched the old `EX_stage - IF_stage` proxy in this validation trace
- the estimated cycle count remained `2,129,817`, so the change is attribution-only

## Uncertainty

- `branch_redirect_cycles` is now an isolated frontend PC-correction wait, not branch execution latency.
- Redirect wait can appear on the instruction after the branch; use `branch_redirect_source_pc`, `branch_redirect_source_type_id`, and `branch_redirect_source_component` for attribution.
- `branch_predict_path_cycles` remains a proxy and is separate from redirect delay.
- Conditional not-taken `branch_actual_target` is reported as `pc + 4`. Compressed-instruction edge cases may need a decoded instruction-length field later.
- The CVA6 branch predictor model is shared by CVA6-derived variants at compile time, but only trace-only cache fields/getters were added and no derived backend files were modified.
- Generated backend scheduler edits may be overwritten by future CorePerfDSL/code-generation runs.

## Next Recommended Step

Update or create a CVA6 contribution analyzer that uses the corrected Step 1-5 timing fields:

- divider: `divider_extra_cycles`
- I-cache/frontend: `icache_extra_cycles`, `frontend_extra_cycles`
- D-cache/memory: `dcache_extra_cycles`, `memory_wait_cycles`
- branch/control-flow: corrected `branch_redirect_cycles`, with attribution through `branch_redirect_source_*`
