# CV32E40P Bottleneck Knowledge Map

This is a static mechanism map only. It identifies potential bottleneck mechanisms from model code and CorePerfDSL; it does not diagnose any benchmark bottleneck without runtime traces.

## A. Processor Identity

- Processor name: `CV32E40P`
- ISA / width / pipeline type: `RV32IMACFD`, 32-bit RISC-V, scalar 4-stage pipeline inferred from `core : "RV32IMACFD"` and `Pipeline CV32E40P_pipeline (IF_stage -> ID_stage -> EX_stage -> WB_stage)`.
- Source files used:
  - `code_gen/descriptions/core_perf_dsl/CV32E40P.corePerfDsl:17-194`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/include/CV32E40P_PerformanceModel.h:39-66`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_PerformanceModel.cpp:38-88`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_SchedulingFunction.cpp`
- Confidence level: high for the generated `CV32E40P` variant; medium for relationship to adjacent variants such as `CV32E40P_CORE`, `CV32E40P_LLM`, and `CV32E40P_QWEN_1` because those are separate generated models.

## B. Repository Map For This Processor

- CorePerfDSL model: `code_gen/descriptions/core_perf_dsl/CV32E40P.corePerfDsl`.
- Generated backend: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/`.
- Generated monitor: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/monitors/variants/CV32E40P/`.
- External models:
  - Shared register model: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/common/StandardRegisterModel.h`.
  - Shared static branch model: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/src/common/StaticBranchPredictModel.cpp`.
  - CV32E40P divider models: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/src/cv32e40p/DividerModel.cpp`, `.../DividerUnsignedModel.cpp`.
- Simulation entry points: `README.md:39-45` documents `./scripts/run.sh em:crc32 cv32e40p`; `scripts/runbencha_trace.sh:66-85` contains commented CV32E40P trace generation logic.
- Code generation entry point: `README.md:53-59` documents `./scripts/code_gen.sh ./code_gen/descriptions/core_perf_dsl/CV32E40P.corePerfDsl`.
- Trace analysis scripts: `scripts/trace_analyzer.sh:33-80`, `scripts/trace_analyzer_summary.sh:7-60`.
- Shared files used by this processor are documented in `../common/shared_mechanisms.md`.

## C. Pipeline Structure

| Stage | Role | Latency/timing rule | Code locations | Stall/block potential | Specific/shared |
|---|---|---|---|---|---|
| `IF_stage` | Instruction fetch and PC generation via `uA_IFetch`, `uA_PCGen` | Fetch and PC generation use `max(n_Enter, staBranchPredModel.getPc()) + 1`; stage also waits for `ID_stage`. | `CV32E40P.corePerfDsl:48-55`, `CV32E40P_SchedulingFunction.cpp:30-50` | Yes, waits on branch predictor PC readiness and downstream ID stage. | CV32E40P-specific generated timing, shared branch model. |
| `ID_stage` | Decode, operand forwarding/read readiness, jump decode | Decode is `n_IF_stage + 1`; operand reads wait on `regModel.getXa()/getXb()`; stage waits for `EX_stage`. | `CV32E40P.corePerfDsl:49-51`, `CV32E40P_SchedulingFunction.cpp:51-65` | Yes, RAW/data dependency through register model and downstream EX occupancy. | CV32E40P-specific timing, shared register model. |
| `EX_stage` | ALU, branch ALU, CSR, LSU, MUL, MULH, DIV, DIVU | ALU-style ops are `n_ID_stage + 1`; DIV/DIVU use external divider delay in instruction-specific scheduling; MULH resource has static `(5)` latency in CorePerfDSL. | `CV32E40P.corePerfDsl:21-24`, `:51`, `:103-116` | Yes, functional-unit and variable divider latency can extend EX readiness. | CV32E40P-specific. |
| `WB_stage` | Load read/writeback and store data port | `uA_Memory_R` writes `Xd`; `uA_Memory_W` consumes `DPort_W`. Explicit cache/memory delay model is not present. | `CV32E40P.corePerfDsl:42-43`, `:52`, `:112-113` | Yes, but only as modeled DPort_R/DPort_W resource timing, not cache misses. | CV32E40P-specific generated resource model. |

## D. Instruction Execution Flow

