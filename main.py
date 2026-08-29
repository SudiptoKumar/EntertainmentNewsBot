# EntertainmentNewsBot
# Channel: @EntertainmentNewsroom

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

DEFAULTS = {
    "channel": "@EntertainmentNewsroom",
    "mode": "entertainment",
    "publish_threshold": 80,
    "max_stories_per_run": 12,
    "lookback_hours": 36,
    "ranking_pool_size": 36,
    "max_candidates_per_sector": 90,
    "max_exa_candidates": 80,
    "max_google_candidates": 60,
}

SECTORS = {
    "Hollywood": {
        "label": "Hollywood",
        "topics": [
            "Major Hollywood Movies", "Major Hollywood Series", "Franchise and IP",
            "Streaming Originals", "Major Casting", "Trailers and First Looks",
            "Release Dates", "Renewals and Cancellations", "Distribution Rights",
            "Studio and Platform Strategy", "Major Production Developments",
        ],
        "domains": [
            "deadline.com", "variety.com", "hollywoodreporter.com", "thewrap.com",
            "indiewire.com", "collider.com", "tvline.com", "ew.com",
            "screenrant.com", "empireonline.com", "netflix.com", "about.netflix.com",
            "tudum.com", "press.wbd.com", "apple.com", "aboutamazon.com",
            "amazon.com", "press.disneyplus.com", "disneyplus.com", "paramount.com",
            "peacocktv.com", "nbcuniversal.com", "warnerbros.com", "marvel.com",
            "dc.com", "sonypictures.com", "universalpictures.com",
        ],
        "queries": [
            "major Hollywood movie news latest studio franchise casting trailer",
            "major Netflix HBO Apple TV Amazon Prime Disney series movie announcement",
            "major Hollywood production casting release date trailer first look",
            "major franchise sequel reboot adaptation movie news",
            "major streaming series renewal cancellation casting production news",
            "major Hollywood streaming rights distribution deal news",
        ],
    },
    "Indian": {
        "label": "Indian",
        "topics": [
            "Bollywood", "Pan-Indian Cinema", "Telugu Cinema", "Tamil Cinema",
            "Malayalam Cinema", "Kannada Cinema", "Major Indian OTT", "Major Indian Casting",
            "Indian Franchises", "Trailers and First Looks", "Release Dates",
            "Production and Distribution", "International OTT Deals",
        ],
        "domains": [
            "ottplay.com", "filmibeat.com", "pinkvilla.com", "bollywoodhungama.com",
            "indianexpress.com", "timesofindia.indiatimes.com", "hindustantimes.com",
            "news18.com", "gadgets360.com", "ndtv.com", "indiatoday.in",
            "koimoi.com", "deadline.com", "variety.com", "netflix.com",
            "about.netflix.com", "tudum.com", "aboutamazon.com", "primevideo.com",
            "hotstar.com", "jiostar.com", "sonyliv.com", "zee5.com",
            "jio.com", "marvel.com", "warnerbros.com", "disneyplus.com",
        ],
        "queries": [
            "major Bollywood movie news upcoming big budget franchise casting trailer",
            "major Indian pan Indian movie Telugu Tamil Malayalam Kannada news",
            "major Indian OTT Netflix Prime Video JioHotstar SonyLIV series movie news",
            "major Indian film production announcement release date first look trailer",
            "major Indian film streaming rights international OTT deal",
            "major Indian franchise sequel big budget movie news",
        ],
    },
    "International": {
        "label": "International",
        "topics": [
            "Korean Drama", "Korean Film", "Chinese Drama", "Chinese Film",
            "Japanese Film and Series", "International Streaming Originals",
            "International OTT Deals", "Major Asian Production", "Major Casting",
            "Trailers and First Looks", "Release Dates", "Renewals and Cancellations",
        ],
        "domains": [
            "soompi.com", "asianwiki.com", "mydramalist.com", "dramazoom.com",
            "koreaherald.com", "koreajoongangdaily.joins.com",
            "scmp.com", "cdramasquare.com", "chinesedrama.info", "netflix.com",
            "about.netflix.com", "tudum.com", "disneyplus.com", "press.disneyplus.com",
            "viki.com", "tving.com", "iq.com", "iqiyi.com", "wetv.vip",
            "youku.tv", "deadline.com", "variety.com", "hollywoodreporter.com",
        ],
        "queries": [
            "major Korean drama Netflix Disney Plus TVING casting production trailer",
            "major Chinese drama Tencent iQIYI Youku Netflix international streaming news",
            "major Korean film international OTT distribution production news",
            "major Chinese film international streaming rights production news",
            "major Asian drama production house international OTT collaboration",
            "major Korean Chinese drama trailer release date renewal cancellation news",
        ],
    },
}

def sector(name: str):
    return SECTORS[name]


def write_defaults_sources():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "sources.json").write_text(json.dumps(SECTORS, indent=2, ensure_ascii=False), encoding="utf-8")


PUBLISH_THRESHOLD = 80

WEIGHTS = {
    "event_significance": 25,
    "audience_impact": 20,
    "project_importance": 15,
    "platform_or_studio": 10,
    "cast_or_creator": 10,
    "international_reach": 10,
    "novelty": 5,
    "recency": 5,
}

PROMPT_RULES = {
    "Hollywood": "Rank major Hollywood film and scripted-series news. Prioritize major studios, franchises, premium streaming originals, globally recognized projects, and developments likely to matter to a broad international audience.",
    "Indian": "Rank major Indian film and scripted-series news. Give strong weight to major Bollywood titles, high-budget or major-scale pan-Indian projects, established stars/directors, major production houses, important franchises, and significant OTT or international distribution.",
    "International": "Rank major international scripted entertainment, with special focus on high-profile Korean and Chinese drama/film. Prioritize reputable production houses, major broadcasters/platforms, recognized actors, international OTT distribution, and major Netflix/Disney+/Viki/TVING/iQIYI/Tencent/Youku projects.",
}

NEGATIVE_RULES = """
Normally reject or score below 80:
- celebrity lifestyle, fashion, relationships, dating, vacations, birthdays, airport sightings
- awards appearances/fashion unless the underlying project announcement is materially important
- rumors, leaks, speculation, unconfirmed casting, fan claims
- minor OTT catalog additions
- obscure/small titles with no meaningful national or international relevance
- routine social-media posts
- trivial production updates
- generic interviews without a major project development
- repetitive rewrites of an already-covered event
"""


def build_prompt(sector: str, topics: list[str]) -> str:
    topic_list = ", ".join(topics)
    return f"""
You are the senior editorial ranking desk for @EntertainmentNewsroom.

Sector: {sector}
{PROMPT_RULES[sector]}

This is a selective major-news channel, not a comprehensive entertainment feed.
All candidates in this batch MUST be scored independently. Do not force publication,
do not use a fixed post quota, and do not reward a story merely because the source is popular.
A score >= 80 is publishable only after factual verification.

IMPORTANT: rank the underlying EVENT, not headline excitement. Avoid celebrity/showbiz noise.
The channel intentionally ignores most routine entertainment updates.

{NEGATIVE_RULES}

Score these 8 dimensions from 0 to 100:
- event_significance: How important is the event itself?
- audience_impact: Likely interest among the target audience?
- project_importance: Importance of the underlying film/series/IP/franchise?
- platform_or_studio: Importance of the platform, studio, network or production house?
- cast_or_creator: Importance of the principal cast/director/showrunner to this project?
- international_reach: National/global distribution and cross-market relevance?
- novelty: Is this a genuinely new development rather than repetition?
- recency: Freshness within the current monitoring window?

Overall score MUST be a weighted score using:
{WEIGHTS}

Editorial calibration:
90-100 = exceptional major entertainment news
85-89 = very high importance
80-84 = publishable major news
70-79 = interesting but below publication threshold
50-69 = low priority
0-49 = weak, excluded, rumor, niche, gossip or routine

A famous actor alone is not enough. A famous platform alone is not enough.
An OTT title is not automatically important.
A large budget is a signal, not an automatic pass.

Allowed topic labels: {topic_list}

Return EVERY candidate.
"""


def weighted_score(factors: dict) -> int:
    total = 0.0
    for key, weight in WEIGHTS.items():
        value = max(0, min(100, int(factors.get(key, 0))))
        total += value * weight / 100.0
    return round(total)


import os
import re
import json
import time
import html
import argparse
import logging
import hashlib
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlparse, urljoin, quote
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from io import BytesIO

import requests
import feedparser
import trafilatura
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageFile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from exa_py import Exa
from cerebras.cloud.sdk import Cerebras



# ============================================================
# CONFIGURATION
# ============================================================

EXA_API_KEY = os.environ["EXA_API_KEY"]
CEREBRAS_API_KEY = os.environ["CEREBRAS_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

TELEGRAM_CHANNEL = (os.environ.get("TELEGRAM_CHANNEL") or DEFAULTS["channel"]).strip()

# Optional. If set, feed-down alerts go here (a private chat/DM with the
# bot, not the public channel). If empty, alerts only go to the run log.
TELEGRAM_ADMIN_CHAT_ID = (os.environ.get("TELEGRAM_ADMIN_CHAT_ID") or "").strip()

NEWS_MODE = (os.environ.get("NEWS_MODE") or DEFAULTS["mode"]).strip().lower()

VALID_NEWS_MODES = {"entertainment"}
if NEWS_MODE not in VALID_NEWS_MODES:
    raise ValueError(
        f"Invalid NEWS_MODE={NEWS_MODE!r}; expected one of {sorted(VALID_NEWS_MODES)}"
    )

CEREBRAS_MODEL = os.environ.get(
    "CEREBRAS_MODEL",
    "gpt-oss-120b",
)

POSTED_FILE = os.environ.get("POSTED_FILE", "posted_urls.txt")
STATE_FILE = os.environ.get("STATE_FILE", "news_state.json")

BD_TZ = ZoneInfo("Asia/Dhaka")

# Editorial target: publish only clearly important entertainment stories.
# Stories compete within three independent sector leaderboards; the cap is a safety fuse, not a quota.
MAX_STORIES_PER_RUN = int(os.environ.get("MAX_POSTS_PER_RUN", os.environ.get("TELEGRAM_PUBLISH_LIMIT", DEFAULTS["max_stories_per_run"])))
RANKING_POOL_SIZE = int(os.environ.get("RANKING_POOL_SIZE", DEFAULTS["ranking_pool_size"]))
DISCOVERY_LOOKBACK_HOURS = int(os.environ.get("DISCOVERY_LOOKBACK_HOURS", DEFAULTS["lookback_hours"]))
PUBLISH_THRESHOLD = int(os.environ.get("PUBLISH_THRESHOLD", DEFAULTS["publish_threshold"]))

# Reliability / quality
POST_DELAY_SECONDS = 3.5
ROLLING_DISCOVERY_HOURS = DISCOVERY_LOOKBACK_HOURS
FUTURE_TOLERANCE_MINUTES = 10
QUEUE_RETENTION_DAYS = 4
EVENT_RETENTION_DAYS = 30
MAX_RSS_CANDIDATES = 240
MAX_EXA_CANDIDATES = 60
MAX_GOOGLE_NEWS_CANDIDATES = 40
THIN_EXCERPT_CHARS = 150
MAX_EXCERPT_ENRICH = 12
MAX_SOURCE_PER_RUN = 99
MAX_CANDIDATES_PER_SECTOR = int(os.environ.get("MAX_CANDIDATES_PER_SECTOR", DEFAULTS["max_candidates_per_sector"]))
MAX_RICH_CHARACTERS = 1024

# Lightweight English stopwords used only by the conservative event/entity
# deduplication layer. This is deliberately small so technology entities and
# meaningful short terms such as AI, OS, UI, and VR are retained.
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for",
    "from", "with", "by", "at", "as", "is", "are", "was", "were",
    "be", "been", "being", "has", "have", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can",
    "this", "that", "these", "those", "it", "its", "their", "they",
    "them", "he", "she", "his", "her", "we", "our", "you", "your",
    "new", "after", "before", "over", "into", "than", "about", "from",
}

# RSS-first sources. Exa remains a fallback/gap filler.
# RSS feeds: best-effort discovery. Source allow-lists below remain authoritative.
RSS_FEEDS = [
    {"name": "Deadline", "region": "Hollywood", "url": "https://deadline.com/feed/"},
    {"name": "Variety", "region": "Hollywood", "url": "https://variety.com/feed/"},
    {"name": "The Hollywood Reporter", "region": "Hollywood", "url": "https://www.hollywoodreporter.com/feed/"},
    {"name": "TheWrap", "region": "Hollywood", "url": "https://www.thewrap.com/feed/"},
    {"name": "IndieWire", "region": "Hollywood", "url": "https://www.indiewire.com/feed/"},
    {"name": "Collider", "region": "Hollywood", "url": "https://collider.com/feed/"},
    {"name": "TVLine", "region": "Hollywood", "url": "https://tvline.com/feed/"},
    {"name": "OTTplay", "region": "Indian", "url": "https://www.ottplay.com/rss"},
    {"name": "Filmibeat", "region": "Indian", "url": "https://www.filmibeat.com/rss/feeds/"},
    {"name": "Pinkvilla", "region": "Indian", "url": "https://www.pinkvilla.com/feed"},
    {"name": "Indian Express Entertainment", "region": "Indian", "url": "https://indianexpress.com/section/entertainment/feed/"},
    {"name": "Soompi", "region": "International", "url": "https://www.soompi.com/feed"},
    {"name": "DramaZOOM", "region": "International", "url": "https://www.dramazoom.com/feed/"},
    {"name": "Korea Herald", "region": "International", "url": "https://www.koreaherald.com/rss"},
    {"name": "SCMP Entertainment", "region": "International", "url": "https://www.scmp.com/rss/91/feed"},
]

