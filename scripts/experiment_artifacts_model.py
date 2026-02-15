#!/usr/bin/env python3
"""Data model and structural validation for experiment artifact manifests."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ArtifactModelError(ValueError):
    """Raised when manifest payload does not match expected structure."""


def _expect_mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ArtifactModelError(
            f"{context}: expected object, got {type(value).__name__}"
        )
    return value


def _expect_str(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ArtifactModelError(f"{context}: expected non-empty string")
    return value


def _expect_int(value: Any, context: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ArtifactModelError(f"{context}: expected integer")
    return value


def _expect_nonneg_int(value: Any, context: str) -> int:
    number = _expect_int(value, context)
    if number < 0:
        raise ArtifactModelError(f"{context}: expected non-negative integer")
    return number


def _optional_nonneg_int(value: Any, context: str) -> int | None:
    if value is None:
        return None
    return _expect_nonneg_int(value, context)


def _optional_str(value: Any, context: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ArtifactModelError(f"{context}: expected string or null")
    return value


@dataclass(frozen=True)
class FileEntry:
    source: str | None
    destination: str
    size_bytes: int
    sha256: str

    @classmethod
    def from_payload(cls, payload: Any, *, context: str) -> "FileEntry":
        obj = _expect_mapping(payload, context)
        source = _optional_str(obj.get("source"), f"{context}.source")
        destination = _expect_str(obj.get("destination"), f"{context}.destination")
        size_bytes = _expect_nonneg_int(obj.get("size_bytes"), f"{context}.size_bytes")
        sha256 = _expect_str(obj.get("sha256"), f"{context}.sha256").lower()
        if not SHA256_RE.match(sha256):
            raise ArtifactModelError(f"{context}.sha256: expected 64-char hex digest")
        return cls(
            source=source,
            destination=destination,
            size_bytes=size_bytes,
            sha256=sha256,
        )


@dataclass(frozen=True)
class RunInfo:
    schema_version: int
    run_id: str
    source_run_dir: str | None
    file_count: int
    total_bytes: int
    files: tuple[FileEntry, ...]
    raw: Mapping[str, Any]

    @classmethod
    def from_payload(cls, payload: Any, *, context: str) -> "RunInfo":
        obj = _expect_mapping(payload, context)
        schema_version = _expect_nonneg_int(
            obj.get("schema_version"), f"{context}.schema_version"
        )
        run_id = _expect_str(obj.get("run_id"), f"{context}.run_id")
        source_run_dir = _optional_str(
            obj.get("source_run_dir"), f"{context}.source_run_dir"
        )
        file_count = _expect_nonneg_int(obj.get("file_count"), f"{context}.file_count")
        total_bytes = _expect_nonneg_int(
            obj.get("total_bytes"), f"{context}.total_bytes"
        )

        files_payload = obj.get("files")
        if not isinstance(files_payload, list):
            raise ArtifactModelError(f"{context}.files: expected array")
        files = tuple(
            FileEntry.from_payload(item, context=f"{context}.files[{idx}]")
            for idx, item in enumerate(files_payload)
        )

        computed_count = len(files)
        if file_count != computed_count:
            raise ArtifactModelError(
                f"{context}.file_count: expected {computed_count} from files array, got {file_count}"
            )

        computed_bytes = sum(file.size_bytes for file in files)
        if total_bytes != computed_bytes:
            raise ArtifactModelError(
                f"{context}.total_bytes: expected {computed_bytes} from files array, got {total_bytes}"
            )

        return cls(
            schema_version=schema_version,
            run_id=run_id,
            source_run_dir=source_run_dir,
            file_count=file_count,
            total_bytes=total_bytes,
            files=files,
            raw=obj,
        )


@dataclass(frozen=True)
class IndexRun:
    run_id: str
    source_run_dir: str | None
    file_count: int | None
    total_bytes: int | None
    raw: Mapping[str, Any]

    @classmethod
    def from_payload(cls, payload: Any, *, context: str) -> "IndexRun":
        obj = _expect_mapping(payload, context)
        run_id = _expect_str(obj.get("run_id"), f"{context}.run_id")
        source_run_dir = _optional_str(
            obj.get("source_run_dir"), f"{context}.source_run_dir"
        )
        file_count = _optional_nonneg_int(
            obj.get("file_count"), f"{context}.file_count"
        )
        total_bytes = _optional_nonneg_int(
            obj.get("total_bytes"), f"{context}.total_bytes"
        )
        return cls(
            run_id=run_id,
            source_run_dir=source_run_dir,
            file_count=file_count,
            total_bytes=total_bytes,
            raw=obj,
        )


@dataclass(frozen=True)
class IndexFile:
    schema_version: int
    run_count: int
    runs: tuple[IndexRun, ...]
    raw: Mapping[str, Any]

    @classmethod
    def from_payload(cls, payload: Any, *, context: str = "INDEX.json") -> "IndexFile":
        obj = _expect_mapping(payload, context)
        schema_version = _expect_nonneg_int(
            obj.get("schema_version"), f"{context}.schema_version"
        )
        run_count = _expect_nonneg_int(obj.get("run_count"), f"{context}.run_count")

        runs_payload = obj.get("runs")
        if not isinstance(runs_payload, list):
            raise ArtifactModelError(f"{context}.runs: expected array")
        runs = tuple(
            IndexRun.from_payload(item, context=f"{context}.runs[{idx}]")
            for idx, item in enumerate(runs_payload)
        )

        if run_count != len(runs):
            raise ArtifactModelError(
                f"{context}.run_count: expected {len(runs)} from runs array, got {run_count}"
            )

        run_ids = [run.run_id for run in runs]
        duplicate_ids = sorted(
            {run_id for run_id in run_ids if run_ids.count(run_id) > 1}
        )
        if duplicate_ids:
            raise ArtifactModelError(
                f"{context}: duplicate run_id entries: {duplicate_ids}"
            )

        return cls(
            schema_version=schema_version,
            run_count=run_count,
            runs=runs,
            raw=obj,
        )


def load_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArtifactModelError(f"{path}: invalid JSON ({exc})") from exc
