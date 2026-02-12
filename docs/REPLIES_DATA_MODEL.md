# Reply-In-Context Data Model

This document defines the JSONL schema for the reply dataset used for AI-generated reply detection on X.

- Dataset file: `data/replies.jsonl`
- Separate from: `data/sample.jsonl`
- One JSON object per line

The unit of labeling is always the **reply**, but each sample must include at least the direct parent context.

## Design Principles

1. Keep rich labels from `docs/LABELS.md` at the data layer (no simplification in JSONL).
2. Store the reply with enough context to evaluate specificity vs templated behavior.
3. Capture profile metadata for both reply and parent authors to support heuristic features.

## Top-Level Schema

Required fields:

| Field           | Type              | Notes                                                                                |
| --------------- | ----------------- | ------------------------------------------------------------------------------------ |
| `id`            | string            | Unique sample ID. For real X replies, use the same numeric status ID as `source_id`. |
| `platform`      | string            | Must be `x`.                                                                         |
| `source_id`     | string            | Reply tweet/status ID.                                                               |
| `collected_at`  | string (ISO 8601) | Time this sample was collected.                                                      |
| `text`          | string            | Reply text (raw, untruncated).                                                       |
| `labels`        | string[]          | Non-empty; values must come from `docs/LABELS.md`.                                   |
| `is_reply`      | boolean           | Must be `true`.                                                                      |
| `parent_id`     | string            | Direct parent tweet/status ID.                                                       |
| `parent_text`   | string            | Direct parent text (minimum required context).                                       |
| `reply_author`  | object            | Author metadata object (schema below).                                               |
| `parent_author` | object            | Author metadata object (schema below).                                               |

Common optional fields:

| Field             | Type     | Notes                                                           |
| ----------------- | -------- | --------------------------------------------------------------- |
| `source_url`      | string   | Canonical URL of the reply.                                     |
| `conversation_id` | string   | X conversation/thread ID.                                       |
| `urls`            | string[] | URLs extracted from reply text.                                 |
| `addresses`       | string[] | Wallet addresses extracted from reply text.                     |
| `notes`           | string   | Labeler rationale or context notes.                             |
| `reply_metrics`   | object   | Public metrics snapshot for reply.                              |
| `parent_metrics`  | object   | Public metrics snapshot for parent.                             |
| `thread_context`  | object[] | Optional extra context beyond parent (ancestors/siblings/root). |

## Author Metadata Object

`reply_author` and `parent_author` use the same shape.

Required fields:

| Field             | Type              | Notes                                                         |
| ----------------- | ----------------- | ------------------------------------------------------------- |
| `handle`          | string            | Username without `@`.                                         |
| `verified`        | boolean           | Verification badge status at scrape time.                     |
| `follower_count`  | integer           | Non-negative.                                                 |
| `following_count` | integer           | Non-negative.                                                 |
| `bio`             | string            | Profile bio text (can be empty if truly blank).               |
| `created_at`      | string (ISO 8601) | Account creation timestamp (needed for account-age features). |

Optional fields:

| Field                  | Type              | Notes                                     |
| ---------------------- | ----------------- | ----------------------------------------- |
| `user_id`              | string            | Numeric user ID when available.           |
| `display_name`         | string            | Display name.                             |
| `tweet_count`          | integer           | Non-negative.                             |
| `listed_count`         | integer           | Non-negative.                             |
| `profile_collected_at` | string (ISO 8601) | Timestamp for profile snapshot freshness. |

## `thread_context` Item Schema

Each item represents additional posts around the reply and parent.

Required item fields:

| Field           | Type    | Notes                                                               |
| --------------- | ------- | ------------------------------------------------------------------- |
| `source_id`     | string  | Context tweet/status ID.                                            |
| `text`          | string  | Context post text.                                                  |
| `author_handle` | string  | Context post author handle (without `@`).                           |
| `context_type`  | enum    | One of: `parent`, `ancestor`, `conversation_root`, `sibling_reply`. |
| `distance`      | integer | Relative hop distance from reply (`1` = immediate relation).        |

Optional item fields:

| Field            | Type              | Notes                                         |
| ---------------- | ----------------- | --------------------------------------------- |
| `author_id`      | string            | Context author ID.                            |
| `source_url`     | string            | Context post URL.                             |
| `created_at`     | string (ISO 8601) | Context post timestamp.                       |
| `public_metrics` | object            | Public metrics snapshot for the context post. |

## Example Record

```json
{
  "id": "2017906312416465342",
  "platform": "x",
  "source_id": "2017906312416465342",
  "source_url": "https://x.com/CryptoKing_2020/status/2017906312416465342",
  "collected_at": "2026-02-12T10:26:00Z",
  "text": "Amazing insight! Totally agree.",
  "labels": ["ai_generated_reply", "reply_spam", "low_effort"],
  "is_reply": true,
  "conversation_id": "2017901000000000000",
  "parent_id": "2017906200000000000",
  "parent_text": "Thread: Risk controls that every trader should automate.",
  "reply_author": {
    "handle": "CryptoKing_2020",
    "user_id": "1890012345678901234",
    "display_name": "THE CRYPTO KING",
    "verified": true,
    "follower_count": 312,
    "following_count": 5421,
    "bio": "Crypto alpha | DM for business",
    "created_at": "2025-11-03T00:00:00Z",
    "tweet_count": 18974,
    "listed_count": 1,
    "profile_collected_at": "2026-02-12T10:20:00Z"
  },
  "parent_author": {
    "handle": "legit_trader",
    "user_id": "1200012345678901234",
    "display_name": "Legit Trader",
    "verified": true,
    "follower_count": 145220,
    "following_count": 801,
    "bio": "Market structure and execution",
    "created_at": "2018-05-13T00:00:00Z",
    "tweet_count": 15420,
    "listed_count": 902,
    "profile_collected_at": "2026-02-12T10:20:00Z"
  },
  "reply_metrics": {
    "like_count": 0,
    "reply_count": 0,
    "repost_count": 0,
    "quote_count": 0
  },
  "parent_metrics": {
    "like_count": 162,
    "reply_count": 97,
    "repost_count": 29,
    "quote_count": 4
  },
  "thread_context": [
    {
      "source_id": "2017906100000000000",
      "text": "1/ Most losses come from poor sizing, not entries.",
      "author_handle": "legit_trader",
      "context_type": "ancestor",
      "distance": 2,
      "created_at": "2026-02-12T09:58:10Z",
      "source_url": "https://x.com/legit_trader/status/2017906100000000000"
    }
  ],
  "urls": [],
  "addresses": [],
  "notes": "Generic high-valence agreement with no reference to parent content."
}
```

## File Layout

| File                               | Contents                                                                                                                          | Label confidence    |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| `data/replies.jsonl`               | Replies **explicitly tagged** as AI by humans on X (e.g. someone replying "AI reply" / "blocked for AI reply" to a specific post) | High — ground truth |
| `data/replies_inferred.jsonl`      | Replies we **suspect** are AI based on heuristics, account signals, or classifier output                                          | Lower — inferred    |
| `data/flagged-ai-reply-bots.jsonl` | Account-level list of flagged AI reply bot handles (from any tagger)                                                              | Account-level only  |

**Rule:** Never mix ground truth and inferred data. See `docs/AI_REPLY_SCRAPING.md` for the full scraping strategy.

## Validation

Use the dedicated integrity checker:

```bash
python scripts/check_reply_integrity.py data/replies.jsonl
```

Strict mode (warnings fail validation):

```bash
python scripts/check_reply_integrity.py data/replies.jsonl --strict
```
