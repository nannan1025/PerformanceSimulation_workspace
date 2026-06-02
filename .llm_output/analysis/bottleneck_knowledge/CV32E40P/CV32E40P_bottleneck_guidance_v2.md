# CV32E40P Bottleneck Guidance v2

## Purpose

This report refines `CV32E40P_bottleneck_guidance_v1.md` with more concrete Performance Simulator workspace guidance. It focuses on how to improve or modify the CV32E40P performance model/code based on the current trace-based bottleneck results.

This is a guidance/report-only file. It does not modify simulator source code, rerun benchmarks, or implement new instrumentation.

## Inputs Used

- Static mechanism map: `.llm_output/analysis/bottleneck_knowledge/CV32E40P/bottleneck_knowledge_map.md`
- Runtime contribution summary: `.llm_output/analysis/bottleneck_knowledge/CV32E40P/contribution_analyzer.md`
- Instrumentation reports:
  - `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step1_trace_instrumentation.md`
  - `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step2_trace_instrumentation.md`
  - `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step3_trace_instrumentation.md`
  - `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step4_trace_instrumentation.md`
  - `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step5_trace_instrumentation.md`

Runtime numbers are from the current `em:ud` trace already summarized by `contribution_analyzer.md`.

## Interpretation Warning

The current runtime totals are additive instrumentation-field sums, not a de-overlapped CPI stack. A row may contribute to both functional-unit delay and a later RAW wait, so these numbers should guide investigation priority rather than be treated as exclusive root-cause cycle counts.

## Runtime Priority

| Priority | Bottleneck | Candidate ID | Runtime field | Current cycles | % attributed delay | Current action priority |
|---:|---|---|---|---:|---:|---|
| 1 | RAW/data dependency | `CV32-BN-001` | `raw_wait_cycles` | `1,138,886` | `45.13%` | Highest |
| 2 | Divider delay | `CV32-BN-003` | `divider_delay_cycles` | `969,568` | `38.42%` | Highest |
| 3 | Branch redirect | `CV32-BN-002` | `branch_redirect_cycles` | `289,343` | `11.47%` | Medium |
| 4 | Multiplier delay | `CV32-BN-005` | `multiplier_delay_cycles` | `125,630` | `4.98%` | Lower |
| 5 | Memory-port structural wait | `CV32-BN-004` | `memory_port_wait_cycles` | `0` | `0.00%` | Validate before optimizing |

## Workspace Modification Principles

Apply model changes in this order:

1. Prefer CorePerfDSL changes first because `code_gen/descriptions/core_perf_dsl/CV32E40P.corePerfDsl` is the source description of the generated backend.
2. Use external model changes when behavior belongs to a reusable model, such as register readiness, branch prediction, or divider delay.
3. Modify generated backend/monitor code only when the needed behavior cannot be expressed in CorePerfDSL or an external model.
4. Use analyzer/instrumentation changes for observability, validation, and de-overlap, not for changing modeled timing behavior.

## Detailed Guidance By Bottleneck

### `CV32-BN-001`: RAW Dependency Wait

Current evidence:

- Runtime field: `raw_wait_cycles`
- Current contribution: `1,138,886` cycles, rank 1.
- Step 3 instrumentation records `raw_wait_cycles`, `raw_blocking_reg`, and `raw_blocking_ready_cycle`, but not producer instruction ID.
- Static mechanism: operand microactions use connectors `Xa`, `Xb`, and `Xd` through `StandardRegisterModel`.

#### Proposed workspace changes

