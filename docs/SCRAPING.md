# X Home-Feed Scraping (OpenClaw Browser Automation)

## Purpose
Collect posts from the X home feed via OpenClaw's Chrome relay and append JSONL
records to `data/sample.jsonl` for downstream labeling.

## Prerequisites
- OpenClaw running with Chrome extension relay configured
- Logged into X in your Chrome browser
- Chrome extension relay tab attached (click the OpenClaw Browser Relay toolbar
  button on the X tab - badge should show ON)

## How it works
OpenClaw connects to your existing Chrome session via the Browser Relay extension.
It injects JS to collect tweets, scrolls to load more, dedupes by tweet ID, and
appends results to the dataset.

## Scraping flow
1. Navigate to `https://x.com/home` in Chrome
2. Attach the tab via the OpenClaw Browser Relay extension
3. OpenClaw injects collection JS and scrolls to gather tweets
4. Tweets are deduplicated against existing IDs in `data/sample.jsonl`
5. New records are appended with empty labels for later annotation

## JS selectors used
```js
// Tweet container
document.querySelectorAll('[data-testid="tweet"]')

// Tweet text
el.querySelector('[data-testid="tweetText"]')?.innerText

// Tweet URL (extract ID from /status/...)
el.querySelector('a[href*="/status/"]')?.href
```

## Output schema (minimal for unlabeled data)
```json
{"id": "x_1234567890", "text": "tweet text here", "labels": []}
```

Where:
- `id`: `x_` prefix + tweet ID (numeric string from URL)
- `text`: full tweet text, preserved exactly
- `labels`: empty array `[]` at collection time

## Full schema (for labeled data)
When labeling or enriching, the full schema from `DATA_SOURCES.md` applies:
```json
{
  "id": "x_1234567890",
  "platform": "x",
  "source_id": "1234567890",
  "source_url": "https://x.com/user/status/1234567890",
  "collected_at": "2026-02-03T20:00:00Z",
  "text": "tweet text",
  "labels": ["crypto"],
  "urls": [],
  "addresses": [],
  "notes": ""
}
```

## Output location
Append to: `data/sample.jsonl`

## Deduplication
Before appending, check existing IDs in `data/sample.jsonl` to avoid duplicates.
The tweet ID (numeric part) is the dedup key.

## Scroll parameters (typical)
- Scroll increment: ~2000px
- Delay between scrolls: ~1.5s
- This loads ~20-30 new tweets per scroll cycle