SECTOR_NAMES = list(SECTORS.keys())
TOPICS = {k: v["topics"] for k, v in SECTORS.items()}

# Source universe is kept in this single-file architecture for easy maintenance.
SOURCE_NAMES = {}
for _sector_name, _cfg in SECTORS.items():
    for _domain in _cfg["domains"]:
        SOURCE_NAMES[_domain] = _domain

ALL_PRIMARY_DOMAINS = sorted({d for cfg in SECTORS.values() for d in cfg["domains"]})
ALL_FALLBACK_DOMAINS = []

GOOGLE_NEWS_QUERIES = {k: v["queries"] for k, v in SECTORS.items()}
GOOGLE_NEWS_LOCALE = {"Hollywood": ("en-US", "US", "US:en"), "Indian": ("en-IN", "IN", "IN:en"), "International": ("en-US", "US", "US:en")}

INSTITUTIONS = []

CATEGORY_HASHTAGS = {
    "Major Hollywood Movies": ["#Hollywood", "#Movies"],
    "Major Hollywood Series": ["#Hollywood", "#Series"],
    "Franchise and IP": ["#Hollywood", "#Franchise"],
    "Streaming Originals": ["#Streaming", "#Series"],
    "Major Casting": ["#Casting", "#Movies"],
    "Trailers and First Looks": ["#Trailer", "#Movies"],
    "Release Dates": ["#ReleaseDate", "#Movies"],
    "Renewals and Cancellations": ["#Renewal", "#Series"],
    "Distribution Rights": ["#OTT", "#Streaming"],
    "Studio and Platform Strategy": ["#OTT", "#Streaming"],
    "Major Production Developments": ["#Production", "#Movies"],
    "Bollywood": ["#Bollywood", "#IndianCinema"],
    "Pan-Indian Cinema": ["#PanIndian", "#IndianCinema"],
    "Telugu Cinema": ["#TeluguCinema", "#IndianCinema"],
    "Tamil Cinema": ["#TamilCinema", "#IndianCinema"],
    "Malayalam Cinema": ["#MalayalamCinema", "#IndianCinema"],
    "Kannada Cinema": ["#KannadaCinema", "#IndianCinema"],
    "Major Indian OTT": ["#IndianOTT", "#OTT"],
    "Major Indian Casting": ["#IndianCinema", "#Casting"],
    "Indian Franchises": ["#IndianCinema", "#Franchise"],
    "Production and Distribution": ["#IndianCinema", "#Production"],
    "International OTT Deals": ["#OTT", "#International"],
    "Korean Drama": ["#KDrama", "#KoreanDrama"],
    "Korean Film": ["#KoreanCinema", "#Movies"],
    "Chinese Drama": ["#CDrama", "#ChineseDrama"],
    "Chinese Film": ["#ChineseCinema", "#Movies"],
    "Japanese Film and Series": ["#JapaneseCinema", "#Series"],
    "International Streaming Originals": ["#Streaming", "#International"],
    "Major Asian Production": ["#AsianCinema", "#International"],
}


CATEGORY_GROUPS = {
    "AI": {"AI Models and Products", "Hugging Face"},
    "Platforms": {"Smartphones", "Operating Systems", "Browsers", "Search", "Social Platforms", "Cloud Platforms", "App Stores", "Major Outages"},
    "Security": {"Cybersecurity", "Privacy"},
    "Industry": {"Major Tech Companies", "Technology Industry", "Acquisitions and Mergers", "Layoffs and Restructuring", "Startups", "Y Combinator"},
    "Products and Ecosystem": {"Consumer Technology", "New Products", "Pricing and Subscriptions", "Open Source", "GitHub Trends"},
}

TOPIC_ALIASES = {}

def canonical_topic(topic, region="Hollywood"):
    key = safe_text(topic).lower().strip()
    topics = TOPICS.get(region, [])
    for item in topics:
        if key == item.lower():
            return item
    patterns = [
        (("bollywood", "hindi"), "Bollywood"),
        (("pan-indian", "pan indian", "telugu", "tamil", "malayalam", "kannada"), "Pan-Indian Cinema"),
        (("korean drama", "k-drama"), "Korean Drama"),
        (("korean film", "korean movie"), "Korean Film"),
        (("chinese drama", "c-drama"), "Chinese Drama"),
        (("chinese film", "chinese movie"), "Chinese Film"),
        (("netflix", "hbo", "max", "apple tv", "prime video", "disney+"), "Streaming Originals"),
        (("casting", "cast"), "Major Casting"),
        (("trailer", "teaser", "first look", "poster"), "Trailers and First Looks"),
        (("release date", "premiere"), "Release Dates"),
        (("renew", "renewed", "renewal", "cancel", "cancelled", "canceled"), "Renewals and Cancellations"),
        (("rights", "acquisition", "acquired", "distribution"), "Distribution Rights"),
    ]
    for needles, canonical in patterns:
        if any(n in key for n in needles) and canonical in topics:
            return canonical
    return topics[0] if topics else "Major Entertainment"

def category_hashtags(story):
    tags = []
    topic = safe_text(story.get("topic"))
    region = safe_text(story.get("region"))
    for tag in CATEGORY_HASHTAGS.get(topic, []):
        if tag not in tags:
            tags.append(tag)
    region_tag = {
        "Hollywood": "#Hollywood",
        "Indian": "#IndianCinema",
        "International": "#International",
    }.get(region)
    if region_tag and region_tag not in tags:
        tags.append(region_tag)
    if "#Entertainment" not in tags:
        tags.append("#Entertainment")
    return tags[:3]


def coverage_state():
    return STATE.setdefault("category_coverage", {})


def update_category_coverage(story):
    topic = safe_text(story.get("topic"))
    if topic:
        coverage_state()[topic] = now_iso()


def refresh_category_coverage():
    coverage = coverage_state()
    for event in STATE.get("events", {}).values():
        if event.get("status") != "published":
            continue
        published_at = parse_datetime(event.get("published_at"))
        if not published_at or published_at.date() != NOW_BD.date():
            continue
        topic = safe_text(event.get("topic"))
        if topic:
            coverage[topic] = event.get("selected_at", published_at.isoformat())


# ============================================================
# LOGGING + HTTP
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("entertainment-news-bot")

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = 50_000_000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    )
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

adapter = HTTPAdapter(
    max_retries=retry_policy,
    pool_connections=20,
    pool_maxsize=20,
)

session.mount("https://", adapter)
session.mount("http://", adapter)


# ============================================================
# HELPERS
# ============================================================

def safe_text(value):
    return "" if value is None else str(value).strip()


def canonical_url(url):
    raw = safe_text(url)
    if not raw:
        return ""

    parsed = urlparse(raw)

    host = (
        parsed.netloc.lower()
        .removeprefix("www.")
        .removeprefix("amp.")
    )

    path = parsed.path or "/"
    path = path.rstrip("/")
    path = re.sub(r"/amp$", "", path, flags=re.I)
    path = re.sub(r"\.amp$", "", path, flags=re.I)

    return f"{host}{path}"


def normalize_title(title):
    text = safe_text(title).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_tokens(text):
    text = normalize_title(text)
    return {
        token
        for token in text.split()
        if len(token) >= 3
    }


def token_jaccard(a, b):
    aa = title_tokens(a)
    bb = title_tokens(b)
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / max(1, len(aa | bb))


def title_similarity(a, b):
    na = normalize_title(a)
    nb = normalize_title(b)
    if not na or not nb:
        return 0.0
    sequence = SequenceMatcher(None, na, nb).ratio()
    jaccard = token_jaccard(na, nb)
    return max(sequence, jaccard)


def event_similarity(a, b):
    """Cheap event-level similarity without an embedding dependency."""
    sequence = SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()
    jaccard = token_jaccard(a, b)
    return (0.55 * sequence) + (0.45 * jaccard)


def likely_same_event(a, b):
    return (
        title_similarity(a, b) >= 0.90
        or event_similarity(a, b) >= 0.80
    )


def parse_datetime(value):
    raw = safe_text(value)
    if not raw:
        return None

    try:
        dt = datetime.fromisoformat(
            raw.replace("Z", "+00:00")
        )
        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )
        return dt.astimezone(BD_TZ)
    except Exception:
        pass

    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )
        return dt.astimezone(BD_TZ)
    except Exception:
        return None


def feed_entry_datetime(entry):
    for key in (
        "published_parsed",
        "updated_parsed",
        "created_parsed",
    ):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime(
                    *parsed[:6],
                    tzinfo=timezone.utc,
                ).astimezone(BD_TZ)
            except Exception:
                pass

    for key in (
        "published",
        "updated",
        "created",
    ):
        dt = parse_datetime(
            entry.get(key)
        )
        if dt:
            return dt

    return None


def trim_source_text(text, limit):
    """Trim source text before rendering. Never appends ellipses."""
    text = safe_text(text)
    if len(text) <= limit:
        return text

    trimmed = text[:limit].rstrip()
    if " " in trimmed:
        trimmed = trimmed.rsplit(" ", 1)[0]

    return trimmed.rstrip(" ,:;-/—")


def clean_generated_text(text):
    text = safe_text(text)

    # Prevent visible truncation artifacts.
    text = re.sub(r"\.{2,}", ".", text)
    text = text.replace("\u2026", "")

    # Remove incomplete endings.
    text = re.sub(
        r"\s*[,;:]\s*$",
        "",
        text,
    )
    text = re.sub(
        r"\s*[-—]\s*$",
        "",
        text,
    )

    return text.strip()


def complete_text(text):
    raw = safe_text(text)
    if not raw:
        return False

    # A text that clean_generated_text() would mutilate
    # (trailing dash/comma/colon) is INCOMPLETE.
    if re.search(r"[\s,;:\-—…]+$", raw):
        return False

    text = clean_generated_text(raw)
    if not text:
        return False

    return not text.endswith(
        (",", ";", ":", "-", "—", "…")
    )


def source_name(url):
    domain = (
        urlparse(
            safe_text(url)
        )
        .netloc
        .lower()
        .removeprefix("www.")
    )

    return SOURCE_NAMES.get(
        domain,
        domain or "Source",
    )


def article_region(url):
    return "Entertainment"


def now_iso():
    return datetime.now(
        BD_TZ
    ).isoformat()


# ============================================================
# STATE: QUEUE + EVENTS + KNOWLEDGE
# ============================================================

def default_state():
    return {
        "feeds": {},
        "queue": {},
        "events": {},
        "event_clusters": {},
        "posted_event_ids": [],
        "recent_titles": [],
    }


def load_state():
    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8",
        ) as f:
            data = json.load(f)

        if not isinstance(
            data,
            dict,
        ):
            return default_state()

        base = default_state()
        base.update(data)

        return base

    except Exception:
        return default_state()


def save_state(state):
    tmp = STATE_FILE + ".tmp"

    with open(
        tmp,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(
        tmp,
        STATE_FILE,
    )


def load_posted_urls():
    try:
        with open(
            POSTED_FILE,
            "r",
            encoding="utf-8",
        ) as f:
            return {
                canonical_url(line)
                for line in f
                if safe_text(line)
            }
    except FileNotFoundError:
        return set()


def save_posted_url(canonical):
    if not canonical:
        return

    with open(
        POSTED_FILE,
        "a",
        encoding="utf-8",
    ) as f:
        f.write(
            canonical
            + "\n"
        )


STATE = load_state()
POSTED_URLS = load_posted_urls()


def prune_state():
    cutoff_queue = (
        datetime.now(BD_TZ)
        - timedelta(
            days=QUEUE_RETENTION_DAYS
        )
    )

    cutoff_events = (
        datetime.now(BD_TZ)
        - timedelta(
            days=EVENT_RETENTION_DAYS
        )
    )

    queue = STATE.get(
        "queue",
        {},
    )

    keep_queue = {}

    for key, item in queue.items():
        dt = parse_datetime(
            item.get("last_seen")
            or item.get("published_date")
        )

        if (
            dt
            and dt >= cutoff_queue
        ):
            keep_queue[key] = item

    STATE["queue"] = keep_queue

    events = STATE.get(
        "events",
        {},
    )

    keep_events = {}

    for key, event in events.items():
        dt = parse_datetime(
            event.get("published_at")
            or event.get("selected_at")
        )

        if (
            dt
            and dt >= cutoff_events
        ):
            keep_events[key] = event

    STATE["events"] = keep_events

    titles = STATE.get(
        "recent_titles",
        [],
    )

    STATE["recent_titles"] = titles[-400:]


# ============================================================
# TIME WINDOWS
# ============================================================

NOW_BD = datetime.now(
    BD_TZ
)

TODAY_START = NOW_BD.replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0,
)

