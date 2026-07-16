# Rocket Trace Instrumentation V2

## 1. Files and plans inspected before implementation

- `.llm_output/correction/rocket_basic_summary.md`
- `.llm_output/correction/rocket_trace_field_instrumentation_plan.md`
- `.llm_output/correction/trace_instrumentation.md`
- `.llm_output/correction/instr_fact/*.md`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/include/ROCKET_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_PerformanceModel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_SchedulingFunction.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/include/ROCKET_Channel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_Printer.cpp`
- `scripts/run.sh` and `scripts/run2.sh`

## 2. Instruction formula/fact files used

All 66 files under `.llm_output/correction/instr_fact` were used as the field guide. Representative files checked during implementation included:

- `add.md`
- `lw.md`
- `sw.md`
- `beq.md`
- `div.md`
- `jalr.md`
- `csrrw.md`

These files identify the stage formulas, local variables, external variables, and abnormal-stage reasons used to choose the V2 timing columns.

## 3. Files modified

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/include/ROCKET_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_PerformanceModel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/ROCKET/src/ROCKET_SchedulingFunction.cpp`
- `scripts/run.sh`

Note: the validation run also updated runtime `.ini` state under `etiss-perf-sim/simulator`; those files were not part of the trace-instrumentation implementation.

## 4. New timing CSV fields

The timing CSV now starts with:

```text
pc,instr,assembly,rd,rs1,rs2,imm,IF,ID,EX,MEM,WB
```

It then emits fixed scheduling-variable columns:

```text
IF_n_Enter,IF_n_PC_Gen,IF_n_uA_PcCorrect,IF_n_uA_CacheBlock,IF_n_uA_PcPredict,IF_n_ITLB,IF_n_ICacheDelay,IF_n_ICache,IF_n_BPU,IF_prev_ID,IF_ext_Pc_mp,IF_ext_Ic_out,IF_ext_Pc_pt
ID_n_Decoder,ID_rs1_ready_cycle,ID_rs2_ready_cycle,ID_n_uA_OF_A,ID_n_uA_OF_B,ID_prev_EX
EX_n_ALU,EX_n_MUL,EX_n_DIVDelay,EX_n_DIV,EX_n_DIVUDelay,EX_n_DIVU,EX_n_EXPass,EX_n_DTLB,EX_n_LSUReq,EX_prev_MEM
MEM_n_MEMPass,MEM_n_DCacheDelay,MEM_n_DCache,MEM_n_StoreCommit,MEM_n_Branch,MEM_n_FlushMem,MEM_prev_WB
WB_n_Reg,WB_n_CSR,WB_n_WBPass,WB_n_LoadWB
```

The required flags are emitted after the scheduling variables:

```text
icache_miss,dcache_miss,branch_control,branch_misprediction
```

The first-version diagnostics are preserved after the V2 fields:

```text
instr_id,uses_rs1,uses_rs2,uses_rd,uses_imm,stage_gap_if_id,stage_gap_id_ex,stage_gap_ex_mem,stage_gap_mem_wb,raw_wait_cycles,raw_blocking_reg,raw_blocking_ready_cycle,icache_delay_cycles,dcache_delay_cycles,branch_redirect_cycles,divider_delay_cycles
```

## 5. Naming rule

Scheduling variables use:

```text
<STAGE>_<variable_name>
```

Examples:

- `IF_n_PC_Gen`
- `IF_n_uA_PcCorrect`
- `ID_n_uA_OF_A`
- `EX_n_ALU`
- `MEM_n_DCache`
- `WB_n_Reg`

External-model and previous-stage inputs are named explicitly:

- `IF_ext_Pc_mp`
- `IF_ext_Ic_out`
- `IF_ext_Pc_pt`
- `IF_prev_ID`
- `ID_prev_EX`
- `EX_prev_MEM`
- `MEM_prev_WB`

## 6. Missing-variable representation

If a variable is not used by the current instruction formula, the CSV field is printed as:

```text
null
```

Examples verified:

- `addi` rows print `null` for `EX_n_MUL`, `EX_n_DIV`, `EX_n_DIVU`, and `MEM_n_DCache`.
- Load/store rows populate `MEM_n_DCache`.
- Branch rows populate `IF_n_BPU`, `MEM_n_Branch`, and `MEM_n_FlushMem`.

The `assembly` column is also printed as `null` because `ROCKET_PerformanceModel` has no safe in-memory assembly string. The actual disassembly remains available in `asm_trace_*.txt` and can be joined offline by PC/row.

## 7. Variable capture sources