| Target bottleneck | Recommended modification level | Related files or components | Suggested change | Expected effect on timing/contribution | Validation method | Risk or uncertainty |
|---|---|---|---|---|---|---|
| RAW dependency wait | CorePerfDSL-level change | `code_gen/descriptions/core_perf_dsl/CV32E40P.corePerfDsl`; `Connector {Xa, Xb, Xd}`; `MicroactionMapping` for ALU, load, multiply, divide, branch, `jalr` | Review whether every instruction group has the correct source operand microactions. Remove `uA_OF_A` or `uA_OF_B` only for groups that truly do not read that source; add missing source microactions if any group is under-modeled. | Reduces false RAW waits if an unused source is modeled as used; improves accuracy if missing operands were hiding waits. | Regenerate backend, rebuild, rerun targeted operand-use microbenchmarks; check `uses_rs1/uses_rs2` and `raw_wait_cycles` against expected operand usage. | Incorrect operand mapping can make timing optimistic or pessimistic; generated code will change broadly after CorePerfDSL regeneration. |
| RAW dependency wait | CorePerfDSL-level change | `CV32E40P.corePerfDsl`; resource/microaction definitions for `uA_ALU_RegUpdate`, `uA_Memory_R`, `uA_MUL`, `uA_MULH`, `uA_DIV`, `uA_DIVU` | Consider modeling forwarding/bypass as explicit alternative connector timing if CorePerfDSL supports a bypass-ready connector earlier than `Xd`. For example, separate result-ready timing from architectural writeback timing. | Could reduce RAW wait where hardware forwards results before full writeback; would lower `raw_wait_cycles` and possibly total cycles. | Compare dependent ALU, load-use, mul-use, and div-use microbenchmarks before/after; verify only intended producer-consumer pairs improve. | Requires confirming CorePerfDSL supports the desired connector semantics; wrong bypass modeling can understate real hazards. |
| RAW dependency wait | External-model-level change | `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/common/StandardRegisterModel.h`; class `common::StandardRegisterModel`; methods `getXa`, `getXb`, `setXd` | Add explicit `rd == 0` handling in `setXd` so writes to `x0` do not update readiness; optionally make register count RV32-specific or document why array size is 64. | Removes possible false dependencies through register zero; can reduce false `raw_wait_cycles` in traces with writes to `x0`. | Run a microbenchmark that writes to `x0` followed by reads of `x0`; expected RAW wait should remain zero. | Shared model may be used by other processors; changing it can affect non-CV32E40P variants unless guarded or validated globally. |
| RAW dependency wait | External-model-level change | `StandardRegisterModel.h`; potential new producer metadata arrays | Track producer instruction ID, producer PC, and producer type ID alongside ready cycle for each destination register. Expose metadata through CV32E40P performance model or trace instrumentation. | Does not directly change timing, but enables correct de-overlap and root-cause analysis of RAW waits. | Rerun contribution analyzer on dependent chains; verify `raw_blocking_instruction_id` points to the expected producer. | Requires channel/performance-model trace additions; metadata must stay aligned with `instrIndex`. |
| RAW dependency wait | Analyzer/instrumentation-level change | `.llm_output/analysis/bottleneck_knowledge/CV32E40P/analyze_cv32e40p_contribution.py`; Step 3 timing fields | Split RAW wait by producer class once producer metadata exists: RAW-after-divider, RAW-after-load, RAW-after-multiply, RAW-after-ALU. | Does not change timing; prevents over-prioritizing RAW separately from the long-latency producer that caused it. | Check that total RAW wait remains unchanged while subcategories sum to the original RAW total. | Cannot be accurate until producer identity exists. |

Recommended first action:

- Inspect CorePerfDSL operand mappings for false source dependencies, then add `rd == 0` handling and producer metadata in `StandardRegisterModel`.

### `CV32-BN-003`: Variable Divider Latency

Current evidence:

- Runtime field: `divider_delay_cycles`
- Current contribution: `969,568` cycles, rank 2.
- Top contributor in the current analyzer is type ID `25`.
- Static mechanism: `Resource {DIV(divider), DIVU(divider_u)}` uses CV32E40P external divider models with `rs2_data`.

#### Proposed workspace changes

