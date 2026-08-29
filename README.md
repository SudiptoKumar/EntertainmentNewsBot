# Entertainment Newsroom V1

Automated movie, streaming, and scripted-series news intelligence for Telegram, powered by GitHub Actions, Exa, Cerebras, RSS/Google News, and batched editorial ranking.

The bot targets **@EntertainmentNewsroom** and follows the supplied editorial policy: selective top-news coverage across Hollywood, Indian cinema, Korean drama, Chinese drama, and major streaming platforms. Stories compete in one ranked pool and must clear an importance score of **7/10** before publication.

## Project structure

```text
EntertainmentNewsBot/
├── .github/
│   └── workflows/
│       └── newbot.yml
├── main.py
├── requirements.txt
├── README.md
├── news_state.json
└── posted_urls.txt
```

## Pipeline

```text
RSS feeds
  ↓
Google News RSS gap fill
  ↓
Exa gap fill
  ↓
Allowed-domain validation
  ↓
24-hour filter + URL deduplication
  ↓
Cerebras ranking in batches of 15
  ↓
Global score merge + soft market diversity
  ↓
Sequential article extraction
  ↓
Verification against article evidence
  ↓
Story generation
  ↓
Branded 1200×675 image
  ↓
Telegram photo + rich HTML caption
  ↓
Persistent state
```

## Editorial behavior

- Publish only candidates scoring **7–10**.
- Rank significance, reach, production scale, platform importance, franchise/IP strength, cast/director prominence, international relevance, and audience anticipation.
- Reject routine celebrity lifestyle/gossip, unsupported rumors, generic interviews, minor casting, low-value promotions, ordinary catalog additions, and duplicate event coverage.
- Use soft market diversity only after importance ranking. Diversity never lowers the importance threshold.
- Keep a rolling published-event history to avoid near-duplicate follow-ups.

## Telegram format

Each post contains:

1. Branded photo card
2. 6–14 word headline
3. Exactly one-sentence summary
4. 3–5 key highlights
5. Expandable **THE CONTEXT** blockquote
6. Expandable **BOTTOM LINE** blockquote
7. Hashtags
8. Clickable source link

Telegram's current HTML parse mode supports expandable blockquotes, which this bot uses for the context and takeaway sections.

## GitHub setup

1. Create a Telegram bot with **@BotFather** and add it as an administrator to `@EntertainmentNewsroom` with permission to post messages.
2. Create GitHub repository secrets:

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

3. Push this project to the repository.
4. Enable GitHub Actions.
5. Run **Entertainment Newsroom Bot → Run workflow** once manually.

The workflow then runs every 3 hours at minute 17 UTC. Change the cron expression in `.github/workflows/newbot.yml` to your preferred cadence.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export EXA_API_KEY="..."
export CEREBRAS_API_KEY="..."
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHANNEL="@EntertainmentNewsroom"

python main.py --self-test
python main.py
```

## Operational notes

- `news_state.json` stores a rolling list of published events and last-run metadata.
- `posted_urls.txt` provides URL-level duplicate prevention across GitHub Action executions.
- The workflow commits those two files back to the repository after a run.
- If image extraction fails, the bot generates a branded fallback card.
- If verification fails or article text cannot be extracted, the candidate is skipped rather than published.
- Exa and Cerebras failures are handled per stage so one failed candidate or one search call does not crash the entire run.
