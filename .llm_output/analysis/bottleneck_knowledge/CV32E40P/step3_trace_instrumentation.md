# CV32E40P Step 3 Trace Instrumentation: RAW Wait

## Summary

Implemented Step 3 RAW/source-register wait instrumentation for the base CV32E40P timing trace. The existing Step 1 identity fields and Step 2 divider/multiplier delay fields were preserved, and the new fields were appended to `CV32E40P_timing_*.csv`.

This step instruments source-register readiness waits by routing generated scheduler source-ready reads through `CV32E40P_PerformanceModel` helper methods. It does not add producer instruction IDs, branch attribution, memory-port attribution, or full bottleneck contribution accounting.

## Files Modified

- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/include/CV32E40P_PerformanceModel.h`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_PerformanceModel.cpp`
- `etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/CV32E40P/src/CV32E40P_SchedulingFunction.cpp`

No `CV32E40P_CORE`, `CV32E40P_LLM`, `CV32E40P_QWEN_1`, monitor, branch, memory-port, or external model files were intentionally modified for this step.

## Functions Modified

- `CV32E40P_PerformanceModel::getPrintHeader`
- `CV32E40P_PerformanceModel::getPipelineStream`
- `CV32E40P_PerformanceModel::getRawReadyA`
- `CV32E40P_PerformanceModel::getRawReadyB`
- Base CV32E40P scheduling lambdas in `CV32E40P_SchedulingFunction.cpp` whose source-read timing previously called:
  - `perfModel->regModel.getXa()`
  - `perfModel->regModel.getXb()`

The direct source-ready calls were replaced with:

- `perfModel->getRawReadyA(n_IF_stage)`
- `perfModel->getRawReadyB(n_IF_stage)`

This covers generated source-read timing for arithmetic, multiplier, divider, CSR source forms, stores, loads, branches, and `jalr` where those source-ready calls are present in the base CV32E40P scheduler.

## New Fields Added

The timing CSV now appends these Step 3 columns after the Step 2 fields:

```text
uses_rs1,uses_rs2,uses_rd,raw_wait_cycles,raw_blocking_reg,raw_blocking_ready_cycle
```

Full representative timing header:

```text
IF_stage,ID_stage,EX_stage,WB_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,rs2_data,divider_delay_cycles,multiplier_delay_cycles,uses_rs1,uses_rs2,uses_rd,raw_wait_cycles,raw_blocking_reg,raw_blocking_ready_cycle
```

## Source of Each Field

| Field | Source |
|---|---|
| `uses_rs1` | Existing CV32E40P type-id helper `has_rs1(type_id)` in `CV32E40P_PerformanceModel.cpp` |
| `uses_rs2` | Existing CV32E40P type-id helper `has_rs2(type_id)` in `CV32E40P_PerformanceModel.cpp` |
| `uses_rd` | Existing CV32E40P type-id helper `has_rd(type_id)` in `CV32E40P_PerformanceModel.cpp` |
| `raw_wait_cycles` | Maximum source wait observed for the current row: `max(0, source_ready_cycle - ID_operand_read_base_cycle)` |
| `raw_blocking_reg` | `rs1` or `rs2` register index associated with the maximum observed source wait, or `-1` when no RAW wait is observed |
| `raw_blocking_ready_cycle` | Register ready cycle returned by `StandardRegisterModel` for the blocking source, or `0` when no RAW wait is observed |

`getRawReadyA(baseCycle)` reads `regModel.getXa()`, compares the ready cycle with `baseCycle`, and records `rs1` as the blocking register when it produces the current maximum wait.

`getRawReadyB(baseCycle)` reads `regModel.getXb()`, compares the ready cycle with `baseCycle`, and records `rs2` as the blocking register when it produces the current maximum wait.

Per-row RAW fields are reset after each timing row is streamed.

## Relevant Bottleneck

- Bottleneck category: `data_dependency`
- Bottleneck mechanism: RAW/source-register readiness wait
- Related model: `StandardRegisterModel` through `regModel.getXa()`, `regModel.getXb()`, and existing generated scheduler timing expressions
- Related existing trace identity fields: `instr_id`, `type_id`, `pc`, `rs1`, `rs2`, `rd`

These fields make it possible to identify rows where source readiness delayed instruction timing, and to distinguish unavailable operands from real register index `0`.

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
- Estimated processor cycles: `2034529`
- Estimated CPI: `2.20315`

Representative output files were present under `.llm_output/analysis/bottleneck_knowledge/CV32E40P/test`:

- `asm_*.txt`: `60` files
- `CV32E40P_timing_*.csv`: `5` files
- `CV32E40P_trace_*.csv`: `7` files

Representative files inspected:

- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/test/asm_trace_0000.txt`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/test/CV32E40P_trace_0000.csv`
- `.llm_output/analysis/bottleneck_knowledge/CV32E40P/test/CV32E40P_timing_0000.csv`

The representative timing CSV had `20` columns, including all Step 3 fields.

Representative timing rows:

```text
IF_stage,ID_stage,EX_stage,WB_stage,instr_id,type_id,pc,rs1,rs2,rd,brTarget,rs2_data,divider_delay_cycles,multiplier_delay_cycles,uses_rs1,uses_rs2,uses_rd,raw_wait_cycles,raw_blocking_reg,raw_blocking_ready_cycle
1,2,3,0,0,10,256,0,0,1,0,0,0,0,1,0,1,0,-1,0
2,3,4,0,1,10,260,1,0,2,0,0,0,0,1,0,1,1,1,3
```

The second row confirms active RAW wait instrumentation:

- `uses_rs1 = 1`
- `uses_rs2 = 0`
- `uses_rd = 1`
- `raw_wait_cycles = 1`
- `raw_blocking_reg = 1`
- `raw_blocking_ready_cycle = 3`

Aggregate timing CSV checks across generated `CV32E40P_timing_*.csv` files:

| Check | Count |
|---|---:|
| Timing rows | `923462` |
| Rows with `uses_rs1 = 1` | `917298` |
| Rows with `uses_rs2 = 1` | `527872` |
| Rows with `uses_rd = 1` | `678073` |
| Rows with `raw_wait_cycles > 0` | `228319` |

The existing decoded instruction trace output and assembly trace output remained present and readable.

## Uncertainty

- No exact producer instruction ID is recorded yet, so `raw_blocking_reg` identifies the blocking architectural register but not the producer row.
- `rd = 0` behavior remains inherited from `StandardRegisterModel`; this step only adds operand availability flags.
- RAW wait is measured relative to the ID operand-read base cycle, not final `n_ID_stage`. For normal decoded instructions this base is `n_Decoder = n_IF_stage + 1`; for `jalr` it is the equivalent jump-decode read point. Rows where `raw_blocking_ready_cycle == n_Decoder` therefore do not count as RAW delay.
- If both source operands have the same maximum wait, the first observed source remains the recorded blocking register because the helper updates only on strictly larger waits.
- `CV32E40P_SchedulingFunction.cpp` is generated code and may be overwritten by future CorePerfDSL/code-generation runs.
- These fields represent modeled source-read wait, not a complete benchmark bottleneck contribution yet.

## Next Recommended Step

Add branch redirect instrumentation or memory-port wait instrumentation, then extend the trace analysis to compute per-category bottleneck contribution from `raw_wait_cycles`, divider/multiplier delay fields, and future branch/memory wait fields.
