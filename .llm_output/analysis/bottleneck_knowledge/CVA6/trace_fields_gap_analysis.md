# CVA6 Trace Fields Gap Analysis

Static comparison of fields needed for bottleneck contribution analysis against fields currently visible in the generated CVA6 trace/monitor/printer code.

| Required field | Available now? | Where found | Why needed | Suggested implementation location |
|---|---|---|---|---|
| `instruction_id` | Partial | `Channel::instrCnt` connected by `CVA6_Monitor.cpp:53`; explicit printed id not confirmed | Join instruction, timing, and mechanism rows | Add explicit id to generated printer/timing rows |
| `pc` | Yes | `CVA6_Channel.h:39`, `CVA6_Printer.cpp:55`, `CVA6_Monitor.cpp:59` | Instruction identity, branch, I-cache attribution | Existing |
| `opcode` | Partial | `typeId` exists in `CVA6_Monitor.cpp:32,54`; mnemonic not printed in CVA6 performance fields | Classify instruction groups | Emit mnemonic or typeId mapping |
| `instruction_class` | No | Not found as runtime field | Aggregate by CorePerfDSL group | Generate instruction group id from CorePerfDSL |
| `stage enter/exit cycles` | Partial | Top-level timing columns `PC_stage,IF_stage,IQ_stage,ID_stage,IS_stage,EX_stage,COM_stage` in `CVA6_PerformanceModel.cpp:95-123` | Compute per-stage delay | Add per-instruction enter/exit and substage timings |
| `stall_reason` | No | Not found | Attribute cycles to mechanisms | Emit selected max contributor from generated scheduling functions |
| `stall_cycles` | No | Not found | Quantify contribution | Emit delta between selected max contributor and base latency |
| `blocking_resource` | No | Static resources in `CVA6.corePerfDsl:23-29`, not runtime fields | Separate cache, branch, RAW, subpipe, commit waits | Instrument generated resource and connector max decisions |
| `blocking_instruction_id` | No | Not found | Attribute RAW, clobber, structural waits to producers | Extend `StandardRegisterModel` and `ClobberModel` with producer ids |
| `branch_prediction_result` | No | Info getters exist in `BranchPredictionModel.h:112-114`, not connected to trace | Branch bottleneck contribution | Connect predictor info getters to trace/printer |
| `branch_redirect_penalty` | No | `t_pc_mp` and `t_pc_pt` internal in `BranchPredictionModel.h:141-142` | Quantify redirect cost | Expose connector timing delta from branch model |
| `cache_hit_or_miss` | Partial internal only | `getInfo_miss()` in `ICacheModel.h:45`, `DCacheModel.h:44` | Memory/frontend bottleneck attribution | Add cache miss fields to timing trace |
| `memory_wait_cycles` | No | D-cache delay code exists, return value not traced | Quantify load memory delay | Trace `DCacheModel::getDelay()` return value |
| `raw_wait_cycles` | No | Readiness model exists in `StandardRegisterModel.h:37-39` | Quantify source dependency waiting | Instrument source ready-cycle deltas |
| `resource_wait_cycles` | No | Subpipe block declarations exist in `CVA6.corePerfDsl:97-103` | Quantify structural conflicts | Add subpipe/resource wait fields in generated scheduling functions |

Top gaps for CVA6: predictor result/redirect fields, I-cache and D-cache miss/delay fields, subpipe/resource max attribution, RAW/clobber producer ids, commit wait, and per-substage timing.