| Target bottleneck | Recommended modification level | Related files or components | Suggested change | Expected effect on timing/contribution | Validation method | Risk or uncertainty |
|---|---|---|---|---|---|---|
| Divider delay | CorePerfDSL-level change | `CV32E40P.corePerfDsl`; `Resource {DIV(divider), DIVU(divider_u)}`; `MicroactionMapping` for `Div_Ra_Rb`, `DivU_Ra_Rb` | Confirm `div`, `rem`, `divu`, and `remu` are mapped to the intended signed/unsigned divider resources. If the target architecture should distinguish `div` from `rem` latency, split instruction groups and resource models. | More accurate per-opcode divider timing; may redistribute or change `divider_delay_cycles`. | Run targeted `div`, `rem`, `divu`, `remu` microbenchmarks and confirm each opcode maps to the expected resource and delay. | Splitting groups changes generated scheduler and trace type IDs; analyzer mappings may need updates. |
| Divider delay | CorePerfDSL-level change | `CV32E40P.corePerfDsl`; `TraceValue {rs2_data}` and `TraceValueMapping` for divider groups | Add trace values for `rs1_data`, signed/unsigned divider kind, or divisor classification if CorePerfDSL trace mapping can express them. | Timing may not change, but model validation becomes much easier and divider delay can be explained by operand pattern. | Check timing CSV or trace output contains the new fields; compare delay against expected divisor classes. | Extra trace fields require backend/printer/monitor regeneration and may increase trace size. |
| Divider delay | External-model-level change | `DividerModel.cpp`; `DividerUnsignedModel.cpp`; methods `getDelay`, `findReverseOneIndex` | Parameterize delay constants currently implied by `delay += 1` or `delay += 3`, and by leading-one behavior. Use config or constructor parameters if supported by the model infrastructure. | Enables experiments with faster/slower divider designs; should directly change `divider_delay_cycles`. | Run the analyzer before/after parameter changes on divider microbenchmarks; verify divider category changes while unrelated categories remain stable except RAW follow-on effects. | Config plumbing may not exist for these resource models; hard-coding parameters risks generated/deploy inconsistencies. |
| Divider delay | External-model-level change | `DividerModel.cpp`; signed operand handling in `getDelay` | Validate signed operand handling against CV32E40P hardware documentation or reference model. Current code inverts signed operands and computes delay from the transformed value. | Corrects divider delay if the current heuristic does not match intended hardware. | Generate operand-sweep microbenchmarks over positive, negative, zero, and high-bit divisors; compare delay outputs to expected model. | Hardware timing may not be documented; changes can invalidate previous calibration. |
| Divider delay | Analyzer/instrumentation-level change | Step 2 timing fields; `analyze_cv32e40p_contribution.py` | Report divider contribution by signed/unsigned kind and by exact opcode after joining with decoded trace rows. | Does not change timing; makes it clear whether `div`, `rem`, `divu`, or `remu` should be optimized first. | Cross-check joined opcode counts against `CV32E40P_trace_*.csv` and timing row counts. | Joining assumes row-order alignment between timing and decoded traces. |

Recommended first action:

- Keep timing behavior in the external divider models, but make the CorePerfDSL grouping and trace values precise enough to validate which divider operation patterns dominate.

### `CV32-BN-002`: Static Branch Redirect

Current evidence:

- Runtime field: `branch_redirect_cycles`
- Current contribution: `289,343` cycles, rank 3.
- Static mechanism: `staBranchPredModel` always predicts not-taken; Step 4 added runtime branch outcome tracing without changing predictor behavior.

#### Proposed workspace changes

