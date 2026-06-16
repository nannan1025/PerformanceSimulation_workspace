# CVA6 Bottleneck Instrumentation Implementation Plan

This is a planning document only. It is based on `bottleneck_knowledge_map.md`, `trace_fields_gap_analysis.md`, and static inspection of the base `CVA6` generated backend, monitor, CorePerfDSL model, and CVA6 external models. It does not diagnose benchmark bottlenecks.

## 1. Goal And Scope

Instrument the base `CVA6` performance simulator so runtime timing traces can attribute potential bottleneck mechanisms identified in the static map:

- `CVA6-BN-001`: I-cache miss and PC/fetch blocking
- `CVA6-BN-002`: dynamic branch prediction redirect and prediction-path delay
- `CVA6-BN-003`: RAW and issue-stage source readiness wait
- `CVA6-BN-004`: clobber / commit dependency and commit bandwidth
- `CVA6-BN-005`: D-cache miss/non-cacheable memory delay
- `CVA6-BN-006`: EX subpipe structural conflicts
- `CVA6-BN-007`: variable 64-bit divider latency

Do not include adjacent variants such as `CVA62`, `CVA6_QWEN_1`, or other CVA6-derived generated folders.

## 2. Current CVA6 Trace Baseline

Current timing CSV output from `CVA6_PerformanceModel::getPipelineStream()` prints only:

```text
PC_stage,IF_stage,IQ_stage,ID_stage,IS_stage,EX_stage,COM_stage
```

Current identity/operand trace values already exist in `CVA6_Channel` and monitor bindings:

- `Channel::typeId`
- `Channel::instrCnt`
- `CVA6_Channel::rs1`, `rs2`, `rd`, `pc`, `brTarget`, `imm`, `rs1_data`, `rs2_data`, `addr`

Important existing code locations:

- `code_gen/descriptions/core_perf_dsl/CVA6.corePerfDsl:17-201`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/include/CVA6_PerformanceModel.h:42-97`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_PerformanceModel.cpp:41-123`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/include/CVA6_Channel.h:36-46`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_Channel.cpp:22-60`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/monitors/variants/CVA6/src/CVA6_Monitor.cpp:29-85`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_SchedulingFunction.cpp`

## 3. Minimal CSV Schema

The minimal new CVA6 timing CSV should keep current stage columns and append identity plus mechanism fields:

```text
PC_stage,IF_stage,IQ_stage,ID_stage,IS_stage,EX_stage,COM_stage,
instr_id,type_id,pc,rs1,rs2,rd,brTarget,imm,rs1_data,rs2_data,addr,
uses_rs1,uses_rs2,uses_rd,
icache_miss,icache_delay_cycles,icache_extra_cycles,frontend_wait_cycles,
branch_is_control,branch_taken,branch_predicted_taken,branch_mispredict,branch_predicted_target,branch_actual_target,branch_redirect_cycles,branch_predict_path_cycles,branch_predictor_component,
raw_wait_cycles,raw_blocking_reg,raw_blocking_ready_cycle,
clobber_wait_cycles,clobber_blocking_reg,clobber_ready_cycle,commit_wait_cycles,
dcache_miss,dcache_not_cacheable,dcache_delay_cycles,dcache_extra_cycles,memory_wait_cycles,
ex_resource_kind,ex_resource_wait_cycles,ex_blocking_resource,
divider_delay_cycles,divider_extra_cycles
```

Field defaults:

- Numeric fields default to `0`.
- Register fields that are not applicable default to `0` and are disambiguated by `uses_rs1`, `uses_rs2`, `uses_rd`.
- Text fields default to `none`.
- `branch_predicted_target` and `branch_actual_target` default to `0` when not available.

## 4. Common Step 0: Identity And Operand Fields

### Required Fields

