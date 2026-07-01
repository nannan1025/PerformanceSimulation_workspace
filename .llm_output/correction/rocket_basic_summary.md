# Rocket Basic Simulator Summary

This note summarizes the current Rocket performance simulator model from:

- `.llm_output/correction/ROCKET_0427.corePerfDsl`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels`
- `trace_output/ROCKET/rocket_aha-mont64`

## Workflow Context

The intended workflow is:

```text
CorePerfDSL -> generate simulator -> run programs on generated simulator -> output instruction traces
```

For Rocket, `.llm_output/correction/ROCKET_0427.corePerfDsl` is the source model that drives the generated scheduling functions, timing variables, trace values, channel wiring, and printer behavior.

## CorePerfDSL Rocket Model

The Rocket CorePerfDSL model defines a 5-stage in-order pipeline:

```text
IF -> ID -> EX -> MEM -> WB
```

The stages are:

| Stage | CorePerfDSL name | Main modeled behavior |
|---|---|---|
| IF | `IF` | PC generation/correction, cache block handling, PC prediction, ITLB, ICache, branch/jump prediction |
| ID | `ID` | decode, operand fetch for source registers |
| EX | `EX` | ALU, branch ALU, address calculation, MUL, DIV, DIVU, DTLB, LSU request |
| MEM | `MEM` | branch resolve, DCache, store commit, flush in MEM, pass-through |
| WB | `WB` | load writeback, CSR retire, register writeback, flush in WB, pass-through |

The user-facing conceptual timing trace may describe these as `IF, IS, EX, MEM, COM`, but the generated Rocket code currently names them `IF, ID, EX, MEM, WB`.

## Microactions And Resources

The DSL breaks each instruction into microactions. Important resources and connectors include:

- `PC_Gen`, `BPU`, `ITLB`, `Decoder`, `ALU`, `Branch`, `DTLB`, `CSR`, `Reg`, `LSUReq`, `LoadWB`, `StoreCommit`
- `ICache(iCacheModel)`
- `DCache(dCacheModel)`
- `MUL`, `DIV(divider)`, `DIVU(divider_u)`
- flush/pass resources: `FlushMem`, `FlushWb`, `EXPass`, `MEMPass`, `WBPass`
- PC/control connectors: `Pc_mp`, `Pc_pt`, `Pc_p`, `Pc_p_j`, `Pc_p_jr`, `Pc_c`
- ICache connectors: `Ic_out`, `Ic_in`
- register dependency connectors: `Xa`, `Xb`, `Xd`

The DSL maps instruction groups to microactions. Examples:

- Integer ALU instructions use operand fetch, ALU, MEM pass, and register writeback.
- Loads use operand fetch, address calculation, DTLB, LSU request, DCache, load writeback, and register writeback.
- Stores use operand fetch, address calculation, DTLB, LSU request, DCache, and store commit.
- Branches use branch prediction, operand fetch, branch ALU, branch resolve, flush in MEM, and WB pass.
- `jal` and `jalr` use jump prediction, branch resolve, flush in MEM, and register writeback.
- Div/rem instructions use `divider` or `divider_u`.

## Trace Values In The DSL

The DSL declares these trace values:

```text
rs1, rs2, rd, pc, brTarget, imm, rs1_data, rs2_data, addr
```

Their mappings are instruction-dependent:

- `pc` is mapped for all instructions.
- `rs1`, `rs2`, and `rd` are mapped from instruction bitfields when relevant.
- `addr` is computed for loads/stores from base register plus immediate.
- `brTarget` and `imm` are computed for branch/jump instructions.
- `rs1_data` and `rs2_data` are mapped for signed and unsigned divide/remainder instructions.

These trace values become arrays in `ROCKET_Channel` and are connected to the external models and trace printer.

## Generated Rocket Backend

Generated Rocket backend files are under:

```text
etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET
```

Important files:

| File | Role |
|---|---|
| `include/ROCKET_PerformanceModel.h` | Defines timing variables and external model instances |
| `src/ROCKET_PerformanceModel.cpp` | Connects channels, writes timing stream/header, reports total cycle count |
| `src/ROCKET_SchedulingFunction.cpp` | Generated per-instruction scheduling functions |
| `include/ROCKET_Channel.h` | Trace value arrays for monitor/channel communication |
| `src/ROCKET_Channel.cpp` | Maps trace value names to channel arrays |
| `include/ROCKET_Printer.h` | Accessors for trace values |
| `src/ROCKET_Printer.cpp` | Trace header for perf trace output |
| `src/ROCKET_InstructionPrinters.cpp` | Per-instruction perf trace formatting |

## Timing Variables

`ROCKET_PerformanceModel` currently stores five single-element timing variables:

```cpp
uint64_t IF = 0;
uint64_t ID = 0;
uint64_t EX = 0;
uint64_t MEM = 0;
uint64_t WB = 0;
```

`getCycleCount()` returns the maximum of those stage cycles.

`getPipelineStream()` currently writes only:

```text
IF,ID,EX,MEM,WB
```

This is exactly what appears at the top of `trace_output/ROCKET/rocket_aha-mont64/timing/ROCKET_timing_0000.csv`.

## Scheduling Function Behavior

`ROCKET_SchedulingFunction.cpp` contains one generated scheduling function per instruction mnemonic. Each function computes local microaction timing variables and then updates the global stage variables.

Typical local variables include:

- `n_Enter`
- `n_PC_Gen`
- `n_uA_PcCorrect`
- `n_uA_CacheBlock`
- `n_uA_PcPredict`
- `n_ITLB`
- `n_ICache`
- `n_Decoder`
- `n_uA_OF_A`
- `n_uA_OF_B`
- `n_ALU`
- `n_DIV`
- `n_DIVU`
- `n_DCache`
- `n_Branch`
- `n_MEMPass`
- `n_Reg`

The pattern is:

1. Read the current stage availability, usually `perfModel->IF`, as `n_Enter`.
2. Compute microaction cycles.
3. Collapse microaction cycles and next-stage occupancy into a stage cycle with `std::max`.
4. Store the stage cycle back into `perfModel->IF`, `ID`, `EX`, `MEM`, or `WB`.
5. Update connector/resource model state such as register writeback readiness, branch prediction connector times, or ICache miss release time.

For example, an integer ALU instruction computes ICache fetch, decode, source register readiness, ALU result, MEM pass, and register writeback. A load additionally computes DCache timing and load writeback. A branch additionally sets predictor state and resolves the branch in MEM.

## Register Dependency Handling

Rocket uses:

```cpp
common::StandardRegisterModel regModel;
```

The model is defined in:

```text
etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/common/StandardRegisterModel.h
```

It stores a ready cycle per architectural register:

- `getXa()` returns the ready cycle for `rs1`.
- `getXb()` returns the ready cycle for `rs2`.
- `setXd(cycle)` records when `rd` becomes ready.

The generated scheduling code uses these values in ID-stage max operations:

```cpp
n_uA_OF_A = std::max({n_IF, perfModel->regModel.getXa()});
n_uA_OF_B = std::max({n_IF, perfModel->regModel.getXb()});
```

There is currently no explicit timing trace field that says:

- whether a RAW dependency occurred,
- which register caused it,
- how long the instruction waited,
- which producer ready cycle blocked it.

The only visible symptom is a larger gap between stage cycle columns.

## Branch Prediction Behavior

Rocket branch prediction is modeled by:

```text
models/rocket/BranchPredictionModel.h
models/rocket/BranchPredictionModel.cpp
```

It includes:

- a branch history table with 2-bit counters,
- a branch target buffer,
- a return address stack,
- connector times for predicted-taken and mispredicted/corrected PC paths.

Relevant connector methods:

- `setPc_p(...)` for conditional branch prediction,
- `setPc_p_j(...)` for `jal`,
- `setPc_p_jr(...)` for `jalr`,
- `setPc_c(...)` for resolved/corrected PC timing,
- `getPc_mp()` for misprediction/correction timing,
- `getPc_pt()` for correctly predicted taken timing.

The model internally tracks:

- `isTaken`
- `isMispredict`
- `branchPredictedTaken`
- branch/jump/jalr flags
- return-address-stack usage state

It exposes string info helpers:

```cpp
getInfo_mispredict()
getInfo_taken()
```

These are not currently written into Rocket timing traces.

## ICache Behavior

Rocket ICache model files:

```text
models/rocket/ICacheModel.h
models/rocket/ICacheModel.cpp
```

The model is a proof-of-concept cache model with:

- 4 ways,
- 64 sets,
- 64-byte indexing behavior by `pc >> 6`,
- tag derived from `pc >> 12`,
- simple LFSR replacement,
- cachable range `0x80000000 <= pc < 0xC0000000`,
- cache hit delay of `1`,
- memory/miss delay of `22`.

`getDelay()`:

1. reads `pc` from the trace channel,
2. checks whether the instruction is in cache,
3. updates `isMiss`,
4. returns `MEMORY_DELAY` for uncachable or miss cases, otherwise `CACHE_DELAY`.

The generated scheduler uses:

```cpp
n_ICache = n_Enter + perfModel->iCacheModel.getDelay();
perfModel->iCacheModel.setIc_in(n_ICache);
```

`setIc_in()` records a miss-release time in `t_ic` when `isMiss` is true. Later `getIc_out()` can block following fetches via `uA_CacheBlock`.

The model exposes:

```cpp
getInfo_miss()
```

But the miss flag and delay are not currently written into timing traces.

## DCache Behavior

Rocket DCache model files:

```text
models/rocket/DCacheModel.h
models/rocket/DCacheModel.cpp
```

The model is a proof-of-concept cache model with:

- 8 ways,
- 256 sets,
- 64-byte lines,
- simple LFSR replacement,
- cachable range `0x80000000 <= addr < 0xC0000000`,
- cache hit delay of `1`,
- memory/miss delay of `39`,
- uncachable delay of `39`.

`getDelay()`:

1. reads `addr` from the trace channel,
2. returns uncachable delay when outside the cachable range,
3. checks cache hit/miss,
4. updates `isMiss`,
5. returns hit or miss delay.

The generated scheduler uses:

```cpp
n_DCache = n_EX + perfModel->dCacheModel.getDelay();
```

There is a TODO noting that preceding-store address blocking is not currently modeled.

The model exposes:

```cpp
getInfo_miss()
```

But the miss flag and delay are not currently written into timing traces.

## Divider Behavior

Rocket divider model files:

```text
models/rocket/DividerModel.h
models/rocket/DividerModel.cpp
models/rocket/DividerUnsignedModel.h
models/rocket/DividerUnsignedModel.cpp
```

The signed and unsigned divider implementations contain realistic helper functions based on dividend/divisor leading-zero behavior:

- `rocketSignedDividerDelay(...)`
- `rocketUnsignedDividerDelay(...)`

However, both Rocket `getDelay()` methods currently ignore those helper functions and return:

```cpp
return 1;
```

Therefore, the current generated Rocket simulator does not model variable divider latency. The scheduling functions still call `divider.getDelay()` or `divider_u.getDelay()`, but the returned value is always one cycle.

## Trace Extraction And Writing

Rocket trace extraction uses the generated channel:

```text
ROCKET_Channel.h
ROCKET_Channel.cpp
```

The channel stores fixed-size arrays for:

```text
pc, brTarget, rs1, rd, imm, rs2, rs1_data, rs2_data, addr
```

`ROCKET_PerformanceModel::connectChannel()` connects those arrays to external models:

- branch predictor receives `pc`, `brTarget`, `rs1`, `rd`, `imm`,
- register model receives `rs1`, `rs2`, `rd`,
- ICache receives `pc`,
- DCache receives `addr`,
- divider models receive `rs1_data`, `rs2_data`.

`ROCKET_Printer` writes the perf trace header and `ROCKET_InstructionPrinters.cpp` writes per-instruction values to:

```text
trace_output/ROCKET/rocket_aha-mont64/perf/ROCKET_trace_*.csv
```

The timing trace is written from:

```cpp
ROCKET_PerformanceModel::getPipelineStream()
ROCKET_PerformanceModel::getPrintHeader()
```

to files such as:

```text
trace_output/ROCKET/rocket_aha-mont64/timing/ROCKET_timing_0000.csv
```

The assembly trace files under:

```text
trace_output/ROCKET/rocket_aha-mont64/asm/asm_trace_*.csv
```

contain PC and disassembly columns.

## Current Trace Output Limitation

The timing trace currently shows only when an instruction reaches each stage. For example:

```text
IF,ID,EX,MEM,WB
22,23,24,25,26
23,24,25,26,27
24,25,26,27,28
```

This is enough to see that a delay happened, but not why. If `ID - IF`, `EX - ID`, `MEM - EX`, or `WB - MEM` is greater than expected, the trace does not directly distinguish:

- data dependency,
- branch flush or misprediction,
- ICache miss,
- DCache miss,
- divider delay,
- structural/resource conflict,
- writeback/commit delay,
- other pipeline stalls.

That limitation motivates adding diagnostic timing fields.
