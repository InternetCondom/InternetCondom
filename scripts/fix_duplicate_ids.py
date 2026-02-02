#!/usr/bin/env python3
"""
Fix duplicate IDs in the dataset by assigning new unique IDs.

READ-ONLY by default. Use --apply to write changes.

Strategy:
- Keep the first occurrence of each ID
- Assign new IDs to subsequent duplicates (e.g., x_0755 -> x_0755_dup1)
- Null IDs get assigned new sequential IDs (e.g., x_auto_0001)
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", default="data/sample.jsonl", help="Path to JSONL file")
    ap.add_argument("--apply", action="store_true", help="Actually write changes (default: preview only)")
    ap.add_argument("--fix-nulls", action="store_true", help="Also assign IDs to null entries")
    args = ap.parse_args()

    path = Path(args.path)
    
    # First pass: collect all entries and find duplicates
    entries = []
    id_counts = defaultdict(int)
    
    for line in path.open(encoding="utf-8"):
        obj = json.loads(line)
        entries.append(obj)
        id_ = obj.get("id")
        if id_ is not None:
            id_counts[id_] += 1
    
    # Find max existing ID number for auto-assignment
    max_id_num = 0
    for id_ in id_counts:
        if id_ and id_.startswith("x_"):
            try:
                num = int(id_.split("_")[1])
                max_id_num = max(max_id_num, num)
            except (ValueError, IndexError):
                pass
    
    auto_id_counter = max_id_num + 1
    
    # Report duplicates
    duplicates = {k: v for k, v in id_counts.items() if v > 1}
    null_count = sum(1 for e in entries if e.get("id") is None)
    
    print(f"Total entries: {len(entries)}")
    print(f"Unique non-null IDs: {len(id_counts)}")
    print(f"Duplicate IDs: {len(duplicates)}")
    print(f"Null IDs: {null_count}")
    print()
    
    if duplicates:
        print("Duplicated IDs (showing first 20):")
        for id_, count in list(duplicates.items())[:20]:
            print(f"  {id_}: {count} occurrences")
        if len(duplicates) > 20:
            print(f"  ... and {len(duplicates) - 20} more")
        print()
    
    # Second pass: fix duplicates
    seen_ids = set()
    changes = []
    output_entries = []
    
    for obj in entries:
        old_id = obj.get("id")
        new_id = old_id
        
        if old_id is None:
            if args.fix_nulls:
                new_id = f"x_auto_{auto_id_counter:04d}"
                auto_id_counter += 1
                changes.append((old_id, new_id, obj.get("text", "")[:60]))
        elif old_id in seen_ids:
            # Duplicate - assign new ID
            dup_num = 1
            while f"{old_id}_dup{dup_num}" in seen_ids:
                dup_num += 1
            new_id = f"{old_id}_dup{dup_num}"
            changes.append((old_id, new_id, obj.get("text", "")[:60]))
        
        seen_ids.add(new_id)
        obj["id"] = new_id
        output_entries.append(obj)
    
    print(f"Changes to make: {len(changes)}")
    if changes:
        print("\nSample changes (first 20):")
        for old, new, text in changes[:20]:
            print(f"  {old} -> {new}")
            print(f"    text: {text}...")
        if len(changes) > 20:
            print(f"  ... and {len(changes) - 20} more")
    
    if not args.apply:
        print("\n⚠️  DRY RUN - no changes written. Use --apply to write.")
        return
    
    # Write atomically
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=path.parent) as tmp:
        for obj in output_entries:
            tmp.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)
    print(f"\n✅ Fixed {len(changes)} entries in {path}")


if __name__ == "__main__":
    main()
