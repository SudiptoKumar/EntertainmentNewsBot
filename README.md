# Entertainment Newsroom V1

Automated update-only entertainment news for Telegram. The technical framework follows the proven BusinessNewsroom Bot API Rich Message architecture. The editorial system is entertainment-specific.

## Telegram credentials

Only these Telegram credentials are required:

```text
TELEGRAM_BOT_TOKEN
```

No Telethon account session, `TELEGRAM_API_ID`, or `TELEGRAM_API_HASH` is required.

## Editorial sectors

Every candidate belongs to one of three sectors:

- Hollywood
- Indian
- International

These are classification sectors, not quotas.

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

Priority determines editorial ordering. It is not a publishing quota.

## Publication gate

The final editorial score is 0-100. A candidate is publishable only at **80/100 or higher** and only after all verification gates pass.

The score is calculated from explicit components:

- Significance: 20
- Audience / industry reach: 15
- Event magnitude: 15
- Platform / franchise / IP strength: 10
- Source authority: 15
- Evidence strength: 10
- International relevance: 5
- Recency: 5
- Audience anticipation: 5

Rumor/speculation is hard-capped below the publication threshold.

## Discovery and editorial pipeline

```text
RSS
→ Google News RSS gap fill
→ Exa gap fill
→ source validation
→ 24-hour rolling window
→ URL deduplication
→ event/entity deduplication
→ thin-excerpt enrichment
→ Cerebras ranking in batches of 15
→ global merge using priority tier/rank, then score
→ 80+ publication gate
→ ranked recovery candidates
→ article extraction
→ structured story generation
→ numeric grounding
→ claim verification
→ event-status verification
→ image selection
→ deterministic Rich HTML rendering
→ Telegram sendRichMessage + attached photo
→ Bot API sendPhoto fallback
→ persistent state
```

## Telegram content model

The public message uses one clean reader-first design. News type changes the content and hook, not the overall visual language.

```text
Photo
Hook
🎬 Title (Year)
📺 Availability when supported
📖 Short synopsis
📌 What's New
🙈 Optional spoiler
⌄ Optional expandable caveat
@channel #tags
Source: Name (clickable)
```

No `What to Know`, `Vocabulary`, `THE CONTEXT`, or `BOTTOM LINE` sections are generated.

## Rich Message implementation

The message is assembled by Python from structured Cerebras output. The model never writes Markdown or HTML into the final message.

The working BusinessNewsroom architecture uses Telegram Bot API `sendRichMessage` with Rich HTML and an attached photo. The Entertainment bot uses the same transport pattern.

## Image policy

For OTT/streaming/language/upcoming-release stories, the image selector prefers the official full poster and preserves the poster without cropping.

Normal editorial photos may use the standard 1200×675 branded card.

Posters and source-logo fallback cards do **not** contain `@EntertainmentNewsroom` branding.

## Required secrets

```text
EXA_API_KEY
CEREBRAS_API_KEY
TELEGRAM_BOT_TOKEN
```

Optional:

```text
TELEGRAM_ADMIN_CHAT_ID
CEREBRAS_MODEL
```

## Scheduling

The GitHub Actions workflow runs hourly from 07:00 through 23:00 Asia/Dhaka and supports manual execution.

## Local checks

```bash
python -m py_compile main.py
EXA_API_KEY=dummy CEREBRAS_API_KEY=dummy TELEGRAM_BOT_TOKEN=dummy python main.py --self-test
python main.py
```
