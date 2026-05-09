#!/usr/bin/env python3
"""Scan a public skill package for obvious private paths, secrets, and client residue."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_BLOCK_PATTERNS = [
    r"/" + "Users" + r"/",
    r"/" + "home" + r"/",
    r"/" + "Volumes" + r"/",
    r"Bearer\s+[A-Za-z0-9._-]+",
    r"sk-[A-Za-z0-9_-]{12,}",
    r"(?i)(api[_-]?key|OPENAI_API_KEY|password|passwd|cookie|secret|token)\s*[:=]",
]

PROJECT_RESIDUE_PATTERNS: list[str] = []

TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".html",
    ".css",
    ".svg",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository or skill root to scan.")
    parser.add_argument("--extra-pattern", action="append", default=[], help="Additional regex pattern to block.")
    parser.add_argument("--allow-project-words", action="store_true", help="Do not fail on built-in project residue word list.")
    return parser.parse_args()


def should_scan(path: Path) -> bool:
    if ".git" in path.parts:
        return False
    if path.name in {".DS_Store"}:
        return False
    return path.suffix.lower() in TEXT_SUFFIXES


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    patterns = [re.compile(p, re.IGNORECASE) for p in DEFAULT_BLOCK_PATTERNS + args.extra_pattern]
    if not args.allow_project_words:
        patterns.extend(re.compile(re.escape(p), re.IGNORECASE) for p in PROJECT_RESIDUE_PATTERNS)

    findings = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and should_scan(p)):
        rel = path.relative_to(root)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern in patterns:
                if pattern.search(line):
                    findings.append((str(rel), line_no, pattern.pattern))

    if findings:
        for rel, line_no, pattern in findings:
            print(f"{rel}:{line_no}: matched {pattern}")
        raise SystemExit(1)

    print("Public skill audit passed.")


if __name__ == "__main__":
    main()
