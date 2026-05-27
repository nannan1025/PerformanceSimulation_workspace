# CVA6 Bottleneck Knowledge Map

This is a static mechanism map only. It identifies potential bottleneck mechanisms from CorePerfDSL and generated code; it does not diagnose actual benchmark bottlenecks without runtime traces.

## A. Processor Identity

- Processor name: `CVA6`
- ISA / width / pipeline type: `RV64IMACFD`, 64-bit RISC-V, multi-stage pipeline with PC, fetch, instruction queue, decode, issue, execute, and commit stages.
- Source files used:
  - `code_gen/descriptions/core_perf_dsl/CVA6.corePerfDsl:17-268`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/include/CVA6_PerformanceModel.h:42-95`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_PerformanceModel.cpp:41-123`
  - `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_SchedulingFunction.cpp`
- Confidence level: high for the generated `CVA6` variant; medium for adjacent variants such as `CVA62` and `CVA6_QWEN_1`, which are related but separate generated models.

## B. Repository Map For This Processor

- CorePerfDSL model: `code_gen/descriptions/core_perf_dsl/CVA6.corePerfDsl`.
- Generated backend: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/`.
- Generated monitor: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/monitors/variants/CVA6/`.
- External models:
  - Dynamic branch predictor: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/src/cva6/BranchPredictionModel.cpp`.
  - I-cache and D-cache: `.../src/cva6/ICacheModel.cpp`, `.../src/cva6/DCacheModel.cpp`.
  - Clobber/commit dependency model: `.../include/models/cva6/ClobberModel.h`.
  - Divider models: `.../src/cva6/DividerModel.cpp`, `.../src/cva6/DividerUnsignedModel.cpp`.
  - Shared register model: `.../include/models/common/StandardRegisterModel.h`.
- Simulation entry points: `README.md:43-45` documents `./scripts/run.sh em:ud cva6 -tp=<YOUR/TRACE/PATH>`.
- Code generation entry point: `README.md:53-59`; use `code_gen/descriptions/core_perf_dsl/CVA6.corePerfDsl`.
- Trace analysis scripts: `scripts/trace_analyzer.sh:33-80`, `scripts/trace_analyzer_summary.sh:7-60`.
- Shared files are documented in `../common/shared_mechanisms.md`.

## C. Pipeline Structure

| Stage | Role | Latency/timing rule | Code locations | Stall/block potential | Specific/shared |
|---|---|---|---|---|---|
| `PC_stage` | PC generation, redirect correction, I-cache block release | PC stage waits on `dynBranchPredModel.getPc_mp()`, `iCacheModel.getIc_out()`, IF capacity, and `IF_substage_0`. | `CVA6.corePerfDsl:105-116`, `CVA6_SchedulingFunction.cpp:30-50` | Yes, branch mispredict and I-cache miss can block PC. | CVA6-specific. |
| `IF_stage` | 3-capacity fetch subpipe: ICache control, ICache, instruction scan/realignment | `IF_stage [capacity:3]`; I-cache delay is `iCacheModel.getDelay()`. | `CVA6.corePerfDsl:73-82`, `:107-109`, `ICacheModel.cpp:25-35` | Yes, limited capacity and cache miss delay. | CVA6-specific. |
| `IQ_stage` | Instruction queue insert, 7-capacity output buffer | `IQ_stage [capacity:7, output-buffer]`; waits on ID stage. | `CVA6.corePerfDsl:109`, `CVA6_PerformanceModel.h:47-49` | Yes, queue capacity/backpressure. | CVA6-specific. |
| `ID_stage` | Decode | Decode is after IQ and waits on issue stage (`IS_stage`). | `CVA6.corePerfDsl:110`, `CVA6_SchedulingFunction.cpp:6301-6307` | Yes, decode can back up behind issue. | CVA6-specific. |
| `IS_stage` | Issue, clobber, operand reads | Issue waits on source readiness, clobber readiness, EX capacity/subpipe availability. | `CVA6.corePerfDsl:111`, `:188-201`, `ClobberModel.h:34-35` | Yes, RAW, WAW/commit-like clobber, issue/EX availability. | CVA6-specific plus shared register model. |
| `EX_stage` | 8-capacity output-buffer execution with ALU, MUL, DIV, load, store subpipes | `EX_stage [capacity:8, output-buffer]`; DIV blocks ALU and MUL subpipes; MUL blocks ALU subpipe. | `CVA6.corePerfDsl:83-103`, `:112` | Yes, functional-unit and subpipe structural conflicts. | CVA6-specific. |
| `COM_stage` | 2-capacity commit and clobber release | `COM_stage [capacity:2]`; `uA_Commit_Cb` updates clobber model. | `CVA6.corePerfDsl:113`, `:195-201`, `CVA6_PerformanceModel.h:50` | Yes, commit bandwidth and clobber release can bottleneck. | CVA6-specific. |

## D. Instruction Execution Flow

| Instruction class | Example opcodes | Pipeline flow | Potential mechanisms | Code locations |
|---|---|---|---|---|
| `Arith_0`, `Arith_Rs1`, `Arith_Rs1_Rs2` | `lui`, `addi`, `add`, `subw` | PC -> IF -> IQ -> ID -> IS -> ALU -> COM | RAW via `regModel`, clobber/commit dependency, issue/EX capacity | `CVA6.corePerfDsl:175-177`, `:188-193` |
| `Branch`, `Jump`, `JumpR` | `beq`, `jal`, `jalr` | PC -> IF branch/jump scan -> ID/IS -> ALU branch/jr -> COM | dynamic BHT/BTB/RAS prediction, redirect correction, PC/IF blocking | `CVA6.corePerfDsl:178-180`, `:194-196`, `BranchPredictionModel.cpp:113-267` |
| `Mul` | `mul`, `mulh`, `mulw` | PC -> IF -> IQ -> ID -> IS -> MUL_I -> MUL_O -> COM | two-stage multiplier and subpipe block against ALU | `CVA6.corePerfDsl:181`, `:197`, `:97-100` |
| `Div`, `DivU` | `div`, `rem`, `divu`, `remuw` | PC -> IF -> IQ -> ID -> IS -> DIV/DIVU -> COM | variable 64-bit divider delay; DIV subpipe blocks ALU and MUL subpipes | `CVA6.corePerfDsl:182-183`, `:198-199`, `DividerModel.cpp:23-48` |
| `Load` | `lw`, `ld`, `lbu` | PC -> IF -> IQ -> ID -> IS -> LCtrl -> DCache -> LUnit -> COM | D-cache hit/miss/non-cacheable delay, load unit occupancy, RAW on result | `CVA6.corePerfDsl:184`, `:200`, `DCacheModel.cpp:25-42` |
| `Store` | `sb`, `sw`, `sd` | PC -> IF -> IQ -> ID -> IS -> SCtrl -> SUnit -> COM | store unit occupancy; D-cache store delay is not modeled in this flow | `CVA6.corePerfDsl:185`, `:201` |

## E. External Models And Runtime Mechanisms

- Branch prediction: `cva6::BranchPredictionModel` uses a 2-page x 64-row BHT, 2-entry RAS, and 2-page x 16-row BTB (`BranchPredictionModel.h:49-153`). It predicts backward branches taken by default when BHT entry invalid (`BranchPredictionModel.cpp:57-65`), updates on taken/mispredict (`:183-187`), and returns correction times through `getPc_mp()` / `getPc_pt()` (`:168-267`).
- Data dependency / RAW: `common::StandardRegisterModel` exposes source readiness and sets destination readiness (`StandardRegisterModel.h:37-39`).
- Scoreboard / clobber: `ClobberModel` stores destination register commit readiness; `getCb_out()` blocks nonzero `rd` until clobber availability (`ClobberModel.h:34-35`). CorePerfDSL names `uA_Issue`, `uA_Clobber`, and `uA_OF_A/B` in `IS_stage` (`CVA6.corePerfDsl:48-51`, `:111`).
- Cache/memory: `ICacheModel` has `CACHE_DELAY=1`, `MEMORY_DELAY=5`, 4-way x 256 entries, and blocks PC on misses (`ICacheModel.h:39-67`, `ICacheModel.cpp:25-35`). `DCacheModel` has `CACHE_DELAY=1`, `MEMORY_DELAY=7`, `NOT_CACHABLE_DELAY=9`, 8-way x 256 entries, and a TODO for store-block address delay (`DCacheModel.h:39-66`, `DCacheModel.cpp:25-42`).
- Resource conflicts: EX subpipes include blocks: `EX_subpipe_mul [blocks: EX_subpipe_alu]`, `EX_subpipe_div [blocks: {EX_subpipe_alu, EX_subpipe_mul}]` (`CVA6.corePerfDsl:97-103`).
- Trace output: `rs1`, `rs2`, `rd`, `pc`, `brTarget`, `imm`, `rs1_data`, `rs2_data`, `addr` (`CVA6_Channel.h:36-44`, `CVA6_Printer.cpp:49-62`, `CVA6_Monitor.cpp:31-64`).

## F. Potential Bottleneck Mechanism Map

### CVA6-BN-001

- bottleneck_id: `CVA6-BN-001`
- bottleneck_name: I-cache miss and PC/fetch blocking
- processor: `CVA6`
- category: `frontend`
- related_pipeline_stage: `PC_stage`, `IF_stage`
- related_instruction_classes: `[ALL]`
- related_code_locations: `CVA6.corePerfDsl:73-82`, `:107-109`, `ICacheModel.h:39-67`, `ICacheModel.cpp:25-35`
- triggering_condition_in_code: `ICacheModel::getDelay()` returns `MEMORY_DELAY` when address is not cacheable or misses.
- cycle_delay_mechanism: I-cache delay and `getIc_out()` feed PC-stage max operations and IF substage timing.
- runtime_signals_needed: `pc`, `icache_hit_or_miss`, `icache_delay`, `PC_stage`, `IF_stage`, frontend wait cycles.
- existing_trace_fields_available: `pc`, timing columns `PC_stage`, `IF_stage`.
- missing_trace_fields: `icache_hit_or_miss`, `icache_delay`, `frontend_wait_cycles`, `stall_reason`.
- blocking_resource: `ICache`, `PC_stage`.
- blocking_instruction_available: null
- possible_contribution_formula: `sum(icache_delay - CACHE_DELAY plus PC/IF wait caused by Ic_out)`
- tunable_parameters: `CACHE_DELAY=1`, `MEMORY_DELAY=5`, 4-way x 256 cache, cacheable range `0x80000000..0xC0000000`.
- suggested_next_instrumentation: expose `ICacheModel::getInfo_miss()` and `getDelay()` in timing trace.
- confidence: high
- open_questions: No explicit cache line size parameter beyond tag/index logic was found.

### CVA6-BN-002

- bottleneck_id: `CVA6-BN-002`
- bottleneck_name: Dynamic branch prediction redirect and prediction-path delay
- processor: `CVA6`
- category: `branch`
- related_pipeline_stage: `PC_stage`, `IF_stage`, `EX_stage`
- related_instruction_classes: `Branch`, `Jump`, `JumpR`
- related_code_locations: `CVA6.corePerfDsl:128-132`, `:194-196`, `BranchPredictionModel.cpp:57-267`, `BranchPredictionModel.h:49-153`
- triggering_condition_in_code: BHT prediction differs from actual taken result, BTB/RAS prediction target differs from current PC, or branch is correctly predicted taken.
- cycle_delay_mechanism: `getPc_mp()` returns correction time `t_pc_mp`; `getPc_pt()` returns predicted-taken time `t_pc_pt`; PC stage waits on these connectors.
- runtime_signals_needed: predicted taken, actual taken, predicted target, actual target, mispredict flag, redirect penalty, BHT/BTB/RAS source.
- existing_trace_fields_available: `pc`, `brTarget`, `imm`, `rs1`, `rd`.
- missing_trace_fields: `branch_prediction_result`, `predicted_target`, `actual_next_pc`, `branch_redirect_penalty`, `predictor_component`.
- blocking_resource: `dynBranchPredModel` connectors `Pc_mp`, `Pc_pt`.
- blocking_instruction_available: false
- possible_contribution_formula: `sum(branch_redirect_penalty for mispredicted branches/jumpR) + predicted-taken frontend delay if modeled separately`
- tunable_parameters: BHT `2 x 64`, BTB `2 x 16`, RAS depth 2, default backward-taken policy.
- suggested_next_instrumentation: print `getInfo_mispredict()`, `getInfo_taken()`, predicted target, and connector delay.
- confidence: high
- open_questions: Need runtime definition of actual next PC row alignment.

### CVA6-BN-003

- bottleneck_id: `CVA6-BN-003`
- bottleneck_name: RAW and issue-stage source readiness wait
- processor: `CVA6`
- category: `data_dependency`
- related_pipeline_stage: `IS_stage`
- related_instruction_classes: `Arith_Rs1`, `Arith_Rs1_Rs2`, `Branch`, `JumpR`, `Mul`, `Div`, `DivU`, `Load`, `Store`
- related_code_locations: `StandardRegisterModel.h:37-39`, `CVA6.corePerfDsl:48-51`, `:188-201`, `CVA6_SchedulingFunction.cpp:6310-6318`
- triggering_condition_in_code: issue-stage timing includes source readiness from `regModel.getXa()/getXb()`.
- cycle_delay_mechanism: consumer issue waits until producer result has been written to `Xd`.
- runtime_signals_needed: `instruction_id`, `rs1`, `rs2`, `rd`, source ready cycles, producer instruction id, `raw_wait_cycles`.
- existing_trace_fields_available: `rs1`, `rs2`, `rd`, `pc`.
- missing_trace_fields: `blocking_instruction_id`, `raw_wait_cycles`, source ready cycle, stage enter/exit cycles.
- blocking_resource: register readiness table.
- blocking_instruction_available: false
- possible_contribution_formula: `sum(max(0, source_ready - issue_base_ready))`
- tunable_parameters: none found.
- suggested_next_instrumentation: store producer id and ready cycle in `StandardRegisterModel`.
- confidence: high
- open_questions: Forwarding behavior is not explicit; model may be readiness-table based only.

### CVA6-BN-004

- bottleneck_id: `CVA6-BN-004`
- bottleneck_name: Clobber / commit dependency and commit bandwidth
- processor: `CVA6`
- category: `commit`
- related_pipeline_stage: `IS_stage`, `COM_stage`
- related_instruction_classes: writeback classes with `uA_Clobber` and `uA_Commit_Cb`
- related_code_locations: `CVA6.corePerfDsl:142-147`, `:111-113`, `:191-201`, `ClobberModel.h:34-35`, `CVA6_PerformanceModel.h:47-50`
- triggering_condition_in_code: `uA_Clobber` reads `Cb_out` before issue; `uA_Commit_Cb` writes `Cb_in` at commit for nonzero `rd`.
- cycle_delay_mechanism: instructions that write the same architectural destination may wait for prior commit/clobber release; COM capacity is 2.
- runtime_signals_needed: `rd`, commit cycle, clobber ready cycle, commit queue occupancy, commit wait cycles.
- existing_trace_fields_available: `rd`, `pc`, timing column `COM_stage`.
- missing_trace_fields: `clobber_wait_cycles`, `commit_wait_cycles`, `blocking_instruction_id`, commit slot occupancy.
- blocking_resource: `ClobberModel`, `COM_stage`.
- blocking_instruction_available: false
- possible_contribution_formula: `sum(clobber_wait_cycles + commit_capacity_wait_cycles)`
- tunable_parameters: `COM_stage` capacity 2.
- suggested_next_instrumentation: expose clobber producer id/ready time and commit capacity wait.
- confidence: medium
- open_questions: Need confirm whether clobber represents WAW, scoreboard, commit dependency, or a simplified blend.

### CVA6-BN-005

- bottleneck_id: `CVA6-BN-005`
- bottleneck_name: D-cache miss/non-cacheable memory delay
- processor: `CVA6`
- category: `memory`
- related_pipeline_stage: `EX_stage`
- related_instruction_classes: `Load`
- related_code_locations: `CVA6.corePerfDsl:159-162`, `:200`, `DCacheModel.h:39-66`, `DCacheModel.cpp:25-42`
- triggering_condition_in_code: `DCacheModel::getDelay()` returns `NOT_CACHABLE_DELAY` for non-cacheable address, `CACHE_DELAY` on hit, `MEMORY_DELAY` on miss.
- cycle_delay_mechanism: load path `LCtrl -> DCache -> LUnit` delays result writeback to `Xd`.
- runtime_signals_needed: `addr`, `dcache_hit_or_miss`, cacheability, dcache delay, load wait cycles.
- existing_trace_fields_available: `addr`, `rs1`, `rd`, `pc`.
- missing_trace_fields: `cache_hit_or_miss`, `memory_wait_cycles`, `dcache_delay`, `cacheability`.
- blocking_resource: `DCache`.
- blocking_instruction_available: null
- possible_contribution_formula: `sum(dcache_delay - CACHE_DELAY) for loads`
- tunable_parameters: `CACHE_DELAY=1`, `MEMORY_DELAY=7`, `NOT_CACHABLE_DELAY=9`, 8-way x 256 cache, cacheable range `0x80000000..0xC0000000`.
- suggested_next_instrumentation: expose `DCacheModel::getInfo_miss()`, cacheability, and delay.
- confidence: high
- open_questions: `DCacheModel.cpp:29` notes missing store-address blocking behavior from another model.

### CVA6-BN-006

- bottleneck_id: `CVA6-BN-006`
- bottleneck_name: EX subpipe structural conflicts
- processor: `CVA6`
- category: `structural_resource`
- related_pipeline_stage: `EX_stage`
- related_instruction_classes: `Mul`, `Div`, `DivU`, ALU classes
- related_code_locations: `CVA6.corePerfDsl:97-103`, `:112`, `CVA6_PerformanceModel.h:67-81`
- triggering_condition_in_code: `EX_subpipe_mul` blocks `EX_subpipe_alu`; `EX_subpipe_div` blocks both `EX_subpipe_alu` and `EX_subpipe_mul`; EX capacity is 8.
- cycle_delay_mechanism: blocked subpipes and EX output buffer capacity push issue/execution readiness later.
- runtime_signals_needed: selected subpipe, subpipe busy-until, EX occupancy, resource wait cycles.
- existing_trace_fields_available: top-level `EX_stage` timing only.
- missing_trace_fields: subpipe selected, substage enter/exit cycles, resource wait cycles, blocking_resource.
- blocking_resource: `EX_subpipe_alu`, `EX_subpipe_mul`, `EX_subpipe_div`, `EX_stage`.
- blocking_instruction_available: false
- possible_contribution_formula: `sum(resource_wait_cycles where selected max operand is blocked subpipe or EX capacity)`
- tunable_parameters: `EX_stage` capacity 8; subpipe block declarations.
- suggested_next_instrumentation: trace substage timings and chosen max contributors in generated scheduling functions.
- confidence: high
- open_questions: Need per-instruction max-input attribution to separate capacity from functional delay.

### CVA6-BN-007

- bottleneck_id: `CVA6-BN-007`
- bottleneck_name: Variable 64-bit divider latency
- processor: `CVA6`
- category: `functional_unit`
- related_pipeline_stage: `EX_stage`
- related_instruction_classes: `Div`, `DivU`
- related_code_locations: `CVA6.corePerfDsl:149-157`, `:198-199`, `DividerModel.cpp:23-48`, `DividerUnsignedModel.cpp:23-44`
- triggering_condition_in_code: divider delay depends on `rs1_data` and `rs2_data`; zero divisor can produce 64-cycle delay.
- cycle_delay_mechanism: DIV/DIVU subpipe delay and block declarations delay result and other EX subpipes.
- runtime_signals_needed: `rs1_data`, `rs2_data`, divider delay, EX/subpipe enter/exit cycles, blocked subpipe wait.
- existing_trace_fields_available: `rs1_data`, `rs2_data`, `rs1`, `rs2`, `rd`, `pc`.
- missing_trace_fields: `divider_delay`, `subpipe_wait_cycles`, `blocking_resource`, stage enter/exit cycles.
- blocking_resource: `DIV`/`DIVU`, `EX_subpipe_div`.
- blocking_instruction_available: null
- possible_contribution_formula: `sum(divider_delay - base_EX_latency + subpipe_block_wait_cycles)`
- tunable_parameters: delay formula in divider code; no external config found.
- suggested_next_instrumentation: record divider `getDelay()` and subpipe blocking attribution.
- confidence: high
- open_questions: Distinguish functional delay from structural blocking caused by the long divider.

## G. Trace Instrumentation Requirements

Needed to compute actual contribution later: `instruction_id`, `pc`, `opcode`, `instruction_class`, `stage enter/exit cycles`, `stall_reason`, `stall_cycles`, `blocking_resource`, `blocking_instruction_id`, `branch_prediction_result`, `branch_redirect_penalty`, `cache_hit_or_miss`, `memory_wait_cycles`, `raw_wait_cycles`, `resource_wait_cycles`.

Currently available: `typeId`, `rs1`, `rs2`, `rd`, `pc`, `brTarget`, `imm`, `rs1_data`, `rs2_data`, `addr`, plus timing CSV top-level columns `PC_stage`, `IF_stage`, `IQ_stage`, `ID_stage`, `IS_stage`, `EX_stage`, `COM_stage` from `CVA6_PerformanceModel.cpp:95-123`. Missing: stable instruction id in printed timing rows, branch predictor result/target, cache hit/miss and delay, subpipe timings, explicit stall reason, blocking producer/resource, commit/clobber wait fields.

## H. Suggested Next Step

Later, run a benchmark only after deciding the instrumentation schema. Join instruction trace, top-level timing trace, and new mechanism fields by instruction order or explicit `instruction_id`. Compute per-stage deltas, attribute excess cycles by explicit source (`icache`, `branch`, `raw`, `clobber`, `dcache`, `divider`, `subpipe`, `commit`), and aggregate per bottleneck id. Do not label any item above as an actual bottleneck until those runtime contributions are measured.