| Instruction class | Example opcodes | Pipeline flow | Potential mechanisms | Code locations |
|---|---|---|---|---|
| `Arith_Ra_Rb` | `add`, `sub`, `xor`, `or`, `and` | IF/PCGen -> Decode -> operand A/B -> ALU writeback | RAW waits via `regModel`, ID/EX structural sequencing, ALU occupancy | `CV32E40P.corePerfDsl:86-88`, `:101-105` |
| `Arith_Ra` / `Arith_X` | `addi`, `lui`, `auipc` | IF/PCGen -> Decode -> optional operand A -> ALU writeback | RAW for `rs1` forms; ALU and downstream stage blocking | `CV32E40P.corePerfDsl:87-88`, `:104-105` |
| `Mul_Ra_Rb`, `MulH_Ra_Rb` | `mul`, `mulh`, `mulhu`, `mulhsu` | IF/PCGen -> Decode -> operand A/B -> MUL/MULH writeback | Multiplier structural/resource latency; `MULH(5)` static latency | `CV32E40P.corePerfDsl:89-90`, `:106-107` |
| `Div_Ra_Rb`, `DivU_Ra_Rb` | `div`, `rem`, `divu`, `remu` | IF/PCGen -> Decode -> operands -> divider model -> `Xd` | Variable divider delay based on `rs2_data`; RAW on operands | `CV32E40P.corePerfDsl:91-92`, `:108-109`, divider code below |
| `Load` / `Store` | `lw`, `lh`, `lbu`, `sb`, `sw` | IF/PCGen -> Decode -> operand/LSU -> DPort read/write | DPort structural timing; no cache miss model found for CV32E40P | `CV32E40P.corePerfDsl:95-96`, `:112-113` |
| `Branch_Ra_Rb`, `jal`, `jalr` | `beq`, `bne`, `jal`, `jalr` | IF/PCGen -> decode/jump decode -> ALU/PC redirect connectors | Static predict-not-taken model; wrong-path/redirect timing represented through `Pc_np` vs `Pc_p` connectors | `CV32E40P.corePerfDsl:97`, `:114-116`, `StaticBranchPredictModel.cpp:23-54` |

## E. External Models And Runtime Mechanisms

- Branch prediction: `staBranchPredModel` uses `models/common/StaticBranchPredictModel.h` and trace `{pc, brTarget}`. It always predicts branch-not-taken and returns `pc_np` when `pc == branchTarget`, otherwise `pc_p` (`StaticBranchPredictModel.cpp:35-52`).
- Data dependency / RAW: `StandardRegisterModel` maps `rs1`/`rs2` to readiness times and updates `rd` readiness through `setXd` (`StandardRegisterModel.h:31-39`). The model has a TODO for `rd = 0` (`StandardRegisterModel.h:35`).
- Forwarding / scoreboard: no explicit forwarding or scoreboard model found for the base `CV32E40P`; RAW is represented by register readiness connectors `Xa`, `Xb`, `Xd`.
- Cache / memory: no processor-specific cache model found for base `CV32E40P`; load/store use `DPort_R` and `DPort_W`.
- Resource conflict: generated timing uses `std::max` over resources/stages in `CV32E40P_SchedulingFunction.cpp`; static resources include `MULH(5)` and divider resource models.
- Trace output: channel/printer/monitor fields are `rs1`, `rs2`, `rd`, `pc`, `brTarget`, `rs2_data` (`CV32E40P_Channel.h:36-41`, `CV32E40P_Printer.cpp:46-56`, `CV32E40P_Monitor.cpp:31-58`).

## F. Potential Bottleneck Mechanism Map

### CV32-BN-001

