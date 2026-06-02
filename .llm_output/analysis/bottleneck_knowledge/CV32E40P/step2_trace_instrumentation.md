# CV32E40P Step 2 Trace Instrumentation

## Summary

Implemented Step 2 of CV32E40P bottleneck instrumentation by adding divider and multiplier delay fields to the existing base `CV32E40P_timing_*.csv` timing trace output.

The Step 2 fields now use extra-cycle attribution semantics: `divider_delay_cycles` and `multiplier_delay_cycles` mean extra execution cycles beyond a normal 1-cycle execution baseline. The actual modeled pipeline timing still uses the full functional-unit latency.

This change is limited to the base `CV32E40P` backend. It does not modify `CV32E40P_CORE`, `CV32E40P_LLM`, `CV32E40P_QWEN_1`, monitors, branch instrumentation, RAW instrumentation, memory-port instrumentation, or external model code.

## Files Modified

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/include/CV32E40P_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_PerformanceModel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_SchedulingFunction.cpp`

## Functions Modified

- `CV32E40P::CV32E40P_PerformanceModel::getPrintHeader()`
  - Appends `divider_delay_cycles` and `multiplier_delay_cycles`.
- `CV32E40P::CV32E40P_PerformanceModel::getPipelineStream()`
  - Emits the new per-row delay fields after the Step 1 identity fields.
  - Resets both delay fields to `0` after each emitted row.
- `CV32E40P::CV32E40P_PerformanceModel::setDividerDelay(uint64_t)`
  - New inline setter for the current row's divider delay.
- `CV32E40P::CV32E40P_PerformanceModel::setMultiplierDelay(uint64_t)`
  - New inline setter for the current row's multiplier delay.
- `schedulingFunction_mul`
  - Keeps `n_MUL = n_ID_stage + 1` and sets `multiplier_delay_cycles = 0`.
- `schedulingFunction_mulh`
  - Keeps `n_MULH = n_ID_stage + 5` and sets `multiplier_delay_cycles = 4`.
- `schedulingFunction_mulhu`
  - Keeps `n_MULH = n_ID_stage + 5` and sets `multiplier_delay_cycles = 4`.
- `schedulingFunction_mulhsu`
  - Keeps `n_MULH = n_ID_stage + 5` and sets `multiplier_delay_cycles = 4`.
- `schedulingFunction_div`
  - Stores `DividerModel::getDelay()` in a local `divDelay`, uses it for timing, and emits `max(0, divDelay - 1)`.
- `schedulingFunction_rem`
  - Stores `DividerModel::getDelay()` in a local `divDelay`, uses it for timing, and emits `max(0, divDelay - 1)`.
- `schedulingFunction_divu`
  - Stores `DividerUnsignedModel::getDelay()` in a local `divDelay`, uses it for timing, and emits `max(0, divDelay - 1)`.
- `schedulingFunction_remu`
  - Stores `DividerUnsignedModel::getDelay()` in a local `divDelay`, uses it for timing, and emits `max(0, divDelay - 1)`.

## New Fields Added

The timing CSV header is now:

```text
IF_stage,ID_stage,EX_stage,WB_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,rs2_data,divider_delay_cycles,multiplier_delay_cycles
```

| Field | Source | Notes |
|---|---|---|
| `divider_delay_cycles` | `max(0, cv32e40p::DividerModel::getDelay() - 1)` for `div/rem`; `max(0, cv32e40p::DividerUnsignedModel::getDelay() - 1)` for `divu/remu` | Emits extra divider execution cycles beyond a normal 1-cycle baseline for type ids `25` to `28`; otherwise `0`. |
| `multiplier_delay_cycles` | Static CV32E40P scheduling constants in `CV32E40P_SchedulingFunction.cpp` minus the normal 1-cycle baseline | Emits `0` for `mul` type id `21`; emits `4` for `mulh/mulhu/mulhsu` type ids `22` to `24`; otherwise `0`. |

## Relevant Bottleneck

- Divider latency bottleneck:
  - type ids `25` (`div`), `26` (`rem`), `27` (`divu`), `28` (`remu`)
  - field: `divider_delay_cycles`
- Multiplier latency bottleneck:
  - type id `21` (`mul`)
  - type ids `22` to `24` (`mulh`, `mulhu`, `mulhsu`)
  - field: `multiplier_delay_cycles`

These fields represent modeled functional-unit latency. They do not yet represent full bottleneck contribution, because RAW wait, branch redirect, memory-port wait, and structural overlap attribution are still not instrumented.

## Test Result

Build commands run:

```sh
cmake --build etiss-perf-sim/etiss/build_dir --target install -- -j2
cmake --build etiss-perf-sim/simulator/build -- -j2
```

Validation command run:

```sh
./scripts/run.sh em:ud cv32e40p -ta=.llm_output/analysis/bottleneck_knowledge/CV32E40P/test -tp=.llm_output/analysis/bottleneck_knowledge/CV32E40P/test
```

The run completed successfully after the extra-cycle attribution update:

- Number of instructions: `923462`
- Estimated processor cycles: `2036105`
- Estimated CPI: `2.20486`

Representative files found under `.llm_output/analysis/bottleneck_knowledge/CV32E40P/test`:

- `asm_trace_0000.txt`: present and contains assembly trace rows.
- `CV32E40P_trace_0000.csv`: present and still contains decoded instruction trace fields.
- `CV32E40P_timing_0000.csv`: present and contains the Step 1 identity fields plus the new Step 2 delay fields.

Representative timing CSV header and first row:

```text
IF_stage,ID_stage,EX_stage,WB_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,rs2_data,divider_delay_cycles,multiplier_delay_cycles
1,2,3,0,0,10,256,0,0,1,0,0,0,0
```

Representative divider row:

```text
2685,2687,2719,2687,2143,25,908,10,8,10,0,4,31,0,1,1,1,1,8,2687,0,0,0,0,0,none
```

This row is type id `25` (`div`). The full modeled divider latency is still used for timing, but `divider_delay_cycles = 31`, representing `DividerModel::getDelay() - 1`.

Representative multiplier row:

```text
2866,2867,2868,2868,2164,21,992,8,9,8,0,0,0,0,1,1,1,0,-1,0,0,0,0,0,0,none
```

This row is type id `21` (`mul`) with `multiplier_delay_cycles = 0`, because the single MUL execution cycle is treated as the normal baseline rather than extra delay.

Observed type-id coverage in the `em:ud` timing shards:

| Type id | Instruction | Rows | Observed emitted delay values |
|---:|---|---:|---:|
| 21 | `mul` | 125630 | `multiplier_delay_cycles = 0` |
| 22 | `mulh` | 0 | Not covered by `em:ud` |
| 23 | `mulhu` | 0 | Not covered by `em:ud` |
| 24 | `mulhsu` | 0 | Not covered by `em:ud` |
| 25 | `div` | 31038 | `divider_delay_cycles = 29`, `30`, or `31` |
| 26 | `rem` | 0 | Not covered by `em:ud` |
| 27 | `divu` | 0 | Not covered by `em:ud` |
| 28 | `remu` | 0 | Not covered by `em:ud` |

## Uncertainty

- `em:ud` exercised `mul` and signed `div`, but did not exercise `mulh`, `mulhu`, `mulhsu`, `rem`, `divu`, or `remu` in the observed timing shards.
- The changed scheduler file is generated code and may be overwritten by future CorePerfDSL/code-generation runs.
- `divider_delay_cycles` and `multiplier_delay_cycles` are extra-cycle attribution values beyond a normal 1-cycle execution baseline, not full bottleneck contribution. They do not subtract overlap or account for RAW, branch, memory-port, or downstream structural waits.

## Next Recommended Step

Implement the remaining attribution fields from the instrumentation plan:

- RAW wait cycles and blocking source register.
- Branch taken/mispredict/redirect cycles.
- Memory-port wait cycles for load/store paths.
- Later, add contribution formulas that separate functional-unit latency from overlapped timing.
