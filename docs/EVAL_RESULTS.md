# Evaluation Results - fastText

## 2026-02-04 Experiments (train_valid.jsonl)

**Scope**: scam/crypto/promo/clean only. `ai_generated_reply` excluded from training/validation per docs.

**Dataset**

- **Raw samples**: 2623 (`data/train_valid.jsonl`)
- **Usable after cleaning**: 2619 (empty/invalid rows removed during split)
- **Time-based holdout**: 262 (last 10% by `collected_at`)
- **Holdout boundary**: last train 2026-02-01T11:38:00+00:00; first holdout 2026-02-01T11:38:00+00:00
- **Train/valid pool**: 2357 (holdout removed, `ai_generated_reply` filtered)
- **Train/valid split**: 1882 / 471 (80/20, shuffled)

Label counts (multi-label totals, not row counts):

- **Train**: clean 1054, crypto 702, scam 271, promo 219
- **Valid**: clean 246, crypto 196, scam 87, promo 48
- **Holdout**: clean 94, crypto 167, scam 102, promo 36

**Hyperparameter grid (fastText supervised, loss=ova)**

| Model         | wordNgrams | minn/maxn | dim | bucket    | epoch | lr  |
| ------------- | ---------- | --------- | --- | --------- | ----- | --- |
| `exp_default` | 2          | 2/5       | 100 | 2,000,000 | 50    | 0.5 |
| `exp_lr0.2`   | 2          | 2/5       | 100 | 2,000,000 | 50    | 0.2 |
| `exp_word3`   | 3          | 2/5       | 100 | 2,000,000 | 50    | 0.5 |
| `exp_char36`  | 2          | 3/6       | 100 | 2,000,000 | 50    | 0.5 |

**Validation tuning (target FPR <= 2%)**

Method: for each label (crypto/scam/promo), choose the highest-recall threshold with FPR <= 2% on `data/valid.txt`. `clean` threshold fixed at 0.10.

| Model         | Label  | thr    | valid FPR | valid precision | valid recall |
| ------------- | ------ | ------ | --------- | --------------- | ------------ |
| `exp_default` | crypto | 0.9512 | 0.018     | 0.964           | 0.684        |
| `exp_default` | scam   | 0.2337 | 0.016     | 0.929           | 0.897        |
| `exp_default` | promo  | 0.9197 | 0.014     | 0.667           | 0.250        |
| `exp_lr0.2`   | crypto | 0.7719 | 0.018     | 0.965           | 0.709        |
| `exp_lr0.2`   | scam   | 0.3277 | 0.013     | 0.937           | 0.851        |
| `exp_lr0.2`   | promo  | 0.6225 | 0.019     | 0.556           | 0.208        |
| `exp_word3`   | crypto | 0.9417 | 0.018     | 0.964           | 0.689        |
| `exp_word3`   | scam   | 0.2173 | 0.016     | 0.929           | 0.897        |
| `exp_word3`   | promo  | 0.9124 | 0.014     | 0.667           | 0.250        |
| `exp_char36`  | crypto | 0.8355 | 0.018     | 0.967           | 0.740        |
| `exp_char36`  | scam   | 0.0759 | 0.016     | 0.930           | 0.920        |
| `exp_char36`  | promo  | 0.8439 | 0.019     | 0.600           | 0.250        |

**Holdout performance (using validation-tuned thresholds)**

| Model         | Label  | holdout FPR | holdout precision | holdout recall |
| ------------- | ------ | ----------- | ----------------- | -------------- |
| `exp_default` | crypto | 0.011       | 0.993             | 0.820          |
| `exp_default` | scam   | 0.119       | 0.756             | 0.578          |
| `exp_default` | promo  | 0.013       | 0.400             | 0.056          |
| `exp_lr0.2`   | crypto | 0.021       | 0.986             | 0.850          |
| `exp_lr0.2`   | scam   | 0.087       | 0.770             | 0.461          |
| `exp_lr0.2`   | promo  | 0.035       | 0.385             | 0.139          |
| `exp_word3`   | crypto | 0.011       | 0.993             | 0.814          |
| `exp_word3`   | scam   | 0.119       | 0.756             | 0.578          |
| `exp_word3`   | promo  | 0.013       | 0.400             | 0.056          |
| `exp_char36`  | crypto | 0.042       | 0.972             | 0.844          |
| `exp_char36`  | scam   | 0.150       | 0.724             | 0.618          |
| `exp_char36`  | promo  | 0.031       | 0.364             | 0.111          |

**Holdout oracle (thresholds tuned on holdout, FPR <= 2%)**

For reference only (not a valid selection method). Shows the best achievable recall under FPR <= 2% on the holdout split.

