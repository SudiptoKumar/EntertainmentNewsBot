# EntertainmentNewsBot V1

EntertainmentNewsBot V1 is an update-only entertainment newsroom using the same proven execution framework as the working BusinessNewsroom project, with Entertainment-specific editorial scoring and presentation.

## Required secrets

```text
EXA_API_KEY
CEREBRAS_API_KEY
TELEGRAM_BOT_TOKEN
```

No `TELEGRAM_API_ID` or `TELEGRAM_API_HASH` is required. Telegram publishing uses the Bot API Rich Message path already proven by the working BusinessNewsroom implementation.

## Editorial sectors

Exactly three sectors:

- Hollywood
- Indian
- International

There is no sector quota.

## Publication gate

A candidate must score **80/100 or higher** and pass all factual and publication checks.

There is no fixed six-post quota.

## News priority

### Tier 1
1. OTT / Streaming Availability
2. Hindi Dub / Language Availability
3. Upcoming OTT Releases
4. Release Date Confirmations

### Tier 2
5. New Movie / Series Announcements
6. Season Renewals / New Season Updates
7. Trailer Releases
8. First Look / First Glimpse / Posters

### Tier 3
9. Cast / Character Announcements
10. Theatrical Releases / Re-releases
11. Production / Filming Updates
12. OTT Platform Acquisition / Streaming Rights
13. Box Office Updates

Priority is an editorial preference, not a quota. Higher-priority qualifying stories are preferred when scores are otherwise competitive. The 80/100 gate is always required.

## 100-point editorial score

- Significance: 20
- Audience / industry reach: 15
- Event magnitude: 15
- Platform / franchise / IP strength: 10
- Source authority: 15
- Evidence strength: 10
- International relevance: 5
- Recency: 5
- Audience anticipation: 5

The model returns the bounded components; Python calculates the final score.

## Discovery and publishing pipeline

```text
RSS
  ↓
Google News gap fill
  ↓
Exa gap fill
  ↓
Source validation
  ↓
24-hour window
  ↓
URL deduplication
  ↓
Event/entity deduplication
  ↓
Thin-excerpt enrichment
  ↓
Cerebras ranking in batches of 15
  ↓
Priority-aware global ordering
  ↓
80+ gate
  ↓
Article extraction
  ↓
Structured story generation
  ↓
Numeric grounding
  ↓
Claim verification
  ↓
Event-status verification
  ↓
Image selection
  ↓
Telegram Rich Message
  ↓
sendPhoto fallback
  ↓
Persistent state
```

## Final Telegram V1 structure

The visible post deliberately has no section headings such as `Availability` or `What's New`.

```text
Photo

{HOOK}

🎬 {TITLE} ({YEAR})

✦ Platform: ...
✦ Episodes: ...
✦ Language: ...
✦ Status: ...
✦ Release: ...

📖 Short synopsis.

✦ Important fact
✦ Important fact
✦ Important fact

(optional expandable note)

@EntertainmentNewsroom #tag #tag

Source: Publication
```

Only supported fields are shown. Empty or unsupported fields disappear.

### Rich formatting

Python builds the Rich HTML deterministically. The model does not write Markdown or HTML.

- Hook: bold
- Title: bold, large heading
- `Platform`, `Episodes`, `Language`, `Status`, `Release`: bold labels
- Details: `✦`
- Synopsis: blockquote
- Optional spoiler: native `<tg-spoiler>`
- Optional caveat/dub/availability note: expandable `<details>` block
- Source publication name: bold label + clickable publication name

## Image pipeline

### OTT / streaming / Hindi-dub / upcoming OTT priority

1. Official full poster
2. Official alternate poster
3. Official platform/studio artwork
4. Article image
5. Official source logo fallback
6. Source-name fallback

Portrait posters are sent as portrait images with their original aspect ratio preserved. They are never forced into a 16:9 crop or padded into a landscape frame.

**Posters do not receive `@EntertainmentNewsroom` branding.**

Normal editorial photos may receive the channel branding chip.

## Local validation

```bash
python -m py_compile main.py
EXA_API_KEY=dummy CEREBRAS_API_KEY=dummy TELEGRAM_BOT_TOKEN=dummy TELEGRAM_CHANNEL=@EntertainmentNewsroom PYTHONPATH=../teststubs python main.py --self-test
```

## GitHub Actions

The included workflow supports manual execution and hourly scheduled runs from 07:00 through 23:00 Asia/Dhaka.
