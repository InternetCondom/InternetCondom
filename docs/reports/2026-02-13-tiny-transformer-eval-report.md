---
date: 2026-02-13
author: Bob <bob@dutifulbob.com>
title: Tiny Transformer Eval Report
tags: [janitr, transformer, distillation, onnx, evaluation]
updated: 2026-02-13T17:35:33Z
---

# Tiny Transformer Eval Report

## Scope

Executed Milestone 2 end-to-end after implementing all Milestone 1 scripts from `docs/plans/2026-02-13-tiny-transformer-plan.md`.

## Postmortem Addendum (GPU Run, Root Cause)

Follow-up execution on 2026-02-13 used the required GPU setup and teacher configuration:

- Teacher: `cardiffnlp/twitter-roberta-large-2022-154m`
- Seeds: `13,42,7`
- CUDA: enabled

Observed outcome:

- Student scam recall collapsed to `0.0` on train/valid/holdout at configured thresholds.
- Holdout scam precision/recall/FPR in `models/student_holdout_eval.json`: `0.0000 / 0.0000 / 0.0000`.

Confirmed root cause:

- `scripts/train_transformer_student_distill.py` builds the tokenizer with `BertTokenizerFast(vocab_file=...)`.
- In current Transformers API, the constructor expects `vocab=...` (or loading from a saved tokenizer file).
- Because of this mismatch, tokenizer backend vocab fell back to special tokens only (`[PAD] [UNK] [CLS] [SEP] [MASK]`), then was padded with `[UNUSED_*]` tokens to reach `8192`.
- Net effect: nearly all words tokenized to `[UNK]`, so the student saw almost no lexical signal and learned near-constant scam probabilities.

Evidence supporting localization:

- Teacher is healthy: `models/teacher/training_summary.json` shows strong ensemble scam performance (holdout recall `0.84`).
- Cached teacher logits are separable (`models/teacher_logits_{train,valid}.npz`).
- Student scam probabilities are compressed to a narrow low range (~`0.146` to `0.303`) across all classes.

Production implication:

- This run is not promotable.
- Fix tokenizer construction and add fail-fast tokenizer sanity checks before rerunning distillation/eval.

## Follow-up (Fix Applied and Rerun)

After patching tokenizer construction and adding fail-fast tokenizer checks:

- `scripts/train_transformer_student_distill.py` now builds tokenizer with `BertTokenizerFast(vocab=...)` and validates backend vocab + sampled UNK ratio.
- `scripts/export_transformer_student_onnx.py` and `scripts/evaluate_transformer.py` now fail fast on tokenizer sanity checks.

Rerun executed on 2026-02-13:

1. `train_transformer_student_distill.py`
2. `export_transformer_student_onnx.py`
3. `quantize_transformer_student.py`
4. `evaluate_transformer.py`

Tokenizer sanity during rerun:

- backend vocab: `8192`
- sampled UNK ratio: `0.0036` (train sample)

Updated holdout metrics (`models/student_holdout_eval.json`):

- thresholds: `scam=0.61`, `topic_crypto=0.60`
- scam: precision `0.9512`, recall `0.7800`, F1 `0.8571`, FPR `0.0122`
- topic_crypto: precision `0.8421`, recall `0.7619`, F1 `0.8000`, FPR `0.0596`
- exact-match accuracy: `0.8598`
- macro F1: `0.8504`
- scam PR-AUC: `0.8890`

Gate status after fix:

- scam FPR on holdout `<= 0.02`: PASS
- scam precision on holdout `>= 0.90`: PASS
- scam recall non-regression vs fastText baseline: PASS
- topic_crypto F1 non-regression vs fastText baseline: PASS

Pipeline executed:

1. prepare data
2. DAPT (skipped)
3. train teacher
4. calibrate teacher
5. cache logits
6. distill student
7. export ONNX
8. quantize ONNX int8
9. evaluate on holdout

## Environment Notes

- Platform: `Linux-6.17.0-1008-nvidia-aarch64`
- Python runtime: `uv --project scripts`
- PyTorch runtime detected in this environment: `2.10.0+cpu`
- CUDA: unavailable in this run (`torch.cuda.is_available() == False`)

