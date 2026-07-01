# Rocket Trace Field Instrumentation Plan

This plan proposes additional Rocket instruction timing trace fields that explain why stage timing gaps occur. The current timing trace records only:

```text
IF,ID,EX,MEM,WB
```

Those columns show *where* cycles accumulated, but not *why*.

## Recommendation: Temporary First, Permanent Later

Because the Rocket backend files under:

```text
etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET
```

are generated from CorePerfDSL, manual edits there can be overwritten when the simulator is regenerated.

Recommended approach:

1. Add the first implementation as temporary/manual instrumentation in generated Rocket files.
2. Use it to validate which fields actually help debug timing inaccuracies.
3. Move the stable field set into generator/CorePerfDSL-supported trace output.

Permanent support is best for fields that are broadly useful and architecture-model-neutral:

- instruction identity,
- PC,
- operands,
- stage gaps,
- RAW wait cycles,
- cache miss/delay,
- branch taken/mispredict,
- divider delay.

Temporary support is best for fields that depend heavily on generated local variable names or exact scheduling implementation details:

- exact stage blocker,
- structural max-term attribution,
- cache set/tag/replacement details,
- experimental stall classification.

## Why Current Timing Traces Are Insufficient

The current timing trace records five stage cycle columns only:

```text
IF,ID,EX,MEM,WB
```

In an ideal simple case, adjacent stages are usually separated by about one cycle:

```text
ID - IF ~= 1
EX - ID ~= 1
MEM - EX ~= 1
WB - MEM ~= 1
```

When a gap is larger than expected, the current trace does not say whether the cause was:

- a RAW register dependency,
- branch redirect or misprediction,
- ICache miss or fetch blocking,
- DCache miss,
- divider latency,
- structural/resource conflict,
- writeback/commit pressure,
- some other modeled stall.

The user must manually correlate timing traces with perf traces, assembly traces, and generated scheduling code. That is slow and error-prone.

## Must-Have Fields

These fields should be added first because they directly explain common Rocket timing gaps.

| Field | Meaning | Related stage/behavior | Timing-inaccuracy reason diagnosed | Likely source | Difficulty | Support type |
|---|---|---|---|---|---|---|
| `instr_id` | Monotonic row id in timing trace | All stages | Aligns timing/perf/asm rows | `ROCKET_PerformanceModel` counter | Low | Permanent |
| `pc` | Instruction PC | All stages | Joins timing with asm/perf traces | `ROCKET_Channel::pc` | Low | Permanent |
| `type_id` | Generated instruction scheduling id | All stages | Groups timing behavior by instruction kind | `SchedulingFunction` id or generated instruction metadata | Medium | Permanent |
| `mnemonic` | Instruction mnemonic | All stages | Human-readable grouping and debugging | Scheduling function name/printer metadata | Medium | Permanent |
| `rs1` | Source register 1 index | ID | RAW dependency diagnosis | `ROCKET_Channel::rs1` | Low | Permanent |
| `rs2` | Source register 2 index | ID | RAW dependency diagnosis | `ROCKET_Channel::rs2` | Low | Permanent |
| `rd` | Destination register index | WB | Producer/consumer dependency diagnosis | `ROCKET_Channel::rd` | Low | Permanent |
| `uses_rs1` | Whether `rs1` is semantically valid | ID | Avoids false RAW interpretation | instruction group/type metadata | Medium | Permanent |
| `uses_rs2` | Whether `rs2` is semantically valid | ID | Avoids false RAW interpretation | instruction group/type metadata | Medium | Permanent |
| `uses_rd` | Whether `rd` is semantically valid | WB | Avoids false producer interpretation | instruction group/type metadata | Medium | Permanent |
| `raw_wait_cycles` | Max register-read wait beyond decode baseline | ID | Data dependency | wrapper around `regModel.getXa()` and `regModel.getXb()` | Medium | Permanent |
| `raw_blocking_reg` | Register causing max RAW wait | ID | Data dependency | `rs1`/`rs2` plus register ready cycles | Medium | Permanent |
| `raw_blocking_ready_cycle` | Cycle when blocking source register becomes ready | ID | Data dependency | `StandardRegisterModel` ready value | Medium | Permanent |
| `icache_delay_cycles` | ICache delay beyond normal 1-cycle hit | IF | ICache miss/fetch wait | local `iCacheModel.getDelay()` result | Low | Permanent |
| `icache_miss` | Whether current fetch missed | IF | ICache miss | `ICacheModel::isMiss` exposed by getter | Low | Permanent |
| `dcache_delay_cycles` | DCache delay beyond normal 1-cycle hit | MEM | DCache miss/data wait | local `dCacheModel.getDelay()` result | Low | Permanent |
| `dcache_miss` | Whether current load/store missed | MEM | DCache miss | `DCacheModel::isMiss` exposed by getter | Low | Permanent |
| `branch_is_control` | Whether instruction is branch/jump/jalr | IF/MEM | Control-flow attribution | scheduling function or instruction type | Low | Permanent |
| `branch_taken` | Actual taken result | MEM/redirect | Branch behavior | `BranchPredictionModel::isTaken` exposed by getter | Medium | Permanent |
| `branch_mispredict` | Whether prediction was wrong | IF/MEM | Branch flush/mispredict | `BranchPredictionModel::isMispredict` exposed by getter | Medium | Permanent |
| `branch_redirect_cycles` | Cycles attributed to redirect/flush | IF/MEM | Branch flush penalty | `Pc_mp`, `Pc_pt`, `n_Branch` instrumentation | Medium | Permanent |
| `divider_delay_cycles` | Divider extra cycles beyond a 1-cycle baseline | EX | Divider delay | `divider.getDelay()`, `divider_u.getDelay()` | Low now; medium if realistic divider delay is re-enabled | Permanent |

