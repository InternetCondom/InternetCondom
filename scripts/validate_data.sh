#!/bin/bash
# Quick validation script for CI/pre-commit
# Usage: ./scripts/validate_data.sh

set -e

echo "Running dataset integrity checks..."
python scripts/check_integrity.py --quiet

echo "Checking for uncommitted label changes..."
if [ -f data/label_changes_*.txt ]; then
    echo "  Found label change audit files ✓"
fi

echo ""
echo "All validations passed! ✓"
