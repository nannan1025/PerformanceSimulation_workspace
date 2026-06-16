# CVA6 Contribution Analyzer

## Purpose

`analyze_cva6_contribution.py` is a stdlib-only trace post-processor for the current CVA6 Step 1-8 timing CSV schema. It reads `CVA6_timing_*.csv` files and computes additive bottleneck contribution summaries from the trace fields already emitted by the simulator.

This is trace-field accounting, not critical-path analysis and not a de-overlapped CPI stack. A single timing row can contribute to multiple categories, so totals can overlap conceptually.

## Files

- Analyzer: `.llm_output/analysis/bottleneck_knowledge/CVA6/analyze_cva6_contribution.py`
- Documentation: `.llm_output/analysis/bottleneck_knowledge/CVA6/contribution_analyzer.md`
- Current validation summary: `.llm_output/analysis/bottleneck_knowledge/CVA6/cva6_contribution_summary.md`

## Input Format

The analyzer reads only:

```text
CVA6_timing_*.csv
```

from the selected trace directory. It ignores `CVA6_trace_*.csv` and `asm_*.txt` in this version.

Required columns:

```text
PC_stage,IF_stage,IQ_stage,ID_stage,IS_stage,EX_stage,COM_stage,
instr_id,type_id,pc,
divider_extra_cycles,
icache_extra_cycles,
frontend_wait_cycles,frontend_wait_type,
dcache_extra_cycles,
branch_redirect_cycles,
raw_wait_cycles,
ex_subpipe_wait_cycles,ex_subpipe_kind,
clobber_wait_cycles,
commit_wait_cycles
```

Malformed numeric fields are counted as parse warnings and treated as `0`.

## Commands

Syntax check:

```sh
python3 -m py_compile .llm_output/analysis/bottleneck_knowledge/CVA6/analyze_cva6_contribution.py
```

Run on the current CVA6 test trace:

```sh
python3 .llm_output/analysis/bottleneck_knowledge/CVA6/analyze_cva6_contribution.py --trace-dir .llm_output/analysis/bottleneck_knowledge/CVA6/test
```

Run and write the Markdown summary:

```sh
python3 .llm_output/analysis/bottleneck_knowledge/CVA6/analyze_cva6_contribution.py --trace-dir .llm_output/analysis/bottleneck_knowledge/CVA6/test --output-md .llm_output/analysis/bottleneck_knowledge/CVA6/cva6_contribution_summary.md
```

Useful options:

- `--trace-dir`: directory containing `CVA6_timing_*.csv`
- `--output-md`: optional path for writing the same Markdown printed to stdout
- `--top-n`: number of top `type_id` and `pc` contributors to show, default `10`

## Contribution Formulas

| Category | Formula |
| --- | --- |
| Divider delay | `sum(divider_extra_cycles)` |
| I-cache delay | `sum(icache_extra_cycles)` |
| Frontend cache-block wait | `sum(frontend_wait_cycles where frontend_wait_type == "cacheBlockWait")` |
| Frontend IF-capacity wait | `sum(frontend_wait_cycles where frontend_wait_type == "ifCapacityWait")` |
| D-cache / memory delay | `sum(dcache_extra_cycles)` |
| Branch redirect delay | `sum(branch_redirect_cycles)` |
| RAW wait | `sum(raw_wait_cycles)` |
| EX subpipe wait | `sum(ex_subpipe_wait_cycles)`, split by `ex_subpipe_kind` |
| Clobber model delay | `sum(clobber_wait_cycles)` |
| Commit wait | `sum(commit_wait_cycles)` |

`frontend_wait_type=pcCorrectWait` is intentionally not counted as a frontend wait category because branch redirect is already counted through `branch_redirect_cycles`.

## Current Validation Result

Validated on `.llm_output/analysis/bottleneck_knowledge/CVA6/test` using the commands above.

- Timing CSV files: `18`
- Timing rows: `1,384,912`
- Max observed pipeline cycle: `2,129,817`
- Total attributed delay cycles: `2,194,389`
- Parse warnings: `0`

Top current additive contributors:

| Category | Cycles | % attributed |
| --- | ---: | ---: |
| Branch redirect delay | 702,539 | 32.02% |
| Clobber model delay | 634,288 | 28.90% |
| RAW wait | 482,736 | 22.00% |
| EX subpipe wait (ALU) | 193,820 | 8.83% |
| Frontend IF-capacity wait | 76,865 | 3.50% |
| Divider extra delay | 45,818 | 2.09% |

The full generated summary is in `cva6_contribution_summary.md`.

## Reuse Notes

The script exposes reusable objects/functions for a future benchmark-suite analyzer:

- `REQUIRED_COLUMNS`
- `STAGE_COLUMNS`
- `analyze_trace_dir(trace_dir: Path) -> AnalysisStats`
- `render_report(stats, trace_dir, top_n) -> str`

## Risks and Caveats

- Category totals are additive field sums, not exclusive root-cause cycles.
- Some categories can overlap conceptually, especially producer latency and downstream RAW/clobber waits.
- Branch redirect uses the corrected `branch_redirect_cycles` field, not `frontend_wait_cycles`.
- Frontend cache-block and IF-capacity waits are separate categories and should not be merged without a specific analysis reason.
- EX subpipe rows with `ex_subpipe_kind=none` are excluded from EX contribution.
- Commit wait is reported as one category using `commit_wait_cycles`; this analyzer does not split backpressure and capacity into separate contribution categories.
