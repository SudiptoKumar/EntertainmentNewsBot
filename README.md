# Entertainment News Bot

> Selective movie, OTT, and scripted-series news intelligence for Telegram, built for **@EntertainmentNewsroom**.

The bot is designed as an **editorial desk, not a news scraper**. It discovers a large candidate pool, separates stories into three editorial sectors, ranks each sector independently, deduplicates events, verifies the highest-ranked stories, and publishes only stories that clear the importance threshold.

## Editorial Mission

The channel covers only **major entertainment news**:

- Hollywood movies and scripted series
- Indian cinema, especially major Bollywood and pan-Indian projects
- High-profile Korean and Chinese film/drama
- Major OTT and streaming developments
- International OTT collaborations and distribution
- Major casting tied to significant productions
- Major trailers, teasers, posters and first looks
- Major release dates, renewals and cancellations
- Major franchise, studio, platform and production-house developments

The channel is deliberately **not** a general celebrity/showbiz feed.

## The Three-Sector Ranking Model

A single global rank would naturally favor Hollywood because Hollywood produces more globally visible franchise stories. To prevent that, the bot first creates **three independent leaderboards**:

```text
                 DISCOVERY
                     |
       +-------------+-------------+
       |             |             |
   HOLLYWOOD       INDIAN      INTERNATIONAL
       |             |             |
    Rank 0-100    Rank 0-100    Rank 0-100
       |             |             |
     >= 80         >= 80         >= 80
       +-------------+-------------+
                     |
              BALANCED MERGE
                     |
              EVENT DEDUPLICATION
                     |
                 VERIFICATION
                     |
                  PUBLISH
```

### Hollywood

Major studio films, franchises, premium streaming originals, major series, important casting, major trailers, release-date changes, distribution deals and other globally significant projects.

### Indian

Major Bollywood titles plus significant Telugu, Tamil, Malayalam, Kannada and other pan-Indian projects. Budget is a signal, not an automatic pass. The system favors large-scale projects, established stars/directors, major production houses, franchises, multi-language releases and major OTT/international distribution.

### International

Selective high-profile Korean and Chinese film/drama, especially projects connected to reputable production houses, major platforms or broadcasters, recognized actors, and international distribution through services such as Netflix, Disney+, Viki, TVING, iQIYI, Tencent Video and Youku.

## No Mandatory Number of Posts

There is **no six-post requirement** and no category quota.

The bot can publish zero, one, three, ten, or any number of stories supported by the qualifying candidate pool, subject only to the optional Telegram safety limit.

The rule is:

```text
Importance Score >= 80
        AND
Verification Pass
        =
Publishable
```

A 79-point story is not published merely because the channel is quiet.

## Ranking Algorithm

Each sector is scored independently from 0 to 100 using eight dimensions:

| Factor | Weight |
|---|---:|
| Event significance | 25% |
| Audience / fan impact | 20% |
| Project / IP / franchise importance | 15% |
| Platform / studio / production-house importance | 10% |
| Cast / director / creator recognition | 10% |
| International / cross-market reach | 10% |
| News novelty | 5% |
| Recency | 5% |
| **Total** | **100%** |

The LLM returns the eight factor scores. The application then computes the weighted score deterministically.

### Score interpretation

```text
90-100  Exceptional major entertainment news
85-89   Very high importance
80-84   Publishable major news
70-79   Interesting, but below threshold
50-69   Low priority
0-49    Weak, excluded, routine, gossip, rumor or niche
```

## Cross-Sector Balancing

After independent ranking:

1. The strongest qualifying story from each sector becomes a **protected anchor** when available.
2. Remaining candidates compete by score.
3. A small sector-saturation penalty prevents one sector from dominating when another sector has a similarly strong story.
4. The system never lowers a story below 80 to fill a sector.
5. Event duplicates are removed before publication.

This means a 94-point Hollywood story still beats a 81-point Indian story, but several 90+ Hollywood stories do not automatically crowd out a 89-88 Indian or International story.

## Editorial Exclusions

Normally rejected:

- Celebrity lifestyle
- Dating/relationship news
- Breakups
- Fashion
- Vacations
- Airport sightings
- Instagram/social posts
- Birthdays
- Paparazzi
- Award-show fashion or attendance
- Fan wars
- Gossip
- Minor interviews
- Rumors and speculation
- Routine catalog additions
- Minor productions with limited relevance
- Routine production updates

An actor/actress can be covered when the news is directly connected to a major movie or series.

## OTT Coverage

The monitored platform universe includes:

- Netflix
- Amazon Prime Video
- HBO / HBO Max
- Apple TV+
- Disney+
- Hulu
- Paramount+
- Peacock
- SonyLIV
- JioHotstar
- Viki
- TVING
- iQIYI
- Tencent Video
- Youku

A platform mention does **not** automatically make a story publishable. The underlying title/event must be significant.

## Source Strategy

### Primary / official confirmation

