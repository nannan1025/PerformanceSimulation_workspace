# ROCKET Simulator Timing Summary

This report summarizes the current ROCKET timing model in this workspace.

Primary sources:

- CorePerfDSL model: `.llm_output/correction/ROCKET_0427.corePerfDsl`
- Generated ROCKET backend: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/`
- Rocket external model headers: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/rocket/`
- Rocket external model sources: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/src/rocket/`
- Common register model: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/common/StandardRegisterModel.h`

This file describes the current simulator and known timing-accuracy risks. 

## Part 1: ROCKET Simulator Information

### 1. Pipeline Structure From CorePerfDSL

The inspected ROCKET CorePerfDSL declares a five-stage in-order pipeline:

```text
ROCKET_pipeline: IF -> ID -> EX -> MEM -> WB
```

The generated simulator keeps one timing variable per stage:

```text
IF, ID, EX, MEM, WB
```

#### Connectors

The CorePerfDSL declares three connector groups:

- Branch / PC connectors: `Pc_mp`, `Pc_pt`, `Pc_p`, `Pc_p_j`, `Pc_p_jr`, `Pc_c`
- ICache connectors: `Ic_out`, `Ic_in`
- Register dependency connectors: `Xa`, `Xb`, `Xd`

Meaning:

- `Pc_p`: conditional-branch prediction timing.
- `Pc_p_j`: immediate jump prediction timing for `jal`.
- `Pc_p_jr`: register-indirect jump prediction timing for `jalr`.
- `Pc_c`: corrected/resolved PC timing after branch or jump resolution.
- `Pc_mp`: misprediction correction timing exposed to later fetch.
- `Pc_pt`: correctly predicted taken timing exposed to later fetch.
- `Ic_in`: time when the current ICache access can release a frontend block.
- `Ic_out`: frontend block time caused by a previous ICache miss.
- `Xa`, `Xb`: source operand ready cycles.
- `Xd`: destination register ready cycle.

#### Resources

The CorePerfDSL declares these timing resources:

- IF / frontend: `PC_Gen`, `BPU`, `ITLB`, `ICache(iCacheModel)`
- ID / decode: `Decoder`
- Register dependency: connectors `Xa`, `Xb`, `Xd` handled by `regModel`
- EX: `ALU`, `MUL`, `DIV(divider)`, `DIVU(divider_u)`, `DTLB`, `LSUReq`, `EXPass`
- MEM: `Branch`, `DCache(dCacheModel)`, `StoreCommit`, `FlushMem`, `MEMPass`
- WB: `Reg`, `CSR`, `LoadWB`, `FlushWb`, `WBPass`

#### Microactions By Stage

IF stage:

- `uA_PCGen`
- `uA_PcCorrect`
- `uA_CacheBlock`
- `uA_PcPredict`
- `uA_ITLB`
- `uA_IFetch`
- `uA_PredictBr`
- `uA_PredictJ`
- `uA_PredictJr`

ID stage:

- `uA_Decode`
- `uA_OF_A`
- `uA_OF_B`

EX stage:

- `uA_ALU_arith`
- `uA_ALU_branch`
- `uA_ALU_addr`
- `uA_MUL`
- `uA_DIV`
- `uA_DIVU`
- `uA_DTLB`
- `uA_LSUReq`
- `uA_EXPass`

MEM stage:

- `uA_BranchResolve`
- `uA_DCachePipe`
- `uA_StoreCommit`
- `uA_FlushMem`
- `uA_MEMPass`

WB stage:

- `uA_LoadWriteBack`
- `uA_CSRRetire`
- `uA_FlushWb`
- `uA_RegWriteBack`
- `uA_WBPass`

#### Instruction-To-Microaction Mapping

All instruction classes use the common frontend and decode flow:

```text
uA_PCGen, uA_PcCorrect, uA_CacheBlock, uA_PcPredict,
uA_ITLB, uA_IFetch, uA_Decode
```

Instruction-class-specific actions:

- ALU register-register instructions use `uA_OF_A`, `uA_OF_B`, `uA_ALU_arith`, `uA_MEMPass`, and `uA_RegWriteBack`.
- ALU immediate instructions use `uA_OF_A`, `uA_ALU_arith`, `uA_MEMPass`, and `uA_RegWriteBack`.
- Upper-immediate instructions such as `lui` and `auipc` use `uA_ALU_arith`, `uA_MEMPass`, and `uA_RegWriteBack`.
- Multiply instructions use `uA_OF_A`, `uA_OF_B`, `uA_MUL`, `uA_MEMPass`, and `uA_RegWriteBack`.
- Signed divide/remainder instructions use `uA_OF_A`, `uA_OF_B`, `uA_DIV`, `uA_MEMPass`, and `uA_RegWriteBack`.
- Unsigned divide/remainder instructions use `uA_OF_A`, `uA_OF_B`, `uA_DIVU`, `uA_MEMPass`, and `uA_RegWriteBack`.
- CSR register instructions use `uA_OF_A`, `uA_EXPass`, `uA_MEMPass`, and `uA_CSRRetire`.
- CSR immediate instructions use `uA_EXPass`, `uA_MEMPass`, and `uA_CSRRetire`.
- Loads use `uA_OF_A`, `uA_ALU_addr`, `uA_DTLB`, `uA_LSUReq`, `uA_DCachePipe`, `uA_LoadWriteBack`, and `uA_RegWriteBack`.
- Stores use `uA_OF_A`, `uA_OF_B`, `uA_ALU_addr`, `uA_DTLB`, `uA_LSUReq`, `uA_DCachePipe`, `uA_StoreCommit`, and `uA_WBPass`.
- Conditional branches use `uA_PredictBr`, `uA_OF_A`, `uA_OF_B`, `uA_ALU_branch`, `uA_BranchResolve`, `uA_FlushMem`, and `uA_WBPass`.
- `jal` uses `uA_PredictJ`, `uA_ALU_arith`, `uA_BranchResolve`, `uA_FlushMem`, and `uA_RegWriteBack`.
- `jalr` uses `uA_PredictJr`, `uA_OF_A`, `uA_ALU_arith`, `uA_BranchResolve`, `uA_FlushMem`, and `uA_RegWriteBack`.
- The default group uses pass-through actions `uA_EXPass`, `uA_MEMPass`, and `uA_WBPass`.

Instruction groups declared in the CorePerfDSL:

- `Arith_Ra_Rb`: `add`, `sub`, `xor`, `or`, `and`, `slt`, `sltu`, `sll`, `srl`, `sra`, `addw`, `subw`
- `Arith_Ra`: `addi`, `xori`, `ori`, `andi`, `slti`, `sltiu`, `slli`, `srli`, `srai`, `addiw`, `slliw`, `sraiw`, `srliw`
- `Arith_X`: `auipc`, `lui`
- `Mul_Ra_Rb`: `mul`, `mulw`
- `MulH_Ra_Rb`: `mulh`, `mulhu`, `mulhsu`
- `Div_Ra_Rb`: `div`, `rem`, `divw`, `remw`
- `DivU_Ra_Rb`: `divu`, `remu`, `divuw`, `remuw`
- `Csr_Ra`: `csrrw`, `csrrs`, `csrrc`
- `Csr_X`: `csrrwi`, `csrrsi`, `csrrci`
- `Store`: `sb`, `sh`, `sw`, `sd`
- `Load`: `lb`, `lbu`, `lh`, `lhu`, `lw`, `ld`, `lwu`
- `Branch_Ra_Rb`: `beq`, `bne`, `blt`, `bge`, `bltu`, `bgeu`
- `Jump`: `jal`
- `JumpR`: `jalr`
- `Default`: fallback instruction group

### 2. Generated Backend Timing Behavior

The generated backend implements one scheduling function per instruction in `ROCKET_SchedulingFunction.cpp`. Each scheduling function computes local timing variables and then collapses them into final stage cycles with `max(...)` expressions.

The common IF formula shape is:

```text
n_Enter          = previous IF value
n_PC_Gen         = n_Enter + 1
n_uA_PcCorrect   = max(n_Enter, Pc_mp from branch model)
n_uA_CacheBlock  = max(n_Enter, Ic_out from ICache model)
n_uA_PcPredict   = max(n_Enter, Pc_pt from branch model)
n_ITLB           = n_Enter + 1
n_ICache         = n_Enter + iCacheModel.getDelay()
n_IF             = max(n_PC_Gen, n_uA_PcCorrect, n_uA_CacheBlock,
                       n_uA_PcPredict, n_ITLB, n_ICache, optional n_BPU,
                       previous ID value)
```

For branch and jump instructions, the IF formula also includes BPU-related prediction variables:

- Conditional branch: `n_BPU`, then `dynBranchPredModel.setPc_p(n_BPU)`
- `jal`: `n_BPU`, then `dynBranchPredModel.setPc_p_j(n_BPU)`
- `jalr`: `n_BPU`, then `dynBranchPredModel.setPc_p_jr(n_BPU)`

Common ID formula shapes:

```text
n_Decoder = n_IF + 1
n_uA_OF_A = max(n_IF, rs1 ready cycle)
n_uA_OF_B = max(n_IF, rs2 ready cycle)
n_ID      = max(n_Decoder, selected operand-read variables, previous EX value)
```

Instructions without a source operand omit the corresponding operand-read variable from the `n_ID` max expression.

Common EX formula families:

- ALU and jump/link results: `n_ALU = n_ID + 1`
- Branch compare/address behavior: `n_ALU = n_ID + 1`
- Multiply: `n_MUL = n_ID + 1`
- Signed divide/remainder: `n_DIV = n_ID + divider.getDelay()`
- Unsigned divide/remainder: `n_DIVU = n_ID + divider_u.getDelay()`
- Load/store address path: `n_ALU = n_ID + 1`, `n_DTLB = n_ID + 1`, `n_LSUReq = n_ID + 1`
- CSR/pass-through: `n_EXPass = n_ID + 1`
- Final EX usually includes `previous MEM value` as a structural/backpressure term.

Common MEM formula families:

- ALU/multiply/divide/CSR/default pass-through: `n_MEMPass = n_EX + 1`
- Load/store data cache access: `n_DCache = n_EX + dCacheModel.getDelay()`
- Store commit: `n_StoreCommit = n_DCache`
- Branch/jump resolution: `n_Branch = n_EX + 1`, then `dynBranchPredModel.setPc_c(n_Branch)`
- Branch/jump flush memory path: `n_FlushMem = n_EX + 1`
- Final MEM usually includes `previous WB value` as a structural/backpressure term.

Common WB formula families:

- ALU/multiply/divide/jump link writeback: `n_Reg = n_MEM + 1`
- Load writeback: `n_LoadWB = n_MEM + 1`, with register readiness set from load writeback timing
- CSR retire/writeback: `n_CSR = n_MEM + 1`
- Store/branch/default pass-through: `n_WBPass = n_MEM + 1`

The register dependency model records producer readiness through `setXd(cycle)`. Consumers read source readiness through `getXa()` and `getXb()` or through the first-pass instrumentation wrappers that call those methods exactly once.

### 3. External Model Behavior Related To Timing

#### Branch Prediction Model

Files:

- Header: `externalModels/include/models/rocket/BranchPredictionModel.h`
- Source: `externalModels/src/rocket/BranchPredictionModel.cpp`

Trace values:

- `pc`
- `brTarget`
- `rs1`
- `rd`
- `imm`

Connector inputs:

- `Pc_p`: conditional branch prediction time
- `Pc_p_j`: `jal` prediction time
- `Pc_p_jr`: `jalr` prediction time
- `Pc_c`: correction / resolved PC time

Connector outputs:

- `Pc_mp`: mispredict correction time
- `Pc_pt`: correctly predicted taken time

Behavior:

- Conditional branches use a 512-entry branch history table with 2-bit saturating counters.
- The BHT index combines PC bits and hashed history.
- Conditional prediction is taken when the counter is at least 2.
- `jal` is treated as taken and may push a return address for calls.
- `jalr` uses a 6-entry return address stack for returns and a 28-entry branch target buffer for non-return indirect jumps.
- `setPc_c()` stores the branch/jump correction time.
- `getPc_mp()` evaluates the previous branch or jump and returns `Pc_c` timing only on misprediction.
- `getPc_pt()` returns prediction timing only when a branch was correctly predicted taken or a jump was correctly predicted.

Timing effect:

- Every scheduling function reads `getPc_mp()` and `getPc_pt()` during IF timing.
- A previous mispredicted branch or jump can push a later instruction's IF cycle through `n_uA_PcCorrect`.
- A previous correctly predicted taken branch or jump can push a later instruction's IF cycle through `n_uA_PcPredict`.

Simplifications:

- Conditional branch taken status is inferred by comparing the current instruction PC with the previous branch target.
- Compressed instruction return addresses are marked as TODO and currently use `pc + 4`.
- Predictor confidence, exact target source, BTB hit, and RAS behavior are not fully exposed in the timing trace.

#### ICache Model

Files:

- Header: `externalModels/include/models/rocket/ICacheModel.h`
- Source: `externalModels/src/rocket/ICacheModel.cpp`

Trace value:

- `pc`

Connector input / output:

- `Ic_in`
- `Ic_out`

Behavior:

- The model is a 4-way, 64-set tag cache.
- Hit delay is `1`.
- Miss delay is `22`.
- Non-cacheable fetches also use the miss delay of `22`.
- The cacheable range is hard-coded to `[0x80000000, 0xC0000000)`.
- Replacement uses a small LFSR.
- `getDelay()` updates the internal `isMiss` state.
- `getMiss()` exposes the most recent miss state without changing cache behavior.
- On a miss, `setIc_in()` records the time when the ICache block is released; later instructions see that through `getIc_out()`.

Timing effect:

- Current fetch timing uses `n_ICache = n_Enter + iCacheModel.getDelay()`.
- Previous ICache miss blocking affects later IF timing through `n_uA_CacheBlock = max(n_Enter, Ic_out)`.

#### DCache Model

Files:

- Header: `externalModels/include/models/rocket/DCacheModel.h`
- Source: `externalModels/src/rocket/DCacheModel.cpp`

Trace value:

- `addr`

Behavior:

- The model is an 8-way, 256-set cache with 64-byte lines.
- Hit delay is `1`.
- Miss delay is `39`.
- Non-cacheable delay is `39`.
- The cacheable range is hard-coded to `[0x80000000, 0xC0000000)`.
- Replacement uses a small LFSR.
- `getDelay()` updates the internal `isMiss` state.
- `getMiss()` exposes the most recent miss state without changing cache behavior.

Timing effect:

- Loads and stores use `n_DCache = n_EX + dCacheModel.getDelay()`.
- Loads set destination register readiness at `n_LoadWB = n_MEM + 1`.
- Stores use `n_StoreCommit = n_DCache` and then pass through WB.

Simplification:

- The source explicitly notes that an older model calculated an additional delay when an address was blocked by a preceding store; the current Rocket DCache model does not implement that behavior.

#### Divider Models

Files:

- Signed divider header/source: `externalModels/include/models/rocket/DividerModel.h`, `externalModels/src/rocket/DividerModel.cpp`
- Unsigned divider header/source: `externalModels/include/models/rocket/DividerUnsignedModel.h`, `externalModels/src/rocket/DividerUnsignedModel.cpp`

Trace values:

- `rs1_data`
- `rs2_data`

Behavior:

- Both divider source files contain helper functions for operand-dependent delay based on dividend/divisor leading-zero relationships.
- The current active `getDelay()` implementation returns `1` for both signed and unsigned divider models.

Timing effect:

- Signed divide/remainder instructions use `n_DIV = n_ID + divider.getDelay()`.
- Unsigned divide/remainder instructions use `n_DIVU = n_ID + divider_u.getDelay()`.
- Because both current `getDelay()` methods return `1`, divider instructions are currently modeled as one-cycle EX operations.

#### Register / Dependency Model

File:

- `externalModels/include/models/common/StandardRegisterModel.h`