| Field | Why needed | Source |
|---|---|---|
| `instr_id` | Join timing rows and decoded instruction rows | New monotonically increasing counter in `CVA6_PerformanceModel` |
| `type_id` | Classify instruction groups | `Channel::typeId` |
| `pc` | Instruction identity, I-cache, branch | `CVA6_Channel::pc` |
| `rs1`, `rs2`, `rd` | RAW, clobber, commit | `CVA6_Channel::rs1`, `rs2`, `rd` |
| `brTarget`, `imm` | Branch target/prediction analysis | `CVA6_Channel::brTarget`, `imm` |
| `rs1_data`, `rs2_data` | Divider and branch outcome validation | `CVA6_Channel::rs1_data`, `rs2_data` |
| `addr` | D-cache/load/store attribution | `CVA6_Channel::addr` |
| `uses_rs1`, `uses_rs2`, `uses_rd` | Distinguish unavailable operands from register zero | Type-id helper functions |

### Code Locations

- Add pointer members and `instr_id` in `CVA6_PerformanceModel.h`.
- Bind pointers in `CVA6_PerformanceModel::connectChannel()` at `CVA6_PerformanceModel.cpp:41-67`.
- Append fields in `CVA6_PerformanceModel::getPrintHeader()` at `CVA6_PerformanceModel.cpp:110-123`.
- Emit fields in `CVA6_PerformanceModel::getPipelineStream()` at `CVA6_PerformanceModel.cpp:95-108`.
- Add CVA6 type-id helper functions in `CVA6_PerformanceModel.cpp` near the top, following the existing CV32E40P pattern.

### Type-ID Groups For Helper Functions

Use generated instruction printer mapping:

- Branch: `34-39`
- `jal`: `40`
- `jalr`: `41`
- Multiply: `42-46`
- Signed divide/remainder: `47-50`
- Unsigned divide/remainder: `51-54`
- Loads: `55-61`
- Stores: `62-65`

## 5. Bottleneck-Specific Instrumentation

### CVA6-BN-001: I-cache Miss And PC/Fetch Blocking

Minimal fields:

- `icache_miss`
- `icache_delay_cycles`
- `icache_extra_cycles`
- `frontend_wait_cycles`

Code locations:

- `ICacheModel::getDelay()` at `externalModels/src/cva6/ICacheModel.cpp:25-35`.
- `ICacheModel::getInfo_miss()` already exists at `externalModels/include/models/cva6/ICacheModel.h:45`.
- Scheduler frontend pattern appears in every scheduling lambda, e.g. `CVA6_SchedulingFunction.cpp:39-75`.
- `CVA6_PerformanceModel::getPipelineStream()` emits the per-row fields.

Files/classes/functions to modify:

- `models/cva6/ICacheModel.h`
- `models/cva6/ICacheModel.cpp`
- `CVA6_PerformanceModel.h`
- `CVA6_PerformanceModel.cpp`
- `CVA6_SchedulingFunction.cpp`

How to compute:

- In `ICacheModel::getDelay()`, store last delay and miss state:
  - `last_delay = MEMORY_DELAY` for miss or non-cacheable
  - `last_delay = CACHE_DELAY` for hit
  - `last_extra = max(0, last_delay - CACHE_DELAY)`
- In each scheduler frontend block, cache the delay locally:
  - `uint64_t iDelay = perfModel->iCacheModel.getDelay();`
  - `n_ICache = n_IF_substage_0 + iDelay;`
  - call a performance-model setter such as `setICacheInstrumentation(isMiss, iDelay, max(0, iDelay - 1), frontendWait)`.
- Compute `frontend_wait_cycles` as the max visible frontend blocking above the normal PC/IF flow:
  - `pc_correct_wait = n_uA_PcCorrect > n_Enter ? n_uA_PcCorrect - n_Enter : 0`
  - `cache_block_wait = n_uA_CacheBlock > n_Enter ? n_uA_CacheBlock - n_Enter : 0`
  - `if_capacity_wait = perfModel->IF_stage.get(3) > n_PCGen ? perfModel->IF_stage.get(3) - n_PCGen : 0`
  - record the maximum, not the sum, to reduce immediate double counting.

Validation microbenchmark:

- I-cache streaming loop with an instruction footprint larger than the modeled I-cache set capacity to force misses.
- Small hot loop expected to warm the cache and then show mostly hits.
- Validate `icache_miss=1` on cold/miss rows, `icache_extra_cycles>0` on miss rows, and `icache_extra_cycles=0` on cache-hit rows.

Risks and uncertainty:

- `ICacheModel::getDelay()` mutates cache state; do not call it twice for the same instruction.
- Non-cacheable and miss both currently return `MEMORY_DELAY`; distinguish only if `ICacheModel` exposes cacheability.
- Generated scheduler edits may be overwritten by code generation.

### CVA6-BN-002: Dynamic Branch Prediction Redirect And Prediction-Path Delay

Minimal fields:

- `branch_is_control`
- `branch_taken`
- `branch_predicted_taken`
- `branch_mispredict`
- `branch_predicted_target`
- `branch_actual_target`
- `branch_redirect_cycles`
- `branch_predict_path_cycles`
- `branch_predictor_component`

Code locations:

- `BranchPredictionModel.h:99-153`.
- `BranchPredictionModel.cpp:113-267`.
- Branch scheduler functions:
  - `beq` at `CVA6_SchedulingFunction.cpp:3293`
  - `bne` at `:3389`
  - `blt` at `:3485`
  - `bge` at `:3581`
  - `bltu` at `:3677`
  - `bgeu` at `:3773`
  - `jal` at `:3869`
  - `jalr` at `:3963`
- Existing predictor calls:
  - `setPc_p(n_IScan)` for branches, e.g. `CVA6_SchedulingFunction.cpp:3623`
  - `setPc_p_j(n_IScan)` for `jal`, `:3911`
  - `setPc_p_jr(n_IScan)` for `jalr`, `:4005`
  - `setPc_c(n_ALU)` for branch/jalr correction, e.g. `:3658`, `:4041`

Files/classes/functions to modify:

- `models/cva6/BranchPredictionModel.h`
- `models/cva6/BranchPredictionModel.cpp`
- `CVA6_PerformanceModel.h`
- `CVA6_PerformanceModel.cpp`
- `CVA6_SchedulingFunction.cpp`

How to compute:

- Extend `BranchPredictionModel` with read-only getters for the last evaluated prediction state:
  - predicted taken
  - actual taken
  - mispredict
  - predicted target
  - actual target
  - predictor component: `BHT`, `BTB`, `RAS`, `JAL`, or `none`
  - `t_pc_mp` and `t_pc_pt` if needed
- Do not add extra calls to `getPc_mp()` or `getPc_pt()` for instrumentation because these methods evaluate and clear predictor state.
- For conditional branches:
  - `branch_is_control = 1`
  - use predictor model state after normal `getPc_mp()`/`getPc_pt()` flow
  - `branch_redirect_cycles = branch_mispredict ? max(0, EX_stage - IF_stage) : 0`
  - `branch_predict_path_cycles = (!branch_mispredict && branch_taken) ? max(0, IF_stage - PC_stage) : 0` or `0` if predicted-taken path delay is too ambiguous.
- For `jal`:
  - `branch_is_control = 1`, `branch_taken = 1`
  - `branch_mispredict = 0` unless the existing model exposes a target mismatch
  - `branch_redirect_cycles = max(0, ID_stage - IF_stage)` if using decode/jump scan attribution.
- For `jalr`:
  - `branch_is_control = 1`, `branch_taken = 1`
  - `branch_mispredict` from BTB/RAS target mismatch in `BranchPredictionModel::getPc_mp()`
  - `branch_redirect_cycles = branch_mispredict ? max(0, EX_stage - IF_stage) : 0`.

Validation microbenchmark:

- Branch pattern microbenchmark with always-taken, always-not-taken, alternating taken/not-taken branches.
- `jal` chain to validate unconditional jump rows.
- `jalr` call/return pattern to exercise RAS and indirect target prediction.
- Validate that conditional branch rows show both `branch_mispredict=0` and `1` after warmup.

Risks and uncertainty:

- The predictor model determines actual branch taken by comparing current row PC to previous branch target (`BranchPredictionModel.cpp:176-181`); row alignment must be checked.
- `getPc_pt()` clears flags, so instrumentation must read cached state after the normal scheduling call order.
- Predicted-target visibility is incomplete for BHT-only conditional branches unless BTB state is exposed.

### CVA6-BN-003: RAW And Issue-Stage Source Readiness Wait

Minimal fields:

- `uses_rs1`
- `uses_rs2`
- `raw_wait_cycles`
- `raw_blocking_reg`
- `raw_blocking_ready_cycle`

Code locations:

- `StandardRegisterModel.h:37-39`.
- Source read calls in generated scheduler:
  - `perfModel->regModel.getXa()` and `getXb()` appear throughout `CVA6_SchedulingFunction.cpp`.
  - Examples: `bge` source reads at `CVA6_SchedulingFunction.cpp:3647-3650`; `mul` at `:4129-4132`; `div` at `:4659-4662`; `lw` at `:5443`; `sw` at `:6412-6415`.
- Destination ready calls:
  - `regModel.setXd(...)`, e.g. ALU `:3943`, MUL `:4147`, DIV implicitly absent in current snippet for result ready and should be checked during implementation, load `:5465`.

Files/classes/functions to modify:

- `CVA6_PerformanceModel.h`
- `CVA6_PerformanceModel.cpp`
- `CVA6_SchedulingFunction.cpp`
- Optionally `StandardRegisterModel.h` if producer ID is added later.

How to compute:

- Add `getRawReadyA(uint64_t baseCycle)` and `getRawReadyB(uint64_t baseCycle)` helper methods to `CVA6_PerformanceModel`.
- Each helper:
  - calls `regModel.getXa()` or `getXb()` once
  - computes `wait = readyCycle > baseCycle ? readyCycle - baseCycle : 0`
  - updates current row `raw_wait_cycles` to the maximum source wait
  - stores `raw_blocking_reg` as `rs1` or `rs2`
  - stores `raw_blocking_ready_cycle`
  - returns the original ready cycle so scheduling behavior is unchanged.
- Replace scheduler source-read calls:
  - `perfModel->regModel.getXa()` -> `perfModel->getRawReadyA(n_ID_stage)`
  - `perfModel->regModel.getXb()` -> `perfModel->getRawReadyB(n_ID_stage)`
- Use `n_ID_stage` as the issue operand-read base because CVA6 source waits are computed in `IS_stage` from `n_ID_stage`.

Validation microbenchmark:

- Dependent ALU chain: `add x3,x1,x2; add x4,x3,x5`.
- Dependent load-use chain: `ld x3,0(x1); add x4,x3,x5`.
- Dependent mul/div chain to verify later consumer waits.
- Independent instruction stream to confirm `raw_wait_cycles=0`.

Risks and uncertainty:

- No exact producer instruction ID without extending `StandardRegisterModel`.
- Need confirm `rd=0` behavior in shared register model; x0 should not create RAW dependency.
- RAW and divider/load delay can overlap; do not interpret sums as exclusive CPI stack.

### CVA6-BN-004: Clobber / Commit Dependency And Commit Bandwidth

Minimal fields:

- `uses_rd`
- `clobber_wait_cycles`
- `clobber_blocking_reg`
- `clobber_ready_cycle`
- `commit_wait_cycles`

Code locations:

- `ClobberModel.h:25-39`.
- Clobber calls:
  - `n_uA_Clobber = std::max({n_ID_stage, perfModel->clobberModel.getCb_out()})`
  - examples: `jal` at `CVA6_SchedulingFunction.cpp:3933-3938`, `mul` at `:4126`, `div` at `:4655`, `lw` at `:5440`.
- Commit/clobber release:
  - `perfModel->clobberModel.setCb_in(n_Commit)`, examples `CVA6_SchedulingFunction.cpp:3954`, `:4158`, `:4680`, `:5476`.
- Commit capacity:
  - `n_COM_stage = std::max({n_Commit, perfModel->COM_stage.get(1)})`, examples `:3955-3958`, `:4677-4684`, `:5473-5480`.

