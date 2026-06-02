# CV32E40P Step 4 Trace Instrumentation: Branch / Control Flow

## Summary

Implemented Step 4 branch/control-flow trace fields for the base CV32E40P timing trace, then updated the redirect-cycle attribution formula so it is derived from printed pipeline stage columns.

The static branch predictor behavior was not changed. Conditional branches still use the actual runtime branch condition from the monitor, while misprediction remains modeled as static predict-not-taken: taken conditional branches are mispredicted, not-taken conditional branches are not mispredicted.

## Files Modified

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/include/CV32E40P_Channel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_Channel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/include/CV32E40P_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_PerformanceModel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_SchedulingFunction.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/monitors/variants/CV32E40P/src/CV32E40P_Monitor.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/monitors/variants/CV32E40P/src/CV32E40P_InstructionMonitors.cpp`

No `CV32E40P_CORE`, `CV32E40P_LLM`, `CV32E40P_QWEN_1`, external model, or `StaticBranchPredictModel` files were intentionally modified.

## Functions Modified

- `CV32E40P_Channel::getTraceValueHook`
- `CV32E40P_PerformanceModel::connectChannel`
- `CV32E40P_PerformanceModel::getPrintHeader`
- `CV32E40P_PerformanceModel::getPipelineStream`
- `CV32E40P_PerformanceModel::setBranchInstrumentation`
- `CV32E40P_Monitor::connectChannel`
- `CV32E40P_Monitor::getBlockDeclarations`
- Base CV32E40P instruction monitors for `beq`, `bne`, `blt`, `bge`, `bltu`, `bgeu`, `jal`, and `jalr`
- Base CV32E40P scheduling lambdas for `beq`, `bne`, `blt`, `bge`, `bltu`, `bgeu`, `jal`, and `jalr`

## New Fields Added

Timing CSV columns added by Step 4:

```text
branch_is_control,branch_taken,branch_mispredict,branch_redirect_cycles
```

Internal channel/monitor field added by the uncertainty fix:

```text
branch_taken_actual
```

The timing CSV header after Step 5 is:

```text
IF_stage,ID_stage,EX_stage,WB_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,rs2_data,divider_delay_cycles,multiplier_delay_cycles,uses_rs1,uses_rs2,uses_rd,raw_wait_cycles,raw_blocking_reg,raw_blocking_ready_cycle,branch_is_control,branch_taken,branch_mispredict,branch_redirect_cycles,memory_port_wait_cycles,memory_port_kind
```

## Source of Each Field

| Field | Source |
|---|---|
| `branch_is_control` | Set in CV32E40P scheduling lambdas for type ids `43-48`, `50`, and `51`. |
| `branch_taken` | Conditional branches use `branch_taken_actual` from the CV32E40P monitor. `jal` and `jalr` are treated as taken. |
| `branch_mispredict` | Static predict-not-taken proxy: equals `branch_taken` for conditional branches, and is `1` for `jal`/`jalr`. |
| `branch_redirect_cycles` | Conditional branches emit `branch_taken ? max(0, EX_stage - IF_stage) : 0`. `jal`/`jalr` emit `max(0, ID_stage - IF_stage)`. |

This updated formula is easier to interpret from the timing CSV itself because it depends on printed stage columns instead of internal `PCGen` timing.

Conditional monitor formulas:

| Instruction | `branch_taken_actual` |
|---|---|
| `beq` | `X[rs1] == X[rs2]` |
| `bne` | `X[rs1] != X[rs2]` |
| `blt` | `(int32_t)X[rs1] < (int32_t)X[rs2]` |
| `bge` | `(int32_t)X[rs1] >= (int32_t)X[rs2]` |
| `bltu` | `X[rs1] < X[rs2]` |
| `bgeu` | `X[rs1] >= X[rs2]` |

The implementation avoids extra calls to `StaticBranchPredictModel::getPc()` because `getPc()` mutates predictor state.

## Relevant Bottleneck

- Bottleneck category: `branch`
- Bottleneck mechanism: control-flow redirect under static predict-not-taken
- Related existing fields: `instr_id`, `type_id`, `pc`, `brTarget`, `IF_stage`, `ID_stage`, `EX_stage`

These fields support attribution of conditional branch redirect cycles and jump redirect cycles.

## Test Result

Rebuild commands run:

```sh
cmake --build etiss-perf-sim/etiss/build_dir --target install -- -j2
cmake --build etiss-perf-sim/simulator/build -- -j2
```

Validation command run:

```sh
./scripts/run.sh em:ud cv32e40p -ta=.llm_output/analysis/bottleneck_knowledge/CV32E40P/test -tp=.llm_output/analysis/bottleneck_knowledge/CV32E40P/test
```

The simulation completed successfully:

- Instructions: `923462`
- Estimated processor cycles: `2036105`
- Estimated CPI: `2.20486`

Representative output files were present under `.llm_output/analysis/bottleneck_knowledge/CV32E40P/test`:

- `asm_*.txt`: `60` files
- `CV32E40P_timing_*.csv`: `5` files
- `CV32E40P_trace_*.csv`: `7` files

Representative taken conditional branch row:

```text
44,45,46,0,43,46,428,26,0,0,444,0,0,0,1,1,0,0,-1,0,1,1,1,2,0,none
```

For this row, `type_id=46` is `bge`, `branch_taken=1`, and `branch_redirect_cycles=EX_stage-IF_stage=46-44=2`.

Representative not-taken conditional branch row:

```text
68,69,70,60,62,43,28884,15,14,0,28916,0,0,0,1,1,0,0,-1,0,1,0,0,0,0,none
```

For this row, `branch_taken=0`, so `branch_redirect_cycles=0`.

Representative `jal` redirect row:

```text
47,48,49,0,44,50,444,0,0,1,28784,0,0,0,0,0,1,0,-1,0,1,1,1,1,0,none
```

For this row, `type_id=50` is `jal` and `branch_redirect_cycles=ID_stage-IF_stage=48-47=1`. This was previously `3` under the old `n_JumpDecoder - n_PCGen` proxy.

Representative `jalr` redirect row:

```text
74,76,77,74,68,51,28908,15,0,1,40976,0,0,0,1,0,1,0,-1,0,1,1,1,2,0,none
```

For this row, `type_id=51` is `jalr` and `branch_redirect_cycles=ID_stage-IF_stage=76-74=2`.

Aggregate timing CSV checks across generated `CV32E40P_timing_*.csv` files:

| Check | Count |
|---|---:|
| Timing rows | `923462` |
| Rows with `branch_redirect_cycles > 0` | `58248` |
| Conditional branch rows, type ids `43-48` | `121900` |
| Conditional branch rows resolved as taken | `53563` |
| Conditional branch rows resolved as not taken | `68337` |
| Conditional branch formula mismatches | `0` |
| `jal`/`jalr` rows, type ids `50-51` | `4685` |
| `jal`/`jalr` formula mismatches | `0` |

Single-trace analyzer result after this update:

| Category | Cycles | Nonzero rows | Max row delay | % attributed |
|---|---:|---:|---:|---:|
| Branch/control-flow redirect | `113447` | `58248` | `3` | `5.35%` |

The existing decoded instruction trace output and assembly trace output remained present and readable.

## Uncertainty

- `branch_redirect_cycles` is still an attribution field, not a de-overlapped benchmark bottleneck contribution.
- Conditional branch outcome comes from monitor-generated register comparisons, so it depends on the monitor seeing the architecturally correct register values at instrumentation time.
- `CV32E40P_Channel`, `CV32E40P_Monitor`, `CV32E40P_InstructionMonitors.cpp`, and `CV32E40P_SchedulingFunction.cpp` are generated-style files and may be overwritten by future code generation.
- No branch predictor behavior was changed; the fields only trace and attribute the existing static predict-not-taken model.

## Next Recommended Step

Use the updated `branch_redirect_cycles` formula in the contribution analyzer reports, then rerun the full benchmark-suite analyzer only when updated whole-suite branch rankings are needed.
