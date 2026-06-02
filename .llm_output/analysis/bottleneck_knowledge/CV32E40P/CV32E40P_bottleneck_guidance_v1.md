# CV32E40P Bottleneck Guidance v1

## Inputs Used

This guidance combines static bottleneck candidates, current runtime contribution summaries, and Step 1-5 trace instrumentation notes for the base `CV32E40P` model only.

Source reports:

- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/bottleneck_knowledge_map.md`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/contribution_analyzer.md`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step1_trace_instrumentation.md`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step2_trace_instrumentation.md`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step3_trace_instrumentation.md`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step4_trace_instrumentation.md`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/step5_trace_instrumentation.md`

Runtime data comes from the current `em:ud` trace already summarized in `contribution_analyzer.md`. No benchmark was rerun for this report.

## Interpretation Warning

The runtime numbers below are additive instrumentation-field sums. They are useful for guidance and prioritization, but they are not a de-overlapped root-cause CPI stack. A single instruction row can contribute to multiple categories, so the total attributed delay can exceed the observed processor-cycle count.

The static mechanisms are architecture/model candidates. The runtime ranking is specific to the current CV32E40P `em:ud` trace.

## Runtime Ranking

| Rank | Bottleneck category | Candidate ID | Runtime field | Current cycles | % attributed delay | Guidance priority |
|---:|---|---|---|---:|---:|---|
| 1 | RAW/data dependency | `CV32-BN-001` | `raw_wait_cycles` | `1,138,886` | `45.13%` | Highest |
| 2 | Divider functional unit | `CV32-BN-003` | `divider_delay_cycles` | `969,568` | `38.42%` | Highest |
| 3 | Branch/control redirect | `CV32-BN-002` | `branch_redirect_cycles` | `289,343` | `11.47%` | Medium |
| 4 | Multiplier functional unit | `CV32-BN-005` | `multiplier_delay_cycles` | `125,630` | `4.98%` | Lower |
| 5 | Memory-port structural wait | `CV32-BN-004` | `memory_port_wait_cycles` | `0` | `0.00%` | Not activated in current trace |

Current high-priority runtime contributors are RAW wait and divider delay. Branch redirect is meaningful but secondary for this trace. Multiplier delay is present but smaller. Memory-port timing is statically valid, and the trace contains many load/store rows, but `memory_port_wait_cycles = 0`; do not optimize memory-port behavior based on this trace alone.

## Candidate Guidance

### `CV32-BN-001`: RAW Dependency Wait Through `StandardRegisterModel`

Static mechanism:

- Category: `data_dependency`
- Related stage: `ID_stage`
- Mechanism: source operand timing waits on register readiness from `StandardRegisterModel`.
- Key locations:
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/common/StandardRegisterModel.h`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_SchedulingFunction.cpp`
  - `code_gen/descriptions/core_perf_dsl/CV32E40P.corePerfDsl`

Runtime evidence:

- Runtime field: `raw_wait_cycles`
- Current contribution: `1,138,886` cycles, rank 1, `45.13%` of attributed delay.
- Nonzero rows: `228,319`.
- Top contributing type IDs from the current analyzer: `37`, `21`, `1`, `25`.
- Step 3 instrumentation records `uses_rs1`, `uses_rs2`, `uses_rd`, `raw_wait_cycles`, `raw_blocking_reg`, and `raw_blocking_ready_cycle`.

Processor architecture view:

- Add or improve forwarding/bypass paths so dependent consumers can read producer results earlier than architectural writeback readiness.
- Improve scoreboard/readiness handling so independent operands do not wait behind unrelated producer state.
- Reduce producer-consumer chains through compiler scheduling, instruction reordering, or software loop restructuring.
- Treat load-use and long-latency functional-unit-use chains separately when optimizing, because RAW delay can be caused by ALU, load, multiplier, or divider producers.

Performance simulator workspace view:

- Extend `StandardRegisterModel` or the CV32E40P wrapper around it to track producer instruction ID along with ready cycle.
- Fix or explicitly model `rd = 0` behavior so writes to `x0` do not create false dependencies.
- Add trace fields for `raw_blocking_instruction_id`, producer `type_id`, and producer `pc` before treating RAW as fully explainable.
- Consider separating RAW wait caused by divider, multiplier, load, and ALU producers in post-processing, because the current `raw_wait_cycles` field only names the blocking register and ready cycle.

Confidence and caveats:

- Static confidence: high.
- Runtime confidence: medium-high for wait-cycle presence, but producer identity is still missing.
- RAW totals can overlap with divider or multiplier delay, because a divider may both contribute its own delay and cause a later RAW wait.

### `CV32-BN-003`: Variable Divider Latency

Static mechanism:

- Category: `functional_unit`
- Related stage: `EX_stage`
- Mechanism: `div`, `rem`, `divu`, and `remu` use CV32E40P divider models whose delay depends on `rs2_data`.
- Key locations:
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/src/cv32e40p/DividerModel.cpp`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/src/cv32e40p/DividerUnsignedModel.cpp`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_SchedulingFunction.cpp`