### Notes On Must-Have Fields

`type_id` and `mnemonic` overlap. If implementation time is tight, add `type_id` first because scheduling functions already carry numeric ids. Add `mnemonic` later if the trace consumer needs human-readable timing files without joining against the assembly trace.

`divider_delay_cycles` will initially be zero if defined as `getDelay() - 1`, because Rocket divider `getDelay()` currently returns `1`. This is still useful: it proves the current model is not injecting divider stalls. Re-enabling the realistic helper functions should be a separate modeling decision.

## Useful Fields

These fields improve usability and speed up post-processing, but they are less essential than the cause-specific fields above.

| Field | Meaning | Related stage/behavior | Timing-inaccuracy reason diagnosed | Likely source | Difficulty | Support type |
|---|---|---|---|---|---|---|
| `stage_gap_if_id` | `ID - IF` | IF/ID | Frontend or decode stalls | timing stream | Low | Permanent |
| `stage_gap_id_ex` | `EX - ID` | ID/EX | RAW or EX resource stalls | timing stream | Low | Permanent |
| `stage_gap_ex_mem` | `MEM - EX` | EX/MEM | DCache, store, resource stalls | timing stream | Low | Permanent |
| `stage_gap_mem_wb` | `WB - MEM` | MEM/WB | Writeback/commit delay | timing stream | Low | Permanent |
| `stall_primary_reason` | Best-effort stall category | All stages | Quick triage | derived from diagnostic fields | Medium | Temporary first |
| `mem_addr` | Load/store effective address | EX/MEM | DCache locality and miss cause | `ROCKET_Channel::addr` | Low | Permanent |
| `brTarget` | Branch/jump target | Branch/jump | Control-flow debugging | `ROCKET_Channel::brTarget` | Low | Permanent |
| `branch_predicted_taken` | Predictor direction decision | IF | Wrong-direction prediction | `BranchPredictionModel::branchPredictedTaken` exposed by getter | Medium | Permanent |
| `btb_hit` | Whether BTB had a predicted target | IF/JALR | JALR target miss | Branch target buffer lookup instrumentation | Medium | Optional permanent |
| `ras_used` | Whether return-address stack was used | JAL/JALR | Call/return prediction behavior | BranchPredictionModel/RAS instrumentation | Medium | Optional permanent |

### Suggested `stall_primary_reason` Values

Use a small string enum:

```text
none
raw_dependency
branch_mispredict
branch_redirect
icache_miss
dcache_miss
divider
structural
writeback
unknown
```

Start this as temporary derived instrumentation. It should not replace the raw fields, because a single instruction can have more than one contributing delay.

## Optional Fields

These fields are useful for detailed model debugging but should not be added to the default permanent trace until there is a clear consumer.