Trace values:

- `rs1`
- `rs2`
- `rd`

Behavior:

- `getXa()` returns the ready cycle stored for source register `rs1`.
- `getXb()` returns the ready cycle stored for source register `rs2`.
- `setXd(cycle)` stores the ready cycle for destination register `rd`.

Timing effect:

- ID operand-read microactions wait on source readiness:

```text
n_uA_OF_A = max(n_IF, rs1_ready_cycle)
n_uA_OF_B = max(n_IF, rs2_ready_cycle)
```

- Producer instructions call `setXd(...)` at the timing point where their destination value is modeled as ready.
- ALU/multiply/divide/jump-link results are generally ready from the producing execution/writeback formula selected by the scheduler.
- Loads set readiness from load writeback timing.

Simplification:

- The model stores one ready cycle per register.
- It does not explicitly model bypass source identity, bypass path availability, or detailed scoreboard state.
- The source contains a TODO for the `rd = 0` corner case.

## Part 2: Possible Reasons For Timing-Cycle Inaccuracies

### 1. Branch Prediction / Redirect Timing Mismatch

Branch and jump effects are split across instructions:

- The branch or jump instruction calls `setPc_p`, `setPc_p_j`, or `setPc_p_jr` in IF.
- The branch or jump instruction calls `setPc_c` in MEM.
- The following instruction calls `getPc_mp()` and `getPc_pt()` in IF, which evaluates the previous control-flow instruction.

This means a branch timing problem may appear on the following instruction's IF timing rather than only on the branch row.

Possible mismatch sources:

- `Pc_mp` and `Pc_pt` are evaluated on the following instruction.
- `branch_misprediction` is not reliably row-local in the current trace.
- Conditional branch taken status is inferred from the next PC and `brTarget`.
- `jalr` target prediction depends on simplified RAS/BTB behavior.
- Compressed return-address behavior uses `pc + 4` TODO logic.

Trace clues:

- `branch_control`
- `branch_misprediction`
- `IF_ext_Pc_mp`
- `IF_ext_Pc_pt`
- `IF_n_uA_PcCorrect`
- `IF_n_uA_PcPredict`
- `MEM_n_Branch`
- `MEM_n_FlushMem`

### 2. ICache Hit/Miss And Frontend Blocking Simplification

The ICache model is a simple tag-cache timing model with fixed hit/miss delays. It does not model all Rocket frontend structures.

Possible mismatch sources:

- Fixed hit delay `1` and miss delay `22`.
- Hard-coded cacheable address range.
- Simple LFSR replacement.
- No explicit instruction prefetch model.
- No fetch queue, fetch packet, MSHR, refill pipeline, or frontend replay detail.
- Previous ICache miss blocking is represented only through `Ic_out`.

Trace clues:

- `icache_miss`
- `icache_delay_cycles`
- `IF_n_ICacheDelay`
- `IF_n_ICache`
- `IF_ext_Ic_out`
- `IF_n_uA_CacheBlock`

### 3. DCache Hit/Miss, Store Blocking, And Memory-System Simplification

The DCache model is also a simple tag-cache timing model. Loads and stores share the same `getDelay()` style access, but real Rocket memory behavior can include more structures than this model represents.

Possible mismatch sources:

- Fixed hit delay `1`.
- Fixed miss/non-cacheable delay `39`.
- Hard-coded cacheable address range.
- Simple LFSR replacement.
- No store buffer occupancy model.
- No store-load forwarding model.
- No bank conflict, MSHR, refill, writeback, or memory-ordering detail.
- Source comment notes missing additional delay for an address blocked by a preceding store.

Trace clues:

- `dcache_miss`
- `dcache_delay_cycles`
- `MEM_n_DCacheDelay`
- `MEM_n_DCache`
- `MEM_n_StoreCommit`
- memory address in perf trace / channel fields

### 4. Divider Latency Collapsed To One Cycle

The signed and unsigned Rocket divider source files contain realistic helper functions, but the active `getDelay()` implementation currently returns `1`.

Possible mismatch sources:

- Real RTL divide/remainder operations may take multiple cycles.
- Operand-dependent early-out behavior is not active.
- 32-bit and 64-bit divide/remainder instructions currently use the same one-cycle delay behavior.

Trace clues:

- `divider_delay_cycles`
- `EX_n_DIVDelay`
- `EX_n_DIV`
- `EX_n_DIVUDelay`
- `EX_n_DIVU`

### 5. Multiply Latency / Result Availability Mismatch

The generated scheduler generally models multiply instructions with:

```text
n_MUL = n_ID + 1
```

Possible mismatch sources:

- Real Rocket multiply behavior may be multi-cycle or pipelined differently depending on configuration.
- Result forwarding and writeback timing may not match a one-cycle `MUL` resource.
- High-half multiply instructions may not have the same timing as low-half multiply in real hardware.

Trace clues:

- `instr`
- `EX_n_MUL`
- `WB_n_Reg`
- downstream `raw_wait_cycles`

### 6. Register Dependency / Forwarding Approximation

The register dependency model stores one ready cycle per register. It can explain RAW waits, but it does not encode the actual forwarding path that produced the value.

Possible mismatch sources:

- Missing bypass-source identity.
- Simplified readiness for ALU, load, CSR, multiply, divide, and jump-link producers.
- No detailed scoreboard model.
- `rd = 0` is a TODO corner case in `StandardRegisterModel`.
- A real Rocket bypass path may provide data earlier or later than the modeled `setXd(...)` cycle.

Trace clues:

- `rs1`, `rs2`, `rd`
- `uses_rs1`, `uses_rs2`, `uses_rd`
- `ID_rs1_ready_cycle`
- `ID_rs2_ready_cycle`
- `ID_n_uA_OF_A`
- `ID_n_uA_OF_B`
- `raw_wait_cycles`
- `raw_blocking_reg`
- `raw_blocking_ready_cycle`

### 7. TLB Timing Simplification

The generated formulas include `ITLB` and `DTLB` local variables, but they are modeled as fixed one-cycle local resources.

Possible mismatch sources:

- No real TLB miss/refill timing.
- No page-table walk timing.
- No address translation contention.
- No privilege or PMP/PMA timing detail.

Trace clues:

- `IF_n_ITLB`
- `EX_n_DTLB`

### 8. Pipeline Structural And Backpressure Simplification

The generated model uses `max(...)` expressions and previous-stage terms to approximate in-order pipeline backpressure.

Examples:

- IF formulas include `previous ID value`.
- ID formulas include `previous EX value`.
- EX formulas include `previous MEM value`.
- MEM formulas include `previous WB value`.

Possible mismatch sources:

- Real frontend/backend queueing is more detailed than a single previous-stage max term.
- Structural hazards may depend on resource occupancy not represented by the formula.
- Flush, replay, exception, and commit behavior may not align exactly with modeled stage variables.
- The model is single-instruction timing-oriented and may not represent every overlap seen in RTL.

Trace clues:

- `IF_prev_ID`
- `ID_prev_EX`
- `EX_prev_MEM`
- `MEM_prev_WB`
- stage gaps: `stage_gap_if_id`, `stage_gap_id_ex`, `stage_gap_ex_mem`, `stage_gap_mem_wb`

### 9. Trace / RTL Comparison Boundary Mismatch

The simulator timing trace records modeled stage cycle variables, not raw RTL pipeline probe signals. RTL traces may define "fetch", "decode", "execute", "memory", or "commit" boundaries differently from this simulator.

Possible mismatch sources:

- Simulator `WB` may correspond to a conceptual commit/writeback point, while RTL may expose retire, writeback, valid, or commit signals separately.
- The timing trace's `assembly` field is `null`; disassembly must be joined from `asm_trace_*.txt`.
- Control-flow effects may be attributed to the following instruction's IF row.
- Cache and branch model internals may be updated during scheduling rather than exactly at RTL event boundaries.

Trace clues:

- Join timing trace `pc` with `asm_trace_*.txt` and `ROCKET_trace_*.csv`.
- Check local formula variables before attributing a mismatch to a single final stage gap.
