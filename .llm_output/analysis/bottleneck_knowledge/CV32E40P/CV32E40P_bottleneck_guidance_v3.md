# CV32E40P Bottleneck Guidance v3

## Purpose

This report combines and filters `CV32E40P_bottleneck_guidance_v1.md` and `CV32E40P_bottleneck_guidance_v2.md`.

The v3 rule is stricter: every recommended Performance Simulator model/code modification must correspond to a plausible CV32E40P hardware or architecture modification. If a simulator change only improves observability, trace clarity, analyzer convenience, or de-overlapped accounting, it is not treated as a performance-model improvement.

This report does not modify simulator source code, rerun benchmarks, or implement instrumentation.

## Inputs Used

- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/CV32E40P_bottleneck_guidance_v1.md`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/CV32E40P_bottleneck_guidance_v2.md`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/bottleneck_knowledge_map.md`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/contribution_analyzer.md`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step1_trace_instrumentation.md`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step2_trace_instrumentation.md`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step3_trace_instrumentation.md`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step4_trace_instrumentation.md`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step5_trace_instrumentation.md`

Runtime numbers are from the current `em:ud` trace already summarized in `contribution_analyzer.md`.

## Rule: Simulator Change Must Map To Hardware Change

Recommended simulator modifications in this report must satisfy both conditions:

1. The change models a plausible hardware/architecture modification for CV32E40P.
2. The expected timing change is visible through the performance model, such as changed RAW wait, divider delay, branch redirect cycles, multiplier latency, or memory-port wait.

Instrumentation-only and analyzer-only changes can still be useful for validation, but they are not model-improvement recommendations unless paired with a hardware change.

## Runtime Priority

| Priority | Bottleneck | Candidate ID | Runtime field | Current cycles | % attributed delay | v3 action |
|---:|---|---|---|---:|---:|---|
| 1 | RAW/data dependency | `CV32-BN-001` | `raw_wait_cycles` | `1,138,886` | `45.13%` | Keep hardware-mapped model changes |
| 2 | Divider delay | `CV32-BN-003` | `divider_delay_cycles` | `969,568` | `38.42%` | Keep hardware-mapped model changes |
| 3 | Branch redirect | `CV32-BN-002` | `branch_redirect_cycles` | `289,343` | `11.47%` | Keep hardware-mapped model changes |
| 4 | Multiplier latency | `CV32-BN-005` | `multiplier_delay_cycles` | `125,630` | `4.98%` | Keep only if modeling multiplier hardware |
| 5 | Memory-port structural wait | `CV32-BN-004` | `memory_port_wait_cycles` | `0` | `0.00%` | Low priority; validate before modeling changes |

The additive totals above are not a de-overlapped CPI stack. They are used only to prioritize investigation.

## Main Hardware-Mapped Recommendations

### `CV32-BN-001`: RAW Dependency Wait

Current evidence:

- Runtime contribution: `1,138,886` cycles, rank 1.
- Runtime field: `raw_wait_cycles`.
- Static mechanism: source operand readiness is modeled through `Xa`, `Xb`, and `Xd` connectors and `StandardRegisterModel`.

| Hardware / architecture modification | Corresponding simulator modification | Modification level | Target files/components | Expected timing effect | Validation method | Risk or uncertainty | v3 decision |
|---|---|---|---|---|---|---|---|
| Add or improve forwarding/bypass so consumers can use producer results before architectural writeback. | Model earlier result availability through CorePerfDSL connector/microaction timing, or through a register readiness model that distinguishes forwarded-ready cycle from writeback-ready cycle. | CorePerfDSL-level first; external-model-level if readiness policy is dynamic. | `code_gen/descriptions/core_perf_dsl/CV32E40P.corePerfDsl`; connectors `Xa`, `Xb`, `Xd`; microactions `uA_ALU_RegUpdate`, `uA_Memory_R`, `uA_MUL`, `uA_MULH`, `uA_DIV`, `uA_DIVU`; `StandardRegisterModel.h`. | Should reduce `raw_wait_cycles` for dependent ALU/load/mul/div chains where forwarding is valid. | Run dependent producer-consumer microbenchmarks for ALU, load-use, multiply-use, and divide-use chains; compare `raw_wait_cycles` before/after. | Must avoid optimistic timing for cases that cannot be forwarded, especially load-use and long-latency units. | Keep |
| Correct architectural zero-register dependency behavior: writes to `x0` must not create a producer readiness dependency. | Update register readiness semantics so `setXd` ignores `rd == 0`, matching RISC-V architectural `x0`. | External-model-level. | `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/common/StandardRegisterModel.h`; `common::StandardRegisterModel::setXd`. | Removes false RAW waits through `x0`; can reduce `raw_wait_cycles` if such false dependencies occur. | Microbenchmark: write to `x0`, then read `x0`; expected `raw_wait_cycles = 0`. Also rerun current trace to confirm no unintended regression. | `StandardRegisterModel` may be shared by other cores; validate shared users or clone/guard the behavior if needed. | Keep |
| Refine scoreboard/readiness semantics to match CV32E40P producer-result timing. | Move readiness update timing in CorePerfDSL or external model so each producer class exposes the architecture-accurate ready cycle. | CorePerfDSL-level first; external-model-level if producer-specific state is needed. | `CV32E40P.corePerfDsl` mappings for ALU/load/mul/div producers; `StandardRegisterModel.h`. | Changes RAW contribution distribution by matching true hardware producer availability. | Use focused microbenchmarks with known expected latency for each producer class; verify `raw_wait_cycles` and total cycles. | Requires hardware timing knowledge; wrong ready-cycle choice distorts many instructions. | Keep |

Do not treat these as model-improvement recommendations:

- Producer instruction ID tracing.
- RAW de-overlap analyzer logic.
- Opcode/name joins for reports.

These are measurement and explanation improvements. They help validate RAW behavior, but they do not correspond to a hardware architecture change by themselves.

### `CV32-BN-003`: Variable Divider Latency

Current evidence:

- Runtime contribution: `969,568` cycles, rank 2.
- Runtime field: `divider_delay_cycles`.
- Static mechanism: `DIV(divider)` and `DIVU(divider_u)` resource models compute delay from `rs2_data`.

| Hardware / architecture modification | Corresponding simulator modification | Modification level | Target files/components | Expected timing effect | Validation method | Risk or uncertainty | v3 decision |
|---|---|---|---|---|---|---|---|
| Use a faster divider implementation with fewer cycles per operation. | Change delay formula or parameters in the CV32E40P divider resource models. | External-model-level. | `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/src/cv32e40p/DividerModel.cpp`; `DividerUnsignedModel.cpp`; methods `getDelay`, `findReverseOneIndex`. | Directly reduces `divider_delay_cycles`; may also reduce later RAW waits from divider consumers. | Operand-sweep microbenchmarks for `div`, `rem`, `divu`, `remu`; compare delay and analyzer totals before/after. | Must be calibrated to a real target divider design; arbitrary lower constants are not valid architecture modeling. | Keep |
| Change divider early-out behavior for specific divisor patterns. | Modify `getDelay()` leading-one or zero-divisor handling to match the intended hardware early-out rule. | External-model-level. | `DividerModel.cpp`; `DividerUnsignedModel.cpp`. | Redistributes divider delay by operand value; can reduce contribution for common divisor patterns. | Sweep divisors including zero, powers of two, high-bit values, negative signed values, and random values; verify expected delay buckets. | Current signed behavior inverts negative operands; hardware documentation is needed before changing it. | Keep |
| Distinguish signed/unsigned or div/rem hardware timing if the architecture does. | Split CorePerfDSL instruction groups and/or bind separate divider resource models for operations with different hardware timing. | CorePerfDSL-level plus external-model-level if separate models are needed. | `CV32E40P.corePerfDsl`; `Div_Ra_Rb`, `DivU_Ra_Rb`; `Resource {DIV(divider), DIVU(divider_u)}`. | More accurate opcode-specific `divider_delay_cycles`; may change which instructions dominate. | Microbenchmarks for each opcode; verify each opcode maps to intended resource and expected delay. | Splitting groups may change generated type IDs and require analyzer/report mapping updates. | Keep |

Do not treat these as model-improvement recommendations:

- Extra divisor-class trace fields.
- Analyzer opcode breakdown.
- Linking divider rows with RAW rows for de-overlap.

These are validation and explanation improvements. They should support a divider model change, not replace the hardware-mapped model change.

### `CV32-BN-002`: Static Predict-Not-Taken Branch Redirect

Current evidence:

- Runtime contribution: `289,343` cycles, rank 3.
- Runtime field: `branch_redirect_cycles`.
- Static mechanism: current branch model is static predict-not-taken; taken conditional branches and jumps generate redirect timing.

| Hardware / architecture modification | Corresponding simulator modification | Modification level | Target files/components | Expected timing effect | Validation method | Risk or uncertainty | v3 decision |
|---|---|---|---|---|---|---|---|
| Replace static predict-not-taken with a simple dynamic branch predictor. | Add a compatible predictor external model and bind it from CorePerfDSL instead of `staBranchPredModel`. | External-model-level plus CorePerfDSL-level binding. | `code_gen/descriptions/core_perf_dsl/CV32E40P.corePerfDsl`; `ConnectorModel staBranchPredModel`; `StaticBranchPredictModel.cpp` as baseline; new predictor model if implemented. | Reduces `branch_redirect_cycles` for predictable taken branches and loops. | Branch-pattern microbenchmarks: always taken, never taken, alternating, loop backedge; verify mispredict and redirect reductions. | Predictor state must be updated without extra `getPc()` calls that mutate state unexpectedly. | Keep |
| Add target prediction / BTB-like behavior. | Extend or replace the branch predictor model so predicted target is available through the same PC connector semantics. | External-model-level plus CorePerfDSL-level binding. | Branch predictor external model; CorePerfDSL connector model for `{Pc, Pc_np, Pc_p}`. | Reduces redirect penalty for taken branches and jumps if target is predicted earlier. | Microbenchmarks with repeated taken branches and jumps; compare `branch_redirect_cycles` before/after. | Current trace fields may not fully distinguish direction miss vs target miss without extra validation fields. | Keep |
| Resolve conditional branches earlier in the pipeline. | Move/split branch decision microaction in CorePerfDSL so redirect is produced earlier than current `uA_ALU_Branch` timing. | CorePerfDSL-level. | `CV32E40P.corePerfDsl`; `uA_ALU_Branch`; `ID_stage`, `EX_stage`; `Branch_Ra_Rb` mapping. | Shortens redirect proxy and should lower `branch_redirect_cycles` per taken conditional branch. | Taken/not-taken branch microbenchmarks; verify redirect cycles change by the expected stage distance. | This is a real architecture timing change and should only be used for a CV32E40P variant that actually resolves earlier. | Keep |

Do not treat these as model-improvement recommendations:

- Branch breakdown by type ID in analyzer.
- Predicted-PC or actual-next-PC trace fields.
- Extra instrumentation-only branch fields.

These help validate branch behavior, but they are not hardware changes unless paired with a predictor or pipeline-stage timing change.

### `CV32-BN-005`: Multiplier and High-Multiplier Latency

Current evidence:

- Runtime contribution: `125,630` cycles, rank 4.
- Runtime field: `multiplier_delay_cycles`.
- Static mechanism: CorePerfDSL declares `Resource {MUL, MULH(5)}` and maps multiply instruction groups to `uA_MUL` and `uA_MULH`.

| Hardware / architecture modification | Corresponding simulator modification | Modification level | Target files/components | Expected timing effect | Validation method | Risk or uncertainty | v3 decision |
|---|---|---|---|---|---|---|---|
| Lower high-multiply latency. | Change the CorePerfDSL `MULH(5)` resource latency to the target hardware latency. | CorePerfDSL-level. | `code_gen/descriptions/core_perf_dsl/CV32E40P.corePerfDsl`; `Resource {MUL, MULH(5)}`. | Directly changes `multiplier_delay_cycles` for high-multiply operations and may reduce RAW waits from high-multiply consumers. | Microbenchmarks for `mulh`, `mulhu`, `mulhsu`; verify per-row delay equals intended latency. | Current trace top multiplier contributor is type ID `21`; confirm whether high-multiply is important before prioritizing this. | Keep, lower priority |
| Change ordinary multiply latency or throughput. | Add explicit `MUL` latency in CorePerfDSL if syntax supports it, or introduce an external multiplier model if latency is dynamic. | CorePerfDSL-level first; external-model-level only for dynamic behavior. | `CV32E40P.corePerfDsl`; `Resource {MUL, MULH(5)}`; possible multiplier resource model. | Changes `multiplier_delay_cycles` for `mul`; may affect RAW waits after multiply. | Multiply-heavy microbenchmark; verify `mul` row delay and total cycles change as expected. | Must reflect actual hardware multiplier design, not just a simulator tuning knob. | Keep, lower priority |
| Pipeline multiplier for throughput. | Model multiplier occupancy/throughput separately from latency if CorePerfDSL/resource model supports pipelined resources. | CorePerfDSL-level or external resource-model-level. | `CV32E40P.corePerfDsl`; multiplier resource declarations; possible external model. | Reduces structural contention in multiply-heavy streams if modeled; may not reduce single multiply latency. | Back-to-back multiply microbenchmarks and dependent multiply-chain microbenchmarks; compare throughput vs latency effects. | Current model may not distinguish latency and throughput; implementation feasibility depends on resource semantics. | Keep only if target hardware is pipelined |

Do not treat these as model-improvement recommendations:

- Joining type IDs to opcode names.
- Report-only split of `MUL` vs `MULH`.

These are useful validation/reporting steps, but not architecture modifications.

### `CV32-BN-004`: Memory-Port / LSU Structural Timing

Current evidence:

- Runtime contribution: `0` cycles, rank 5.
- Runtime field: `memory_port_wait_cycles`.
- Current trace contains memory rows: `DPort_R = 283,175`, `DPort_W = 123,481`.
- Current trace did not activate positive memory-port structural wait.

| Hardware / architecture modification | Corresponding simulator modification | Modification level | Target files/components | Expected timing effect | Validation method | Risk or uncertainty | v3 decision |
|---|---|---|---|---|---|---|---|
| Separate load and store datapaths or change DPort resource topology. | Change CorePerfDSL resource topology for `DPort_R`, `DPort_W`, `LSU`, or related memory microactions to match the target hardware. | CorePerfDSL-level. | `code_gen/descriptions/core_perf_dsl/CV32E40P.corePerfDsl`; `Resource {IPort_R, DPort_R, DPort_W}`; `uA_LSU`, `uA_Memory_R`, `uA_Memory_W`; `Load`, `Store` mappings. | Could change `memory_port_wait_cycles` and memory instruction stage timing in memory-heavy traces. | Back-to-back load/store stress microbenchmarks; verify wait appears or disappears according to expected resource conflicts. | Current `em:ud` has zero memory-port wait, so this is not justified by current runtime result alone. | Keep only after targeted memory trace shows need |
| Add store buffering or LSU buffering. | Model buffer behavior through CorePerfDSL resource/microaction timing or an external LSU/resource model if dynamic state is needed. | CorePerfDSL-level for simple timing; external-model-level for dynamic buffering. | `CV32E40P.corePerfDsl`; possible new LSU resource model. | May reduce store-related blocking and alter `memory_port_wait_cycles` in store-heavy workloads. | Store-heavy microbenchmarks with dependent and independent stores; compare DPort wait and total cycles. | Requires actual target architecture support; otherwise speculative. | Keep only if modeling a buffered CV32E40P variant |
| Add real cache or memory hierarchy latency. | Add a memory/cache resource model and bind it from CorePerfDSL only if the target CV32E40P configuration includes such hierarchy timing. | External-model-level plus CorePerfDSL-level binding. | New memory/cache model; `CV32E40P.corePerfDsl` resource model binding; load/store mappings. | Adds memory wait beyond structural DPort wait; may introduce nonzero memory contribution. | Hit/miss microbenchmarks and address-pattern tests; validate expected hit/miss delay. | Without known cache/memory parameters, this would be speculative and should not be recommended. | Keep only with hardware target parameters |

Do not treat these as model-improvement recommendations:

- Adding effective address trace fields by itself.
- Adding memory operation size trace fields by itself.
- Analyzer warning that memory rows exist while wait is zero.

Those are useful validation aids. They do not represent hardware/architecture modifications unless paired with a real DPort, LSU, cache, or memory hierarchy model change.

## Measurement-Only Changes Not Recommended As Model Improvements

These suggestions from v1/v2 are useful for debugging and validation, but they should not be counted as performance simulator model improvements under the v3 rule:

| Measurement-only change | Why it is not a hardware/architecture modification | How it can still be used |
|---|---|---|
| Add producer instruction ID, producer PC, or producer type ID for RAW | Adds observability but does not change register readiness or forwarding behavior. | Use to validate RAW root cause and de-overlap RAW from divider/multiplier/load producers. |
| Add divisor class, zero-divisor flag, or computed divider iteration count | Explains divider behavior but does not change the divider hardware model. | Use to validate a proposed divider model or early-out rule. |
| Add predicted PC, actual next PC, or branch predictor state trace fields | Explains branch behavior but does not implement a predictor or stage timing change. | Use to validate a new predictor model or earlier branch-resolution model. |
| Join timing rows with opcode names in the analyzer | Improves report readability but does not modify simulated hardware. | Use after model changes to identify which instructions dominate. |
| Add effective address and memory operation size fields | Improves memory validation but does not add a DPort, LSU, cache, or memory hierarchy change. | Use to validate a future memory hierarchy model. |
| Add de-overlap logic to the contribution analyzer | Changes accounting, not simulated timing. | Use after producer/blocking-resource fields exist to produce a cleaner CPI explanation. |

## Recommended Order Of Work Under v3 Rule

1. RAW: only pursue model changes that represent forwarding, bypass, correct zero-register semantics, or architecture-accurate readiness timing.
2. Divider: prioritize divider model changes only if they represent a real faster divider or documented early-out behavior.
3. Branch: compare static predictor against a real alternative predictor or earlier-resolution pipeline model; do not treat extra branch trace fields as performance improvements.
4. Multiplier: change `MUL`/`MULH` timing only for a concrete target multiplier design, and keep it lower priority for the current trace.
5. Memory-port: do not change DPort/LSU/cache modeling from the current `em:ud` trace alone because `memory_port_wait_cycles = 0`; require a targeted memory trace or hardware target parameters first.

## Final Notes

- This report is CV32E40P-only and does not apply to CVA6 or adjacent generated CV32E40P variants.
- The current runtime data is from one trace summary, not a full benchmark-suite diagnosis.
- CorePerfDSL should remain the first place to encode architectural timing changes. External models should encode dynamic hardware policy. Generated backend edits should be avoided unless no source-level modeling route exists.
