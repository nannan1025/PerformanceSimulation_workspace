# Trace Field Policy

## Stable fields

The current cross-core baseline is:

```text
pc,instr,rd,rs1,rs2,imm,rs1_data,rs2_data
IF,ID,EX,MEM,WB
used_rs1,used_rs2,used_rd,rd_ready_cycle
icache_miss,dcache_miss,icache_delay_cycles,dcache_delay_cycles
sim_misprediction
```

Do not require a field that the core cannot safely produce. Use `null` for
unsupported values and record the reason.

## Scheduling fields

Derive fields from the current CorePerfDSL formula and generated scheduling code.
The field name is always:

```text
<stage>_<source variable>
```

Examples include `IF_n_PC_Gen`, `ID_n_uA_OF_A`, `EX_n_ALU`, and
`MEM_n_DCache`. The field describes the value used by the formula, not a
post-hoc attribution guess.

## External fields

External values are valid only when captured from an existing scheduling call.
Never re-run a stateful model method during output. Preferred sources are:

| Field | Source | Fallback |
|---|---|---|
| `icache_delay_cycles` | saved `getDelay()` result | `null` |
| `dcache_delay_cycles` | saved `getDelay()` result | `null` |
| `icache_miss` | safe last-result getter | `null` |
| `dcache_miss` | safe last-result getter | `null` |
| `rd_ready_cycle` | existing register connector result/state | `null` |
| `sim_misprediction` | saved predictor result or safe snapshot | `null` |

## Schema evolution

Preserve old field order. Add new fields at the end of their stage group. Keep
removed names in history and identify likely renames by comparing normalized
variable names and formula context. Do not silently rename downstream-visible
columns.
