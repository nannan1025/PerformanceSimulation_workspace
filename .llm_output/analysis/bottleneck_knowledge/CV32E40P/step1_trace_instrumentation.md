# CV32E40P Step 1 Trace Identity Instrumentation

## Summary

Implemented Step 1 of CV32E40P bottleneck instrumentation by appending basic instruction identity fields to the existing CV32E40P timing trace output (`CV32E40P_timing_*.csv`). The change is limited to the base `CV32E40P` backend performance model and does not modify `CV32E40P_CORE`, `CV32E40P_LLM`, `CV32E40P_QWEN_1`, monitors, scheduling functions, or external models.

The first validation run after editing source still produced the old timing schema because the installed SoftwareEval plugin had not been rebuilt. After rebuilding the installed ETISS/SoftwareEval plugin and relinking the simulator, the requested validation command produced timing CSV files with the new identity columns.

## Files Modified

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/include/CV32E40P_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_PerformanceModel.cpp`

## Functions Modified

- `CV32E40P::CV32E40P_PerformanceModel::connectChannel(Channel*)`
  - Binds the performance model to existing channel arrays for `typeId`, `rs1`, `rs2`, `rd`, `pc`, `brTarget`, and `rs2_data`.
- `CV32E40P::CV32E40P_PerformanceModel::getPrintHeader()`
  - Appends identity column names to the existing timing CSV header.
- `CV32E40P::CV32E40P_PerformanceModel::getPipelineStream()`
  - Appends per-instruction identity values to each timing row.
  - Uses `instrIndex - 1` because `PerformanceEstimator::execute()` calls `PerformanceModel::update()` before streaming the row.
  - Increments the local `instr_id` once per emitted timing row.

Additional local helper functions were added in `CV32E40P_PerformanceModel.cpp` to suppress stale channel values for fields that are unavailable for a given `type_id`.

## New Fields Added

The timing CSV header is now:

```text
IF_stage,ID_stage,EX_stage,WB_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,rs2_data
```

| Field | Source | Notes |
|---|---|---|
| `instr_id` | New local counter in `CV32E40P_PerformanceModel` | Monotonic per emitted timing row. |
| `type_id` | `Channel::typeId` | Existing instruction type id used by the scheduler and printers. |
| `pc` | `CV32E40P_Channel::pc` | Instruction PC. |
| `rs1` | `CV32E40P_Channel::rs1` | Printed only for type ids that define `rs1`; otherwise `0`. |
| `rs2` | `CV32E40P_Channel::rs2` | Printed only for type ids that define `rs2`; otherwise `0`. |
| `rd` | `CV32E40P_Channel::rd` | Printed only for type ids that define `rd`; otherwise `0`. |
| `brTarget` | `CV32E40P_Channel::brTarget` | Printed only for branch/jump type ids; otherwise `0`. |
| `rs2_data` | `CV32E40P_Channel::rs2_data` | Printed only for divider/remainder type ids; otherwise `0`. |

## Relevant Bottlenecks

- RAW dependency: `instr_id`, `type_id`, `pc`, `rs1`, `rs2`, `rd`.
- Branch/static prediction: `instr_id`, `type_id`, `pc`, `brTarget`.
- Divider latency: `instr_id`, `type_id`, `pc`, `rs1`, `rs2`, `rd`, `rs2_data`.
- Memory-port attribution: `instr_id`, `type_id`, `pc`, `rs1`, `rs2`, `rd`.
- Multiplier attribution: `instr_id`, `type_id`, `pc`, `rs1`, `rs2`, `rd`.

## Test Result

Command run:

```sh
./scripts/run.sh em:crc32 cv32e40p -ta=.llm_output/analysis/bottleneck_knowledge/CV32E40P/test -tp=.llm_output/analysis/bottleneck_knowledge/CV32E40P/test
```

Build/validation steps performed:

1. Ran the requested command after source edits; it completed, but representative `CV32E40P_timing_0000.csv` still had the old four-column header.
2. Rebuilt the installed ETISS/SoftwareEval plugin. The first sandboxed rebuild failed on DNS resolution for the `softfloat` dependency update; rerunning with network approval succeeded.
3. Relinked `etiss-perf-sim/simulator/build/main`.
4. Reran the requested command successfully.
5. Inspected representative files under `.llm_output/analysis/bottleneck_knowledge/CV32E40P/test`.

Representative files found:

- `asm_trace_0000.txt`: present and contains assembly trace rows.
- `CV32E40P_trace_0000.csv`: present and still contains decoded trace-printer fields.
- `CV32E40P_timing_0000.csv`: present and contains the new timing identity fields.

Representative timing output:

```text
IF_stage,ID_stage,EX_stage,WB_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,rs2_data
1,2,3,0,0,10,256,0,0,1,0,0
2,3,4,0,1,10,260,1,0,2,0,0
3,4,5,0,2,10,264,1,0,3,0,0
```

`instr_id` monotonicity check on `CV32E40P_timing_0000.csv` passed for `318256` rows.

An additional branch sample was found in the same representative timing file:

```text
44,45,46,0,43,46,428,26,0,0,444,0
```

This confirms `brTarget` is populated for a branch-like type id and unavailable fields are printed as `0`.

No divider/remainder type id (`25` to `28`) was found in the generated `crc32` timing shards, so `rs2_data` column presence is validated, but runtime nonzero divider data was not exercised by this benchmark.

## Uncertainty

- `instr_id` is emitted by timing-row order in `CV32E40P_PerformanceModel`, not by monitor-side `instrCnt`.
- Unavailable operand fields are represented as `0` in the timing CSV. This avoids stale channel values but means "unavailable" and architectural register/value zero are not distinguishable in Step 1.
- Field availability is gated by the generated CV32E40P instruction-printer type-id layout in `CV32E40P_InstructionPrinters.cpp`; if type ids are regenerated, the helper ranges must be checked.
- This Step 1 change does not compute bottleneck cycles or stall attribution.

## Next Recommended Step

Implement Step 2 instrumentation for computed bottleneck contribution fields:

- RAW wait cycles and blocking source register.
- Branch taken/mispredict/redirect cycles.
- Divider delay cycles from the divider models.
- Memory-port wait cycles for load/store paths.
- Multiplier/high-multiplier delay cycles.
