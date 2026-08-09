# Rocket Branch Prediction Model Phase 1 Implementation

This document records the conservative Rocket-aware branch predictor implementation for the `RC` Rocket test variant.

## Summary

Implemented a conservative Rocket-aware dynamic branch predictor in the shared Rocket external model used by `RC`, and added RC timing-trace fields for branch predictor diagnostics.

The implementation keeps the existing CorePerfDSL and timing connector shape unchanged:

```text
Pc_p, Pc_p_j, Pc_p_jr, Pc_c -> Pc_mp, Pc_pt
```

No CorePerfDSL files were modified.

## Files Modified

Predictor implementation:

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/rocket/BranchPredictionModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/src/rocket/BranchPredictionModel.cpp`

RC timing trace instrumentation:

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/RC/include/RC_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/RC/src/RC_PerformanceModel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/RC/src/RC_SchedulingFunction.cpp`

Documentation:

- `.llm_output/correction/rocket_branch_prediction_model_phase1.md`

## Implemented Predictor Behavior

BHT:

- Uses 512 entries.
- Uses 1-bit prediction entries.
- Keeps 8-bit global history.
- Keeps the existing 3-bit history hash contribution to the BHT index.
- Updates the 1-bit entry and advances global history at branch resolution.

BTB:

- Keeps 28 entries.
- Stores valid bit, PC, target address, and conservative control-flow kind metadata.
- Uses fully scanned lookup and simple next-replacement update.
- Does not implement exact six-page Rocket BTB compression because the exact page semantics are not available in the current simulator.

RAS:

- Keeps 6 entries.
- Direct and indirect calls push `pc + 4`.
- Returns pop from the RAS.
- Compressed instruction length is still approximated because instruction length is not available.

Control-flow handling:

- Conditional branch direction comes from BHT.
- Conditional branch predicted target comes from BTB when BHT predicts taken and BTB hits.
- Direct `jal` is predicted taken and uses `brTarget` as predicted target.
- `jalr` returns use RAS.
- Other `jalr` instructions use BTB.
- Direction misprediction and target misprediction are tracked separately.
- Final misprediction is `direction_mispredict || target_mispredict`.

Timing behavior:

- `getPc_mp()` returns `t_pc_mp` only on final misprediction.
- `getPc_pt()` returns `t_pc_pt` only for correctly predicted taken control flow.
- `setPc_c()` still records MEM-stage correction timing as `pc_c + 1`, preserving the current Rocket model convention.

## Added Trace Fields

The RC timing CSV still starts with:

```text
IF,ID,EX,MEM,WB
```

The following predictor fields were added after the stage columns:

```text
pc
branch_is_control
branch_taken
branch_predicted_taken
branch_direction_mispredict
branch_target_mispredict
branch_misprediction
branch_predicted_target
branch_actual_target
branch_predictor_component
branch_redirect_source_pc
branch_redirect_source_component
branch_btb_hit
branch_bht_index
branch_ras_used
IF_ext_Pc_mp
IF_ext_Pc_pt
```

`IF_ext_Pc_mp` and `IF_ext_Pc_pt` are captured from local variables in `RC_SchedulingFunction.cpp`. The scheduling code still calls each stateful connector method exactly once per instruction and reuses the local value in the existing `max(...)` expression.

## Row-Local Trace Semantics

Branch prediction in this simulator is delayed:

- A control instruction calls `setPc_p`, `setPc_p_j`, or `setPc_p_jr` in its IF formula.
- The same control instruction calls `setPc_c` in its MEM formula.
- The following instruction calls `getPc_mp()` and `getPc_pt()` in IF, resolving the previous control instruction.

Because of that:

- Prediction fields can describe the current control instruction when the current row itself is branch/jump.
- Redirect-source fields can describe a previous control instruction whose redirect is consumed by this row.
- No delayed row patching was implemented.

## Validation

Build/install command run successfully:

```bash
cmake --build etiss-perf-sim/etiss/build_dir --target SWEVAL_BACKENDS_LIB SoftwareEval install -j2
```

Requested validation command run successfully:

```bash
./scripts/run2.sh em:ud.riscv RC -ta=.llm_output/correction/test -tp=.llm_output/correction/test
```

Run result:

- Completed successfully.
- Number of instructions: `3618273`.
- Estimated processor cycles: `4246598`.
- Estimated CPI: `1.17365`.

Representative files inspected:

- `.llm_output/correction/test/asm_trace_0000.txt`
- `.llm_output/correction/test/RC_trace_0000.csv`
- `.llm_output/correction/test/RC_timing_0000.csv`

Timing CSV validation:

- Header contains `IF,ID,EX,MEM,WB` plus the new predictor fields.
- `RC_timing_0000.csv` has `22` columns.
- `190004` rows were checked in `RC_timing_0000.csv`; row lengths matched the header.
- Representative branch rows contain non-default predictor fields such as `BHT`, `BHT+BTB`, and `JAL`.
- Representative misprediction rows contain non-zero `branch_misprediction` and non-zero `IF_ext_Pc_mp`.
- Representative correctly predicted taken rows contain non-zero `IF_ext_Pc_pt`.

Example representative rows observed in `RC_timing_0000.csv`:

```text
102,103,104,105,106,2147483792,1,0,0,0,0,0,0,0,BHT,0,none,0,36,0,0,0
106,107,108,109,110,2147483812,1,1,0,1,0,1,0,2147483812,BHT,2147483792,BHT,0,36,0,106,0
143,144,145,146,147,2147483872,1,1,1,0,0,0,2147495228,2147495228,JAL,0,none,1,0,0,0,0
165,166,167,168,169,2147495228,1,1,1,0,0,0,2147495228,2147495228,JAL,0,none,1,0,0,0,143
```

## Limitations And Follow-Up Work

- Exact six BTB page-entry compression/replacement semantics are still not implemented.
- Return address push still uses `pc + 4`; compressed instruction length is not modeled.
- Trace rows are not patched after delayed branch resolution.
- The predictor is shared through `models/rocket/BranchPredictionModel`, so other variants using this model may see the new 1-bit BHT behavior after rebuild.
- `branch_predictor_component` is a plain CSV string and currently uses values such as `BHT`, `BHT+BTB`, `BTB`, `RAS`, `CALL`, `JALR`, and `JAL`.
- More precise validation should use focused branch/jump/call/return microbenchmarks in addition to `em:ud.riscv`.
