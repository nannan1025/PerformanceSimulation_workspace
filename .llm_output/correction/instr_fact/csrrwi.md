# csrrwi

## 1. Primary source

- `ROCKET_SchedulingFunction.cpp`
- Scheduling function: `schedulingFunction_csrrwi`
- Scheduling-function id: `43`
- Source location: `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_SchedulingFunction.cpp:3103`

## 2. Instruction Input

- Instruction inputs: pc, csr, imm/uimm, rd. No integer source register readiness is used in this formula.

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
ID = n_ID = max(n_Decoder, prev.EX)
n_EXPass = n_ID + 1
EX = n_EX = max(n_EXPass, prev.MEM)
n_MEMPass = n_EX + 1
MEM = n_MEM = max(n_MEMPass, prev.WB)
n_CSR = n_MEM + 1
rd_ready_cycle = n_CSR
rd_ready_stage = CSR
RegReady[rd] = n_CSR
n_Reg = n_MEM + 1
WB = n_WB = max(n_CSR, n_Reg)
```

## 4. Normal Case

Assuming no cache/register/resource stalls:

```text
IF = prev.IF + 1
ID = IF + 1
EX = ID + 1
MEM = EX + 1
WB = MEM + 1
rd_ready_cycle = WB
rd_ready_stage = CSR
```

## 5.Possible reason for each abnormal stage

IF:
    Previous instruction/control state: previous branch misprediction or correction makes `ext.Pc_mp` later than the normal fetch time.
    Previous instruction/control state: previous predicted-taken branch or jump redirect makes `ext.Pc_pt` later than the normal fetch time.
    Previous instruction/cache state: previous ICache miss or fetch block makes `ext.Ic_out` later than the normal fetch time.
    Current instruction: current fetch has an ICache miss or long ICache delay, so `ext.ICacheDelay > 1` and `n_ICache` wins.
    Previous pipeline state: previous decode/front-end backpressure makes `prev.ID` win the IF `max(...)`.
ID:
    Current instruction: no integer source-register readiness is modeled for this instruction class.
    Previous pipeline state: previous execute-stage occupancy/backpressure makes `prev.EX` win the ID `max(...)`.
EX:
    Current instruction: EX pass-through is modeled as `n_EXPass = n_ID + 1`; any longer intended CSR pre-retire execute behavior would be a wrong execution cycle count.
    Previous pipeline state: previous memory-stage occupancy/backpressure makes `prev.MEM` win the EX `max(...)`.
MEM:
    Current instruction: MEM pass-through path is normally `n_MEMPass = n_EX + 1`.
    Previous pipeline state: previous writeback/commit occupancy makes `prev.WB` win the MEM `max(...)`.
WB:
    Current instruction: CSR retire/writeback is modeled as `n_CSR = n_MEM + 1`; if this should be later, the CSR writeback cycle count is wrong.
    Current instruction/modeling: incorrect published forwarding stage `rd_ready_stage = CSR` would affect later consumers of `rd`.
    Instrumentation/modeling: if WB is not `MEM + 1` for this formula class, suspect trace extraction, regenerated code changes, or an unmodeled writeback/commit delay.