| Field | Meaning | Related stage/behavior | Timing-inaccuracy reason diagnosed | Likely source | Difficulty | Support type |
|---|---|---|---|---|---|---|
| `icache_set` | ICache set index | IF | Cache conflict analysis | ICacheModel internals | Medium | Temporary |
| `icache_tag` | ICache tag | IF | Cache conflict analysis | ICacheModel internals | Medium | Temporary |
| `dcache_set` | DCache set index | MEM | Cache conflict analysis | DCacheModel internals | Medium | Temporary |
| `dcache_tag` | DCache tag | MEM | Cache conflict analysis | DCacheModel internals | Medium | Temporary |
| `cache_replaced_way` | Replacement way selected by cache model | IF/MEM | Replacement behavior | cache model `updateCache()` and LFSR path | Medium | Temporary |
| `structural_wait_cycles` | Delay from previous stage/resource occupancy | All stages | Structural/resource conflict | generated scheduling max inputs such as `perfModel->ID`, `EX`, `MEM`, `WB` | High | Temporary first |
| `stage_blocker` | Exact max term that selected a stage cycle | All stages | Full timing attribution | generated local variables such as `n_ICache`, `n_DCache`, `n_uA_OF_A` | High | Temporary first |

`stage_blocker` is powerful but fragile because it depends on generated local variable names and max-expression structure. It is better implemented in the generator than hand-maintained in generated C++.

## Likely Source Locations

| Area | Current location | Values to extract |
|---|---|---|
| Rocket timing stream | `variants/ROCKET/src/ROCKET_PerformanceModel.cpp` | new CSV columns, stage gaps, per-instruction instrumentation reset |
| Rocket timing state | `variants/ROCKET/include/ROCKET_PerformanceModel.h` | pointers to channel values, instrumentation fields, helper methods |
| Rocket scheduling functions | `variants/ROCKET/src/ROCKET_SchedulingFunction.cpp` | local delay values, RAW wrappers, branch/cache/divider instrumentation calls |
| Rocket channel | `variants/ROCKET/include/ROCKET_Channel.h`, `src/ROCKET_Channel.cpp` | existing trace values: `pc`, `rs1`, `rs2`, `rd`, `brTarget`, `addr`, divider operands |
| ICache model | `externalModels/include/models/rocket/ICacheModel.h`, `src/rocket/ICacheModel.cpp` | miss flag, delay, optional set/tag/replacement metadata |
| DCache model | `externalModels/include/models/rocket/DCacheModel.h`, `src/rocket/DCacheModel.cpp` | miss flag, delay, optional set/tag/replacement metadata |
| Branch predictor | `externalModels/include/models/rocket/BranchPredictionModel.h`, `src/rocket/BranchPredictionModel.cpp` | taken, mispredict, predicted taken, BTB/RAS events |
| Register model | `externalModels/include/models/common/StandardRegisterModel.h` | ready cycles for `rs1` and `rs2` |
| Divider models | `externalModels/include/models/rocket/DividerModel.h`, `DividerUnsignedModel.h`, `src/rocket/*.cpp` | divider delay |
| Current traces | `trace_output/ROCKET/rocket_aha-mont64/{timing,perf,asm}` | validation and row alignment |

## Implementation Strategy

### Step 1: Mirror The Existing CV32E40P Instrumentation Pattern

There is already a useful precedent in:

```text
etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P
```

That backend manually adds fields such as:

- `instr_id`
- `pc`
- operands,
- divider delay,
- RAW wait cycles,
- branch fields,
- memory port wait fields.

Use the same pattern for Rocket:

1. Add timing-trace state fields to `ROCKET_PerformanceModel`.
2. Connect channel pointers in `connectChannel()`.
3. Extend `getPipelineStream()` and `getPrintHeader()`.
4. Reset per-instruction instrumentation fields after streaming each row.

### Step 2: Add Rocket PerformanceModel Helper Methods

Add helper methods similar to:

```cpp
uint64_t getRawReadyA(uint64_t baseCycle);
uint64_t getRawReadyB(uint64_t baseCycle);
void setDividerDelay(uint64_t delay);
void setICacheInstrumentation(uint64_t delay, bool miss);
void setDCacheInstrumentation(uint64_t delay, bool miss);
void setBranchInstrumentation(bool isControl, bool taken, bool mispredict, uint64_t redirectCycles);
```

`getRawReadyA()` and `getRawReadyB()` should:

1. call `regModel.getXa()` or `regModel.getXb()`,
2. compare the ready cycle against the decode baseline,
3. record the largest wait,
4. record the blocking register and ready cycle.

### Step 3: Update Generated Rocket Scheduling Functions Manually For The Experiment

For the first pass, manually edit `ROCKET_SchedulingFunction.cpp`.

Replace direct register ready reads:

```cpp
perfModel->regModel.getXa()
perfModel->regModel.getXb()
```

with:

```cpp
perfModel->getRawReadyA(n_Decoder)
perfModel->getRawReadyB(n_Decoder)
```

Store cache delays in local variables before using them:

