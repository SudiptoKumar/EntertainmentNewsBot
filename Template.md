# Entertainment Newsroom V1 Telegram Template

## Master reader-first structure

```text
Photo

*{HOOK}*

*🎬 {TITLE} ({YEAR})*

📺 *Availability*
• Platform: `{Platform}`
• Episodes: `{count}`
• Language: `{languages}`
• Status: `{status}`
• 📅 Release: {date}

> 📖 {short 1-2 sentence synopsis}

📌 *What's New:*
• {most important new fact}
• {second important new fact}
• {third important new fact, optional}

🙈 *Spoiler* (optional, only if genuinely relevant)
||{plot twist / ending / post-credit detail}||

> ℹ️ {optional caveat, unconfirmed note, dub/language note}

@EntertainmentNewsroom #tag #tag
*Source:* Name (Name is the clickable URL)
```

## Rendering rules

- Do not print `What to Know`, `Vocabulary`, `THE CONTEXT`, or `BOTTOM LINE`.
- Do not print `Hollywood • Industry • Industry` or any generic sector/genre/format header.
- The title is the primary visual element after the hook and must be clear and bold.
- The year belongs immediately after the title when supported.
- Availability is placed immediately after the title whenever platform, status, episode count, language, or release information is known.
- Only supported availability fields are shown. Empty/unknown fields are omitted.
- If a release date already appears inside Availability, do not repeat it below.
- The synopsis is short and useful. It should not read like a blog paragraph.
- `What's New` contains 2-3 current, factual developments and does not repeat the synopsis.
- Spoiler is optional and rare.
- The caveat is an optional expandable Rich Message block and replaces the old knowledge/vocabulary blocks.
- The source name is clickable. Never display a raw URL.
- The LLM supplies structured content only. Python generates all Rich HTML deterministically.

## Hook rules

```text
OTT / Streaming Availability        → 🔥 NOW STREAMING
Hindi Dub / Language Availability   → 🇮🇳 HINDI DUB NOW AVAILABLE
Upcoming OTT Releases               → 📺 OTT RELEASE ANNOUNCED
Release Date Confirmations          → 📅 RELEASE DATE CONFIRMED
New Movie / Series Announcements    → 🎬 NEW ANNOUNCEMENT
Season Renewals / New Season        → 🔄 SEASON UPDATE
Trailer Releases                    → 🎞️ TRAILER RELEASED
First Look / Posters                → 👀 FIRST LOOK
Cast / Character Announcements      → 🎭 CAST ANNOUNCEMENT
Theatrical / Re-release              → 🎬 THEATRICAL UPDATE
Production / Filming                 → 🎥 PRODUCTION UPDATE
OTT Rights / Distribution            → 🌍 STREAMING RIGHTS UPDATE
Box Office Updates                   → 💰 BOX OFFICE UPDATE
```

## Dynamic availability examples

### Streaming now

```text
📺 Availability
• Platform: `Paramount+`
• Status: `Streaming 🔥`
```

### Upcoming release

```text
📺 Availability
• Platform: `Apple TV+`
• 📅 Release: September 9, 2026
```

### Series with episode count

```text
📺 Availability
• Platform: `Netflix`
• Episodes: `8`
• Status: `Coming Soon`
• 📅 Release: September 24, 2026
```

### Language update

```text
📺 Availability
• Platform: `Netflix`
• Language: `Hindi, English`
• Status: `Streaming 🔥`
```

### No platform information

If the story is a film production or casting update and no platform information is supported, omit the Availability section entirely.

## Image rules

### Normal editorial image

A usable article/editorial image is cropped to the standard 1200×675 card and carries the `@EntertainmentNewsroom` brand chip at bottom-right.

### OTT / streaming / language / upcoming-release poster

Prefer an official full poster/key art.

- Preserve the complete poster.
- Never crop a portrait poster into 16:9.
- Fit the full poster inside the 1200×675 canvas with neutral side padding when necessary.
- Do **not** place `@EntertainmentNewsroom` on the poster.

### Image fallback

If no usable article image or poster exists:

1. Try the official publication/source logo.
2. Center the logo on the fallback card.
3. Do **not** place `@EntertainmentNewsroom` on the fallback card.
4. If no logo is available, use the source-name fallback without the channel handle.

## Objective

The reader should understand what happened, where it is available, and the key new information in under 10 seconds.
