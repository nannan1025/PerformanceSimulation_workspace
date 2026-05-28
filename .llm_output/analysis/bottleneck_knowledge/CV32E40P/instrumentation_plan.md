# CV32E40P Instrumentation Implementation Plan

This is a Step 2 implementation plan only. It does not implement instrumentation, modify source code, or run benchmarks. The plan is based on:

- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/bottleneck_knowledge_map.md`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/trace_fields_gap_analysis.md`
- `code_gen/descriptions/core_perf_dsl/CV32E40P.corePerfDsl`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/monitors/variants/CV32E40P/`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/`

## 1. Minimal Trace Fields Required

The goal is to compute contribution for these potential bottleneck categories:

- RAW dependency
- Branch redirect / static prediction
- Divider latency
- Memory-port / LSU structural timing
- Multiplier latency

Add these minimal per-instruction fields to a new bottleneck instrumentation CSV stream, or append them to the existing CV32E40P timing CSV:

| Field | Type | Needed for | Meaning |
|---|---:|---|---|
| `instr_id` | integer | all | Monotonic global instruction id. |
| `type_id` | integer | all | Existing instruction type id from `Channel::typeId`. |
| `pc` | uint64 | all, branch | Instruction PC. |
| `rs1` | uint64 | RAW | Source register 1 index. |
| `rs2` | uint64 | RAW | Source register 2 index. |
| `rd` | uint64 | RAW, producer tracking | Destination register index. |
| `instr_class` | string/enum | all | Static class such as `arith`, `branch`, `jump`, `load`, `store`, `mul`, `mulh`, `div`, `divu`. |
| `bottleneck_category` | string/enum | all | Dominant category for the row: `raw`, `branch`, `divider`, `memory_port`, `multiplier`, `none`. |
| `raw_wait_cycles` | uint64 | RAW | Max source-register readiness wait. |
| `raw_blocking_reg` | integer | RAW | Register index causing max RAW wait, or `-1`. |
| `raw_blocking_ready_cycle` | uint64 | RAW | Ready cycle of the blocking source register. |
| `branch_is_control` | bool/int | branch | `1` for branch/jump/jalr rows. |
| `branch_taken` | bool/int | branch | Runtime taken flag using current static predictor semantics. |
| `branch_mispredict` | bool/int | branch | Static predict-not-taken mispredict flag. |
| `branch_redirect_cycles` | uint64 | branch | Estimated redirect/fetch wait cycles. |
| `divider_delay_cycles` | uint64 | divider | Return value of `divider.getDelay()` or `divider_u.getDelay()`. |
| `memory_port_wait_cycles` | uint64 | memory-port | Wait caused by modeled WB/DPort serialization. |
| `memory_port_kind` | string/enum | memory-port | `DPort_R`, `DPort_W`, or `none`. |
| `multiplier_delay_cycles` | uint64 | multiplier | `1` for `mul`, `5` for `mulh/mulhu/mulhsu`. |
| `resource_wait_cycles` | uint64 | structural/resource | Generic wait cycles for the selected resource. |
| `blocking_resource` | string/enum | all | `Xa`, `Xb`, `Pc`, `DIV`, `DIVU`, `DPort_R`, `DPort_W`, `MUL`, `MULH`, `none`. |

Fields deliberately not required for the minimal implementation:

- `blocking_instruction_id`: useful later, but requires extending `StandardRegisterModel` to store producer ids.
- `cache_hit_or_miss`: no CV32E40P cache model was found for the base model.
- exact per-stage enter cycles: useful later, but the existing timing trace already prints stage completion cycles.

## 2. Exact Code Locations Where Fields Should Be Added

### Performance Model State And Output

