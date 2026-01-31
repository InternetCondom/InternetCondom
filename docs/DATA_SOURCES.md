# Data Sources (AI-first)

## Goal
Source text data for `crypto_scam`, `ai_reply`, and `clean`, with provenance
stored for every record.

## Primary sources
- X (Twitter): posts and replies.
- Discord: DMs and server messages.
- Web: site content or scraped text you control.

## AI-first labeling workflow
1) Collect raw text + metadata.
2) Use AI models to label `crypto_scam` at scale.
3) Source `ai_reply` candidates by searching X for “AI reply”.
4) Keep everything else as `clean` unless the AI labels it otherwise.

## Provenance fields (required)
- `platform`: x | discord | web | dm | other
- `source_id`: platform-native id (tweet id, message id, etc.)
- `source_url`: canonical URL when available
- `collected_at`: ISO timestamp

## JSONL schema (recap)
Each record:
```
{
  "id": "x_0001",
  "platform": "x",
  "source_id": "1234567890",
  "source_url": "https://x.com/...",
  "collected_at": "2026-01-31T00:00:00Z",
  "text": "raw text",
  "label": "crypto_scam|ai_reply|clean",
  "urls": ["https://example.com"],
  "addresses": ["..."],
  "notes": "optional"
}
```

## Sampling strategy
- Ensure class balance across `crypto_scam`, `ai_reply`, and `clean`.
- Deduplicate near-identical text.
- Keep a separate holdout split for evaluation.

## Output location
- Store curated datasets in `data/` as JSONL.
- Keep raw dumps in `data/raw/` (optional).
