#!/usr/bin/env python3
"""
Create deterministic time-based train/calib/holdout splits from JSONL.

Outputs fastText-formatted .txt and JSONL files for each split, plus metadata.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DEFAULT_INPUT = REPO_ROOT / "data" / "train_valid.jsonl"
DEFAULT_TRAIN_JSONL = REPO_ROOT / "data" / "train_time.jsonl"
DEFAULT_CALIB_JSONL = REPO_ROOT / "data" / "calib.jsonl"
DEFAULT_HOLDOUT_JSONL = REPO_ROOT / "data" / "holdout_time.jsonl"
DEFAULT_TRAIN_TXT = REPO_ROOT / "data" / "train_time.txt"
DEFAULT_CALIB_TXT = REPO_ROOT / "data" / "calib.txt"
DEFAULT_HOLDOUT_TXT = REPO_ROOT / "data" / "holdout_time.txt"
DEFAULT_META = REPO_ROOT / "data" / "time_split_meta.json"

from prepare_data import clean_text, extract_labels  # type: ignore


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        text = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for obj in rows:
            f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_fasttext(path: Path, rows: list[tuple[list[str], str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for labels, text in rows:
            if not labels:
                continue
            prefix = " ".join(f"__label__{label}" for label in labels)
            f.write(f"{prefix} {text}\n")


def count_from_ratio(total: int, ratio: float) -> int:
    if ratio <= 0:
        return 0
    return max(1, int(total * ratio))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create time-based train/calib/holdout splits"
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT, help="Input JSONL file"
    )
    parser.add_argument("--train-jsonl", type=Path, default=DEFAULT_TRAIN_JSONL)
    parser.add_argument("--calib-jsonl", type=Path, default=DEFAULT_CALIB_JSONL)
    parser.add_argument("--holdout-jsonl", type=Path, default=DEFAULT_HOLDOUT_JSONL)
    parser.add_argument("--train-txt", type=Path, default=DEFAULT_TRAIN_TXT)
    parser.add_argument("--calib-txt", type=Path, default=DEFAULT_CALIB_TXT)
    parser.add_argument("--holdout-txt", type=Path, default=DEFAULT_HOLDOUT_TXT)
    parser.add_argument("--meta-out", type=Path, default=DEFAULT_META)
    parser.add_argument("--holdout-ratio", type=float, default=0.1)
    parser.add_argument("--calib-ratio", type=float, default=0.1)
    parser.add_argument(
        "--strip-urls", action="store_true", help="Remove URLs from text"
    )
    parser.add_argument(
        "--no-normalize", action="store_true", help="Disable Unicode normalization"
    )
    parser.add_argument(
        "--no-lowercase", action="store_true", help="Disable lowercasing"
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")
    if args.holdout_ratio < 0 or args.calib_ratio < 0:
        raise SystemExit("Ratios must be >= 0")

    records: list[tuple[datetime | None, str, dict, list[str], str]] = []
    with args.input.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            labels = extract_labels(obj)
            if not labels:
                continue
            text = obj.get("text") or obj.get("raw_text") or ""
            cleaned = clean_text(
                text,
                normalize=not args.no_normalize,
                lowercase=not args.no_lowercase,
                strip_urls=args.strip_urls,
            )
            if not cleaned:
                continue
            ts = parse_time(obj.get("collected_at"))
            id_ = str(obj.get("id", ""))
            records.append((ts, id_, obj, labels, cleaned))

    if not records:
        raise SystemExit("No valid records found.")

    min_dt = datetime.min.replace(tzinfo=timezone.utc)
    records.sort(key=lambda row: (row[0] or min_dt, row[1]))

    total = len(records)
    holdout_count = count_from_ratio(total, args.holdout_ratio)
    calib_count = count_from_ratio(total, args.calib_ratio)
    if holdout_count + calib_count >= total:
        raise SystemExit("holdout+calib splits leave no training data. Adjust ratios.")

    split_holdout = total - holdout_count
    split_calib = split_holdout - calib_count

    train = records[:split_calib]
    calib = records[split_calib:split_holdout]
    holdout = records[split_holdout:]

    def build_rows(chunk):
        rows_txt: list[tuple[list[str], str]] = []
        rows_jsonl: list[dict] = []
        for _, _, obj, labels, cleaned in chunk:
            clone = dict(obj)
            clone["labels"] = labels
            clone.pop("label", None)
            rows_jsonl.append(clone)
            rows_txt.append((labels, cleaned))
        return rows_jsonl, rows_txt

    train_jsonl, train_txt = build_rows(train)
    calib_jsonl, calib_txt = build_rows(calib)
    holdout_jsonl, holdout_txt = build_rows(holdout)

    write_jsonl(args.train_jsonl, train_jsonl)
    write_jsonl(args.calib_jsonl, calib_jsonl)
    write_jsonl(args.holdout_jsonl, holdout_jsonl)

    write_fasttext(args.train_txt, train_txt)
    write_fasttext(args.calib_txt, calib_txt)
    write_fasttext(args.holdout_txt, holdout_txt)

    meta = {
        "input": str(args.input),
        "train_jsonl": str(args.train_jsonl),
        "calib_jsonl": str(args.calib_jsonl),
        "holdout_jsonl": str(args.holdout_jsonl),
        "train_txt": str(args.train_txt),
        "calib_txt": str(args.calib_txt),
        "holdout_txt": str(args.holdout_txt),
        "holdout_ratio": args.holdout_ratio,
        "calib_ratio": args.calib_ratio,
        "total": total,
        "train_count": len(train),
        "calib_count": len(calib),
        "holdout_count": len(holdout),
        "last_train_collected_at": train[-1][0].isoformat()
        if train and train[-1][0]
        else None,
        "first_calib_collected_at": calib[0][0].isoformat()
        if calib and calib[0][0]
        else None,
        "last_calib_collected_at": calib[-1][0].isoformat()
        if calib and calib[-1][0]
        else None,
        "first_holdout_collected_at": holdout[0][0].isoformat()
        if holdout and holdout[0][0]
        else None,
    }
    args.meta_out.parent.mkdir(parents=True, exist_ok=True)
    args.meta_out.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote train JSONL to {args.train_jsonl}")
    print(f"Wrote calib JSONL to {args.calib_jsonl}")
    print(f"Wrote holdout JSONL to {args.holdout_jsonl}")
    print(f"Wrote train TXT to {args.train_txt}")
    print(f"Wrote calib TXT to {args.calib_txt}")
    print(f"Wrote holdout TXT to {args.holdout_txt}")
    print(f"Wrote metadata to {args.meta_out}")
    print(
        f"Counts: train={len(train)} calib={len(calib)} holdout={len(holdout)} total={total}"
    )


if __name__ == "__main__":
    main()
