#!/usr/bin/env python3
"""Rebuild a single INDEX.json from run-level manifests."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from experiment_artifacts_model import ArtifactModelError, RunInfo, load_json_file

DEFAULT_RUNS_ROOT = Path("~/offline/janitr-experiments/runs").expanduser()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument(
        "--keep-extra-indexes",
        action="store_true",
        help="Do not delete additional INDEX*.json files besides INDEX.json.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runs_root = args.runs_root.expanduser()

    if not runs_root.exists() or not runs_root.is_dir():
        print(
            f"[rebuild_experiment_index] runs root not found: {runs_root}",
            file=sys.stderr,
        )
        return 2

    rows: list[dict[str, object]] = []
    for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
        info_path = run_dir / "RUN_INFO.json"
        if not info_path.exists():
            print(
                f"[rebuild_experiment_index] skipping {run_dir.name}: missing RUN_INFO.json",
                file=sys.stderr,
            )
            continue
        try:
            info = RunInfo.from_payload(
                load_json_file(info_path),
                context=f"{run_dir.name}/RUN_INFO.json",
            )
        except ArtifactModelError as exc:
            print(
                f"[rebuild_experiment_index] invalid {info_path}: {exc}",
                file=sys.stderr,
            )
            return 1

        row: dict[str, object] = {
            "run_id": info.run_id,
            "file_count": info.file_count,
            "total_bytes": info.total_bytes,
        }
        if info.source_run_dir is not None:
            row["source_run_dir"] = info.source_run_dir

        git_date = info.raw.get("git_date")
        if isinstance(git_date, str) and git_date.strip():
            row["git_date"] = git_date
        rows.append(row)

    rows.sort(key=lambda row: str(row["run_id"]))
    index_payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_count": len(rows),
        "runs": rows,
    }

    index_path = runs_root / "INDEX.json"
    index_path.write_text(json.dumps(index_payload, indent=2) + "\n", encoding="utf-8")

    removed: list[str] = []
    if not args.keep_extra_indexes:
        for path in sorted(runs_root.glob("INDEX*.json")):
            if path.name == "INDEX.json":
                continue
            path.unlink()
            removed.append(path.name)

    print(f"[rebuild_experiment_index] wrote {index_path}")
    print(f"[rebuild_experiment_index] runs indexed: {len(rows)}")
    if removed:
        print(f"[rebuild_experiment_index] removed extra index files: {removed}")
    else:
        print("[rebuild_experiment_index] no extra index files removed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