- bottleneck_id: `CV32-BN-001`
- bottleneck_name: RAW dependency wait through `StandardRegisterModel`
- processor: `CV32E40P`
- category: `data_dependency`
- related_pipeline_stage: `ID_stage`
- related_instruction_classes: `Arith_Ra_Rb`, `Arith_Ra`, `Mul_Ra_Rb`, `MulH_Ra_Rb`, `Div_Ra_Rb`, `DivU_Ra_Rb`, `Load`, `Store`, `Branch_Ra_Rb`, `jalr`
- related_code_locations: `StandardRegisterModel.h:37-39`, `CV32E40P_SchedulingFunction.cpp:51-65`
- triggering_condition_in_code: operand timing nodes compute `max(n_IF_stage, regModel.getXa()/getXb())`.
- cycle_delay_mechanism: consumer ID cannot finish before producer `Xd` availability stored by `setXd`.
- runtime_signals_needed: `instruction_id`, `pc`, `opcode`, `instruction_class`, `rs1`, `rs2`, `rd`, producer instruction id, producer writeback cycle, operand wait cycles.
- existing_trace_fields_available: `typeId`, `rs1`, `rs2`, `rd`, `pc`.
- missing_trace_fields: `instruction_id`, `stage enter/exit cycles per instruction`, `stall_reason`, `raw_wait_cycles`, `blocking_instruction_id`.
- blocking_resource: register readiness table entry for `rs1` or `rs2`.
- blocking_instruction_available: false
- possible_contribution_formula: `sum(max(0, ID_ready_cycle - IF_arrival_cycle - decode_base_latency) attributed to RAW)`
- tunable_parameters: none found.
- suggested_next_instrumentation: trace operand ready times from `StandardRegisterModel::getXa/getXb` and producer id stored in `setXd`.
- confidence: high
- open_questions: How should `rd = 0` be excluded from dependency state?

### CV32-BN-002

- bottleneck_id: `CV32-BN-002`
- bottleneck_name: Static predict-not-taken branch redirect
- processor: `CV32E40P`
- category: `branch`
- related_pipeline_stage: `IF_stage`, `ID_stage`, `EX_stage`
- related_instruction_classes: `Branch_Ra_Rb`, `jal`, `jalr`
- related_code_locations: `CV32E40P.corePerfDsl:67-72`, `:114-116`, `StaticBranchPredictModel.cpp:23-54`
- triggering_condition_in_code: branch target is captured by `setPc_np`; `getPc` returns `pc_np` when observed `pc == branchTarget`, otherwise `pc_p`.
- cycle_delay_mechanism: next fetch waits on `staBranchPredModel.getPc()` through IF-stage `max` timing.
- runtime_signals_needed: `pc`, `brTarget`, actual next pc, predicted pc, branch taken, mispredict flag, redirect penalty cycles.
- existing_trace_fields_available: `pc`, `brTarget`, `typeId`.
- missing_trace_fields: `branch_prediction_result`, `actual_next_pc`, `branch_redirect_penalty`, `stage enter/exit cycles`.
- blocking_resource: `Pc` connector from static branch predictor.
- blocking_instruction_available: false
- possible_contribution_formula: `sum(fetch_delay_after_branch where predicted_pc != actual_next_pc)`
- tunable_parameters: static policy fixed in code; no tunable parameter found.
- suggested_next_instrumentation: expose predicted-taken/mispredict/redirect-cycle fields from `StaticBranchPredictModel`.
- confidence: medium
- open_questions: The code infers taken by comparing current `pc` with `branchTarget`; precise trace semantics should be validated at runtime.

### CV32-BN-003

- bottleneck_id: `CV32-BN-003`
- bottleneck_name: Variable divider latency
- processor: `CV32E40P`
- category: `functional_unit`
- related_pipeline_stage: `EX_stage`
- related_instruction_classes: `Div_Ra_Rb`, `DivU_Ra_Rb`
- related_code_locations: `CV32E40P.corePerfDsl:74-82`, `:146-157`, `DividerModel.cpp:24-48`, `DividerUnsignedModel.cpp:24-41`
- triggering_condition_in_code: divider delay is computed from `rs2_data`; zero divisor or leading-one position changes delay.
- cycle_delay_mechanism: `DIV`/`DIVU` resource model contributes variable `getDelay()` before `Xd` availability.
- runtime_signals_needed: `instruction_id`, `opcode`, `rs1`, `rs2`, `rd`, `rs2_data`, divider delay, EX enter/exit cycles.
- existing_trace_fields_available: `typeId`, `rs1`, `rs2`, `rd`, `pc`, `rs2_data`.
- missing_trace_fields: `divider_delay`, `stage enter/exit cycles`, `stall_reason`, `blocking_resource`.
- blocking_resource: `DIV` or `DIVU`.
- blocking_instruction_available: null
- possible_contribution_formula: `sum(divider_delay - base_EX_latency) for div/rem/divu/remu`
- tunable_parameters: none found.
- suggested_next_instrumentation: record `ResourceModel::getDelay()` return value for divider instructions.
- confidence: high
- open_questions: Need generated scheduling locations for each div opcode to attribute exact cycles per instruction.