Modify:

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/include/CV32E40P_PerformanceModel.h`

Add to class `CV32E40P::CV32E40P_PerformanceModel`:

- channel pointers:
  - `uint64_t* typeId_ptr`
  - `uint64_t* rs1_ptr`
  - `uint64_t* rs2_ptr`
  - `uint64_t* rd_ptr`
  - `uint64_t* pc_ptr`
  - `uint64_t* brTarget_ptr`
  - `uint64_t* rs2_data_ptr`
- global instruction counter:
  - `uint64_t globalInstrId`
- last-row instrumentation fields matching the CSV schema.
- helper methods:
  - `void resetInstrumentation(const char* instrClass)`
  - `void setRawInstrumentation(uint64_t baseCycle, uint64_t rs1Ready, uint64_t rs2Ready, bool usesRs1, bool usesRs2)`
  - `void setBranchInstrumentation(bool isControl, bool taken, bool mispredict, uint64_t redirectCycles)`
  - `void setDividerInstrumentation(uint64_t delay, const char* resource)`
  - `void setMemoryPortInstrumentation(uint64_t waitCycles, const char* portKind)`
  - `void setMultiplierInstrumentation(uint64_t delay, const char* resource)`
  - `void finalizeInstrumentationCategory()`

Modify:

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_PerformanceModel.cpp`

Add logic in:

- `CV32E40P_PerformanceModel::connectChannel(Channel*)`
  - bind the new pointers from `CV32E40P_Channel`.
- `CV32E40P_PerformanceModel::getPrintHeader()`
  - append the new CSV columns after `WB_stage`.
- `CV32E40P_PerformanceModel::getPipelineStream()`
  - append the current instruction instrumentation field values after `WB_stage`.

### Channel Data Already Available

The current trace channel already provides most basic fields:

- `CV32E40P_Channel.h:36-41`
  - `rs1`
  - `rs2`
  - `rd`
  - `pc`
  - `brTarget`
  - `rs2_data`

No minimal channel extension is required unless a future implementation wants `addr` or additional decoded immediates.

### Monitor Connections

The current monitor connects existing channel fields:

- `CV32E40P_Monitor.cpp:31-38`
- `CV32E40P_Monitor.cpp:46-58`
- `CV32E40P_Monitor.cpp:62-76`

For this minimal plan, no monitor change is strictly required because `PerformanceModel::connectChannel()` can read already-populated channel arrays. Only change the monitor if a later version adds new decoded trace values such as `addr`.

### Scheduling Function Instrumentation

