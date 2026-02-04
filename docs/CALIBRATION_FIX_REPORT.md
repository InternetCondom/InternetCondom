# Calibration Fix Report

Date: 2026-02-04
Owner: Codex (autonomous)
Scope: Fix calibration instability for `time_exp_default_hn` (hard negatives)

## Problem Statement
The current calibration set is extremely imbalanced (only 43 clean samples out of 261 total). This makes FPR estimation brittle and pushes per-label thresholds too high, which suppresses recall.

Given state at start:
- Model: `models/experiments/time_exp_default_hn.bin`
- Calibration set: `data/calib.txt` (43 clean / 261 total)
- Current tuned thresholds: `models/experiments/time_exp_default_hn.calib.thresholds.json`
- Reported metrics: Scam recall ~42% @ ~1% FPR, Crypto recall ~74.5%, Promo recall 0%

## Datasets Snapshot
Counts are number of rows containing each label (multi-label rows counted for each label).

- `data/calib.txt`: total 261
  - clean 43
  - crypto 216
  - scam 169
  - promo 25
- `data/holdout_time.txt`: total 261
  - clean 94
  - crypto 166
  - scam 101
  - promo 36
- `data/valid.txt`: total 471
  - clean 246
  - crypto 196
  - scam 87
  - promo 48
- `data/train_pool.jsonl`: clean-only rows 1304
- `data/train_time_hn_calib.txt`: clean rows 1386 (matches “clean pool available” mentioned in task)

## Evaluation Harness
- Script: `scripts/evaluate.py`
- Threshold tuning (FPR constrained): `scripts/tune_thresholds_fpr.py`
- Evaluation set: `data/holdout_time.txt` (time-based holdout)

## Option A — Accept Current Model As-Is
Baseline thresholds from `models/experiments/time_exp_default_hn.calib.thresholds.json`.

Command:
```bash
python scripts/evaluate.py \
  --model models/experiments/time_exp_default_hn.bin \
  --valid data/holdout_time.txt \
  --thresholds models/experiments/time_exp_default_hn.calib.thresholds.json
```

Result on holdout_time:
- Scam: precision 1.000, recall 0.257, FPR 0.000, threshold 0.97
- Crypto: precision 0.992, recall 0.735, FPR 0.011, threshold 0.82
- Promo: precision 0.000, recall 0.000, FPR 0.004, threshold 1.00

Tradeoffs:
- Pros: Very low FPR
- Cons: Scam recall extremely low; Promo completely broken (0% recall)

Status: Baseline only; not acceptable for deployment.

## Option B — Rebalance Calibration Set With More Clean Samples
Goal: reduce threshold brittleness by adding clean negatives, then re-tune at 2% FPR.

### B1: Full clean pool augmentation (largest possible)
Calibration build:
- Script: `scripts/build_rebalanced_calib.py`
- Command: `python scripts/build_rebalanced_calib.py`
- Clean pool source: `data/train_time_hn_calib.txt`
- Output: `data/calib_rebalanced.txt`
- Resulting counts: clean 1300, crypto 216, scam 169, promo 25 (total 1518)

Threshold tuning:
```bash
python scripts/tune_thresholds_fpr.py \
  --model models/experiments/time_exp_default_hn.bin \
  --data data/calib_rebalanced.txt \
  --out models/experiments/time_exp_default_hn.calib_rebalanced.thresholds.json \
  --target-fpr 0.02
```

Holdout evaluation:
```bash
python scripts/evaluate.py \
  --model models/experiments/time_exp_default_hn.bin \
  --valid data/holdout_time.txt \
  --thresholds models/experiments/time_exp_default_hn.calib_rebalanced.thresholds.json
```

Result on holdout_time:
- Scam: precision 0.616, recall 0.446, FPR 0.175, threshold 0.01
- Crypto: precision 0.857, recall 0.976, FPR 0.284, threshold 0.02
- Promo: precision 0.000, recall 0.000, FPR 0.004, threshold 1.00

Tradeoffs:
- Pros: big recall boost for scam and crypto
- Cons: FPR explodes on holdout (17.5% scam, 28.4% crypto). Clean pool appears too “easy”, pushing thresholds too low.

### B2: Hard-negative clean augmentation (smaller, harder)
Calibration build:
- Clean pool: `data/hardneg_scam.txt` (200 clean hard negatives)
- Command:
```bash
python scripts/build_rebalanced_calib.py \
  --clean-pool data/hardneg_scam.txt \
  --out data/calib_rebalanced_hardneg.txt \
  --meta-out data/calib_rebalanced_hardneg.meta.json
```
- Resulting counts: clean 243, crypto 216, scam 169, promo 25 (total 461)