| Target bottleneck | Recommended modification level | Related files or components | Suggested change | Expected effect on timing/contribution | Validation method | Risk or uncertainty |
|---|---|---|---|---|---|---|
| Branch redirect | CorePerfDSL-level change | `CV32E40P.corePerfDsl`; `ConnectorModel staBranchPredModel`; connectors `{Pc, Pc_np, Pc_p}`; microactions `uA_PCGen`, `uA_ALU_Branch`, `uA_JumpDecode`, `uA_JumpDecodeReg` | Keep branch timing structure in CorePerfDSL, but consider replacing `staBranchPredModel` binding with a configurable predictor connector model if the generator supports selecting a different model. | Enables comparing static and dynamic predictor timing without editing generated backend code. | Regenerate with alternative predictor binding; run branch microbenchmarks and verify `branch_redirect_cycles` drops for predictable taken branches. | Needs compatible connector interface; predictor model may need additional trace state. |
| Branch redirect | CorePerfDSL-level change | `CV32E40P.corePerfDsl`; stage definitions for `ID_stage` and `EX_stage`; branch microactions | If modeling an architecture variant with earlier branch resolution, move or split branch decision microaction so redirect is produced earlier than current `uA_ALU_Branch` timing. | Could reduce `branch_redirect_cycles` by shortening `n_ALU - n_PCGen` or equivalent redirect proxy. | Use taken/not-taken branch microbenchmarks; check redirect cycle per taken conditional branch changes as expected. | This changes architecture timing assumptions, not just instrumentation; should only be done if the target CV32E40P variant actually resolves earlier. |
| Branch redirect | External-model-level change | `StaticBranchPredictModel.cpp`; class `common::StaticBranchPredictModel`; methods `setPc_p`, `setPc_np`, `getPc` | Create a new predictor model rather than modifying static behavior in place: e.g., `ConfigurableBranchPredictModel` or simple 1-bit/2-bit predictor with same connector inputs/outputs. | Predictable taken branches can stop paying static-not-taken redirect cost; `branch_redirect_cycles` should decrease for loops. | Run branch-pattern microbenchmarks: always taken, never taken, alternating, loop backedge. Compare predicted/mispredict counts. | `getPc()` mutates predictor state; instrumentation must avoid extra calls. Shared predictor changes can affect other processors if not isolated. |
| Branch redirect | Generated-code-level change | Base CV32E40P generated scheduler lambdas for type IDs `43-48`, `50`, `51`; `CV32E40P_PerformanceModel::setBranchInstrumentation` | Only use generated-code edits if CorePerfDSL/external predictor cannot expose needed timing. Add fields for predicted PC, actual PC, redirect source stage, and branch class. | Usually improves observability, not timing; helps determine whether redirect cycles are due to conditional branches or jumps. | Validate taken conditional rows have mispredicts under static policy, not-taken rows do not, and jumps remain always taken. | Generated scheduler edits can be overwritten by codegen. |
| Branch redirect | Analyzer/instrumentation-level change | `analyze_cv32e40p_contribution.py`; Step 4 fields | Add branch breakdown by type ID and branch kind: conditional taken, conditional not-taken, `jal`, `jalr`. | Does not change timing; improves guidance by separating branch categories. | Recompute totals and verify branch subcategories sum to `branch_redirect_cycles`. | Requires reliable type ID to opcode mapping or trace join. |

Recommended first action:

- Keep the current static predictor as baseline, then add a separate configurable/dynamic predictor external model and switch to it through CorePerfDSL if supported.

### `CV32-BN-005`: Multiplier and High-Multiplier Latency

Current evidence:

- Runtime field: `multiplier_delay_cycles`
- Current contribution: `125,630` cycles, rank 4.
- Static mechanism: `Resource {MUL, MULH(5)}` and `uA_MUL`/`uA_MULH` in CorePerfDSL.

#### Proposed workspace changes