Modify:

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_SchedulingFunction.cpp`

Add instrumentation at these exact mechanism points:

| Mechanism | Scheduling locations |
|---|---|
| RAW | Around source-read timing, for example `n_uA_OF_A = std::max({n_IF_stage, perfModel->regModel.getXa()})` and `n_uA_OF_B = std::max({n_IF_stage, perfModel->regModel.getXb()})`. |
| Branch | Around branch/jump calls to `perfModel->staBranchPredModel.setPc_np(...)` and IF-stage `staBranchPredModel.getPc()` dependency. |
| Divider | Around `n_DIV = n_ID_stage + perfModel->divider.getDelay()` and `n_DIVU = n_ID_stage + perfModel->divider_u.getDelay()`. |
| Memory-port | Around load/store `n_EX_stage = std::max({n_LSU, perfModel->WB_stage})`, then `n_DPort_R = n_EX_stage + 1` or `n_DPort_W = n_EX_stage + 1`. |
| Multiplier | Around `n_MUL = n_ID_stage + 1` and `n_MULH = n_ID_stage + 5`. |

Known generated function anchors from static search:

- `schedulingFunction_mul`: around `CV32E40P_SchedulingFunction.cpp:979`
- `schedulingFunction_mulh`: around `CV32E40P_SchedulingFunction.cpp:1026`
- `schedulingFunction_mulhu`: around `CV32E40P_SchedulingFunction.cpp:1073`
- `schedulingFunction_mulhsu`: around `CV32E40P_SchedulingFunction.cpp:1120`
- `schedulingFunction_div`: around `CV32E40P_SchedulingFunction.cpp:1167`
- `schedulingFunction_rem`: around `CV32E40P_SchedulingFunction.cpp:1214`
- `schedulingFunction_divu`: around `CV32E40P_SchedulingFunction.cpp:1261`
- `schedulingFunction_remu`: around `CV32E40P_SchedulingFunction.cpp:1308`
- store path examples: around `CV32E40P_SchedulingFunction.cpp:1628`, `1681`, `1716`
- load path examples: around `CV32E40P_SchedulingFunction.cpp:1769`, `1838`, `1889`, `1940`, `1991`
- branch/jump path examples: around `CV32E40P_SchedulingFunction.cpp:2024`, `2333`, `2375`

### External Model Optional Additions

Do not modify these for the minimal plan unless required:

- `StandardRegisterModel.h`
  - Optional later: add producer id tracking and ignore `rd == 0`.
- `StaticBranchPredictModel.h/.cpp`
  - Optional later: add non-mutating info getters for predicted/taken/mispredict.
- `DividerModel.cpp` and `DividerUnsignedModel.cpp`
  - No change needed if scheduling functions store `getDelay()` return values in locals.

## 3. Files, Classes, And Functions That Need Modification

Minimal implementation:

| File | Class/function | Change |
|---|---|---|
| `CV32E40P_PerformanceModel.h` | `CV32E40P_PerformanceModel` | Add channel pointers, instrumentation fields, helper declarations. |
| `CV32E40P_PerformanceModel.cpp` | `connectChannel` | Bind channel pointers. |
| `CV32E40P_PerformanceModel.cpp` | `getPrintHeader` | Append CSV columns. |
| `CV32E40P_PerformanceModel.cpp` | `getPipelineStream` | Append field values. |
| `CV32E40P_PerformanceModel.cpp` | new helper methods | Reset, set, and finalize bottleneck contribution fields. |
| `CV32E40P_SchedulingFunction.cpp` | all scheduling lambdas | Call reset/finalize; add mechanism-specific setters. |

Not required for minimal implementation:

| File | Reason |
|---|---|
| `CV32E40P_Channel.h/.cpp` | Existing fields cover minimal plan. |
| `CV32E40P_Monitor.cpp` | Existing monitor already populates needed fields. |
| `CV32E40P_InstructionMonitors.cpp` | Existing per-instruction decoded fields are enough for minimal plan. |
| `StandardRegisterModel.h` | Needed only for exact `blocking_instruction_id`. |
| `StaticBranchPredictModel.cpp` | Avoid changing until non-mutating predictor info is required. |

## 4. How To Compute Each Field

### Common Row Fields

For each scheduling lambda:

1. Call `resetInstrumentation("<class>")` at the beginning.
2. Read current instruction index from `PerformanceModel::instrIndex`.
3. Fill:
   - `instr_id = globalInstrId`
   - `type_id = typeId_ptr[instrIndex]`
   - `pc = pc_ptr[instrIndex]`
   - `rs1 = rs1_ptr[instrIndex]`
   - `rs2 = rs2_ptr[instrIndex]`
   - `rd = rd_ptr[instrIndex]`
4. At the end of the scheduling lambda, call `finalizeInstrumentationCategory()`.
5. Increment `globalInstrId` after row output or during reset for the next row. Prefer incrementing in `getPipelineStream()` after streaming to keep row ids aligned with output.

### RAW Dependency Contribution

For instructions using `rs1`:

```cpp
uint64_t rs1Ready = perfModel->regModel.getXa();
uint64_t waitA = (rs1Ready > n_IF_stage) ? (rs1Ready - n_IF_stage) : 0;
```

For instructions using `rs2`:

```cpp
uint64_t rs2Ready = perfModel->regModel.getXb();
uint64_t waitB = (rs2Ready > n_IF_stage) ? (rs2Ready - n_IF_stage) : 0;
```

Then:

- `raw_wait_cycles = max(waitA, waitB)`
- `raw_blocking_reg = rs1` if `waitA >= waitB`, else `rs2`
- `raw_blocking_ready_cycle = rs1Ready` or `rs2Ready`
- `blocking_resource = Xa` or `Xb` if RAW is dominant

For instructions without a source operand, set RAW fields to zero / `-1`.

### Branch Contribution

For `Branch_Ra_Rb`, `jal`, and `jalr`:

- `branch_is_control = 1`
- `branch_taken`:
  - conditional branch: match current static predictor semantics with `pc == brTarget`
  - `jal`: always `1`
  - `jalr`: always `1`
- `branch_mispredict`:
  - static predictor is predict-not-taken, so conditional branch mispredict is `branch_taken`
  - for `jal` and `jalr`, treat as redirect-producing control flow; set `branch_mispredict = 1` unless later predictor semantics distinguish unconditional jumps
- `branch_redirect_cycles`:
  - compute from existing branch path timing without extra calls to `StaticBranchPredictModel::getPc()`, because `getPc()` mutates `branchInstr`
  - use `max(0, n_IF_stage_after_branch_dependency - n_IF_stage_without_branch_dependency)` if both values are available
  - if not available in v1, use `max(0, n_ID_stage_or_EX_branch_resolution - n_PCGen)` as a conservative redirect proxy and document it

### Divider Contribution

For `div` and `rem`:

```cpp
uint64_t divDelay = perfModel->divider.getDelay();
n_DIV = n_ID_stage + divDelay;
perfModel->setDividerInstrumentation(divDelay, "DIV");
```

For `divu` and `remu`:

```cpp
uint64_t divDelay = perfModel->divider_u.getDelay();
n_DIVU = n_ID_stage + divDelay;
perfModel->setDividerInstrumentation(divDelay, "DIVU");
```

Set:

- `divider_delay_cycles = divDelay`
- `resource_wait_cycles = divDelay`
- `blocking_resource = DIV` or `DIVU` if divider is dominant

### Memory-Port Contribution

For stores:

```cpp
n_LSU = n_ID_stage + 1;
memoryWait = (perfModel->WB_stage > n_LSU) ? (perfModel->WB_stage - n_LSU) : 0;
n_EX_stage = std::max({n_LSU, perfModel->WB_stage});
n_DPort_W = n_EX_stage + 1;
```

Set:

- `memory_port_wait_cycles = memoryWait`
- `memory_port_kind = DPort_W`
- `blocking_resource = DPort_W` if memory wait is dominant

For loads, same logic with `DPort_R`.

This is not cache miss accounting. It measures modeled WB/DPort serialization only.

### Multiplier Contribution

For `mul`:

- `multiplier_delay_cycles = 1`
- `blocking_resource = MUL`

For `mulh`, `mulhu`, `mulhsu`:

- `multiplier_delay_cycles = 5`
- `blocking_resource = MULH`

Contribution can be interpreted later as:

```text
extra_multiplier_cycles = max(0, multiplier_delay_cycles - 1)
```

because a normal ALU EX path is one cycle.

### Dominant Category Selection

At `finalizeInstrumentationCategory()`:

1. Compute candidate values:
   - RAW: `raw_wait_cycles`
   - Branch: `branch_redirect_cycles`
   - Divider: `divider_delay_cycles`
   - Memory: `memory_port_wait_cycles`
   - Multiplier: `max(0, multiplier_delay_cycles - 1)`
2. Pick the largest nonzero as `bottleneck_category`.
3. If all are zero, set `bottleneck_category = none`.

## 5. Minimal CSV Schema

Recommended header:

```csv
IF_stage,ID_stage,EX_stage,WB_stage,instr_id,type_id,pc,rs1,rs2,rd,instr_class,bottleneck_category,raw_wait_cycles,raw_blocking_reg,raw_blocking_ready_cycle,branch_is_control,branch_taken,branch_mispredict,branch_redirect_cycles,divider_delay_cycles,memory_port_wait_cycles,memory_port_kind,multiplier_delay_cycles,resource_wait_cycles,blocking_resource
```

Example row shape:

```csv
10,11,12,0,42,0,0x80000000,1,2,3,arith,none,0,-1,0,0,0,0,0,0,0,none,0,0,none
```

Encoding rules:

- Numeric values should be decimal except `pc`, which may remain decimal for CSV simplicity. If printed hex, use consistent `0x...` formatting.
- Boolean fields should be `0` or `1`.
- Missing resource/string fields should use `none`.
- Missing register should use `-1`.

## 6. Validation Microbenchmarks

These should be tiny assembly or C-with-inline-assembly tests, not full benchmark runs.

### RAW Dependency

Pattern:

```asm
add x5, x1, x2
add x6, x5, x3
add x7, x6, x4
```

Expected:

- dependent `add` rows have `raw_wait_cycles > 0`
- `raw_blocking_reg` matches the producer destination
- non-dependent filler instructions have `raw_wait_cycles = 0`

### Branch Redirect

Pattern:

```asm
li x5, 10
loop:
addi x5, x5, -1
bne x5, x0, loop
```

Expected:

- branch rows have `branch_is_control = 1`
- taken loop branches have `branch_taken = 1`
- taken loop branches have `branch_mispredict = 1` under static predict-not-taken
- final not-taken branch has `branch_taken = 0`

### Divider

Pattern:

```asm
li x1, 100
li x2, 0
div x3, x1, x2
li x2, 1
div x4, x1, x2
li x2, 16
divu x5, x1, x2
```

Expected:

- divider rows have nonzero `divider_delay_cycles`
- different divisors produce different delay values
- non-divider rows have `divider_delay_cycles = 0`

### Memory-Port

Pattern:

```asm
lw x5, 0(x10)
lw x6, 4(x10)
sw x5, 8(x10)
sw x6, 12(x10)
```

Expected:

- load rows have `memory_port_kind = DPort_R`
- store rows have `memory_port_kind = DPort_W`
- `memory_port_wait_cycles` is nonzero only when modeled WB/DPort serialization occurs

### Multiplier

Pattern:

```asm
mul x5, x1, x2
mulh x6, x1, x2
mulhu x7, x1, x2
mulhsu x8, x1, x2
```

Expected:

- `mul` has `multiplier_delay_cycles = 1`
- high-multiply rows have `multiplier_delay_cycles = 5`
- high-multiply contribution is larger than plain multiply

## 7. Risks And Uncertainty

- `StaticBranchPredictModel::getPc()` mutates `branchInstr`; do not call it additional times only for instrumentation.
- `branch_taken = (pc == brTarget)` follows current model behavior but may be semantically fragile. Runtime validation is required.
- `StandardRegisterModel` does not track producer instruction ids. Minimal v1 reports blocking register and ready cycle, not `blocking_instruction_id`.
- `StandardRegisterModel` has a TODO for `rd = 0`; false RAW dependencies through x0 are possible unless corrected later.
- Base CV32E40P has no cache model found. Memory contribution is only DPort/WB structural timing.
- Direct edits to generated files may be overwritten by future code generation. A later robust implementation should move this instrumentation into generator templates.
- Existing timing CSV row alignment depends on `PerformanceEstimator::execute()` streaming once per instruction after `callSchedulingFunction()`. Preserve this behavior.

## Recommended Implementation Order

1. Add instrumentation fields and helper methods to `CV32E40P_PerformanceModel`.
2. Append CSV header and row output in `getPrintHeader()` and `getPipelineStream()`.
3. Add reset/finalize calls in every CV32E40P scheduling lambda.
4. Add mechanism-specific setters for multiplier and divider first, because they are least ambiguous.
5. Add memory-port wait.
6. Add RAW wait.
7. Add branch fields last, because predictor state mutation makes it the riskiest.
8. Validate with the five microbenchmarks before using full benchmark traces.
