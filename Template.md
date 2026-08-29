# Telegram Entertainment News — Dynamic Template System 

This file is the **content/layout specification**. Production delivery uses Telethon native `MessageEntity*` objects rather than sending Markdown/HTML markup. The visual rules below map to bold, italic, code, text-url, spoiler, and blockquote entities.

---

## 🎨 Formatting Legend — what's used where, and why

| Syntax | Renders as | Used for | Why |
|---|---|---|---|
| `*text*` | **Bold** | Hooks, titles, key numbers | Grabs the eye first |
| `_text_` | *Italic* | Meta info (country/genre), show names in-line | Secondary emphasis, doesn't compete with bold |
| `` `text` `` | `Code` | Status tags, episode counts, platform names | Monospace box makes it read like a **badge/chip** |
| `[text](url)` | Clickable link | Source, watch links | No more bare "🔗 [Source]" — it's tappable |
| `\|\|text\|\|` | Spoiler | Plot twists, post-credit scenes, endings | Reader taps to reveal — protects people from spoilers |
| `> text` | Blockquote | Synopsis, disclaimers/notes | Visually separates it as a callout, not body text |
| `*Bold _italic_*` | **Bold with *italic* inside** | Hook line + title combo | One line, two levels of emphasis |

---

## 🧩 Core Blocks (updated syntax)

```
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

🔗 [{Source Name}]({URL})

@channel #tag
```

**Why the changes:**
- `Status`, `Episodes`, `Platform` wrapped in `` `code` `` — they now look like little badges instead of blending into plain text.
- Synopsis and Note are now `>` blockquotes — they visually separate from the "hard facts" blocks above/below them.
- Source is a real markdown link, not just a label — one tap, no copy-pasting URLs.
- Spoiler block is new — use it any time a detail would ruin the story for someone who hasn't watched yet.

---

## 🎯 Hook Legend (bold + italic combo)

| News Type | Hook |
|---|---|
| Unconfirmed / rumor | `*🚨 BREAKING*` |
| Officially confirmed | `*📢 CONFIRMED*` |
| New streaming release | `*🔥 NOW STREAMING*` |
| Trailer / teaser | `*🎞️ TRAILER DROP*` |
| Renewed | `*⚡ RENEWED*` |
| Cancelled | `*❌ CANCELLED*` |
| Box office | `*💰 BOX OFFICE*` |
| Exclusive | `*⭐ EXCLUSIVE*` |
| Re-release | `*🎥 ENCORE RELEASE*` |

For a hook that names the show inline, combine bold + italic:
`*🚨 BREAKING: _{TITLE}_ UPDATE!*`

---

## Ready-to-Use Variants

### 1️⃣ New Release
```
*🔥 NOW STREAMING*

*🎬 {TITLE} ({YEAR})*

_{Country} • {Genre} • {Format}_

> 📖 {synopsis}

📺 *Availability*
• Platform: `{name}`
• Episodes: `{count}`
• Language: `{languages}`
• Status: `Available Now`

📅 *Release:* {date}

🔗 [Watch Now]({url})

@channel #NowStreaming
```

### 2️⃣ Breaking / Rumor
```
*🚨 BREAKING: _{TITLE}_ UPDATE!*

📌 *Reported Details:*
• {detail}
• {detail}

📅 *Expected:* {date/window}

> ℹ️ Not officially confirmed yet.

@channel #Rumor
```

### 3️⃣ Trailer / Teaser Drop
```
*🎞️ TRAILER DROP: {TITLE}*

*🎬 {TITLE} ({YEAR})*

📌 {what the trailer reveals}

📅 *Releases:* {date}

🔗 [Watch Trailer]({url})

@channel #Trailer
```

### 4️⃣ Renewal / Cancellation
```
*⚡ RENEWED: {TITLE}*

📌 {Show} renewed for Season `{X}`

📺 Platform: `{name}`

> ℹ️ {production start / expected date, if known}

🔗 [Source]({url})

@channel #Renewed
```

### 5️⃣ Box Office
```
*💰 BOX OFFICE: {TITLE}*

*🎬 {TITLE} ({YEAR})*

📌 *{Day/Weekend} Collection:* `{amount}`
• Domestic: `{amount}`
• Worldwide: `{amount}`

📅 Days since release: `{X}`

🔗 [Source]({url})

@channel #BoxOffice
```

### 6️⃣ Spoiler-Sensitive Update (new — for finale/twist news)
```
*⭐ EXCLUSIVE: {TITLE} ENDING DETAILS*

*🎬 {TITLE} ({YEAR})*

📌 {non-spoiler framing line — what kind of news this is}

🙈 *Tap to reveal:*
||{the actual spoiler/twist/ending detail}||

> ℹ️ Spoiler warning applies past this point.

@channel #Spoiler
```

---

## Quick Rules
- **Single asterisks only** — `*bold*` not `**bold**`. Double asterisks show as literal stars in Telegram.
- **Badge trick:** wrap any short factual tag (`Status`, `Episodes`, counts) in backticks — instant visual chip with zero extra effort.
- **Blockquote = callout**, not decoration. Use `>` only for synopsis and disclaimer/note — overusing it flattens the effect.
- **Always link the source** — `[Name](url)` beats a bare "🔗 Source" every time.
- **Spoiler tag is opt-in per post** — only add the Spoiler block when the news genuinely contains a reveal; don't force it into every template.
- **Length:** still 4096 chars for text posts, 1024 for photo captions.