- Netflix Newsroom / Tudum
- Warner Bros. Discovery / HBO press
- Apple TV / Apple Newsroom
- Amazon / Prime Video
- Disney / Disney+
- Paramount
- Peacock / NBCUniversal
- Sony Pictures
- Warner Bros.
- Marvel
- DC
- Major Indian studios and production houses
- Major Korean platforms, broadcasters and production companies
- Tencent Video
- iQIYI
- Youku

### Industry discovery

- Deadline
- Variety
- The Hollywood Reporter
- TheWrap
- IndieWire
- Collider
- TVLine
- OTTplay
- Filmibeat
- Pinkvilla
- Bollywood Hungama
- Indian Express Entertainment
- Soompi
- DramaZOOM
- Other approved regional sources

Industry sources are discovery inputs. Major claims should be confirmed against the strongest available source when possible.

## Discovery Pipeline

```text
Official sources
      ↓
Industry publications
      ↓
Regional movie/drama sources
      ↓
RSS
      ↓
Google News RSS gap-fill
      ↓
Exa gap-fill
      ↓
Sector classification
      ↓
Candidate filtering
      ↓
Independent sector ranking
      ↓
0-100 weighted score
      ↓
80+ threshold
      ↓
Event clustering / deduplication
      ↓
Cross-sector balancing
      ↓
Article extraction
      ↓
Story generation
      ↓
Claim + numeric verification
      ↓
Image card
      ↓
Telegram
```

## Event Deduplication

Multiple websites reporting the same event are treated as **one underlying event**.

Example:

```text
Deadline:  Actor joins Netflix thriller
Variety:   Star cast in Netflix thriller
THR:       Netflix thriller adds major actor
                     |
                     v
              ONE EVENT CLUSTER
```

A later meaningful development can still be published:

```text
Project announced       -> may publish
Major casting announced -> may publish
First trailer released  -> may publish
Now streaming           -> may publish
```

Each stage must independently clear the editorial bar.

## Verification

Importance and factual accuracy are separate gates.

Before publication the bot checks:

- Headline claims
- Dates
- Cast
- Platform
- Episode/season information
- Budget figures when used
- Languages
- Release information
- Numeric claims

Failed verification causes regeneration or rejection.

## Telegram Format

```text
Photo / Poster

⚡ HEADLINE

1-sentence summary

📌 KEY HIGHLIGHTS
• Fact
• Fact
• Fact

📝 THE STORY
2-4 sentences of relevant context.

📺 RELEASE / AVAILABILITY
• Platform
• Release date
• Episodes
• Languages

🔗 Source: Publication / Official source

@EntertainmentNewsroom #update
```

Sections are dynamic. Empty metadata is not added just to satisfy a template.

## Repository Structure

```text
EntertainmentNewsBot/
│
├── .github/
│   └── workflows/
│       └── newbot.yml
│
├── main.py
├── requirements.txt
├── news_state.json
├── posted_urls.txt
├── README.md
└── .gitignore
```

`main.py` contains the complete discovery, extraction, ranking, verification, image, Telegram and state machinery. The repository intentionally stays single-file for easy maintenance. The three editorial sectors and their source/query universe are defined near the top of `main.py`.

## Environment

Required secrets:

```text
EXA_API_KEY
CEREBRAS_API_KEY
TELEGRAM_BOT_TOKEN
```

Optional:

```text
TELEGRAM_ADMIN_CHAT_ID
CEREBRAS_MODEL
PUBLISH_THRESHOLD
TELEGRAM_PUBLISH_LIMIT
```

Recommended defaults:

```text
TELEGRAM_CHANNEL=@EntertainmentNewsroom
NEWS_MODE=entertainment
PUBLISH_THRESHOLD=80
TELEGRAM_PUBLISH_LIMIT=12
```

`TELEGRAM_PUBLISH_LIMIT` is only an operational safety ceiling. It is **not** an editorial target.

## Local Checks

```bash
python -m py_compile main.py

EXA_API_KEY=dummy \
CEREBRAS_API_KEY=dummy \
TELEGRAM_BOT_TOKEN=dummy \
EXA_API_KEY=dummy \
CEREBRAS_API_KEY=dummy \
TELEGRAM_BOT_TOKEN=dummy \
python main.py --self-test

python main.py
```

## Core Principle

> **@EntertainmentNewsroom publishes the entertainment news that matters, not all entertainment news that exists.**

The system is intentionally comfortable with a quiet run when no story clears the bar.


# Dynamic Telegram Template

The bot uses a dynamic Rich HTML renderer based on the project's Telegram template specification.

Supported event templates:

- Release / streaming
- Breaking
- Trailer / teaser
- Renewal
- Cancellation
- Box office
- Spoiler-sensitive
- General update

The renderer adapts the post to the event rather than forcing every story into one fixed layout. It uses bold hooks/titles, italic metadata, code-style factual badges, expandable context, clickable source/action links, and optional spoiler formatting.

`telegram_news_template.md` documents the intended visual semantics and reusable template variants.
