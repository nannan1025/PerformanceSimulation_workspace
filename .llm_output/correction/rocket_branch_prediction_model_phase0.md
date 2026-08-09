# Rocket Branch Prediction Model Phase 0 Analysis

This Phase 0 report is documentation only. It inspects the current Rocket, CVA6, and common dynamic branch predictor implementations and the generated Rocket scheduling connector usage before any code changes.

Primary sources:

- Rocket predictor header: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/rocket/BranchPredictionModel.h`
- Rocket predictor source: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/src/rocket/BranchPredictionModel.cpp`
- CVA6 predictor header/source: `externalModels/include/models/cva6/BranchPredictionModel.h`, `externalModels/src/cva6/BranchPredictionModel.cpp`
- Common dynamic predictor header/source: `externalModels/include/models/common/DynamicBranchPredictModel.h`, `externalModels/src/common/DynamicBranchPredictModel.cpp`
- Rocket scheduling connector usage: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_SchedulingFunction.cpp`
- Rocket CorePerfDSL reference: `.llm_output/correction/ROCKET_0716.corePerfDsl`

## Current Model Inspection

The current Rocket model already uses the same connector shape as CVA6:

```text
Pc_p, Pc_p_j, Pc_p_jr, Pc_c -> Pc_mp, Pc_pt
```

Meaning in the generated scheduler:

- `setPc_p(n_BPU)` is called by conditional branch scheduling functions during IF prediction.
- `setPc_p_j(n_BPU)` is called by `jal` during IF prediction.
- `setPc_p_jr(n_BPU)` is called by `jalr` during IF prediction.
- `setPc_c(n_Branch)` is called when the branch/jump resolve timing is computed in MEM.
- `getPc_mp()` is called at the beginning of every instruction's IF formula and can return a previous control-flow instruction's redirect/correction time.
- `getPc_pt()` is called after `getPc_mp()` in every instruction's IF formula and can return a previous correctly predicted taken timing.

Current Rocket predictor state:

- 512-entry BHT with 8-bit global history and 3-bit history hash in the index calculation.
- Current BHT entries are 2-bit saturating counters, initialized to `1`, and predict taken when `counter >= 2`.
- 28-entry BTB implemented as a fully scanned array of `{valid, pc, addr}` entries with simple next-replacement.
- 6-entry RAS implemented as a circular stack.
- Separate flags for pending conditional branch, direct jump, register jump, and return.

Important current gaps relative to the requested RocketConfig:

- The requested BHT has 1-bit prediction entries; the current Rocket model uses 2-bit counters.
- The requested BTB has six page entries; the current Rocket model has no BTB page table, page compression, or page replacement semantics.
- The current BTB does not store control-flow type.
- Current Rocket debug trace is limited compared with CVA6. It exposes `getInfo_mispredict()`, `getInfo_taken()`, and `getMispredict()`, but not detailed predictor component, direction-vs-target correctness, redirect source, BTB hit, BHT index, or RAS usage.

CVA6 is the closest software reference because it already implements:

- the same connector API;
- prediction/update separation;
- separate BHT, BTB, and RAS components;
- conditional branch, `jal`, and `jalr` paths;
- delayed evaluation through `getPc_mp()` / `getPc_pt()`;
- richer trace/debug getters.

The common dynamic predictor is useful only as a simple baseline:

- It has BHT and BTB maps plus a FIFO replacement depth.
- It does not model `jal`, `jalr`, calls, returns, RAS, target component source, or `Pc_mp` / `Pc_pt`.
- It chooses between `pc_p` and `pc_np`, so it is less suitable as the direct Rocket structure reference.

## 1. What Can Be Implemented Exactly?

The following items can be implemented directly with the trace values and connector timing currently available:

- A 28-entry BTB capacity.
- BTB lookup/update for indirect jump targets.
- A 512-entry BHT with 1-bit prediction entries.
- 8-bit global history.
- 3-bit history hash contribution to the BHT index.
- A 6-entry RAS.
- Distinct handling for:
  - conditional branches;
  - direct jumps;
  - indirect jumps;
  - calls;
  - returns.
- Separate state for:
  - predicted direction;
  - predicted target;
  - actual direction;
  - actual target;
  - direction correctness;
  - target correctness;
  - final misprediction.
- Existing timing connector behavior using:

```text
setPc_p
setPc_p_j
setPc_p_jr
setPc_c
getPc_mp
getPc_pt
```

The current CorePerfDSL trace values are enough for the first precise implementation of most predictor behavior:

- `pc`
- `brTarget`
- `imm`
- `rs1`
- `rd`

For `jal` and conditional branches, `brTarget` gives the target directly. For `jalr`, `brTarget` is already computed from `rs1 + imm` and masked by `& -2U` in the Rocket CorePerfDSL trace mapping.

## 2. What Must Be Approximated?

The following items cannot be implemented exactly from the current code and trace values without additional Rocket RTL/reference details or additional trace fields:

- Six BTB page-entry behavior:
  - The current model has no page table abstraction.
  - Exact tag compression, page replacement, and target reconstruction semantics need a Rocket RTL/reference definition.
- Full frontend fetch packet behavior:
  - The performance simulator schedules one instruction row at a time.
  - It does not naturally model multiple predictions inside one fetch packet.
- Exact actual next-PC source:
  - The current model evaluates previous control-flow correctness while scheduling the following instruction.
  - It infers actual outcome from the following instruction PC and stored target state.
- Compressed instruction return-address increment:
  - Current call handling uses `pc + 4`.
  - Exact compressed support requires instruction length or a reliable compressed-instruction flag.
- Precise row-local branch result reporting:
  - `getPc_mp()` and `getPc_pt()` evaluate the previous control-flow instruction while scheduling the next instruction.
  - Stamping final misprediction information onto the original branch row would require delayed row patching or a shifted reporting convention.

Recommended first approximation:

- Preserve existing delayed connector semantics.
- Report redirect-source information on the row where `Pc_mp` / `Pc_pt` is consumed.
- Avoid rewriting earlier timing rows.
- Implement six BTB page entries only after exact Rocket BTB page semantics are defined.

## 3. What Additional Trace Fields Or Connector Semantics Are Required?

No new timing connectors are required for the first implementation. The existing connector semantics should be preserved:

```text
Pc_p, Pc_p_j, Pc_p_jr, Pc_c -> Pc_mp, Pc_pt
```

Recommended additional predictor trace/debug fields, modeled after CVA6's debug style:

- `branch_is_control` or `predictor_is_control`
- `branch_taken`
- `branch_predicted_taken`
- `branch_direction_mispredict`
- `branch_target_mispredict`
- `branch_misprediction`
- `branch_predicted_target`
- `branch_actual_target`
- `branch_predictor_component`
- `branch_redirect_source_pc`
- `branch_redirect_source_type_id`
- `branch_redirect_source_component`
- `btb_hit`
- `bht_index`
- `ras_used`

Potential instruction identity trace additions:

- `typeId`, if stable numeric instruction-kind attribution is needed.
- instruction mnemonic, if the generated timing row should be readable without joining against the asm trace.

Important connector/trace distinction:

- `Pc_mp` and `Pc_pt` are timing connectors.
- Direction prediction, target prediction, BTB hit, RAS usage, and BHT index are debug/diagnostic trace fields.
- These debug fields should not change timing behavior by themselves.

Recommended reporting rule:

- Keep connector behavior stateful and delayed as it is today.
- Expose redirect-source fields so the row consuming `Pc_mp` can identify which earlier branch/jump caused the redirect.
- Do not attempt row-local final branch result reporting unless the timing trace writer gains delayed row patching support.

## 4. Which Files Will Be Modified Later?

Expected files for a later implementation:

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/rocket/BranchPredictionModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/src/rocket/BranchPredictionModel.cpp`

