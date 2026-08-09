# ROCKET Trace Fields Instrumentation 4.3% Report

## 1. Scope And Primary Inputs

This report focuses on the ROCKET backend, not the RC backend.

Primary files inspected:

- `.llm_output/correction/rocket_trace_field_instrumentation_plan.md`
- `.llm_output/correction/ROCKET_0717_4.3%error.corePerfDsl`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/include/ROCKET_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_PerformanceModel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/include/ROCKET_Channel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_Channel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_SchedulingFunction.cpp`
- Rocket external models under `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/rocket` and `src/rocket`
- Representative timing trace: `.llm_output/correction/test/ROCKET_timing_0000.csv`

The CorePerfDSL file describes a 5-stage ROCKET pipeline:

```text
IF -> ID -> EX -> MEM -> WB
```

The CorePerfDSL also provides these trace values through the channel layer:

```text
pc, brTarget, rs1, rs2, rd, imm, rs1_data, rs2_data, addr
```

The current ROCKET backend additionally has manual timing-trace instrumentation in the generated backend files.

## 2. Current Timing CSV Field Count

The current instrumented ROCKET backend can generate 67 timing fields in `ROCKET_timing_*.csv`.

Representative checked file:

```text
.llm_output/correction/test/ROCKET_timing_0000.csv
```

Observed result:

```text
Header column count: 67
Checked data rows: same column count as header
```

Important note:

Some older files under `trace_output/ROCKET/...` still contain only:

```text
IF,ID,EX,MEM,WB
```

Those are older or non-instrumented outputs. The current inspected ROCKET backend is capable of producing the wider 67-column timing trace.

## 3. Current Generated Timing Fields

### Identity Fields

These 9 fields are printed before the stage timing fields:

```text
pc,instr,assembly,rd,rs1,rs2,imm,rs1_data,rs2_data
```

Sources:

- `pc`, `rd`, `rs1`, `rs2`, `imm`, `rs1_data`, `rs2_data`: `ROCKET_Channel`
- `instr`: set in each scheduling function through `setInstructionInfo(...)`
- `assembly`: `ROCKET_Channel::assembly`

### Final Stage Timing Fields

These 5 fields are the final pipeline stage cycle values:

```text
IF,ID,EX,MEM,WB
```

Sources:

- `ROCKET_PerformanceModel::getPipelineStream()`
- Stage values are assigned in `ROCKET_SchedulingFunction.cpp`

### Scheduling Variable Fields

These 43 fields expose local scheduling variables used by the stage formulas.
The naming rule is:

```text
<STAGE>_<variable_name>
```

IF-stage scheduling variables:

```text
IF_n_Enter
IF_n_PC_Gen
IF_n_uA_PcCorrect
IF_n_uA_CacheBlock
IF_n_uA_PcPredict
IF_n_ITLB
IF_n_ICache
IF_n_BPU
IF_prev_ID
IF_ext_Pc_mp
IF_ext_Pc_pt
IF_ext_Pc_p
IF_ext_Pc_p_j
IF_ext_Pc_p_jr
IF_ext_Ic_out
```

ID-stage scheduling variables:

```text
ID_n_Decoder
ID_rs1_ready_cycle
ID_rs2_ready_cycle
ID_n_uA_OF_A
ID_n_uA_OF_B
ID_prev_EX
```

EX-stage scheduling variables:

```text
EX_n_ALU
EX_n_MUL_max
EX_n_MUL
EX_n_DIVDelay
EX_n_DIV
EX_n_DIVUDelay
EX_n_DIVU
EX_n_EXPass
EX_n_DTLB
EX_n_LSUReq
EX_prev_MEM
```

MEM-stage scheduling variables:

```text
MEM_n_MEMPass
MEM_n_DCache
MEM_n_StoreCommit
MEM_n_Branch
MEM_n_FlushMem
MEM_prev_WB
MEM_ext_Pc_c
```

WB-stage scheduling variables:

```text
WB_n_Reg
WB_n_CSR
WB_n_WBPass
WB_n_LoadWB
```

Missing scheduling variables are printed as:

```text
null
```

For example, an ALU instruction usually does not use `MEM_n_DCache`, so that field is printed as `null`.

### Diagnostic Fields

These 10 fields are printed after the scheduling-variable fields:

```text
used_rs1
used_rs2
used_rd
rd_ready_cycle
icache_miss
dcache_miss
icache_delay_cycles
dcache_delay_cycles
divider_delay_cycles
sim_misprediction
```

Sources:

- `used_rs1`, `used_rs2`, `used_rd`: set by `setInstructionInfo(...)` in each scheduling function
- `rd_ready_cycle`: recorded with `setRdReadyCycle(...)`
- `icache_miss`: read from `iCacheModel.getMiss()` after the existing ICache delay call
- `dcache_miss`: read from `dCacheModel.getMiss()` after the existing DCache delay call
- `icache_delay_cycles`: recorded from the already-computed ICache delay local
- `dcache_delay_cycles`: recorded from the already-computed DCache delay local
- `divider_delay_cycles`: recorded from the already-computed divider delay local
- `sim_misprediction`: read from `dynBranchPredModel.getTrace_mispredict()`

## 4. Where The Current Fields Are Added

### `ROCKET_PerformanceModel.h`

This is where trace state and helper APIs are declared.

Important pieces:

- Channel pointers:
  - `pc_ptr`
  - `rd_ptr`
  - `rs1_ptr`
  - `rs2_ptr`
  - `imm_ptr`
  - `rs1_data_ptr`
  - `rs2_data_ptr`
  - `assembly_ptr`
- Per-instruction trace state:
  - instruction name
  - operand-use flags
  - cache miss/delay values
  - divider delay
  - simulated misprediction
  - sparse scheduling-variable map
- Helper methods:
  - `setInstructionInfo(...)`
  - `recordSchedVar(...)`
  - `setICacheInstrumentation(...)`
  - `setDCacheInstrumentation(...)`
  - `setSimMisprediction(...)`
  - `setRdReadyCycle(...)`
  - `setDividerDelay(...)`
  - `resetTraceState()`

### `ROCKET_PerformanceModel.cpp`

This is where the timing CSV schema and row printing are implemented.

Important locations:

- `getSchedTraceColumns()`
  - defines the fixed ordered list of scheduling-variable columns
- `connectChannel(...)`
  - connects channel values and external model pointers
- `getPipelineStream()`
  - emits one timing row
  - prints unset sparse variables as `null`
  - resets per-instruction trace state after printing
- `getPrintHeader()`
  - emits the timing CSV header

Any new field that should appear in `ROCKET_timing_*.csv` must be added consistently to:

```text
ROCKET_PerformanceModel.h
ROCKET_PerformanceModel.cpp::getPrintHeader()
ROCKET_PerformanceModel.cpp::getPipelineStream()
```

If the field is sparse and formula-related, it should also be added to:

```text
ROCKET_PerformanceModel.cpp::getSchedTraceColumns()
```

### `ROCKET_Channel.h` / `ROCKET_Channel.cpp`

This is where instruction/channel trace values are stored and exposed.

Current channel values include:

```text
pc, brTarget, rs1, rd, imm, rs2, rs1_data, rs2_data, addr, assembly
```

To add a new identity or instruction-input field, add it here if the value is not already in the channel.

Examples of fields that could be added from the channel path:

```text
brTarget
addr
type_id
```

### `ROCKET_SchedulingFunction.cpp`

This is where local scheduling variables are computed and recorded.

Current instrumentation pattern:

```cpp
perfModel->setInstructionInfo("add", true, true, true);
perfModel->recordSchedVar("IF_n_PC_Gen", n_PC_Gen);
perfModel->recordSchedVar("ID_n_uA_OF_A", n_uA_OF_A);
perfModel->recordSchedVar("EX_n_ALU", n_ALU);
perfModel->setRdReadyCycle(n_ALU);
```

This file is the correct place to add fields that depend on scheduling locals, such as:

```text
n_PC_Gen
n_ICache
n_uA_OF_A
n_ALU
n_MUL
n_DIV
n_DCache
n_Branch
prev.ID
prev.EX
prev.MEM
prev.WB
```

Important constraint:

Do not call stateful model methods twice for trace output. Store stateful method results in local variables once, use the local for both the formula and trace recording.

Examples:

```cpp
auto ext_Pc_mp = perfModel->dynBranchPredModel.getPc_mp();
auto ext_ICacheDelay = perfModel->iCacheModel.getDelay();
auto rs1_ready_cycle = perfModel->regModel.getXa();
```

Then record the local values:

```cpp
perfModel->recordSchedVar("IF_ext_Pc_mp", ext_Pc_mp);
perfModel->recordSchedVar("IF_n_ICache", n_ICache);
perfModel->recordSchedVar("ID_rs1_ready_cycle", rs1_ready_cycle);
```

### External Models

External model fields currently used:

- Branch model:
  - `getPc_mp()`
  - `getPc_pt()`
  - `getTrace_mispredict()`
- ICache model:
  - `getDelay()`
  - `getMiss()`
- DCache model:
  - `getDelay()`
  - `getMiss()`
- Divider models:
  - `getDelay()`
- Register / Mul register model:
  - `getXa()`
  - `getXb()`
  - `setXd(...)`
  - `getMulReady()`
  - `setMulIssue(...)`

If a new field needs external-model internals, prefer adding a read-only getter. Do not add a second call to an existing stateful method just for trace output.

## 5. Fields That Can Currently Be Generated

The current ROCKET backend can generate these field groups directly:

- instruction identity:
  - `pc`
  - `instr`
  - `assembly`
  - `rd`
  - `rs1`
  - `rs2`
  - `imm`
  - `rs1_data`
  - `rs2_data`
- final stage timing:
  - `IF`
  - `ID`
  - `EX`
  - `MEM`
  - `WB`
- sparse scheduling variables:
  - all 43 fields listed in section 3
- basic data-hazard fields:
  - `used_rs1`
  - `used_rs2`
  - `used_rd`
  - `rd_ready_cycle`
- cache fields:
  - `icache_miss`
  - `dcache_miss`
  - `icache_delay_cycles`
  - `dcache_delay_cycles`
- divider field:
  - `divider_delay_cycles`
- branch field:
  - `sim_misprediction`

These fields are already present in the checked 67-column timing CSV header.

## 6. Fields Available But Not Currently Printed

The current code has enough information to add several more fields, but they are not part of the current 67-column timing CSV.

### Channel Fields Not Printed In Timing CSV

These are available in `ROCKET_Channel` but are not currently timing CSV columns:

```text
brTarget
addr
```

Likely place to add:

- add channel pointers in `ROCKET_PerformanceModel.h`
- connect them in `ROCKET_PerformanceModel.cpp::connectChannel(...)`
- print them in `getPrintHeader()` and `getPipelineStream()`

### Detailed Branch Predictor Fields

The Rocket branch model exposes several read-only debug getters that are not currently printed:

```text
branch_taken
branch_predicted_taken
branch_direction_mispredict
branch_target_mispredict
branch_predicted_target
branch_actual_target
branch_predictor_component
branch_redirect_source_pc
branch_redirect_source_component
branch_btb_hit
branch_bht_index
branch_ras_used
```

Likely place to add:

- add trace state and print columns in `ROCKET_PerformanceModel`
- capture the getter results in `ROCKET_SchedulingFunction.cpp` after the relevant branch connector calls

Caveat:

Some branch trace values may describe the control-flow instruction resolved while scheduling the following row. They are useful, but not always perfectly row-local to the branch instruction itself.

### Stage Gap Fields

These are not printed now:

```text
stage_gap_if_id
stage_gap_id_ex
stage_gap_ex_mem
stage_gap_mem_wb
```

They can be derived from existing stage fields:

```text
stage_gap_if_id  = ID  - IF
stage_gap_id_ex  = EX  - ID
stage_gap_ex_mem = MEM - EX
stage_gap_mem_wb = WB  - MEM
```

Likely place to add:

- compute directly in `ROCKET_PerformanceModel::getPipelineStream()`
- no scheduling-function change is required

### RAW Attribution Fields

These first-pass plan fields are not currently printed:

```text
raw_wait_cycles
raw_blocking_reg
raw_blocking_ready_cycle
forward_source_stage
```

Current timing CSV prints:

```text
ID_rs1_ready_cycle
ID_rs2_ready_cycle
rd_ready_cycle
```

This is enough to diagnose many dependencies manually, but it does not explicitly say which source register blocked the instruction or which forwarding stage produced the value.

Likely place to add:

- wrap or locally instrument `regModel.getXa()` and `regModel.getXb()` in `ROCKET_SchedulingFunction.cpp`
- compare ready cycles against the current decode/input baseline
- record the max blocking source
- add read-only provenance support in the register model if exact `forward_source_stage` is required

Caveat:

The current register model returns ready cycles, not a source-stage label. Exact forwarding-source-stage output requires additional model semantics.

### Instruction ID / Type ID

These are not currently printed:

```text
instr_id
type_id
```

Current `instr` string covers mnemonic-level grouping.

Likely place to add:

- `instr_id`: increment in `ROCKET_PerformanceModel::getPipelineStream()`
- `type_id`: add from scheduling function metadata or generated instruction type metadata

## 7. Relationship To `ROCKET_0717_4.3%error.corePerfDsl`

The CorePerfDSL file defines the pipeline, resources, connectors, microactions, instruction mappings, trace values, and external model bindings. It does not by itself define the current 67-column timing CSV schema.

Current formula-related trace output is added manually in the generated ROCKET backend:

```text
variants/ROCKET/include/ROCKET_PerformanceModel.h
variants/ROCKET/src/ROCKET_PerformanceModel.cpp
variants/ROCKET/src/ROCKET_SchedulingFunction.cpp
```

If the backend is regenerated from `ROCKET_0717_4.3%error.corePerfDsl`, the manual instrumentation may be overwritten unless the code generator/templates are also updated.

For permanent trace support, the correct long-term place to add these fields is the generator/CorePerfDSL trace-generation path, not only the generated `variants/ROCKET` files.

## 8. Recommended Places To Add Future Fields

### Add A New Always-Present Timing CSV Column

Modify:

```text
ROCKET_PerformanceModel.h
ROCKET_PerformanceModel.cpp::getPrintHeader()
ROCKET_PerformanceModel.cpp::getPipelineStream()
```

Use this for fields such as:

```text
instr_id
stage_gap_if_id
brTarget
addr
branch_taken
branch_btb_hit
```

### Add A New Sparse Scheduling Variable

Modify:

```text
ROCKET_PerformanceModel.cpp::getSchedTraceColumns()
ROCKET_SchedulingFunction.cpp
```

Pattern:

```cpp
perfModel->recordSchedVar("<STAGE>_<variable_name>", value);
```

Unset variables will print as:

```text
null
```

Use this for new formula-local variables or external connector locals.

### Add A New Channel-Based Field

Modify:

```text
ROCKET_Channel.h
ROCKET_Channel.cpp
ROCKET_PerformanceModel.h
ROCKET_PerformanceModel.cpp
```

Use this for fields that come from instruction decoding or the trace channel, such as:

```text
brTarget
addr
instruction length
type_id
```

### Add A New External-Model Diagnostic

Modify:

```text
externalModels/include/models/rocket/<Model>.h
externalModels/src/rocket/<Model>.cpp
ROCKET_PerformanceModel.h
ROCKET_PerformanceModel.cpp
ROCKET_SchedulingFunction.cpp
```

Use read-only getters when possible. Avoid changing timing behavior.

## 9. Current Limitations

- Current 67-field instrumentation is temporary generated-backend instrumentation.
- Regenerating the ROCKET backend may remove the manual trace-field additions.
- Some old timing traces still have only `IF,ID,EX,MEM,WB`; they do not reflect the current instrumented backend schema.
- `sim_misprediction` may be shifted relative to the branch row because branch redirect state can be consumed by the following instruction.
- `icache_delay_cycles`, `dcache_delay_cycles`, and `divider_delay_cycles` are recorded from the delay values already used by the scheduler. They should be interpreted as modeled delay values from the external models, not necessarily extra cycles beyond a hit baseline.
- Exact RAW blocker and exact forwarding source stage are not currently printed.
- Exact stage-blocker attribution is not printed; the trace exposes the max-expression inputs, and the blocker can be derived offline.
- Cache set/tag/replacement-way fields are not currently printed.
- Detailed BTB/RAS/BHT predictor internals are available only partially through external model debug getters and are not part of the current timing schema.

## 10. Summary

For the current ROCKET backend associated with `ROCKET_0717_4.3%error.corePerfDsl`, the instrumented timing trace can generate:

```text
67 fields total
```

Breakdown:

```text
9  identity fields
5  final stage fields
43 scheduling-variable fields
10 diagnostic fields
```

The main files where these fields are added are:

```text
ROCKET_PerformanceModel.h
ROCKET_PerformanceModel.cpp
ROCKET_SchedulingFunction.cpp
ROCKET_Channel.h
ROCKET_Channel.cpp
```

The current backend already prints the important stage-formula variables and basic diagnostic fields requested by the earlier instrumentation plan. Additional fields such as detailed branch predictor internals, stage gaps, memory address, branch target, RAW blocker, and forwarding source stage can be added in the same instrumentation pattern, but some require extra read-only model metadata or generator support to be permanent.