- Instruction identity: `setInstructionInfo(...)` in each generated Rocket scheduling lambda records the mnemonic and operand-valid flags.
- `pc`, `rd`, `rs1`, `rs2`, `imm`: extracted from `ROCKET_Channel` in `ROCKET_PerformanceModel::connectChannel()`.
- IF variables: captured in `ROCKET_SchedulingFunction.cpp` after computing `n_Enter`, `n_PC_Gen`, `n_uA_PcCorrect`, `n_uA_CacheBlock`, `n_uA_PcPredict`, `n_ITLB`, `n_ICacheDelay`, `n_ICache`, and optional `n_BPU`.
- External IF values: existing stateful calls to `getPc_mp()`, `getIc_out()`, and `getPc_pt()` are stored once in locals and reused for both formulas and trace recording.
- ID variables: `n_Decoder`, `n_uA_OF_A`, `n_uA_OF_B`, `prev.EX`, and register-ready cycles are captured from the existing operand-read path.
- EX variables: ALU, MUL, DIV, DIVU, EXPass, DTLB, LSUReq, and `prev.MEM` locals are captured after they are computed.
- MEM variables: MEMPass, DCache delay/result, StoreCommit, Branch, FlushMem, and `prev.WB` locals are captured after they are computed.
- WB variables: Reg, CSR, WBPass, and LoadWB locals are captured after they are computed.

## 8. Flag computation

- `icache_miss`: from existing `iCacheModel.getMiss()` after the already-computed `iCacheModel.getDelay()` call.
- `dcache_miss`: from existing `dCacheModel.getMiss()` after the already-computed `dCacheModel.getDelay()` call for load/store formulas.
- `branch_control`: set by branch, `jal`, and `jalr` scheduling functions through existing branch instrumentation.
- `branch_misprediction`: currently defaults to `0`. Reliable row-local misprediction attribution would require delayed row patching or another stateful branch predictor call, so it is intentionally not computed in this conservative pass.

## 9. Default/null fields and limitations

- `assembly` is always `null` in timing CSV for this pass.
- Formula variables not used by an instruction are `null`.
- `branch_misprediction` remains default `0` for conservative behavior.
- Branch redirect cycles remain default `0` for the same reason as branch misprediction.
- This instrumentation is temporary generated-code instrumentation; regenerating Rocket backend files may overwrite it.
- The field list is fixed to the current Rocket generated formula shapes. If CorePerfDSL or generator output changes, the V2 column set should be regenerated or moved into generator-supported trace emission.

## 10. Validation command result

The requested command completed successfully:

```bash
./scripts/run.sh em:ud.riscv ROCKET -ta=.llm_output/correction/test -tp=.llm_output/correction/test
```

Build steps completed before validation:

```bash
cmake --build etiss-perf-sim/etiss/build_dir --target SWEVAL_BACKENDS_LIB
cmake --build etiss-perf-sim/etiss/build_dir --target SoftwareEval
cmake --build etiss-perf-sim/etiss/build_dir --target install
```

`SWEVAL_BACKENDS_LIB`, `SoftwareEval`, and `install` completed successfully.

## 11. Generated trace files inspected

Representative files inspected:

- `.llm_output/correction/test/asm_trace_0000.txt`
- `.llm_output/correction/test/ROCKET_trace_0000.csv`
- `.llm_output/correction/test/ROCKET_timing_0000.csv`

Generated file counts observed after validation:

- `asm_trace_*.txt`: 232 files
- `ROCKET_trace_*.csv`: 41 files
- `ROCKET_timing_*.csv`: 79 files

## 12. Timing CSV validation

For `.llm_output/correction/test/ROCKET_timing_0000.csv`:

- Header fields: 72
- Data rows checked: 52810
- Header and every checked row have matching column counts.
- Required fields are present: `pc,instr,assembly,rd,rs1,rs2,imm,IF,ID,EX,MEM,WB`.
- Representative scheduling columns are present: `IF_n_PC_Gen`, `IF_n_uA_PcCorrect`, `IF_n_uA_CacheBlock`, `IF_n_uA_PcPredict`, `IF_n_ICache`.
- Flags are present: `icache_miss`, `dcache_miss`, `branch_control`, `branch_misprediction`.
- `null` values were observed for variables not used by a row's instruction formula.
- PC alignment is plausible: first timing row PC `2147483648` equals `0x80000000`, matching `asm_trace_0000.txt` and `ROCKET_trace_0000.csv`.

Representative observed rows:

- `addi`: `EX_n_MUL=null`, `EX_n_DIV=null`, `MEM_n_DCache=null`.
- `sd`: `MEM_n_DCache` populated.
- `bge`: `branch_control=1` and branch variables populated.
- `mul`: `EX_n_MUL` populated.
- `div`: `EX_n_DIV` populated.

## 13. Follow-up work

- Move the stable V2 field set into the Rocket generator/CorePerfDSL trace-output flow so regeneration preserves it.
- Add delayed row patching if accurate branch misprediction attribution on the branch row is required.
- Add an optional post-processing join between timing CSV and `asm_trace_*.txt` if a real `assembly` column is required inside timing CSV.
- Consider replacing the `std::unordered_map` sparse trace storage with generated fixed fields if runtime overhead matters for large traces.
