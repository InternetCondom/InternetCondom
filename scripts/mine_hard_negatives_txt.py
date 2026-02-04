#!/usr/bin/env python3
"""
Mine hard negative clean examples from a fastText dataset.

Selects clean rows with high p(label) and writes them as __label__clean lines.
Optionally appends them to a training file with repetition.
"""

from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DEFAULT_MODEL = REPO_ROOT / "models" / "scam_detector.bin"
DEFAULT_INPUT = REPO_ROOT / "data" / "train.txt"
DEFAULT_OUT = REPO_ROOT / "data" / "hard_negatives.txt"

from evaluate import get_scores, parse_line  # type: ignore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="Model file")
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT, help="Input fastText txt"
    )
    parser.add_argument(
        "--label", type=str, default="scam", help="Label to mine against"
    )
    parser.add_argument(
        "--top-n", type=int, default=200, help="Top N clean examples by score (0 = all)"
    )
    parser.add_argument(
        "--threshold", type=float, default=None, help="Minimum score to include"
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT, help="Output hard negatives txt"
    )
    parser.add_argument(
        "--train-in", type=Path, default=None, help="Optional base training txt"
    )
    parser.add_argument(
        "--train-out", type=Path, default=None, help="Optional output training txt"
    )
    parser.add_argument(
        "--mult",
        type=int,
        default=3,
        help="Repeat hard negatives N times when appending",
    )
    args = parser.parse_args()

    if not args.model.exists():
        raise SystemExit(f"Model file not found: {args.model}")
    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")
    if args.top_n < 0:
        raise SystemExit("--top-n must be >= 0")
    if args.mult < 1:
        raise SystemExit("--mult must be >= 1")
    if (args.train_in is None) != (args.train_out is None):
        raise SystemExit("--train-in and --train-out must be provided together")

    try:
        import fasttext  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "fasttext is not installed. Install with: pip install fasttext-wheel"
        ) from exc

    model = fasttext.load_model(str(args.model))

    scored: list[tuple[float, str]] = []
    total_clean = 0
    with args.input.open("r", encoding="utf-8") as f:
        for line in f:
            parsed = parse_line(line)
            if parsed is None:
                continue
            labels, text = parsed
            if labels != {"clean"}:
                continue
            total_clean += 1
            scores = get_scores(model, text)
            score = float(scores.get(args.label, 0.0))
            if args.threshold is not None and score < args.threshold:
                continue
            scored.append((score, text))

    if not scored:
        raise SystemExit("No hard negatives found.")

    scored.sort(key=lambda row: row[0], reverse=True)
    if args.top_n:
        scored = scored[: args.top_n]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for score, text in scored:
            f.write(f"__label__clean {text}\n")

    if args.train_in and args.train_out:
        if not args.train_in.exists():
            raise SystemExit(f"Training file not found: {args.train_in}")
        args.train_out.parent.mkdir(parents=True, exist_ok=True)
        with args.train_out.open("w", encoding="utf-8") as out_f:
            with args.train_in.open("r", encoding="utf-8") as in_f:
                for line in in_f:
                    out_f.write(line)
            for _ in range(args.mult):
                for score, text in scored:
                    out_f.write(f"__label__clean {text}\n")

    min_score = scored[-1][0] if scored else 0.0
    max_score = scored[0][0] if scored else 0.0
    avg_score = sum(score for score, _ in scored) / len(scored)
    print(f"Scored clean rows: {total_clean}")
    print(f"Selected hard negatives: {len(scored)}")
    print(f"Score range: min={min_score:.4f} max={max_score:.4f} avg={avg_score:.4f}")
    print(f"Wrote hard negatives to {args.out}")
    if args.train_out:
        print(f"Wrote augmented training file to {args.train_out} (mult={args.mult})")


if __name__ == "__main__":
    main()