| Target bottleneck | Recommended modification level | Related files or components | Suggested change | Expected effect on timing/contribution | Validation method | Risk or uncertainty |
|---|---|---|---|---|---|---|
| Multiplier latency | CorePerfDSL-level change | `CV32E40P.corePerfDsl`; `Resource {MUL, MULH(5)}` | Parameterize or adjust `MULH(5)` only if modeling a variant with different high-multiply latency. Consider changing `MUL` latency if CorePerfDSL syntax supports explicit latency for `MUL`. | Directly changes generated multiply scheduling and `multiplier_delay_cycles`. | Run multiply microbenchmarks for `mul`, `mulh`, `mulhu`, `mulhsu`; verify per-row delay equals intended latency. | Changing CorePerfDSL affects generated scheduler and may change type IDs or generated code shape after regeneration. |
| Multiplier latency | CorePerfDSL-level change | `MicroactionMapping`; `Mul_Ra_Rb`, `MulH_Ra_Rb` groups | Split multiply groups further if exact opcodes need distinct latency or resource behavior. | More accurate multiplier timing and contribution attribution by opcode. | Validate each multiply opcode with targeted traces; compare analyzer top type IDs/opcodes. | More groups increase generated code and analyzer mapping complexity. |
| Multiplier latency | External-model-level change | New or existing resource model for multiplier if introduced; currently no separate CV32E40P multiplier external model found | If latency should depend on operands or configuration, replace static resource latency with a multiplier resource model similar to divider. | Allows operand-dependent or configurable multiplier timing; may change `multiplier_delay_cycles`. | Operand-sweep multiply microbenchmarks; verify delay follows the intended model. | Adds model complexity for a currently lower-priority bottleneck. |
| Multiplier latency | Analyzer/instrumentation-level change | Step 2 fields; `analyze_cv32e40p_contribution.py` | Split multiplier report into `MUL` and `MULH` classes and join type IDs to opcode names. | Does not change timing; clarifies whether high-multiply latency is actually important in the current workload. | Check subcategory totals sum to existing `multiplier_delay_cycles`. | Requires stable type ID/opcode mapping. |

Recommended first action:

- Do not prioritize multiplier timing changes for the current `em:ud` trace unless a multiply-heavy benchmark shows larger contribution. If needed, start with CorePerfDSL resource latency changes.

### `CV32-BN-004`: Memory-Port / LSU Structural Timing

Current evidence:

- Runtime field: `memory_port_wait_cycles`
- Current contribution: `0` cycles, rank 5.
- Current trace contains memory rows: `DPort_R = 283,175`, `DPort_W = 123,481`, but max `memory_port_wait_cycles` is `0`.
- Static mechanism: `Resource {IPort_R, DPort_R, DPort_W}`, `uA_LSU`, `uA_Memory_R`, `uA_Memory_W`; no CV32E40P cache model found.

#### Proposed workspace changes

| Target bottleneck | Recommended modification level | Related files or components | Suggested change | Expected effect on timing/contribution | Validation method | Risk or uncertainty |
|---|---|---|---|---|---|---|
| Memory-port structural wait | CorePerfDSL-level change | `CV32E40P.corePerfDsl`; `Resource {IPort_R, DPort_R, DPort_W}`; `uA_LSU`, `uA_Memory_R`, `uA_Memory_W`; `Load`, `Store` mappings | First verify whether the current single DPort read/write resource model matches intended CV32E40P. If modeling a structural conflict, keep shared DPort constraints; if modeling independent paths, split resources. | May increase or reduce memory-port wait depending on resource topology; should affect `memory_port_wait_cycles` and stage timing for memory-heavy traces. | Create targeted back-to-back load/store microbenchmarks; verify DPort wait appears only when modeled structural conflict should occur. | Current `em:ud` does not activate this wait, so validation requires a new targeted trace. |
| Memory-port structural wait | CorePerfDSL-level change | `TraceValue` and `TraceValueMapping` for `Load` and `Store` | Add effective address and access size trace values if CorePerfDSL can express them. Current base trace lacks memory address. | Does not directly change timing, but enables real memory attribution and cache-model validation later. | Confirm trace contains address/size for load/store rows; compare against assembly expectations. | Trace expression for effective address may require reading `rs1` data and immediate fields correctly. |
| Memory-port / memory hierarchy | External-model-level change | Potential new cache/memory resource model; no base CV32E40P cache model currently linked | Add an explicit memory/cache model only if CV32E40P should include memory hierarchy timing. Bind it from CorePerfDSL as a resource model rather than hand-editing generated scheduler. | Adds memory wait cycles beyond DPort structural wait; may reveal memory bottlenecks absent from current model. | Run hit/miss microbenchmarks and verify new `memory_wait_cycles` or cache fields. | Without hardware target parameters, cache model may become speculative. |
| Memory-port structural wait | Generated-code-level change | `CV32E40P_SchedulingFunction.cpp`; `CV32E40P_PerformanceModel::setMemoryPortInstrumentation` | Avoid changing generated code for timing. Use it only if CorePerfDSL cannot express a temporary experimental trace hook. | Mostly improves observability; generated edits may not survive regeneration. | Rebuild and confirm header/rows still align; rerun memory stress test. | High overwrite risk from code generation. |
| Memory-port structural wait | Analyzer/instrumentation-level change | Step 5 fields; `analyze_cv32e40p_contribution.py` | Keep reporting `DPort_R`, `DPort_W`, and `none` row counts. Add warnings when memory rows exist but wait is zero, as in current trace. | Does not change timing; prevents false conclusions that memory has no role in the program. | Analyzer should report row counts and zero wait clearly. | Cannot infer cache/memory latency without additional fields. |

