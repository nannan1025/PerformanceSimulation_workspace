# ROCKET Trace Fields Instrumentation 2.9% Report

## 1. Scope And Primary Inputs

This report focuses on the generated `ROCKET` backend, not the `RC` backend.

Primary files inspected:

- `.llm_output/correction/rocket_trace_field_instrumentation_plan.md`
- `.llm_output/correction/ROCKET_Trace_fields_instrumentation_4.3%.md`
- `.llm_output/correction/ROCKET_0720_2.9%error.corePerfDsl`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/include/ROCKET_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_PerformanceModel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/include/ROCKET_Channel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_Channel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_SchedulingFunction.cpp`
- Rocket external models under `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/libs/externalModels/include/models/rocket`

Before this re-instrumentation, the regenerated ROCKET timing trace had only:

```text
IF,ID,EX,MEM,WB
```

The `ROCKET_0720_2.9%error.corePerfDsl` model still describes:

```text
IF -> ID -> EX -> MEM -> WB
```

It also declares these trace values:

```text
rs1, rs2, rd, pc, brTarget, imm, rs1_data, rs2_data, addr
```

## 2. Current Timing CSV Field Count

The restored 2.9%-aware ROCKET timing trace now generates:

```text
68 fields
```

Validated representative file:

```text
.llm_output/correction/test/ROCKET_timing_0000.csv
```

Validation result:

```text
Header column count: 68
Checked rows: 51240
All checked rows matched the header column count.
```

## 3. Current Generated Timing Fields

### Identity Fields

These 9 fields are printed before the stage timing fields:

```text
pc,instr,assembly,rd,rs1,rs2,imm,rs1_data,rs2_data
```

Sources:

- `pc`, `rd`, `rs1`, `rs2`, `imm`, `rs1_data`, `rs2_data`: `ROCKET_Channel`
- `instr`: set in each scheduling function through `setInstructionInfo(...)`
- `assembly`: timing schema field kept for compatibility; currently prints `null` because this generated ROCKET timing backend has no real assembly string source connected from the assembly trace monitor

### Final Stage Timing Fields

These 5 fields are the final pipeline stage cycle values:

```text
IF,ID,EX,MEM,WB
```

Sources:

- `ROCKET_PerformanceModel::getPipelineStream()`
- stage assignments in `ROCKET_SchedulingFunction.cpp`

### Scheduling Variable Fields

These 45 fields expose local scheduling variables and connector-return values used by the stage formulas.

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
EX_ext_MulReady
EX_n_MUL_max
EX_n_MUL
EX_ext_DivReady
EX_n_DIV_max
EX_n_DIV
EX_n_DIVU_max
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

### Diagnostic Fields

These 9 fields are printed after the scheduling-variable fields:

```text
used_rs1
used_rs2
used_rd
rd_ready_cycle
icache_miss
dcache_miss
icache_delay_cycles
dcache_delay_cycles
sim_misprediction
```

Sources:

- `used_rs1`, `used_rs2`, `used_rd`: `setInstructionInfo(...)` in each scheduling function
- `rd_ready_cycle`: `setRdReadyCycle(...)`
- `icache_miss`: `iCacheModel.getMiss()` after the already-computed ICache delay call
- `dcache_miss`: `dCacheModel.getMiss()` after the already-computed DCache delay call
- `icache_delay_cycles`: local `ext_ICacheDelay` from `iCacheModel.getDelay()`
- `dcache_delay_cycles`: local `ext_DCacheDelay` from `dCacheModel.getDelay()`
- `sim_misprediction`: `dynBranchPredModel.getTrace_mispredict()` after `getPc_mp()` is evaluated

## 4. Where The Fields Were Added

### `ROCKET_PerformanceModel.h`

Restored timing-trace state and helpers:

- channel pointers for identity fields
- sparse scheduling-variable map
- cache miss/delay state
- simulated branch misprediction state
- operand-use flags
- destination-ready-cycle state
- helper methods:
  - `getSchedTraceColumns()`
  - `setInstructionInfo(...)`
  - `recordSchedVar(...)`
  - `setICacheInstrumentation(...)`
  - `setDCacheInstrumentation(...)`
  - `setSimMisprediction(...)`
  - `setRdReadyCycle(...)`
  - `resetTraceState()`

### `ROCKET_PerformanceModel.cpp`

Restored timing CSV schema and row printing:

- `getSchedTraceColumns()` defines the 45 fixed sparse scheduling-variable columns
- `connectChannel(...)` connects channel pointers
- `getPipelineStream()` emits one 68-field row and resets per-instruction trace state
- `getPrintHeader()` emits the 68-field timing header

### `ROCKET_Channel.h` / `ROCKET_Channel.cpp`

Restored/supports:

```text
rs1_data
rs2_data
assembly
```

`rs1_data` and `rs2_data` are required because the 2.9% CorePerfDSL declares them and maps them for divider-family instructions.

`assembly` is kept as a schema field, but the current timing backend has no real in-memory assembly source. It therefore prints `null` in the timing CSV.

### `ROCKET_SchedulingFunction.cpp`

Restored per-instruction trace capture:

- `setInstructionInfo(...)` at the start of every scheduling lambda
- `recordSchedVar(...)` after local formula variables are computed
- one local capture per stateful external-model call
- cache instrumentation after the existing cache-delay calls
- MulDiv readiness instrumentation for multiply and divider/remainder families
- branch connector instrumentation for `Pc_mp`, `Pc_pt`, `Pc_p`, `Pc_p_j`, `Pc_p_jr`, and `Pc_c`

## 5. Restored Fields From The Previous 4.3% Version

The following previous fields were restored unchanged:

- identity fields:
  - `pc`
  - `instr`
  - `assembly`
  - `rd`
  - `rs1`
  - `rs2`
  - `imm`
  - `rs1_data`
  - `rs2_data`
- final stage fields:
  - `IF`
  - `ID`
  - `EX`
  - `MEM`
  - `WB`
- IF scheduling fields:
  - all previous IF fields
- ID scheduling fields:
  - all previous ID fields
- retained EX scheduling fields:
  - `EX_n_ALU`
  - `EX_n_MUL_max`
  - `EX_n_MUL`
  - `EX_n_DIV`
  - `EX_n_DIVU`
  - `EX_n_EXPass`
  - `EX_n_DTLB`
  - `EX_n_LSUReq`
  - `EX_prev_MEM`
- MEM scheduling fields:
  - all previous MEM fields
- WB scheduling fields:
  - all previous WB fields
- retained diagnostics:
  - `used_rs1`
  - `used_rs2`
  - `used_rd`
  - `rd_ready_cycle`
  - `icache_miss`
  - `dcache_miss`
  - `icache_delay_cycles`
  - `dcache_delay_cycles`
  - `sim_misprediction`

## 6. Deleted Fields From The Previous 4.3% Version

These previous fields were not restored:

```text
EX_n_DIVDelay
EX_n_DIVUDelay
divider_delay_cycles
```

Reason:

In the current 2.9% CorePerfDSL/backend, divider and remainder instructions use the shared `RocketMulRegisterModel` connector path:

```text
DivReady -> DIV -> DivIssue
DivReady -> DIVU -> DivIssue
```

The generated scheduling functions no longer call:

```text
divider.getDelay()
divider_u.getDelay()
```

Therefore the old divider-delay fields would be stale and misleading for this backend version.

## 7. New Fields Added For The 2.9% Version

These 4 fields were added:

```text
EX_ext_MulReady
EX_ext_DivReady
EX_n_DIV_max
EX_n_DIVU_max
```

Meanings:

- `EX_ext_MulReady`: value returned by `regModel.getMulReady()` before computing `n_MUL_max`
- `EX_ext_DivReady`: value returned by `regModel.getDivReady()` before computing `n_DIV_max` or `n_DIVU_max`
- `EX_n_DIV_max`: max input result before signed divider/remainder issue cycle
- `EX_n_DIVU_max`: max input result before unsigned divider/remainder issue cycle

These fields match the current shared MulDiv-unit scheduling formulas:

```text
n_MUL_max  = max(n_ID, getMulReady())
n_MUL      = n_MUL_max + 1
n_DIV_max  = max(n_ID, getDivReady())
n_DIV      = n_DIV_max + 1
n_DIVU_max = max(n_ID, getDivReady())
n_DIVU     = n_DIVU_max + 1
```

## 8. Difference Between Previous Version

Compared with `ROCKET_Trace_fields_instrumentation_4.3%.md`:

- Current regenerated ROCKET backend initially lost all manual instrumentation and returned to 5 timing fields.
- Current restored schema has 68 fields, not the previous 67 fields.
- Scheduling-variable fields increased from 43 to 45 because the 2.9% schema removes 2 old divider ResourceModel delay fields and adds 4 shared MulDiv readiness/max fields.
- Removed scheduling-variable fields:

```text
EX_n_DIVDelay
EX_n_DIVUDelay
```

- Added scheduling-variable fields:

```text
EX_ext_MulReady
EX_ext_DivReady
EX_n_DIV_max
EX_n_DIVU_max
```

- Retained divider/remainder scheduling fields whose meaning changed to the shared MulDiv connector model:

```text
EX_n_DIV
EX_n_DIVU
```

- Diagnostic fields decreased from 10 to 9 because the old divider ResourceModel delay diagnostic was removed.
- Removed diagnostic field:

```text
divider_delay_cycles
```

- Retained diagnostics:

```text
used_rs1
used_rs2
used_rd
rd_ready_cycle
icache_miss
dcache_miss
icache_delay_cycles
dcache_delay_cycles
sim_misprediction
```

- No new diagnostic field was added; the new divider/multiply observability is represented as scheduling-variable fields instead.
- Divider/remainder `rd_ready_cycle` now comes from `RocketMulRegisterModel::getLastDivResultReadyCycle()`.
- Multiply `rd_ready_cycle` now comes from `RocketMulRegisterModel::getLastMulResultReadyCycle()`.
- `assembly` remains in the schema, but currently prints `null` because this generated timing backend does not receive a real assembly string from the assembly trace monitor.

## 9. Validation

Build command:

```bash
cmake --build etiss-perf-sim/etiss/build_dir --target SWEVAL_BACKENDS_LIB SoftwareEval install -j2
```

Result:

```text
Completed successfully.
```

Smoke run command:

```bash
./scripts/run.sh em:ud.riscv ROCKET -ta=.llm_output/correction/test -tp=.llm_output/correction/test
```

Result:

```text
Completed successfully.
```

Representative generated files inspected:

```text
.llm_output/correction/test/asm_trace_0000.txt
.llm_output/correction/test/ROCKET_trace_0000.csv
.llm_output/correction/test/ROCKET_timing_0000.csv
```

Timing CSV validation:

```text
ROCKET_timing_0000.csv header columns: 68
Rows checked: 51240
All checked rows had the same column count as the header.
```

The timing header contains the new 2.9%-specific fields:

```text
EX_ext_MulReady
EX_ext_DivReady
EX_n_DIV_max
EX_n_DIVU_max
```

The stale fields are absent:

```text
EX_n_DIVDelay
EX_n_DIVUDelay
divider_delay_cycles
```

## 10. Limitations And Follow-Up Work

- This is temporary generated-backend instrumentation. Regenerating the ROCKET backend can overwrite it again.
- For permanent support, the trace schema and `recordSchedVar(...)` emission should move into the CorePerfDSL generator/templates.
- `assembly` is present but prints `null`; real assembly should be passed from the assembly trace monitor/channel path if it must be row-local in timing CSV.
- `sim_misprediction` may describe branch state consumed while scheduling the following instruction, so it is useful but not always perfectly branch-row-local.
- Exact stage-blocker attribution is still not printed; it can be derived offline from the exposed max-expression inputs.
- Exact RAW blocker and forwarding-source-stage labels are still not printed. The trace currently exposes source ready cycles and destination ready cycle.
