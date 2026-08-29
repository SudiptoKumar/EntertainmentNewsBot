#!/usr/bin/env python3
"""EntertainmentNewsroom V1.

RSS/Google News/Exa discovery -> source validation -> event dedupe ->
Cerebras editorial ranking -> article extraction -> story generation ->
claim verification -> 1200x675 branded image -> Telegram -> persistent state.
"""
from __future__ import annotations

import argparse
import html
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import quote_plus, urljoin, urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup
from cerebras.cloud.sdk import Cerebras
from exa_py import Exa
from PIL import Image, ImageDraw, ImageFont, ImageFile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "news_state.json"
POSTED_FILE = ROOT / "posted_urls.txt"

EXA_API_KEY = os.environ["EXA_API_KEY"]
CEREBRAS_API_KEY = os.environ["CEREBRAS_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHANNEL = (os.environ.get("TELEGRAM_CHANNEL") or "@EntertainmentNewsroom").strip()
TELEGRAM_ADMIN_CHAT_ID = (os.environ.get("TELEGRAM_ADMIN_CHAT_ID") or "").strip()
NEWS_MODE = (os.environ.get("NEWS_MODE") or "update").strip().lower()
CEREBRAS_MODEL = os.environ.get("CEREBRAS_MODEL", "gpt-oss-120b")

if NEWS_MODE != "update":
    raise ValueError(f"Invalid NEWS_MODE={NEWS_MODE!r}; expected 'update'")

BD_TZ = ZoneInfo("Asia/Dhaka")
STORIES_PER_RUN = 6
RECOVERY_POOL_SIZE = 24
RANK_MAX_CANDIDATES = 60
LOOKBACK_HOURS = 24
FUTURE_TOLERANCE_MINUTES = 10
QUEUE_RETENTION_DAYS = 4
EVENT_RETENTION_DAYS = 30
POST_DELAY_SECONDS = 3.0
FEED_FAIL_ALERT_THRESHOLD = 3
MAX_EXA_CANDIDATES = 60
MAX_GOOGLE_CANDIDATES = 40
MAX_RSS_CANDIDATES = 240

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("entertainment-news-bot")
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = 50_000_000

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; EntertainmentNewsroomBot/1.0; +https://github.com/)"
}
session = requests.Session()
session.headers.update(HEADERS)
retry_policy = Retry(
    total=4,
    connect=4,
    read=4,
    backoff_factor=1.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    respect_retry_after_header=True,
)
adapter = HTTPAdapter(max_retries=retry_policy, pool_connections=20, pool_maxsize=20)
session.mount("https://", adapter)
session.mount("http://", adapter)
retry_policy = Retry(
    total=4,
    connect=4,
    read=4,
    backoff_factor=1.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    respect_retry_after_header=True,
)
adapter = HTTPAdapter(max_retries=retry_policy, pool_connections=20, pool_maxsize=20)
session.mount("https://", adapter)
session.mount("http://", adapter)

exa = Exa(api_key=EXA_API_KEY)
cerebras = Cerebras(api_key=CEREBRAS_API_KEY)

RSS_FEEDS = [
    {"name": "Deadline", "url": "https://deadline.com/feed/"},
    {"name": "Variety", "url": "https://variety.com/feed/"},
    {"name": "The Hollywood Reporter", "url": "https://www.hollywoodreporter.com/feed/"},
    {"name": "TheWrap", "url": "https://www.thewrap.com/feed/"},
    {"name": "IndieWire", "url": "https://www.indiewire.com/feed/"},
    {"name": "Collider", "url": "https://collider.com/feed/"},
    {"name": "TVLine", "url": "https://tvline.com/feed/"},
    {"name": "OTTplay", "url": "https://www.ottplay.com/rss"},
    {"name": "Filmibeat", "url": "https://www.filmibeat.com/rss/feeds/filmibeat-news.xml"},
    {"name": "Pinkvilla", "url": "https://www.pinkvilla.com/rss"},
    {"name": "Bollywood Hungama", "url": "https://www.bollywoodhungama.com/rss/"},
    {"name": "Gadgets 360 Entertainment", "url": "https://www.gadgets360.com/rss/entertainment"},
    {"name": "Soompi", "url": "https://www.soompi.com/feed"},
]

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

TOPICS = [
    "Major Film", "Major Series", "Streaming Platform", "Casting", "Trailer / First Look",
    "Release Date", "Renewal / Cancellation", "Production", "Rights / Distribution",
    "Indian Cinema", "Korean Drama", "Chinese Drama", "Franchise / IP", "Industry Business",
]

