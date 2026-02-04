#!/usr/bin/env python3
"""
Build a rebalanced calibration set by augmenting an existing calib.txt
with additional clean-only samples from a clean pool.

Inputs/outputs are fastText-formatted .txt files.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DEFAULT_BASE = REPO_ROOT / "data" / "calib.txt"
DEFAULT_CLEAN_POOL = REPO_ROOT / "data" / "train_time_hn_calib.txt"
DEFAULT_HOLDOUT = REPO_ROOT / "data" / "holdout_time.txt"
DEFAULT_OUT = REPO_ROOT / "data" / "calib_rebalanced.txt"
DEFAULT_META = REPO_ROOT / "data" / "calib_rebalanced.meta.json"


def parse_fasttext_line(line: str) -> tuple[list[str], str] | None:
    text = line.strip()
    if not text or not text.startswith("__label__"):
        return None
    parts = text.split()
    labels: list[str] = []
    idx = 0
    for token in parts:
        if token.startswith("__label__"):
            labels.append(token.replace("__label__", "", 1))
            idx += 1
        else:
            break
    payload = " ".join(parts[idx:]) if idx < len(parts) else ""
    if not labels or not payload:
        return None
    return labels, payload


def load_lines(path: Path) -> list[str]:
    lines: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)
    return lines


def count_labels(lines: list[str]) -> Counter:
    counts: Counter = Counter()
    for line in lines:
        parsed = parse_fasttext_line(line)
        if parsed is None:
            continue
        labels, _ = parsed
        for label in labels:
            counts[label] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE, help="Base calib.txt")
    parser.add_argument(
        "--clean-pool", type=Path, default=DEFAULT_CLEAN_POOL, help="Clean-only pool (.txt)"
    )
    parser.add_argument(
        "--holdout",
        type=Path,
        default=DEFAULT_HOLDOUT,
        help="Holdout set to exclude (fastText txt)",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output calib txt")
    parser.add_argument("--meta-out", type=Path, default=DEFAULT_META, help="Output meta json")
    parser.add_argument(
        "--max-clean",
        type=int,
        default=None,
        help="Maximum number of clean samples to add (default: all available)",
    )
    parser.add_argument("--seed", type=int, default=7, help="Random seed for sampling")
    args = parser.parse_args()

    if not args.base.exists():
        raise SystemExit(f"Base calib not found: {args.base}")
    if not args.clean_pool.exists():
        raise SystemExit(f"Clean pool not found: {args.clean_pool}")
    if args.holdout and not args.holdout.exists():
        raise SystemExit(f"Holdout not found: {args.holdout}")

    base_lines = load_lines(args.base)
    holdout_lines = load_lines(args.holdout) if args.holdout else []

    base_texts = set()
    for line in base_lines:
        parsed = parse_fasttext_line(line)
        if parsed is None:
            continue
        _, text = parsed
        base_texts.add(text)

    holdout_texts = set()
    for line in holdout_lines:
        parsed = parse_fasttext_line(line)
        if parsed is None:
            continue
        _, text = parsed
        holdout_texts.add(text)

    pool_candidates: list[str] = []
    skipped_overlap = 0
    skipped_nonclean = 0
    for line in load_lines(args.clean_pool):
        parsed = parse_fasttext_line(line)
        if parsed is None:
            continue
        labels, text = parsed
        if labels != ["clean"]:
            skipped_nonclean += 1
            continue
        if text in base_texts or text in holdout_texts:
            skipped_overlap += 1
            continue
        pool_candidates.append(text)

    random.seed(args.seed)
    if args.max_clean is not None and args.max_clean < len(pool_candidates):
        pool_candidates = random.sample(pool_candidates, args.max_clean)

    extra_lines = [f"__label__clean {text}" for text in pool_candidates]
    out_lines = base_lines + extra_lines

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for line in out_lines:
            f.write(line + "\n")

    meta = {
        "base": str(args.base),
        "clean_pool": str(args.clean_pool),
        "holdout": str(args.holdout) if args.holdout else None,
        "out": str(args.out),
        "seed": args.seed,
        "max_clean": args.max_clean,
        "base_counts": dict(count_labels(base_lines)),
        "out_counts": dict(count_labels(out_lines)),
        "base_total": len(base_lines),
        "added_clean": len(extra_lines),
        "out_total": len(out_lines),
        "skipped_nonclean": skipped_nonclean,
        "skipped_overlap": skipped_overlap,
        "pool_candidates": len(pool_candidates),
    }
    args.meta_out.parent.mkdir(parents=True, exist_ok=True)
    args.meta_out.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