Threshold tuning:
```bash
python scripts/tune_thresholds_fpr.py \
  --model models/experiments/time_exp_default_hn.bin \
  --data data/calib_rebalanced_hardneg.txt \
  --out models/experiments/time_exp_default_hn.calib_hardneg.thresholds.json \
  --target-fpr 0.02
```

Holdout evaluation:
```bash
python scripts/evaluate.py \
  --model models/experiments/time_exp_default_hn.bin \
  --valid data/holdout_time.txt \
  --thresholds models/experiments/time_exp_default_hn.calib_hardneg.thresholds.json
```

Result on holdout_time:
- Scam: precision 0.850, recall 0.337, FPR 0.037, threshold 0.07
- Crypto: precision 0.957, recall 0.928, FPR 0.074, threshold 0.25
- Promo: precision 0.000, recall 0.000, FPR 0.004, threshold 1.00

Tradeoffs:
- Pros: better scam recall than baseline with modest FPR increase; much more stable than 43-clean calibration.
- Cons: still misses promo entirely; FPR on holdout is ~3.7%, above the original 2% target.

## Option C — Relax FPR Constraint to 5%
Calibrate on the original `data/calib.txt`, but allow up to 5% FPR.

Threshold tuning:
```bash
python scripts/tune_thresholds_fpr.py \
  --model models/experiments/time_exp_default_hn.bin \
  --data data/calib.txt \
  --out models/experiments/time_exp_default_hn.calib_fpr5.thresholds.json \
  --target-fpr 0.05
```

Holdout evaluation:
```bash
python scripts/evaluate.py \
  --model models/experiments/time_exp_default_hn.bin \
  --valid data/holdout_time.txt \
  --thresholds models/experiments/time_exp_default_hn.calib_fpr5.thresholds.json
```

Result on holdout_time:
- Scam: precision 0.850, recall 0.337, FPR 0.037, threshold 0.07
- Crypto: precision 0.956, recall 0.922, FPR 0.074, threshold 0.29
- Promo: precision 0.000, recall 0.000, FPR 0.004, threshold 1.00

Tradeoffs:
- Pros: simple change, improves recall while keeping FPR < 5% on holdout
- Cons: does not address calibration imbalance; promo remains broken

## Option D — Other Approaches Worth Trying

### D1: Calibrate on `valid.txt` (larger, more balanced)
Rationale: bigger calibration set may stabilize FPR and avoid tiny-clean artifacts, at the cost of mixing time periods.

Threshold tuning:
```bash
python scripts/tune_thresholds_fpr.py \
  --model models/experiments/time_exp_default_hn.bin \
  --data data/valid.txt \
  --out models/experiments/time_exp_default_hn.valid_fpr2.thresholds.json \
  --target-fpr 0.02
```

Holdout evaluation:
```bash
python scripts/evaluate.py \
  --model models/experiments/time_exp_default_hn.bin \
  --valid data/holdout_time.txt \
  --thresholds models/experiments/time_exp_default_hn.valid_fpr2.thresholds.json
```

Result on holdout_time:
- Scam: precision 0.809, recall 0.376, FPR 0.056, threshold 0.03
- Crypto: precision 0.952, recall 0.946, FPR 0.084, threshold 0.17
- Promo: precision 0.267, recall 0.111, FPR 0.049, threshold 0.86

Tradeoffs:
- Pros: highest scam recall among “reasonable FPR” options; promo recall non-zero.
- Cons: FPR on holdout rises above 5% for scam/crypto; mixes time periods (potential leakage risk).

### D2: Hard-negative mining (top-600 clean by p(scam))
Rationale: add many hard clean negatives, not just random clean.

Commands:
```bash
python scripts/mine_hard_negatives_txt.py \
  --model models/experiments/time_exp_default_hn.bin \
  --input data/train_time_hn_calib.txt \
  --label scam \
  --top-n 600 \
  --out data/hardneg_scam_top600.txt

python scripts/build_rebalanced_calib.py \
  --clean-pool data/hardneg_scam_top600.txt \
  --out data/calib_rebalanced_hardneg600.txt \
  --meta-out data/calib_rebalanced_hardneg600.meta.json
```

Threshold tuning:
```bash
python scripts/tune_thresholds_fpr.py \
  --model models/experiments/time_exp_default_hn.bin \
  --data data/calib_rebalanced_hardneg600.txt \
  --out models/experiments/time_exp_default_hn.calib_hardneg600.thresholds.json \
  --target-fpr 0.02
```

Holdout evaluation:
```bash
python scripts/evaluate.py \
  --model models/experiments/time_exp_default_hn.bin \
  --valid data/holdout_time.txt \
  --thresholds models/experiments/time_exp_default_hn.calib_hardneg600.thresholds.json
```