YESTERDAY_START = (
    TODAY_START
    - timedelta(days=1)
)

DISCOVERY_START = (
    NOW_BD
    - timedelta(
        hours=ROLLING_DISCOVERY_HOURS
    )
)
DISCOVERY_END = (
    NOW_BD
    + timedelta(
        minutes=FUTURE_TOLERANCE_MINUTES
    )
)

DISCOVERY_TARGET_PER_REGION = 18


# ============================================================
# CLIENTS
# ============================================================

exa = None
cerebras = None


def get_exa():
    global exa
    if exa is None:
        exa = Exa(api_key=EXA_API_KEY)
    return exa


def get_cerebras():
    global cerebras
    if cerebras is None:
        cerebras = Cerebras(api_key=CEREBRAS_API_KEY)
    return cerebras


# ============================================================
# CANDIDATE FILTERING
# ============================================================

BAD_PATH_RE = re.compile(
    r"/(opinion|editorial|sponsored|"
    r"tag|topic|live-blog|liveblog|"
    r"photo|photos|video)(/|$)",
    re.I,
)

BAD_TITLE_RE = re.compile(
    r"\b(sponsored|advertisement|"
    r"promo|opinion|editorial)\b",
    re.I,
)


def candidate_basic_allowed(item):
    url = safe_text(
        item.get("url")
    )
    title = safe_text(
        item.get("title")
    )
    published = item.get(
        "published_dt"
    )

    if (
        not url
        or not title
        or not published
    ):
        return False

    if BAD_PATH_RE.search(
        urlparse(url).path
    ):
        return False

    if BAD_TITLE_RE.search(
        title
    ):
        return False

    if not (
        DISCOVERY_START
        <= published
        <= DISCOVERY_END
    ):
        return False

    region = safe_text(item.get("region"))
    if region and not allowed_source_for_region(url, region):
        return False

    canonical = canonical_url(
        url
    )

    return bool(
        canonical
    )


def title_duplicate_against_state(title):
    for previous in STATE.get(
        "recent_titles",
        [],
    )[-250:]:
        if title_similarity(
            title,
            previous,
        ) >= 0.88:
            return True

    return False


def title_duplicate_against_list(
    title,
    candidates,
    threshold=0.88,
):
    for candidate in candidates:
        if title_similarity(
            title,
            candidate["title"],
        ) >= threshold:
            return True

    return False


# ============================================================
# RSS INGESTION + PERSISTENT QUEUE
# ============================================================

def extract_entry_image(
    entry,
    page_url,
):
    for key in (
        "media_content",
        "media_thumbnail",
    ):
        for item in entry.get(
            key,
            [],
        ):
            image_url = safe_text(
                item.get("url")
            )

            if image_url:
                return urljoin(
                    page_url,
                    image_url,
                )

    for enclosure in entry.get(
        "enclosures",
        [],
    ):
        href = safe_text(
            enclosure.get("href")
        )

        mime = safe_text(
            enclosure.get("type")
        ).lower()

        if (
            href
            and (
                not mime
                or mime.startswith(
                    "image/"
                )
            )
        ):
            return urljoin(
                page_url,
                href,
            )

    return ""


def queue_candidate(item):
    canonical = item["canonical"]

    existing = STATE["queue"].get(
        canonical
    )

    if existing:
        existing.update(
            {
                "last_seen": now_iso(),
                "image": (
                    item.get("image")
                    or existing.get("image", "")
                ),
            }
        )
        return

    STATE["queue"][canonical] = {
        **item,
        "status": "pending",
        "first_seen": now_iso(),
        "last_seen": now_iso(),
    }


def fetch_rss_feed(
    feed_def,
):
    url = feed_def["url"]

    old = STATE["feeds"].get(
        url,
        {},
    )

    headers = dict(
        HEADERS
    )

    if old.get("etag"):
        headers["If-None-Match"] = old[
            "etag"
        ]

    if old.get(
        "last_modified"
    ):
        headers["If-Modified-Since"] = old[
            "last_modified"
        ]

    try:
        response = session.get(
            url,
            headers=headers,
            timeout=20,
        )

        # 304 means the queue remains intact. The feed is reachable,
        # so this counts as healthy and clears any fail streak.
        if response.status_code == 304:
            logger.info(
                "RSS 304: %s",
                feed_def["name"],
            )
            mark_feed_healthy(feed_def, old)
            return 0

        if response.status_code >= 400:
            logger.warning(
                "RSS %s returned %s",
                feed_def["name"],
                response.status_code,
            )
            mark_feed_failed(feed_def, old)
            return 0

        STATE["feeds"][url] = {
            "etag": response.headers.get(
                "ETag",
                old.get("etag"),
            ),
            "last_modified": response.headers.get(
                "Last-Modified",
                old.get("last_modified"),
            ),
            "last_checked": now_iso(),
            "fail_count": 0,
            "alerted": False,
        }

        parsed = feedparser.parse(
            response.content
        )

        added = 0

        for entry in parsed.entries:
            published_dt = feed_entry_datetime(
                entry
            )

            date_estimated = False

            if not published_dt:
                # Some feeds send a date format we cannot parse.
                # Do not throw the story away: use fetch time instead,
                # and mark it so downstream code knows it is a guess.
                published_dt = datetime.now(
                    BD_TZ
                )
                date_estimated = True

            article_url = urljoin(
                url,
                safe_text(
                    entry.get("link")
                ),
            )

            title = safe_text(
                entry.get("title")
            )

            if not article_url or not title:
                continue

            item = {
                "title": title,
                "url": article_url,
                "canonical": canonical_url(
                    article_url
                ),
                "published_dt": published_dt.isoformat(),
                "published_date": published_dt.isoformat(),
                "source": feed_def["name"],
                "region": feed_def["region"],
                "excerpt": BeautifulSoup(
                    safe_text(
                        entry.get(
                            "summary"
                        )
                        or entry.get(
                            "description"
                        )
                    ),
                    "html.parser",
                ).get_text(
                    " ",
                    strip=True,
                )[:2000],
                "image": extract_entry_image(
                    entry,
                    article_url,
                ),
                "discovery": "rss",
                "date_estimated": date_estimated,
            }

            if not candidate_basic_allowed(
                {
                    **item,
                    "published_dt": published_dt,
                }
            ):
                continue

            if (
                item["canonical"]
                in POSTED_URLS
            ):
                continue

            before = item["canonical"] in STATE[
                "queue"
            ]

            queue_candidate(
                item
            )

            if not before:
                added += 1

        return added

    except Exception as exc:
        logger.warning(
            "RSS failed %s: %s",
            feed_def["name"],
            exc,
        )
        mark_feed_failed(feed_def, old)
        return 0


# Consecutive failed runs before we alert about a broken feed.
FEED_FAIL_ALERT_THRESHOLD = 3


def mark_feed_healthy(feed_def, old):
    STATE["feeds"][feed_def["url"]] = {
        **old,
        "last_checked": now_iso(),
        "fail_count": 0,
        "alerted": False,
    }


def mark_feed_failed(feed_def, old):
    fail_count = int(old.get("fail_count", 0)) + 1

    STATE["feeds"][feed_def["url"]] = {
        **old,
        "last_checked": now_iso(),
        "fail_count": fail_count,
    }

    if fail_count >= FEED_FAIL_ALERT_THRESHOLD and not old.get("alerted"):
        alert_feed_down(feed_def, fail_count)
        STATE["feeds"][feed_def["url"]]["alerted"] = True


def alert_feed_down(feed_def, fail_count):
    """Tell the admin a source has gone quiet, instead of failing silently forever."""
    message = (
        f"Feed down: {feed_def['name']} ({feed_def['region']})\n"
        f"Failed {fail_count} runs in a row.\n"
        f"URL: {feed_def['url']}\n"
        f"It will keep retrying, but this source is not feeding the bot right now."
    )

    if TELEGRAM_ADMIN_CHAT_ID:
        try:
            telegram_call(
                "sendMessage",
                data={
                    "chat_id": TELEGRAM_ADMIN_CHAT_ID,
                    "text": message,
                },
            )
        except Exception as exc:
            logger.warning(
                "Feed-down alert failed to send: %s",
                exc,
            )

    logger.error(message)


def collect_rss():
    added = 0

    for feed_def in RSS_FEEDS:
        added += fetch_rss_feed(
            feed_def
        )

    # Critical: queue is saved together with feed validators.
    # A later 304 cannot erase unposted queued stories.
    save_state(
        STATE
    )

    logger.info(
        "RSS queue additions: %d",
        added,
    )

    return added


# ============================================================
# EXA GAP-FILL DISCOVERY
# ============================================================

# ============================================================
# SOURCE UNIVERSE
# ============================================================
# Configured in src/config.py. Keep a single approved domain universe.
ALL_PRIMARY_DOMAINS = sorted({d for cfg in SECTORS.values() for d in cfg["domains"]})
ALL_FALLBACK_DOMAINS = []
ALL_ALLOWED_DOMAINS = ALL_PRIMARY_DOMAINS

def normalized_domain(url_or_source):
    raw = safe_text(url_or_source).lower()
    if "://" in raw:
        raw = urlparse(raw).netloc
    return raw.split(":")[0].removeprefix("www.").strip().rstrip("/")

def is_domain_allowed(url, domains):
    domain = normalized_domain(url)
    return any(domain == d or domain.endswith("." + d) for d in domains)

def primary_domain_allowed(url, region=None):
    domains = PRIMARY_DOMAINS_BY_SECTOR.get(region, ALL_PRIMARY_DOMAINS) if region else ALL_PRIMARY_DOMAINS
    return is_domain_allowed(url, domains)

def fallback_domain_allowed(url, region=None):
    return False

def allowed_source_for_region(url, region=None):
    return primary_domain_allowed(url, region) or fallback_domain_allowed(url, region)

PRIMARY_DOMAINS_BY_SECTOR = {k: v["domains"] for k, v in SECTORS.items()}
FALLBACK_DOMAINS_BY_SECTOR = {k: [] for k in SECTORS}

# ============================================================
# GOOGLE NEWS RSS: FREE GAP FILL
# ============================================================

def resolve_google_news_url(link):
    """Google News RSS gives a redirect link, not the publisher URL.
    Follow it once (without downloading the full page) to get the
    real article URL. Return "" if it cannot be resolved safely."""
    try:
        response = session.get(
            link,
            timeout=10,
            allow_redirects=True,
            headers=HEADERS,
            stream=True,
        )
        real_url = safe_text(response.url)
        response.close()

        if not real_url or "news.google.com" in real_url:
            return ""

        return real_url

    except Exception:
        return ""


def google_news_gap_fill(
    region,
    existing_count,
    needed,
):
    # Same thin-coverage trigger as Exa, tried first because it is free.
    if existing_count >= max(
        6,
        needed * 3,
    ):
        return 0

    queries = GOOGLE_NEWS_QUERIES.get(region, [])
    hl, gl, ceid = GOOGLE_NEWS_LOCALE.get(region, ("en-US", "US", "US:en"))

    added = 0

    for query in queries:
        try:
            feed_url = (
                "https://news.google.com/rss/search?q="
                + quote(f"{query} when:2d")
                + f"&hl={hl}&gl={gl}&ceid={ceid}"
            )

            response = session.get(
                feed_url,
                timeout=15,
                headers=HEADERS,
            )

            if response.status_code >= 400:
                continue

            parsed = feedparser.parse(
                response.content
            )

            for entry in parsed.entries[:6]:
                title = safe_text(
                    entry.get("title")
                )
                link = safe_text(
                    entry.get("link")
                )

                if not title or not link:
                    continue

                real_url = resolve_google_news_url(
                    link
                )

                if not real_url:
                    continue

                published_dt = feed_entry_datetime(
                    entry
                )
                date_estimated = False

                if not published_dt:
                    published_dt = datetime.now(
                        BD_TZ
                    )
                    date_estimated = True

                item = {
                    "title": title,
                    "url": real_url,
                    "canonical": canonical_url(
                        real_url
                    ),
                    "published_dt": published_dt.isoformat(),
                    "published_date": published_dt.isoformat(),
                    "source": source_name(
                        real_url
                    ),
                    "region": region,
                    "excerpt": BeautifulSoup(
                        safe_text(
                            entry.get("summary")
                        ),
                        "html.parser",
                    ).get_text(
                        " ",
                        strip=True,
                    )[:2000],
                    "image": "",
                    "discovery": "google_news",
                    "date_estimated": date_estimated,
                }

                if not primary_domain_allowed(real_url, region):
                    continue

                if not candidate_basic_allowed(
                    {
                        **item,
                        "published_dt": published_dt,
                    }
                ):
                    continue

                if item["canonical"] in POSTED_URLS:
                    continue

                if item["canonical"] in STATE["queue"]:
                    continue

                queue_candidate(
                    item
                )
                added += 1

                if added >= MAX_GOOGLE_NEWS_CANDIDATES:
                    return added

        except Exception as exc:
            logger.warning(
                "Google News gap fill failed %s: %s",
                region,
                exc,
            )

    return added


