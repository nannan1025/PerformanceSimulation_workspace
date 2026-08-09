#!/usr/bin/env python3
"""Create a structural fingerprint for DSL/backend consistency checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def text_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix in {".h", ".cpp", ".corePerfDsl"})


def digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def tokens(pattern: str, text: str) -> list[str]:
    return sorted(set(re.findall(pattern, text)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("coreperfdsl", type=Path)
    parser.add_argument("backend", type=Path)
    args = parser.parse_args()

    dsl = args.coreperfdsl.read_text(encoding="utf-8", errors="replace")
    backend_text = ""
    if args.backend.is_dir():
        backend_text = "\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in text_files(args.backend)
        )

    payload = {
        "core_models": tokens(r"\bCorePerfModel\s+([A-Za-z_][A-Za-z0-9_]*)", dsl),
        "dsl_uas": tokens(r"\b(uA_[A-Za-z0-9_]+)", dsl),
        "dsl_connectors": tokens(r"\b(?:connector|Connector)\s*[:{]?\s*([A-Za-z_][A-Za-z0-9_]*)", dsl),
        "dsl_resources": tokens(r"\b(?:resource|Resource)\s*[:{]?\s*([A-Za-z_][A-Za-z0-9_]*)", dsl),
        "backend_functions": tokens(r"\bschedulingFunction_([A-Za-z0-9_]+)", backend_text),
        "backend_n_variables": tokens(r"\b(n_[A-Za-z0-9_]+)\b", backend_text),
        "backend_models": tokens(r"\bperfModel->([A-Za-z_][A-Za-z0-9_]*)", backend_text),
    }
    print(json.dumps({"fingerprint": digest(payload), "components": payload}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
