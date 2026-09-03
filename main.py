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
from PIL import Image, ImageDraw, ImageFont, ImageFile, ImageFilter
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

TELEGRAM_CHANNEL = (os.environ.get("TELEGRAM_CHANNEL") or "@EntertainmentNewsroom").strip()
CHANNEL_TAG = TELEGRAM_CHANNEL if TELEGRAM_CHANNEL.startswith("@") else ""

# Optional. If set, feed-down alerts go here (a private chat/DM with the
# bot, not the public channel). If empty, alerts only go to the run log.
TELEGRAM_ADMIN_CHAT_ID = (os.environ.get("TELEGRAM_ADMIN_CHAT_ID") or "").strip()

NEWS_MODE = (os.environ.get("NEWS_MODE") or "update").strip().lower()

VALID_NEWS_MODES = {"update"}
if NEWS_MODE not in VALID_NEWS_MODES:
    raise ValueError(
        f"Invalid NEWS_MODE={NEWS_MODE!r}; expected one of {sorted(VALID_NEWS_MODES)}"
    )

CEREBRAS_MODEL = os.environ.get(
    "CEREBRAS_MODEL",
    "gpt-oss-120b",
)

POSTED_FILE = "posted_urls.txt"
STATE_FILE = "news_state.json"

BD_TZ = ZoneInfo("Asia/Dhaka")

# Editorial target: publish every verified candidate that clears the 80/100 gate.
# There is no fixed post quota and no sector quota.
PUBLISH_THRESHOLD = 80
RANKING_BATCH_SIZE = 15
MAX_RANK_CANDIDATES = 120
NEWS_PRIORITY = {
    "OTT / Streaming Availability": (1, 1),
    "Hindi Dub / Language Availability": (1, 2),
    "Upcoming OTT Releases": (1, 3),
    "Release Date Confirmations": (1, 4),
    "New Movie / Series Announcements": (2, 5),
    "Season Renewals / New Season Updates": (2, 6),
    "Trailer Releases": (2, 7),
    "First Look / First Glimpse / Posters": (2, 8),
    "Cast / Character Announcements": (3, 9),
    "Theatrical Releases / Re-releases": (3, 10),
    "Production / Filming Updates": (3, 11),
    "OTT Platform Acquisition / Streaming Rights": (3, 12),
    "Box Office Updates": (3, 13),
}
NEWS_TYPE_TO_PRIORITY = {
    "Now Streaming": "OTT / Streaming Availability",
    "Hindi Dub": "Hindi Dub / Language Availability",
    "Upcoming OTT": "Upcoming OTT Releases",
    "Release Date": "Release Date Confirmations",
    "Announcement": "New Movie / Series Announcements",
    "Renewal": "Season Renewals / New Season Updates",
    "Cancellation": "Season Renewals / New Season Updates",
    "Trailer": "Trailer Releases",
    "First Look": "First Look / First Glimpse / Posters",
    "Casting": "Cast / Character Announcements",
    "Theatrical": "Theatrical Releases / Re-releases",
    "Production": "Production / Filming Updates",
    "Distribution": "OTT Platform Acquisition / Streaming Rights",
    "Box Office": "Box Office Updates",
    "Industry": "New Movie / Series Announcements",
    "Confirmed": "New Movie / Series Announcements",
    "Reported": "New Movie / Series Announcements",
}
DISCOVERY_LOOKBACK_HOURS = 24

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
MAX_RICH_CHARACTERS = 32768
MAX_RICH_CHARACTERS = 32768
MAX_TELEGRAM_CAPTION_CHARACTERS = 1024

# Lightweight English stopwords used only by the conservative event/entity
# deduplication layer. This is deliberately small so legitimate game entities
# and meaningful terms are not filtered out.
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for",
    "from", "with", "by", "at", "as", "is", "are", "was", "were",
    "be", "been", "being", "has", "have", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can",
    "this", "that", "these", "those", "it", "its", "their", "they",
    "them", "he", "she", "his", "her", "we", "our", "you", "your",
    "new", "after", "before", "over", "into", "than", "about", "from",
}

# RSS-first sources. Google News and Exa remain gap-fill discovery.
RSS_FEEDS = [
    {"name":"Deadline","region":"Entertainment","url":"https://deadline.com/feed/"},
    {"name":"Variety","region":"Entertainment","url":"https://variety.com/feed/"},
    {"name":"The Hollywood Reporter","region":"Entertainment","url":"https://www.hollywoodreporter.com/feed/"},
    {"name":"TheWrap","region":"Entertainment","url":"https://www.thewrap.com/feed/"},
    {"name":"IndieWire","region":"Entertainment","url":"https://www.indiewire.com/feed/"},
    {"name":"Collider","region":"Entertainment","url":"https://collider.com/feed/"},
    {"name":"TVLine","region":"Entertainment","url":"https://tvline.com/feed/"},
    {"name":"OTTplay","region":"Entertainment","url":"https://www.ottplay.com/rss"},
    {"name":"Filmibeat","region":"Entertainment","url":"https://www.filmibeat.com/rss/feeds/filmibeat-news.xml"},
    {"name":"Pinkvilla","region":"Entertainment","url":"https://www.pinkvilla.com/rss"},
    {"name":"Bollywood Hungama","region":"Entertainment","url":"https://www.bollywoodhungama.com/feed/"},
    {"name":"Gadgets 360 Entertainment","region":"Entertainment","url":"https://www.gadgets360.com/entertainment/rss"},
    {"name":"Soompi","region":"Entertainment","url":"https://www.soompi.com/feed"},
    {"name":"What's on Netflix","region":"Entertainment","url":"https://www.whats-on-netflix.com/feed/"},
    {"name":"Netflix Tudum","region":"Entertainment","url":"https://www.netflix.com/tudum/rss.xml"},
    {"name":"Warner Bros. Discovery / HBO Max Pressroom","region":"Entertainment","url":"https://press.wbd.com/us/en/rss"},
    {"name":"Apple TV Press","region":"Entertainment","url":"https://www.apple.com/tv-pr/newsroom/feed/"},
    {"name":"Prime Video / Amazon News","region":"Entertainment","url":"https://www.aboutamazon.com/rss"},
    {"name":"Marvel","region":"Entertainment","url":"https://www.marvel.com/articles/feed"},
    {"name":"DC","region":"Entertainment","url":"https://www.dc.com/blog/rss.xml"},
    {"name":"Sony Pictures","region":"Entertainment","url":"https://www.sonypictures.com/rss"},
    {"name":"Paramount","region":"Entertainment","url":"https://www.paramount.com/rss"},
    {"name":"Universal Pictures","region":"Entertainment","url":"https://www.universalpictures.com/rss"},
]