BAD_PATH_RE = re.compile(r"/(opinion|editorial|sponsored|tag|topic|live-blog|liveblog|photos?|video)(/|$)", re.I)
BAD_TITLE_RE = re.compile(r"\b(sponsored|advertisement|promo|opinion|editorial)\b", re.I)

DISCOVERY_END = datetime.now(BD_TZ) + timedelta(minutes=FUTURE_TOLERANCE_MINUTES)
DISCOVERY_START = DISCOVERY_END - timedelta(hours=LOOKBACK_HOURS)


def now_iso() -> str:
    return datetime.now(BD_TZ).isoformat()


def safe_text(value) -> str:
    return "" if value is None else str(value).strip()


def parse_datetime(value):
    raw = safe_text(value)
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(BD_TZ)
    except Exception:
        pass
    try:
        parsed = parsedate_to_datetime(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(BD_TZ)
    except Exception:
        return None


def canonical_url(url: str) -> str:
    raw = safe_text(url)
    if not raw:
        return ""
    p = urlparse(raw)
    host = p.netloc.lower().removeprefix("www.").removeprefix("amp.")
    path = re.sub(r"/amp$|\.amp$", "", p.path.rstrip("/"), flags=re.I)
    return f"{host}{path}"


def domain_of(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.").split(":")[0]


def allowed_domain(url: str) -> bool:
    domain = domain_of(url)
    return any(domain == d or domain.endswith("." + d) for d in ALLOWED_DOMAINS)


def source_name(url: str) -> str:
    mapping = {
        "deadline.com": "Deadline", "variety.com": "Variety", "hollywoodreporter.com": "The Hollywood Reporter",
        "thewrap.com": "TheWrap", "indiewire.com": "IndieWire", "collider.com": "Collider", "tvline.com": "TVLine",
        "ottplay.com": "OTTplay", "filmibeat.com": "Filmibeat", "pinkvilla.com": "Pinkvilla",
        "bollywoodhungama.com": "Bollywood Hungama", "gadgets360.com": "Gadgets 360", "soompi.com": "Soompi",
        "whats-on-netflix.com": "What's on Netflix", "netflix.com": "Netflix", "press.wbd.com": "Warner Bros. Discovery",
        "apple.com": "Apple TV Press", "aboutamazon.com": "Amazon", "aboutamazon.in": "Amazon India",
        "press.disneyplus.com": "Disney+ Press", "marvel.com": "Marvel", "dc.com": "DC",
        "sonypictures.com": "Sony Pictures", "paramount.com": "Paramount", "universalpictures.com": "Universal Pictures",
    }
    return mapping.get(domain_of(url), domain_of(url) or "Source")


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", safe_text(title).lower())).strip()


def title_tokens(title: str) -> set[str]:
    return {x for x in normalize_title(title).split() if len(x) >= 3}


def title_similarity(a: str, b: str) -> float:
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    ta, tb = title_tokens(na), title_tokens(nb)
    jac = len(ta & tb) / max(1, len(ta | tb))
    return max(seq, jac)


def default_state():
    return {"feeds": {}, "queue": {}, "events": {}, "recent_titles": [], "last_run": None}


def load_state():
    if not STATE_FILE.exists():
        return default_state()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        base = default_state()
        if isinstance(data, dict):
            base.update(data)
        return base
    except Exception:
        return default_state()


def save_state():
    STATE["last_run"] = now_iso()
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(STATE, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, STATE_FILE)


def load_posted_urls():
    if not POSTED_FILE.exists():
        return set()
    return {canonical_url(x) for x in POSTED_FILE.read_text(encoding="utf-8").splitlines() if safe_text(x)}


def save_posted_url(url: str):
    value = canonical_url(url)
    if not value:
        return
    with POSTED_FILE.open("a", encoding="utf-8") as f:
        f.write(value + "\n")


STATE = load_state()
POSTED_URLS = load_posted_urls()


def prune_state():
    queue_cutoff = datetime.now(BD_TZ) - timedelta(days=QUEUE_RETENTION_DAYS)
    event_cutoff = datetime.now(BD_TZ) - timedelta(days=EVENT_RETENTION_DAYS)
    STATE["queue"] = {
        k: v for k, v in STATE.get("queue", {}).items()
        if not parse_datetime(v.get("last_seen") or v.get("published_date"))
        or parse_datetime(v.get("last_seen") or v.get("published_date")) >= queue_cutoff
    }
    STATE["events"] = {
        k: v for k, v in STATE.get("events", {}).items()
        if not parse_datetime(v.get("published_at") or v.get("selected_at"))
        or parse_datetime(v.get("published_at") or v.get("selected_at")) >= event_cutoff
    }
    STATE["recent_titles"] = STATE.get("recent_titles", [])[-400:]


def candidate_basic_allowed(item: dict) -> bool:
    url = safe_text(item.get("url"))
    title = safe_text(item.get("title"))
    published = item.get("published_dt") or parse_datetime(item.get("published_date"))
    if not url or not title or not published:
        return False
    if BAD_PATH_RE.search(urlparse(url).path) or BAD_TITLE_RE.search(title):
        return False
    if not (DISCOVERY_START <= published <= DISCOVERY_END):
        return False
    return allowed_domain(url)


def queue_candidate(item: dict):
    canonical = canonical_url(item.get("url"))
    if not canonical or canonical in POSTED_URLS:
        return False
    existing = STATE["queue"].get(canonical)
    if existing:
        existing.update({"last_seen": now_iso()})
        if not existing.get("image") and item.get("image"):
            existing["image"] = item["image"]
        return False
    item = dict(item)
    item["canonical"] = canonical
    item["first_seen"] = now_iso()
    item["last_seen"] = now_iso()
    item["status"] = "pending"
    STATE["queue"][canonical] = item
    return True


def feed_entry_image(entry, page_url):
    for media in entry.get("media_content", []) or []:
        url = safe_text(media.get("url"))
        if url:
            return url
    for media in entry.get("media_thumbnail", []) or []:
        url = safe_text(media.get("url"))
        if url:
            return url
    for link in entry.get("links", []) or []:
        if safe_text(link.get("type")).startswith("image/") and safe_text(link.get("href")):
            return urljoin(page_url, link["href"])
    return ""


def feed_entry_datetime(entry):
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc).astimezone(BD_TZ)
            except Exception:
                pass
    for key in ("published", "updated", "created", "pubDate"):
        parsed = parse_datetime(entry.get(key))
        if parsed:
            return parsed
    return None


def fetch_rss_feed(feed_def):
    url = feed_def["url"]
    old = STATE["feeds"].get(url, {})
    try:
        response = session.get(url, timeout=25)
        response.raise_for_status()
        import feedparser
        parsed = feedparser.parse(response.content)
        added = 0
        for entry in parsed.entries:
            published_dt = feed_entry_datetime(entry) or datetime.now(BD_TZ)
            link = urljoin(url, safe_text(entry.get("link")))
            title = safe_text(entry.get("title"))
            if not link or not title:
                continue
            summary = BeautifulSoup(safe_text(entry.get("summary") or entry.get("description")), "html.parser").get_text(" ", strip=True)
            item = {
                "title": title,
                "url": link,
                "published_dt": published_dt,
                "published_date": published_dt.isoformat(),
                "source": feed_def["name"],
                "region": "Global Entertainment",
                "excerpt": summary[:2200],
                "image": feed_entry_image(entry, link),
                "discovery": "rss",
            }
            if not candidate_basic_allowed(item):
                continue
            if queue_candidate(item):
                added += 1
        STATE["feeds"][url] = {**old, "last_checked": now_iso(), "fail_count": 0, "alerted": False}
        return added
    except Exception as exc:
        failures = int(old.get("fail_count", 0)) + 1
        STATE["feeds"][url] = {**old, "last_checked": now_iso(), "fail_count": failures}
        logger.warning("RSS failed %s: %s", feed_def["name"], exc)
        if failures >= FEED_FAIL_ALERT_THRESHOLD and not old.get("alerted"):
            STATE["feeds"][url]["alerted"] = True
            alert = f"Feed down: {feed_def['name']}\nFailed {failures} runs.\n{url}"
            logger.error(alert)
            if TELEGRAM_ADMIN_CHAT_ID:
                telegram_call("sendMessage", data={"chat_id": TELEGRAM_ADMIN_CHAT_ID, "text": alert})
        return 0


def google_news_rss(query: str) -> int:
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    added = 0
    try:
        response = session.get(url, timeout=25)
        response.raise_for_status()
        import feedparser
        parsed = feedparser.parse(response.content)
        for entry in parsed.entries:
            published_dt = feed_entry_datetime(entry)
            link = safe_text(entry.get("link"))
            title = safe_text(entry.get("title"))
            if not published_dt or not link or not title:
                continue
            if not allowed_domain(link) or not (DISCOVERY_START <= published_dt <= DISCOVERY_END):
                continue
            item = {
                "title": title, "url": link, "published_dt": published_dt, "published_date": published_dt.isoformat(),
                "source": source_name(link), "region": "Global Entertainment",
                "excerpt": BeautifulSoup(safe_text(entry.get("summary")), "html.parser").get_text(" ", strip=True)[:2000],
                "image": "", "discovery": "google_news",
            }
            if candidate_basic_allowed(item) and queue_candidate(item):
                added += 1
            if added >= MAX_GOOGLE_CANDIDATES:
                break
    except Exception as exc:
        logger.warning("Google News discovery failed: %s", exc)
    return added


def exa_gap_fill():
    queries = [
        "major Hollywood movie casting trailer release date franchise announcement",
        "major Netflix HBO Disney Apple Prime Video scripted series news renewal cancellation",
        "major Bollywood Indian Pan-Indian film casting trailer OTT rights release date",
        "major Korean drama Netflix Disney TVING Viki casting trailer release distribution",
        "major Chinese drama iQIYI Tencent Youku Netflix casting trailer release distribution",
        "major streaming rights acquisition international distribution entertainment industry",
    ]
    added = 0
    for query in queries:
        try:
            results = exa.search_and_contents(
                query,
                type="auto",
                category="news",
                num_results=10,
                include_domains=sorted(ALLOWED_DOMAINS),
                start_published_date=DISCOVERY_START.isoformat(),
                end_published_date=DISCOVERY_END.isoformat(),
                contents={"highlights": {"max_characters": 900}},
            )
            for result in results.results:
                url = safe_text(getattr(result, "url", ""))
                title = safe_text(getattr(result, "title", ""))
                published = parse_datetime(getattr(result, "published_date", ""))
                if not url or not title or not published or not allowed_domain(url):
                    continue
                highlights = getattr(result, "highlights", [])
                if isinstance(highlights, list):
                    excerpt = " ".join(map(str, highlights))
                else:
                    excerpt = safe_text(highlights)
                item = {
                    "title": title, "url": url, "published_dt": published, "published_date": published.isoformat(),
                    "source": source_name(url), "region": "Global Entertainment", "excerpt": excerpt[:2200],
                    "image": safe_text(getattr(result, "image", "")), "discovery": "exa",
                }
                if candidate_basic_allowed(item) and queue_candidate(item):
                    added += 1
                if added >= MAX_EXA_CANDIDATES:
                    return added
        except Exception as exc:
            logger.warning("Exa discovery failed for query=%r: %s", query, exc)
    return added


def event_key(title: str) -> str:
    text = normalize_title(title)
    words = [w for w in text.split() if w not in {"the", "a", "an", "is", "of", "to", "and", "for", "in", "on", "with", "new"}]
    return " ".join(words[:18])


def already_published_event(title: str) -> bool:
    for event in STATE.get("events", {}).values():
        if event.get("status") != "published":
            continue
        if title_similarity(title, event.get("headline", "")) >= 0.88:
            return True
        old_key = safe_text(event.get("event_key"))
        if old_key and title_similarity(event_key(title), old_key) >= 0.82:
            return True
    return False


def available_candidates() -> list[dict]:
    candidates = []
    seen = set()
    for item in STATE["queue"].values():
        if item.get("status") not in {"pending", "selected"}:
            continue
        published = parse_datetime(item.get("published_date"))
        if not published or not (DISCOVERY_START <= published <= DISCOVERY_END):
            continue
        canonical = safe_text(item.get("canonical"))
        if not canonical or canonical in seen or canonical in POSTED_URLS:
            continue
        if already_published_event(item.get("title", "")):
            continue
        if any(title_similarity(item.get("title", ""), x.get("title", "")) >= 0.94 for x in candidates):
            continue
        candidates.append(dict(item))
        seen.add(canonical)
    candidates.sort(key=lambda x: parse_datetime(x.get("published_date")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return candidates[:RANK_MAX_CANDIDATES]


RANK_SCHEMA = {
    "type": "object",
    "properties": {
        "ranked": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "minimum": 1},
                    "rank": {"type": "integer", "minimum": 1},
                    "score": {"type": "integer", "minimum": 0, "maximum": 10},
                    "important": {"type": "boolean"},
                    "topic": {"type": "string"},
                    "event_key": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["id", "rank", "score", "important", "topic", "event_key", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["ranked"],
    "additionalProperties": False,
}


def rank_candidates(candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []
    recent = [x.get("headline", "") for x in STATE.get("events", {}).values() if x.get("status") == "published"][-40:]
    regional = candidates[:RANK_MAX_CANDIDATES]
    blocks = []
    for idx, item in enumerate(regional, 1):
        published = parse_datetime(item.get("published_date"))
        age = f"Age: {max(0, (DISCOVERY_END - published).total_seconds() / 3600):.1f} hours" if published else ""
        blocks.append("\n".join([
            f"ID: {idx}", f"Title: {item.get('title','')}", f"Source: {item.get('source','')}",
            f"Published: {item.get('published_date','')}", age,
            f"Excerpt: {safe_text(item.get('excerpt',''))[:900]}", ""
        ]))
    prompt = f"""
You are the editor-in-chief of @EntertainmentNewsroom.

Rank these candidates from MOST IMPORTANT to LEAST IMPORTANT using only their supplied metadata.
The channel covers major movie, streaming and scripted-series news. Publishable means score >= 7.
All candidates compete in one global pool. Do not fill quotas.

Prioritize:
- major Hollywood movies, franchises and high-profile scripted series
- major Netflix, Prime Video, HBO/Max, Apple TV+, Disney+, Hulu, Paramount+, Peacock, SonyLIV,
  JioHotstar, Viki, TVING, iQIYI, Tencent Video and Youku developments
- major Indian / Bollywood / Pan-Indian projects
- important Korean and Chinese drama productions with strong international relevance
- major casting, trailers, first looks, production starts/wraps, release-date changes,
  renewals, cancellations, rights acquisitions, international distribution and platform deals
- developments with meaningful audience, franchise, platform or industry impact

Deprioritize:
- celebrity lifestyle, dating, fashion, birthdays and social posts
- unsupported rumors, speculation and leaks presented as fact
- minor casting, routine catalog additions, generic interviews and promotional fluff
- reviews, rankings and opinion pieces without a concrete news event
- duplicate or repetitive coverage

9-10 = exceptional global importance
7-8 = clearly important and publishable
4-6 = interesting but normally not publishable
0-3 = low-value, routine, repetitive, promotional, rumor/speculation or niche

important MUST be true only when score >= 7. When in doubt, score lower.
Return EVERY candidate. Allowed topics: {', '.join(TOPICS)}
Recently published headlines: {json.dumps(recent[-20:], ensure_ascii=False)}
"""
    try:
        response = cerebras.chat.completions.create(
            model=CEREBRAS_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "\n".join(blocks)},
            ],
            response_format={"type": "json_schema", "json_schema": {"name": "entertainment_news_rank", "strict": True, "schema": RANK_SCHEMA}},
            reasoning_effort="low",
            temperature=0.0,
            max_completion_tokens=6500,
        )
        data = json.loads(safe_text(response.choices[0].message.content))
        by_id = {i: item for i, item in enumerate(regional, 1)}
        rows = []
        for row in data.get("ranked", []):
            idx = int(row.get("id", 0))
            if idx not in by_id:
                continue
            item = dict(by_id[idx])
            score = max(0, min(10, int(row.get("score", 0))))
            item.update({
                "editor_rank": int(row.get("rank", 999)),
                "importance_score": score,
                "important": bool(row.get("important")) and score >= 7,
                "topic": safe_text(row.get("topic")) or "Major Series",
                "event_key": safe_text(row.get("event_key")) or event_key(item.get("title", "")),
                "rank_reason": safe_text(row.get("reason")),
            })
            rows.append(item)
        rows.sort(key=lambda x: (x.get("editor_rank", 999), -x.get("importance_score", 0)))
        return [x for x in rows if x.get("important") and x.get("importance_score", 0) >= 7]
    except Exception as exc:
        logger.error("Editorial ranking failed: %s", exc)
        return []


def collapse_events(ranked: list[dict]) -> list[dict]:
    out = []
    for item in ranked:
        duplicate = False
        for existing in out:
            if title_similarity(item.get("title", ""), existing.get("title", "")) >= 0.82:
                duplicate = True
                break
            if item.get("event_key") and existing.get("event_key") and title_similarity(item["event_key"], existing["event_key"]) >= 0.80:
                duplicate = True
                break
        if not duplicate:
            out.append(item)
    return out


def extract_article(item: dict):
    url = item["url"]
    try:
        response = session.get(url, headers={**HEADERS, "Referer": url}, timeout=30)
        response.raise_for_status()
        text = trafilatura.extract(response.text, include_comments=False, include_tables=False, favor_precision=True)
        image_url = item.get("image") or find_og_image(response.text, response.url)
        if text and len(text.strip()) >= 500:
            return text.strip(), image_url
    except Exception as exc:
        logger.warning("Local extraction failed %s: %s", url, exc)
    try:
        result = exa.get_contents([url], text={"max_characters": 12000})
        if result.results:
            first = result.results[0]
            text = safe_text(getattr(first, "text", ""))
            image_url = item.get("image") or safe_text(getattr(first, "image", ""))
            if text:
                return text, image_url
    except Exception as exc:
        logger.warning("Exa article fallback failed %s: %s", url, exc)
    return "", item.get("image", "")


def find_og_image(page_html: str, base_url: str) -> str:
    soup = BeautifulSoup(page_html, "html.parser")
    tag = soup.find("meta", attrs={"property": "og:image"}) or soup.find("meta", attrs={"name": "twitter:image"})
    return urljoin(base_url, safe_text(tag.get("content"))) if tag else ""


STORY_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "highlights": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 5},
        "context": {"type": "string"},
        "bottom_line": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 4},
        "source_name": {"type": "string"},
    },
    "required": ["headline", "summary", "highlights", "context", "bottom_line", "hashtags", "source_name"],
    "additionalProperties": False,
}


