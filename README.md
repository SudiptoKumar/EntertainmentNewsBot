# EntertainmentNewsroom Final v1.0.0

Automated movie, streaming, and scripted-series news intelligence for Telegram, powered by GitHub Actions, Exa, and Cerebras.

## Editorial mission

This bot is intentionally selective. It prioritizes major Hollywood films and series, major Indian cinema, major streaming-platform developments, significant Korean and Chinese productions, major casting, trailers, first looks, release-date changes, renewals/cancellations, production milestones, rights/distribution deals, and high-impact entertainment-industry developments.

Stories compete in one ranked pool. A story is publishable only at **7/10 or higher**. Weak category coverage never displaces a stronger story.

## Pipeline

```text
RSS
  -> Google News RSS gap fill
  -> Exa gap fill
  -> source + date validation
  -> URL + event deduplication
  -> Cerebras structured editorial ranking
  -> recovery pool
  -> article extraction / Exa fallback
  -> story generation
  -> claim verification
  -> 1200x675 branded card
  -> Telegram Rich Message / Bot API fallback
  -> persistent state
```

## Secrets

Required:

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

The workflow defaults to:

```text
TELEGRAM_CHANNEL=@EntertainmentNewsroom
NEWS_MODE=update
CEREBRAS_MODEL=gpt-oss-120b
```

## Local checks

```bash
python -m py_compile main.py
EXA_API_KEY=dummy CEREBRAS_API_KEY=dummy TELEGRAM_BOT_TOKEN=dummy python main.py --self-test
```

## Scheduling

The included GitHub Actions workflow runs hourly from **07:00 through 23:00 Asia/Dhaka** and also supports manual execution. GitHub Actions cron is expressed in UTC.

## Notes

- Persistent state is stored in `news_state.json`.
- Published URL memory is stored in `posted_urls.txt`.
- The ranking, generation, and verification calls use the official `cerebras_cloud_sdk` client and strict JSON schemas.
- The article pipeline uses local extraction first and Exa search/content signals as a fallback. Exa discovery uses the current `exa.search()` API.
- Failed verification rejects the story instead of publishing unsupported claims.

## Reliability checks

The final build includes a regression test for runtime `datetime` values in persistent state, the failure that affected the beta build. State writes convert datetimes to ISO-8601 strings before JSON serialization. RSS, Exa, extraction, ranking, generation, verification, and Telegram failures are isolated so one failed candidate does not terminate the entire publishing loop.

The GitHub Actions workflow also performs the self-test before the live run.