# ============================================================
# TAXONOMY: ENTERTAINMENT NEWS
# ============================================================
SECTORS=["Hollywood","Indian","International"]
TOPICS={"Entertainment":["Major Film Announcements","Major Series Announcements","Casting","Trailers and First Looks","Production Starts","Production Wraps","Release Dates","Renewals and Cancellations","Streaming Premieres","Streaming Platform News","OTT Rights and Distribution","Franchises and IP","Studio Business","Platform Business","Acquisitions and Mergers","Cinema Industry","Production Deals","Major Awards and Recognition","Box Office","International Distribution"]}
INSTITUTIONS=["Netflix","Amazon","Prime Video","HBO","HBO Max","Warner Bros.","Warner Bros. Discovery","Disney","Disney+","Hulu","Apple TV+","Paramount","Paramount+","Universal Pictures","Sony Pictures","Marvel","DC","JioHotstar","SonyLIV","Viki","TVING","iQIYI","Tencent Video","Youku","Yash Raj Films","Dharma Productions","A24","Lionsgate","MGM"]
SOURCE_NAMES={"deadline.com":"Deadline","variety.com":"Variety","hollywoodreporter.com":"The Hollywood Reporter","thewrap.com":"TheWrap","indiewire.com":"IndieWire","collider.com":"Collider","tvline.com":"TVLine","ottplay.com":"OTTplay","filmibeat.com":"Filmibeat","pinkvilla.com":"Pinkvilla","bollywoodhungama.com":"Bollywood Hungama","gadgets360.com":"Gadgets 360","soompi.com":"Soompi","dramazoom.com":"DramaZOOM","mydramalist.com":"MyDramaList","asianwiki.com":"AsianWiki","whats-on-netflix.com":"What's on Netflix","netflix.com":"Netflix Tudum","press.wbd.com":"Warner Bros. Discovery / HBO Max Pressroom","apple.com":"Apple TV Press","aboutamazon.com":"Prime Video / Amazon News","aboutamazon.in":"Prime Video / Amazon News","marvel.com":"Marvel","dc.com":"DC","sonypictures.com":"Sony Pictures","paramount.com":"Paramount","universalpictures.com":"Universal Pictures"}
CATEGORY_HASHTAGS={"Major Film Announcements":["#Movies","#Film"],"Major Series Announcements":["#Series","#Streaming"],"Casting":["#Casting"],"Trailers and First Looks":["#Trailer"],"Production Starts":["#Production"],"Production Wraps":["#Production"],"Release Dates":["#ReleaseDate"],"Renewals and Cancellations":["#Streaming"],"Streaming Premieres":["#Streaming"],"Streaming Platform News":["#Streaming"],"OTT Rights and Distribution":["#OTT"],"Franchises and IP":["#Franchise"],"Studio Business":["#FilmIndustry"],"Platform Business":["#Streaming"],"Acquisitions and Mergers":["#MediaBusiness"],"Cinema Industry":["#Cinema"],"Production Deals":["#Production"],"Major Awards and Recognition":["#Awards"],"Box Office":["#BoxOffice"],"International Distribution":["#Distribution"]}
TOPIC_ALIASES={"casting":"Casting","cast":"Casting","trailer":"Trailers and First Looks","teaser":"Trailers and First Looks","release date":"Release Dates","release":"Release Dates","renewed":"Renewals and Cancellations","renewal":"Renewals and Cancellations","cancelled":"Renewals and Cancellations","canceled":"Renewals and Cancellations","streaming":"Streaming Platform News","ott":"Streaming Platform News","distribution":"OTT Rights and Distribution","rights":"OTT Rights and Distribution","franchise":"Franchises and IP","bollywood":"Indian Cinema","acquisition":"Acquisitions and Mergers","merger":"Acquisitions and Mergers","studio":"Studio Business","box office":"Box Office"}
def canonical_topic(topic,region="Entertainment"):
    key=safe_text(topic).lower().strip()
    if key in TOPIC_ALIASES:return TOPIC_ALIASES[key]
    for item in TOPICS["Entertainment"]:
        if key==item.lower():return item
    patterns=[(("cast","actor","actress","star"),"Casting"),(("trailer","teaser","first look","poster"),"Trailers and First Looks"),(("release date","premiere date","release"),"Release Dates"),(("renew","cancel","cancellation"),"Renewals and Cancellations"),(("streaming premiere","premieres","debut"),"Streaming Premieres"),(("netflix","prime video","hbo","disney+","apple tv","streaming platform"),"Streaming Platform News"),(("rights","distribution","international release"),"OTT Rights and Distribution"),(("franchise","sequel","spinoff","spin-off","adaptation"),"Franchises and IP"),(("bollywood","indian cinema","pan-indian","telugu","tamil","malayalam","hindi cinema"),"Indian Cinema"),(("acquisition","acquires","merger"),"Acquisitions and Mergers"),(("production starts","begins production","starts filming"),"Production Starts"),(("wraps production","production wrapped","wraps filming"),"Production Wraps"),(("box office","opening weekend","gross"),"Box Office"),(("studio","layoff","jobs","business"),"Studio Business")]
    for needles,canon in patterns:
        if any(n in key for n in needles):return canon
    return "Major Film Announcements"
def normalize_sector(value):
    raw=safe_text(value).strip().lower(); aliases={"indian cinema":"Indian","india":"Indian","bollywood":"Indian","international":"International","global":"International","hollywood":"Hollywood","us":"Hollywood","u.s.":"Hollywood"}
    if raw in aliases:return aliases[raw]
    if safe_text(value) in SECTORS:return safe_text(value)
    return "International"
def sector_hashtag(sector):
    return {"Hollywood":"#Hollywood","Indian":"#IndianCinema","International":"#International"}.get(normalize_sector(sector),"#International")
def category_hashtags(story):
    tags=[]
    for tag in CATEGORY_HASHTAGS.get(safe_text(story.get("topic")),[]):
        if tag not in tags:tags.append(tag)
    for tag in [sector_hashtag(story.get("sector")),"#Entertainment"]:
        if tag not in tags:tags.append(tag)
    return tags[:3]

def canonical_topic(topic,region="Entertainment"):
    key=safe_text(topic).lower().strip()
    if key in TOPIC_ALIASES:return TOPIC_ALIASES[key]
    for item in TOPICS["Entertainment"]:
        if key==item.lower():return item
    patterns=[(("cast","actor","actress","star"),"Casting"),(("trailer","teaser","first look","poster"),"Trailers and First Looks"),(("release date","premiere date","release"),"Release Dates"),(("renew","cancel","cancellation"),"Renewals and Cancellations"),(("streaming premiere","premieres","debut"),"Streaming Premieres"),(("netflix","prime video","hbo","disney+","apple tv","streaming platform"),"Streaming Platform News"),(("rights","distribution","international release"),"OTT Rights and Distribution"),(("franchise","sequel","spinoff","spin-off","adaptation"),"Franchises and IP"),(("bollywood","indian cinema","pan-indian"),"Indian Cinema"),(("k-drama","korean drama","korea"),"Korean Drama"),(("c-drama","chinese drama","china"),"Chinese Drama"),(("acquisition","acquires","merger"),"Acquisitions and Mergers"),(("production starts","begins production","starts filming"),"Production Starts"),(("wraps production","production wrapped","wraps filming"),"Production Wraps"),(("studio","layoff","jobs","business"),"Studio Business")]
    for needles,canon in patterns:
        if any(n in key for n in needles):return canon
    return "Major Film Announcements"
def category_hashtags(story):
    tags=[]
    for tag in CATEGORY_HASHTAGS.get(safe_text(story.get("topic")),[]):
        if tag not in tags:tags.append(tag)
    im={"Netflix":"#Netflix","Prime Video":"#PrimeVideo","Disney+":"#DisneyPlus","HBO Max":"#HBOMax","Marvel":"#Marvel","DC":"#DC","Sony Pictures":"#SonyPictures","Paramount+":"#ParamountPlus","Universal Pictures":"#UniversalPictures"}
    inst=safe_text(story.get("institution"))
    if inst in im and im[inst] not in tags:tags.append(im[inst])
    if "#Entertainment" not in tags:
        if len(tags) >= 3:
            tags = [tags[0], tags[-1], "#Entertainment"]
        else:
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


