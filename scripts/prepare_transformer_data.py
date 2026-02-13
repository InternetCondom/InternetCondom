#!/usr/bin/env python3
"""Prepare transformer-ready JSONL splits from Janitr data/*.jsonl inputs."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from transformer_common import (
    DATA_DIR,
    PreparedRecord,
    load_jsonl,
    record_from_sample,
    write_jsonl,
)

DEFAULT_TRAIN_IN = DATA_DIR / "train.jsonl"
DEFAULT_VALID_IN = DATA_DIR / "valid.jsonl"
DEFAULT_HOLDOUT_IN = DATA_DIR / "holdout.jsonl"
DEFAULT_OUT_DIR = DATA_DIR / "transformer"


def to_payload(record: PreparedRecord) -> dict:
    return {
        "id": record.id,
        "text": record.text,
        "text_normalized": record.text_normalized,
        "labels": record.labels,
        "raw_labels": record.raw_labels,
        "collapsed_label": record.collapsed_label,
        "y_scam_clean": record.y_scam_clean,
        "y_topics": record.y_topics,
        "has_url": record.has_url,
        "author_handle": record.author_handle,
    }


def prepare_split(
    in_path: Path,
    out_path: Path,
    *,
    normalize: bool,
    lowercase: bool,
    strip_urls: bool,
) -> tuple[int, int, Counter[str]]:
    samples = load_jsonl(in_path)
    rows: list[dict] = []
    skipped = 0
    counts: Counter[str] = Counter()

    for sample in samples:
        record = record_from_sample(
            sample,
            normalize=normalize,
            lowercase=lowercase,
            strip_urls=strip_urls,
        )
        if record is None:
            skipped += 1
            continue
        rows.append(to_payload(record))
        counts[record.collapsed_label] += 1

    write_jsonl(out_path, rows)
    return len(rows), skipped, counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-in", type=Path, default=DEFAULT_TRAIN_IN)
    parser.add_argument("--valid-in", type=Path, default=DEFAULT_VALID_IN)
    parser.add_argument("--holdout-in", type=Path, default=DEFAULT_HOLDOUT_IN)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--no-normalize", action="store_true")
    parser.add_argument("--no-lowercase", action="store_true")
    parser.add_argument("--strip-urls", action="store_true")
    args = parser.parse_args()

    splits = {
        "train": (args.train_in, args.out_dir / "train.prepared.jsonl"),
        "valid": (args.valid_in, args.out_dir / "valid.prepared.jsonl"),
        "holdout": (args.holdout_in, args.out_dir / "holdout.prepared.jsonl"),
    }

    for name, (in_path, out_path) in splits.items():
        if not in_path.exists():
            raise SystemExit(f"Input split not found for {name}: {in_path}")
        kept, skipped, counts = prepare_split(
            in_path,
            out_path,
            normalize=not args.no_normalize,
            lowercase=not args.no_lowercase,
            strip_urls=args.strip_urls,
        )
        print(
            f"[{name}] wrote {kept} rows to {out_path} (skipped_empty={skipped}, "
            f"label_counts={dict(counts)})"
        )


if __name__ == "__main__":
    main()
