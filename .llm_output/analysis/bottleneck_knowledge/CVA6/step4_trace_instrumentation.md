# CVA6 Step 4 Trace Instrumentation: D-Cache Delay Fields

## Summary

Implemented D-cache/load memory delay instrumentation for the base `CVA6` backend timing trace. This step preserves Step 1 identity/operand fields, Step 2 divider fields, and Step 3 I-cache/frontend fields, then appends:

```text
dcache_miss,dcache_not_cacheable,dcache_delay_cycles,dcache_extra_cycles,memory_wait_cycles
```

This is attribution-only instrumentation. The existing D-cache delay is still used in the same scheduling equation for `n_DCache`, and `DCacheModel` behavior was not changed.

No `CVA62`, `CVA6_QWEN_1`, monitor, branch, RAW, I-cache, divider, or external D-cache model code was modified. Store rows are not instrumented as D-cache delay rows because the current CVA6 generated store path has `SCtrl -> SUnit` and no `DCache` stage.

## Files Modified

| File | Purpose |
|---|---|
| `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/include/CVA6_PerformanceModel.h` | Added per-row D-cache/memory fields, setter declaration, and cacheability helper declaration. |
| `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_PerformanceModel.cpp` | Implemented setter/helper, CSV header emission, CSV row emission, and per-row reset. |
| `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_SchedulingFunction.cpp` | Captured D-cache model delay once in load scheduler lambdas and sent it to the performance model setter. |

## Functions Modified

- `CVA6_PerformanceModel::setDCacheInstrumentation`
- `CVA6_PerformanceModel::isDCacheAddressNotCacheable`
- `CVA6_PerformanceModel::getPrintHeader`
- `CVA6_PerformanceModel::getPipelineStream`
- Load scheduler lambdas: `lw`, `lh`, `lhu`, `lb`, `lbu`, `ld`, `lwu`

## New Fields Added

| Field | Source | Meaning |
|---|---|---|
| `dcache_miss` | `DCacheModel::getInfo_miss()` read after the normal `getDelay()` call | Current model miss flag; non-cacheable accesses also set this flag in the current model. |
| `dcache_not_cacheable` | Backend helper using the same range as `DCacheModel`: not in `0x80000000..0xC0000000` | Whether the load address is outside the modeled cacheable range. |
| `dcache_delay_cycles` | Local `dDelay = DCacheModel::getDelay()` | Raw D-cache model delay used by `n_DCache`. |
| `dcache_extra_cycles` | `dDelay > 0 ? dDelay - 1 : 0` | Extra delay beyond a normal 1-cycle D-cache hit baseline. |
| `memory_wait_cycles` | Equal to `dcache_extra_cycles` for Step 4 | Contribution-style memory wait proxy for load D-cache delay. |

## Implementation Detail

The generated load scheduler block previously used:

```cpp
n_DCache = n_EX_substage_lCtrl + perfModel->dCacheModel.getDelay();
```

It now captures the delay once:

```cpp
uint64_t dDelay = perfModel->dCacheModel.getDelay();
n_DCache = n_EX_substage_lCtrl + dDelay;
perfModel->setDCacheInstrumentation(
  perfModel->dCacheModel.getInfo_miss() == "1",
  perfModel->isDCacheAddressNotCacheable(),
  dDelay
);
```

The `n_DCache` timing equation is otherwise unchanged. `getDelay()` is still called once per load row.

## Relevant Bottleneck

- `CVA6-BN-005`: D-cache miss / non-cacheable memory delay.

Step 4 separates:

- raw/model D-cache latency: `dcache_delay_cycles`
- extra delay above the 1-cycle hit baseline: `dcache_extra_cycles`
- memory wait proxy for contribution summaries: `memory_wait_cycles`
- non-cacheable access identification: `dcache_not_cacheable`

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

The estimated cycle count matches the Step 1-3 validation runs, so this attribution-only change did not visibly alter scheduling behavior for this test.

## Representative Output Files

Representative files under `.llm_output/analysis/bottleneck_knowledge/CVA6/test`:

- `asm_trace_0000.txt`
- `CVA6_trace_0000.csv`
- `CVA6_timing_0000.csv`

The assembly trace and decoded trace remain readable. The timing CSV now has the Step 4 D-cache/memory fields.

Representative timing header:

```text
PC_stage,IF_stage,IQ_stage,ID_stage,IS_stage,EX_stage,COM_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,imm,rs1_data,rs2_data,addr,uses_rs1,uses_rs2,uses_rd,divider_delay_cycles,divider_extra_cycles,icache_miss,icache_delay_cycles,icache_extra_cycles,frontend_wait_cycles,frontend_extra_cycles,dcache_miss,dcache_not_cacheable,dcache_delay_cycles,dcache_extra_cycles,memory_wait_cycles
```

Representative first timing rows:

```text
1,8,9,10,10,11,12,0,18,65536,0,0,8,0,0,0,0,0,1,0,1,0,0,1,5,4,0,0,0,0,0,0,0
7,14,15,16,16,17,18,1,12,65540,8,0,8,0,0,0,0,0,1,0,1,0,0,0,5,4,6,5,0,0,0,0,0
```

Representative load rows, shown as:

```text
PC_stage,IF_stage,IS_stage,EX_stage,COM_stage,instr_id,type_id,pc,addr,dcache_miss,dcache_not_cacheable,dcache_delay_cycles,dcache_extra_cycles,memory_wait_cycles
```

```text
286,289,291,300,301,104,60,2147493708,2684354560,1,0,7,6,6
330,337,339,348,349,113,60,2147493728,3221225464,1,0,7,6,6
336,339,341,349,350,114,60,2147493732,3221225456,0,0,1,0,0
337,340,347,356,357,115,60,2147493736,3221225448,1,0,7,6,6
338,341,348,357,358,116,60,2147493740,3221225440,0,0,1,0,0
```

## Aggregate Validation Checks

| Check | Result |
|---|---:|
| Timing files scanned | `11` |
| Timing rows scanned | `1384912` |
| Load rows with `type_id` in `55-61` | `299431` |
| Load rows with nonzero `dcache_delay_cycles` | `299431` |
| Non-load rows with nonzero D-cache fields | `0` |
| `dcache_delay_cycles` distribution | `{0: 1085481, 1: 299260, 7: 170, 9: 1}` |
| Rows with `dcache_miss=1` | `171` |
| Rows with `dcache_not_cacheable=1` | `1` |
| Rows where `dcache_extra_cycles != max(0, dcache_delay_cycles - 1)` | `0` |
| Rows where `memory_wait_cycles != dcache_extra_cycles` | `0` |

## Uncertainty

- `dcache_miss` uses the existing `DCacheModel::isMiss` flag. In the current model, non-cacheable accesses also set this flag.
- `dcache_not_cacheable` is computed in the backend using the same address range as the model. This avoids changing external model behavior, but duplicates the cacheability rule.
- Store rows are not assigned D-cache delay because the generated store path does not call `DCacheModel::getDelay()`.
- `memory_wait_cycles` is a per-load D-cache delay proxy, not a de-overlapped memory CPI contribution.
- The scheduler file is generated-style code and may be overwritten by future CorePerfDSL/code-generation runs.

## Next Recommended Step

Add branch prediction/redirect instrumentation or RAW/clobber wait instrumentation next, continuing to separate raw/model latency from extra delay beyond a normal 1-cycle baseline.
