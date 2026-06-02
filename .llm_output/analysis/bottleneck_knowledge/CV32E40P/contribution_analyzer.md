# CV32E40P Trace Contribution Analyzer

## Purpose

`analyze_cv32e40p_contribution.py` is a Python stdlib-only post-processing tool for CV32E40P Step 1-5 timing traces.

It reads all `CV32E40P_timing_*.csv` files in a trace directory and computes additive delay summaries for:

- RAW wait from `raw_wait_cycles`
- branch/control-flow redirect from `branch_redirect_cycles`
- divider extra execution delay from `divider_delay_cycles`
- multiplier extra execution delay from `multiplier_delay_cycles`
- memory-port structural wait from `memory_port_wait_cycles`

The analyzer intentionally ignores `CV32E40P_trace_*.csv` and `asm_*.txt` for v1.

For this CV32E40P trace version, `raw_wait_cycles` means
`max(0, source_ready_cycle - ID_operand_read_base_cycle)`. For normal decoded
instructions, `ID_operand_read_base_cycle = n_Decoder = n_IF_stage + 1`.

For this CV32E40P trace version, `divider_delay_cycles` and
`multiplier_delay_cycles` mean extra execution cycles beyond a normal 1-cycle
execution baseline. The simulator still uses the full functional-unit latency
for pipeline timing.

## Input Format

Required timing CSV columns:

- `instr_id`, `type_id`, `pc`
- `IF_stage`, `ID_stage`, `EX_stage`, `WB_stage`
- `raw_wait_cycles`
- `branch_redirect_cycles`
- `divider_delay_cycles`
- `multiplier_delay_cycles`
- `memory_port_wait_cycles`
- `memory_port_kind`

Blank numeric fields are treated as `0`. Malformed numeric fields are counted as parse warnings and treated as `0`.

## Commands

Print a report to stdout:

```bash
python3 .llm_output/analysis/bottleneck_knowledge/CV32E40P/analyze_cv32e40p_contribution.py --trace-dir .llm_output/analysis/bottleneck_knowledge/CV32E40P/test
```

Print the same report and write it to Markdown:

```bash
python3 .llm_output/analysis/bottleneck_knowledge/CV32E40P/analyze_cv32e40p_contribution.py --trace-dir .llm_output/analysis/bottleneck_knowledge/CV32E40P/test --output-md /tmp/cv32e40p_contribution_summary.md
```

Optional:

- `--top-n N`: number of top PC/type-ID contributors to show per category. Default is `10`.

## Contribution Formulas

| Category | Formula |
| --- | --- |
| RAW wait | `sum(raw_wait_cycles)` |
| Branch/control-flow redirect | `sum(branch_redirect_cycles)` |
| Divider extra execution delay | `sum(divider_delay_cycles)` |
| Multiplier extra execution delay | `sum(multiplier_delay_cycles)` |
| Memory-port structural wait | `sum(memory_port_wait_cycles)` |

The report also computes:

- nonzero row count per category
- max single-row delay per category
- percentage of total attributed delay
- percentage relative to max observed pipeline cycle
- memory-port row counts by `memory_port_kind`
- top contributing `type_id` and `pc` values per category

## Validation Result

Syntax check:

```bash
python3 -m py_compile .llm_output/analysis/bottleneck_knowledge/CV32E40P/analyze_cv32e40p_contribution.py
```

Analyzer run:

```bash
python3 .llm_output/analysis/bottleneck_knowledge/CV32E40P/analyze_cv32e40p_contribution.py --trace-dir .llm_output/analysis/bottleneck_knowledge/CV32E40P/test
```

Optional Markdown output check:

```bash
python3 .llm_output/analysis/bottleneck_knowledge/CV32E40P/analyze_cv32e40p_contribution.py --trace-dir .llm_output/analysis/bottleneck_knowledge/CV32E40P/test --output-md /tmp/cv32e40p_contribution_summary.md
```

Current validation summary on `.llm_output/analysis/bottleneck_knowledge/CV32E40P/test`:

- Timing CSV files: `5`
- Timing rows: `923,462`
- Max observed pipeline cycle: `2,036,105`
- Total attributed delay cycles: `1,962,544`

| Category | Cycles | Nonzero rows | Max row delay | % attributed | % max cycle |
| --- | ---: | ---: | ---: | ---: | ---: |
| RAW wait | `910,567` | `88,799` | `31` | `46.40%` | `44.72%` |
| Branch/control-flow redirect | `113,447` | `58,248` | `3` | `5.78%` | `5.57%` |
| Divider extra execution delay | `938,530` | `31,038` | `31` | `47.82%` | `46.09%` |
| Multiplier extra execution delay | `0` | `0` | `0` | `0.00%` | `0.00%` |
| Memory-port structural wait | `0` | `0` | `0` | `0.00%` | `0.00%` |

Memory-port kind rows:

| memory_port_kind | Rows | % rows |
| --- | ---: | ---: |
| `none` | `516,806` | `55.96%` |
| `DPort_R` | `283,175` | `30.66%` |
| `DPort_W` | `123,481` | `13.37%` |

No malformed numeric fields were observed.

## Risks and Uncertainty

- The category sums are additive instrumentation-field totals, not a de-overlapped root-cause CPI stack.
- A single instruction row can contribute to multiple categories.
- `memory_port_wait_cycles` is currently zero for the validated `em:ud` trace even though load/store rows are present.
- Branch cycles depend on Step 4 branch outcome and redirect-cycle instrumentation correctness.
- RAW attribution does not yet include producer instruction ID.
- Memory-port attribution covers modeled DPort/WB-stage structural wait only, not cache hit/miss or external memory latency.