def json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, set):
        return sorted(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


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
            default=json_default,
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

exa = Exa(
    api_key=EXA_API_KEY
)

cerebras = Cerebras(
    api_key=CEREBRAS_API_KEY
)


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

# Hard scope guard: EntertainmentNewsroom is strictly film/series/OTT news.
# Sports competitions, sports leagues, combat-sports events, and athlete news
# are rejected before any LLM ranking so they cannot become publishable by mistake.
SPORTS_SCOPE_RE = re.compile(
    r"\b(football|soccer|basketball|baseball|cricket|tennis|golf|hockey|rugby|volleyball|"
    r"nfl|nba|nhl|mlb|fifa|uefa|atp|wta|formula\s*1|f1|nascar|motogp|"
    r"ufc|mma|wwe|aew|boxing|wrestling|fight\s+night|grand\s+slam|us\s+open|"
    r"tournament|championship|league|playoff|playoffs|fixture|standings|score|"
    r"athlete|player|coach|manager|draft|transfer|match|medal|olympics?|"
    r"super\s*bowl|world\s*cup)\b",
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

    if SPORTS_SCOPE_RE.search(title):
        return False

    if SPORTS_SCOPE_RE.search(safe_text(item.get("excerpt"))):
        # Require a clear entertainment title signal before allowing a candidate
        # whose excerpt mentions a sports term. This blocks sports leakage while
        # retaining legitimate film/series coverage that merely references a sport.
        entertainment_signal = re.search(
            r"\b(movie|film|series|season|episode|streaming|netflix|prime video|hbo|max|disney|apple tv|paramount|trailer|poster|cast|actor|actress|director|production|theatrical)\b",
            f"{title} {safe_text(item.get('excerpt'))}",
            re.I,
        )
        if not entertainment_signal:
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
            telegram_call("sendMessage", data={"chat_id": TELEGRAM_ADMIN_CHAT_ID, "text": message})
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
PRIMARY_ENTERTAINMENT_DOMAINS=["deadline.com","variety.com","hollywoodreporter.com","thewrap.com","indiewire.com","collider.com","tvline.com","ottplay.com","filmibeat.com","pinkvilla.com","bollywoodhungama.com","gadgets360.com","soompi.com","dramazoom.com","mydramalist.com","asianwiki.com","whats-on-netflix.com","netflix.com","press.wbd.com","apple.com","aboutamazon.com","aboutamazon.in","disneyplus.com","press.disneyplus.com","marvel.com","dc.com","sonypictures.com","paramount.com","universalpictures.com"]
FALLBACK_ENTERTAINMENT_DOMAINS=[]
ALL_PRIMARY_DOMAINS=PRIMARY_ENTERTAINMENT_DOMAINS
ALL_FALLBACK_DOMAINS=FALLBACK_ENTERTAINMENT_DOMAINS
ALL_ALLOWED_DOMAINS=ALL_PRIMARY_DOMAINS
def normalized_domain(url_or_source):
    raw=safe_text(url_or_source).lower()
    if "://" in raw:raw=urlparse(raw).netloc
    return raw.split(":")[0].removeprefix("www.").strip().rstrip("/")
def is_domain_allowed(url,domains):
    d=normalized_domain(url); return any(d==x or d.endswith("."+x) for x in domains)
def primary_domain_allowed(url,region=None):return is_domain_allowed(url,ALL_PRIMARY_DOMAINS)
def fallback_domain_allowed(url,region=None):return is_domain_allowed(url,ALL_FALLBACK_DOMAINS)
def allowed_source_for_region(url,region=None):return primary_domain_allowed(url,region) or fallback_domain_allowed(url,region)

# ============================================================
# GOOGLE NEWS RSS: FREE GAP FILL
# ============================================================

GOOGLE_NEWS_QUERIES={"Entertainment":["major Hollywood movie series news Netflix HBO Disney Prime Video","major Indian cinema Bollywood pan-Indian film streaming news","Korean drama film major streaming platform news","Chinese drama film major streaming platform news","major entertainment studio acquisition production release casting news","major OTT rights international distribution streaming deal news"]}
GOOGLE_NEWS_LOCALE={"Entertainment":("en-US","US","US:en")}

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

    queries = GOOGLE_NEWS_QUERIES.get("Entertainment", [])
    hl, gl, ceid = GOOGLE_NEWS_LOCALE.get("Entertainment", ("en-US", "US", "US:en"))

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

    domains = FALLBACK_ENTERTAINMENT_DOMAINS if fallback else PRIMARY_ENTERTAINMENT_DOMAINS
    if not domains:
        return 0
    queries=[
        "latest major Hollywood movie and series news",
        "latest major Netflix HBO Disney Prime Video entertainment news",
        "latest major Indian cinema Bollywood streaming news",
        "latest major Korean drama Chinese drama news",
        "latest major entertainment studio platform business distribution news",
        "latest major film casting trailer release franchise news",
    ]

    added = 0
    for query in queries:
        try:
            results = exa.search_and_contents(
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
                    "source": source_name(url), "region": "Entertainment",
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
# ARTICLE ENRICHMENT FOR THIN FEED EXCERPTS
# ============================================================

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


# ============================================================
# VERSION 1 EDITORIAL RANKING
# ============================================================

RANK_COMPONENTS = [
    "significance","reach","event_magnitude","platform_ip_strength",
    "source_authority","evidence_strength","international_relevance",
    "recency","audience_anticipation",
]
RANK_SCHEMA={
    "type":"object",
    "properties":{
        "ranked":{
            "type":"array",
            "items":{
                "type":"object",
                "properties":{
                    "id":{"type":"integer"},
                    "rank":{"type":"integer","minimum":1},
                    "sector":{"type":"string","enum":SECTORS},
                    "source_class":{"type":"string","enum":["official","reported","rumor"]},
                    **{k:{"type":"integer","minimum":0,"maximum":m} for k,m in {
                        "significance":20,"reach":15,"event_magnitude":15,"platform_ip_strength":10,
                        "source_authority":15,"evidence_strength":10,"international_relevance":5,
                        "recency":5,"audience_anticipation":5}.items()},
                    "topic":{"type":"string"},"institution":{"type":"string"},
                    "event_key":{"type":"string"},"reason":{"type":"string"},
                    "priority_type":{"type":"string","enum":list(NEWS_PRIORITY.keys())},
                },
                "required":["id","rank","sector","source_class",*RANK_COMPONENTS,"topic","institution","event_key","reason","priority_type"],
                "additionalProperties":False,
            },
        }
    },
    "required":["ranked"],
    "additionalProperties":False,
}

def rank_score(row):
    score=sum(int(row.get(k,0)) for k in RANK_COMPONENTS)
    if safe_text(row.get("source_class")).lower()=="rumor":
        score=min(score,69)
    return max(0,min(100,score))

def rank_candidates(candidates,region):
    if not candidates:return []
    regional=sorted(candidates,key=lambda x:parse_datetime(x.get("published_date")) or datetime.min.replace(tzinfo=timezone.utc),reverse=True)[:MAX_RANK_CANDIDATES]
    regional=enrich_thin_excerpts(regional)
    rows=[]
    priority_list="\n".join(f"{i}. {name}" for i,name in enumerate(NEWS_PRIORITY,1))
    for offset in range(0,len(regional),RANKING_BATCH_SIZE):
        batch=regional[offset:offset+RANKING_BATCH_SIZE]
        lines=[]
        for idx,item in enumerate(batch,1):
            dt=parse_datetime(item.get("published_date")); age=f"Age: {max(0.0,(NOW_BD-dt).total_seconds()/3600):.1f} hours" if dt else ""
            lines.append("\n".join([f"ID: {idx}",f"Title: {item.get('title','')}",f"Source: {item.get('source','')}",f"Published: {item.get('published_date','')}",age,f"Excerpt: {trim_source_text(item.get('excerpt',''),850)},",""]))
        prompt=f"""You are the senior editor of @EntertainmentNewsroom. Rank entertainment news candidates using the exact component scoring model below.
Sectors: Hollywood, Indian, International.
Priority list, from highest to lowest:
{priority_list}
Assign exactly one priority_type. Priority tiers are strong ordering preferences: Tier 1 ahead of Tier 2, Tier 2 ahead of Tier 3. This is not a quota. The final raw score remains the publication gate: only score >= 80 is publishable.
Score components must sum to exactly 100: significance 0-20; reach 0-15; event_magnitude 0-15; platform_ip_strength 0-10; source_authority 0-15; evidence_strength 0-10; international_relevance 0-5; recency 0-5; audience_anticipation 0-5.
Judge the underlying event, not headline excitement. Strongly deprioritize celebrity lifestyle, gossip, fashion, generic interviews, minor casting, routine catalog additions, weak promotions, unsupported rumors, opinion-only pieces, and duplicates.
Official confirmation is stronger than reputable reporting. Rumor/speculation is never publishable and must be scored below 80.
Do not invent information not present in the candidate metadata. Return EVERY candidate."""
        try:
            response=cerebras.chat.completions.create(model=CEREBRAS_MODEL,messages=[{"role":"system","content":prompt},{"role":"user","content":"\n".join(lines)}],response_format={"type":"json_schema","json_schema":{"name":"entertainment_news_v1_rank","strict":True,"schema":RANK_SCHEMA}},reasoning_effort="low",temperature=0.0,max_completion_tokens=4200)
            data=json.loads(safe_text(response.choices[0].message.content)); by_id={i:x for i,x in enumerate(batch,1)}; returned=set()
            for r in data.get("ranked",[]):
                idx=int(r.get("id",0))
                if idx not in by_id:continue
                item=dict(by_id[idx]); ptype=safe_text(r.get("priority_type"))
                if ptype not in NEWS_PRIORITY: ptype="New Movie / Series Announcements"
                score=rank_score(r)
                item.update({"importance_score":score,"important":score>=PUBLISH_THRESHOLD,"sector":normalize_sector(r.get("sector")),"source_class":safe_text(r.get("source_class")) or "reported","topic":canonical_topic(safe_text(r.get("topic")),region),"institution":safe_text(r.get("institution")),"event_key":safe_text(r.get("event_key")),"rank_reason":safe_text(r.get("reason")),"priority_type":ptype,"priority_tier":NEWS_PRIORITY[ptype][0],"priority_rank":NEWS_PRIORITY[ptype][1],"score_components":{k:int(r.get(k,0)) for k in RANK_COMPONENTS}})
                rows.append(item); returned.add(safe_text(item.get("canonical")))
            for idx,item in enumerate(batch,1):
                if safe_text(item.get("canonical")) not in returned:
                    fallback=dict(item); fallback.update({"importance_score":0,"important":False,"sector":"International","source_class":"reported","topic":canonical_topic(item.get("topic",""),region),"institution":"","event_key":"","rank_reason":"Unscored fallback; withheld from publication.","priority_type":"New Movie / Series Announcements","priority_tier":2,"priority_rank":5,"score_components":{k:0 for k in RANK_COMPONENTS}}); rows.append(fallback)
        except Exception as exc:
            logger.error("Editorial ranking batch failed for %s: %s",region,exc)
            for item in batch:
                row=dict(item); row.update({"importance_score":0,"important":False,"sector":"International","source_class":"reported","topic":canonical_topic(item.get("topic",""),region),"institution":"","event_key":"","rank_reason":"Ranking-service failure; candidate withheld.","priority_type":"New Movie / Series Announcements","priority_tier":2,"priority_rank":5,"score_components":{k:0 for k in RANK_COMPONENTS}}); rows.append(row)
    rows.sort(key=lambda x:(int(x.get("priority_tier",2)),int(x.get("priority_rank",5)),-int(x.get("importance_score",0)),-(parse_datetime(x.get("published_date")).timestamp() if parse_datetime(x.get("published_date")) else 0)))
    for global_rank,row in enumerate(rows,1):
        row["editor_rank"]=global_rank
        row["important"]=int(row.get("importance_score",0))>=PUBLISH_THRESHOLD
    return rows


def extract_entities(text):
    words = re.findall(r"[A-Za-z][A-Za-z&'-]{2,}", safe_text(text).lower())
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
            same_key = bool(
                safe_text(item.get("event_key"))
                and safe_text(item.get("event_key")) == safe_text(representative.get("event_key"))
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
            image_candidates = _extract_image_candidates_from_html(page_html, response.url, item.get("title", ""))
            item["image_candidates"] = image_candidates[:20]

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
        result_set = exa.get_contents(
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

STORY_SCHEMA={"type":"object","properties":{"headline":{"type":"string"},"year":{"type":"string"},"summary":{"type":"string"},"sector":{"type":"string","enum":SECTORS},"format":{"type":"string","enum":["Film","Series","Streaming","Industry"]},"news_type":{"type":"string","enum":["Confirmed","Reported","Now Streaming","Hindi Dub","Upcoming OTT","Release Date","Trailer","First Look","Renewal","Cancellation","Box Office","Theatrical","Industry","Casting","Production","Distribution","Announcement"]},"priority_type":{"type":"string","enum":list(NEWS_PRIORITY.keys())},"highlights":{"type":"array","items":{"type":"string"},"minItems":2,"maxItems":3},"platform":{"type":"string"},"episodes":{"type":"string"},"languages":{"type":"string"},"status":{"type":"string"},"release_date":{"type":"string"},"expected_date":{"type":"string"},"season":{"type":"string"},"amount":{"type":"string"},"domestic_amount":{"type":"string"},"worldwide_amount":{"type":"string"},"days_since_release":{"type":"string"},"reported_details":{"type":"array","items":{"type":"string"},"maxItems":4},"framing_line":{"type":"string"},"spoiler":{"type":"string"},"note":{"type":"string"},"bold_terms":{"type":"array","items":{"type":"string"},"maxItems":18}},"required":["headline","year","summary","sector","format","news_type","priority_type","highlights","platform","episodes","languages","status","release_date","expected_date","season","amount","domestic_amount","worldwide_amount","days_since_release","reported_details","framing_line","spoiler","note","bold_terms"],"additionalProperties":False}


def first_sentence(text):
    text = clean_generated_text(
        text
    )

    # Conservative sentence extraction. Avoids common entertainment
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


def generate_story(item,article_text):
    sector=normalize_sector(item.get("sector"))
    prompt=f"""You are the senior newspaper entertainment editor for @EntertainmentNewsroom. Create a factual Telegram news card. Sector: {sector}. Editorial score: {item.get('importance_score',0)}/100.
Rules: headline 6-14 words; year should be the relevant release/production year when clearly supported, otherwise empty; summary 1-2 short sentences; sector exactly Hollywood/Indian/International; format Film/Series/Streaming/Industry; choose a precise news_type and priority_type from the fixed 13-item list; 2-3 factual highlights; keep the copy compact enough to understand in under 10 seconds. Populate only the template fields supported by the source; leave irrelevant dynamic fields empty. Use the exact Telegram template variant matching news_type. Spoiler is empty unless a real plot/finale/twist reveal is central. No unsupported facts, numbers, dates, cast, platforms or status claims. No hashtags, Markdown or HTML inside JSON.
Return only valid JSON matching the schema."""
    user=f"REGION: Entertainment\nSECTOR: {sector}\nSOURCE: {item['source']}\nSOURCE CLASS: {item.get('source_class','reported')}\nTITLE: {item['title']}\nDATE: {item['published_date']}\n\nARTICLE:\n{article_text[:14000]}"
    for attempt in range(3):
        try:
            response=cerebras.chat.completions.create(model=CEREBRAS_MODEL,messages=[{"role":"system","content":prompt},{"role":"user","content":user}],response_format={"type":"json_schema","json_schema":{"name":"entertainment_news_story_v11","strict":True,"schema":STORY_SCHEMA}},reasoning_effort="low",temperature=0.15,max_completion_tokens=1700)
            data=json.loads(safe_text(response.choices[0].message.content)); headline=clean_generated_text(data.get("headline")); year=clean_generated_text(data.get("year")); summary=first_sentence(data.get("summary")); highlights=[clean_generated_text(x) for x in data.get("highlights",[]) if clean_generated_text(x)]; spoiler=clean_generated_text(data.get("spoiler")); note=clean_generated_text(data.get("note")); fmt=safe_text(data.get("format")); news_type=safe_text(data.get("news_type")); out_sector=normalize_sector(data.get("sector"));
            allowed_types={"Confirmed","Reported","Now Streaming","Hindi Dub","Upcoming OTT","Release Date","Trailer","First Look","Renewal","Cancellation","Box Office","Theatrical","Industry","Casting","Production","Distribution","Announcement"}
            if not headline or not summary or not complete_text(headline) or not complete_text(summary) or fmt not in {"Film","Series","Streaming","Industry"} or news_type not in allowed_types or not (2<=len(highlights)<=3) or any(not complete_text(x) for x in highlights) or (spoiler and not complete_text(spoiler)): raise ValueError("Invalid story structure")
            dynamic_fields={k:trim_source_text(clean_generated_text(data.get(k)),700) for k in ["platform","episodes","languages","status","release_date","expected_date","season","amount","domestic_amount","worldwide_amount","days_since_release","framing_line","note"]}
            dynamic_fields["reported_details"]=[trim_source_text(clean_generated_text(x),180) for x in data.get("reported_details",[]) if clean_generated_text(x)][:4]
            priority_type = safe_text(data.get("priority_type")) or NEWS_TYPE_TO_PRIORITY.get(news_type, "New Movie / Series Announcements")
            if priority_type not in NEWS_PRIORITY:
                priority_type = NEWS_TYPE_TO_PRIORITY.get(news_type, "New Movie / Series Announcements")
            return {**item,"headline":trim_source_text(headline,120),"year":trim_source_text(year,10),"summary":trim_source_text(summary,300),"sector":out_sector,"format":fmt,"news_type":news_type,"priority_type":priority_type,"highlights":[trim_source_text(x,150) for x in highlights],**dynamic_fields,"spoiler":trim_source_text(spoiler,700),"bold_terms":[safe_text(x) for x in data.get("bold_terms",[]) if safe_text(x)]}
        except Exception as exc:
            logger.warning("Story generation attempt %d failed: %s",attempt+1,exc)
            if attempt<2:time.sleep(1)
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

YEAR_RE = re.compile(
    r"^(?:19|20)\d{2}$"
)


def normalize_number(
    raw,
):
    text = (
        safe_text(raw)
        .lower()
        .replace(",", "")
        .replace("৳", "tk")
        .replace("$", "usd")
    )

    return re.sub(
        r"\s+",
        "",
        text,
    )


def numeric_tokens(text):
    tokens = []

    for match in NUMBER_RE.finditer(
        safe_text(text)
    ):
        token = safe_text(
            match.group(0)
        )

        stripped = re.sub(
            r"[^\d.]",
            "",
            token,
        )

        if (
            YEAR_RE.match(
                stripped
            )
            and not any(
                x in token.lower()
                for x in (
                    "tk",
                    "usd",
                    "bdt",
                    "$",
                    "€",
                    "£",
                    "¥",
                    "%",
                    "million",
                    "billion",
                    "crore",
                    "lakh",
                )
            )
        ):
            continue

        if token:
            tokens.append(
                token
            )

    return tokens


def numeric_grounded(
    story,
    article_text,
):
    source_numbers = [
        normalize_number(x)
        for x in numeric_tokens(
            article_text
        )
    ]

    generated_text = " ".join(
        [
            story.get(
                "headline",
                "",
            ),
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

    for token in numeric_tokens(
        generated_text
    ):
        normalized = normalize_number(
            token
        )

        if not normalized:
            continue

        # Require either exact normalized occurrence or a sufficiently
        # close numeric token from source.
        if normalized not in source_numbers:
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
# TELEGRAM RICH MESSAGE HTML
# ============================================================

def rich_visible_length(text):
    """Count user-visible characters in Rich HTML, excluding markup."""
    no_tags = re.sub(r"<[^>]+>", "", safe_text(text))
    return len(html.unescape(no_tags))


def add_media_reference():
    return '<img src="tg://photo?id=newsphoto">'


def _story_priority_label(story):
    direct = safe_text(story.get("priority_type"))
    if direct in NEWS_PRIORITY:
        return direct
    return NEWS_TYPE_TO_PRIORITY.get(safe_text(story.get("news_type")), "New Movie / Series Announcements")


def _hook_for_story(story):
    news_type = safe_text(story.get("news_type"))
    status = safe_text(story.get("status")).lower()
    if news_type == "Now Streaming" or status in {"streaming", "available now", "now streaming"}:
        return "🔥 NOW STREAMING"
    if news_type == "Hindi Dub":
        return "🇮🇳 HINDI DUB NOW AVAILABLE"
    if news_type == "Upcoming OTT":
        return "📺 OTT RELEASE ANNOUNCED"
    if news_type == "Release Date":
        return "📅 RELEASE DATE CONFIRMED"
    if news_type == "Trailer":
        return "🎞️ TRAILER RELEASED"
    if news_type == "First Look":
        return "👀 FIRST LOOK"
    if news_type == "Renewal":
        return "🔄 SEASON RENEWED"
    if news_type == "Cancellation":
        return "❌ CANCELLED"
    if news_type == "Casting":
        return "🎭 CAST ANNOUNCEMENT"
    if news_type == "Theatrical":
        return "🎬 THEATRICAL UPDATE"
    if news_type == "Production":
        return "🎥 PRODUCTION UPDATE"
    if news_type == "Distribution":
        return "🌍 STREAMING RIGHTS UPDATE"
    if news_type == "Box Office":
        return "💰 BOX OFFICE UPDATE"
    if news_type == "Reported":
        return "📰 REPORTED"
    return "📢 CONFIRMED"


def _display_release_date(story):
    return safe_text(story.get("release_date")) or safe_text(story.get("expected_date"))


def _availability_lines(story):
    lines = []
    platform = safe_text(story.get("platform"))
    episodes = safe_text(story.get("episodes"))
    languages = safe_text(story.get("languages"))
    status = safe_text(story.get("status"))
    release_date = _display_release_date(story)

    if platform:
        lines.append(f"✦ <b>Platform:</b> {escape_rich_html(platform)}")
    if episodes:
        lines.append(f"✦ <b>Episodes:</b> {escape_rich_html(episodes)}")
    if languages:
        lines.append(f"✦ <b>Language:</b> {escape_rich_html(languages)}")
    if status:
        lines.append(f"✦ <b>Status:</b> {escape_rich_html(status)}")
    if platform and release_date:
        lines.append(f"✦ <b>Release:</b> {escape_rich_html(release_date)}")
    return lines


def dynamic_rich_html(story):
    """Render the final V1 reader-first Entertainment structure.

    Section labels such as Availability and What's New are intentionally omitted.
    Python owns the visible layout; the LLM supplies only structured content.
    """
    terms = derive_bold_terms(story)
    title = escape_rich_html(story.get("headline", ""))
    year = safe_text(story.get("year"))
    summary = bold_terms_html(story.get("summary", ""), terms)
    lines = [
        add_media_reference(),
        f"<p><b>{escape_rich_html(_hook_for_story(story))}</b></p>",
        f"<h1><b>🎬 {title}" + (f" ({escape_rich_html(year)})" if year else "") + "</b></h1>",
    ]

    availability = _availability_lines(story)
    if availability:
        lines.extend(f"<p>{line}</p>" for line in availability)

    if summary:
        lines.append(f"<p>📖 {summary}</p>")

    highlights = [bold_terms_html(x, terms) for x in story.get("highlights", []) if safe_text(x)][:3]
    lines.extend(f"<p>✦ {x}</p>" for x in highlights)

    release_date = _display_release_date(story)
    if release_date and not safe_text(story.get("platform")):
        lines.append(f"<p>✦ <b>Release:</b> {escape_rich_html(release_date)}</p>")

    spoiler = safe_text(story.get("spoiler"))
    if spoiler:
        lines.append(f"<p>🙈 <b>Spoiler:</b> <tg-spoiler>{bold_terms_html(spoiler, terms)}</tg-spoiler></p>")

    note = safe_text(story.get("note"))
    if note:
        lines.append(
            "<details><summary>ℹ️ More</summary>"
            f"<p>{bold_terms_html(note, terms)}</p></details>"
        )

    hashtags = " ".join(category_hashtags(story))
    if hashtags:
        lines.append(f"<p>{escape_rich_html(hashtags)}</p>")

    source = escape_rich_html(story.get("source", "Source"))
    url = html.escape(safe_text(story.get("url", "")), quote=True)
    if url:
        lines.append(f"<footer><b>Source:</b> <a href=\"{url}\">{source}</a></footer>")
    else:
        lines.append(f"<footer><b>Source:</b> {source}</footer>")
    return "\n".join(lines)


def fit_rich_html(story):
    """Trim non-critical fields until the Rich Message fits Telegram's limit."""
    variants = [
        dict(story),
        dict(story, summary=trim_source_text(story.get("summary", ""), 240)),
        dict(story, summary=trim_source_text(story.get("summary", ""), 190), highlights=[trim_source_text(x, 120) for x in story.get("highlights", [])[:4]], note=trim_source_text(story.get("note", ""), 220)),
        dict(story, summary=trim_source_text(story.get("summary", ""), 170), highlights=[trim_source_text(x, 105) for x in story.get("highlights", [])[:3]], note=trim_source_text(story.get("note", ""), 160)),
    ]
    for candidate in variants:
        rendered = dynamic_rich_html(candidate)
        if rich_visible_length(rendered) <= MAX_RICH_CHARACTERS:
            return rendered
    raise ValueError("Unable to fit Rich Message within Telegram limits")

# ============================================================
# IMAGE HANDLING: NORMAL PHOTOS BRANDED; POSTERS/FALLBACKS UNBRANDED
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


def crop_cover(image, size=(1200, 675)):
    target_w, target_h = size
    ratio = max(target_w / image.width, target_h / image.height)
    resized = image.resize((int(image.width * ratio), int(image.height * ratio)), Image.Resampling.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _vertical_sharpness_profile(image):
    """Return a simple per-column edge-energy profile for padded-poster detection."""
    gray = image.convert("L").resize((min(900, image.width), min(900, image.height)))
    w, h = gray.size
    px = gray.load()
    profile = [0.0] * w
    for x in range(1, w - 1):
        total = 0.0
        for y in range(1, h - 1):
            total += abs(px[x + 1, y] - px[x - 1, y])
        profile[x] = total / max(1, h - 2)
    return profile


def _looks_like_padded_portrait_poster(image):
    """Detect a wide 16:9-style image that embeds a centered portrait poster with soft side panels."""
    w, h = image.size
    ratio = w / max(1, h)
    if ratio < 1.55 or ratio > 1.95:
        return False

    target_w = int(h * (2 / 3))
    if target_w < 240 or target_w >= w * 0.70:
        return False

    left = (w - target_w) // 2
    right = left + target_w
    small = image.convert("L").resize((360, 202))
    sw, sh = small.size
    # Map the expected central poster window into the reduced image.
    scale = sw / w
    l = max(1, int(left * scale))
    r = min(sw - 1, int(right * scale))
    if r - l < 110:
        return False

    px = small.load()
    center_edge = 0.0
    side_edge = 0.0
    center_count = 0
    side_count = 0
    for x in range(1, sw - 1):
        for y in range(1, sh - 1):
            edge = abs(px[x + 1, y] - px[x - 1, y]) + abs(px[x, y + 1] - px[x, y - 1])
            if l <= x < r:
                center_edge += edge
                center_count += 1
            else:
                side_edge += edge
                side_count += 1
    center_edge /= max(1, center_count)
    side_edge /= max(1, side_count)

    # Also require both side panels to resemble each other, which is typical of
    # blur-fill composites generated from the same poster.
    left_box = small.crop((0, 0, l, sh)).resize((40, 22))
    right_box = small.crop((r, 0, sw, sh)).resize((40, 22))
    a = list(left_box.get_flattened_data())
    b = list(right_box.get_flattened_data())
    side_similarity = sum(abs(x - y) for x, y in zip(a, b)) / max(1, len(a))

    return center_edge > 1.8 * max(side_edge, 0.1) and side_similarity < 42


def extract_portrait_poster(image):
    """Return the full portrait poster, removing only artificial side padding."""
    image = image.convert("RGB")
    if image.height > image.width * 1.12:
        return image

    if not _looks_like_padded_portrait_poster(image):
        return None

    target_ratio = 2 / 3
    crop_w = min(image.width, int(image.height * target_ratio))
    left = (image.width - crop_w) // 2
    return image.crop((left, 0, left + crop_w, image.height))


def fit_full_poster(image, max_side=2048):
    """Keep the entire poster at its natural portrait ratio without padding or branding."""
    image = image.convert("RGB")
    extracted = extract_portrait_poster(image)
    if extracted is not None:
        image = extracted
    longest = max(image.width, image.height)
    if longest <= max_side:
        return image
    ratio = max_side / longest
    return image.resize(
        (max(1, int(image.width * ratio)), max(1, int(image.height * ratio))),
        Image.Resampling.LANCZOS,
    )


def image_average_brightness(image):
    return image.resize((1, 1)).convert("L").getpixel((0, 0))


def branded_card(photo):
    """Normal editorial-image branding. Poster/fallback images bypass this."""
    base = crop_cover(photo).convert("RGBA")
    brightness = image_average_brightness(base)
    bg = (245, 245, 245, 225) if brightness < 125 else (18, 22, 28, 205)
    fg = (20, 24, 28, 255) if brightness < 125 else (245, 245, 245, 255)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font_path = find_font(bold=True)
    font = ImageFont.truetype(font_path, 24) if font_path else ImageFont.load_default()
    text = "@EntertainmentNewsroom"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    padding_x, padding_y = 22, 10
    chip_w, chip_h = text_w + padding_x * 2, text_h + padding_y * 2
    x2, y2 = 1200 - 28, 675 - 24
    x1, y1 = x2 - chip_w, y2 - chip_h
    draw.rounded_rectangle((x1, y1, x2, y2), radius=18, fill=bg)
    draw.text((x1 + padding_x, y1 + padding_y - 1), text, font=font, fill=fg)
    return Image.alpha_composite(base, overlay).convert("RGB")


def _is_poster_priority(story):
    priority = _story_priority_label(story)
    return priority in {
        "OTT / Streaming Availability",
        "Upcoming OTT Releases",
        "Hindi Dub / Language Availability",
    }


def _extract_image_candidates_from_html(page_html, base_url, title):
    candidates = []
    try:
        soup = BeautifulSoup(page_html, "html.parser")
        for tag in soup.find_all("meta"):
            prop = safe_text(tag.get("property") or tag.get("name")).lower()
            content = safe_text(tag.get("content"))
            if content and prop in {"og:image", "og:image:url", "twitter:image"}:
                candidates.append(urljoin(base_url, content))
        needle = normalize_title(title)
        for img in soup.find_all("img")[:60]:
            src = safe_text(img.get("src") or img.get("data-src") or img.get("data-lazy-src"))
            if not src:
                srcset = safe_text(img.get("srcset") or img.get("data-srcset"))
                if srcset:
                    src = safe_text(srcset.split(",")[0].strip().split(" ")[0])
            if not src:
                continue
            alt = normalize_title(img.get("alt", ""))
            full = urljoin(base_url, src)
            score = 0
            if "poster" in alt or "key art" in alt or (needle and needle in alt):
                score += 5
            if any(token in safe_text(src).lower() for token in ("poster", "key-art", "keyart")):
                score += 4
            candidates.append((score, full))
        scored = []
        for x in candidates:
            if isinstance(x, tuple): scored.append(x)
            else: scored.append((0, x))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [u for _, u in scored if u]
    except Exception:
        return candidates


def _download_source_logo(source_url, article_url):
    """Best-effort official-site logo/icon fetch. Used only as image fallback."""
    try:
        parsed = urlparse(source_url or article_url)
        if not parsed.netloc:
            return None
        home = f"https://{parsed.netloc}/"
        response = session.get(home, headers={**HEADERS, "Referer": article_url or home}, timeout=15)
        if response.status_code >= 400:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        candidates = []
        for link in soup.find_all("link"):
            rel = " ".join(link.get("rel", [])).lower()
            href = safe_text(link.get("href"))
            if href and ("icon" in rel or "logo" in rel):
                candidates.append(urljoin(response.url, href))
        # JSON-LD logo is preferable when present.
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or script.get_text())
                records = data if isinstance(data, list) else [data]
                for record in records:
                    if isinstance(record, dict):
                        logo = record.get("logo")
                        if isinstance(logo, dict): logo = logo.get("url")
                        if logo: candidates.insert(0, urljoin(response.url, safe_text(logo)))
            except Exception:
                pass
        for url in candidates:
            logo = download_image(url, home)
            if logo:
                return logo
    except Exception:
        return None
    return None


def _source_logo_card(logo):
    canvas = Image.new("RGB", (1200, 675), (24, 34, 46))
    if logo is None:
        return canvas
    max_w, max_h = 500, 250
    ratio = min(max_w / logo.width, max_h / logo.height)
    resized = logo.resize((max(1, int(logo.width * ratio)), max(1, int(logo.height * ratio))), Image.Resampling.LANCZOS)
    canvas.paste(resized, ((1200 - resized.width) // 2, (675 - resized.height) // 2), resized if resized.mode == "RGBA" else None)
    return canvas


def prepare_image(story, index):
    is_poster = False
    image_urls = []
    primary = safe_text(story.get("image_url"))
    if primary and primary.startswith(("http://", "https://")):
        image_urls.append(primary)
    for candidate in story.get("image_candidates", [])[:20]:
        candidate = safe_text(candidate)
        if candidate and candidate.startswith(("http://", "https://")) and candidate not in image_urls:
            image_urls.append(candidate)

    # Poster-priority stories: use the actual portrait poster whenever possible.
    # If a publisher exposes a wide image with a portrait poster embedded between
    # blurred side panels, extract the center poster instead of sending the wide
    # padded composite. Never apply the normal 1200x675 branding/crop to posters.
    if _is_poster_priority(story):
        for url in image_urls:
            image = download_image(url, story.get("url", ""))
            if not image:
                continue
            poster = extract_portrait_poster(image)
            if poster is not None:
                poster = fit_full_poster(poster)
                path = f"/tmp/news_{index}.jpg"
                poster.save(path, "JPEG", quality=92, optimize=True)
                return path

    for url in image_urls:
        image = download_image(url, story.get("url", ""))
        if image:
            branded = branded_card(image)
            path = f"/tmp/news_{index}.jpg"
            branded.save(path, "JPEG", quality=88, optimize=True)
            return path

    # No usable article image. Prefer official publication logo in the center.
    logo = _download_source_logo(story.get("source", ""), story.get("url", ""))
    fallback = _source_logo_card(logo)
    path = f"/tmp/news_{index}.jpg"
    fallback.save(path, "JPEG", quality=90, optimize=True)
    return path


# ============================================================
# TELEGRAM RICH MESSAGES
# ============================================================

def telegram_call(method, data=None, files=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    last = {"ok": False, "description": "Unknown error"}
    for attempt in range(1, 6):
        try:
            response = session.post(url, data=data or {}, files=files, timeout=90)
            result = response.json()
            if result.get("ok"):
                return result
            last = result
            if response.status_code == 429:
                retry_after = int(result.get("parameters", {}).get("retry_after", 5))
                logger.warning("Telegram 429; waiting %ss", retry_after)
                time.sleep(max(1, retry_after))
                continue
            if response.status_code >= 500:
                time.sleep(2 * attempt)
                continue
            break
        except Exception as exc:
            last = {"ok": False, "description": str(exc)}
            time.sleep(2 * attempt)
    return last


def send_bot_api_fallback(image_path, rich_html):
    """Last-resort photo send when Rich Messages are unavailable."""
    text = re.sub(r"<details[^>]*>|</details>|<summary[^>]*>|</summary>", "", rich_html, flags=re.I)
    text = re.sub(r"<tg-spoiler>|</tg-spoiler>", "", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|h1|h2|h3|footer|blockquote)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > MAX_TELEGRAM_CAPTION_CHARACTERS:
        text = text[:MAX_TELEGRAM_CAPTION_CHARACTERS].rsplit(" ", 1)[0].rstrip() + "..."
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(image_path, "rb") as photo:
            response = session.post(url, data={"chat_id": TELEGRAM_CHANNEL, "caption": text}, files={"photo": photo}, timeout=90)
        return response.json()
    except Exception as exc:
        return {"ok": False, "description": str(exc)}


def send_rich_photo(image_path, rich_html):
    """Send image + rich HTML through Telegram Bot API Rich Messages."""
    rich_message = {
        "html": rich_html,
        "media": [{
            "id": "newsphoto",
            "media": {"type": "photo", "media": "attach://photo"},
        }],
        "skip_entity_detection": False,
    }
    with open(image_path, "rb") as photo:
        return telegram_call(
            "sendRichMessage",
            data={"chat_id": TELEGRAM_CHANNEL, "rich_message": json.dumps(rich_message, ensure_ascii=False)},
            files={"photo": photo},
        )

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

def build_candidate_pool(ranked,threshold=PUBLISH_THRESHOLD):
    return [dict(item) for item in ranked if int(item.get("importance_score",0))>=threshold and bool(item.get("important"))]


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
        response = cerebras.chat.completions.create(
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
        # Verification is a publication gate. Infrastructure failure is not evidence.
        return False, ["verification infrastructure failure"]


def event_status_verified(story,article_text):
    claims="\n".join([story.get("headline",""),story.get("summary",""),*story.get("highlights",[])])
    status_terms=re.findall(r"\b(?:confirmed|announced|renewed|cancelled|canceled|coming to|premieres|released|in theaters|production started|production wrapped|acquired|acquires|rights)\b[^.?!]{0,120}",claims,re.I)
    if not status_terms:return True,[]
    schema={"type":"object","properties":{"supported":{"type":"boolean"},"unsupported_claims":{"type":"array","items":{"type":"string"},"maxItems":3}},"required":["supported","unsupported_claims"],"additionalProperties":False}
    prompt="You are a strict entertainment status verifier. Check whether status claims in the generated story are directly supported by the source article. Reject upgrades from speculation to confirmation and misstatements of release, renewal, cancellation, production, rights, platform availability or theatrical status. Return only JSON."
    try:
        r=cerebras.chat.completions.create(model=CEREBRAS_MODEL,messages=[{"role":"system","content":prompt},{"role":"user","content":"SOURCE ARTICLE:\n"+article_text[:12000]+"\n\nSTATUS CLAIMS:\n- "+"\n- ".join(status_terms)}],response_format={"type":"json_schema","json_schema":{"name":"entertainment_status_check","strict":True,"schema":schema}},reasoning_effort="low",temperature=0.0,max_completion_tokens=350)
        d=json.loads(safe_text(r.choices[0].message.content));return bool(d.get("supported")),d.get("unsupported_claims",[])
    except Exception as exc:
        logger.warning("Event-status verification failed: %s",exc);return False,["verification infrastructure failure"]


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

    status_verified, status_claims = event_status_verified(story, article_text)
    if not status_verified:
        logger.warning("DROP event-status verification: %s | claims=%s", story.get("headline"), status_claims)
        return None

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
    ranked = collapse_event_clusters(ranked)
    ranked = [item for item in ranked if item.get("importance_score", 0) >= PUBLISH_THRESHOLD and item.get("important") is True]
    persist_event_cluster_state(ranked)
    return ranked


def process_ranked_region(region,ranked):
    pool=build_candidate_pool(ranked); valid=[]; attempted=0; rejected=0
    for item in pool:
        attempted+=1; story=process_story_candidate(item)
        if not story:rejected+=1; continue
        if is_already_published_candidate({**item,"title":story.get("headline",item.get("title"))}):rejected+=1; continue
        story["sector"]=normalize_sector(story.get("sector") or item.get("sector")); story["topic"]=canonical_topic(story.get("topic") or item.get("topic"),region); story["category_hashtags"]=category_hashtags(story); valid.append(story)
    logger.info("FINAL VALID: %d | threshold=%d/100 | pool=%d attempted=%d rejected=%d",len(valid),PUBLISH_THRESHOLD,len(pool),attempted,rejected)
    return valid


def run():
    logger.info("ENTERTAINMENTNEWSROOM V1 UPDATE-ONLY | 3 sectors | 80/100 gate")
    logger.info("Channel=%s Mode=%s Threshold=%d/100",TELEGRAM_CHANNEL,NEWS_MODE,PUBLISH_THRESHOLD)
    logger.info("LOOKBACK=%d hours | %s -> %s",DISCOVERY_LOOKBACK_HOURS,DISCOVERY_START.isoformat(),DISCOVERY_END.isoformat())
    prune_state(); refresh_category_coverage(); collect_rss()
    count=queue_candidates_for_region("Entertainment"); count+=google_news_gap_fill("Entertainment",count,DISCOVERY_TARGET_PER_REGION); exa_gap_fill("Entertainment",count,DISCOVERY_TARGET_PER_REGION); save_state(STATE)
    candidates=available_candidates("Entertainment",source_pool="primary"); logger.info("DISCOVERY CANDIDATES: %d",len(candidates))
    ranked=prepare_ranked_region("Entertainment",candidates); logger.info("PUBLISHABLE RANKED CANDIDATES: %d",len(ranked))
    stories=process_ranked_region("Entertainment",ranked); published_count=0
    for index,story in enumerate(stories,1):
        try:
            rich_html = fit_rich_html(story)
            logger.info("Telegram rich message prepared: chars=%d type=%s", rich_visible_length(rich_html), story.get("news_type"))
            image_path=prepare_image(story,index)
            result=send_rich_photo(image_path, rich_html)
            if not result.get("ok"):
                logger.warning("Rich Message publish failed; trying Bot API sendPhoto fallback: %s", result.get("description"))
                result=send_bot_api_fallback(image_path, rich_html)
            if not result.get("ok"):
                raise RuntimeError(result.get("description") or "Telegram publish failed")
            message=result.get("result", {})
            published_count+=1
            message_id=message.get("message_id") if isinstance(message, dict) else None
            canonical=story["canonical"]; POSTED_URLS.add(canonical); save_posted_url(canonical); qi=STATE["queue"].get(canonical)
            if qi:qi["status"]="posted";qi["posted_at"]=now_iso()
            store_event(story,published=True,message_id=message_id); remember_posted_event(story); update_category_coverage(story); STATE["recent_titles"].append(normalize_title(story["headline"]))
            logger.info("Published #%d score=%s sector=%s type=%s: %s",published_count,story.get("importance_score",0),story.get("sector"),story.get("news_type"),story["headline"])
        except Exception as exc:
            logger.error("Telegram publication failed for %s: %s",story.get("headline"),exc)
        save_state(STATE); time.sleep(POST_DELAY_SECONDS)
    save_state(STATE); logger.info("Finished. Published=%d",published_count)


# ============================================================
# SELF TEST
# ============================================================

def self_test():
    sample={
        "headline":"Major Series Locks New Release Date",
        "summary":"The production has confirmed a new release date for the major series.",
        "sector":"Hollywood","format":"Series","news_type":"Release Date","priority_type":"Release Date Confirmations",
        "highlights":["The new date has been confirmed.","The series is a major production.","The announcement changes the launch schedule."],
        "platform":"Netflix","episodes":"8","languages":"English","status":"Coming Soon",
        "release_date":"October 10, 2026","expected_date":"","season":"","amount":"","domestic_amount":"","worldwide_amount":"","days_since_release":"",
        "reported_details":[],"framing_line":"","spoiler":"","note":"This detail is source-confirmed.",
        "bold_terms":["Netflix","release date"],"source":"Deadline","url":"https://deadline.com/example/story",
        "region":"Entertainment","topic":"Release Dates","institution":"Netflix","importance_score":88,"important":True,
        "event_key":"major_series_release_date","source_class":"reported"
    }
    rendered=dynamic_rich_html(sample)
    assert "THE CONTEXT" not in rendered and "BOTTOM LINE" not in rendered
    assert "What to Know" not in rendered and "Vocabulary" not in rendered
    assert "📌" not in rendered and "What's New:" not in rendered
    assert "📺" not in rendered and "Availability" not in rendered
    assert "<details>" in rendered and "<summary>ℹ️ More</summary>" in rendered
    assert "<a href=\"https://deadline.com/example/story\">Deadline</a>" in rendered
    assert rich_visible_length(rendered) <= MAX_RICH_CHARACTERS
    assert rank_score({"significance":20,"reach":15,"event_magnitude":15,"platform_ip_strength":10,"source_authority":15,"evidence_strength":10,"international_relevance":5,"recency":5,"audience_anticipation":5,"source_class":"official"})==100
    assert rank_score({"significance":20,"reach":15,"event_magnitude":15,"platform_ip_strength":10,"source_authority":15,"evidence_strength":10,"international_relevance":5,"recency":5,"audience_anticipation":5,"source_class":"rumor"})==69
    assert build_candidate_pool([{"importance_score":79,"important":False},{"importance_score":80,"important":True}]) == [{"importance_score":80,"important":True}]
    assert normalize_sector("Bollywood")=="Indian"

    # Persistent state serialization regression.
    test_state=default_state(); test_state["queue"]["example.com/story"]={"region":"Entertainment","published_date":now_iso(),"last_seen":now_iso(),"status":"pending","title":"Example","url":"https://example.com/story"}
    original=globals()["STATE"]; globals()["STATE"]=test_state
    try:
        save_state(test_state)
        with open(STATE_FILE,encoding="utf-8") as f: loaded=json.load(f)
        assert loaded["queue"]["example.com/story"]["region"]=="Entertainment"
    finally: globals()["STATE"]=original

    # Template structure contract for all supported news types.
    variants=["Now Streaming","Reported","Trailer","Renewal","Cancellation","Box Office","Release Date","Confirmed","Casting","Production","Industry","Distribution","Announcement"]
    for variant in variants:
        probe=dict(sample,news_type=variant)
        if variant in {"Renewal","Cancellation"}: probe["season"]="2"
        if variant == "Box Office": probe.update({"amount":"$100 million","domestic_amount":"$60 million","worldwide_amount":"$100 million","days_since_release":"3"})
        if variant == "Reported": probe["reported_details"]=["The report contains the announced development."]
        if variant == "Trailer": probe["release_date"]="October 10, 2026"
        if variant == "Now Streaming": probe["status"]="Available Now"
        out=dynamic_rich_html(probe)
        assert "What to Know" not in out and "Vocabulary" not in out
        assert "THE CONTEXT" not in out and "BOTTOM LINE" not in out
        assert "Deadline" in out and "<a href=\"https://deadline.com/example/story\">" in out
        assert rich_visible_length(out) <= MAX_RICH_CHARACTERS

    # Spoiler and note use native Rich HTML tags, not literal Markdown.
    spoiler=dict(sample, news_type="Confirmed", spoiler="A major ending reveal.")
    sout=dynamic_rich_html(spoiler)
    assert "<tg-spoiler>A major ending reveal.</tg-spoiler>" in sout
    assert "||" not in sout and "`" not in sout and "[Deadline]" not in sout

    # Numeric grounding.
    grounded_story=dict(sample,headline="Major Series Has 8 Episodes",summary="The series has 8 episodes.",highlights=["The series has 8 episodes.","The production is major.","The release date is confirmed."])
    assert numeric_grounded(grounded_story,"The series will have 8 episodes and release on October 10, 2026.")[0] is True
    assert numeric_grounded(dict(grounded_story,headline="Major Series Has 12 Episodes"),"The series will have 8 episodes and release on October 10, 2026.")[0] is False

    # Event deduplication.
    a=dict(sample,canonical="https://deadline.com/a",title="Major Series Locks New Release Date",editor_rank=1,importance_score=92,event_key="series_release_date")
    b=dict(sample,canonical="https://variety.com/b",title="Major Series Locks Its New Release Date",editor_rank=2,importance_score=88,event_key="series_release_date")
    assert len(collapse_event_clusters([a,b]))==1

    # Telegram Rich Message transport contract with a deterministic mock.
    import tempfile
    class FakeHTTPResponse:
        status_code = 200
        def __init__(self, payload): self._payload = payload
        def json(self): return self._payload
    class FakeSession:
        def __init__(self): self.posts=[]
        def post(self, url, data=None, files=None, timeout=None):
            self.posts.append((url, data or {}, files or {}))
            return FakeHTTPResponse({"ok": True, "result": {"message_id": 123}})
    fake_session=FakeSession(); original_session=globals()["session"]
    globals()["session"]=fake_session
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"fake-image")
            image_path=tmp.name
        transport_story=dict(sample)
        rich=fit_rich_html(transport_story)
        result=send_rich_photo(image_path, rich)
        assert result.get("ok") is True
        assert len(fake_session.posts)==1
        url,data,files=fake_session.posts[0]
        assert url.endswith("/sendRichMessage")
        payload=json.loads(data["rich_message"])
        assert payload["html"]==rich
        assert payload["media"][0]["id"]=="newsphoto"
        assert payload["media"][0]["media"]["media"]=="attach://photo"
        assert "photo" in files
        # Rich failure must fall back to the standard Bot API photo path.
        class FailSession(FakeSession):
            def post(self,url,data=None,files=None,timeout=None):
                self.posts.append((url,data or {},files or {}))
                if url.endswith("/sendRichMessage"):
                    return FakeHTTPResponse({"ok":False,"description":"rich unsupported"})
                return FakeHTTPResponse({"ok":True,"result":{"message_id":124}})
        fail_session=FailSession(); globals()["session"]=fail_session
        rich_result=send_rich_photo(image_path, rich)
        assert rich_result.get("ok") is False
        fallback=send_bot_api_fallback(image_path, rich)
        assert fallback.get("ok") is True
        assert any(u.endswith("/sendPhoto") for u,_,_ in fail_session.posts)
    finally:
        globals()["session"]=original_session
        try: os.unlink(image_path)
        except Exception: pass

    # Global batch ranking mock.
    class FakeMessage:
        def __init__(self,payload): self.content=json.dumps(payload)
    class FakeChoice:
        def __init__(self,payload): self.message=FakeMessage(payload)
    class FakeResponse:
        def __init__(self,payload): self.choices=[FakeChoice(payload)]
    class FakeChat:
        class completions:
            @staticmethod
            def create(**kwargs):
                ids=[int(x.split("ID: ")[1].split("\n")[0]) for x in kwargs["messages"][1]["content"].split("\n") if x.startswith("ID: ")]
                return FakeResponse({"ranked":[{"id":i,"rank":1,"sector":"Hollywood","source_class":"official","significance":20,"reach":15,"event_magnitude":15,"platform_ip_strength":10,"source_authority":15,"evidence_strength":10,"international_relevance":5,"recency":5,"audience_anticipation":5,"topic":"Major Film Announcements","institution":"Netflix","event_key":f"event_{i}","priority_type":("OTT / Streaming Availability" if i == 1 else ("Trailer Releases" if i == 2 else "Box Office Updates")),"reason":"major"} for i in ids]})
    original_c=globals()["cerebras"]; original_e=globals()["enrich_thin_excerpts"]
    globals()["cerebras"]=type("FakeCerebras",(),{"chat":FakeChat()})(); globals()["enrich_thin_excerpts"]=lambda xs:xs
    try:
        candidates=[{"canonical":f"https://example.com/{i}","url":f"https://example.com/{i}","title":f"Story {i}","excerpt":"major entertainment event","source":"Deadline","published_date":now_iso(),"region":"Entertainment"} for i in range(16)]
        ranked_test=rank_candidates(candidates,"Entertainment")
        assert len(ranked_test)==16 and [x["editor_rank"] for x in ranked_test]==list(range(1,17))
    finally:
        globals()["cerebras"]=original_c; globals()["enrich_thin_excerpts"]=original_e

    # Image framing regression: portrait poster keeps its full native ratio.
    poster = Image.new("RGB", (800, 1200), (40, 50, 60))
    framed = fit_full_poster(poster)
    assert framed.size == (800, 1200)

    # Padded-composite poster regression: a portrait poster centered inside a
    # wide blurred image must be extracted to the poster itself.
    sharp = Image.new("RGB", (450, 675), (230, 40, 40))
    draw = ImageDraw.Draw(sharp)
    draw.rectangle((40, 70, 410, 605), outline=(255, 255, 255), width=10)
    for y in range(120, 580, 20):
        draw.line((60, y, 390, y), fill=(255, 220, 40), width=6)
    padded = Image.new("RGB", (1200, 675), (30, 35, 45))
    side = sharp.resize((450, 675), Image.Resampling.LANCZOS)
    padded.paste(side, (375, 0))
    # Simulate soft side panels by down/up sampling the edge source.
    left_pad = side.resize((375, 675), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(12))
    padded.paste(left_pad, (0, 0))
    padded.paste(left_pad, (825, 0))
    extracted = extract_portrait_poster(padded)
    assert extracted is not None
    assert extracted.height == 675
    assert abs((extracted.width / extracted.height) - (2/3)) < 0.01
    assert abs((framed.height / framed.width) - 1.5) < 0.001

    # Poster path must bypass normal channel branding.
    original_download = globals()["download_image"]
    original_brand = globals()["branded_card"]
    try:
        globals()["download_image"] = lambda url, ref: poster
        globals()["branded_card"] = lambda image: (_ for _ in ()).throw(AssertionError("poster branding path used"))
        poster_path = prepare_image(dict(sample, image_url="https://example.com/poster.jpg", priority_type="OTT / Streaming Availability"), 99)
        assert Image.open(poster_path).size == (800, 1200)
    finally:
        globals()["download_image"] = original_download
        globals()["branded_card"] = original_brand

    fallback_card = _source_logo_card(Image.new("RGBA", (600, 200), (255, 255, 255, 255)))
    assert fallback_card.size == (1200, 675)

    logger.info("EntertainmentNewsroom V1 self-test passed.")


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test:
        self_test()
    else:
        run()
