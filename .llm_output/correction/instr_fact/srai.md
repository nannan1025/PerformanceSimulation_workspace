# srai

## 1. Primary source

- `ROCKET_SchedulingFunction.cpp`
- Scheduling function: `schedulingFunction_srai`
- Scheduling-function id: `20`
- Source location: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_SchedulingFunction.cpp:1447`

## 2. Instruction Input

- Instruction inputs: pc, rs1, imm, rd. `rs1_value` and `imm` feed the ALU operation.

Variable classes used below:

- Local variables are `n_*` values created inside this scheduling lambda, such as `n_IF`, `n_ID`, `n_ALU`, or `n_DCache`. They can be traced by saving them before the lambda returns.
- External variables are values read from persistent simulator state or external models: previous stage state `prev.IF/ID/EX/MEM/WB`, branch connector times `ext.Pc_mp/Pc_pt`, cache connector/delay values `ext.Ic_out/ICacheDelay/DCacheDelay`, divider delay `ext.DIVDelay/ext.DIVUDelay`, and register readiness `rs1_ready_cycle/rs2_ready_cycle` from the register model.
- `prev.*` means the corresponding `perfModel->*` value before this instruction updates it.
- `rs1_forward_source_stage` and `rs2_forward_source_stage` are defined by the previous producer of that register. If the producer used `setRegWriteReady(n_ALU)`, the source stage is `ALU`; if it used `setRegWriteReady(n_MUL)`, `MUL`; if `setRegWriteReady(n_DIV)` or `n_DIVU`, `DIV` or `DIVU`; if `setRegWriteReady(n_LoadWB)`, `LoadWB`; if `setRegWriteReady(n_CSR)`, `CSR`. If the operand is already available from the architectural register file or is x0/no dependency, the source stage is `RegFile/none`.


## 3. Complete formula summary

```text
n_Enter = prev.IF
n_PC_Gen = n_Enter + 1
n_uA_PcCorrect = max(n_Enter, ext.Pc_mp)
n_uA_CacheBlock = max(n_Enter, ext.Ic_out)
n_uA_PcPredict = max(n_Enter, ext.Pc_pt)
n_ITLB = n_Enter + 1
n_ICache = n_Enter + ext.ICacheDelay
IF = n_IF = max(n_PC_Gen, n_uA_PcCorrect, n_uA_CacheBlock, n_uA_PcPredict, n_ITLB, n_ICache, prev.ID)
n_Decoder = n_IF + 1
rs1_ready_cycle = ext.RegReady[rs1]
rs1_forward_source_stage = prev_writer[rs1].rd_ready_stage
n_uA_OF_A = max(n_IF, rs1_ready_cycle)
ID = n_ID = max(n_Decoder, n_uA_OF_A, prev.EX)
n_ALU = n_ID + 1
rd_ready_cycle = n_ALU
rd_ready_stage = ALU
RegReady[rd] = n_ALU
EX = n_EX = max(n_ALU, prev.MEM)
n_MEMPass = n_EX + 1
MEM = n_MEM = max(n_MEMPass, prev.WB)
n_Reg = n_MEM + 1
WB = n_WB = n_Reg
```

## 4. Normal Case

Assuming no cache/branch/register/resource stalls:

```text
IF = prev.IF + 1
ID = IF + 1
EX = ID + 1
MEM = EX + 1
WB = MEM + 1
rd_ready_cycle = ID + 1
rd_ready_stage = ALU
```

## 5.Possible reason for each abnormal stage

IF:
    Previous instruction/control state: previous branch misprediction or correction makes `ext.Pc_mp` later than the normal fetch time.
    Previous instruction/control state: previous predicted-taken branch or jump redirect makes `ext.Pc_pt` later than the normal fetch time.
    Previous instruction/cache state: previous ICache miss or fetch block makes `ext.Ic_out` later than the normal fetch time.
    Current instruction: current fetch has an ICache miss or long ICache delay, so `ext.ICacheDelay > 1` and `n_ICache` wins.
    Previous pipeline state: previous decode/front-end backpressure makes `prev.ID` win the IF `max(...)`.
ID:
    Previous producer instruction: RAW dependency on `rs1` delays `rs1_ready_cycle`, so `n_uA_OF_A` wins.
    Previous producer/instrumentation: incorrect dataforwarding source stage for `rs1` gives the wrong `rs1_ready_cycle` and makes ID too early or too late.
    Previous pipeline state: previous execute-stage occupancy/backpressure makes `prev.EX` win the ID `max(...)`.
EX:
    Current instruction: ALU path is modeled as `n_ALU = n_ID + 1`; any longer intended ALU/link/target calculation would be a wrong execution cycle count.
    Current instruction/modeling: incorrect published forwarding stage `rd_ready_stage = ALU` would affect later consumers of `rd`.
    Previous pipeline state: previous memory-stage occupancy/backpressure makes `prev.MEM` win the EX `max(...)`.
MEM:
    Current instruction: MEM pass-through path is normally `n_MEMPass = n_EX + 1`.
    Previous pipeline state: previous writeback/commit occupancy makes `prev.WB` win the MEM `max(...)`.
WB:
    Current instruction: register writeback is modeled as `n_Reg = n_MEM + 1`; no extra WB stall is represented after MEM.
    Instrumentation/modeling: if WB is not `MEM + 1` for this formula class, suspect trace extraction, regenerated code changes, or an unmodeled writeback/commit delay.