def exa_gap_fill(region, existing_count, needed, fallback=False):
    if existing_count >= max(12, needed * 3):
        return 0

    domains = FALLBACK_DOMAINS_BY_SECTOR.get(region, []) if fallback else PRIMARY_DOMAINS_BY_SECTOR.get(region, [])
    if not domains:
        return 0
    queries = GOOGLE_NEWS_QUERIES.get(region, [])

    added = 0
    for query in queries:
        try:
            results = get_exa().search_and_contents(
                query, type="auto", category="news", num_results=8,
                include_domains=domains,
                start_published_date=DISCOVERY_START.isoformat(),
                end_published_date=DISCOVERY_END.isoformat(),
                contents={"highlights": {"max_characters": 900}},
            )
            for result in results.results:
                url = safe_text(getattr(result, "url", ""))
                title = safe_text(getattr(result, "title", ""))
                published_dt = parse_datetime(getattr(result, "published_date", ""))
                if not url or not title or not published_dt:
                    continue
                if fallback:
                    if not fallback_domain_allowed(url, region):
                        continue
                elif not primary_domain_allowed(url, region):
                    continue
                item = {
                    "title": title, "url": url, "canonical": canonical_url(url),
                    "published_dt": published_dt.isoformat(), "published_date": published_dt.isoformat(),
                    "source": source_name(url), "region": region,
                    "excerpt": safe_text(" ".join(getattr(result, "highlights", []) if isinstance(getattr(result, "highlights", []), list) else str(getattr(result, "highlights", ""))))[:2000],
                    "image": safe_text(getattr(result, "image", "")),
                    "discovery": "exa_fallback" if fallback else "exa",
                    "source_pool": "fallback" if fallback else "primary",
                }
                if not candidate_basic_allowed({**item, "published_dt": published_dt}):
                    continue
                if item["canonical"] in POSTED_URLS or item["canonical"] in STATE["queue"]:
                    continue
                queue_candidate(item)
                added += 1
                if added >= MAX_EXA_CANDIDATES:
                    return added
        except Exception as exc:
            logger.warning("Exa %s discovery failed: %s", "fallback" if fallback else "primary", exc)
    return added


def queue_candidates_for_region(
    region,
):
    count = 0

    for item in STATE[
        "queue"
    ].values():
        if (
            item.get("region")
            == region
            and item.get("status")
            == "pending"
        ):
            published = parse_datetime(
                item.get(
                    "published_date"
                )
            )

            if (
                published
                and DISCOVERY_START
                <= published
                <= DISCOVERY_END
            ):
                count += 1

    return count


# ============================================================
# CANDIDATE NORMALIZATION
# ============================================================

# ============================================================
# VERSION 1 EDITORIAL RANKING
# ============================================================

RANK_SCHEMA = {
    "type": "object",
    "properties": {
        "ranked": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "rank": {"type": "integer", "minimum": 1},
                    "score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "factors": {"type": "object", "properties": {k: {"type": "integer", "minimum": 0, "maximum": 100} for k in WEIGHTS}, "required": list(WEIGHTS.keys()), "additionalProperties": False},
                    "important": {"type": "boolean"},
                    "topic": {"type": "string"},
                    "institution": {"type": "string"},
                    "event_key": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["id", "rank", "score", "important", "topic", "institution", "event_key", "reason", "factors"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["ranked"],
    "additionalProperties": False,
}


def enrich_thin_excerpt(item):
    """Best-effort article enrichment. Failure never removes a candidate."""
    try:
        downloaded = trafilatura.fetch_url(item["url"])
        if not downloaded:
            return None
        text = trafilatura.extract(downloaded)
        return safe_text(text)[:1200] if text else None
    except Exception:
        return None


def enrich_thin_excerpts(regional):
    enriched = 0
    for item in regional:
        if enriched >= MAX_EXCERPT_ENRICH:
            break
        excerpt = safe_text(item.get("excerpt", ""))
        if len(excerpt) >= THIN_EXCERPT_CHARS:
            continue
        fuller = enrich_thin_excerpt(item)
        if fuller and len(fuller) > len(excerpt):
            item["excerpt"] = fuller
            enriched += 1
    return regional


def _rank_prompt(region):
    return build_prompt(region, TOPICS.get(region, []))

def _rank_batch(batch, region, batch_no):
    lines = []
    for idx, item in enumerate(batch, start=1):
        published = item.get("published_date", "")
        age_note = ""
        dt = parse_datetime(published)
        if dt:
            age_hours = max(0.0, (NOW_BD - dt).total_seconds() / 3600)
            age_note = f"Age: {age_hours:.1f} hours"
        lines.append("\n".join([
            f"ID: {idx}",
            f"Title: {item.get('title','')}",
            f"Source: {item.get('source','')}",
            f"Published: {published}",
            age_note,
            f"Description/Excerpt: {trim_source_text(item.get('excerpt',''), 650)}",
            "",
        ]))

    try:
        response = get_cerebras().chat.completions.create(
            model=CEREBRAS_MODEL,
            messages=[
                {"role": "system", "content": _rank_prompt(region)},
                {"role": "user", "content": "\n".join(lines)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": f"entertainment_news_rank_batch_{batch_no}",
                    "strict": True,
                    "schema": RANK_SCHEMA,
                },
            },
            reasoning_effort="low",
            temperature=0.0,
            max_completion_tokens=3500,
        )
        data = json.loads(safe_text(response.choices[0].message.content))
        return data.get("ranked", [])
    except Exception as exc:
        logger.error("Ranking batch %d failed: %s", batch_no, exc)
        return []


def rank_candidates(candidates, region):
    """Rank the discovery pool in bounded LLM batches, then merge globally.

    Batching prevents a large structured response from being truncated. The merged result
    is globally ordered by editorial score, then model rank, then freshness.
    """
    if not candidates:
        return []

    regional = sorted(
        candidates,
        key=lambda x: parse_datetime(x.get("published_date")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )[:MAX_CANDIDATES_PER_SECTOR]

    batch_size = 15
    ranked_rows = []
    for offset in range(0, len(regional), batch_size):
        batch = regional[offset:offset + batch_size]
        logger.info("%s RANK BATCH %d: %d candidates", region, offset // batch_size + 1, len(batch))
        rows = _rank_batch(batch, region, offset // batch_size + 1)
        by_id = {idx: item for idx, item in enumerate(batch, start=1)}
        for row in rows:
            try:
                idx = int(row["id"])
            except Exception:
                continue
            if idx not in by_id:
                continue
            item = dict(by_id[idx])
            factors = row.get("factors", {}) if isinstance(row.get("factors", {}), dict) else {}
            score = weighted_score(factors)
            item.update({
                "importance_score": score,
                "important": bool(row.get("important")) and score >= PUBLISH_THRESHOLD,
                "topic": canonical_topic(safe_text(row.get("topic")), region),
                "institution": safe_text(row.get("institution")),
                "event_key": safe_text(row.get("event_key")),
                "rank_reason": safe_text(row.get("reason")),
                "rank_factors": factors,
                "batch_rank": int(row.get("rank", 9999)),
            })
            ranked_rows.append(item)

    # A failed/partial batch is recoverable, but never receives an invented importance score.
    # It remains available only for diagnostics, not eligibility.
    ranked_rows.sort(key=lambda x: (
        -x.get("importance_score", 0),
        x.get("batch_rank", 9999),
        -(parse_datetime(x.get("published_date")).timestamp() if parse_datetime(x.get("published_date")) else 0),
    ))

    for rank, item in enumerate(ranked_rows, start=1):
        item["editor_rank"] = rank

    logger.info("%s RANK MODEL ROWS: %d/%d", region, len(ranked_rows), len(regional))
    return ranked_rows


# ============================================================
# VERSION 1 EVENT DEDUPLICATION
# ============================================================

def extract_entities(text):
    words = re.findall(r"[A-Za-z][A-Za-z&'-]{1,}", safe_text(text).lower())
    return {w for w in words if w not in STOPWORDS}


def entity_overlap(a, b):
    ea = extract_entities(f"{a.get('title','')} {a.get('excerpt','')}")
    eb = extract_entities(f"{b.get('title','')} {b.get('excerpt','')}")
    if not ea or not eb:
        return 0.0
    return len(ea & eb) / max(1, min(len(ea), len(eb)))


def event_similarity_v04(a, b):
    title_score = title_similarity(a.get("title", ""), b.get("title", ""))
    entity_score = entity_overlap(a, b)
    return (0.75 * title_score) + (0.25 * entity_score)


def same_event_window(a, b, hours=30):
    da = parse_datetime(a.get("published_date"))
    db = parse_datetime(b.get("published_date"))
    if not da or not db:
        return False
    return abs((da - db).total_seconds()) <= hours * 3600


def cluster_ranked_events(ranked):
    """Conservative event clustering. Uncertain items are always kept."""
    clusters = []
    ordered = sorted(
        ranked,
        key=lambda x: x.get("editor_rank", 9999),
    )
    for item in ordered:
        placed = False
        for cluster in clusters:
            representative = cluster[0]
            item_event_key = safe_text(item.get("event_key"))
            rep_event_key = safe_text(representative.get("event_key"))
            same_key = bool(
                item_event_key
                and rep_event_key
                and item_event_key == rep_event_key
                and (
                    entity_overlap(item, representative) >= 0.25
                    or title_similarity(item.get("title", ""), representative.get("title", "")) >= 0.55
                )
            )
            if same_key or (
                same_event_window(item, representative)
                and event_similarity_v04(item, representative) >= 0.88
            ):
                cluster.append(item)
                placed = True
                break
        if not placed:
            clusters.append([item])

    output = []
    for index, cluster in enumerate(clusters, start=1):
        representative = cluster[0]
        stable_key = normalize_title(representative.get("title", "")) or representative.get("canonical", "")
        digest = hashlib.sha1(stable_key.encode("utf-8")).hexdigest()[:10]
        cluster_id = f"evt_{digest}"
        sources = sorted({safe_text(x.get("source")) for x in cluster if safe_text(x.get("source"))})
        for member in cluster:
            row = dict(member)
            row.update({
                "event_cluster_id": cluster_id,
                "event_cluster_size": len(cluster),
                "event_sources": sources,
                "event_source_count": len(sources),
                "event_confidence": 1.0 if len(cluster) > 1 else 0.6,
            })
            output.append(row)
    return output


def collapse_event_clusters(ranked):
    clustered = cluster_ranked_events(ranked)
    winners = {}
    for item in clustered:
        key = item.get("event_cluster_id") or item.get("canonical")
        old = winners.get(key)
        if old is None:
            winners[key] = item
            continue
        # Preserve the highest editorial rank, then newest story.
        item_key = (
            item.get("editor_rank", 9999),
            -(parse_datetime(item.get("published_date")).timestamp() if parse_datetime(item.get("published_date")) else 0),
        )
        old_key = (
            old.get("editor_rank", 9999),
            -(parse_datetime(old.get("published_date")).timestamp() if parse_datetime(old.get("published_date")) else 0),
        )
        if item_key < old_key:
            winners[key] = item
    return sorted(winners.values(), key=lambda x: x.get("editor_rank", 9999))


def persist_event_cluster_state(ranked):
    clusters = STATE.setdefault("event_clusters", {})
    for item in ranked:
        event_id = item.get("event_cluster_id")
        if not event_id:
            continue
        clusters[event_id] = {
            "event_id": event_id,
            "topic": item.get("topic", ""),
            "region": item.get("region", ""),
            "sources": item.get("event_sources", []),
            "source_count": item.get("event_source_count", 0),
            "confidence": item.get("event_confidence", 0),
            "last_seen": now_iso(),
            "headline": item.get("title", ""),
        }


def remember_posted_event(story):
    event_id = story.get("event_cluster_id") or make_event_id(story)
    ids = STATE.setdefault("posted_event_ids", [])
    if event_id and event_id not in ids:
        ids.append(event_id)
    STATE["posted_event_ids"] = ids[-500:]
    return event_id


# ============================================================
# ARTICLE EXTRACTION
# ============================================================

def find_og_image(
    url,
    page_html=None,
    final_url=None,
):
    try:
        base_url = (
            final_url
            or url
        )

        if page_html is None:
            response = session.get(
                url,
                headers={
                    **HEADERS,
                    "Referer": url,
                },
                timeout=20,
            )

            if response.status_code >= 400:
                return ""

            page_html = response.text
            base_url = response.url

        soup = BeautifulSoup(
            page_html,
            "html.parser",
        )

        for attrs in (
            {"property": "og:image"},
            {"property": "og:image:url"},
            {"name": "twitter:image"},
        ):
            tag = soup.find(
                "meta",
                attrs=attrs,
            )

            if tag and tag.get(
                "content"
            ):
                return urljoin(
                    base_url,
                    safe_text(
                        tag["content"]
                    ),
                )

    except Exception:
        pass

    return ""


def extract_article(
    item,
):
    url = item["url"]

    try:
        response = session.get(
            url,
            headers={
                **HEADERS,
                "Referer": url,
            },
            timeout=25,
        )

        if response.status_code < 400:
            page_html = response.text

            text = trafilatura.extract(
                page_html,
                include_comments=False,
                include_tables=False,
                favor_precision=True,
            )

            image_url = (
                item.get("image")
                or find_og_image(
                    url,
                    page_html,
                    response.url,
                )
            )

            if text and len(safe_text(text)) >= 500:
                return (
                    safe_text(text),
                    image_url,
                )

    except Exception as exc:
        logger.warning(
            "Local extraction failed %s: %s",
            url,
            exc,
        )

    try:
        result_set = get_exa().get_contents(
            [url],
            text={
                "max_characters": 12000,
            },
        )

        if result_set.results:
            result = result_set.results[0]

            text = safe_text(
                getattr(
                    result,
                    "text",
                    "",
                )
            )

            image_url = (
                item.get("image")
                or safe_text(
                    getattr(
                        result,
                        "image",
                        "",
                    )
                )
            )

            if text:
                return (
                    text,
                    image_url,
                )

    except Exception as exc:
        logger.warning(
            "Exa article fallback failed %s: %s",
            url,
            exc,
        )

    return (
        "",
        item.get("image", ""),
    )


# ============================================================
# STORY + KNOWLEDGE GENERATION
# ============================================================

STORY_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "highlights": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 5,
        },
        "the_context": {"type": "string"},
        "bottom_line": {"type": "string"},
        "bold_terms": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 16,
        },
        "template_type": {
            "type": "string",
            "enum": [
                "general",
                "release",
                "breaking",
                "trailer",
                "renewal",
                "cancellation",
                "box_office",
                "spoiler",
            ],
        },
        "platform": {"type": "string"},
        "episodes": {"type": "string"},
        "languages": {"type": "string"},
        "status": {"type": "string"},
        "release_date": {"type": "string"},
        "action_url": {"type": "string"},
        "action_label": {"type": "string"},
        "note": {"type": "string"},
        "spoiler_text": {"type": "string"},
    },
    "required": [
        "headline",
        "summary",
        "highlights",
        "the_context",
        "bottom_line",
        "bold_terms",
        "template_type",
        "platform",
        "episodes",
        "languages",
        "status",
        "release_date",
        "action_url",
        "action_label",
        "note",
        "spoiler_text",
    ],
    "additionalProperties": False,
}


def first_sentence(text):
    text = clean_generated_text(
        text
    )

    # Conservative sentence extraction. Avoids common tech
    # abbreviations and decimals splitting incorrectly.
    protected = {
        "U.S.": "US_SENTINEL",
        "U.K.": "UK_SENTINEL",
        "E.U.": "EU_SENTINEL",
        "No.": "NO_SENTINEL",
        "Inc.": "INC_SENTINEL",
        "Ltd.": "LTD_SENTINEL",
        "Dr.": "DR_SENTINEL",
        "Mr.": "MR_SENTINEL",
        "Mrs.": "MRS_SENTINEL",
        "Ms.": "MS_SENTINEL",
    }

    working = text

    for old, marker in protected.items():
        working = working.replace(
            old,
            marker,
        )

    match = re.search(
        r"(.+?[.!?])(?:\s|$)",
        working,
    )

    if match:
        sentence = match.group(1)
    else:
        sentence = working

    for old, marker in protected.items():
        sentence = sentence.replace(
            marker,
            old,
        )

    return clean_generated_text(
        sentence
    )


def generate_story(
    item,
    article_text,
):
    topic_hint = item.get(
        "topic",
        "",
    )

    prompt = f"""
You are a senior entertainment editor for @EntertainmentNewsroom.

Create a compact Telegram movie/series news card from the source article.
Sector: {item.get("region", "Entertainment")}
Topic: {topic_hint}

Only describe the verified entertainment event in the source. Do not add celebrity gossip, lifestyle,
fan speculation, unsupported budget numbers, release dates, episode counts, platform availability,
or casting details that are not supported by the article.

PUBLIC CONTENT:
- Headline: 6-16 words, accurate and newspaper-style.
- Summary: exactly ONE complete sentence.
- Highlights: 3-5 short factual points, chosen dynamically.
- The Context: 2-4 complete sentences only when useful.
- Bottom Line: exactly ONE complete sentence.
- Choose template_type from: general, release, breaking, trailer, renewal, cancellation, box_office, spoiler.
- Use release for new streaming/theatrical availability.
- Use trailer for a trailer/teaser/first-look drop.
- Use renewal or cancellation only when that is the actual news.
- Use box_office for a material box-office result or milestone.
- Use breaking for major developing news where a release/trailer/renewal/cancellation template does not fit.
- Use spoiler only when the source contains a meaningful plot/ending/post-credit reveal.
- Optional metadata fields must be empty when unsupported. Never invent values.
- For action_url, use the source URL only if it is genuinely useful for the reader; otherwise return an empty string.
- action_label should be one of: Watch Now, Watch Trailer, Source, Read More, or empty.
- No repetition, no clickbait, no rumor presented as fact.
- No hashtags in generated fields.

The public post is aimed at readers who want major movie, OTT and scripted-series news, not general showbiz.
"""

    user = (
        f"REGION: {item['region']}\n"
        f"SOURCE: {item['source']}\n"
        f"TITLE: {item['title']}\n"
        f"DATE: {item['published_date']}\n\n"
        f"ARTICLE:\n{article_text[:12000]}"
    )

    for attempt in range(3):
        try:
            response = get_cerebras().chat.completions.create(
                model=CEREBRAS_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": prompt,
                    },
                    {
                        "role": "user",
                        "content": user,
                    },
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "entertainment_news_story_v1_0",
                        "strict": True,
                        "schema": STORY_SCHEMA,
                    },
                },
                reasoning_effort="low",
                temperature=0.2,
                max_completion_tokens=1400,
            )

            data = json.loads(
                safe_text(
                    response.choices[0]
                    .message
                    .content
                )
            )

            headline = clean_generated_text(
                data.get(
                    "headline"
                )
            )

            summary = first_sentence(
                data.get(
                    "summary"
                )
            )

            highlights = [
                clean_generated_text(x)
                for x in data.get("highlights", [])
                if clean_generated_text(x)
            ]
            if not (3 <= len(highlights) <= 5):
                raise ValueError("Highlights must contain 3-5 points")

            the_context = clean_generated_text(data.get("the_context"))
            bottom_line = clean_generated_text(data.get("bottom_line"))
            context_count = len(re.findall(r"(?<=[.!?])\s+", the_context)) + (1 if the_context and the_context[-1] in ".!?" else 0)
            bottom_count = len(re.findall(r"(?<=[.!?])\s+", bottom_line)) + (1 if bottom_line and bottom_line[-1] in ".!?" else 0)
            if not the_context or not bottom_line or not (2 <= context_count <= 4) or bottom_count != 1:
                raise ValueError("Invalid The Context or Bottom Line")

            if (
                not headline
                or not summary
                or not complete_text(headline)
                or not complete_text(summary)
                or any(not complete_text(x) for x in highlights)
                or not complete_text(the_context)
                or not complete_text(bottom_line)
            ):
                raise ValueError("Incomplete story")

            template_type = safe_text(data.get("template_type")).lower() or "general"
            allowed_templates = {
                "general", "release", "breaking", "trailer",
                "renewal", "cancellation", "box_office", "spoiler",
            }
            if template_type not in allowed_templates:
                raise ValueError(f"Unsupported template_type: {template_type}")

            story = {
                **item,
                "headline": trim_source_text(headline, 110),
                "summary": trim_source_text(summary, 260),
                "highlights": [trim_source_text(x, 130) for x in highlights],
                "the_context": trim_source_text(the_context, 520),
                "bottom_line": trim_source_text(bottom_line, 220),
                "bold_terms": [safe_text(x) for x in data.get("bold_terms", []) if safe_text(x)],
                "template_type": template_type,
                "platform": trim_source_text(data.get("platform", ""), 80),
                "episodes": trim_source_text(data.get("episodes", ""), 40),
                "languages": trim_source_text(data.get("languages", ""), 120),
                "status": trim_source_text(data.get("status", ""), 60),
                "release_date": trim_source_text(data.get("release_date", ""), 80),
                "action_url": safe_text(data.get("action_url", "")),
                "action_label": trim_source_text(data.get("action_label", ""), 30),
                "note": trim_source_text(data.get("note", ""), 240),
                "spoiler_text": trim_source_text(data.get("spoiler_text", ""), 500),
            }

            return story

        except Exception as exc:
            logger.warning(
                "Story generation attempt %d failed: %s",
                attempt + 1,
                exc,
            )

            if attempt == 0:
                time.sleep(1)

    return None