def first_sentence(text: str) -> str:
    clean = re.sub(r"\s+", " ", safe_text(text)).strip()
    m = re.search(r"^(.+?[.!?])(?:\s|$)", clean)
    return m.group(1).strip() if m else clean


def complete_text(text: str) -> bool:
    text = safe_text(text)
    return bool(text) and not re.search(r"[,;:\-—…]\s*$", text)


def clean_generated(text: str) -> str:
    text = safe_text(text)
    text = text.replace("\u2026", "")
    text = re.sub(r"\.{2,}", ".", text)
    return re.sub(r"\s+", " ", text).strip()


def generate_story(item: dict, article_text: str):
    prompt = """
You are a senior entertainment-news editor. Write one publishable Telegram post using ONLY the supplied article.
Do not invent, infer or strengthen claims beyond the source.

Rules:
- Headline: 6-14 words, specific and newspaper-style.
- Summary: exactly one complete sentence.
- Highlights: 3-5 concise factual points with no repetition.
- Context: 2-4 complete sentences explaining why the project/development matters.
- Bottom line: exactly one complete sentence stating the central takeaway.
- Hashtags: 2-4 relevant tags without # in the JSON values.
- No Markdown/HTML in any JSON field.
- Do not turn rumors/speculation into confirmed facts.
"""
    user = f"SOURCE: {item.get('source')}\nTITLE: {item.get('title')}\nDATE: {item.get('published_date')}\nARTICLE:\n{article_text[:12000]}"
    for attempt in range(3):
        try:
            response = cerebras.chat.completions.create(
                model=CEREBRAS_MODEL,
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user}],
                response_format={"type": "json_schema", "json_schema": {"name": "entertainment_story_v1", "strict": True, "schema": STORY_SCHEMA}},
                reasoning_effort="low",
                temperature=0.2,
                max_completion_tokens=1500,
            )
            data = json.loads(safe_text(response.choices[0].message.content))
            if not all(k in data for k in STORY_SCHEMA["required"]):
                raise ValueError("missing story fields")
            data["headline"] = clean_generated(data["headline"])
            data["summary"] = first_sentence(data["summary"])
            data["highlights"] = [clean_generated(x) for x in data["highlights"] if clean_generated(x)]
            data["context"] = clean_generated(data["context"])
            data["bottom_line"] = clean_generated(data["bottom_line"])
            data["hashtags"] = [re.sub(r"[^A-Za-z0-9]", "", safe_text(x).lstrip("#")) for x in data["hashtags"] if safe_text(x)]
            if not 6 <= len(data["headline"].split()) <= 14 or not (3 <= len(data["highlights"]) <= 5):
                raise ValueError("story format validation failed")
            if not all(complete_text(x) for x in [data["summary"], data["context"], data["bottom_line"]]):
                raise ValueError("incomplete generated text")
            return data
        except Exception as exc:
            logger.warning("Story generation attempt %d failed: %s", attempt + 1, exc)
            time.sleep(attempt + 1)
    return None


VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "supported": {"type": "boolean"},
        "unsupported_claims": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
    },
    "required": ["supported", "unsupported_claims"],
    "additionalProperties": False,
}


def verify_story(story: dict, article_text: str) -> bool:
    claims = [story.get("headline", ""), story.get("summary", ""), *story.get("highlights", [])]
    prompt = """
Act as a strict fact-checking editor. Mark supported=true ONLY when every material factual claim in the headline,
summary and highlights is directly supported by the supplied article or is a faithful paraphrase.
Reject invented facts, wrong people, wrong dates, wrong figures, unsupported status claims, causal claims, and
claims stronger than the source. Return only the JSON schema.
"""
    user = "SOURCE ARTICLE:\n" + article_text[:12000] + "\n\nCLAIMS:\n- " + "\n- ".join(claims)
    try:
        response = cerebras.chat.completions.create(
            model=CEREBRAS_MODEL,
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user}],
            response_format={"type": "json_schema", "json_schema": {"name": "entertainment_claim_verify", "strict": True, "schema": VERIFY_SCHEMA}},
            reasoning_effort="low",
            temperature=0.0,
            max_completion_tokens=500,
        )
        data = json.loads(safe_text(response.choices[0].message.content))
        return bool(data.get("supported"))
    except Exception as exc:
        logger.warning("Claim verification failed: %s", exc)
        return False


