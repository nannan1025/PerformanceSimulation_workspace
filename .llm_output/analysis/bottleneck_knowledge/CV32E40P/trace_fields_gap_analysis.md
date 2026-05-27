# CV32E40P Trace Fields Gap Analysis

Static comparison of fields needed for bottleneck contribution analysis against fields currently visible in the generated CV32E40P trace/monitor/printer code.

| Required field | Available now? | Where found | Why needed | Suggested implementation location |
|---|---|---|---|---|
| `instruction_id` | Partial | `Channel::instrCnt` connected by `CV32E40P_Monitor.cpp:50`; no printed stable id confirmed | Join timing, instruction, and stall attribution rows | Add explicit printed id in `CV32E40P_Printer` / generated trace printer templates |
| `pc` | Yes | `CV32E40P_Channel.h:39`, `CV32E40P_Printer.cpp:52`, `CV32E40P_Monitor.cpp:56` | Instruction identity and branch/memory attribution | Existing |
| `opcode` | Partial | `typeId` in `CV32E40P_Monitor.cpp:32,51`; opcode string in monitor definitions but not printed as text in performance trace | Classify instruction flows | Add opcode mnemonic or typeId-to-opcode mapping in report/analyzer |
| `instruction_class` | No | Not found as runtime field | Aggregate by model instruction group | Generate from `typeId` mapping or emit group id in monitor |
| `stage enter/exit cycles` | Partial | Timing stream has stage completion columns `IF_stage,ID_stage,EX_stage,WB_stage` in `CV32E40P_PerformanceModel.cpp:66-87` | Compute per-stage waiting and contribution | Extend timing trace to include per-instruction stage enter and exit cycles |
| `stall_reason` | No | Not found | Attribute excess cycles to mechanism | Add explicit stall reason in scheduling nodes or post-process from instrumented max operands |
| `stall_cycles` | No | Not found | Quantify bottleneck contribution | Emit chosen max input and delta in generated scheduling functions |
| `blocking_resource` | No | Resources present in CorePerfDSL, not traced | Distinguish functional unit, port, stage, branch, RAW waits | Instrument generated resource timing and max decisions |
| `blocking_instruction_id` | No | Not found | Attribute RAW and structural blocking to producers | Store producer id in `StandardRegisterModel::setXd` and expose on `getXa/getXb` |
| `branch_prediction_result` | No | Static predictor logic found in `StaticBranchPredictModel.cpp:35-52`, no trace field | Compute branch penalty contribution | Add info getters/trace fields for predicted/actual/mispredict |
| `branch_redirect_penalty` | No | Not found | Quantify branch bottleneck | Emit `Pc` connector delay and mispredict cycle delta |
| `cache_hit_or_miss` | No | No CV32E40P cache model found | Needed only if cache/memory model exists later | Add memory model or mark unavailable for CV32E40P |
| `memory_wait_cycles` | No | Load/store resources only in `CV32E40P.corePerfDsl:112-113` | Quantify load/store waiting | Instrument `LSU`, `DPort_R`, `DPort_W`; add `addr` first |
| `raw_wait_cycles` | No | Register readiness exists in `StandardRegisterModel.h:37-39` | Quantify dependency stalls | Add ready-cycle delta and producer id in register model |
| `resource_wait_cycles` | No | Resources defined in `CV32E40P.corePerfDsl:21-24` | Quantify structural bottlenecks | Emit selected resource, previous busy-until, and wait delta |

Top gaps for CV32E40P: explicit stall attribution, per-instruction stage enter/exit cycles, blocking producer/resource, branch prediction result, effective memory address, and cache/memory wait fields.
