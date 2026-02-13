---
name: general-visualization
description: Format comparisons and metrics as readable fixed-width plain text with aligned columns, explicit better/worse labels, and optional deltas. Use when users ask for side-by-side values, no-markdown-table output, console-style alignment, before-vs-after comparisons, experiment scorecards, or quick leaderboard-style summaries.
---

# General Visualization

## Purpose

Render quantitative results in a compact format that is easy to scan in terminal-style clients.
Prefer aligned plain text blocks over Markdown tables unless the user explicitly asks for Markdown tables.

## Core Rules

- Use fixed-width alignment inside fenced `text` blocks for comparisons with multiple metrics.
- Keep one precision policy per output (for example, 4 decimals for rates).
- Preserve units and directionality (`higher is better` vs `lower is better`).
- Always include a verdict column (`better`, `worse`, `same`) when comparing two variants.
- If direction is ambiguous, state the assumption explicitly.
- Keep row labels short and stable (`Scam precision`, `Macro F1`, `Latency p95`).
- Do not hide regressions.

## Metric Direction Defaults

- Higher is better: `precision`, `recall`, `f1`, `accuracy`, `auc`, `throughput`.
- Lower is better: `fpr`, `fnr`, `latency`, `error`, `loss`, `size`, `memory`.
- For unknown metric names, require an explicit assumption before labeling better/worse.

## Workflow

1. Collect rows: metric, baseline, candidate.
2. Set direction for each metric.
3. Compute optional delta (`candidate - baseline` or `%` change).
4. Assign verdict (`better`, `worse`, `same`).
5. Render aligned plain-text block.

## Output Templates

### Side-by-Side Comparison (default)

```text
Metric          Baseline    Candidate   Verdict
Scam precision  0.9512      0.9211      worse
Scam recall     0.7800      0.7000      worse
Scam FPR        0.0122      0.0183      worse
Macro F1        0.8504      0.8301      worse
```

### Comparison with Delta

```text
Metric          Baseline    Candidate   Delta       Verdict
Model size MB   3.40        3.10        -0.30       better
Scam recall     0.7800      0.7600      -0.0200     worse
Latency p95 ms  58          61          +3          worse
```

## Style Controls

- If user requests emphasis, apply `**bold**` only to values or verdicts.
- If user requests no table, still use aligned rows (not Markdown tables).
- If output is short (1-3 metrics), keep to single compact block without extra sections.

This skill intentionally uses no bundled scripts/resources.
