# Entertainment Newsroom V1 Template

## Public post structure

The public Telegram post uses one clean reader-first structure. Section labels such as `Availability` and `What's New` are not displayed.

```text
Photo

*{HOOK}*

*🎬 {TITLE} ({YEAR})*

✦ *Platform:* {Platform}
✦ *Episodes:* {count}
✦ *Language:* {languages}
✦ *Status:* {status}
✦ *Release:* {date}

📖 {1–2 sentence synopsis}

✦ {detail}
✦ {detail}
✦ {detail}

🙈 *Spoiler:* ||{only when genuinely relevant}||

<expandable note when needed>

@EntertainmentNewsroom #tag #tag
*Source:* {clickable source name}
```

### Rendering rules

- Hook: bold.
- Title + year: bold and visually prominent. Do not prefix the title with Markdown heading symbols such as `#`.
- Use `✦` for all ordinary detail bullets. Do not use `•`.
- Field labels such as `Platform`, `Episodes`, `Language`, `Status`, and `Release` are bold. Their values are normal text.
- Do not display `Availability` or `What's New` as section headings.
- Synopsis is short and begins with `📖`.
- Spoiler is optional and must use Telegram spoiler markup only when the actual news requires it.
- Optional secondary caveat, dub limitation, or unconfirmed note goes in a collapsible Rich Message block.
- Source label is bold and the source name is a clickable link.
- Do not include `What to Know`, `Vocabulary`, `THE CONTEXT`, or `BOTTOM LINE`.
- Omit unknown fields. Never publish placeholders such as `Unknown`.

### Information priority

Order content around what readers need first. For Tier 1 streaming/release stories, platform/status/release information comes immediately after the title. Avoid repeating the same release date in multiple places.

### Image rules

For OTT, streaming, Hindi-dub, and upcoming OTT stories, prefer the official full poster/key art.

- Preserve the poster's original aspect ratio.
- Do not crop it into 16:9.
- Do not add blurred side panels.
- Do not place the poster on a padded 1200×675 landscape canvas.
- Do not add `@EntertainmentNewsroom` branding to posters.
- If a source image is a wide composite containing a centered portrait poster with blurred side panels, extract the center poster rather than sending the composite.
- If no usable article/poster image exists, prefer the official publication logo as the fallback visual.
- Normal editorial photographs may use the branded 1200×675 treatment.
