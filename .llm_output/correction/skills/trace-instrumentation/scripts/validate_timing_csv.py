#!/usr/bin/env python3
"""Validate timing CSV headers and row widths using Python's csv module."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


DEFAULT_REQUIRED = [
    "IF",
    "ID",
    "EX",
    "MEM",
    "WB",
]


def validate(path: Path, required: list[str], max_rows: int) -> dict[str, object]:
    result: dict[str, object] = {
        "file": str(path),
        "header_columns": 0,
        "checked_rows": 0,
        "duplicate_columns": [],
        "missing_required_columns": [],
        "row_length_errors": [],
        "empty_header_columns": [],
        "null_field_counts": {},
        "ok": False,
    }
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            result["row_length_errors"] = ["empty file"]
            return result

        result["header_columns"] = len(header)
        result["duplicate_columns"] = sorted({x for x in header if header.count(x) > 1})
        result["empty_header_columns"] = [str(i) for i, x in enumerate(header) if not x]
        result["missing_required_columns"] = [x for x in required if x not in header]
        null_counts = {name: 0 for name in header}

        for row_number, row in enumerate(reader, start=2):
            if max_rows and result["checked_rows"] >= max_rows:
                break
            result["checked_rows"] = int(result["checked_rows"]) + 1
            if len(row) != len(header):
                result["row_length_errors"].append({"row": row_number, "columns": len(row)})
                continue
            for name, value in zip(header, row):
                if value == "null":
                    null_counts[name] += 1
        result["null_field_counts"] = {k: v for k, v in null_counts.items() if v}

    result["ok"] = not any(
        result[key]
        for key in (
            "duplicate_columns",
            "missing_required_columns",
            "row_length_errors",
            "empty_header_columns",
        )
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, nargs="+")
    parser.add_argument("--required", action="append", default=[])
    parser.add_argument("--max-rows", type=int, default=10000)
    args = parser.parse_args()

    required = args.required or DEFAULT_REQUIRED
    results = [validate(path, required, args.max_rows) for path in args.path]
    output = {"files": results, "ok": all(bool(item["ok"]) for item in results)}
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