# ============================================================
# NUMERIC GROUNDING
# ============================================================

NUMBER_RE = re.compile(
    r"""
    (?:
        (?:US|U\.S\.|HK|HK\$|Tk|BDT|USD|EUR|GBP|JPY|CNY|INR|৳|\$|€|£|¥)
        \s*
    )?
    \d[\d,]*(?:\.\d+)?
    \s*
    (?:
        million|billion|trillion|
        crore|lakh|bn|mn|b|m|k|%
    )?
    """,
    re.I | re.X,
)

YEAR_RE = re.compile(r"^(?:19|20)\d{2}$")

_NUMERIC_SCALES = {
    "": 1.0,
    "k": 1e3,
    "m": 1e6,
    "mn": 1e6,
    "million": 1e6,
    "b": 1e9,
    "bn": 1e9,
    "billion": 1e9,
    "trillion": 1e12,
    "t": 1e12,
    "crore": 1e7,
    "lakh": 1e5,
}
_NUMERIC_CURRENCIES = {
    "$": "usd",
    "usd": "usd",
    "tk": "bdt",
    "bdt": "bdt",
    "৳": "bdt",
    "€": "eur",
    "eur": "eur",
    "£": "gbp",
    "gbp": "gbp",
    "¥": "jpy",
    "jpy": "jpy",
    "cny": "cny",
    "inr": "inr",
    "₹": "inr",
    "hk$": "hkd",
    "hk": "hkd",
}

def _numeric_signature(raw):
    text = safe_text(raw).strip().lower()
    if not text:
        return None

    currency = None
    for symbol in sorted(_NUMERIC_CURRENCIES, key=len, reverse=True):
        if text.startswith(symbol):
            currency = _NUMERIC_CURRENCIES[symbol]
            text = text[len(symbol):].strip()
            break

    if text.endswith("%"):
        unit = "%"
        text = text[:-1].strip()
    else:
        m = re.search(r"(trillion|billion|million|crore|lakh|bn|mn|[kmbt])$", text)
        unit = m.group(1) if m else ""
        if m:
            text = text[:m.start()].strip()

    text = text.replace(",", "")
    try:
        value = float(text)
    except ValueError:
        return None

    if unit == "%":
        scale = 1.0
        percent = True
    else:
        scale = _NUMERIC_SCALES.get(unit, 1.0)
        percent = False

    return {
        "value": value * scale,
        "percent": percent,
        "currency": currency,
    }

def normalize_number(raw):
    sig = _numeric_signature(raw)
    if not sig:
        return ""
    value = sig["value"]
    value_key = f"{value:.12g}"
    currency = sig["currency"] or ""
    percent = "%" if sig["percent"] else ""
    return f"{currency}|{percent}|{value_key}"

def numeric_tokens(text):
    tokens = []
    for match in NUMBER_RE.finditer(safe_text(text)):
        token = safe_text(match.group(0)).strip()
        sig = _numeric_signature(token)
        if not sig:
            continue

        # Ignore bare years, but retain years with a financial/percent/unit marker.
        numeric_value = sig["value"]
        if (
            numeric_value.is_integer()
            and YEAR_RE.match(str(int(numeric_value)))
            and not sig["percent"]
            and not sig["currency"]
        ):
            continue

        if token:
            tokens.append(token)
    return tokens

def _numeric_equivalent(source_sig, generated_sig):
    if not source_sig or not generated_sig:
        return False
    if source_sig["percent"] != generated_sig["percent"]:
        return False

    # If both explicitly name currencies, they must agree.
    # If only one names a currency, accept the numeric equivalent because
    # source extraction often drops currency symbols around abbreviated forms.
    if (
        source_sig["currency"]
        and generated_sig["currency"]
        and source_sig["currency"] != generated_sig["currency"]
    ):
        return False

    return abs(source_sig["value"] - generated_sig["value"]) <= max(
        1e-9, abs(source_sig["value"]) * 1e-9
    )

def numeric_grounded(story, article_text):
    source_sigs = [
        _numeric_signature(x)
        for x in numeric_tokens(article_text)
    ]
    source_sigs = [x for x in source_sigs if x]

    generated_text = " ".join(
        [
            story.get("headline", ""),
            story.get("summary", ""),
            *story.get("highlights", []),
        ]
    )

    for token in numeric_tokens(generated_text):
        generated_sig = _numeric_signature(token)
        if not generated_sig:
            continue

        if not any(
            _numeric_equivalent(source_sig, generated_sig)
            for source_sig in source_sigs
        ):
            return False, token

    return True, ""


# ============================================================
# BOLD TERMS
# ============================================================