## Executed Configuration

### Data

- Input splits:
  - `data/train.jsonl` (3421)
  - `data/valid.jsonl` (428)
  - `data/holdout.jsonl` (214)
- Prepared splits:
  - `data/transformer/train.prepared.jsonl`
  - `data/transformer/valid.prepared.jsonl`
  - `data/transformer/holdout.prepared.jsonl`

### DAPT

- Optional DAPT was skipped to keep runtime practical in this CPU-only execution.

### Teacher

- Teacher model: `prajjwal1/bert-mini`
- Seeds: `13`
- Epochs: `2`
- Output summary: `models/teacher/training_summary.json`

Teacher ensemble metrics (single seed ensemble) from training summary:

- Valid scam: precision `0.6515`, recall `0.8776`, F1 `0.7478`, FPR `0.1394`
- Holdout scam: precision `0.7719`, recall `0.8800`, F1 `0.8224`, FPR `0.0793`
- Holdout macro F1: `0.8144`

### Calibration

- Calibration file: `models/teacher_calibration.json`
- Best temperatures:
  - scam/clean head: `0.850`
  - topic head: `0.900`

### Distilled Student

- Student checkpoint: `models/student/pytorch_model.bin`
- Student eval snapshot: `models/student/student_eval.json`

### ONNX + Quantization

- FP32 ONNX: `models/student.onnx` (`7.0 MB`)
- INT8 ONNX: `models/student.int8.onnx` (`1.9 MB`)

### Threshold Tuning + Holdout Eval

- Thresholds file: `config/thresholds.transformer.json`
- Tuned thresholds:
  - scam: `0.56`
  - topic_crypto: `0.59`
- Evaluation artifact: `models/student_holdout_eval_int8.json`

Holdout metrics (int8 ONNX):

- scam:
  - precision `0.2500`
  - recall `0.0200`
  - F1 `0.0370`
  - FPR `0.0183`
- topic_crypto:
  - precision `0.3750`
  - recall `0.4762`
  - F1 `0.4196`
  - FPR `0.3311`
- clean:
  - precision `0.5231`
  - recall `0.6733`
  - F1 `0.5887`
  - FPR `0.5487`
- exact-match accuracy: `0.4626`
- macro F1: `0.3485`
- micro F1: `0.4626`
- scam PR-AUC: `0.2403`

Subgroup highlights (holdout):

- short posts `<40`: scam recall `0.0000`, scam FPR `0.0000` (16 samples)
- with URL: scam recall `0.0000`, scam FPR `0.0000` (5 samples)
- without URL: scam recall `0.0200`, scam FPR `0.0189` (209 samples)
- seen handles: no samples (`0`)
- unseen handles: scam recall `0.0200`, scam FPR `0.0183` (214 samples)

## Gate Check Summary

Target gates from plan:

- scam FPR on holdout `<= 0.02`: PASS (`0.0183`)
- scam precision on holdout `>= 0.90`: FAIL (`0.2500`)
- scam recall near fastText baseline: FAIL (very low recall `0.0200`)
- topic_crypto non-regression: FAIL in this run

Result: **not promotable** in current run configuration.

## Artifacts Produced

All artifacts were written under `models/`:

- `models/teacher/seed_13/pytorch_model.bin`
- `models/teacher/training_summary.json`
- `models/teacher_valid_preds.jsonl`
- `models/teacher_holdout_preds.jsonl`
- `models/teacher_calibration.json`
- `models/teacher_valid_preds_calibrated.jsonl`
- `models/teacher_logits_train.npz`
- `models/teacher_logits_valid.npz`
- `models/student/pytorch_model.bin`
- `models/student/student_config.json`
- `models/student/student_eval.json`
- `models/student.onnx`
- `models/student.int8.onnx`
- `models/student_holdout_eval_int8.json`

## Notes

- Pipeline completed fully with generated artifacts and evaluation outputs.
- This run used a smaller teacher (`prajjwal1/bert-mini`) for practical runtime; results are expected to differ from plan targets that assume a stronger tweet-native teacher.
