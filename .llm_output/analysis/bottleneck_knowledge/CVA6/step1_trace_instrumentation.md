# CVA6 Step 1 Trace Instrumentation: Identity And Operand Fields

## Summary

Implemented Step 1 of CVA6 bottleneck instrumentation by appending basic instruction identity and operand fields to the base `CVA6_timing_*.csv` timing trace.

This step changes timing-trace observability only. It does not compute RAW, branch, cache, divider, resource, clobber, commit, or memory bottleneck delays. It does not modify CVA62, CVA6_QWEN_1, monitors, external models, branch prediction behavior, cache models, divider models, or scheduling behavior.

Important accounting note for later steps: future CVA6 delay fields should distinguish raw/model latency from extra delay beyond the normal 1-cycle base latency. Step 1 does not compute delay fields.

## Files Modified

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/include/CVA6_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_PerformanceModel.cpp`

## Functions Modified

- `CVA6::CVA6_PerformanceModel::connectChannel`
- `CVA6::CVA6_PerformanceModel::getPipelineStream`
- `CVA6::CVA6_PerformanceModel::getPrintHeader`

Helper functions added in `CVA6_PerformanceModel.cpp`:

- `has_rs1(uint64_t typeId)`
- `has_rs2(uint64_t typeId)`
- `has_rd(uint64_t typeId)`
- `has_brTarget(uint64_t typeId)`
- `has_imm(uint64_t typeId)`
- `has_rs1_data(uint64_t typeId)`
- `has_rs2_data(uint64_t typeId)`
- `has_addr(uint64_t typeId)`

## New Fields Added

The existing timing columns remain first:

```text
PC_stage,IF_stage,IQ_stage,ID_stage,IS_stage,EX_stage,COM_stage
```

Step 1 appends:

```text
instr_id,type_id,pc,rs1,rs2,rd,brTarget,imm,rs1_data,rs2_data,addr,uses_rs1,uses_rs2,uses_rd
```

Full validated header:

```text
PC_stage,IF_stage,IQ_stage,ID_stage,IS_stage,EX_stage,COM_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,imm,rs1_data,rs2_data,addr,uses_rs1,uses_rs2,uses_rd
```

## Source Of Each Field

| Field | Source |
|---|---|
| `instr_id` | New monotonically increasing counter in `CVA6_PerformanceModel`; increments once per emitted timing row. |
| `type_id` | Base `Channel::typeId`. |
| `pc` | `CVA6_Channel::pc`. |
| `rs1` | `CVA6_Channel::rs1`, emitted only when `has_rs1(type_id)` is true. |
| `rs2` | `CVA6_Channel::rs2`, emitted only when `has_rs2(type_id)` is true. |
| `rd` | `CVA6_Channel::rd`, emitted only when `has_rd(type_id)` is true. |
| `brTarget` | `CVA6_Channel::brTarget`, emitted for branch/jump rows. |
| `imm` | `CVA6_Channel::imm`, emitted for branch/jump rows. |
| `rs1_data` | `CVA6_Channel::rs1_data`, emitted for divider rows. |
| `rs2_data` | `CVA6_Channel::rs2_data`, emitted for divider rows. |
| `addr` | `CVA6_Channel::addr`, emitted for load/store rows. |
| `uses_rs1` | Type-id availability helper. |
| `uses_rs2` | Type-id availability helper. |
| `uses_rd` | Type-id availability helper. |

Unavailable operands print as `0`; `uses_rs1`, `uses_rs2`, and `uses_rd` disambiguate unavailable operands from real zero-valued registers.

## Relevant Bottlenecks Supported

Step 1 provides the identity and operand context needed by later instrumentation for:

- `CVA6-BN-001`: I-cache/fetch attribution via `pc`.
- `CVA6-BN-002`: branch attribution via `type_id`, `pc`, `brTarget`, `imm`, `rs1`, `rs2`.
- `CVA6-BN-003`: RAW attribution via `rs1`, `rs2`, `rd`, `uses_rs1`, `uses_rs2`, `uses_rd`.
- `CVA6-BN-004`: clobber/commit attribution via `rd` and `uses_rd`.
- `CVA6-BN-005`: D-cache/load-store attribution via `addr`, `rs1`, `rd`.
- `CVA6-BN-006`: EX resource attribution via `type_id` and instruction identity.
- `CVA6-BN-007`: divider attribution via `rs1_data`, `rs2_data`, `rs1`, `rs2`, `rd`.

## Validation Command And Result

Build commands run:

```sh
cmake --build etiss-perf-sim/etiss/build_dir --target install -- -j2
cmake --build etiss-perf-sim/simulator/build -- -j2
```

Validation command run:

```sh
./scripts/run.sh em:ud cva6 -ta=.llm_output/analysis/bottleneck_knowledge/CVA6/test -tp=.llm_output/analysis/bottleneck_knowledge/CVA6/test
```

The run completed successfully:

- Number of instructions: `1384912`
- Estimated processor cycles: `2129817`
- Estimated CPI: `1.53787`

Representative files found under `.llm_output/analysis/bottleneck_knowledge/CVA6/test`:

- `asm_*.txt`: `89` files
- `CVA6_timing_*.csv`: `9` files
- `CVA6_trace_*.csv`: `16` files

Representative `asm_trace_0000.txt` starts with readable assembly rows:

```text
pc         ; assembly   ;
0x00010000 ; addiw # 0x0010041b [rd=8 | rs1=0 | imm=1]          ;
```

Representative `CVA6_trace_0000.csv` is present and contains decoded trace fields such as `rs1`, `rs2`, `rd`, `pc`, `brTarget`, `imm`, `rs1_data`, `rs2_data`, and `addr`.

## Representative Timing Rows

Header and first rows from `CVA6_timing_0000.csv`:

```text
PC_stage,IF_stage,IQ_stage,ID_stage,IS_stage,EX_stage,COM_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,imm,rs1_data,rs2_data,addr,uses_rs1,uses_rs2,uses_rd
1,8,9,10,10,11,12,0,18,65536,0,0,8,0,0,0,0,0,1,0,1
7,14,15,16,16,17,18,1,12,65540,8,0,8,0,0,0,0,0,1,0,1
```

Representative branch row:

```text
214,217,218,219,220,221,222,82,37,2147484076,26,0,0,2147484092,16,0,0,0,1,1,0
```

Representative load row:

```text
286,289,290,291,291,300,301,104,60,2147493708,8,0,15,0,0,0,0,2684354560,1,0,1
```

Representative divider row:

```text
5466,5473,5474,5475,5478,5480,5481,2326,47,2147484576,10,28,10,0,0,3,4,0,1,1,1
```

Representative multiply row:

```text
5571,5574,5575,5576,5576,5578,5579,2367,42,2147484740,6,28,6,0,0,0,0,0,1,1,1
```

## Aggregate Checks

Across generated `CVA6_timing_*.csv` files:

| Check | Result |
|---|---:|
| Timing rows | `1384912` |
| Header matches expected Step 1 schema | yes |
| Rows with non-empty `instr_id`, `type_id`, and `pc` | `1384912` |
| `instr_id` monotonicity violations | `0` |
| Rows with `uses_rs1 = 1` | `1301860` |
| Rows with `uses_rs2 = 1` | `697854` |
| Rows with `uses_rd = 1` | `1133593` |

## Uncertainty

- `instr_id` is emitted by performance-model timing row order, not by an externally validated monitor instruction count field.
- Type-id availability helpers are derived from generated `CVA6_InstructionPrinters.cpp` and CorePerfDSL instruction groups. Future code generation may change type IDs.
- Generated backend files may be overwritten by future CorePerfDSL/code-generation runs.
- Step 1 does not compute actual bottleneck contribution or any delay fields.

## Next Recommended Step

Implement Step 2 mechanism fields for the least ambiguous CVA6 delays first, preferably divider and cache delay fields. For later delay fields, keep separate semantics for raw/model latency and extra delay beyond the normal 1-cycle execution baseline.