def derive_bold_terms(
    story,
):
    terms = [
        safe_text(x)
        for x in story.get(
            "bold_terms",
            [],
        )
        if safe_text(x)
    ]

    combined = " ".join(
        [
            story.get(
                "summary",
                "",
            ),
            *story.get(
                "highlights",
                [],
            ),
        ]
    )

    # Financial figures, but do not bold bare years.
    for match in NUMBER_RE.finditer(
        combined
    ):
        token = safe_text(
            match.group(0)
        )

        numeric_only = re.sub(
            r"[^\d.]",
            "",
            token,
        )

        if (
            YEAR_RE.match(
                numeric_only
            )
            and not re.search(
                r"(Tk|BDT|USD|EUR|GBP|JPY|CNY|INR|৳|\$|€|£|¥|%|million|billion|crore|lakh)",
                token,
                re.I,
            )
        ):
            continue

        if token:
            terms.append(
                token
            )

    unique = []
    seen = set()

    for term in sorted(
        terms,
        key=len,
        reverse=True,
    ):
        key = term.lower()

        if (
            len(term) >= 2
            and key not in seen
        ):
            seen.add(key)
            unique.append(term)

    return unique[:16]


def escape_rich_html(
    text,
):
    return html.escape(
        clean_generated_text(text),
        quote=False,
    )


def bold_terms_html(
    text,
    terms,
):
    text = clean_generated_text(
        text
    )

    if not text:
        return ""

    result = text

    # Use letter-only markers to avoid collisions with numeric terms.
    replacements = []

    for index, term in enumerate(
        sorted(
            {
                safe_text(x)
                for x in terms
                if safe_text(x)
            },
            key=len,
            reverse=True,
        )
    ):
        marker = (
            f"__RICHBOLD_{chr(65 + (index % 26))}"
            f"{index // 26}__"
        )

        pattern = re.compile(
            re.escape(term),
            re.I,
        )

        match = pattern.search(
            result
        )

        if match:
            original = match.group(
                0
            )
            result = (
                result[:match.start()]
                + marker
                + result[match.end():]
            )
            replacements.append(
                (
                    marker,
                    original,
                )
            )

    escaped = html.escape(
        result,
        quote=False,
    )

    for marker, original in replacements:
        escaped = escaped.replace(
            marker,
            "<b>"
            + html.escape(
                original,
                quote=False,
            )
            + "</b>",
        )

    return escaped


# ============================================================
# DYNAMIC RICH MESSAGE HTML
# ============================================================

def dynamic_rich_html(story):
    """Render a dynamic Telegram Rich HTML card based on the news event type.

    The visual semantics mirror telegram_news_template.md:
    bold hook/title, italic metadata, code-style factual badges, expandable
    context/disclaimer blocks, clickable action/source links, and optional spoiler.
    """
    terms = derive_bold_terms(story)
    template = safe_text(story.get("template_type", "general")).lower()

    hook_map = {
        "general": "📌 UPDATE",
        "release": "🔥 NOW STREAMING",
        "breaking": "🚨 BREAKING",
        "trailer": "🎞️ TRAILER DROP",
        "renewal": "⚡ RENEWED",
        "cancellation": "❌ CANCELLED",
        "box_office": "💰 BOX OFFICE",
        "spoiler": "⭐ EXCLUSIVE",
    }
    hook = hook_map.get(template, "📌 UPDATE")

    region = safe_text(story.get("region", ""))
    topic = safe_text(story.get("topic", ""))
    platform = safe_text(story.get("platform", ""))
    episodes = safe_text(story.get("episodes", ""))
    languages = safe_text(story.get("languages", ""))
    status = safe_text(story.get("status", ""))
    release_date = safe_text(story.get("release_date", ""))
    note = safe_text(story.get("note", ""))
    action_url = safe_text(story.get("action_url", ""))
    action_label = safe_text(story.get("action_label", ""))
    spoiler_text = safe_text(story.get("spoiler_text", ""))

    meta_bits = []
    if region:
        meta_bits.append(region)
    if topic:
        meta_bits.append(topic)
    if meta_bits:
        metadata = " • ".join(meta_bits)
    else:
        metadata = ""

    parts = ['<img src="tg://photo?id=newsphoto">']
    parts.append("<p><b>" + escape_rich_html(hook) + "</b></p>")
    parts.append("<h1>🎬 " + escape_rich_html(story["headline"]) + "</h1>")

    if metadata:
        parts.append("<p><i>" + escape_rich_html(metadata) + "</i></p>")

    if story.get("summary"):
        parts.append("<p>" + bold_terms_html(story["summary"], terms) + "</p>")

    # Dynamic highlights. Never show an empty section.
    highlights = [safe_text(x) for x in story.get("highlights", []) if safe_text(x)]
    if highlights:
        label = {
            "trailer": "What The Trailer Reveals",
            "box_office": "Key Numbers",
            "renewal": "Renewal Details",
            "cancellation": "Cancellation Details",
        }.get(template, "What's New")
        parts.append("<h2>📌 " + escape_rich_html(label) + "</h2>")
        parts.append(
            "<p>" + "<br>".join(
                "• " + bold_terms_html(point, terms) for point in highlights
            ) + "</p>"
        )

    # Availability block for releases or whenever meaningful metadata exists.
    availability_lines = []
    if platform:
        availability_lines.append("• Platform: <code>" + escape_rich_html(platform) + "</code>")
    if episodes:
        availability_lines.append("• Episodes: <code>" + escape_rich_html(episodes) + "</code>")
    if languages:
        availability_lines.append("• Language: <code>" + escape_rich_html(languages) + "</code>")
    if status:
        availability_lines.append("• Status: <code>" + escape_rich_html(status) + "</code>")

    if availability_lines:
        parts.append("<h2>📺 Availability</h2>")
        parts.append("<p>" + "<br>".join(availability_lines) + "</p>")

    if release_date:
        parts.append(
            "<p>📅 <b>Release:</b> " + escape_rich_html(release_date) + "</p>"
        )

    # Box-office events can have a dedicated compact section from highlights,
    # while renewal/cancellation can show a note without manufacturing fields.
    if action_url and action_label:
        safe_url = html.escape(action_url, quote=True)
        parts.append(
            "<p>🔗 "
            f'<a href="{safe_url}">{escape_rich_html(action_label)}</a>'
            "</p>"
        )

    if spoiler_text:
        parts.append("<p>🙈 <b>Tap to reveal:</b></p>")
        parts.append("<p><tg-spoiler>" + escape_rich_html(spoiler_text) + "</tg-spoiler></p>")

    if note:
        parts.append("<blockquote><b>ℹ️ Note</b><br>" + escape_rich_html(note) + "</blockquote>")

    context = safe_text(story.get("the_context", ""))
    if context:
        parts.append(
            "<blockquote expandable><b>THE CONTEXT</b><br>"
            + bold_terms_html(context, terms)
            + "</blockquote>"
        )

    bottom = safe_text(story.get("bottom_line", ""))
    if bottom:
        parts.append(
            "<blockquote expandable><b>BOTTOM LINE</b><br>"
            + bold_terms_html(bottom, terms)
            + "</blockquote>"
        )

    hashtags = " ".join(category_hashtags(story))
    if hashtags:
        parts.append("<p>" + escape_rich_html(hashtags) + "</p>")

    source = escape_rich_html(story["source"])
    source_url = html.escape(story["url"], quote=True)
    parts.append(
        "<footer><b>Source:</b> "
        f'<a href="{source_url}">{source}</a>'
        "</footer>"
    )

    return "\n".join(parts)

def rich_visible_length(text):
    """Return Telegram-visible character count for Rich HTML text.

    Telegram limits the rendered text, not the raw HTML markup, so strip
    tags and decode HTML entities before counting characters.
    """
    no_tags = re.sub(r"<[^>]+>", "", text)
    no_attrs = re.sub(
        r"\[[^\]]+\]\([^)]+\)",
        lambda m: m.group(0).split("]")[0][1:],
        no_tags,
    )
    return len(html.unescape(no_attrs))


def fit_rich_html(story):
    variants = [
        (260, 130, 520, 220),
        (220, 115, 440, 190),
        (190, 100, 380, 170),
        (160, 85, 320, 150),
    ]

    for summary_len, highlight_len, context_len, bottom_len in variants:
        candidate = dict(story)
        candidate["summary"] = trim_source_text(story["summary"], summary_len)
        candidate["highlights"] = [trim_source_text(x, highlight_len) for x in story.get("highlights", [])]
        candidate["the_context"] = trim_source_text(story.get("the_context", ""), context_len)
        candidate["bottom_line"] = trim_source_text(story.get("bottom_line", ""), bottom_len)
        html_text = dynamic_rich_html(candidate)
        if rich_visible_length(html_text) <= MAX_RICH_CHARACTERS:
            return html_text

    return dynamic_rich_html(story)



# ============================================================
# IMAGE BRANDING: ONLY @EntertainmentNewsroom
# ============================================================

def find_font(
    bold=False,
):
    candidates = (
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
        if bold
        else [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]
    )

    for path in candidates:
        if os.path.exists(path):
            return path

    return None


def download_image(
    url,
    referer,
):
    if not url:
        return None

    try:
        response = session.get(
            url,
            headers={
                **HEADERS,
                "Referer": referer,
            },
            timeout=20,
            stream=True,
        )

        if response.status_code >= 400:
            return None

        content_type = (
            response.headers.get(
                "content-type",
                "",
            )
            .lower()
        )

        if (
            content_type
            and not content_type.startswith(
                "image/"
            )
        ):
            return None

        buf = BytesIO()

        for chunk in response.iter_content(
            65536
        ):
            if not chunk:
                continue

            buf.write(
                chunk
            )

            if buf.tell() > 8_000_000:
                return None

        buf.seek(0)

        image = Image.open(
            buf
        )
        image.load()

        if (
            image.width < 400
            or image.height < 250
        ):
            return None

        return image.convert(
            "RGB"
        )

    except Exception as exc:
        logger.warning(
            "Image download failed: %s",
            exc,
        )
        return None


def crop_cover(
    image,
    size=(1200, 675),
):
    target_w, target_h = size

    ratio = max(
        target_w / image.width,
        target_h / image.height,
    )

    resized = image.resize(
        (
            int(
                image.width
                * ratio
            ),
            int(
                image.height
                * ratio
            ),
        ),
        Image.Resampling.LANCZOS,
    )

    left = (
        resized.width
        - target_w
    ) // 2

    top = (
        resized.height
        - target_h
    ) // 2

    return resized.crop(
        (
            left,
            top,
            left + target_w,
            top + target_h,
        )
    )


def image_average_brightness(
    image,
):
    small = image.resize(
        (1, 1)
    ).convert(
        "L"
    )
    return small.getpixel(
        (0, 0)
    )


def display_source_name(source):
    """Return a reader-friendly publication label for the image chip."""
    raw = safe_text(source).strip()
    if not raw:
        return "Source"

    aliases = {
        "WIRED": "Wired",
        "ZDNET": "ZDNET",
        "9to5Google": "9to5Google",
        "MacRumors": "MacRumors",
        "WABetaInfo": "WABetaInfo",
        "TestingCatalog": "TestingCatalog",
        "AI News": "AI News",
        "Unite.AI": "Unite.AI",
        "The Decoder": "The Decoder",
        "SiliconANGLE": "SiliconANGLE",
        "Techmeme": "Techmeme",
        "MIT Technology Review": "MIT Technology Review",
    }
    if raw in aliases:
        return aliases[raw]
    return raw


def branded_card(
    photo,
    source,
    source_position="left",
):
    """Crop the image and add only the channel chip.

    The publication/source name is not rendered on the photo.
    """
    base = crop_cover(
        photo
    ).convert(
        "RGBA"
    )

    brightness = image_average_brightness(
        base
    )

    if brightness < 125:
        chip_bg = (245, 245, 245, 225)
        chip_fg = (20, 24, 28, 255)
    else:
        chip_bg = (18, 22, 28, 205)
        chip_fg = (245, 245, 245, 255)

    overlay = Image.new(
        "RGBA",
        base.size,
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(overlay)

    font_path = find_font(
        bold=True
    )
    if font_path:
        font = ImageFont.truetype(
            font_path,
            24,
        )
    else:
        font = ImageFont.load_default()

    channel_text = "@EntertainmentNewsroom"
    bbox = draw.textbbox(
        (0, 0),
        channel_text,
        font=font,
    )
    padding_x = 18
    padding_y = 9
    margin_x = 28
    margin_y = 24
    chip_w = (bbox[2] - bbox[0]) + padding_x * 2
    chip_h = (bbox[3] - bbox[1]) + padding_y * 2
    x2 = 1200 - margin_x
    y2 = 675 - margin_y
    x1 = x2 - chip_w
    y1 = y2 - chip_h

    draw.rounded_rectangle(
        (x1, y1, x2, y2),
        radius=16,
        fill=chip_bg,
    )
    draw.text(
        (x1 + padding_x, y1 + padding_y - 1),
        channel_text,
        font=font,
        fill=chip_fg,
    )

    return Image.alpha_composite(
        base,
        overlay,
    ).convert(
        "RGB"
    )


def prepare_image(
    story,
    index,
):
    image = download_image(
        story.get(
            "image_url",
            "",
        ),
        story["url"],
    )

    image_was_missing = image is None

    if image is None:
        image = Image.new(
            "RGB",
            (1200, 675),
            (28, 38, 50),
        )

        font_path = find_font(
            bold=True
        )

        if font_path:
            font = ImageFont.truetype(
                font_path,
                48,
            )
        else:
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(
            image
        )

        draw.text(
            (50, 50),
            "Entertainment News",
            font=font,
            fill="white",
        )

    branded = branded_card(
        image,
        story.get("source", "Source"),
        source_position="center" if image_was_missing else "left",
    )

    path = f"/tmp/news_{index}.jpg"

    branded.save(
        path,
        "JPEG",
        quality=88,
        optimize=True,
    )

    return path


# ============================================================
# TELEGRAM RICH MESSAGES
# ============================================================

def telegram_call(
    method,
    data=None,
    files=None,
):
    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/"
        f"{method}"
    )

    last = {
        "ok": False,
        "description": "Unknown error",
    }

    for attempt in range(
        1,
        6,
    ):
        try:
            response = session.post(
                url,
                data=data or {},
                files=files,
                timeout=90,
            )

            result = response.json()

            if result.get(
                "ok"
            ):
                return result

            last = result

            if response.status_code == 429:
                retry_after = int(
                    result.get(
                        "parameters",
                        {},
                    ).get(
                        "retry_after",
                        5,
                    )
                )

                logger.warning(
                    "Telegram 429; waiting %ss",
                    retry_after,
                )

                time.sleep(
                    max(
                        1,
                        retry_after,
                    )
                )
                continue

            if response.status_code >= 500:
                time.sleep(
                    2 * attempt
                )
                continue

            break

        except Exception as exc:
            last = {
                "ok": False,
                "description": str(exc),
            }

            time.sleep(
                2 * attempt
            )

    return last



