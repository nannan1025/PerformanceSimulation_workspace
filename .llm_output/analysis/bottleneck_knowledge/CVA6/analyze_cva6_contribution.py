#!/usr/bin/env python3
"""CVA6 timing-trace bottleneck contribution analyzer.

This tool reads CVA6_timing_*.csv files with Step 1-8 instrumentation fields
and summarizes additive bottleneck attribution signals.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_TRACE_DIR = Path(".llm_output/analysis/bottleneck_knowledge/CVA6/test")

STAGE_COLUMNS = ("PC_stage", "IF_stage", "IQ_stage", "ID_stage", "IS_stage", "EX_stage", "COM_stage")

REQUIRED_COLUMNS = {
    *STAGE_COLUMNS,
    "instr_id",
    "type_id",
    "pc",
    "divider_extra_cycles",
    "icache_extra_cycles",
    "frontend_wait_cycles",
    "frontend_wait_type",
    "dcache_extra_cycles",
    "branch_redirect_cycles",
    "raw_wait_cycles",
    "ex_subpipe_wait_cycles",
    "ex_subpipe_kind",
    "clobber_wait_cycles",
    "commit_wait_cycles",
}

BASE_CATEGORIES = {
    "divider": {
        "name": "Divider extra delay",
        "field": "divider_extra_cycles",
        "formula": "sum(divider_extra_cycles)",
    },
    "icache": {
        "name": "I-cache extra delay",
        "field": "icache_extra_cycles",
        "formula": "sum(icache_extra_cycles)",
    },
    "frontend_cache_block": {
        "name": "Frontend cache-block wait",
        "field": "frontend_wait_cycles",
        "formula": 'sum(frontend_wait_cycles where frontend_wait_type == "cacheBlockWait")',
    },
    "frontend_if_capacity": {
        "name": "Frontend IF-capacity wait",
        "field": "frontend_wait_cycles",
        "formula": 'sum(frontend_wait_cycles where frontend_wait_type == "ifCapacityWait")',
    },
    "dcache": {
        "name": "D-cache / memory extra delay",
        "field": "dcache_extra_cycles",
        "formula": "sum(dcache_extra_cycles)",
    },
    "branch_redirect": {
        "name": "Branch redirect delay",
        "field": "branch_redirect_cycles",
        "formula": "sum(branch_redirect_cycles)",
    },
    "raw": {
        "name": "RAW wait",
        "field": "raw_wait_cycles",
        "formula": "sum(raw_wait_cycles)",
    },
    "clobber": {
        "name": "Clobber model delay",
        "field": "clobber_wait_cycles",
        "formula": "sum(clobber_wait_cycles)",
    },
    "commit": {
        "name": "Commit wait",
        "field": "commit_wait_cycles",
        "formula": "sum(commit_wait_cycles)",
    },
}

KNOWN_EX_SUBPIPE_KINDS = ("ALU", "MUL", "DIV", "DIVU", "LOAD", "STORE")

CATEGORIES = {
    **BASE_CATEGORIES,
    **{
        f"ex_subpipe_{kind.lower()}": {
            "name": f"EX subpipe wait ({kind})",
            "field": "ex_subpipe_wait_cycles",
            "formula": f'sum(ex_subpipe_wait_cycles where ex_subpipe_kind == "{kind}")',
        }
        for kind in KNOWN_EX_SUBPIPE_KINDS
    },
}


@dataclass
class CategoryStats:
    total_cycles: int = 0
    nonzero_rows: int = 0
    max_row_delay: int = 0
    top_type_id: Counter[str] = field(default_factory=Counter)
    top_pc: Counter[str] = field(default_factory=Counter)


@dataclass
class AnalysisStats:
    timing_files: list[Path] = field(default_factory=list)
    rows: int = 0
    max_pipeline_cycle: int = 0
    parse_warnings: Counter[str] = field(default_factory=Counter)
    frontend_wait_type_rows: Counter[str] = field(default_factory=Counter)
    frontend_wait_type_cycles: Counter[str] = field(default_factory=Counter)
    ex_subpipe_kind_rows: Counter[str] = field(default_factory=Counter)
    ex_subpipe_kind_cycles: Counter[str] = field(default_factory=Counter)
    categories: dict[str, CategoryStats] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.categories:
            self.categories = {key: CategoryStats() for key in CATEGORIES}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze CVA6 Step 1-8 timing trace contribution fields."
    )
    parser.add_argument(
        "--trace-dir",
        default=str(DEFAULT_TRACE_DIR),
        help=f"Directory containing CVA6_timing_*.csv files. Default: {DEFAULT_TRACE_DIR}",
    )
    parser.add_argument(
        "--output-md",
        default=None,
        help="Optional path to write the generated Markdown report.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of top PC/type_id contributors to show per category. Default: 10",
    )
    return parser.parse_args()


def parse_int(value: str | None, field_name: str, stats: AnalysisStats) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(value, 0)
    except ValueError:
        stats.parse_warnings[field_name] += 1
        return 0


def normalize_frontend_wait_type(value: str | None) -> str:
    if not value:
        return "none"
    if value in {"none", "pcCorrectWait", "cacheBlockWait", "ifCapacityWait"}:
        return value
    return f"other:{value}"


def normalize_ex_subpipe_kind(value: str | None) -> str:
    if not value:
        return "none"
    if value in {"none", *KNOWN_EX_SUBPIPE_KINDS}:
        return value
    return f"other:{value}"


def validate_header(path: Path, fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise ValueError(f"{path}: missing CSV header")
    missing = sorted(REQUIRED_COLUMNS.difference(fieldnames))
    if missing:
        raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")


def add_category_delay(
    stats: AnalysisStats,
    key: str,
    delay: int,
    type_id: str,
    pc: str,
) -> None:
    category = stats.categories.setdefault(key, CategoryStats())
    category.total_cycles += delay
    if delay > 0:
        category.nonzero_rows += 1
        if delay > category.max_row_delay:
            category.max_row_delay = delay
        category.top_type_id[type_id] += delay
        category.top_pc[pc] += delay


def analyze_trace_dir(trace_dir: Path) -> AnalysisStats:
    stats = AnalysisStats()
    stats.timing_files = sorted(trace_dir.glob("CVA6_timing_*.csv"))
    if not stats.timing_files:
        raise FileNotFoundError(f"No CVA6_timing_*.csv files found in {trace_dir}")

    for path in stats.timing_files:
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            validate_header(path, reader.fieldnames)
            for row in reader:
                stats.rows += 1

                for stage in STAGE_COLUMNS:
                    value = parse_int(row.get(stage), stage, stats)
                    if value > stats.max_pipeline_cycle:
                        stats.max_pipeline_cycle = value

                type_id = row.get("type_id", "")
                pc = row.get("pc", "")

                add_category_delay(
                    stats,
                    "divider",
                    parse_int(row.get("divider_extra_cycles"), "divider_extra_cycles", stats),
                    type_id,
                    pc,
                )
                add_category_delay(
                    stats,
                    "icache",
                    parse_int(row.get("icache_extra_cycles"), "icache_extra_cycles", stats),
                    type_id,
                    pc,
                )

                frontend_wait = parse_int(row.get("frontend_wait_cycles"), "frontend_wait_cycles", stats)
                frontend_type = normalize_frontend_wait_type(row.get("frontend_wait_type"))
                stats.frontend_wait_type_rows[frontend_type] += 1
                stats.frontend_wait_type_cycles[frontend_type] += frontend_wait
                if frontend_type == "cacheBlockWait":
                    add_category_delay(stats, "frontend_cache_block", frontend_wait, type_id, pc)
                elif frontend_type == "ifCapacityWait":
                    add_category_delay(stats, "frontend_if_capacity", frontend_wait, type_id, pc)

                add_category_delay(
                    stats,
                    "dcache",
                    parse_int(row.get("dcache_extra_cycles"), "dcache_extra_cycles", stats),
                    type_id,
                    pc,
                )
                add_category_delay(
                    stats,
                    "branch_redirect",
                    parse_int(row.get("branch_redirect_cycles"), "branch_redirect_cycles", stats),
                    type_id,
                    pc,
                )
                add_category_delay(
                    stats,
                    "raw",
                    parse_int(row.get("raw_wait_cycles"), "raw_wait_cycles", stats),
                    type_id,
                    pc,
                )

                ex_delay = parse_int(row.get("ex_subpipe_wait_cycles"), "ex_subpipe_wait_cycles", stats)
                ex_kind = normalize_ex_subpipe_kind(row.get("ex_subpipe_kind"))
                stats.ex_subpipe_kind_rows[ex_kind] += 1
                stats.ex_subpipe_kind_cycles[ex_kind] += ex_delay
                if ex_kind != "none":
                    ex_key = f"ex_subpipe_{ex_kind.lower().replace(':', '_')}"
                    if ex_key not in CATEGORIES:
                        CATEGORIES[ex_key] = {
                            "name": f"EX subpipe wait ({ex_kind})",
                            "field": "ex_subpipe_wait_cycles",
                            "formula": f'sum(ex_subpipe_wait_cycles where ex_subpipe_kind == "{ex_kind}")',
                        }
                    add_category_delay(stats, ex_key, ex_delay, type_id, pc)

                add_category_delay(
                    stats,
                    "clobber",
                    parse_int(row.get("clobber_wait_cycles"), "clobber_wait_cycles", stats),
                    type_id,
                    pc,
                )
                add_category_delay(
                    stats,
                    "commit",
                    parse_int(row.get("commit_wait_cycles"), "commit_wait_cycles", stats),
                    type_id,
                    pc,
                )

    return stats


def pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.00%"
    return f"{(numerator / denominator) * 100:.2f}%"


def format_int(value: int) -> str:
    return f"{value:,}"


def markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def format_top(counter: Counter[str], top_n: int) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{key}:{format_int(value)}" for key, value in counter.most_common(top_n))


def category_items(stats: AnalysisStats) -> list[tuple[str, dict[str, str], CategoryStats]]:
    ordered_keys = [key for key in CATEGORIES if key in stats.categories]
    return [(key, CATEGORIES[key], stats.categories[key]) for key in ordered_keys]


def render_report(stats: AnalysisStats, trace_dir: Path, top_n: int) -> str:
    total_attributed = sum(category.total_cycles for category in stats.categories.values())

    lines: list[str] = []
    lines.append("# CVA6 Trace Bottleneck Contribution Summary")
    lines.append("")
    lines.append("## Input")
    lines.append("")
    lines.append(f"- Trace directory: `{trace_dir}`")
    lines.append(f"- Timing CSV files: `{len(stats.timing_files)}`")
    lines.append(f"- Timing rows: `{format_int(stats.rows)}`")
    lines.append(f"- Max observed pipeline cycle: `{format_int(stats.max_pipeline_cycle)}`")
    lines.append(f"- Total attributed delay cycles: `{format_int(total_attributed)}`")
    lines.append("")

    lines.append("## Category Summary")
    lines.append("")
    category_rows = []
    for _key, meta, category in category_items(stats):
        category_rows.append(
            [
                meta["name"],
                meta["field"],
                format_int(category.total_cycles),
                format_int(category.nonzero_rows),
                format_int(category.max_row_delay),
                pct(category.total_cycles, total_attributed),
                pct(category.total_cycles, stats.max_pipeline_cycle),
            ]
        )
    lines.extend(
        markdown_table(
            [
                "Category",
                "Source field",
                "Cycles",
                "Nonzero rows",
                "Max row delay",
                "% attributed",
                "% max cycle",
            ],
            category_rows,
        )
    )
    lines.append("")

    lines.append("## Frontend Wait Type Breakdown")
    lines.append("")
    frontend_rows = [
        [kind, format_int(stats.frontend_wait_type_rows[kind]), format_int(cycles), pct(cycles, total_attributed)]
        for kind, cycles in stats.frontend_wait_type_cycles.most_common()
    ]
    lines.extend(markdown_table(["frontend_wait_type", "Rows", "Cycles", "% attributed"], frontend_rows))
    lines.append("")

    lines.append("## EX Subpipe Kind Breakdown")
    lines.append("")
    ex_rows = [
        [kind, format_int(stats.ex_subpipe_kind_rows[kind]), format_int(cycles), pct(cycles, total_attributed)]
        for kind, cycles in stats.ex_subpipe_kind_cycles.most_common()
    ]
    lines.extend(markdown_table(["ex_subpipe_kind", "Rows", "Cycles", "% attributed"], ex_rows))
    lines.append("")

    lines.append(f"## Top Contributors by Type ID and PC (top {top_n})")
    lines.append("")
    top_rows = []
    for _key, meta, category in category_items(stats):
        top_rows.append(
            [
                meta["name"],
                format_top(category.top_type_id, top_n),
                format_top(category.top_pc, top_n),
            ]
        )
    lines.extend(markdown_table(["Category", "Top type_id:cycles", "Top pc:cycles"], top_rows))
    lines.append("")

    lines.append("## Formulas")
    lines.append("")
    formula_rows = [[meta["name"], meta["formula"]] for _key, meta, _category in category_items(stats)]
    lines.extend(markdown_table(["Category", "Formula"], formula_rows))
    lines.append("")

    lines.append("## Parse Warnings")
    lines.append("")
    if stats.parse_warnings:
        warning_rows = [[field, format_int(count)] for field, count in stats.parse_warnings.most_common()]
        lines.extend(markdown_table(["Field", "Malformed values treated as 0"], warning_rows))
    else:
        lines.append("No malformed numeric fields were observed.")
    lines.append("")

    lines.append("## Interpretation Notes")
    lines.append("")
    lines.append("- These totals are additive sums of instrumentation fields, not critical-path analysis and not a de-overlapped CPI stack.")
    lines.append("- A single instruction row can contribute to more than one category, so category totals can overlap conceptually.")
    lines.append("- `frontend_wait_type=pcCorrectWait` is excluded from frontend wait categories because branch redirect is counted through `branch_redirect_cycles`.")
    lines.append("- Frontend cache-block and IF-capacity waits are intentionally reported as separate categories.")
    lines.append("- EX subpipe wait is split by `ex_subpipe_kind`; rows with `ex_subpipe_kind=none` do not contribute.")
    lines.append("- Commit wait uses `commit_wait_cycles` as one total category; this report does not split backpressure and capacity into separate contribution categories.")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    trace_dir = Path(args.trace_dir)
    if args.top_n < 1:
        print("--top-n must be >= 1", file=sys.stderr)
        return 2

    try:
        stats = analyze_trace_dir(trace_dir)
        report = render_report(stats, trace_dir, args.top_n)
    except (FileNotFoundError, ValueError, OSError) as exc:
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
