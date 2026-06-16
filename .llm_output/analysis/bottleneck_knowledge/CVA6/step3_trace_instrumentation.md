# CVA6 Step 3 Trace Instrumentation: I-Cache Delay Fields

## Summary

Implemented I-cache/frontend delay instrumentation for the base `CVA6` backend timing trace. This step preserves Step 1 identity/operand fields and Step 2 divider fields, then appends:

```text
icache_miss,icache_delay_cycles,icache_extra_cycles,frontend_wait_cycles,frontend_extra_cycles,frontend_wait_type
```

This is attribution-only instrumentation. The existing I-cache delay is still used in the same scheduling equation for `n_ICache`, and `ICacheModel` behavior was not changed.

No `CVA62`, `CVA6_QWEN_1`, monitor, branch, RAW, D-cache, divider, or external I-cache model code was modified.

## Files Modified

| File | Purpose |
|---|---|
| `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/include/CVA6_PerformanceModel.h` | Added per-row I-cache/frontend fields and setter declaration. |
| `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_PerformanceModel.cpp` | Implemented setter, CSV header emission, CSV row emission, and per-row reset. |
| `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CVA6/src/CVA6_SchedulingFunction.cpp` | Captured I-cache model delay once per scheduler row and sent it to the performance model setter. |

## Functions Modified

- `CVA6_PerformanceModel::setICacheInstrumentation`
- `CVA6_PerformanceModel::getPrintHeader`
- `CVA6_PerformanceModel::getPipelineStream`
- All base CVA6 scheduling lambdas with the frontend `ICache` block.

## New Fields Added

| Field | Source | Meaning |
|---|---|---|
| `icache_miss` | `ICacheModel::getInfo_miss()` read after the normal `getDelay()` call | Current model miss flag. |
| `icache_delay_cycles` | Local `iDelay = ICacheModel::getDelay()` | Raw I-cache model delay used by `n_ICache`. |
| `icache_extra_cycles` | `iDelay > 0 ? iDelay - 1 : 0` | Extra delay beyond a normal 1-cycle cache-hit baseline. |
| `frontend_wait_cycles` | Max of existing PC correction, cache-block, and IF-capacity wait candidates | Conservative frontend blocking proxy. |
| `frontend_extra_cycles` | `frontend_wait_cycles > 0 ? frontend_wait_cycles - 1 : 0` | Extra frontend blocking beyond one normal frontend cycle. |
| `frontend_wait_type` | Winner of `max(pcCorrectWait, cacheBlockWait, ifCapacityWait)` | Source of the max frontend wait: `pcCorrectWait`, `cacheBlockWait`, `ifCapacityWait`, or `none`. Ties use this priority order. |

## Implementation Detail

The generated frontend scheduler block previously used:

```cpp
n_ICache = n_IF_substage_0 + perfModel->iCacheModel.getDelay();
```

It now captures the delay once:

```cpp
uint64_t iDelay = perfModel->iCacheModel.getDelay();
n_ICache = n_IF_substage_0 + iDelay;
uint64_t pcCorrectWait = n_uA_PcCorrect > n_Enter ? n_uA_PcCorrect - n_Enter : 0;
uint64_t cacheBlockWait = n_uA_CacheBlock > n_Enter ? n_uA_CacheBlock - n_Enter : 0;
uint64_t ifCapacityWait = perfModel->IF_stage.get(3) > n_PCGen ? perfModel->IF_stage.get(3) - n_PCGen : 0;
uint64_t frontendWait = std::max({pcCorrectWait, cacheBlockWait, ifCapacityWait});
std::string frontendWaitType = "none";
if(frontendWait > 0)
{
  frontendWaitType = pcCorrectWait == frontendWait ? "pcCorrectWait" : (cacheBlockWait == frontendWait ? "cacheBlockWait" : "ifCapacityWait");
}
perfModel->setICacheInstrumentation(perfModel->iCacheModel.getInfo_miss() == "1", iDelay, frontendWait, frontendWaitType);
```

The original `perfModel->iCacheModel.setIc_in(n_ICache);` call remains unchanged.

## Relevant Bottleneck

- `CVA6-BN-001`: I-cache miss and PC/fetch blocking.

