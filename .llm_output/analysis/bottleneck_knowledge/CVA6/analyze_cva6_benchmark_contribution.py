#!/usr/bin/env python3
"""CVA6 benchmark-suite timing-trace contribution analyzer.

This tool analyzes benchmark folders laid out as:

  trace_output/cva6_bottleneck/<benchmark>/timing/CVA6_timing_*.csv

It reuses the single-directory CVA6 contribution analyzer for the
per-benchmark calculations, then aggregates the results across benchmarks.

--output-md .llm_output/analysis/bottleneck_knowledge/CVA6/cva6_benchmark_contribution.md

"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from analyze_cva6_contribution import (
    CATEGORIES,
    AnalysisStats,
    CategoryStats,
    analyze_trace_dir,
    format_int,
    markdown_table,
    pct,
)


DEFAULT_ROOT_DIR = Path("trace_output/cva6_bottleneck")


@dataclass
class BenchmarkResult:
    name: str
    trace_dir: Path
    stats: AnalysisStats


@dataclass
class SuiteStats:
    benchmark_results: list[BenchmarkResult] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    timing_files: int = 0
    rows: int = 0
    aggregate_max_cycle_sum: int = 0
    total_attributed: int = 0
    parse_warnings: Counter[str] = field(default_factory=Counter)
    frontend_wait_type_rows: Counter[str] = field(default_factory=Counter)
    frontend_wait_type_cycles: Counter[str] = field(default_factory=Counter)
    ex_subpipe_kind_rows: Counter[str] = field(default_factory=Counter)
    ex_subpipe_kind_cycles: Counter[str] = field(default_factory=Counter)
    categories: dict[str, CategoryStats] = field(
        default_factory=lambda: {key: CategoryStats() for key in CATEGORIES}
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze CVA6 timing contribution fields across benchmark folders."
    )
    parser.add_argument(
        "--root-dir",
        default=str(DEFAULT_ROOT_DIR),
        help=f"Root directory containing benchmark folders. Default: {DEFAULT_ROOT_DIR}",
    )
    parser.add_argument(
        "--benchmark",
        action="append",
        default=None,
        help="Optional benchmark name to analyze. Can be passed more than once.",
    )
    parser.add_argument(
        "--output-md",
        default=None,
        help="Optional path to write the generated Markdown report.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Number of benchmarks to show in ranking tables. Default: 5",
    )
    return parser.parse_args()


def benchmark_dirs(root_dir: Path, filters: list[str] | None) -> tuple[list[Path], list[str]]:
    skipped: list[str] = []
    if filters:
        dirs: list[Path] = []
        for name in filters:
            path = root_dir / name
            if path.is_dir():
                dirs.append(path)
            else:
                skipped.append(f"{name}: benchmark directory not found at {path}")
        return sorted(dirs, key=lambda path: path.name), skipped

    if not root_dir.is_dir():
        raise FileNotFoundError(f"Root directory not found: {root_dir}")
    dirs = sorted((path for path in root_dir.iterdir() if path.is_dir()), key=lambda path: path.name)
    return dirs, skipped


def category_total(stats: AnalysisStats, key: str) -> int:
    category = stats.categories.get(key)
    return category.total_cycles if category else 0


def ex_subpipe_total(stats: AnalysisStats) -> int:
    return sum(
        category.total_cycles
        for key, category in stats.categories.items()
        if key.startswith("ex_subpipe_")
    )


def benchmark_total(stats: AnalysisStats) -> int:
    return sum(category.total_cycles for category in stats.categories.values())


def dominant_category(stats: AnalysisStats) -> str:
    if not stats.categories:
        return "none"
    key, category = max(stats.categories.items(), key=lambda item: item[1].total_cycles)
    if category.total_cycles == 0:
        return "none"
    return CATEGORIES.get(key, {"name": key})["name"]


def add_category_stats(dst: CategoryStats, src: CategoryStats) -> None:
    dst.total_cycles += src.total_cycles
    dst.nonzero_rows += src.nonzero_rows
    if src.max_row_delay > dst.max_row_delay:
        dst.max_row_delay = src.max_row_delay
    dst.top_type_id.update(src.top_type_id)
    dst.top_pc.update(src.top_pc)


def build_suite_stats(root_dir: Path, filters: list[str] | None) -> SuiteStats:
    suite = SuiteStats()
    dirs, skipped = benchmark_dirs(root_dir, filters)
    suite.skipped.extend(skipped)

    for bench_dir in dirs:
        timing_dir = bench_dir / "timing"
        timing_files = sorted(timing_dir.glob("CVA6_timing_*.csv"))
        if not timing_files:
            suite.skipped.append(f"{bench_dir.name}: no CVA6_timing_*.csv files under {timing_dir}")
            continue

        try:
            stats = analyze_trace_dir(timing_dir)
        except (FileNotFoundError, ValueError, OSError) as exc:
            raise RuntimeError(f"{bench_dir.name}: {exc}") from exc

        result = BenchmarkResult(name=bench_dir.name, trace_dir=timing_dir, stats=stats)
        suite.benchmark_results.append(result)
        suite.timing_files += len(stats.timing_files)
        suite.rows += stats.rows
        suite.aggregate_max_cycle_sum += stats.max_pipeline_cycle
        suite.total_attributed += benchmark_total(stats)
        suite.parse_warnings.update(stats.parse_warnings)
        suite.frontend_wait_type_rows.update(stats.frontend_wait_type_rows)
        suite.frontend_wait_type_cycles.update(stats.frontend_wait_type_cycles)
        suite.ex_subpipe_kind_rows.update(stats.ex_subpipe_kind_rows)
        suite.ex_subpipe_kind_cycles.update(stats.ex_subpipe_kind_cycles)

        for key, category in stats.categories.items():
            if key not in suite.categories:
                suite.categories[key] = CategoryStats()
            add_category_stats(suite.categories[key], category)

    if not suite.benchmark_results:
        raise FileNotFoundError("No benchmarks with timing CSV files were analyzed")
    return suite


def render_category_summary(suite: SuiteStats) -> list[str]:
    rows: list[list[str]] = []
    for key, meta in CATEGORIES.items():
        category = suite.categories.get(key, CategoryStats())
        rows.append(
            [
                meta["name"],
                meta["field"],
                format_int(category.total_cycles),
                format_int(category.nonzero_rows),
                format_int(category.max_row_delay),
                pct(category.total_cycles, suite.total_attributed),
                pct(category.total_cycles, suite.aggregate_max_cycle_sum),
            ]
        )
    return markdown_table(
        [
            "Category",
            "Source field",
            "Cycles",
            "Nonzero rows",
            "Max row delay",
            "% attributed",
            "% aggregate max cycle sum",
        ],
        rows,
    )


def render_per_benchmark_table(results: list[BenchmarkResult]) -> list[str]:
    rows: list[list[str]] = []
    for result in results:
        stats = result.stats
        rows.append(
            [
                result.name,
                format_int(len(stats.timing_files)),
                format_int(stats.rows),
                format_int(stats.max_pipeline_cycle),
                format_int(benchmark_total(stats)),
                dominant_category(stats),
                format_int(category_total(stats, "divider")),
                format_int(category_total(stats, "icache")),
                format_int(category_total(stats, "frontend_cache_block")),
                format_int(category_total(stats, "frontend_if_capacity")),
                format_int(category_total(stats, "dcache")),
                format_int(category_total(stats, "branch_redirect")),
                format_int(category_total(stats, "raw")),
                format_int(category_total(stats, "clobber")),
                format_int(category_total(stats, "commit")),
                format_int(ex_subpipe_total(stats)),
            ]
        )
    return markdown_table(
        [
            "Benchmark",
            "Timing files",
            "Rows",
            "Max cycle",
            "Attributed cycles",
            "Dominant category",
            "Divider",
            "I-cache",
            "Frontend cache-block",
            "Frontend IF-capacity",
            "D-cache",
            "Branch redirect",
            "RAW",
            "Clobber",
            "Commit",
            "EX subpipe total",
        ],
        rows,
    )


def render_ranking(results: list[BenchmarkResult], label: str, value_fn, top_n: int) -> list[str]:
    ranked = sorted(results, key=lambda result: value_fn(result), reverse=True)[:top_n]
    rows = [
        [
            str(index),
            result.name,
            format_int(value_fn(result)),
            format_int(result.stats.rows),
            format_int(result.stats.max_pipeline_cycle),
        ]
        for index, result in enumerate(ranked, start=1)
    ]
    lines = [f"### Top {top_n} Benchmarks By {label}", ""]
    lines.extend(markdown_table(["Rank", "Benchmark", "Cycles", "Rows", "Max cycle"], rows))
    lines.append("")
    return lines


def render_frontend_wait_notes(results: list[BenchmarkResult]) -> list[str]:
    rows: list[list[str]] = []
    for result in results:
        stats = result.stats
        rows.append(
            [
                result.name,
                format_int(stats.frontend_wait_type_cycles.get("cacheBlockWait", 0)),
                format_int(stats.frontend_wait_type_rows.get("cacheBlockWait", 0)),
                format_int(stats.frontend_wait_type_cycles.get("ifCapacityWait", 0)),
                format_int(stats.frontend_wait_type_rows.get("ifCapacityWait", 0)),
                format_int(stats.frontend_wait_type_cycles.get("pcCorrectWait", 0)),
                "counted as branch redirect, not frontend",
            ]
        )
    return markdown_table(
        [
            "Benchmark",
            "cacheBlockWait cycles",
            "cacheBlockWait rows",
            "ifCapacityWait cycles",
            "ifCapacityWait rows",
            "pcCorrectWait cycles",
            "Note",
        ],
        rows,
    )


def render_ex_subpipe_notes(results: list[BenchmarkResult]) -> list[str]:
    rows: list[list[str]] = []
    for result in results:
        stats = result.stats
        rows.append(
            [
                result.name,
                format_int(ex_subpipe_total(stats)),
                format_int(stats.ex_subpipe_kind_cycles.get("ALU", 0)),
                format_int(stats.ex_subpipe_kind_cycles.get("MUL", 0)),
                format_int(stats.ex_subpipe_kind_cycles.get("DIV", 0)),
                format_int(stats.ex_subpipe_kind_cycles.get("DIVU", 0)),
                format_int(stats.ex_subpipe_kind_cycles.get("LOAD", 0)),
                format_int(stats.ex_subpipe_kind_cycles.get("STORE", 0)),
            ]
        )
    return markdown_table(
        [
            "Benchmark",
            "EX subpipe total",
            "ALU",
            "MUL",
            "DIV",
            "DIVU",
            "LOAD",
            "STORE",
        ],
        rows,
    )


def render_report(root_dir: Path, suite: SuiteStats, top_n: int) -> str:
    results = sorted(suite.benchmark_results, key=lambda result: result.name)
    lines: list[str] = []
    lines.append("# CVA6 Benchmark-Suite Delay Contribution Summary")
    lines.append("")
    lines.append("## Input Summary")
    lines.append("")
    lines.append(f"- Root directory: `{root_dir}`")
    lines.append(f"- Benchmarks analyzed: `{format_int(len(results))}`")
    lines.append(f"- Timing CSV files: `{format_int(suite.timing_files)}`")
    lines.append(f"- Timing rows: `{format_int(suite.rows)}`")
    lines.append(f"- Aggregate max observed cycle sum: `{format_int(suite.aggregate_max_cycle_sum)}`")
    lines.append(f"- Total attributed delay cycles: `{format_int(suite.total_attributed)}`")
    lines.append("")

    if suite.skipped:
        lines.append("## Skipped Benchmark Folders / Warnings")
        lines.append("")
        for item in suite.skipped:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("## Whole-Suite Category Summary")
    lines.append("")
    lines.extend(render_category_summary(suite))
    lines.append("")

    lines.append("## Per-Benchmark Summary")
    lines.append("")
    lines.extend(render_per_benchmark_table(results))
    lines.append("")

    lines.append("## Ranking Tables")
    lines.append("")
    lines.extend(render_ranking(results, "Total Attributed Delay", lambda result: benchmark_total(result.stats), top_n))
    for key, meta in CATEGORIES.items():
        lines.extend(
            render_ranking(
                results,
                meta["name"],
                lambda result, category_key=key: category_total(result.stats, category_key),
                top_n,
            )
        )

    lines.append("## Frontend Wait Notes")
    lines.append("")
    lines.extend(render_frontend_wait_notes(results))
    lines.append("")

    lines.append("## EX Subpipe Notes")
    lines.append("")
    lines.extend(render_ex_subpipe_notes(results))
    lines.append("")

    lines.append("## Parse Warnings")
    lines.append("")
    if suite.parse_warnings:
        warning_rows = [
            [field, format_int(count)]
            for field, count in suite.parse_warnings.most_common()
        ]
        lines.extend(markdown_table(["Field", "Malformed values treated as 0"], warning_rows))
    else:
        lines.append("No malformed numeric fields were observed.")
    lines.append("")

    lines.append("## Interpretation Notes")
    lines.append("")
    lines.append("- These totals are additive instrumentation-field sums, not critical-path analysis and not a de-overlapped CPI stack.")
    lines.append("- A single instruction row can contribute to more than one category.")
    lines.append("- Per-benchmark totals are independent benchmark summaries; the whole-suite summary adds those independent totals.")
    lines.append("- `frontend_wait_type=pcCorrectWait` is not counted as frontend wait because branch redirect is counted through `branch_redirect_cycles`.")
    lines.append("- Frontend cache-block and IF-capacity waits are intentionally reported as separate categories.")
    lines.append("- EX subpipe wait is split by `ex_subpipe_kind`; rows with `ex_subpipe_kind=none` do not contribute.")
    lines.append("- Commit wait uses `commit_wait_cycles` as one total category; this report does not split backpressure and capacity into separate contribution categories.")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    if args.top_n < 1:
        print("--top-n must be >= 1", file=sys.stderr)
        return 2

    root_dir = Path(args.root_dir)
    try:
        suite = build_suite_stats(root_dir, args.benchmark)
        report = render_report(root_dir, suite, args.top_n)
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(report)
    if args.output_md:
        output_path = Path(args.output_md)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
