#!/usr/bin/env python3
"""Inventory a CorePerfDSL file and its generated backend without editing files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def unique(pattern: str, text: str) -> list[str]:
    return sorted(set(re.findall(pattern, text, flags=re.MULTILINE)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("coreperfdsl", type=Path)
    parser.add_argument("backend", type=Path)
    args = parser.parse_args()

    dsl = read_text(args.coreperfdsl)
    result: dict[str, object] = {
        "coreperfdsl": str(args.coreperfdsl),
        "coreperfdsl_sha256": sha256(args.coreperfdsl),
        "backend": str(args.backend),
        "backend_exists": args.backend.is_dir(),
        "dsl_core_models": unique(r"\bCorePerfModel\s+([A-Za-z_][A-Za-z0-9_]*)", dsl),
        "stages": unique(r"\b(?:stage|Stage)\s*[:{]\s*([A-Za-z_][A-Za-z0-9_]*)", dsl),
        "microactions": unique(r"\b(uA_[A-Za-z0-9_]+)", dsl),
        "resources": unique(r"\b(?:resource|Resource)\s*[:{]?\s*([A-Za-z_][A-Za-z0-9_]*)", dsl),
        "connectors": unique(r"\b(?:connector|Connector)\s*[:{]?\s*([A-Za-z_][A-Za-z0-9_]*)", dsl),
    }

    if args.backend.is_dir():
        files = sorted(p for p in args.backend.rglob("*") if p.is_file())
        result["backend_files"] = [str(p) for p in files]
        combined = "\n".join(read_text(p) for p in files if p.suffix in {".h", ".cpp"})
        result["scheduling_functions"] = unique(r"\b(?:void|static\s+void)\s+schedulingFunction_([A-Za-z0-9_]+)", combined)
        result["n_variables"] = unique(r"\b(n_[A-Za-z0-9_]+)\b", combined)
        result["trace_helpers"] = {
            name: (name in combined)
            for name in (
                "getPipelineStream",
                "getPrintHeader",
                "recordSchedVar",
                "trace_sched_vars",
                "getDelay(",
                "getXa(",
                "getXb(",
                "getPc_mp(",
                "getPc_pt(",
            )
        }
    else:
        result["backend_files"] = []

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
