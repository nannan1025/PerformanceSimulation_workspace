# ROCKET Simulator Timing Summary

This report summarizes the current ROCKET timing model in this workspace.

Primary sources:

- CorePerfDSL model: `.llm_output/correction/ROCKET_0720_2.9%error.corePerfDsl`
- Generated ROCKET backend: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/`
- Rocket external model headers: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/rocket/`
- Rocket external model sources: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/src/rocket/`
- Current timing-trace instrumentation: `ROCKET_PerformanceModel`, `ROCKET_Channel`, and `ROCKET_SchedulingFunction.cpp`

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

The current CorePerfDSL declares four connector groups:

- Branch / PC connectors: `Pc_mp`, `Pc_pt`, `Pc_p`, `Pc_p_j`, `Pc_p_jr`, `Pc_c`
- ICache connectors: `Ic_out`, `Ic_in`
- Register dependency connectors: `Xa`, `Xb`, `Xd`
- Shared MulDiv connectors: `MulReady`, `MulIssue`, `DivReady`, `DivIssue`

Meaning:

- `Pc_p`: conditional-branch prediction timing.
- `Pc_p_j`: direct jump prediction timing for `jal`.
- `Pc_p_jr`: register-indirect jump prediction timing for `jalr`.
- `Pc_c`: corrected/resolved PC timing after branch or jump resolution.
- `Pc_mp`: misprediction correction timing exposed to later fetch.
- `Pc_pt`: correctly predicted taken timing exposed to later fetch.
- `Ic_in`: time when the current ICache access can release a frontend block.
- `Ic_out`: frontend block time caused by a previous ICache miss.
- `Xa`, `Xb`: source operand ready cycles.
- `Xd`: destination register ready cycle for normal register-producing instructions.
- `MulReady`: availability constraint for the shared MulDiv unit before a multiply issue.
- `MulIssue`: multiply issue time, used to set future multiply result and shared-unit availability.
- `DivReady`: availability constraint for the shared MulDiv unit before a divider/remainder issue.
- `DivIssue`: divider/remainder issue time, used to set future divider result and shared-unit availability.

#### Resources

The CorePerfDSL declares these timing resources:

- IF / frontend: `PC_Gen`, `BPU`, `ITLB`, `ICache(iCacheModel)`
- ID / decode: `Decoder`
- Register dependency and shared MulDiv readiness: connectors handled by `regModel`
- EX: `ALU`, `MUL`, `DIV`, `DIVU`, `DTLB`, `LSUReq`, `EXPass`
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
- CSR register instructions use `uA_OF_A`, `uA_EXPass`, `uA_MEMPass`, `uA_CSRRetire`, and `uA_RegWriteBack`.
- CSR immediate instructions use `uA_EXPass`, `uA_MEMPass`, `uA_CSRRetire`, and `uA_RegWriteBack`.
- Loads use `uA_OF_A`, `uA_ALU_addr`, `uA_DTLB`, `uA_LSUReq`, `uA_DCachePipe`, and `uA_LoadWriteBack`.
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

The generated backend implements one scheduling function per instruction in `ROCKET_SchedulingFunction.cpp`. Each scheduling function computes local timing variables and then collapses them into final stage cycles with `max(...)` expressions. The current generated backend has temporary trace instrumentation that records the local formula variables without changing the formula values.

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
- Multiply: `n_MUL_max = max(n_ID, regModel.getMulReady())`, then `n_MUL = n_MUL_max + 1`
- Signed divide/remainder: `n_DIV_max = max(n_ID, regModel.getDivReady())`, then `n_DIV = n_DIV_max + 1`
- Unsigned divide/remainder: `n_DIVU_max = max(n_ID, regModel.getDivReady())`, then `n_DIVU = n_DIVU_max + 1`
- Load/store address path: `n_ALU = n_ID + 1`, `n_DTLB = n_ID + 1`, `n_LSUReq = n_ID + 1`
- CSR/pass-through: `n_EXPass = n_ID + 1`
- Final EX usually includes `previous MEM value` as a structural/backpressure term.

Current shared MulDiv timing abstraction:

- The multiply/divider producer row is not directly stretched by the long result latency beyond the generated issue point.
- `regModel.setMulIssue(n_MUL)` records multiply result readiness and shared MulDiv next availability.
- `regModel.setDivIssue(n_DIV)` or `regModel.setDivIssue(n_DIVU)` records divider/remainder result readiness and shared MulDiv next availability.
- The current external model constants are `RocketMulRegisterModel::MUL_LATENCY_CYCLES = 5` and `RocketMulRegisterModel::DIV_LATENCY_CYCLES = 30`.
- The timing trace records `EX_ext_MulReady`, `EX_n_MUL_max`, `EX_n_MUL`, `EX_ext_DivReady`, `EX_n_DIV_max`, `EX_n_DIV`, `EX_n_DIVU_max`, `EX_n_DIVU`, and `rd_ready_cycle` for these instruction families.

Common MEM formula families:

- ALU/multiply/divide/CSR/default pass-through: `n_MEMPass = n_EX + 1`
- Load/store data cache access: `n_DCache = n_EX + dCacheModel.getDelay()`
- Store commit: `n_StoreCommit = n_EX + 1` in the current generated store scheduling functions
- Branch/jump resolution: `n_Branch = n_EX + 1`, then `dynBranchPredModel.setPc_c(n_Branch)`
- Branch/jump flush memory path: `n_FlushMem = n_EX + 1`
- Final MEM usually includes `previous WB value` as a structural/backpressure term.

Common WB formula families:

- ALU/multiply/divide/jump-link writeback: `n_Reg = n_MEM + 1`
- Load writeback: `n_LoadWB = n_MEM + 1`
- CSR retire/writeback: `n_CSR = n_MEM + 1`
- Store/branch/default pass-through: `n_WBPass = n_MEM + 1`

The register dependency model records producer readiness through `setXd(cycle)` for normal writers and through `setMulIssue(issueCycle)` / `setDivIssue(issueCycle)` for multiply/divider writers. Consumers read source readiness through `getXa()` and `getXb()`.

### 3. Current Timing Trace Instrumentation

The current timing CSV starts with identity and final-stage fields:

```text
pc,instr,assembly,rd,rs1,rs2,imm,rs1_data,rs2_data,IF,ID,EX,MEM,WB
```

Important details:

- `assembly` is kept as a timing schema field, but currently prints `null` because this generated timing backend has no real assembly string source connected from the assembly trace monitor.
- Channel fields are read with the correct timing-row index so `pc`, `instr`, and operand fields align with the scheduled instruction row.
- Missing scheduling variables are printed as `null`.
- The trace records only already-computed scheduling values; stateful model calls are not repeated only for printing.
- The current restored timing schema has 68 fields.

Stable scheduling-variable columns include:

```text
IF_n_Enter, IF_n_PC_Gen, IF_n_uA_PcCorrect, IF_n_uA_CacheBlock,
IF_n_uA_PcPredict, IF_n_ITLB, IF_n_ICache, IF_n_BPU,
IF_prev_ID, IF_ext_Pc_mp, IF_ext_Pc_pt, IF_ext_Pc_p,
IF_ext_Pc_p_j, IF_ext_Pc_p_jr, IF_ext_Ic_out,
ID_n_Decoder, ID_rs1_ready_cycle, ID_rs2_ready_cycle,
ID_n_uA_OF_A, ID_n_uA_OF_B, ID_prev_EX,
EX_n_ALU, EX_ext_MulReady, EX_n_MUL_max, EX_n_MUL,
EX_ext_DivReady, EX_n_DIV_max, EX_n_DIV, EX_n_DIVU_max,
EX_n_DIVU, EX_n_EXPass, EX_n_DTLB, EX_n_LSUReq,
EX_prev_MEM, MEM_n_MEMPass, MEM_n_DCache, MEM_n_StoreCommit,
MEM_n_Branch, MEM_n_FlushMem, MEM_prev_WB, MEM_ext_Pc_c,
WB_n_Reg, WB_n_CSR, WB_n_WBPass, WB_n_LoadWB
```

Additional diagnostic fields currently emitted after the scheduling-variable columns:

```text
used_rs1, used_rs2, used_rd, rd_ready_cycle,
icache_miss, dcache_miss,
icache_delay_cycles, dcache_delay_cycles,
sim_misprediction
```

### 4. External Model Behavior Related To Timing

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

- Conditional branches use a 512-entry BHT with 1-bit prediction entries.
- The BHT has 8-bit global history and a 3-bit history hash in the index calculation.
- Conditional direction prediction comes from the BHT; taken branches can also use BTB target prediction.
- The BTB has 28 entries, stores `pc`, `addr`, and control-flow kind, and is searched linearly.
- The RAS has 6 entries and is used for return-style `jalr` predictions.
- `jal` uses the direct jump prediction path `Pc_p_j`.
- `jalr` uses the register-indirect jump prediction path `Pc_p_jr`.
- `setPc_c(pc_c)` stores the correction timing for later `Pc_mp` handling.
- `getPc_mp()` evaluates pending previous control-flow state and updates predictor debug fields.
- `getPc_pt()` returns the prediction timing for correctly predicted taken control flow and clears pending control-flow flags.

Timing effect:

- Every scheduling function reads `getPc_mp()` and `getPc_pt()` during IF timing.
- A previous mispredicted branch or jump can push a later instruction's IF cycle through `n_uA_PcCorrect`.
- A previous correctly predicted taken branch or jump can push a later instruction's IF cycle through `n_uA_PcPredict`.

Simplifications:

- Actual taken/target behavior is inferred by comparing the current instruction PC with the previous predicted/control target.
- Exact six-entry BTB page compression from Rocket RTL is not modeled.
- Compressed instruction return addresses are approximated with `pc + 4`.
- Row-local branch reporting can be shifted because prediction resolution is consumed by the following instruction's IF formula.

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

- The model is an 8-way, 64-set tag cache with 64-byte lines.
- Hit delay is `1`.
- Miss delay is `22`.
- Non-cacheable fetches use the miss delay of `22` and do not populate the ICache.
- The cacheable range is `[0x80000000, 0x90000000)`.
- Address decomposition uses line offset bits `[5:0]`, set index bits `[11:6]`, and tag `addr >> 12`.
- Replacement uses a small LFSR and selects ways `0..7`.
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

- The model is an 8-way, 64-set tag cache with 64-byte lines.
- Hit delay is `1`.
- Miss delay is `6`.
- Non-cacheable delay is `6`.
- The cacheable range is `[0x80000000, 0x90000000)`.
- Address decomposition uses line offset bits `[5:0]`, set index bits `[11:6]`, and tag `addr >> 12`.
- Replacement uses a small LFSR and selects ways `0..7`.
- `getDelay()` updates the internal `isMiss` state.
- `getMiss()` exposes the most recent miss state without changing cache behavior.

Timing effect:

- Loads and stores use `n_DCache = n_EX + dCacheModel.getDelay()`.
- Loads record destination readiness at the DCache timing point in the current instrumentation.
- Stores call the generated DCache path and then use a separate `n_StoreCommit = n_EX + 1` term before final MEM `max(...)`.
- The generated store DCachePipe still routes through `Xd`, but stores have `used_rd = 0`; the timing trace should not interpret that side effect as an architectural store destination.

Simplification:

- The source explicitly notes that an older model calculated an additional delay when an address was blocked by a preceding store; the current Rocket DCache model does not implement that behavior.
- The target configuration mentions a shared L2 cache, but no shared-L2 model is currently implemented in the Rocket external models.

#### Shared Register / MulDiv Dependency Model

File:

- `externalModels/include/models/rocket/RocketMulRegisterModel.h`
- `externalModels/src/rocket/RocketMulRegisterModel.cpp`

Trace values:

- `rs1`
- `rs2`
- `rd`

Behavior:

- `getXa()` returns the ready cycle stored for source register `rs1`.
- `getXb()` returns the ready cycle stored for source register `rs2`.
- `setXd(cycle)` stores the ready cycle for destination register `rd`, ignoring `rd = 0` and out-of-range registers.
- `getMulReady()` returns the scheduling-base cycle needed so generated `n_MUL = max(n_ID, getMulReady()) + 1` reaches the next legal multiply issue cycle.
- `setMulIssue(issueCycle)` records `muldiv_unit_next_issue_cycle = issueCycle + 5` and `register_ready[rd] = issueCycle + 5` for multiply destination registers.
- `getDivReady()` reads the same shared MulDiv unit availability state as `getMulReady()`.
- `setDivIssue(issueCycle)` records `muldiv_unit_next_issue_cycle = issueCycle + 30` and `register_ready[rd] = issueCycle + 30` for divider/remainder destination registers.

Timing effect:

- ID operand-read microactions wait on source readiness:

```text
n_uA_OF_A = max(n_IF, rs1_ready_cycle)
n_uA_OF_B = max(n_IF, rs2_ready_cycle)
```

- Normal producer instructions call `setXd(...)` at the timing point where their destination value is modeled as ready.
- Multiply producer instructions call `setMulIssue(n_MUL)`, which affects later dependent consumers and later users of the shared MulDiv unit.
- Divider/remainder producer instructions call `setDivIssue(n_DIV)` or `setDivIssue(n_DIVU)`, which affects later dependent consumers and later users of the shared MulDiv unit.
- Register x0 does not create a dependency in `RocketMulRegisterModel`.

Simplification:

- The model stores one ready cycle per register.
- It does not explicitly expose bypass-source identity.
- Multiply latency is fixed at `5` cycles in the current source.
- Divider/remainder latency is fixed at `30` cycles in the current source.
- Operand-dependent multiply/divider early-out behavior is not modeled in this current ROCKET backend version.
- The shared MulDiv unit is modeled as non-pipelined through `muldiv_unit_next_issue_cycle`.

#### Divider Resource Models

Files:

- Signed divider header/source: `externalModels/include/models/rocket/DividerModel.h`, `externalModels/src/rocket/DividerModel.cpp`
- Unsigned divider header/source: `externalModels/include/models/rocket/DividerUnsignedModel.h`, `externalModels/src/rocket/DividerUnsignedModel.cpp`

Current status:

- The 2.9% CorePerfDSL/backend no longer instantiates these divider ResourceModels for the ROCKET model.
- Current divide/remainder timing comes from `RocketMulRegisterModel` through `DivReady` and `DivIssue`.
- The older `EX_n_DIVDelay`, `EX_n_DIVUDelay`, and `divider_delay_cycles` trace fields are therefore intentionally absent.

## Part 2: Possible Reasons For Timing-Cycle Inaccuracies

### 1. CorePerfDSL / Generated Backend / Manual Instrumentation Drift

The ROCKET backend is generated from CorePerfDSL, then manually instrumented for trace observability.

Possible mismatch sources:

- Regenerating from `.llm_output/correction/ROCKET_0720_2.9%error.corePerfDsl` can overwrite temporary instrumentation.
- Manual instrumentation must continue to record values already computed by scheduling functions; calling stateful models again would change behavior.
- Trace fields may lag behind future CorePerfDSL changes if the generator is not updated.

Trace clues:

- Confirm the timing CSV header contains the current 68-field schema.
- Missing formula fields appear as `null`, not as omitted columns.

### 2. Branch Prediction / Redirect Timing Mismatch

Branch and jump effects are split across instructions:

- The branch or jump instruction calls `setPc_p`, `setPc_p_j`, or `setPc_p_jr` in IF.
- The branch or jump instruction calls `setPc_c` in MEM.
- The following instruction calls `getPc_mp()` and `getPc_pt()` in IF, which evaluates the previous control-flow instruction.

This means a branch timing problem may appear on the following instruction's IF timing rather than only on the branch row.

Possible mismatch sources:

- `Pc_mp` and `Pc_pt` are evaluated on the following instruction.
- `sim_misprediction` may describe the previous control-flow instruction consumed by the current row.
- Conditional branch taken status is inferred from the next PC and `brTarget`.
- `jalr` target prediction depends on simplified RAS/BTB behavior.
- Exact Rocket BTB page-entry compression is not modeled.
- Compressed return-address behavior uses `pc + 4` approximation.

Trace clues:

- `sim_misprediction`
- `IF_ext_Pc_mp`
- `IF_ext_Pc_pt`
- `IF_ext_Pc_p`
- `IF_ext_Pc_p_j`
- `IF_ext_Pc_p_jr`
- `IF_n_uA_PcCorrect`
- `IF_n_uA_PcPredict`
- `MEM_n_Branch`
- `MEM_n_FlushMem`
- `MEM_ext_Pc_c`

### 3. ICache Hit/Miss And Frontend Blocking Simplification

The ICache model is a simple tag-cache timing model with fixed hit/miss delays. It does not model all Rocket frontend structures.

Possible mismatch sources:

- Fixed hit delay `1` and miss delay `22`.
- Cacheable range is limited to `[0x80000000, 0x90000000)`.
- Simple LFSR replacement.
- No explicit instruction prefetch model.
- No fetch queue, fetch packet, MSHR, refill pipeline, or frontend replay detail.
- Previous ICache miss blocking is represented only through `Ic_out`.
- No shared L2 model is currently implemented.

Trace clues:

- `icache_miss`
- `icache_delay_cycles`
- `IF_n_ICache`
- `IF_ext_Ic_out`
- `IF_n_uA_CacheBlock`

### 4. DCache Hit/Miss, Store Blocking, And Memory-System Simplification

The DCache model is also a simple tag-cache timing model. Loads and stores share the same `getDelay()` style access, but real Rocket memory behavior can include more structures than this model represents.

Possible mismatch sources:

- Fixed hit delay `1`.
- Fixed miss/non-cacheable delay `6`.
- Cacheable range is limited to `[0x80000000, 0x90000000)`.
- Simple LFSR replacement.
- No store buffer occupancy model.
- No store-load forwarding model.
- No bank conflict, MSHR, refill, writeback, or memory-ordering detail.
- No shared L2 model is currently implemented.
- Source comment notes missing additional delay for an address blocked by a preceding store.

Trace clues:

- `dcache_miss`
- `dcache_delay_cycles`
- `MEM_n_DCache`
- `MEM_n_StoreCommit`
- `addr` in `ROCKET_trace_*.csv`

### 5. Shared MulDiv Latency Approximation

The current model does not directly stretch the multiply/divider instruction's own row by the long result latency. Instead, it delays later dependent consumers and later users of the shared MulDiv unit.

Possible mismatch sources:

- Current fixed multiply latency is `5` cycles; target RTL may use a different latency.
- Current fixed divider/remainder latency is `30` cycles; target RTL may use a different latency.
- Operand-dependent multiply/divider early-out behavior is not modeled.
- The shared MulDiv unit is modeled as one non-pipelined unit; RTL may differ by configuration.
- Producer writeback timing in the pipeline row may not correspond exactly to the architectural result-ready cycle used by the model.

Trace clues:

- `EX_ext_MulReady`
- `EX_n_MUL_max`
- `EX_n_MUL`
- `EX_ext_DivReady`
- `EX_n_DIV_max`
- `EX_n_DIV`
- `EX_n_DIVU_max`
- `EX_n_DIVU`
- `rd_ready_cycle`
- `ID_rs1_ready_cycle`
- `ID_rs2_ready_cycle`

### 6. Register Dependency / Forwarding Approximation

The register dependency model stores one ready cycle per register. It can explain RAW waits, but it does not encode the actual forwarding path that produced the value.

Possible mismatch sources:

- Missing bypass-source identity.
- Simplified readiness for ALU, load, CSR, multiply, divide, and jump-link producers.
- No detailed scoreboard model.
- A real Rocket bypass path may provide data earlier or later than the modeled ready cycle.
- Load readiness is currently captured from the generated DCache timing path, which may not exactly match RTL writeback/forwarding behavior.

Trace clues:

- `rs1`, `rs2`, `rd`
- `used_rs1`, `used_rs2`, `used_rd`
- `rd_ready_cycle`
- `ID_rs1_ready_cycle`
- `ID_rs2_ready_cycle`
- `ID_n_uA_OF_A`
- `ID_n_uA_OF_B`

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
- Final stage fields: `IF`, `ID`, `EX`, `MEM`, `WB`

### 9. Trace / RTL Comparison Boundary Mismatch

The simulator timing trace records modeled stage cycle variables, not raw RTL pipeline probe signals. RTL traces may define "fetch", "decode", "execute", "memory", or "commit" boundaries differently from this simulator.

Possible mismatch sources:

- Simulator `WB` may correspond to a conceptual writeback point, while RTL may expose retire, writeback, valid, or commit signals separately.
- Control-flow effects may be attributed to the following instruction's IF row.
- Cache and branch model internals may be updated during scheduling rather than exactly at RTL event boundaries.
- Timing rows include `pc` and `instr`, but `assembly` currently prints `null` in the timing CSV and should be cross-checked against `asm_trace_*.txt`.

Trace clues:

- Use `pc` and `instr` directly from `ROCKET_timing_*.csv`.
- Cross-check with `asm_trace_*.txt` and `ROCKET_trace_*.csv` when debugging trace alignment.
- Check local formula variables before attributing a mismatch to a single final stage gap.