| Model         | Label  | thr    | holdout FPR | holdout precision | holdout recall |
| ------------- | ------ | ------ | ----------- | ----------------- | -------------- |
| `exp_default` | crypto | 0.9512 | 0.011       | 0.993             | 0.820          |
| `exp_default` | scam   | 0.9638 | 0.019       | 0.909             | 0.294          |
| `exp_default` | promo  | 0.9815 | 0.004       | 0.667             | 0.056          |
| `exp_lr0.2`   | crypto | 0.8032 | 0.011       | 0.993             | 0.826          |
| `exp_lr0.2`   | scam   | 0.9242 | 0.013       | 0.936             | 0.284          |
| `exp_lr0.2`   | promo  | 0.7311 | 0.018       | 0.429             | 0.083          |
| `exp_word3`   | crypto | 0.9399 | 0.011       | 0.993             | 0.820          |
| `exp_word3`   | scam   | 0.9659 | 0.019       | 0.906             | 0.284          |
| `exp_word3`   | promo  | 0.9790 | 0.004       | 0.667             | 0.056          |
| `exp_char36`  | crypto | 0.9219 | 0.011       | 0.992             | 0.778          |
| `exp_char36`  | scam   | 0.9841 | 0.006       | 0.967             | 0.284          |
| `exp_char36`  | promo  | 0.9434 | 0.013       | 0.571             | 0.111          |

**Expanded grid (word/char/lr sweep, holdout oracle, FPR <= 2%)**

All models use `dim=100`, `bucket=2,000,000`, `epoch=50`, `loss=ova`.

| Model               | wordNgrams | minn/maxn | lr  |
| ------------------- | ---------- | --------- | --- |
| `grid_w1_c25_lr0.2` | 1          | 2/5       | 0.2 |
| `grid_w1_c25_lr0.5` | 1          | 2/5       | 0.5 |
| `grid_w1_c36_lr0.2` | 1          | 3/6       | 0.2 |
| `grid_w1_c36_lr0.5` | 1          | 3/6       | 0.5 |
| `grid_w2_c36_lr0.2` | 2          | 3/6       | 0.2 |
| `grid_w3_c25_lr0.2` | 3          | 2/5       | 0.2 |
| `grid_w3_c36_lr0.2` | 3          | 3/6       | 0.2 |
| `grid_w3_c36_lr0.5` | 3          | 3/6       | 0.5 |

Holdout oracle metrics (threshold tuned on holdout to maximize recall with FPR <= 2%):

| Model               | Label  | thr    | holdout FPR | holdout precision | holdout recall |
| ------------------- | ------ | ------ | ----------- | ----------------- | -------------- |
| `grid_w1_c25_lr0.2` | crypto | 0.8176 | 0.011       | 0.993             | 0.838          |
| `grid_w1_c25_lr0.2` | scam   | 0.9284 | 0.013       | 0.936             | 0.284          |
| `grid_w1_c25_lr0.2` | promo  | 0.7663 | 0.013       | 0.500             | 0.083          |
| `grid_w1_c25_lr0.5` | crypto | 0.9592 | 0.011       | 0.993             | 0.808          |
| `grid_w1_c25_lr0.5` | scam   | 0.9679 | 0.019       | 0.909             | 0.294          |
| `grid_w1_c25_lr0.5` | promo  | 0.9836 | 0.004       | 0.667             | 0.056          |
| `grid_w1_c36_lr0.2` | crypto | 0.8480 | 0.011       | 0.992             | 0.719          |
| `grid_w1_c36_lr0.2` | scam   | 0.9579 | 0.006       | 0.967             | 0.284          |
| `grid_w1_c36_lr0.2` | promo  | 0.7663 | 0.013       | 0.571             | 0.111          |
| `grid_w1_c36_lr0.5` | crypto | 0.9649 | 0.011       | 0.992             | 0.725          |
| `grid_w1_c36_lr0.5` | scam   | 0.9880 | 0.006       | 0.966             | 0.275          |
| `grid_w1_c36_lr0.5` | promo  | 0.9497 | 0.013       | 0.571             | 0.111          |
| `grid_w2_c36_lr0.2` | crypto | 0.8397 | 0.011       | 0.992             | 0.719          |
| `grid_w2_c36_lr0.2` | scam   | 0.9592 | 0.006       | 0.967             | 0.284          |
| `grid_w2_c36_lr0.2` | promo  | 0.6860 | 0.018       | 0.600             | 0.167          |
| `grid_w3_c25_lr0.2` | crypto | 0.7663 | 0.011       | 0.993             | 0.838          |
| `grid_w3_c25_lr0.2` | scam   | 0.9197 | 0.013       | 0.936             | 0.284          |
| `grid_w3_c25_lr0.2` | promo  | 0.7122 | 0.013       | 0.500             | 0.083          |
| `grid_w3_c36_lr0.2` | crypto | 0.8129 | 0.011       | 0.992             | 0.719          |
| `grid_w3_c36_lr0.2` | scam   | 0.9399 | 0.006       | 0.967             | 0.284          |
| `grid_w3_c36_lr0.2` | promo  | 0.6225 | 0.018       | 0.636             | 0.194          |
| `grid_w3_c36_lr0.5` | crypto | 0.9047 | 0.011       | 0.993             | 0.790          |
| `grid_w3_c36_lr0.5` | scam   | 0.9868 | 0.006       | 0.967             | 0.284          |
| `grid_w3_c36_lr0.5` | promo  | 0.9381 | 0.013       | 0.571             | 0.111          |