### CV32-BN-004

- bottleneck_id: `CV32-BN-004`
- bottleneck_name: Memory port / LSU structural timing without cache detail
- processor: `CV32E40P`
- category: `memory`
- related_pipeline_stage: `EX_stage`, `WB_stage`
- related_instruction_classes: `Load`, `Store`
- related_code_locations: `CV32E40P.corePerfDsl:21-24`, `:42-43`, `:112-113`
- triggering_condition_in_code: load/store paths use `LSU`, `DPort_R`, and `DPort_W` resources; no cache model is linked.
- cycle_delay_mechanism: memory operations serialize through modeled resources and WB stage; external memory wait is missing.
- runtime_signals_needed: memory address, load/store size, cache hit/miss if added, memory wait cycles, resource wait cycles.
- existing_trace_fields_available: `rs1`, `rs2`, `rd`, `pc`; no `addr` field found for CV32E40P base trace.
- missing_trace_fields: `addr`, `cache_hit_or_miss`, `memory_wait_cycles`, `resource_wait_cycles`, `stall_reason`.
- blocking_resource: `LSU`, `DPort_R`, `DPort_W`.
- blocking_instruction_available: false
- possible_contribution_formula: `sum(memory_stage_wait_cycles attributed to DPort/LSU)`
- tunable_parameters: none found.
- suggested_next_instrumentation: add effective address and per-resource wait cycle tracing around `uA_LSU`, `uA_Memory_R`, `uA_Memory_W`.
- confidence: medium
- open_questions: Is a real CV32E40P cache/memory model intentionally absent, or generated elsewhere?

### CV32-BN-005

- bottleneck_id: `CV32-BN-005`
- bottleneck_name: Multiplier and high-multiplier resource latency
- processor: `CV32E40P`
- category: `functional_unit`
- related_pipeline_stage: `EX_stage`
- related_instruction_classes: `Mul_Ra_Rb`, `MulH_Ra_Rb`
- related_code_locations: `CV32E40P.corePerfDsl:21-23`, `:89-90`, `:106-107`
- triggering_condition_in_code: `MULH(5)` declares a multi-cycle resource; MUL/MULH write `Xd`.
- cycle_delay_mechanism: multiplier resource latency delays destination register readiness and downstream consumers.
- runtime_signals_needed: opcode, instruction_class, resource enter/exit cycles, multiplier wait cycles.
- existing_trace_fields_available: `typeId`, `rs1`, `rs2`, `rd`, `pc`.
- missing_trace_fields: `functional_unit_delay`, `resource_wait_cycles`, `stage enter/exit cycles`.
- blocking_resource: `MUL`, `MULH`.
- blocking_instruction_available: null
- possible_contribution_formula: `sum(EX_exit - EX_enter - base_ALU_latency for multiply classes)`
- tunable_parameters: `MULH(5)` static latency in CorePerfDSL.
- suggested_next_instrumentation: emit selected functional unit and resource delay per instruction.
- confidence: medium
- open_questions: Need generated MUL/MULH scheduling snippets to confirm exact generated cycle formula.

## G. Trace Instrumentation Requirements

Needed to compute actual contribution later: `instruction_id`, `pc`, `opcode`, `instruction_class`, `stage enter/exit cycles`, `stall_reason`, `stall_cycles`, `blocking_resource`, `blocking_instruction_id`, `branch_prediction_result`, `branch_redirect_penalty`, `cache_hit_or_miss`, `memory_wait_cycles`, `raw_wait_cycles`, `resource_wait_cycles`.

Currently available: `typeId`, `rs1`, `rs2`, `rd`, `pc`, `brTarget`, `rs2_data`, plus timing CSV stage columns `IF_stage`, `ID_stage`, `EX_stage`, `WB_stage` from `CV32E40P_PerformanceModel.cpp:66-87`. Missing: stable instruction id, opcode text, explicit stall attribution, blocking producer/resource, memory address, branch prediction result, and per-mechanism delay.

## H. Suggested Next Step

Later, run a benchmark with trace output only after instrumentation is added or selected existing traces are understood. Join instruction trace rows to timing rows by instruction order, compute per-instruction stage deltas, classify each excess cycle by explicit `stall_reason` or by modeled contributor fields, and aggregate cycles by bottleneck id. Until then, all entries above remain potential mechanisms.