```cpp
uint64_t iCacheDelay = perfModel->iCacheModel.getDelay();
n_ICache = n_Enter + iCacheDelay;
perfModel->setICacheInstrumentation(iCacheDelay > 0 ? iCacheDelay - 1 : 0,
                                    perfModel->iCacheModel.getMiss());
```

For DCache:

```cpp
uint64_t dCacheDelay = perfModel->dCacheModel.getDelay();
n_DCache = n_EX + dCacheDelay;
perfModel->setDCacheInstrumentation(dCacheDelay > 0 ? dCacheDelay - 1 : 0,
                                    perfModel->dCacheModel.getMiss());
```

For divider:

```cpp
uint64_t divDelay = perfModel->divider.getDelay();
n_DIV = n_ID + divDelay;
perfModel->setDividerDelay(divDelay > 0 ? divDelay - 1 : 0);
```

For branches and jumps, record:

- whether the instruction is a control-flow instruction,
- predicted taken if available,
- actual taken,
- mispredict,
- redirect penalty.

### Step 4: Add External Model Getters

Add minimal non-invasive getters:

For ICache:

```cpp
bool getMiss() const;
uint64_t getLastDelay() const;
```

For DCache:

```cpp
bool getMiss() const;
uint64_t getLastDelay() const;
```

For BranchPredictionModel:

```cpp
bool getTaken() const;
bool getMispredict() const;
bool getPredictedTaken() const;
```

If more detailed fields are later needed, add temporary getters for BTB/RAS/cache set/tag metadata.

### Step 5: Keep Divider Modeling Decision Separate

The Rocket divider models already contain realistic signed/unsigned delay helper functions, but `getDelay()` currently returns `1`.

Do not silently change divider timing while adding trace fields. First add `divider_delay_cycles`; it will show zero extra cycles under the current model. Then decide separately whether to re-enable:

```cpp
rocketSignedDividerDelay(rs1, rs2, 64)
rocketUnsignedDividerDelay(rs1, rs2, 64)
```

Changing this affects simulator timing behavior, not just trace visibility.

### Step 6: Move Stable Fields Into Permanent Generator/CorePerfDSL Support

After validating the temporary manual instrumentation:

1. Add stable trace field declarations to the model/generator flow.
2. Teach the generator to emit timing-trace identity and diagnostic fields.
3. Keep temporary-only detailed debug fields behind a build flag or debug trace mode.

## Proposed Timing CSV Header

First-pass Rocket timing header:

```text
IF,ID,EX,MEM,WB,
instr_id,type_id,pc,rs1,rs2,rd,uses_rs1,uses_rs2,uses_rd,
stage_gap_if_id,stage_gap_id_ex,stage_gap_ex_mem,stage_gap_mem_wb,
raw_wait_cycles,raw_blocking_reg,raw_blocking_ready_cycle,
icache_delay_cycles,icache_miss,
dcache_delay_cycles,dcache_miss,mem_addr,
branch_is_control,branch_taken,branch_mispredict,branch_predicted_taken,branch_redirect_cycles,brTarget,
divider_delay_cycles,
stall_primary_reason
```

If the CSV width becomes inconvenient, defer `stall_primary_reason`, `branch_predicted_taken`, and `mnemonic` to the second pass.

## Test Plan

After implementing the instrumentation:

1. Build the Rocket backend.
2. Run a small Rocket simulation and generate timing/perf/asm traces.
3. Confirm the timing CSV header contains the new fields.
4. Confirm every timing row has the same number of columns as the header.
5. Cross-check `pc`, `rs1`, `rs2`, `rd`, `addr`, and `brTarget` against the perf trace and assembly trace.
6. Use traces containing dependent ALU/load instructions and confirm `raw_wait_cycles` is nonzero where expected.
7. Use branch/jump/jalr traces and confirm branch fields are populated only for control-flow instructions.
8. Use cold fetch behavior and confirm ICache miss/delay fields are visible.
9. Use load/store traces and confirm DCache miss/delay fields are visible.
10. Use div/rem instructions and confirm `divider_delay_cycles` reports the currently modeled behavior.
11. Confirm irrelevant fields default to `0`, `-1`, or `"none"` consistently.

## Assumptions And Defaults

- Add documentation files at the workspace root.
- Treat generated Rocket stage `WB` as the conceptual commit/complete stage unless later trace post-processing renames it to `COM`.
- Keep first-pass instrumentation manual and temporary because Rocket generated files can be overwritten.
- Make stable, broadly useful fields permanent in the generator/CorePerfDSL flow after validation.
- Do not change functional timing behavior while only adding trace fields.
- Do not re-enable variable divider latency as part of trace-field instrumentation unless explicitly requested.