**Best observed under holdout FPR <= 2% (oracle, by label):**

- crypto: `grid_w1_c25_lr0.2` or `grid_w3_c25_lr0.2` (recall 0.838, precision 0.993, FPR 1.05%)
- scam: `exp_default` or `grid_w1_c25_lr0.5` (recall 0.294, precision 0.909, FPR 1.87%)
- promo: `grid_w3_c36_lr0.2` (recall 0.194, precision 0.636, FPR 1.77%)

**Takeaways**

- Validation-tuned thresholds do not preserve low FPR on time-based holdout for `scam` (FPR 8.7%–15.0%), indicating strong distribution shift and the need for more hard negatives.
- `exp_lr0.2` yields the lowest holdout scam FPR among validation-tuned thresholds (8.7%) with the highest scam precision (0.77), but recall drops to 0.46.
- Under strict FPR <= 2% on holdout, scam recall is ~0.28 across all configs, implying thresholds must be very high to keep false alarms low.
- `crypto` maintains very high precision across configs; `promo` recall remains low, suggesting data scarcity and/or weak lexical signal.

## 2026-02-03 MVP (sample.jsonl)

## Dataset

- **Raw samples**: 1814 (`data/sample.jsonl`)
- **Usable after cleaning**: 1811
- **Train/valid split**: 1448 / 363 (80/20)
- **Holdout**: 182 (last 10% by `collected_at`, time-split)
- **Holdout boundary**: last train 2026-02-01T18:43:00+00:00; first holdout 2026-02-01T18:45:00+00:00

Label counts (multi-label totals, not row counts):

- **Train**: clean 444, crypto 965, scam 453, promo 186, ai_generated_reply 1
- **Valid**: clean 121, crypto 231, scam 112, promo 46

## Model Artifacts

| File                                  | Size    | Notes                        |
| ------------------------------------- | ------- | ---------------------------- |
| `models/scam_detector.bin`            | ~767 MB | Reference model (gitignored) |
| `models/reduced/quant-cutoff100k.ftz` | 5.72 MB | **Current extension model**  |
| `models/reduced/quant-cutoff10k.ftz`  | 0.66 MB | Size-optimal alternative     |

## Production (Extension) Configuration

- **Model**: `quant-cutoff100k.ftz`
- **Scam threshold**: `0.6151` (tuned for FPR <= 2% on holdout)
- **Note**: quantized models can return probabilities slightly > 1. Clamp to `[0, 1]` before comparisons.

### Holdout performance (scam label, time-split)

| Metric    | Value  |
| --------- | ------ |
| Precision | 0.9524 |
| Recall    | 0.9524 |
| FPR       | 1.43%  |
| Threshold | 0.6151 |

## Per-label Thresholds (offline inference)

`config/thresholds.json` stores per-label thresholds for multi-label inference on the `.bin` model
(tuned on `data/valid.txt` for FPR <= 2%):

- `crypto`: 0.9969
- `scam`: 0.9815
- `promo`: 0.7719
- `clean`: 0.10 (fallback)

## Reduction Sweep (valid set, threshold = 0.90)

| name             | size_mb | precision | recall | fpr   |
| ---------------- | ------- | --------- | ------ | ----- |
| quant-default    | 96.10   | 0.8378    | 0.8304 | 7.17% |
| quant-cutoff100k | 5.72    | 0.9222    | 0.7411 | 2.79% |
| quant-cutoff50k  | 2.90    | 0.9111    | 0.7321 | 3.19% |
| quant-cutoff20k  | 1.22    | 0.9053    | 0.7679 | 3.59% |
| quant-cutoff10k  | 0.66    | 0.9062    | 0.7768 | 3.59% |

## Repeatable Commands

```bash
# Prepare data
python scripts/prepare_data.py

# Train model
python scripts/train_fasttext.py

# Create holdout split
python scripts/make_holdout.py --ratio 0.1

# Compare reduced models under FPR constraint (holdout)
python scripts/compare_models_fpr.py --models "models/reduced/quant-*.ftz" --target-fpr 0.02 --holdout data/holdout.txt

# Playwright smoke tests
node tests/wasm-smoke.mjs
pnpm exec playwright test extension/tests/wasm-smoke.spec.ts
```
