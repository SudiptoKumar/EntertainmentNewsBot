# Entertainment News — Ultimate V1 Template

This is the authoritative public structure. The technical renderer must generate it deterministically through Telegram Rich HTML.

```text
Photo

*{HOOK}*

*🎬 {TITLE} ({YEAR})*

_{Country} • {Genre} • {Format}_

> 📖 {1-3 sentence synopsis}

📌 *What's New:*
• {detail}
• {detail}

📺 *Availability*
• Platform: `{Platform}`
• Episodes: `{count}`
• Language: `{languages}`
• Status: `{Available Now / Coming Soon / Renewed}`

📅 *Release:* {date}

🙈 *Spoiler* (optional, only if relevant)
||{plot twist / ending / post-credit detail}||

> ℹ️ {caveat, unconfirmed note, dub info}

@channel #tag
*Source:* Name (Name URL attached)
```

## Rules

- No `What to Know`.
- No `Vocabulary`.
- No `THE CONTEXT`.
- No `BOTTOM LINE`.
- No generic extra sections.
- Availability fields appear only when supported by the source.
- Release appears only when supported by the source.
- Spoiler is optional and only used for genuine reveals.
- The caveat/note can be rendered as Telegram's expandable `<details>` block.
- Source name is the visible clickable link text. The bare URL must not appear in the rendered message.
- The LLM returns structured fields. Python builds the Rich HTML.
- No literal Markdown or HTML syntax is accepted from the model output.