Step 3 separates:

- raw/model I-cache latency: `icache_delay_cycles`
- extra delay above the 1-cycle hit baseline: `icache_extra_cycles`
- visible frontend blocking proxy: `frontend_wait_cycles`
- visible frontend extra blocking proxy: `frontend_extra_cycles`
- frontend blocking source label: `frontend_wait_type`

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

The estimated cycle count matches the Step 1 and Step 2 validation runs, so this attribution-only change did not visibly alter scheduling behavior for this test.

## Representative Output Files

Representative files under `.llm_output/analysis/bottleneck_knowledge/CVA6/test`:

- `asm_trace_0000.txt`
- `CVA6_trace_0000.csv`
- `CVA6_timing_0000.csv`

The assembly trace and decoded trace remain readable. The timing CSV now has the Step 3 I-cache/frontend fields.

Representative timing header:

```text
PC_stage,IF_stage,IQ_stage,ID_stage,IS_stage,EX_stage,COM_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,imm,rs1_data,rs2_data,addr,uses_rs1,uses_rs2,uses_rd,divider_delay_cycles,divider_extra_cycles,icache_miss,icache_delay_cycles,icache_extra_cycles,frontend_wait_cycles,frontend_extra_cycles,frontend_wait_type
```

Representative first timing rows:

```text
1,8,9,10,10,11,12,0,18,65536,0,0,8,0,0,0,0,0,1,0,1,0,0,1,5,4,0,0
7,14,15,16,16,17,18,1,12,65540,8,0,8,0,0,0,0,0,1,0,1,0,0,0,5,4,6,5
```

Representative I-cache rows, shown as:

```text
PC_stage,IF_stage,IQ_stage,ID_stage,instr_id,type_id,pc,icache_miss,icache_delay_cycles,icache_extra_cycles,frontend_wait_cycles,frontend_extra_cycles,frontend_wait_type
```

```text
1,8,9,10,0,18,65536,1,5,4,0,0
7,14,15,16,1,12,65540,0,5,4,6,5
8,19,20,21,2,16,65544,0,5,4,0,0
18,29,30,31,4,6,65552,1,5,4,0,0
38,45,46,47,6,6,2147483648,1,5,4,10,9
```

## Aggregate Validation Checks

| Check | Result |
|---|---:|
| Timing files scanned | `10` |
| Timing rows scanned | `1384912` |
| Rows with nonzero `icache_delay_cycles` | `1384912` |
| `icache_delay_cycles` distribution | `{5: 785, 1: 1384127}` |
| Rows with `icache_miss=1` | `781` |
| Rows where `icache_delay_cycles > 1` but `icache_extra_cycles != icache_delay_cycles - 1` | `0` |
| Rows where `icache_delay_cycles == 1` but `icache_extra_cycles != 0` | `0` |
| Rows with nonzero `frontend_wait_cycles` | `119217` |
| Maximum observed `frontend_wait_cycles` | `25` |
| Rows where `frontend_wait_cycles > 0` but `frontend_extra_cycles != frontend_wait_cycles - 1` | `0` |

## Uncertainty

- `icache_miss` comes from the existing `ICacheModel::isMiss` state. Non-cacheable accesses can also return the 5-cycle memory delay, so a row may show `icache_delay_cycles=5` with `icache_miss=0`.
- `frontend_wait_cycles` is a max-of-candidates proxy for how long the next instruction is blocked from entering/progressing through the frontend path; `frontend_extra_cycles` removes one normal frontend cycle from that proxy.
- `frontend_wait_type=pcCorrectWait` uses the same scheduler-side source as the corrected Step 5 `branch_redirect_cycles`. Other frontend wait rows can be from cache-block or IF-capacity waits.
- Step 3 does not distinguish I-cache miss delay from branch redirection, IF queue capacity, or cache-block waits beyond the proxy field.
- The scheduler file is generated-style code and may be overwritten by future CorePerfDSL/code-generation runs.

## Next Recommended Step

Add D-cache/memory delay instrumentation or branch prediction instrumentation next, continuing to separate raw/model latency from extra delay beyond a normal 1-cycle baseline.