Runtime evidence:

- Runtime field: `divider_delay_cycles`
- Current contribution: `969,568` cycles, rank 2, `38.42%` of attributed delay.
- Nonzero rows: `31,038`.
- Top contributing type ID from the current analyzer: `25`.
- Step 2 instrumentation records divider model delay values directly from `DividerModel::getDelay()` or `DividerUnsignedModel::getDelay()`.

Processor architecture view:

- Use a faster divider implementation, such as more bits per iteration or a lower-latency algorithm.
- Improve early-out behavior for common divisor patterns if hardware budget allows.
- Avoid hardware division in hot paths where software can use reciprocal multiplication, shifts, table lookup, or algorithmic refactoring.
- If divider throughput matters more than latency, consider pipelining or allowing independent operations around long divide latency.

Performance simulator workspace view:

- Expose divider latency parameters so experiments can compare alternative divider implementations without editing generated scheduler code each time.
- Add more detailed divider trace fields such as signed/unsigned kind, divisor class, zero divisor flag, and computed iteration count.
- Link divider delay rows with subsequent RAW waits to avoid double-counting when explaining end-to-end performance.
- Add targeted divider microbenchmarks that vary `rs2_data` to validate the divider delay model across edge cases.

Confidence and caveats:

- Static confidence: high.
- Runtime confidence: high for current divider delay measurement.
- Current top type ID suggests signed divider/rem behavior dominates the current trace, but opcode-level names should be joined from decoded trace if exact instruction names are needed.

### `CV32-BN-002`: Static Predict-Not-Taken Branch Redirect

Static mechanism:

- Category: `branch`
- Related stages: `IF_stage`, `ID_stage`, `EX_stage`
- Mechanism: CV32E40P uses a static predict-not-taken branch model. Taken conditional branches and jumps create redirect timing.
- Key locations:
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/src/common/StaticBranchPredictModel.cpp`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_SchedulingFunction.cpp`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/monitors/variants/CV32E40P/src/CV32E40P_InstructionMonitors.cpp`

Runtime evidence:

- Runtime field: `branch_redirect_cycles`
- Current contribution: `289,343` cycles, rank 3, `11.47%` of attributed delay.
- Nonzero rows: `58,248`.
- Top contributing type IDs from the current analyzer: `43`, `44`, `48`, `50`, `51`.
- Step 4 instrumentation records `branch_is_control`, `branch_taken`, `branch_mispredict`, and `branch_redirect_cycles`.

Processor architecture view:

- Replace static predict-not-taken with a dynamic predictor for recurring branch patterns.
- Add or improve a branch target buffer so taken branch targets are available earlier.
- Resolve conditional branch outcome earlier in the pipeline when feasible.
- Reduce redirect penalty by moving target/condition calculation earlier or by improving frontend recovery.
- Reduce taken branch frequency in software through layout, loop restructuring, or branchless transforms where profitable.

Performance simulator workspace view:

- Make the static branch policy configurable so experiments can compare predict-not-taken, predict-taken, and simple dynamic policies.
- Add a dynamic branch predictor model behind the same connector interface instead of changing benchmark code.
- Add trace fields for predicted target, actual target, actual next PC, and predictor state to distinguish direction misses from target misses.
- Keep avoiding extra calls to `StaticBranchPredictModel::getPc()` in instrumentation because it mutates predictor state.

Confidence and caveats:

- Static confidence: medium.
- Runtime confidence: medium-high after the Step 4 branch outcome fix.
- Branch redirect cycles are a modeled redirect proxy, not yet a full frontend lost-cycle decomposition.

### `CV32-BN-005`: Multiplier and High-Multiplier Resource Latency

Static mechanism:

- Category: `functional_unit`
- Related stage: `EX_stage`
- Mechanism: multiply instructions write destination readiness through multiply resources; `MULH(5)` is a static multi-cycle resource in the CorePerfDSL model.
- Key locations:
  - `code_gen/descriptions/core_perf_dsl/CV32E40P.corePerfDsl`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_SchedulingFunction.cpp`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/include/CV32E40P_PerformanceModel.h`

Runtime evidence:

- Runtime field: `multiplier_delay_cycles`
- Current contribution: `125,630` cycles, rank 4, `4.98%` of attributed delay.
- Nonzero rows: `125,630`.
- Top contributing type ID from the current analyzer: `21`.
- Step 2 instrumentation records `1` cycle for `mul` and `5` cycles for high-multiply instructions.

Processor architecture view:

- Reduce high-multiply latency if workloads use `mulh`, `mulhu`, or `mulhsu` heavily.
- Pipeline the multiplier if throughput is more important than single-operation latency.
- Provide software/compiler alternatives for repeated multiply-heavy kernels, such as strength reduction or algorithmic changes.
- Prioritize multiplier architecture changes below RAW and divider for the current trace, unless another benchmark shows multiply-heavy behavior.

Performance simulator workspace view:

- Parameterize `MUL` and `MULH` latencies in CorePerfDSL instead of hard-coding them only in generated scheduler output.
- Separate multiplier latency from multiplier structural contention if future models allow pipelined multiply units.
- Add opcode names or instruction classes to the contribution analyzer by joining timing rows with decoded trace rows.
- Validate with a targeted multiply microbenchmark, especially for high-multiply instructions, because the current top runtime contributor is type ID `21`.

Confidence and caveats:

- Static confidence: medium.
- Runtime confidence: high for the currently instrumented static delay fields.
- Current contribution is present but much smaller than RAW and divider in the `em:ud` trace.

### `CV32-BN-004`: Memory-Port / LSU Structural Timing Without Cache Detail

Static mechanism:

- Category: `memory` / `structural_resource`
- Related stages: `EX_stage`, `WB_stage`
- Mechanism: load/store paths use `LSU`, `DPort_R`, and `DPort_W`; no CV32E40P cache model was found in the base model.
- Key locations:
  - `code_gen/descriptions/core_perf_dsl/CV32E40P.corePerfDsl`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_SchedulingFunction.cpp`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_PerformanceModel.cpp`

Runtime evidence:

- Runtime field: `memory_port_wait_cycles`
- Current contribution: `0` cycles, rank 5, `0.00%` of attributed delay.
- Step 5 found load/store rows in the current trace: `DPort_R = 283,175` rows and `DPort_W = 123,481` rows.
- Maximum observed `memory_port_wait_cycles` in the current trace: `0`.

Processor architecture view:

- Do not prioritize memory-port architecture changes based on this trace alone.
- If a memory-heavy trace later shows positive memory-port wait, consider separate load/store ports, store buffering, or improved LSU scheduling.
- If real CV32E40P hardware includes memory hierarchy effects not modeled here, add cache/memory latency modeling before drawing architecture conclusions.
- For software, use memory-access microbenchmarks to separate true memory bottlenecks from ALU/divider/RAW effects.

Performance simulator workspace view:

- Add effective address, memory operation size, and load/store type fields before deeper memory attribution.
- Add cache hit/miss or external memory wait fields only if CV32E40P should model a cache or memory hierarchy.
- Keep `memory_port_wait_cycles` as the DPort/WB structural wait proxy; do not reinterpret it as memory latency.
- Create a targeted load/store stress benchmark to intentionally activate positive DPort structural wait before optimizing this path.

Confidence and caveats:

- Static confidence: medium.
- Runtime confidence: high that this current trace did not activate positive memory-port structural wait.
- The current model has no cache hit/miss detail, so absence of memory-port wait does not prove absence of real memory-system bottlenecks.

## Cross-Candidate Guidance

| Priority | Recommendation | Reason |
|---:|---|---|
| 1 | Investigate RAW and divider together | They are the top two runtime contributors and can overlap when divider results block consumers. |
| 2 | Keep branch as a secondary optimization target | Branch redirect has visible runtime contribution but is far below RAW plus divider in this trace. |
| 3 | Treat multiplier as workload-dependent | Current contribution exists but is smaller; targeted multiply-heavy benchmarks may change priority. |
| 4 | Do not optimize memory-port yet | Current memory-port wait is zero despite many memory rows; use a targeted stress trace first. |

## Suggested Next Work

Architecture-side next work:

- First explore whether the `em:ud` hot path can reduce division frequency or hide divider latency.
- Then examine RAW chains around top PCs and type IDs to see whether forwarding, scheduling, or software transformations could reduce consumer waits.
- Treat branch and multiplier changes as secondary unless a benchmark-specific goal says otherwise.

Simulator-workspace next work:

- Extend RAW attribution with producer instruction ID and producer PC.
- Join timing rows with decoded instruction names so type IDs can be reported as opcodes in the contribution analyzer.
- Add targeted microbenchmarks for divider, RAW chains, branch taken/not-taken patterns, multiply, and DPort stress.
- Add a de-overlap or root-cause attribution pass after producer IDs and explicit stall reasons are available.

## Final Caveats

- This report is CV32E40P-only and should not be applied to CVA6 or adjacent generated variants.
- The guidance is based on the current `em:ud` trace summary, not a full benchmark suite.
- Generated scheduler files may be overwritten by future CorePerfDSL/code-generation runs, so simulator experiments should be tracked carefully.