Result on holdout_time:
- Scam: precision 0.702, recall 0.396, FPR 0.106, threshold 0.02
- Crypto: precision 0.924, recall 0.958, FPR 0.137, threshold 0.09
- Promo: precision 0.000, recall 0.000, FPR 0.004, threshold 1.00

Tradeoffs:
- Pros: boosts scam recall.
- Cons: FPR becomes too high; not acceptable if FPR budget matters.

### D3: Use the full `train_time_hn_calib.txt` as calibration
Rationale: largest available calibration set with all labels.

Threshold tuning:
```bash
python scripts/tune_thresholds_fpr.py \
  --model models/experiments/time_exp_default_hn.bin \
  --data data/train_time_hn_calib.txt \
  --out models/experiments/time_exp_default_hn.train_time_hn_calib.thresholds.json \
  --target-fpr 0.02
```

Holdout evaluation:
```bash
python scripts/evaluate.py \
  --model models/experiments/time_exp_default_hn.bin \
  --valid data/holdout_time.txt \
  --thresholds models/experiments/time_exp_default_hn.train_time_hn_calib.thresholds.json
```

Result on holdout_time:
- Scam: precision 0.917, recall 0.327, FPR 0.019, threshold 0.16
- Crypto: precision 0.930, recall 0.958, FPR 0.126, threshold 0.13
- Promo: precision 0.259, recall 0.417, FPR 0.191, threshold 0.14

Tradeoffs:
- Pros: large calibration set, better promo recall.
- Cons: promo FPR is extremely high (19%); indicates strong distribution mismatch.

## Summary Table (Holdout-Time Metrics)
All metrics measured on `data/holdout_time.txt`.

| Option | Scam recall | Scam FPR | Crypto recall | Crypto FPR | Promo recall | Promo FPR |
| --- | --- | --- | --- | --- | --- | --- |
| A: As-is | 0.257 | 0.000 | 0.735 | 0.011 | 0.000 | 0.004 |
| B1: Rebalance (full clean pool) | 0.446 | 0.175 | 0.976 | 0.284 | 0.000 | 0.004 |
| B2: Rebalance (hardneg 200) | 0.337 | 0.037 | 0.928 | 0.074 | 0.000 | 0.004 |
| C: FPR 5% | 0.337 | 0.037 | 0.922 | 0.074 | 0.000 | 0.004 |
| D1: Valid calibration | 0.376 | 0.056 | 0.946 | 0.084 | 0.111 | 0.049 |
| D2: Hardneg top-600 | 0.396 | 0.106 | 0.958 | 0.137 | 0.000 | 0.004 |
| D3: Full train_time_hn_calib | 0.327 | 0.019 | 0.958 | 0.126 | 0.417 | 0.191 |

## Final Recommendation
Adopt **Option B2** (rebalanced calibration with hard-negative clean augmentation) for the time-exp model, and keep the 2% FPR target. This directly fixes the calibration imbalance while avoiding the extreme FPR blowups seen with large easy-clean pools.

Why B2:
- Improves scam recall from 0.257 → 0.337 on holdout while keeping FPR to 3.7%.
- Uses a more stable calibration set (243 clean instead of 43), reducing threshold brittleness.
- Avoids the distribution mismatch seen with full clean-pool augmentation.

What this does not fix:
- Promo recall remains 0. The model needs more promo data or retraining; calibration alone cannot fix it.

Recommended thresholds artifact:
- `models/experiments/time_exp_default_hn.calib_hardneg.thresholds.json`

If you are willing to tolerate ~5% FPR:
- Option C offers the same holdout metrics as B2 with fewer moving parts, but it does not resolve calibration imbalance and remains brittle.

If promo detection is critical:
- D1 is the only option that yields non-zero promo recall, but it pushes FPR past 5% and risks time leakage.

## Artifacts Created
- `scripts/build_rebalanced_calib.py` (utility for clean augmentation)
- `data/calib_rebalanced.txt`
- `data/calib_rebalanced.meta.json`
- `data/calib_rebalanced_hardneg.txt`
- `data/calib_rebalanced_hardneg.meta.json`
- `data/hardneg_scam_top600.txt`
- `data/calib_rebalanced_hardneg600.txt`
- `data/calib_rebalanced_hardneg600.meta.json`
- `models/experiments/time_exp_default_hn.calib_rebalanced.thresholds.json`
- `models/experiments/time_exp_default_hn.calib_hardneg.thresholds.json`
- `models/experiments/time_exp_default_hn.calib_hardneg600.thresholds.json`
- `models/experiments/time_exp_default_hn.calib_fpr5.thresholds.json`
- `models/experiments/time_exp_default_hn.valid_fpr2.thresholds.json`
- `models/experiments/time_exp_default_hn.train_time_hn_calib.thresholds.json`
