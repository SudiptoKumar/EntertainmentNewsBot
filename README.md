# EntertainmentNewsBot V1.1.2

Automated movie, streaming, and scripted-series news publishing for Telegram. The technical execution framework follows the proven GamingNewsroom architecture; the editorial algorithm and public template are Entertainment-specific.

## Editorial sectors

Every candidate is assigned exactly one sector:

- **Hollywood**: US/Hollywood film, series, studio, franchise, streaming, and industry news.
- **Indian**: Bollywood, major Pan-Indian productions, Indian cinema/series/OTT, and major India-led entertainment business news.
- **International**: major non-Indian, non-Hollywood global entertainment and cross-border developments, including Korean and Chinese productions.

Sectors are classification lanes, not quotas.

## Publication algorithm

The old six-post rule is removed. There is no fixed number of posts per run.

A candidate is publishable only when its deterministic composite score is **80/100 or higher** and every verification gate passes.

| Component | Maximum |
|---|---:|
| Significance | 20 |
| Audience / industry reach | 15 |
| Event magnitude | 15 |
| Platform / franchise / IP strength | 10 |
| Source authority | 15 |
| Evidence strength | 10 |
| International relevance | 5 |
| Recency | 5 |
| Audience anticipation | 5 |
| **Total** | **100** |

Cerebras returns the bounded components. Python calculates the final score. Rumor/speculation is hard-capped below the publication threshold.

## Discovery

```text
RSS → Google News gap fill → Exa gap fill
    → source validation → 24h filter
    → URL dedup → event/entity dedup
    → thin-excerpt enrichment
    → Cerebras ranking in batches of 15
    → global score merge → event collapse
    → 80+ candidates
    → extraction → generation
    → metadata grounding → numeric grounding
    → claim verification → event-status verification
    → image → Telegram Rich Message
    → Bot API sendPhoto fallback → persistent state
```

## Editorial rules

- Judge the underlying event, not headline excitement.
- Major franchise, platform, studio, distribution, casting, release, renewal/cancellation, production, trailer, box-office, and industry developments receive priority when genuinely significant.
- Celebrity lifestyle, gossip, minor casting, routine catalog additions, fan theories, weak promotions, and unsupported rumors are normally rejected.
- Official sources outrank reputable reporting for confirmation.
- Duplicate coverage of an already-published event is rejected even when the URL differs.
- No weak story is published to satisfy a sector balance.

## Dynamic Telegram template

`Template.md` is the authoritative public formatting specification. It uses different structures for New Release, Breaking/Reported, Trailer/Teaser, Renewal/Cancellation, Box Office, and Spoiler-Sensitive updates.

The removed `THE CONTEXT` and `BOTTOM LINE` blocks are not generated. The renderer follows the supplied dynamic template instead.

Telegram formatting follows the uploaded template: bold hooks/titles, italic metadata, code-style factual badges, clickable source/watch links, blockquotes for synopsis/notes, and optional spoiler formatting.

## Reliability

- Candidate failures do not terminate the run.
- Failed feeds are isolated and tracked.
- Ranking is bounded in batches of 15.
- Persistent state uses JSON-safe ISO timestamps.
- State writes are atomic.
- Telegram has retry handling and a standard `sendPhoto` fallback.
- Image selection prefers official key art/stills, then article/editorial images, then a branded fallback.

## Required GitHub Secrets

```text
EXA_API_KEY
CEREBRAS_API_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_API_ID
TELEGRAM_API_HASH
```

Optional:

```text
TELEGRAM_ADMIN_CHAT_ID
CEREBRAS_MODEL
```

Workflow configuration:

```text
TELEGRAM_CHANNEL=@EntertainmentNewsroom
NEWS_MODE=update
CEREBRAS_MODEL=gpt-oss-120b
```

## Schedule

GitHub Actions runs hourly from 07:00 through 23:00 Asia/Dhaka and supports manual execution.

## Local validation

```bash
python -m py_compile main.py
EXA_API_KEY=dummy CEREBRAS_API_KEY=dummy TELEGRAM_BOT_TOKEN=dummy python main.py --self-test
python main.py
```

The self-test covers scoring, the 80-point gate, all supported dynamic template variants, numeric grounding, event collapse, 15-item ranking batches, JSON-safe state persistence, and the removed Context/Bottom-Line blocks.

## Deployment note

The code can be syntax-tested and mock-integrated locally, but live Exa, Cerebras, image, and Telegram delivery must be exercised by GitHub Actions with the real secrets.

### Telegram delivery

The production publisher uses Telethon MTProto with native Telegram message entities. The post is built as plain text plus `MessageEntityBold`, `MessageEntityItalic`, `MessageEntityCode`, `MessageEntityTextUrl`, `MessageEntitySpoiler`, and `MessageEntityBlockquote` objects rather than sending Markdown/HTML markup. Telethon's `send_file()` supports `formatting_entities`, so the branded image and rich caption are sent together.

Required Telegram secrets:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_API_ID
TELEGRAM_API_HASH
```

`TELEGRAM_API_ID` and `TELEGRAM_API_HASH` come from `my.telegram.org`. The bot token comes from BotFather.