Files/classes/functions to modify:

- `models/cva6/ClobberModel.h`
- `CVA6_PerformanceModel.h`
- `CVA6_PerformanceModel.cpp`
- `CVA6_SchedulingFunction.cpp`

How to compute:

- Add a performance-model helper `getClobberReady(uint64_t baseCycle)`:
  - calls `clobberModel.getCb_out()`
  - computes `clobber_wait_cycles = max(0, readyCycle - baseCycle)`
  - records `clobber_blocking_reg = rd`
  - records `clobber_ready_cycle = readyCycle`
  - returns `readyCycle`.
- Replace generated clobber calls with `perfModel->getClobberReady(n_ID_stage)`.
- Compute `commit_wait_cycles` in scheduling lambdas after `n_COM_stage`:
  - `commit_wait_cycles = n_COM_stage > n_Commit ? n_COM_stage - n_Commit : 0`
  - set only for rows that reach `COM_stage`.

Validation microbenchmark:

- Many instructions repeatedly writing the same destination register to trigger clobber waits.
- Stream of independent writes to different registers to distinguish clobber wait from commit bandwidth.
- Dense ALU stream to stress `COM_stage` capacity 2.

Risks and uncertainty:

- Static report notes uncertainty whether clobber represents WAW, scoreboard, commit dependency, or a simplified blend.
- `ClobberModel` has a TODO for `rd=0`; instrumentation should not over-attribute x0.
- Commit wait and clobber wait may overlap with EX output-buffer backpressure.

### CVA6-BN-005: D-cache Miss / Non-cacheable Memory Delay

Minimal fields:

- `dcache_miss`
- `dcache_not_cacheable`
- `dcache_delay_cycles`
- `dcache_extra_cycles`
- `memory_wait_cycles`

Code locations:

- `DCacheModel::getDelay()` at `externalModels/src/cva6/DCacheModel.cpp:25-43`.
- `DCacheModel::getInfo_miss()` at `externalModels/include/models/cva6/DCacheModel.h:44`.
- Load scheduler functions:
  - `lw` at `CVA6_SchedulingFunction.cpp:5375`, D-cache call `:5455-5460`
  - `lh` at `:5485`
  - `lhu` at `:5595`
  - `lb` at `:5705`
  - `lbu` at `:5815`
  - `ld` at `:5925`, D-cache call `:6005-6010`
  - `lwu` at `:6035`

Files/classes/functions to modify:

- `models/cva6/DCacheModel.h`
- `models/cva6/DCacheModel.cpp`
- `CVA6_PerformanceModel.h`
- `CVA6_PerformanceModel.cpp`
- `CVA6_SchedulingFunction.cpp`

How to compute:

- Extend `DCacheModel` with last-delay and cacheability getters:
  - `getInfo_miss()`
  - `getInfo_not_cacheable()`
  - `getLastDelay()`
- In each load scheduler, call `getDelay()` once:
  - `uint64_t dDelay = perfModel->dCacheModel.getDelay();`
  - `n_DCache = n_EX_substage_lCtrl + dDelay;`
  - `dcache_extra_cycles = max(0, dDelay - CACHE_DELAY)`
  - `memory_wait_cycles = dcache_extra_cycles`
- Do not instrument stores as D-cache miss delay unless store path is modeled; current CorePerfDSL store flow has `SCtrl -> SUnit` and no `DCache`.

Validation microbenchmark:

- Repeated load from same address for cache-hit baseline.
- Strided loads across more unique cache lines than modeled cache capacity to force misses.
- Load from non-cacheable address range outside `0x80000000..0xC0000000` if test environment can safely map it.

Risks and uncertainty:

- `DCacheModel.cpp:29` explicitly notes missing store address-blocking behavior from another model.
- Cacheability may be difficult to validate if benchmark memory is outside the modeled cacheable range.
- `getDelay()` mutates cache state; do not call it twice per instruction.

### CVA6-BN-006: EX Subpipe Structural Conflicts

Minimal fields:

- `ex_resource_kind`
- `ex_resource_wait_cycles`
- `ex_blocking_resource`

