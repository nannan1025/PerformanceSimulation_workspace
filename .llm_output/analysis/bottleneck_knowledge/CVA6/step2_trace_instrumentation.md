# CVA6 Step 2 Trace Instrumentation: Divider Delay Fields

## Summary

Implemented divider delay instrumentation for the base `CVA6` backend timing trace. This step preserves the Step 1 identity and operand fields and adds only:

```text
divider_delay_cycles,divider_extra_cycles
```

This is attribution-only instrumentation. The scheduler still uses the same raw divider model delay for `n_DIV` and `n_DIVU`, so simulator timing behavior is intended to remain unchanged.

No `CVA62`, `CVA6_QWEN_1`, monitor, external divider model, branch, cache, RAW, clobber, commit, or analyzer code was modified.

## Files Modified

| File | Purpose |
|---|---|
| `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/include/CVA6_PerformanceModel.h` | Added per-row divider fields and setter declaration. |
| `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_PerformanceModel.cpp` | Implemented setter, CSV header emission, CSV row emission, and per-row reset. |
| `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_SchedulingFunction.cpp` | Captured divider model delay once in divider scheduler lambdas and sent it to the performance model setter. |

## Functions Modified

- `CVA6_PerformanceModel::setDividerInstrumentation`
- `CVA6_PerformanceModel::getPrintHeader`
- `CVA6_PerformanceModel::getPipelineStream`
- `schedulingFunction_div`
- `schedulingFunction_rem`
- `schedulingFunction_divw`
- `schedulingFunction_remw`
- `schedulingFunction_divu`
- `schedulingFunction_remu`
- `schedulingFunction_divuw`
- `schedulingFunction_remuw`

## New Fields Added

| Field | Source | Meaning |
|---|---|---|
| `divider_delay_cycles` | `DividerModel::getDelay()` or `DividerUnsignedModel::getDelay()` | Raw modeled divider latency used by the scheduler. |
| `divider_extra_cycles` | `divider_delay_cycles > 0 ? divider_delay_cycles - 1 : 0` | Extra divider delay beyond a normal 1-cycle execution baseline. |

For non-divider rows, both fields are reset to `0` after each emitted timing row.

## Implementation Detail

The generated divider scheduler paths previously used direct delay calls:

```cpp
n_DIV = n_IS_stage + perfModel->divider.getDelay();
n_DIVU = n_IS_stage + perfModel->divider_u.getDelay();
```

They now capture the delay once:

```cpp
uint64_t divDelay = perfModel->divider.getDelay();
n_DIV = n_IS_stage + divDelay;
perfModel->setDividerInstrumentation(divDelay);
```

and for unsigned division:

```cpp
uint64_t divDelay = perfModel->divider_u.getDelay();
n_DIVU = n_IS_stage + divDelay;
perfModel->setDividerInstrumentation(divDelay);
```

This avoids double-calling `getDelay()` and keeps the stage timing formula identical.

## Relevant Bottleneck

- `CVA6-BN-007`: variable 64-bit divider latency.

Step 2 supports later runtime attribution by separating:

- raw/model divider latency: `divider_delay_cycles`
- extra delay beyond baseline execution: `divider_extra_cycles`

The extra-cycle field should be used for contribution-style summaries, because it avoids counting the normal 1-cycle execution slot as bottleneck delay.

## Validation Command

Rebuild commands:

```sh
cmake --build etiss-perf-sim/etiss/build_dir --target install -- -j2
cmake --build etiss-perf-sim/simulator/build -- -j2
```

Run command:

```sh
./scripts/run.sh em:ud cva6 -ta=.llm_output/analysis/bottleneck_knowledge/CVA6/test -tp=.llm_output/analysis/bottleneck_knowledge/CVA6/test
```

Run result:

```text
Number of instructions: 1384912
Estimated number of processor cycles: 2129817
Estimated average number of processor cycles per instruction: 1.53787
```

The estimated cycle count matches the Step 1 validation run, so this attribution-only change did not visibly alter scheduling behavior for this test.

## Representative Output Files

Representative files found under `.llm_output/analysis/bottleneck_knowledge/CVA6/test`:

- `asm_trace_0000.txt`
- `CVA6_trace_0000.csv`
- `CVA6_timing_0000.csv`

The assembly trace and decoded trace remain readable. The timing CSV now has the Step 2 columns.

Representative timing header:

```text
PC_stage,IF_stage,IQ_stage,ID_stage,IS_stage,EX_stage,COM_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,imm,rs1_data,rs2_data,addr,uses_rs1,uses_rs2,uses_rd,divider_delay_cycles,divider_extra_cycles
```

Representative non-divider rows:

```text
1,8,9,10,10,11,12,0,18,65536,0,0,8,0,0,0,0,0,1,0,1,0,0
7,14,15,16,16,17,18,1,12,65540,8,0,8,0,0,0,0,0,1,0,1,0,0
```

Representative divider rows, shown as:

```text
PC_stage,IF_stage,IQ_stage,ID_stage,IS_stage,EX_stage,COM_stage,instr_id,type_id,pc,rs1_data,rs2_data,divider_delay_cycles,divider_extra_cycles
```

```text
5466,5473,5474,5475,5478,5480,5481,2326,47,2147484576,3,4,2,1
5490,5493,5494,5495,5499,5502,5503,2335,47,2147484612,4,4,3,2
5510,5513,5514,5515,5521,5524,5525,2345,47,2147484652,5,4,3,2
5529,5536,5537,5538,5542,5545,5546,2354,47,2147484688,6,4,3,2
```

## Aggregate Validation Checks

| Check | Result |
|---|---:|
| Timing files scanned | `9` |
| Timing rows scanned | `1384912` |
| Divider rows with `type_id` in `47-54` | `31038` |
| Divider row type IDs observed in `em:ud` | `{47: 31038}` |
| Maximum observed `divider_delay_cycles` | `4` |
| Divider rows where `divider_extra_cycles != max(0, divider_delay_cycles - 1)` | `0` |
| Non-divider rows with nonzero divider fields | `0` |

## Uncertainty

- The `em:ud` validation run exercised only signed `div` rows with `type_id=47`; it did not activate `rem`, `divw`, `remw`, or unsigned divider rows in this trace.
- `divw/remw/divuw/remuw` still use the same existing generated 64-bit divider model path. This report records that current model behavior rather than judging whether it is architecturally ideal.
- The scheduler file is generated-style code and may be overwritten by future CorePerfDSL/code-generation runs.
- Divider delay can overlap with later RAW, clobber, commit, or EX resource waits. Step 2 does not compute a de-overlapped CPI contribution.

## Next Recommended Step

Add the next least-ambiguous CVA6 mechanism fields, preferably I-cache or D-cache delay fields, while keeping raw/model latency separate from extra delay beyond the normal 1-cycle baseline.
