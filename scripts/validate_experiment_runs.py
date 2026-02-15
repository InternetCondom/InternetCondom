#!/usr/bin/env python3
"""Validate experiment run manifests and payload files."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

from experiment_artifacts_model import (
    ArtifactModelError,
    IndexFile,
    RunInfo,
    load_json_file,
)

DEFAULT_RUNS_ROOT = Path("~/offline/janitr-experiments/runs").expanduser()
MODEL_SIZE_SUFFIXES = {".onnx", ".bin", ".ftz"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_model_artifact(destination: str) -> bool:
    rel = Path(destination)
    return rel.parts[:1] == ("model",) and rel.suffix in MODEL_SIZE_SUFFIXES


def validate_runs_root(
    *,
    runs_root: Path,
    max_model_bytes: int,
) -> tuple[list[str], str]:
    errors: list[str] = []

    if not runs_root.exists():
        errors.append(f"Runs root not found: {runs_root}")
        return errors, "runs_missing"
    if not runs_root.is_dir():
        errors.append(f"Runs root is not a directory: {runs_root}")
        return errors, "runs_not_dir"

    index_candidates = sorted(runs_root.glob("INDEX*.json"))
    index_path = runs_root / "INDEX.json"
    if not index_path.exists():
        errors.append(f"Missing required index file: {index_path}")
        return errors, "index_missing"
    if len(index_candidates) != 1 or index_candidates[0].name != "INDEX.json":
        names = [path.name for path in index_candidates]
        errors.append(
            "Single-index policy violation. Expected only INDEX.json; "
            f"found: {names if names else 'none'}"
        )

    try:
        index = IndexFile.from_payload(load_json_file(index_path), context="INDEX.json")
    except ArtifactModelError as exc:
        errors.append(str(exc))
        return errors, "index_invalid"

    indexed_run_ids = {run.run_id for run in index.runs}
    run_dirs = sorted(path for path in runs_root.iterdir() if path.is_dir())
    discovered_run_ids = {path.name for path in run_dirs}

    missing_from_fs = sorted(indexed_run_ids - discovered_run_ids)
    extra_on_fs = sorted(discovered_run_ids - indexed_run_ids)
    if missing_from_fs:
        errors.append(
            f"Runs listed in INDEX.json but missing on disk: {missing_from_fs}"
        )
    if extra_on_fs:
        errors.append(
            f"Run directories present but missing from INDEX.json: {extra_on_fs}"
        )

    for run_row in index.runs:
        run_dir = runs_root / run_row.run_id
        if not run_dir.exists():
            continue

        info_path = run_dir / "RUN_INFO.json"
        if not info_path.exists():
            errors.append(f"{run_row.run_id}: missing RUN_INFO.json")
            continue

        try:
            run_info = RunInfo.from_payload(
                load_json_file(info_path),
                context=f"{run_row.run_id}/RUN_INFO.json",
            )
        except ArtifactModelError as exc:
            errors.append(str(exc))
            continue

        if run_info.run_id != run_row.run_id:
            errors.append(
                f"{run_row.run_id}: run_id mismatch in RUN_INFO.json ({run_info.run_id})"
            )

        if run_row.file_count is not None and run_row.file_count != run_info.file_count:
            errors.append(
                f"{run_row.run_id}: index file_count={run_row.file_count} "
                f"!= run file_count={run_info.file_count}"
            )
        if (
            run_row.total_bytes is not None
            and run_row.total_bytes != run_info.total_bytes
        ):
            errors.append(
                f"{run_row.run_id}: index total_bytes={run_row.total_bytes} "
                f"!= run total_bytes={run_info.total_bytes}"
            )
        if (
            run_row.source_run_dir is not None
            and run_info.source_run_dir is not None
            and run_row.source_run_dir != run_info.source_run_dir
        ):
            errors.append(
                f"{run_row.run_id}: index source_run_dir={run_row.source_run_dir} "
                f"!= run source_run_dir={run_info.source_run_dir}"
            )

        allowed_files = {"RUN_INFO.json"}
        for entry in run_info.files:
            rel = Path(entry.destination)
            if rel.is_absolute() or ".." in rel.parts:
                errors.append(
                    f"{run_row.run_id}: invalid destination path {entry.destination}"
                )
                continue

            payload_path = run_dir / rel
            allowed_files.add(rel.as_posix())

            if not payload_path.exists():
                errors.append(
                    f"{run_row.run_id}: missing payload file {rel.as_posix()}"
                )
                continue
            if not payload_path.is_file():
                errors.append(f"{run_row.run_id}: payload is not file {rel.as_posix()}")
                continue

            actual_size = payload_path.stat().st_size
            if actual_size != entry.size_bytes:
                errors.append(
                    f"{run_row.run_id}: size mismatch for {rel.as_posix()} "
                    f"(manifest={entry.size_bytes}, actual={actual_size})"
                )

            actual_sha = sha256(payload_path)
            if actual_sha != entry.sha256:
                errors.append(
                    f"{run_row.run_id}: sha256 mismatch for {rel.as_posix()} "
                    f"(manifest={entry.sha256}, actual={actual_sha})"
                )

            if is_model_artifact(entry.destination) and actual_size > max_model_bytes:
                errors.append(
                    f"{run_row.run_id}: model artifact exceeds limit for {rel.as_posix()} "
                    f"({actual_size} bytes > {max_model_bytes} bytes)"
                )

        for path in sorted(run_dir.rglob("*")):
            rel = path.relative_to(run_dir).as_posix()
            if path.is_file() and rel not in allowed_files:
                errors.append(
                    f"{run_row.run_id}: untracked file not in RUN_INFO.json: {rel}"
                )
            if path.is_dir():
                try:
                    next(path.iterdir())
                except StopIteration:
                    errors.append(f"{run_row.run_id}: empty directory present: {rel}")

    summary = (
        f"Validated runs root: {runs_root} | indexed_runs={len(indexed_run_ids)} | "
        f"errors={len(errors)}"
    )
    return errors, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--max-model-mb", type=int, default=30)
    parser.add_argument(
        "--require-runs-root",
        action="store_true",
        help="Fail if --runs-root does not exist. Default is to skip validation when missing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runs_root = args.runs_root.expanduser()
    max_model_bytes = args.max_model_mb * 1024 * 1024

    if not runs_root.exists():
        if args.require_runs_root:
            print(
                f"[validate_experiment_runs] runs root not found: {runs_root}",
                file=sys.stderr,
            )
            return 2
        print(f"[validate_experiment_runs] skip: runs root not found: {runs_root}")
        return 0

    errors, summary = validate_runs_root(
        runs_root=runs_root,
        max_model_bytes=max_model_bytes,
    )
    if errors:
        print(f"[validate_experiment_runs] {summary}", file=sys.stderr)
        for idx, error in enumerate(errors, start=1):
            print(f"{idx}. {error}", file=sys.stderr)
        return 1

    print(f"[validate_experiment_runs] {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