Recommended first action:

- Do not optimize memory-port timing based on the current trace. First add or run a targeted memory stress benchmark; then consider CorePerfDSL resource topology or new memory/cache model only if positive wait is observed or required by the intended hardware model.

## Cross-Cutting Workspace Improvements

| Recommended modification level | Related files or components | Suggested change | Expected effect | Validation method | Risk or uncertainty |
|---|---|---|---|---|---|
| CorePerfDSL-level change | `CV32E40P.corePerfDsl`; generated backend under `variants/CV32E40P` | Treat CorePerfDSL as the source of truth. After any CorePerfDSL timing/resource change, regenerate the backend and compare generated scheduler diffs. | Keeps model changes reproducible and avoids hand-maintained generated code. | Run code generation, rebuild, and compare timing CSV headers plus selected microbenchmark timing. | Regeneration may overwrite Step 1-5 hand instrumentation unless instrumentation is also integrated into templates or reapplied. |
| External-model-level change | `StandardRegisterModel`, `StaticBranchPredictModel`, divider models | Put reusable timing policy in external models when it depends on dynamic state or operands. | Keeps generated scheduler simpler and makes policy experiments easier. | Unit-like microbenchmarks for each external model behavior. | Shared external models may affect multiple cores unless cloned or guarded. |
| Analyzer/instrumentation-level change | `analyze_cv32e40p_contribution.py`; Step 1-5 trace fields | Add a de-overlap pass once producer IDs and explicit stall reasons exist. | Converts additive guidance into closer root-cause attribution. | Verify category totals are stable and de-overlapped total does not exceed observed cycle envelope by construction. | Requires additional instrumentation; current fields are not enough for exact root-cause attribution. |
| Analyzer/instrumentation-level change | Timing trace plus decoded trace files | Join timing rows with decoded instruction/opcode names and source locations. | Makes top type IDs and PCs actionable for source or assembly optimization. | Validate row count and `pc` alignment between timing and trace files. | Row-order mismatches or rotated files can break joins if not handled carefully. |

## Recommended Order Of Work

1. RAW: inspect CorePerfDSL operand mappings; then fix `StandardRegisterModel` `rd == 0` behavior and add producer metadata.
2. Divider: validate CorePerfDSL grouping and external divider model behavior with operand-sweep microbenchmarks; then parameterize delay if experimenting with faster divider designs.
3. Branch: keep static predictor baseline; add a separate configurable/dynamic predictor external model and bind it through CorePerfDSL if supported.
4. Multiplier: only tune CorePerfDSL `MUL`/`MULH` latency after a multiply-heavy benchmark justifies it.
5. Memory-port: do not optimize current DPort timing from `em:ud`; first use targeted memory stress traces and add address/size observability.

## Final Notes

- This report is for the base `CV32E40P` model only, not `CV32E40P_CORE`, `CV32E40P_LLM`, `CV32E40P_QWEN_1`, CVA6, or other variants.
- Current guidance uses already-generated reports and current trace summaries; it does not claim a benchmark-wide bottleneck diagnosis beyond the current trace.
- Any CorePerfDSL or external-model change should be validated with focused microbenchmarks before using it to interpret broad benchmark results.
