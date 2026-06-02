#!/usr/bin/env python3
"""CV32E40P timing-trace delay contribution analyzer.

This tool reads Step 1-5 CV32E40P_timing_*.csv files and summarizes
attribution fields that were added for bottleneck analysis.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import DefaultDict


DEFAULT_TRACE_DIR = Path(".llm_output/analysis/bottleneck_knowledge/CV32E40P/test")

REQUIRED_COLUMNS = {
    "IF_stage",
    "ID_stage",
    "EX_stage",
    "WB_stage",
    "instr_id",
    "type_id",
    "pc",
    "raw_wait_cycles",
    "branch_redirect_cycles",
    "divider_delay_cycles",
    "multiplier_delay_cycles",
    "memory_port_wait_cycles",
    "memory_port_kind",
}

STAGE_COLUMNS = ("IF_stage", "ID_stage", "EX_stage", "WB_stage")

CATEGORIES = {
    "raw": {
        "name": "RAW wait",
        "field": "raw_wait_cycles",
        "formula": "sum(raw_wait_cycles)",
    },
    "branch": {
        "name": "Branch/control-flow redirect",
        "field": "branch_redirect_cycles",
        "formula": "sum(branch_redirect_cycles)",
    },
    "divider": {
        "name": "Divider delay",
        "field": "divider_delay_cycles",
        "formula": "sum(divider_delay_cycles)",
    },
    "multiplier": {
        "name": "Multiplier delay",
        "field": "multiplier_delay_cycles",
        "formula": "sum(multiplier_delay_cycles)",
    },
    "memory_port": {
        "name": "Memory-port structural wait",
        "field": "memory_port_wait_cycles",
        "formula": "sum(memory_port_wait_cycles)",
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
    memory_port_kind_rows: Counter[str] = field(default_factory=Counter)
    categories: dict[str, CategoryStats] = field(
        default_factory=lambda: {key: CategoryStats() for key in CATEGORIES}
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze CV32E40P Step 1-5 timing trace contribution fields."
    )
    parser.add_argument(
        "--trace-dir",
        default=str(DEFAULT_TRACE_DIR),
        help=f"Directory containing CV32E40P_timing_*.csv files. Default: {DEFAULT_TRACE_DIR}",
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


def normalize_memory_kind(kind: str | None) -> str:
    if not kind:
        return "none"
    if kind in {"DPort_R", "DPort_W", "none"}:
        return kind
    return f"other:{kind}"


def validate_header(path: Path, fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise ValueError(f"{path}: missing CSV header")
    missing = sorted(REQUIRED_COLUMNS.difference(fieldnames))
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"{path}: missing required columns: {missing_text}")


def analyze_trace_dir(trace_dir: Path) -> AnalysisStats:
    stats = AnalysisStats()
    stats.timing_files = sorted(trace_dir.glob("CV32E40P_timing_*.csv"))
    if not stats.timing_files:
        raise FileNotFoundError(f"No CV32E40P_timing_*.csv files found in {trace_dir}")

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
                stats.memory_port_kind_rows[normalize_memory_kind(row.get("memory_port_kind"))] += 1

                for key, meta in CATEGORIES.items():
                    delay = parse_int(row.get(meta["field"]), meta["field"], stats)
                    category = stats.categories[key]
                    category.total_cycles += delay
                    if delay > 0:
                        category.nonzero_rows += 1
                        if delay > category.max_row_delay:
                            category.max_row_delay = delay
                        category.top_type_id[type_id] += delay
                        category.top_pc[pc] += delay

    return stats


def pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.00%"
    return f"{(numerator / denominator) * 100:.2f}%"


def format_int(value: int) -> str:
    return f"{value:,}"


def markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def format_top(counter: Counter[str], top_n: int) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{key}:{format_int(value)}" for key, value in counter.most_common(top_n))


def render_report(stats: AnalysisStats, trace_dir: Path, top_n: int) -> str:
    total_attributed = sum(category.total_cycles for category in stats.categories.values())

    lines: list[str] = []
    lines.append("# CV32E40P Trace Delay Contribution Summary")
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
    for key, meta in CATEGORIES.items():
        category = stats.categories[key]
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

    lines.append("## Memory-Port Kind Rows")
    lines.append("")
    memory_rows = [
        [kind, format_int(count), pct(count, stats.rows)]
        for kind, count in stats.memory_port_kind_rows.most_common()
    ]
    lines.extend(markdown_table(["memory_port_kind", "Rows", "% rows"], memory_rows))
    lines.append("")

    lines.append(f"## Top Contributors by Type ID and PC (top {top_n})")
    lines.append("")
    top_rows = []
    for key, meta in CATEGORIES.items():
        category = stats.categories[key]
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
    formula_rows = [
        [meta["name"], meta["formula"]]
        for meta in CATEGORIES.values()
    ]
    lines.extend(markdown_table(["Category", "Formula"], formula_rows))
    lines.append("")

    lines.append("## Parse Warnings")
    lines.append("")
    if stats.parse_warnings:
        warning_rows = [
            [field, format_int(count)]
            for field, count in stats.parse_warnings.most_common()
        ]
        lines.extend(markdown_table(["Field", "Malformed values treated as 0"], warning_rows))
    else:
        lines.append("No malformed numeric fields were observed.")
    lines.append("")

    lines.append("## Interpretation Notes")
    lines.append("")
    lines.append("- These totals are additive sums of instrumentation fields, not a de-overlapped CPI stack.")
    lines.append("- A single instruction row can contribute to more than one category.")
    lines.append("- `memory_port_wait_cycles` covers modeled DPort/WB-stage structural wait only, not cache or external memory latency.")
    lines.append("- RAW attribution does not yet include producer instruction ID.")
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