def rich_html_to_legacy_html(rich_html):
    """Convert the internal rich template to Telegram Bot API HTML."""
    text = safe_text(rich_html)

    # Remove internal Rich-media placeholder. sendPhoto carries the actual image.
    text = re.sub(r"<img\b[^>]*?/?>", "", text, flags=re.I)

    # Convert structural tags to newline-separated Bot API HTML.
    text = re.sub(r"<h[1-6]>(.*?)</h[1-6]>", r"<b>\1</b>\n", text, flags=re.I | re.S)
    text = re.sub(r"<p>(.*?)</p>", r"\1\n", text, flags=re.I | re.S)
    text = re.sub(r"<footer>(.*?)</footer>", r"\1\n", text, flags=re.I | re.S)

    # Keep supported formatting tags and convert expandable blockquote to normal blockquote.
    text = re.sub(r"<blockquote(?:\s+expandable)?>(.*?)</blockquote>", r"<blockquote>\1</blockquote>", text, flags=re.I | re.S)

    # Internal Rich HTML uses <br>; Bot API HTML should use literal newlines.
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)

    # Remove any unsupported structural tags while retaining supported inline tags.
    text = re.sub(
        r"</?(?:details|summary|cite|aside|figure|figcaption)(?:\s[^>]*)?>",
        "",
        text,
        flags=re.I,
    )

    # Normalize excess blank lines.
    text = re.sub(r"\n{4,}", "\n\n", text)
    return text.strip()


def truncate_html_safe(html_text, max_visible=1024):
    """Truncate HTML by visible characters without cutting tags/entities."""
    source = safe_text(html_text)
    if not source:
        return ""

    out=[]
    stack=[]
    visible=0
    pos=0
    tag_re=re.compile(r"<[^>]+>")

    for match in tag_re.finditer(source):
        chunk=source[pos:match.start()]
        if chunk:
            remaining=max_visible-visible
            if len(chunk)>remaining:
                if remaining>0:
                    piece=chunk[:remaining].rsplit(" ",1)[0].rstrip() if " " in chunk[:remaining] else chunk[:remaining].rstrip()
                    out.append(piece)
                    visible += len(piece)
                break
            out.append(chunk)
            visible += len(chunk)

        tag=match.group(0)
        out.append(tag)

        m=re.match(r"<(a|b|strong|i|em|u|ins|s|strike|del|code|blockquote)(?:\s[^>]*)?>", tag, re.I)
        if m:
            stack.append(m.group(1))
        elif re.match(r"</(a|b|strong|i|em|u|ins|s|strike|del|code|blockquote)>", tag, re.I):
            if stack:
                stack.pop()

        pos=match.end()

    if pos < len(source) and visible < max_visible:
        chunk=source[pos:]
        remaining=max_visible-visible
        if len(chunk)<=remaining:
            out.append(chunk)
        elif remaining>0:
            piece=chunk[:remaining].rsplit(" ",1)[0].rstrip() if " " in chunk[:remaining] else chunk[:remaining].rstrip()
            out.append(piece)

    # Close any open tags in reverse order.
    for tag in reversed(stack):
        out.append(f"</{tag}>")

    result="".join(out).strip()
    if len(re.sub(r"<[^>]+>","",html.unescape(result))) > max_visible:
        # Conservative final fallback: strip markup and truncate. This is only
        # used for pathological generated HTML.
        plain=html.unescape(re.sub(r"<[^>]+>","",result))
        result=html.escape(plain[:max_visible-1],quote=False)+"…"
    return result


def send_bot_api_fallback(image_path, rich_html):
    """Publish with standard Telegram Bot API HTML if the primary photo call fails."""
    caption=truncate_html_safe(rich_html_to_legacy_html(rich_html),1024)
    url=f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(image_path,"rb") as photo:
            response=session.post(
                url,
                data={
                    "chat_id":TELEGRAM_CHANNEL,
                    "caption":caption,
                    "parse_mode":"HTML",
                },
                files={"photo":photo},
                timeout=90,
            )
        try:
            return response.json()
        except Exception:
            return {"ok":False,"description":response.text[:500]}
    except Exception as exc:
        return {"ok":False,"description":str(exc)}


def send_rich_photo(image_path, rich_html):
    """Use the standard Telegram Bot API sendPhoto method with HTML caption."""
    caption=truncate_html_safe(rich_html_to_legacy_html(rich_html),1024)
    url=f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(image_path,"rb") as photo:
            response=session.post(
                url,
                data={
                    "chat_id":TELEGRAM_CHANNEL,
                    "caption":caption,
                    "parse_mode":"HTML",
                },
                files={"photo":photo},
                timeout=90,
            )
        try:
            return response.json()
        except Exception:
            return {"ok":False,"description":response.text[:500]}
    except Exception as exc:
        return {"ok":False,"description":str(exc)}


# ============================================================
# KNOWLEDGE / EVENT RECORD
# ============================================================

def make_event_id(
    story,
):
    event_key = safe_text(
        story.get(
            "event_key"
        )
    )

    if event_key:
        return (
            re.sub(
                r"[^a-z0-9]+",
                "_",
                event_key.lower(),
            ).strip("_")
        )

    return canonical_url(
        story["url"]
    )


def store_event(
    story,
    published=False,
    message_id=None,
):
    event_id = make_event_id(
        story
    )

    event = {
        "event_id": event_id,
        "canonical_url": story[
            "canonical"
        ],
        "original_url": story[
            "url"
        ],
        "source": story[
            "source"
        ],
        "region": story[
            "region"
        ],
        "topic": story.get(
            "topic",
            "",
        ),
        "institution": story.get(
            "institution",
            "",
        ),
        "event_cluster_id": story.get(
            "event_cluster_id",
            event_id,
        ),
        "event_confidence": story.get(
            "event_confidence",
            0,
        ),
        "event_source_count": story.get(
            "event_source_count",
            0,
        ),
        "headline": story[
            "headline"
        ],
        "summary": story[
            "summary"
        ],
        "highlights": story[
            "highlights"
        ],
        "concepts": story.get(
            "concepts",
            [],
        ),
        "key_numbers": story.get(
            "key_numbers",
            [],
        ),
        "published_at": story[
            "published_date"
        ],
        "selected_at": now_iso(),
        "status": (
            "published"
            if published
            else "selected"
        ),
        "message_id": message_id,
    }

    STATE["events"][
        event_id
    ] = event

    return event_id


# ============================================================
# ============================================================



# ============================================================
# VERSION 1 FALLBACK POOLS
# ============================================================

def build_candidate_pool(ranked, needed):
    """Return a verification pool from already-ranked qualifying candidates.

    There is no mandatory post quota. Selection is primarily by score, with a
    light anti-saturation preference so one repeated franchise/platform does not
    crowd out equally strong independent events.
    """
    if not ranked:
        return []
    eligible = [dict(x) for x in ranked if x.get("importance_score", 0) >= PUBLISH_THRESHOLD and x.get("important") is True]
    eligible.sort(key=lambda x: (-x.get("importance_score", 0), x.get("editor_rank", 9999)))
    return eligible[:max(RANKING_POOL_SIZE, min(len(eligible), needed * 3 if needed else RANKING_POOL_SIZE))]


VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "supported": {"type": "boolean"},
        "unsupported_claims": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        },
    },
    "required": ["supported", "unsupported_claims"],
    "additionalProperties": False,
}


def claims_grounded(story, article_text):
    """Second-pass editorial verification for non-numeric factual claims."""
    claims = [
        story.get("headline", ""),
        story.get("summary", ""),
        *story.get("highlights", []),
    ]
    claims = [safe_text(x) for x in claims if safe_text(x)]

    prompt = """
You are a strict fact-checking editor. Compare the generated claims with the source article.
Mark supported=true only if every material factual claim in the headline, summary and highlights
is directly supported by the source article, either explicitly or by a faithful paraphrase.
Do not reject normal wording changes. Reject invented facts, unsupported causal claims, wrong dates,
wrong institutions, wrong people, wrong figures, exaggerated rankings, or claims stronger than the source.
Return only the JSON schema.
"""

    user = (
        "SOURCE ARTICLE:\n" + article_text[:12000]
        + "\n\nGENERATED CLAIMS:\n- " + "\n- ".join(claims)
    )

    try:
        response = get_cerebras().chat.completions.create(
            model=CEREBRAS_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "story_claim_verification",
                    "strict": True,
                    "schema": VERIFY_SCHEMA,
                },
            },
            reasoning_effort="low",
            temperature=0.0,
            max_completion_tokens=500,
        )
        data = json.loads(safe_text(response.choices[0].message.content))
        return bool(data.get("supported")), data.get("unsupported_claims", [])
    except Exception as exc:
        logger.warning("Claim verification failed: %s", exc)
        # Verification infrastructure failure must not silently become a hard drop.
        # Numeric grounding remains mandatory; this pass is advisory on verifier outage.
        return True, []


def process_story_candidate(item):
    """
    Extract, generate, ground and normalize one candidate.
    Returns a publishable story or None.
    """
    article_text, image_url = extract_article(item)

    if not article_text:
        logger.warning(
            "DROP extraction: %s",
            item.get("title"),
        )
        return None

    story = generate_story(
        item,
        article_text,
    )

    if not story:
        logger.warning(
            "DROP generation: %s",
            item.get("title"),
        )
        return None

    region = item.get(
        "region",
        "Entertainment",
    )

    story["topic"] = canonical_topic(
        story.get("topic") or item.get("topic"),
        region,
    )

    story["image_url"] = (
        image_url
        or item.get("image")
    )

    grounded, bad_number = numeric_grounded(
        story,
        article_text,
    )

    if not grounded:
        logger.warning(
            "Numeric grounding failed: %s (%s)",
            story.get("headline"),
            bad_number,
        )

        retry_story = generate_story(
            {
                **item,
                "grounding_warning": bad_number,
            },
            article_text,
        )

        if not retry_story:
            return None

        retry_story["topic"] = canonical_topic(
            retry_story.get("topic") or item.get("topic"),
            region,
        )
        retry_story["image_url"] = (
            image_url
            or item.get("image")
        )

        grounded_retry, _ = numeric_grounded(
            retry_story,
            article_text,
        )

        if not grounded_retry:
            logger.warning(
                "DROP numeric grounding: %s",
                story.get("headline"),
            )
            return None

        story = retry_story

    verified, unsupported_claims = claims_grounded(story, article_text)
    if not verified:
        logger.warning(
            "Claim verification failed: %s | claims=%s",
            story.get("headline"),
            unsupported_claims,
        )

        retry_story = generate_story(
            {**item, "grounding_warning": ", ".join(unsupported_claims[:3])},
            article_text,
        )
        if not retry_story:
            return None

        retry_story["topic"] = canonical_topic(
            retry_story.get("topic") or item.get("topic"),
            region,
        )
        retry_story["image_url"] = image_url or item.get("image")

        grounded_retry, _ = numeric_grounded(retry_story, article_text)
        if not grounded_retry:
            return None

        verified_retry, _ = claims_grounded(retry_story, article_text)
        if not verified_retry:
            logger.warning("DROP claim grounding: %s", story.get("headline"))
            return None
        story = retry_story

    story["topic"] = canonical_topic(
        story.get("topic") or item.get("topic"),
        region,
    )
    story["institution"] = item.get(
        "institution",
        "",
    )
    story["event_key"] = item.get(
        "event_key",
        "",
    )
    story["event_cluster_id"] = item.get(
        "event_cluster_id",
        "",
    )
    story["event_confidence"] = item.get(
        "event_confidence",
        0,
    )
    story["event_source_count"] = item.get(
        "event_source_count",
        0,
    )
    story["category_hashtags"] = category_hashtags(
        story
    )

    return story