Code locations:

- CorePerfDSL block declarations:
  - `CVA6.corePerfDsl:83-103`
  - `EX_subpipe_mul [blocks: EX_subpipe_alu]`
  - `EX_subpipe_div [blocks: {EX_subpipe_alu, EX_subpipe_mul}]`
- Scheduler IS-stage max expressions:
  - Branch/ALU waits on `EX_substage_alu`, `EX_substage_mul_o`, `EX_substage_div`, e.g. `CVA6_SchedulingFunction.cpp:3652-3654`
  - Mul waits on `EX_substage_mul_i`, `EX_substage_alu`, `EX_substage_div`, e.g. `:4140-4142`
  - Div waits on `EX_substage_div`, e.g. `:4664-4666`
  - Load waits on `EX_substage_lCtrl`, e.g. `:5445-5447`
  - Store waits on `EX_substage_sCtrl`, e.g. `:6417-6419`

Files/classes/functions to modify:

- `CVA6_PerformanceModel.h`
- `CVA6_PerformanceModel.cpp`
- `CVA6_SchedulingFunction.cpp`

How to compute:

- Add setter `setEXResourceInstrumentation(waitCycles, kind, blockingResource)`.
- In each scheduling lambda, compute the difference between the selected EX availability term and the normal issue base:
  - `base = max(n_Issue, n_uA_Clobber, n_uA_OF_A, n_uA_OF_B)` for instructions that have those terms.
  - `resource_ready = max(EX capacity/subpipe terms in the IS-stage max)`
  - `ex_resource_wait_cycles = resource_ready > base ? resource_ready - base : 0`
- Set `ex_resource_kind` by instruction class:
  - `ALU`
  - `MUL`
  - `DIV`
  - `LOAD`
  - `STORE`
- Set `ex_blocking_resource` to the max contributing subpipe where identifiable:
  - `EX_capacity`
  - `EX_substage_alu`
  - `EX_substage_mul_o`
  - `EX_substage_div`
  - `EX_substage_lCtrl`
  - `EX_substage_sCtrl`

Validation microbenchmark:

- Long divider followed by ALU and MUL instructions to show DIV blocking ALU/MUL.
- Multiply-heavy loop to show MUL subpipe blocking ALU if modeled.
- Independent ALU stream to show low or zero resource wait unless EX capacity saturates.

Risks and uncertainty:

- Generated scheduler max expressions do not record which term won; implementation must compare candidates manually.
- Functional-unit latency and resource blocking can overlap; do not sum without caveat.
- String fields in CSV need stable values for analyzer scripts.

### CVA6-BN-007: Variable 64-bit Divider Latency

Minimal fields:

- `divider_delay_cycles`
- `divider_extra_cycles`
- `ex_resource_kind`
- `ex_resource_wait_cycles`

Code locations:

- `DividerModel::getDelay()` at `externalModels/src/cva6/DividerModel.cpp:23-48`.
- `DividerUnsignedModel::getDelay()` at `externalModels/src/cva6/DividerUnsignedModel.cpp:23-44`.
- Signed divider scheduler functions:
  - `div` at `CVA6_SchedulingFunction.cpp:4591`, `n_DIV = n_IS_stage + perfModel->divider.getDelay()` at `:4667-4670`
  - `rem` at `:4689`
  - `divw` at `:4787`
  - `remw` at `:4885`
- Unsigned divider scheduler functions:
  - `divu` at `:4983`, `n_DIVU = n_IS_stage + perfModel->divider_u.getDelay()` at `:5059-5061`
  - `remu` at `:5081`
  - `divuw` at `:5179`
  - `remuw` at `:5277`

Files/classes/functions to modify:

- `CVA6_PerformanceModel.h`
- `CVA6_PerformanceModel.cpp`
- `CVA6_SchedulingFunction.cpp`
- Optionally add read-only last-delay getters in divider model headers if desired.

How to compute:

- In each divider scheduler, call `getDelay()` once and store locally:
  - `uint64_t divDelay = perfModel->divider.getDelay();`
  - `n_DIV = n_IS_stage + divDelay;`
  - `setDividerInstrumentation(divDelay, divDelay > 0 ? divDelay - 1 : 0);`
- For unsigned divider:
  - `uint64_t divDelay = perfModel->divider_u.getDelay();`
  - `n_DIVU = n_IS_stage + divDelay;`
- `divider_delay_cycles` records full model delay.
- `divider_extra_cycles` records extra cycles above a normal 1-cycle EX operation.

Validation microbenchmark:

- Signed and unsigned divide with divisor zero to validate 64-cycle case.
- Operand sweep with small, large, positive, and negative operands to validate variable delay.
- Independent ALU after DIV to validate EX subpipe blocking fields if Step BN-006 is implemented.

Risks and uncertainty:

- `divw/remw/divuw/remuw` use the same 64-bit delay model in the generated scheduler; confirm whether this is intended.
- Avoid double-calling `getDelay()` because it depends on current `instrIndex`.
- Divider delay is not the same as de-overlapped bottleneck contribution when later RAW waits are also counted.

## 6. Minimal Implementation Order

1. Add identity/operand fields to timing CSV.
2. Add simple per-row setters/reset logic in `CVA6_PerformanceModel`.
3. Add I-cache, D-cache, divider, RAW, clobber, commit, branch, and EX resource fields in generated scheduling code.
4. Extend external models only where existing info getters are insufficient:
   - `BranchPredictionModel`
   - `ICacheModel`
   - `DCacheModel`
   - possibly `ClobberModel`
5. Add a CVA6-specific contribution analyzer after traces contain the fields.

## 7. Minimal CSV Consumer Formulas

Initial analyzer formulas should be additive and explicitly non-exclusive:

| Category | Formula |
|---|---|
| I-cache/frontend | `sum(icache_extra_cycles + frontend_wait_cycles)` |
| Branch | `sum(branch_redirect_cycles + branch_predict_path_cycles)` |
| RAW | `sum(raw_wait_cycles)` |
| Clobber/commit | `sum(clobber_wait_cycles + commit_wait_cycles)` |
| D-cache/memory | `sum(memory_wait_cycles)` |
| EX structural | `sum(ex_resource_wait_cycles)` |
| Divider | `sum(divider_extra_cycles)` |

These sums can overlap and must not be presented as a de-overlapped CPI stack.

## 8. Validation Acceptance Criteria

For each validation run, inspect one representative `CVA6_timing_*.csv`, one decoded trace CSV if present, and one `asm_*.txt` file if trace printer is enabled.

Required checks:

- Header includes all identity and mechanism fields.
- `instr_id` is monotonically increasing by emitted timing row.
- `type_id`, `pc`, `rs1`, `rs2`, `rd`, `addr`, `rs1_data`, `rs2_data` are non-empty where expected.
- Each microbenchmark activates at least one nonzero row for its target category.
- Untargeted categories remain zero or are explicitly explained if they also activate.
- Estimated processor cycle count should not change when adding pure instrumentation fields.

## 9. Risks And Uncertainty

- `CVA6_SchedulingFunction.cpp`, `CVA6_Channel.*`, and `CVA6_Monitor.*` are generated-style files and may be overwritten by CorePerfDSL/code generation.
- Some bottleneck fields require external model read-only state; adding instrumentation must not alter model behavior or call stateful getters more times than before.
- RAW, clobber, EX resource, divider, branch, and memory delay can overlap on the same instruction stream; additive totals are useful guidance but not root-cause CPI decomposition.
- Current CVA6 store path does not model D-cache delay, so store memory bottlenecks should be marked missing rather than inferred.
- `ClobberModel` semantics are not fully documented; field names should keep “clobber” rather than overclaim WAW or commit dependency until validated.
- Branch actual-taken logic currently depends on next-row PC comparison inside `BranchPredictionModel`; row alignment must be validated before interpreting branch contribution.
- No stable blocking instruction ID is available unless `StandardRegisterModel` and `ClobberModel` are extended with producer IDs.
