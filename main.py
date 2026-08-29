#!/usr/bin/env python3
"""Entertainment Newsroom bot.

Discover -> filter -> rank -> verify -> generate -> brand image -> publish -> persist.
Designed for GitHub Actions and a single scheduled execution per run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import io
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "news_state.json"
POSTED_PATH = ROOT / "posted_urls.txt"

EXA_URL = "https://api.exa.ai/search"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
TELEGRAM_API = "https://api.telegram.org/bot{token}"

TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL", "@EntertainmentNewsroom")
NEWS_MODE = os.getenv("NEWS_MODE", "update")
CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "llama-3.3-70b")
MAX_STORIES = int(os.getenv("MAX_STORIES", "6"))
BATCH_SIZE = 15
LOOKBACK_HOURS = 24

ALLOWED_DOMAINS = {
    "deadline.com", "variety.com", "hollywoodreporter.com", "thewrap.com", "indiewire.com",
    "collider.com", "tvline.com", "ottplay.com", "filmibeat.com", "pinkvilla.com",
    "bollywoodhungama.com", "gadgets360.com", "soompi.com", "dramazoom.com", "mydramalist.com",
    "asianwiki.com", "whats-on-netflix.com", "netflix.com", "press.wbd.com", "apple.com",
    "aboutamazon.com", "aboutamazon.in", "press.disneyplus.com", "marvel.com", "dc.com",
    "sonypictures.com", "paramount.com", "universalpictures.com",
}
OFFICIAL_DOMAINS = {
    "netflix.com", "press.wbd.com", "apple.com", "aboutamazon.com", "aboutamazon.in",
    "press.disneyplus.com", "marvel.com", "dc.com", "sonypictures.com", "paramount.com",
    "universalpictures.com",
}

RSS_FEEDS = [
    "https://deadline.com/feed/",
    "https://variety.com/feed/",
    "https://www.hollywoodreporter.com/feed/",
    "https://www.thewrap.com/feed/",
    "https://www.indiewire.com/feed/",
    "https://collider.com/feed/",
    "https://tvline.com/feed/",
    "https://www.ottplay.com/rss",
    "https://www.filmibeat.com/rss/feeds/filmibeat-news.xml",
    "https://www.pinkvilla.com/rss",
    "https://www.soompi.com/feed",
]

QUERY_PACK = [
    'major movie film franchise casting trailer release date Netflix HBO Disney Amazon Prime Video',
    'major Indian cinema Bollywood Pan India movie trailer casting release date OTT',
    'major Korean drama Netflix Disney+ TVING Viki casting trailer release',
    'major Chinese drama iQIYI Tencent Youku Netflix casting trailer release',
]

UA = "EntertainmentNewsroomBot/1.0 (+https://github.com/)"


@dataclass
class Candidate:
    title: str
    url: str
    source: str
    domain: str
    published: str = ""
    summary: str = ""
    image_url: str = ""
    search_reason: str = ""
    score: float = 0.0
    why: str = ""

    @property
    def age_hours(self) -> float | None:
        if not self.published:
            return None
        try:
            value = dt.datetime.fromisoformat(self.published.replace("Z", "+00:00"))
            if value.tzinfo is None:
                value = value.replace(tzinfo=dt.timezone.utc)
            return max(0.0, (dt.datetime.now(dt.timezone.utc) - value).total_seconds() / 3600)
        except ValueError:
            return None


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"published_events": [], "last_run": None}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"published_events": [], "last_run": None}


def load_posted_urls() -> set[str]:
    if not POSTED_PATH.exists():
        return set()
    return {line.strip() for line in POSTED_PATH.read_text(encoding="utf-8").splitlines() if line.strip()}


def save_state(state: dict[str, Any], posted_urls: set[str]) -> None:
    state["last_run"] = dt.datetime.now(dt.timezone.utc).isoformat()
    state["published_events"] = state.get("published_events", [])[-500:]
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    POSTED_PATH.write_text("\n".join(sorted(posted_urls)) + ("\n" if posted_urls else ""), encoding="utf-8")


def domain_of(url: str) -> str:
    host = urlparse(url).netloc.lower().split(":")[0]
    return host[4:] if host.startswith("www.") else host


def allowed_domain(url: str) -> bool:
    domain = domain_of(url)
    return any(domain == d or domain.endswith("." + d) for d in ALLOWED_DOMAINS)


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def parse_published(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.isoformat()
    except ValueError:
        pass
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = dt.datetime.strptime(value, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed.astimezone(dt.timezone.utc).isoformat()
        except ValueError:
            continue
    return value


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(node: ET.Element, names: tuple[str, ...]) -> str:
    for child in node.iter():
        if _local_name(child.tag) in names and child is not node:
            text = "".join(child.itertext()).strip()
            if text:
                return text
    return ""


def _media_image(node: ET.Element) -> str:
    for child in node.iter():
        name = _local_name(child.tag)
        if name in {"content", "thumbnail"}:
            url = child.attrib.get("url", "").strip()
            if url:
                return url
        if name == "enclosure" and child.attrib.get("type", "").startswith("image/"):
            return child.attrib.get("url", "").strip()
    return ""


def parse_feed(url: str) -> list[Candidate]:
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=20)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as exc:
        print(f"[warn] RSS failed {url}: {exc}", file=sys.stderr)
        return []
    feed_title = _child_text(root, ("title",)) or domain_of(url)
    out: list[Candidate] = []
    nodes = [n for n in root.iter() if _local_name(n.tag) in {"item", "entry"}]
    for entry in nodes:
        title = _child_text(entry, ("title",))
        link = ""
        for child in entry:
            if _local_name(child.tag) == "link":
                link = child.attrib.get("href", "").strip() or (child.text or "").strip()
                if link:
                    break
        published = _child_text(entry, ("published", "updated", "pubDate", "date"))
        summary = _child_text(entry, ("description", "summary", "content"))
        summary = re.sub(r"<[^>]+>", " ", summary)
        summary = re.sub(r"\s+", " ", html.unescape(summary)).strip()[:1200]
        link = link.strip()
        title = re.sub(r"\s+", " ", html.unescape(title)).strip()
        if not link or not title or not allowed_domain(link):
            continue
        out.append(Candidate(
            title=title,
            url=normalize_url(link),
            source=feed_title,
            domain=domain_of(link),
            published=parse_published(published),
            summary=summary,
            image_url=_media_image(entry),
            search_reason="rss",
        ))
    return out

def google_news_rss(query: str) -> list[Candidate]:
    from urllib.parse import quote_plus
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    return parse_feed(url)


def exa_search(api_key: str, query: str, num_results: int = 12) -> list[Candidate]:
    now = dt.datetime.now(dt.timezone.utc)
    start = (now - dt.timedelta(hours=LOOKBACK_HOURS)).isoformat().replace("+00:00", "Z")
    payload = {
        "query": query,
        "includeDomains": sorted(ALLOWED_DOMAINS),
        "startPublishedDate": start,
        "endPublishedDate": now.isoformat().replace("+00:00", "Z"),
        "numResults": num_results,
        "contents": {"text": False, "highlights": True, "summary": True, "extras": {"imageLinks": 1}},
    }
    try:
        r = requests.post(EXA_URL, headers={"x-api-key": api_key, "Content-Type": "application/json", "User-Agent": UA}, json=payload, timeout=45)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        print(f"[warn] Exa failed: {exc}", file=sys.stderr)
        return []
    out: list[Candidate] = []
    for item in data.get("results", []):
        url = str(item.get("url", "")).strip()
        if not url or not allowed_domain(url):
            continue
        out.append(Candidate(
            title=str(item.get("title", "")).strip(),
            url=normalize_url(url),
            source=domain_of(url),
            domain=domain_of(url),
            published=str(item.get("publishedDate", "")),
            summary=str(item.get("summary", ""))[:1400],
            image_url=str(item.get("image", "")),
            search_reason="exa",
        ))
    return out


def dedupe_candidates(candidates: Iterable[Candidate], posted_urls: set[str]) -> list[Candidate]:
    seen: set[str] = set()
    out: list[Candidate] = []
    for c in candidates:
        c.url = normalize_url(c.url)
        if c.url in posted_urls or c.url in seen:
            continue
        age = c.age_hours
        if age is not None and age > LOOKBACK_HOURS:
            continue
        seen.add(c.url)
        out.append(c)
    return out


def call_cerebras(api_key: str, messages: list[dict[str, str]], temperature: float = 0.1, max_tokens: int = 2500) -> str:
    payload = {
        "model": CEREBRAS_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    r = requests.post(CEREBRAS_URL, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return str(data["choices"][0]["message"]["content"])


def extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = min([i for i in (text.find("["), text.find("{")) if i >= 0], default=-1)
        if start >= 0:
            for end in range(len(text), start, -1):
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    continue
    raise ValueError("No valid JSON in model response")


def rank_batches(cerebras_key: str, candidates: list[Candidate], state: dict[str, Any]) -> list[Candidate]:
    ranked: list[Candidate] = []
    recent_events = [x.get("headline", "") for x in state.get("published_events", [])[-40:]]
    for start in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[start:start + BATCH_SIZE]
        items = []
        for i, c in enumerate(batch):
            items.append({"id": i, "title": c.title, "source": c.source, "url": c.url, "published": c.published, "description": c.summary})
        prompt = {
            "recently_published_headlines": recent_events,
            "candidates": items,
        }
        messages = [
            {"role": "system", "content": "You are the editorial ranker for a selective movie/streaming/scripted-series Telegram newsroom. Score each candidate 0-10 using only supplied metadata. Publishable means score >= 7. Penalize gossip, rumors, routine catalog additions, repetitive follow-up coverage, minor casting, generic interviews, and promotional fluff. Prefer major films/series, major streaming platforms, franchises, major Indian cinema, significant Korean/Chinese drama, important international distribution, and high-impact industry developments. When unsure, choose the lower score. Return JSON array only with objects: id, score, publishable, why."},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ]
        try:
            data = extract_json(call_cerebras(cerebras_key, messages, max_tokens=3500))
        except Exception as exc:
            print(f"[warn] ranking batch failed: {exc}", file=sys.stderr)
            continue
        for item in data if isinstance(data, list) else []:
            idx = item.get("id")
            if isinstance(idx, int) and 0 <= idx < len(batch):
                c = batch[idx]
                c.score = float(item.get("score", 0))
                c.why = str(item.get("why", ""))
                if c.score >= 7:
                    ranked.append(c)
    return sorted(ranked, key=lambda c: (-c.score, c.age_hours if c.age_hours is not None else 9999))


def diversify(candidates: list[Candidate]) -> list[Candidate]:
    # Soft diversity only after importance ranking. Never replace a meaningfully stronger story.
    buckets: dict[str, int] = {}
    selected: list[Candidate] = []
    for c in candidates:
        low = f"{c.title} {c.summary}".lower()
        if any(x in low for x in ("netflix", "hbo", "disney", "prime video", "apple tv", "streaming")):
            bucket = "platform"
        elif any(x in low for x in ("korea", "korean", "k-drama")):
            bucket = "korea"
        elif any(x in low for x in ("china", "chinese", "c-drama")):
            bucket = "china"
        elif any(x in low for x in ("bollywood", "india", "indian", "pan-india")):
            bucket = "india"
        else:
            bucket = "hollywood-international"
        if buckets.get(bucket, 0) >= 2 and len(selected) < MAX_STORIES:
            continue
        buckets[bucket] = buckets.get(bucket, 0) + 1
        selected.append(c)
        if len(selected) >= MAX_STORIES:
            break
    # Fill remaining slots by raw score.
    if len(selected) < MAX_STORIES:
        used = {c.url for c in selected}
        selected.extend([c for c in candidates if c.url not in used][:MAX_STORIES - len(selected)])
    return selected[:MAX_STORIES]


def fetch_article(url: str) -> tuple[str, str]:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
    except Exception:
        return "", ""
    text = r.text
    title = ""
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', text, re.I)
    if not m:
        m = re.search(r'<title[^>]*>(.*?)</title>', text, re.I | re.S)
    if m:
        title = re.sub(r"\s+", " ", html.unescape(m.group(1))).strip()
    # Extract visible paragraphs with a deliberately conservative length cap.
    paras = re.findall(r"<p[^>]*>(.*?)</p>", text, re.I | re.S)
    clean = []
    for p in paras:
        p = re.sub(r"<[^>]+>", " ", p)
        p = re.sub(r"\s+", " ", html.unescape(p)).strip()
        if len(p) >= 80:
            clean.append(p)
    return title, "\n".join(clean)[:12000]


def verify_candidate(cerebras_key: str, c: Candidate, article_title: str, article_text: str) -> bool:
    if not article_text:
        return False
    messages = [
        {"role": "system", "content": "Verify whether a candidate news story is sufficiently supported by the supplied article. Check event status and reject unsupported or speculative claims. Return JSON only: {\"supported\": true|false, \"reason\": \"...\"}."},
        {"role": "user", "content": json.dumps({"candidate": asdict(c), "article_title": article_title, "article": article_text}, ensure_ascii=False)},
    ]
    try:
        obj = extract_json(call_cerebras(cerebras_key, messages, max_tokens=700))
        return bool(obj.get("supported"))
    except Exception as exc:
        print(f"[warn] verification failed: {exc}", file=sys.stderr)
        return False


def generate_story(cerebras_key: str, c: Candidate, article_title: str, article_text: str) -> dict[str, Any] | None:
    messages = [
        {"role": "system", "content": "Write a Telegram entertainment-news post from the supplied source only. Headline must be 6-14 words, newspaper-style. Summary must be exactly one sentence. Highlights must be 3-5 concise factual bullets. Context must be 2-4 sentences. Bottom line exactly one sentence. Never invent facts. Choose 2-4 relevant hashtags. Output JSON only with headline, summary, highlights, context, bottom_line, hashtags, source_name."},
        {"role": "user", "content": json.dumps({"candidate": asdict(c), "article_title": article_title, "article": article_text}, ensure_ascii=False)},
    ]
    try:
        obj = extract_json(call_cerebras(cerebras_key, messages, temperature=0.2, max_tokens=1700))
        required = ("headline", "summary", "highlights", "context", "bottom_line", "hashtags", "source_name")
        if not all(k in obj for k in required):
            return None
        if not isinstance(obj["highlights"], list) or not 3 <= len(obj["highlights"]) <= 5:
            return None
        return obj
    except Exception as exc:
        print(f"[warn] story generation failed: {exc}", file=sys.stderr)
        return None


def safe_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def download_image(url: str) -> Image.Image | None:
    if not url:
        return None
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        return img
    except Exception:
        return None


def create_branded_image(c: Candidate, story: dict[str, Any], source_img: Image.Image | None) -> bytes:
    if source_img is None:
        img = Image.new("RGB", (1200, 675), "#151515")
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, 1200, 675), fill="#151515")
        draw.text((70, 90), "ENTERTAINMENT NEWS", fill="white", font=safe_font(34, True))
        draw.text((70, 155), story["headline"], fill="white", font=safe_font(54, True), spacing=8)
        draw.text((70, 600), c.source, fill="#dddddd", font=safe_font(26))
    else:
        img.thumbnail((1200, 675), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (1200, 675), "#111111")
        x = (1200 - img.width) // 2
        y = (675 - img.height) // 2
        canvas.paste(img, (x, y))
        img = canvas
        draw = ImageDraw.Draw(img)
    # Branding strip / chips.
    draw.rectangle((0, 625, 1200, 675), fill=(10, 10, 10))
    draw.rounded_rectangle((28, 637, 28 + max(120, len(c.source) * 14), 667), radius=10, fill=(35, 35, 35))
    draw.text((42, 642), c.source[:35], fill="white", font=safe_font(19, True))
    brand = "@EntertainmentNewsroom"
    brand_w = draw.textbbox((0, 0), brand, font=safe_font(21, True))[2]
    draw.rounded_rectangle((1172 - brand_w, 637, 1172, 667), radius=10, fill=(35, 35, 35))
    draw.text((1188 - brand_w, 642), brand, fill="white", font=safe_font(19, True))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90, optimize=True)
    return buf.getvalue()


def format_caption(story: dict[str, Any], c: Candidate) -> str:
    def esc(s: str) -> str:
        return html.escape(str(s), quote=False)
    highlights = "\n".join(f"• {esc(x)}" for x in story["highlights"])
    tags = " ".join("#" + re.sub(r"[^A-Za-z0-9]", "", str(x).lstrip("#")) for x in story["hashtags"])
    source = esc(story.get("source_name") or c.source)
    return (
        f"<b>{esc(story['headline'])}</b>\n\n"
        f"{esc(story['summary'])}\n\n"
        f"<b>KEY HIGHLIGHTS</b>\n{highlights}\n\n"
        f"<blockquote expandable><b>THE CONTEXT</b>\n{esc(story['context'])}</blockquote>\n"
        f"<blockquote expandable><b>BOTTOM LINE</b>\n{esc(story['bottom_line'])}</blockquote>\n\n"
        f"{tags}\n\n"
        f"<b>Source:</b> <a href=\"{html.escape(c.url, quote=True)}\">{source}</a>"
    )[:1024]


def telegram_send_photo(token: str, channel: str, photo: bytes, caption: str) -> dict[str, Any]:
    url = TELEGRAM_API.format(token=token) + "/sendPhoto"
    files = {"photo": ("story.jpg", photo, "image/jpeg")}
    data = {"chat_id": channel, "caption": caption, "parse_mode": "HTML"}
    r = requests.post(url, data=data, files=files, timeout=60)
    r.raise_for_status()
    return r.json()


def self_test() -> int:
    assert BATCH_SIZE == 15
    assert MAX_STORIES >= 1
    assert allowed_domain("https://deadline.com/x")
    assert not allowed_domain("https://example.com/x")
    assert normalize_url("https://www.variety.com/foo?utm_source=x") == "https://www.variety.com/foo"
    sample = format_caption({
        "headline": "Major Netflix Series Sets a New Release Date",
        "summary": "Netflix confirmed a new release date for the series.",
        "highlights": ["Release date confirmed", "Netflix is the platform", "Production remains active"],
        "context": "The project is a major scripted series with broad audience interest.",
        "bottom_line": "The new date changes the rollout timing for viewers.",
        "hashtags": ["Netflix", "Series"],
        "source_name": "Variety",
    }, Candidate("x", "https://variety.com/story", "Variety", "variety.com"))
    assert "THE CONTEXT" in sample and "BOTTOM LINE" in sample
    print("self-test: PASS")
    return 0


def run() -> int:
    exa_key = require_env("EXA_API_KEY")
    cerebras_key = require_env("CEREBRAS_API_KEY")
    telegram_token = require_env("TELEGRAM_BOT_TOKEN")
    state = load_state()
    posted_urls = load_posted_urls()

    discovered: list[Candidate] = []
    for feed in RSS_FEEDS:
        discovered.extend(parse_feed(feed))
    for query in QUERY_PACK:
        discovered.extend(google_news_rss(query))
        discovered.extend(exa_search(exa_key, query))
    candidates = dedupe_candidates(discovered, posted_urls)
    print(f"discovered={len(discovered)} eligible={len(candidates)}")
    if not candidates:
        save_state(state, posted_urls)
        return 0

    ranked = rank_batches(cerebras_key, candidates, state)
    selected = diversify(ranked)
    print(f"ranked_publishable={len(ranked)} selected={len(selected)}")

    published = 0
    for c in selected:
        article_title, article_text = fetch_article(c.url)
        if not article_text or not verify_candidate(cerebras_key, c, article_title, article_text):
            continue
        story = generate_story(cerebras_key, c, article_title, article_text)
        if not story:
            continue
        image = download_image(c.image_url)
        card = create_branded_image(c, story, image)
        caption = format_caption(story, c)
        if len(caption) > 1024:
            # Telegram photo captions are capped at 1024 characters.
            caption = caption[:1000].rstrip() + "…"
        try:
            telegram_send_photo(telegram_token, TELEGRAM_CHANNEL, card, caption)
        except Exception as exc:
            print(f"[warn] Telegram publish failed for {c.url}: {exc}", file=sys.stderr)
            continue
        posted_urls.add(c.url)
        state.setdefault("published_events", []).append({
            "url": c.url,
            "headline": story["headline"],
            "source": story.get("source_name", c.source),
            "score": c.score,
            "published_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        })
        published += 1
        save_state(state, posted_urls)
        print(f"published={published} {story['headline']}")
        if published >= MAX_STORIES:
            break
        time.sleep(1.2)

    save_state(state, posted_urls)
    print(f"done published={published}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    return self_test() if args.self_test else run()


if __name__ == "__main__":
    raise SystemExit(main())
