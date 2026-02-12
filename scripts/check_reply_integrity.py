#!/usr/bin/env python3
"""
Dataset integrity checks for replies.jsonl.

Checks:
1. Valid JSON on every line
2. Required reply/context fields present
3. No duplicate IDs (excluding null)
4. Valid label values
5. Required reply_author/parent_author metadata for heuristics
6. Parent/reply consistency checks
7. Optional thread_context structure checks
8. Basic type checks for optional metrics and arrays

Exit codes:
- 0: All checks passed
- 1: Errors found
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from labelset import load_v2026_labels_from_labels_md

VALID_LABELS = set(load_v2026_labels_from_labels_md())
RECORD_ID_PATTERN = re.compile(
    r"^\d{16,20}$|^x_reply_\d+(_dup\d+)?$|^xr_\d+(_dup\d+)?$"
)
SOURCE_ID_PATTERN = re.compile(r"^\d{16,20}$|^x_[a-zA-Z0-9_]+$")
TWEET_STATUS_ID_PATTERN = re.compile(r"^\d{16,20}$")
CONTEXT_TYPES = {"parent", "ancestor", "conversation_root", "sibling_reply"}
METRIC_FIELDS = {
    "like_count",
    "reply_count",
    "repost_count",
    "quote_count",
    "bookmark_count",
    "view_count",
}


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_non_negative_int(value: object) -> bool:
    return isinstance(value, int) and value >= 0


def _is_tweet_status_id(value: object) -> bool:
    return isinstance(value, str) and bool(TWEET_STATUS_ID_PATTERN.fullmatch(value))


def _is_iso_datetime(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


def _validate_metrics(
    metrics: object,
    field_name: str,
    line_num: int,
    record_id: object,
    errors: list[str],
    warnings: list[str],
) -> None:
    if not isinstance(metrics, dict):
        errors.append(
            f"Line {line_num} (id={record_id}): '{field_name}' must be an object"
        )
        return

    for key, value in metrics.items():
        if key not in METRIC_FIELDS:
            warnings.append(
                f"Line {line_num} (id={record_id}): '{field_name}' contains unknown metric '{key}'"
            )
            continue
        if not _is_non_negative_int(value):
            errors.append(
                f"Line {line_num} (id={record_id}): '{field_name}.{key}' must be a non-negative integer"
            )


def _validate_author(
    author: object,
    field_name: str,
    line_num: int,
    record_id: object,
    errors: list[str],
    warnings: list[str],
) -> None:
    if not isinstance(author, dict):
        errors.append(
            f"Line {line_num} (id={record_id}): '{field_name}' must be an object"
        )
        return

    handle = author.get("handle")
    if not _is_non_empty_string(handle):
        errors.append(
            f"Line {line_num} (id={record_id}): '{field_name}.handle' must be a non-empty string"
        )
    elif isinstance(handle, str) and handle.startswith("@"):
        errors.append(
            f"Line {line_num} (id={record_id}): '{field_name}.handle' should not include @"
        )

    if not isinstance(author.get("verified"), bool):
        errors.append(
            f"Line {line_num} (id={record_id}): '{field_name}.verified' must be a boolean"
        )

    for int_field in ("follower_count", "following_count"):
        if not _is_non_negative_int(author.get(int_field)):
            errors.append(
                f"Line {line_num} (id={record_id}): '{field_name}.{int_field}' must be a non-negative integer"
            )

    bio = author.get("bio")
    if not isinstance(bio, str):
        errors.append(
            f"Line {line_num} (id={record_id}): '{field_name}.bio' must be a string"
        )
    elif not bio.strip():
        warnings.append(
            f"Line {line_num} (id={record_id}): '{field_name}.bio' is empty"
        )

    created_at = author.get("created_at")
    if not _is_iso_datetime(created_at):
        errors.append(
            f"Line {line_num} (id={record_id}): '{field_name}.created_at' must be an ISO 8601 timestamp"
        )

    if "user_id" in author and not isinstance(author["user_id"], str):
        errors.append(
            f"Line {line_num} (id={record_id}): '{field_name}.user_id' must be a string"
        )

    if "display_name" in author and not isinstance(author["display_name"], str):
        errors.append(
            f"Line {line_num} (id={record_id}): '{field_name}.display_name' must be a string"
        )

    for opt_int_field in ("tweet_count", "listed_count"):
        if opt_int_field in author and not _is_non_negative_int(author[opt_int_field]):
            errors.append(
                f"Line {line_num} (id={record_id}): '{field_name}.{opt_int_field}' must be a non-negative integer"
            )

    if "profile_collected_at" in author and not _is_iso_datetime(
        author["profile_collected_at"]
    ):
        errors.append(
            f"Line {line_num} (id={record_id}): '{field_name}.profile_collected_at' must be an ISO 8601 timestamp"
        )


def _validate_thread_context(
    thread_context: object,
    line_num: int,
    record_id: object,
    parent_id: object,
    source_id: object,
    errors: list[str],
    warnings: list[str],
) -> None:
    if not isinstance(thread_context, list):
        errors.append(
            f"Line {line_num} (id={record_id}): 'thread_context' must be an array"
        )
        return

    seen_source_ids: set[str] = set()

    for idx, item in enumerate(thread_context):
        item_idx = idx + 1
        item_prefix = f"Line {line_num} (id={record_id}) thread_context[{item_idx}]"

        if not isinstance(item, dict):
            errors.append(f"{item_prefix}: item must be an object")
            continue

        context_source_id = item.get("source_id")
        if not _is_non_empty_string(context_source_id):
            errors.append(f"{item_prefix}: 'source_id' must be a non-empty string")
        else:
            context_source_id = context_source_id.strip()
            if context_source_id in seen_source_ids:
                warnings.append(
                    f"{item_prefix}: duplicate context source_id '{context_source_id}'"
                )
            seen_source_ids.add(context_source_id)
            if context_source_id == source_id:
                errors.append(
                    f"{item_prefix}: context source_id cannot equal reply source_id"
                )
            if context_source_id == parent_id and item.get("context_type") != "parent":
                warnings.append(
                    f"{item_prefix}: source_id matches parent_id but context_type is not 'parent'"
                )

        context_type = item.get("context_type")
        if context_type not in CONTEXT_TYPES:
            errors.append(
                f"{item_prefix}: 'context_type' must be one of {sorted(CONTEXT_TYPES)}"
            )
        elif context_type == "parent" and context_source_id != parent_id:
            errors.append(
                f"{item_prefix}: context_type='parent' must use source_id equal to parent_id"
            )

        distance = item.get("distance")
        if not isinstance(distance, int) or distance < 1:
            errors.append(f"{item_prefix}: 'distance' must be an integer >= 1")

        text = item.get("text")
        if not isinstance(text, str):
            errors.append(f"{item_prefix}: 'text' must be a string")
        elif not text.strip():
            warnings.append(f"{item_prefix}: empty text")

        author_handle = item.get("author_handle")
        if not _is_non_empty_string(author_handle):
            errors.append(f"{item_prefix}: 'author_handle' must be a non-empty string")
        elif isinstance(author_handle, str) and author_handle.startswith("@"):
            errors.append(f"{item_prefix}: 'author_handle' should not include @")

        if "author_id" in item and not isinstance(item["author_id"], str):
            errors.append(f"{item_prefix}: 'author_id' must be a string")

        if "source_url" in item and not isinstance(item["source_url"], str):
            errors.append(f"{item_prefix}: 'source_url' must be a string")

        if "created_at" in item and not _is_iso_datetime(item["created_at"]):
            errors.append(f"{item_prefix}: 'created_at' must be an ISO 8601 timestamp")

        if "public_metrics" in item:
            _validate_metrics(
                item["public_metrics"],
                f"thread_context[{item_idx}].public_metrics",
                line_num,
                record_id,
                errors,
                warnings,
            )


def check_integrity(path: Path) -> tuple[list[str], list[str]]:
    """Run all integrity checks. Returns (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    id_counts: defaultdict[object, list[int]] = defaultdict(list)

    try:
        with path.open(encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    warnings.append(f"Line {line_num}: Empty line")
                    continue

                # Check 1: valid JSON
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    errors.append(f"Line {line_num}: Invalid JSON - {e}")
                    continue

                # Required fields
                id_ = obj.get("id")
                platform = obj.get("platform")
                source_id = obj.get("source_id")
                collected_at = obj.get("collected_at")
                text = obj.get("text")
                labels = obj.get("labels")
                is_reply = obj.get("is_reply")
                parent_id = obj.get("parent_id")
                parent_text = obj.get("parent_text")
                reply_author = obj.get("reply_author")
                parent_author = obj.get("parent_author")

                # Check 2: required fields and basic types
                if platform != "x":
                    errors.append(
                        f"Line {line_num} (id={id_}): 'platform' must be 'x' for replies dataset"
                    )

                if not _is_non_empty_string(source_id):
                    errors.append(
                        f"Line {line_num} (id={id_}): Missing or invalid 'source_id'"
                    )

                if not _is_iso_datetime(collected_at):
                    errors.append(
                        f"Line {line_num} (id={id_}): Missing or invalid 'collected_at' (ISO 8601 required)"
                    )

                if text is None:
                    errors.append(f"Line {line_num} (id={id_}): Missing 'text' field")
                elif not isinstance(text, str):
                    errors.append(
                        f"Line {line_num} (id={id_}): 'text' must be a string"
                    )
                elif not text.strip():
                    warnings.append(f"Line {line_num} (id={id_}): Empty text")

                if labels is None:
                    errors.append(f"Line {line_num} (id={id_}): Missing 'labels' field")
                elif not isinstance(labels, list) or not labels:
                    errors.append(
                        f"Line {line_num} (id={id_}): 'labels' must be a non-empty list"
                    )

                if is_reply is not True:
                    errors.append(
                        f"Line {line_num} (id={id_}): 'is_reply' must be true for reply dataset"
                    )

                if not _is_non_empty_string(parent_id):
                    errors.append(
                        f"Line {line_num} (id={id_}): Missing or invalid 'parent_id'"
                    )

                if parent_text is None:
                    errors.append(
                        f"Line {line_num} (id={id_}): Missing 'parent_text' field"
                    )
                elif not isinstance(parent_text, str):
                    errors.append(
                        f"Line {line_num} (id={id_}): 'parent_text' must be a string"
                    )
                elif not parent_text.strip():
                    warnings.append(f"Line {line_num} (id={id_}): Empty parent_text")

                if reply_author is None:
                    errors.append(
                        f"Line {line_num} (id={id_}): Missing 'reply_author' field"
                    )
                else:
                    _validate_author(
                        reply_author,
                        "reply_author",
                        line_num,
                        id_,
                        errors,
                        warnings,
                    )

                if parent_author is None:
                    errors.append(
                        f"Line {line_num} (id={id_}): Missing 'parent_author' field"
                    )
                else:
                    _validate_author(
                        parent_author,
                        "parent_author",
                        line_num,
                        id_,
                        errors,
                        warnings,
                    )

                # Check 3: track IDs for duplicate detection
                if id_ is not None:
                    id_counts[id_].append(line_num)
                    if not isinstance(id_, str):
                        errors.append(
                            f"Line {line_num}: 'id' must be a string or null (got {type(id_).__name__})"
                        )
                else:
                    warnings.append(f"Line {line_num}: Null ID")

                # Check 4: valid labels
                if labels is not None and isinstance(labels, list):
                    if len(labels) != len(set(labels)):
                        errors.append(
                            f"Line {line_num} (id={id_}): Duplicate labels (labels={labels})"
                        )
                    for label in labels:
                        if label not in VALID_LABELS:
                            errors.append(
                                f"Line {line_num} (id={id_}): Invalid label '{label}' (valid: {VALID_LABELS})"
                            )

                # Check 5: id/source_id consistency and source format
                if isinstance(id_, str) and not RECORD_ID_PATTERN.match(id_):
                    warnings.append(f"Line {line_num}: Non-standard ID format '{id_}'")

                if isinstance(source_id, str) and not SOURCE_ID_PATTERN.match(
                    source_id
                ):
                    warnings.append(
                        f"Line {line_num} (id={id_}): Non-standard source_id format '{source_id}'"
                    )

                if isinstance(parent_id, str) and not SOURCE_ID_PATTERN.match(
                    parent_id
                ):
                    warnings.append(
                        f"Line {line_num} (id={id_}): Non-standard parent_id format '{parent_id}'"
                    )

                source_is_status_id = _is_tweet_status_id(source_id)
                id_is_status_id = _is_tweet_status_id(id_)

                if source_is_status_id and id_ != source_id:
                    errors.append(
                        f"Line {line_num}: Numeric source_id must match id (id={id_}, source_id={source_id})"
                    )
                elif id_is_status_id and source_id is not None and source_id != id_:
                    errors.append(
                        f"Line {line_num}: Numeric id must match source_id when source_id is present (id={id_}, source_id={source_id})"
                    )

                if (
                    isinstance(source_id, str)
                    and isinstance(parent_id, str)
                    and source_id == parent_id
                ):
                    errors.append(
                        f"Line {line_num} (id={id_}): 'source_id' and 'parent_id' cannot be the same"
                    )

                # Check 6: optional field types
                if "source_url" in obj and not isinstance(obj["source_url"], str):
                    errors.append(
                        f"Line {line_num} (id={id_}): 'source_url' must be a string"
                    )

                if "conversation_id" in obj and not isinstance(
                    obj["conversation_id"], str
                ):
                    errors.append(
                        f"Line {line_num} (id={id_}): 'conversation_id' must be a string"
                    )

                for field in ("urls", "addresses"):
                    if field in obj:
                        value = obj[field]
                        if not isinstance(value, list):
                            errors.append(
                                f"Line {line_num} (id={id_}): '{field}' must be an array"
                            )
                        elif not all(isinstance(item, str) for item in value):
                            errors.append(
                                f"Line {line_num} (id={id_}): '{field}' must contain only strings"
                            )

                if "notes" in obj and not isinstance(obj["notes"], str):
                    errors.append(
                        f"Line {line_num} (id={id_}): 'notes' must be a string"
                    )

                if "reply_metrics" in obj:
                    _validate_metrics(
                        obj["reply_metrics"],
                        "reply_metrics",
                        line_num,
                        id_,
                        errors,
                        warnings,
                    )

                if "parent_metrics" in obj:
                    _validate_metrics(
                        obj["parent_metrics"],
                        "parent_metrics",
                        line_num,
                        id_,
                        errors,
                        warnings,
                    )

                # Check 7: thread context
                if "thread_context" in obj:
                    _validate_thread_context(
                        obj["thread_context"],
                        line_num,
                        id_,
                        parent_id,
                        source_id,
                        errors,
                        warnings,
                    )

    except FileNotFoundError:
        errors.append(f"File not found: {path}")
        return errors, warnings

    # Check 3b: report duplicates
    for id_, lines in id_counts.items():
        if len(lines) > 1:
            errors.append(f"Duplicate ID '{id_}' on lines: {lines}")

    return errors, warnings


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "path", nargs="?", default="data/replies.jsonl", help="Path to JSONL file"
    )
    ap.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    ap.add_argument("--quiet", action="store_true", help="Only output if errors found")
    args = ap.parse_args()

    path = Path(args.path)
    errors, warnings = check_integrity(path)

    exit_code = 0

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for error in errors[:50]:
            print(f"  {error}")
        if len(errors) > 50:
            print(f"  ... and {len(errors) - 50} more errors")
        exit_code = 1

    if warnings:
        if args.strict:
            print(f"WARNINGS AS ERRORS ({len(warnings)}):")
            exit_code = 1
        elif not args.quiet:
            print(f"WARNINGS ({len(warnings)}):")

        if not args.quiet or args.strict:
            for warning in warnings[:30]:
                print(f"  {warning}")
            if len(warnings) > 30:
                print(f"  ... and {len(warnings) - 30} more warnings")

    if exit_code == 0 and not args.quiet:
        with path.open(encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]

        label_counts: defaultdict[str, int] = defaultdict(int)
        with_thread_context = 0
        for row in rows:
            for label in row.get("labels", []) or []:
                label_counts[label] += 1
            if row.get("thread_context"):
                with_thread_context += 1

        print("All checks passed!")
        print("\nDataset stats:")
        print(f"  Total entries: {len(rows)}")
        print(f"  Entries with thread_context: {with_thread_context}")
        for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
            print(f"  {label}: {count}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
