# Entertainment Newsroom V1

Automated, update-only entertainment news for Telegram. Technical transport follows the proven BusinessNewsroom Bot API Rich Message architecture. Editorial rules are entertainment-specific.

## Editorial model

Three sectors compete in one global pool:

- Hollywood
- Indian
- International

There is no fixed six-post rule and no sector quota. A story is publishable only when its deterministic editorial score is **80/100 or higher** and all verification gates pass.

### 100-point editorial score

- Significance: 20
- Audience / industry reach: 15
- Event magnitude: 15
- Platform / franchise / IP strength: 10
- Source authority: 15
- Evidence strength: 10
- International relevance: 5
- Recency: 5
- Audience anticipation: 5

Rumor/speculation is hard-capped below 80.

## Technical pipeline

```text
RSS → Google News RSS → Exa → source validation → 24h filter
→ URL dedup → event/entity dedup → thin-excerpt enrichment
→ Cerebras ranking in batches of 15 → global merge
→ 80+ gate → recovery pool → article extraction
→ structured story generation → metadata grounding
→ numeric grounding → claim verification → event-status verification
→ branded image → Telegram Rich Message → Bot API sendPhoto fallback
→ persistent state
```

The Telegram transport uses the Bot API `sendRichMessage` method with Rich HTML and an attached photo. No Telethon account session is required.

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

## Telegram structure

Every published story uses the same clean master structure defined in `Template.md`:

```text
Photo
Hook
🎬 Title (Year)
Country • Genre • Format
📖 Synopsis
📌 What's New:
• fact
• fact
• fact
📺 Availability (only when supported)
📅 Release (only when supported)
🙈 Spoiler (optional)
⌄ ℹ️ More to Know (optional expandable block)
@channel #tag
Source: Name (clickable)
```

`What to Know`, `Vocabulary`, `THE CONTEXT`, and `BOTTOM LINE` are not used.

Formatting is produced by Python Rich HTML, not by model-generated Markdown. Telegram's current Bot API supports Rich HTML, expandable details blocks, spoiler formatting, media references, and `sendRichMessage`.

## Local checks

```bash
python -m py_compile main.py
EXA_API_KEY=dummy CEREBRAS_API_KEY=dummy TELEGRAM_BOT_TOKEN=dummy python main.py --self-test
python main.py
```