def download_image(url: str):
    if not url:
        return None
    try:
        response = session.get(url, headers=HEADERS, timeout=25)
        response.raise_for_status()
        return Image.open(__import__("io").BytesIO(response.content)).convert("RGB")
    except Exception:
        return None


def safe_font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def create_branded_image(item: dict, story: dict):
    image = download_image(item.get("image", ""))
    if image is None:
        image = Image.new("RGB", (1200, 675), (24, 28, 38))
        draw = ImageDraw.Draw(image)
        draw.text((55, 55), "ENTERTAINMENT NEWS", font=safe_font(36, True), fill="white")
        headline = story["headline"]
        words = headline.split()
        lines, line = [], ""
        for word in words:
            test = (line + " " + word).strip()
            if draw.textbbox((0, 0), test, font=safe_font(52, True))[2] > 1060 and line:
                lines.append(line)
                line = word
            else:
                line = test
        if line:
            lines.append(line)
        y = 150
        for line in lines[:5]:
            draw.text((55, y), line, font=safe_font(52, True), fill="white")
            y += 65
    else:
        image.thumbnail((1200, 675), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (1200, 675), (12, 12, 12))
        canvas.paste(image, ((1200 - image.width) // 2, (675 - image.height) // 2))
        image = canvas
        draw = ImageDraw.Draw(image)
    draw.rectangle((0, 625, 1200, 675), fill=(8, 8, 8))
    source = source_name(item.get("url", ""))[:32]
    draw.rounded_rectangle((24, 636, 24 + max(120, len(source) * 13), 668), radius=10, fill=(38, 38, 38))
    draw.text((38, 642), source, font=safe_font(18, True), fill="white")
    brand = "@EntertainmentNewsroom"
    bw = draw.textbbox((0, 0), brand, font=safe_font(19, True))[2]
    draw.rounded_rectangle((1174 - bw, 636, 1174, 668), radius=10, fill=(38, 38, 38))
    draw.text((1188 - bw, 642), brand, font=safe_font(18, True), fill="white")
    path = "/tmp/entertainment_story.jpg"
    image.save(path, "JPEG", quality=90, optimize=True)
    return path


def format_rich_message(story: dict, item: dict) -> str:
    esc = lambda x: html.escape(safe_text(x), quote=False)
    tags = " ".join("#" + re.sub(r"[^A-Za-z0-9]", "", x.lstrip("#")) for x in story.get("hashtags", []))
    highlights = "\n".join(f"• {esc(x)}" for x in story["highlights"])
    return (
        f"<b>{esc(story['headline'])}</b>\n\n"
        f"{esc(story['summary'])}\n\n"
        f"<b>KEY HIGHLIGHTS</b>\n{highlights}\n\n"
        f"<blockquote expandable><b>THE CONTEXT</b>\n{esc(story['context'])}</blockquote>\n"
        f"<blockquote expandable><b>BOTTOM LINE</b>\n{esc(story['bottom_line'])}</blockquote>\n\n"
        f"{tags}\n\n"
        f"<b>Source:</b> <a href=\"{html.escape(item['url'], quote=True)}\">{esc(story.get('source_name') or source_name(item['url']))}</a>"
    )


def telegram_call(method, data=None, files=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    last = {"ok": False, "description": "unknown"}
    for attempt in range(1, 6):
        try:
            response = session.post(url, data=data or {}, files=files, timeout=90)
            result = response.json()
            if result.get("ok"):
                return result
            last = result
            if response.status_code == 429:
                wait = int(result.get("parameters", {}).get("retry_after", 5))
                time.sleep(max(1, wait))
                continue
            if response.status_code >= 500:
                time.sleep(2 * attempt)
                continue
            break
        except Exception as exc:
            last = {"ok": False, "description": str(exc)}
            time.sleep(2 * attempt)
    return last


def send_rich_photo(image_path: str, rich_html: str):
    rich_message = {
        "html": rich_html,
        "media": [{"id": "newsphoto", "media": {"type": "photo", "media": "attach://photo"}}],
        "skip_entity_detection": False,
    }
    with open(image_path, "rb") as photo:
        result = telegram_call(
            "sendRichMessage",
            data={"chat_id": TELEGRAM_CHANNEL, "rich_message": json.dumps(rich_message, ensure_ascii=False)},
            files={"photo": photo},
        )
    if result.get("ok"):
        return result
    # Compatibility fallback for standard Bot API environments.
    plain = re.sub(r"<[^>]+>", "", html.unescape(rich_html))
    plain = re.sub(r"\n{3,}", "\n\n", plain).strip()
    if len(plain) > 950:
        plain = plain[:950].rsplit(" ", 1)[0] + "..."
    with open(image_path, "rb") as photo:
        return telegram_call("sendPhoto", data={"chat_id": TELEGRAM_CHANNEL, "caption": plain}, files={"photo": photo})


def persist_published(item: dict, story: dict, message_id=None):
    event_id = hashlib_sha1(item.get("url", ""))
    STATE["events"][event_id] = {
        "event_key": item.get("event_key") or event_key(item.get("title", "")),
        "headline": story.get("headline", ""),
        "source": story.get("source_name") or source_name(item.get("url", "")),
        "url": item.get("url", ""),
        "importance_score": item.get("importance_score", 0),
        "topic": item.get("topic", ""),
        "published_at": now_iso(),
        "selected_at": now_iso(),
        "status": "published",
        "message_id": message_id,
    }
    STATE["recent_titles"].append(story.get("headline", ""))
    STATE["queue"].pop(item.get("canonical", ""), None)


def hashlib_sha1(value: str) -> str:
    import hashlib
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def process_candidate(item: dict):
    article_text, image_url = extract_article(item)
    if not article_text:
        logger.warning("DROP extraction: %s", item.get("title"))
        return None
    item = dict(item)
    if image_url:
        item["image"] = image_url
    story = generate_story(item, article_text)
    if not story:
        return None
    if not verify_story(story, article_text):
        logger.warning("DROP claim verification: %s", story.get("headline", ""))
        return None
    return item, story


def self_test() -> int:
    assert STORIES_PER_RUN == 6
    assert 7 <= 10
    assert allowed_domain("https://deadline.com/feature/x")
    assert not allowed_domain("https://example.com/x")
    assert title_similarity("Netflix announces Stranger Things 5", "Netflix Announces Stranger Things Season 5") > 0.7
    sample_item = {"url": "https://variety.com/example"}
    sample_story = {
        "headline": "Netflix Announces Major New Series Release Date",
        "summary": "Netflix confirmed a new release date for the series.",
        "highlights": ["Release date confirmed", "Netflix is the platform", "Production remains active"],
        "context": "The project is a major scripted series with broad audience interest.",
        "bottom_line": "The announcement changes the rollout timing for viewers.",
        "hashtags": ["Netflix", "Series"],
        "source_name": "Variety",
    }
    assert "THE CONTEXT" in format_rich_message(sample_story, sample_item)
    assert "BOTTOM LINE" in format_rich_message(sample_story, sample_item)
    print("self-test: PASS")
    return 0


def run() -> int:
    logger.info("ENTERTAINMENTNEWSROOM V1")
    logger.info("Channel=%s Mode=%s", TELEGRAM_CHANNEL, NEWS_MODE)
    prune_state()
    for feed in RSS_FEEDS:
        fetch_rss_feed(feed)
    google_news_rss("major movie series streaming entertainment news")
    google_news_rss("Bollywood Pan India Netflix Korean Chinese drama entertainment news")
    exa_gap_fill()
    save_state()

    candidates = available_candidates()
    logger.info("eligible=%d", len(candidates))
    if not candidates:
        return 0

    ranked = collapse_events(rank_candidates(candidates))
    logger.info("ranked_publishable=%d", len(ranked))
    pool = ranked[:RECOVERY_POOL_SIZE]
    published = 0
    attempted = 0

    for item in pool:
        if published >= STORIES_PER_RUN:
            break
        attempted += 1
        result = process_candidate(item)
        if not result:
            continue
        final_item, story = result
        if already_published_event(story["headline"]):
            logger.info("DROP duplicate event: %s", story["headline"])
            continue
        image_path = create_branded_image(final_item, story)
        rich_html = format_rich_message(story, final_item)
        response = send_rich_photo(image_path, rich_html)
        if not response.get("ok"):
            logger.error("Telegram publish failed: %s", response)
            continue
        message_id = response.get("result", {}).get("message_id")
        persist_published(final_item, story, message_id)
        POSTED_URLS.add(canonical_url(final_item["url"]))
        save_posted_url(final_item["url"])
        save_state()
        published += 1
        logger.info("ACCEPT #%d rank=%s score=%s title=%s", published, final_item.get("editor_rank"), final_item.get("importance_score"), story.get("headline"))
        time.sleep(POST_DELAY_SECONDS)

    save_state()
    logger.info("done published=%d attempted=%d", published, attempted)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    return self_test() if args.self_test else run()


if __name__ == "__main__":
    raise SystemExit(main())
