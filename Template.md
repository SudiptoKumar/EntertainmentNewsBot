# Entertainment News Telegram V1 Template

This file is the authoritative **visible post structure** for V1.

## Master structure

```text
Photo

*{HOOK}*

# 🎬 {TITLE} ({YEAR})

✦ *Platform:* {Platform}
✦ *Episodes:* {count}
✦ *Language:* {languages}
✦ *Status:* {status}
✦ *Release:* {date}

> 📖 {short synopsis}

✦ {important fact}
✦ {important fact}
✦ {important fact}

{optional expandable caveat / unconfirmed note / dub or regional note}

@channel #tag #tag

*Source:* Name (Name URL attached)
```

The `#` above is only documentation notation for a heading. It must not be emitted in the Telegram message.

## Rules

- Movie or series name must be the clear title line followed by `(Year)` when the year is source-supported.
- Do not add `Hollywood • Industry • Industry`, `Availability`, `What's New`, `What to Know`, `Vocabulary`, `THE CONTEXT`, or `BOTTOM LINE` as visible section headings.
- Availability information is represented directly as `✦` rows.
- Release information is represented directly as `✦ *Release:* ...` and should not be duplicated.
- Details always use `✦`, not `•`.
- Synopsis uses the `📖` blockquote.
- Spoiler is optional and uses Telegram Rich HTML spoiler markup.
- Caveats such as unconfirmed status, regional availability, or dub information use an expandable Rich HTML block only when genuinely useful.
- Source is `*Source:* Name`, where `Name` is a clickable link.
- No raw URL is displayed.
- No Markdown or HTML is produced by the LLM. Python renders all formatting.

## Priority-aware ordering

The same visual grammar is used for all stories, but the information order reflects the story type.

### OTT / Streaming Availability

```text
🔥 NOW STREAMING

🎬 Title (Year)

✦ Platform: Netflix
✦ Status: Streaming 🔥

📖 Short synopsis.

✦ Added to Netflix today
✦ Hindi and English audio available
✦ 4K available

@channel #Netflix #Streaming

*Source:* Name
```

### Hindi Dub / Language Availability

```text
🇮🇳 HINDI DUB AVAILABLE

🎬 Title (Year)

✦ Platform: Netflix
✦ Language: Hindi, English
✦ Status: Streaming 🔥

📖 Short synopsis.

✦ Hindi dub is now available
✦ English audio remains available

@channel #HindiDub #Netflix

*Source:* Name
```

### Upcoming OTT Release

```text
📺 UPCOMING OTT RELEASE

🎬 Title (Year)

✦ Platform: Apple TV+
✦ Release: September 9, 2026

📖 Short synopsis.

✦ Platform confirmed the premiere
✦ Season 1 will contain 8 episodes

@channel #AppleTV #Streaming

*Source:* Name
```

### Release Date Confirmation

```text
📅 RELEASE DATE CONFIRMED

🎬 Title (Year)

✦ Platform: Apple TV+
✦ Release: September 9, 2026

📖 Short synopsis.

✦ Apple TV+ confirmed the premiere date
✦ Season 1 will contain 8 episodes

@channel #AppleTV #Streaming

*Source:* Name
```

### Trailer

```text
🎞️ TRAILER RELEASED

🎬 Title (Year)

📖 Short synopsis.

✦ First trailer has been released
✦ The trailer reveals ...
✦ The film/series arrives on ...

@channel #Trailer #Movies

*Source:* Name
```

### Renewal / New Season

```text
🔄 SEASON UPDATE

🎬 Title (Year)

✦ Platform: Netflix
✦ Status: Renewed for Season 2

📖 Short synopsis.

✦ Season 2 has been officially confirmed
✦ Production timing is ...

@channel #Netflix #Series

*Source:* Name
```

### Box Office

```text
💰 BOX OFFICE

🎬 Title (Year)

✦ Worldwide: $500 million
✦ Domestic: $200 million
✦ Status: Day 10

📖 Short synopsis.

✦ The film crossed the latest milestone
✦ International markets contributed ...

@channel #BoxOffice #Movies

*Source:* Name
```

## Image rule

For OTT-related stories, use the complete official poster whenever available. Preserve the original poster ratio. Do not add the channel username to a poster.