Files needed only if new predictor fields should appear in `ROCKET_timing_*.csv`:

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/include/ROCKET_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_PerformanceModel.cpp`

Optional files, only if adding new trace values such as `typeId`:

- `.llm_output/correction/ROCKET_0716.corePerfDsl`
- generated Rocket channel/printer/scheduler files after regeneration

Recommendation:

- Do not modify CorePerfDSL for the first implementation unless `typeId` or another missing trace value becomes necessary.
- Keep the first code implementation localized to the Rocket external branch predictor and, if desired, the timing trace output.

## 5. What Tests Will Validate Each Mechanism?

### Unit-Style Predictor Tests

If a small standalone predictor test harness is practical, validate:

- BHT learns repeated taken branches.
- BHT learns repeated not-taken branches.
- 1-bit BHT flips after each opposite outcome.
- Global history changes the BHT index.
- Direction mispredict and target mispredict are reported separately.
- BTB miss for first indirect jump target.
- BTB hit after indirect jump target update.
- BTB replacement after more than 28 distinct targets.
- RAS push on call.
- RAS pop on return.
- 6-entry RAS overflow behavior.
- Return with empty RAS reports invalid prediction / target miss.

### Simulator Trace Scenarios

Use small Rocket programs or focused trace snippets containing:

- Conditional branch taken.
- Conditional branch not taken.
- Repeated branch pattern to test BHT learning.
- Direct `jal`.
- `jalr` indirect jump.
- Call/return pair.
- Branch direction wrong but target known.
- Target wrong for `jalr`.
- Prediction-correct path where `Pc_pt` affects IF.
- Misprediction path where `Pc_mp` affects IF.

### CSV Validation

If timing trace fields are added:

- The timing CSV header includes the new predictor fields.
- All rows have the same column count as the header.
- `IF_ext_Pc_mp` and `IF_ext_Pc_pt` remain present.
- `branch_misprediction` or equivalent redirect fields reflect the delayed nature of branch evaluation.
- Branch timing changes only when the new predictor intentionally changes prediction correctness.

## Ambiguities And Clarifications Needed Before Code Changes

1. Exact six BTB page-entry semantics are not present in the current simulator.
   - Need Rocket RTL/reference behavior for page matching, page replacement, target reconstruction, and how page entries interact with the 28 BTB entries.

2. Requested BHT entries are 1-bit, but current Rocket simulator uses 2-bit counters.
   - If matching the target RocketConfig is the goal, switch to 1-bit entries.
   - If preserving current simulator behavior is the goal, keep 2-bit counters and document the mismatch.

3. Actual target for `jalr` is currently available as `brTarget` from the trace mapping, but actual control-flow correctness is still evaluated when the following instruction is scheduled.
   - Exact row-local attribution would need delayed row patching or a different trace convention.

4. Compressed instruction support requires instruction length.
   - Without instruction length, call return address should remain approximated as `pc + 4`.

5. The desired trace convention must be decided before implementation.
   - Safer first pass: report redirect-source fields on the consuming row.
   - More invasive pass: add delayed row patching so the original branch row can be updated after the next row is known.

## Assumptions

- This Phase 0 step is documentation only.
- No C++, CorePerfDSL, generated scheduler, build files, or traces are modified by this report.
- Later implementation should follow CVA6's software structure and debug-instrumentation style, but it must use Rocket-specific predictor parameters and semantics.
- The current generated Rocket scheduling connector timing should remain unchanged unless a later task explicitly requests timing changes.
