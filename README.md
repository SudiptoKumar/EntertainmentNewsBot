# EntertainmentNewsBot v1.0.1

Entertainment Newsroom built by porting the working GamingNewsroom reliability framework and replacing only the editorial domain, sources, taxonomy and story format.

Pipeline: RSS → Google News → Exa → source validation → 24h window → URL/event deduplication → excerpt enrichment → Cerebras ranking in batches of 15 → event collapse → recovery pool → extraction → generation → numeric grounding → claim verification → event-status verification → branded 1200×675 image → Telegram Rich Message → Bot API fallback → persistent state.

Required secrets: `EXA_API_KEY`, `CEREBRAS_API_KEY`, `TELEGRAM_BOT_TOKEN`. Optional: `TELEGRAM_ADMIN_CHAT_ID`, `CEREBRAS_MODEL`.

Run self-test with `EXA_API_KEY=dummy CEREBRAS_API_KEY=dummy TELEGRAM_BOT_TOKEN=dummy python main.py --self-test`.