# ============================================================
# MAIN
# ============================================================

def is_already_published_candidate(item):
    canonical = safe_text(item.get("canonical"))
    if canonical and canonical in POSTED_URLS:
        return True

    title = safe_text(item.get("title"))
    if not title:
        return False

    for event in STATE.get("events", {}).values():
        if event.get("status") != "published":
            continue
        if event.get("region") != item.get("region"):
            continue
        published_at = parse_datetime(event.get("published_at"))
        if not published_at or (NOW_BD - published_at).total_seconds() > EVENT_RETENTION_DAYS * 86400:
            continue
        previous_title = safe_text(event.get("headline"))
        if previous_title and title_similarity(title, previous_title) >= 0.90:
            return True
    return False


def available_candidates(region, source_pool=None):
    candidates = []
    seen = set()

    for item in STATE.get("queue", {}).values():
        if item.get("region") != region:
            continue
        if item.get("status") not in {"pending", "selected"}:
            continue

        published = parse_datetime(item.get("published_date"))
        if not published or not (DISCOVERY_START <= published <= DISCOVERY_END):
            continue

        url = safe_text(item.get("url"))
        canonical = safe_text(item.get("canonical"))
        if not canonical or canonical in seen:
            continue

        if source_pool == "primary" and not primary_domain_allowed(url, region):
            continue
        if source_pool == "fallback" and not fallback_domain_allowed(url, region):
            continue
        if source_pool is None and not allowed_source_for_region(url, region):
            continue

        if is_already_published_candidate(item):
            continue
        if title_duplicate_against_list(item.get("title", ""), candidates, threshold=0.94):
            continue

        candidates.append(dict(item))
        seen.add(canonical)

    candidates.sort(
        key=lambda x: parse_datetime(x.get("published_date"))
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return candidates[:MAX_RSS_CANDIDATES]


def prepare_ranked_region(region, candidates):
    ranked = rank_candidates(candidates, region)
    logger.info("%s RANKED RETURNED: %d", region, len(ranked))

    clustered = collapse_event_clusters(ranked)
    logger.info("%s AFTER EVENT DEDUP: %d", region, len(clustered))

    eligible = [
        item for item in clustered
        if item.get("importance_score", 0) >= PUBLISH_THRESHOLD
        and item.get("important") is True
    ]
    logger.info("%s IMPORTANCE PASS (score>=PUBLISH_THRESHOLD): %d", region, len(eligible))

    persist_event_cluster_state(eligible)
    return eligible


def process_ranked_region(region, ranked):
    pool = build_candidate_pool(ranked, MAX_STORIES_PER_RUN)
    valid = []
    attempted = 0
    rejected = 0

    for item in pool:
        if len(valid) >= MAX_STORIES_PER_RUN:
            break
        attempted += 1
        story = process_story_candidate(item)
        if not story:
            rejected += 1
            continue

        # Final duplicate check after generation.
        if is_already_published_candidate({**item, "title": story.get("headline", item.get("title"))}):
            logger.info("DROP already published event: %s", story.get("headline", ""))
            rejected += 1
            continue

        story["topic"] = canonical_topic(story.get("topic"), region)
        story["category_hashtags"] = category_hashtags(story)
        valid.append(story)
        logger.info(
            "ACCEPT %s #%d: rank=%s title=%s",
            region,
            len(valid),
            item.get("editor_rank", "?"),
            story.get("headline", ""),
        )

    logger.info(
        "%s FINAL VALID: %d/%d | pool=%d attempted=%d rejected=%d",
        region,
        len(valid),
        MAX_STORIES_PER_RUN,
        len(pool),
        attempted,
        rejected,
    )
    return valid


def select_balanced_candidates(ranked_by_sector):
    """Merge sector leaderboards without letting Hollywood crowd out the others.

    1) Keep the best qualifying candidate from each sector as a protected anchor.
    2) Fill remaining capacity globally by score with a soft sector-saturation penalty.
    3) Never publish below the 80 threshold and never invent a category quota.
    """
    anchors = []
    for sector in SECTOR_NAMES:
        rows = ranked_by_sector.get(sector, [])
        for row in rows:
            if row.get("importance_score", 0) >= PUBLISH_THRESHOLD:
                anchors.append(dict(row))
                break

    def adjusted_score(item, selected):
        sector = item.get("region")
        base = float(item.get("importance_score", 0))
        count = sum(1 for x in selected if x.get("region") == sector)
        # Soft saturation: 0 for first story, then small penalties only when
        # another sector has a similarly strong candidate available.
        return base - min(8, count * 3)

    selected = []
    seen_events = set()
    for item in sorted(anchors, key=lambda x: (-x.get("importance_score", 0), x.get("editor_rank", 9999))):
        key = item.get("event_key") or item.get("canonical")
        if key and key not in seen_events:
            selected.append(item)
            seen_events.add(key)

    pool = []
    for sector, rows in ranked_by_sector.items():
        pool.extend([dict(x) for x in rows if x.get("importance_score", 0) >= PUBLISH_THRESHOLD])

    while len(selected) < MAX_STORIES_PER_RUN and pool:
        pool = [x for x in pool if (x.get("event_key") or x.get("canonical")) not in seen_events]
        if not pool:
            break
        best = max(pool, key=lambda x: (adjusted_score(x, selected), x.get("importance_score", 0), -x.get("editor_rank", 9999)))
        selected.append(best)
        key = best.get("event_key") or best.get("canonical")
        if key:
            seen_events.add(key)
        pool.remove(best)

    # Final cross-sector event dedupe. The same story can be discovered in more
    # than one sector because some major sources/platforms overlap. Prefer the
    # highest-scoring instance so one event produces at most one post per run.
    deduped = []
    seen_event_signatures = []
    for item in sorted(selected, key=lambda x: (-x.get("importance_score", 0), x.get("editor_rank", 9999))):
        signature = normalize_title(item.get("title", ""))
        duplicate = False
        for previous in seen_event_signatures:
            if likely_same_event(signature, previous):
                duplicate = True
                break
        if duplicate:
            continue
        seen_event_signatures.append(signature)
        deduped.append(item)

    deduped.sort(key=lambda x: (-x.get("importance_score", 0), x.get("region", ""), x.get("editor_rank", 9999)))
    return deduped


def run():
    logger.info("ENTERTAINMENT NEWS BOT")
    logger.info("Channel=%s Mode=%s Threshold=%d Limit=%d", TELEGRAM_CHANNEL, NEWS_MODE, PUBLISH_THRESHOLD, MAX_STORIES_PER_RUN)
    logger.info("Lookback=%d hours | %s -> %s", DISCOVERY_LOOKBACK_HOURS, DISCOVERY_START.isoformat(), DISCOVERY_END.isoformat())

    prune_state()
    refresh_category_coverage()
    collect_rss()

    ranked_by_sector = {}
    for sector in SECTOR_NAMES:
        count = queue_candidates_for_region(sector)
        count += google_news_gap_fill(sector, count, max(8, DISCOVERY_TARGET_PER_REGION))
        exa_gap_fill(sector, count, max(12, DISCOVERY_TARGET_PER_REGION))
        save_state(STATE)

        candidates = available_candidates(sector, source_pool="primary")
        logger.info("DISCOVERY CANDIDATES: %s=%d", sector, len(candidates))
        ranked = prepare_ranked_region(sector, candidates)
        ranked_by_sector[sector] = ranked
        logger.info("QUALIFYING: %s=%d", sector, len(ranked))
        for item in ranked[:8]:
            logger.info("RANK %s #%s score=%s | %s", sector, item.get("editor_rank", "?"), item.get("importance_score", 0), item.get("title", ""))

    selected = select_balanced_candidates(ranked_by_sector)
    logger.info("FINAL SELECTED=%d | sectors=%s", len(selected), {s: sum(1 for x in selected if x.get("region") == s) for s in SECTOR_NAMES})

    published_count = 0
    for index, item in enumerate(selected, start=1):
        story = process_story_candidate(item)
        if not story:
            continue
        rich_html = fit_rich_html(story)
        if rich_visible_length(rich_html) > MAX_RICH_CHARACTERS:
            logger.error("Rich message exceeds Telegram limit: %s", story["headline"])
            continue

        image_path = prepare_image(story, index)
        result = send_rich_photo(image_path, rich_html)
        if not result.get("ok"):
            logger.warning("Rich publish failed; using Bot API fallback: %s", result.get("description"))
            result = send_bot_api_fallback(image_path, rich_html)

        if result.get("ok"):
            published_count += 1
            message = result.get("result", {})
            message_id = message.get("message_id") if isinstance(message, dict) else None
            canonical = story["canonical"]
            POSTED_URLS.add(canonical)
            save_posted_url(canonical)
            queue_item = STATE["queue"].get(canonical)
            if queue_item:
                queue_item["status"] = "posted"
                queue_item["posted_at"] = now_iso()
            store_event(story, published=True, message_id=message_id)
            remember_posted_event(story)
            update_category_coverage(story)
            STATE["recent_titles"].append(normalize_title(story["headline"]))
            logger.info("Published %d/%d: [%s] score=%s %s", published_count, len(selected), story.get("region"), item.get("importance_score"), story["headline"])
        else:
            logger.error("Telegram failed: %s", result.get("description"))
        save_state(STATE)
        time.sleep(POST_DELAY_SECONDS)

    save_state(STATE)
    logger.info("Finished. Published=%d Selected=%d", published_count, len(selected))


# ============================================================
# SELF TEST
# ============================================================

def self_test():
    sample = {
        "headline": "Netflix Announces Major New Korean Thriller Series",
        "summary": "Netflix announced a major Korean thriller series with an internationally recognized cast.",
        "highlights": [
            "Netflix confirmed the series as part of its upcoming scripted slate.",
            "The production features an established Korean cast.",
            "The series is planned for international streaming on Netflix.",
            "The announcement expands the platform's Korean scripted lineup.",
        ],
        "the_context": "The announcement comes as Netflix continues to invest in Korean scripted productions for global audiences.",
        "bottom_line": "The project combines a major Korean production with Netflix's global distribution.",
        "bold_terms": ["Netflix", "Korean", "series"],
        "source": "Netflix",
        "url": "https://www.netflix.com/",
        "region": "International",
        "topic": "Korean Drama",
        "institution": "Netflix",
        "template_type": "release",
        "platform": "Netflix",
        "episodes": "8",
        "languages": "Korean, English",
        "status": "Available Now",
        "release_date": "August 28, 2026",
        "action_url": "https://www.netflix.com/",
        "action_label": "Watch Now",
        "note": "International streaming availability is confirmed.",
        "spoiler_text": "",
    }
    rendered = dynamic_rich_html(sample)
    assert "<h1>🎬 " in rendered
    assert "🔥 NOW STREAMING" in rendered
    assert "<h2>📺 Availability</h2>" in rendered
    assert "<code>Netflix</code>" in rendered
    assert "<a href=" in rendered
    assert "<tg-spoiler>" not in rendered
    assert "<h1>🎬 Netflix Announces Major New Korean Thriller Series</h1>" in rendered
    assert "What's New" in rendered
    assert "THE CONTEXT" in rendered
    assert "BOTTOM LINE" in rendered
    assert '<img src="tg://photo?id=newsphoto">' in rendered
    assert rendered.count("• ") >= 4
    assert "#KDrama" in rendered and "#International" in rendered
    legacy = rich_html_to_legacy_html(rendered)
    assert "<h1>" not in legacy and "<h2>" not in legacy
    assert "<br" not in legacy.lower()
    assert "<b>🎬" in legacy
    assert "<code>Netflix</code>" in legacy
    assert len(html.unescape(re.sub(r"<[^>]+>", "", legacy))) <= 1024
    assert "@EntertainmentNewsroom" in legacy

    sample_trailer = dict(sample)
    sample_trailer["template_type"] = "trailer"
    sample_trailer["action_label"] = "Watch Trailer"
    trailer_html = dynamic_rich_html(sample_trailer)
    assert "🎞️ TRAILER DROP" in trailer_html
    assert "Watch Trailer" in trailer_html

    sample_spoiler = dict(sample)
    sample_spoiler["template_type"] = "spoiler"
    sample_spoiler["spoiler_text"] = "A major post-credit reveal occurs."
    spoiler_html = dynamic_rich_html(sample_spoiler)
    assert "⭐ EXCLUSIVE" in spoiler_html
    assert "<tg-spoiler>" in spoiler_html

    clustered = cluster_ranked_events([
        {"title":"Netflix announces major Korean thriller series","source":"Netflix","url":"https://netflix.com/a","published_date":now_iso(),"region":"International","event_key":"netflix_korean_thriller"},
        {"title":"Netflix announces major Korean thriller series","source":"Netflix","url":"https://netflix.com/b","published_date":now_iso(),"region":"International","event_key":"netflix_korean_thriller"},
    ])
    assert len(clustered) >= 1
    assert clustered[0]["event_cluster_size"] >= 1
    logger.info("EntertainmentNewsBot self-test passed.")

def visible_text_for_test(
    rendered,
):
    text = re.sub(
        r"<[^>]+>",
        "",
        rendered,
    )
    return html.unescape(
        text
    )




def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        run()

if __name__ == "__main__":
    main()
