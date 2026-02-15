#!/usr/bin/env python3
"""Sync X-posts/X-replies datasets into experiments repo with hash-based dedupe."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from run_naming import resolve_run_name

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DEST_ROOT = Path("~/offline/janitr-experiments").expanduser()
DEFAULT_X_POSTS_SOURCE = REPO_ROOT / "data" / "sample.jsonl"
DEFAULT_X_REPLIES_SOURCE = REPO_ROOT / "data" / "replies.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest-root", type=Path, default=DEFAULT_DEST_ROOT)
    parser.add_argument("--x-posts-source", type=Path, default=DEFAULT_X_POSTS_SOURCE)
    parser.add_argument(
        "--x-replies-source", type=Path, default=DEFAULT_X_REPLIES_SOURCE
    )
    parser.add_argument(
        "--snapshot-name",
        type=str,
        default=None,
        help="Optional name. Defaults to yyyy-mm-dd-<petname>.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allow-non-git",
        action="store_true",
        help="Allow destination root that is not a git repository.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def current_git_commit() -> str | None:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    commit = out.stdout.strip()
    return commit if out.returncode == 0 and commit else None


def ensure_dest_repo(dest_root: Path, *, allow_non_git: bool) -> None:
    if not dest_root.exists():
        raise FileNotFoundError(f"Destination root does not exist: {dest_root}")
    if allow_non_git:
        return
    if not (dest_root / ".git").exists():
        raise RuntimeError(
            f"Destination is not a git repository: {dest_root}\n"
            "Use --allow-non-git to bypass this check."
        )


def ensure_snapshot_id_unique(
    *,
    base_id: str,
    snapshots_root: Path,
    existing_ids: set[str],
) -> str:
    run_id = base_id
    idx = 2
    while run_id in existing_ids or (snapshots_root / run_id).exists():
        run_id = f"{base_id}-v{idx}"
        idx += 1
    return run_id


def main() -> int:
    args = parse_args()
    dest_root = args.dest_root.expanduser()
    x_posts_source = args.x_posts_source.expanduser()
    x_replies_source = args.x_replies_source.expanduser()

    try:
        ensure_dest_repo(dest_root, allow_non_git=args.allow_non_git)
    except Exception as exc:
        print(f"[sync_datasets] error: {exc}", file=sys.stderr)
        return 2

    for source in (x_posts_source, x_replies_source):
        if not source.exists():
            print(f"[sync_datasets] error: source missing: {source}", file=sys.stderr)
            return 2
        if not source.is_file():
            print(
                f"[sync_datasets] error: source is not a file: {source}",
                file=sys.stderr,
            )
            return 2

    datasets_root = dest_root / "datasets"
    snapshots_root = datasets_root / "snapshots"
    index_path = datasets_root / "INDEX.json"

    x_posts_sha = sha256_file(x_posts_source)
    x_replies_sha = sha256_file(x_replies_source)
    combined_sha = stable_sha256_text(f"{x_posts_sha}:{x_replies_sha}")

    if index_path.exists():
        try:
            index_payload = load_json(index_path)
        except Exception as exc:
            print(
                f"[sync_datasets] error: invalid {index_path}: {exc}", file=sys.stderr
            )
            return 2
    else:
        index_payload = {
            "schema_version": 1,
            "generated_at_utc": utc_now_iso(),
            "snapshots": [],
        }

    snapshots = index_payload.get("snapshots", [])
    if not isinstance(snapshots, list):
        print(
            f"[sync_datasets] error: {index_path} snapshots must be an array",
            file=sys.stderr,
        )
        return 2

    for snapshot in snapshots:
        if not isinstance(snapshot, dict):
            continue
        if snapshot.get("combined_sha256") == combined_sha:
            snapshot_id = snapshot.get("snapshot_id", "<unknown>")
            print(
                "[sync_datasets] no changes detected; dataset snapshot already exists"
            )
            print(f"[sync_datasets] snapshot_id: {snapshot_id}")
            print(f"[sync_datasets] combined_sha256: {combined_sha}")
            return 0

    base_id = resolve_run_name(args.snapshot_name)
    existing_ids = {
        str(snapshot.get("snapshot_id"))
        for snapshot in snapshots
        if isinstance(snapshot, dict) and snapshot.get("snapshot_id")
    }
    snapshot_id = ensure_snapshot_id_unique(
        base_id=base_id,
        snapshots_root=snapshots_root,
        existing_ids=existing_ids,
    )
    snapshot_dir = snapshots_root / snapshot_id

    snapshot_entry = {
        "snapshot_id": snapshot_id,
        "created_at_utc": utc_now_iso(),
        "combined_sha256": combined_sha,
        "source_commit": current_git_commit(),
        "files": {
            "x-posts": {
                "source": str(x_posts_source),
                "size_bytes": x_posts_source.stat().st_size,
                "sha256": x_posts_sha,
                "destination": f"datasets/snapshots/{snapshot_id}/x-posts.jsonl",
            },
            "x-replies": {
                "source": str(x_replies_source),
                "size_bytes": x_replies_source.stat().st_size,
                "sha256": x_replies_sha,
                "destination": f"datasets/snapshots/{snapshot_id}/x-replies.jsonl",
            },
        },
    }

    if args.dry_run:
        print(f"[dry-run] would create snapshot: {snapshot_id}")
        print(
            f"[dry-run] x-posts: {x_posts_source} -> {snapshot_dir / 'x-posts.jsonl'}"
        )
        print(
            f"[dry-run] x-replies: {x_replies_source} -> {snapshot_dir / 'x-replies.jsonl'}"
        )
        return 0

    snapshot_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(x_posts_source, snapshot_dir / "x-posts.jsonl")
    shutil.copy2(x_replies_source, snapshot_dir / "x-replies.jsonl")
    save_json(snapshot_dir / "SNAPSHOT.json", snapshot_entry)

    snapshots.append(snapshot_entry)
    index_payload["schema_version"] = 1
    index_payload["generated_at_utc"] = utc_now_iso()
    index_payload["snapshot_count"] = len(snapshots)
    save_json(index_path, index_payload)

    print(f"[sync_datasets] created snapshot: {snapshot_id}")
    print(f"[sync_datasets] x_posts_sha256: {x_posts_sha}")
    print(f"[sync_datasets] x_replies_sha256: {x_replies_sha}")
    print(f"[sync_datasets] combined_sha256: {combined_sha}")
    print(f"[sync_datasets] wrote: {snapshot_dir}")
    print(f"[sync_datasets] wrote: {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
