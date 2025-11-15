from dateutil import parser as dateparser
from datetime import datetime, timezone, timedelta
import logging
import re
from typing import Optional, Iterable, List

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

logger = logging.getLogger(__name__)

# regex patterns
_MULTI_WS_RE = re.compile(r"\s+")
_LEAD_TRAIL_PUNCT_RE = re.compile(
    r'^[\s\-\–\—\:\;\"\'\(\)\[\]\,\.«»“”‘’\u200e\u200f]+|[\s\-\–\—\:\;\"\'\(\)\[\]\,\.«»“”‘’\u200e\u200f]+$'
)
_BACA_JUGA_RE = re.compile(
    r'\b(baca\s+juga|baca:?\s+selengkapnya|baca\s+selengkapnya|baca\s+juga:?)\b',
    flags=re.IGNORECASE,
)
_DATALAYER_RE = re.compile(r'window\.dataLayer\s*=\s*window\.dataLayer\s*\|\|\s*\[\];.*?;\s*', flags=re.DOTALL)
_JSON_FRAGMENT_RE = re.compile(r'\{.*?"content_description".*?\}', flags=re.DOTALL)
_HTML_TAGS_RE = re.compile(r'<(?:script|style)[\s\S]*?</(?:script|style)>', flags=re.IGNORECASE)

# date parsing
# fallback_map for some common IANA names to fixed offsets (hours)
_FALLBACK_TZ_MAP = {
    "UTC": timezone.utc,
    "Etc/UTC": timezone.utc,
    "Asia/Jakarta": timezone(timedelta(hours=7)),
    "Asia/Jayapura": timezone(timedelta(hours=9)),
    "Asia/Makassar": timezone(timedelta(hours=8))
}

def _resolve_target_tz(tz_name: str):
    if not tz_name:
        return timezone.utc
    if ZoneInfo:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            logger.debug("ZoneInfo could not resolve %r, trying fallback map", tz_name)
    # fallback map (use fixed offsets)
    tz = _FALLBACK_TZ_MAP.get(tz_name)
    if tz:
        return tz
    # try to parse simple offsets like "+07:00" or "UTC+7"
    m = re.match(r'^[UuTtCc]?[Tt][Cc]?(?:([+-]\d{1,2})(?::?(\d{2}))?)$', tz_name)
    if m:
        hours = int(m.group(1) or 0)
        mins = int(m.group(2) or 0)
        return timezone(timedelta(hours=hours, minutes=mins))
    return timezone.utc

def parse_date_to_iso(date_str, tz: str = "UTC", assume_utc_if_naive: bool = True) -> str:
    if not date_str:
        raise ValueError("date_str is empty or None")

    if isinstance(date_str, datetime):
        dt = date_str
    else:
        try:
            dt = dateparser.parse(str(date_str), fuzzy=True)
        except Exception as e:
            raise ValueError(f"unable to parse date_str: {date_str!r}") from e

    if dt is None:
        raise ValueError(f"unable to parse date_str: {date_str!r}")

    if dt.tzinfo is None:
        if assume_utc_if_naive:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.replace(tzinfo=timezone.utc)

    target = _resolve_target_tz(tz)
    try:
        dt = dt.astimezone(target)
    except Exception:
        # last-resort: convert via timestamp to avoid weird tz impl differences
        ts = dt.timestamp()
        offset_dt = datetime.fromtimestamp(ts, tz=target)
        dt = offset_dt
    return dt.isoformat()

# cleaning utilities
def clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    s = str(text)
    s = _HTML_TAGS_RE.sub("", s)
    s = _DATALAYER_RE.sub("", s)
    s = _JSON_FRAGMENT_RE.sub("", s)
    s = s.strip()
    s = _BACA_JUGA_RE.sub("", s)
    s = _MULTI_WS_RE.sub(" ", s)
    s = _LEAD_TRAIL_PUNCT_RE.sub("", s)
    s = _MULTI_WS_RE.sub(" ", s).strip()
    return s

# paragraphs cleaning
def clean_paragraphs(paragraphs: Iterable[str], min_total_length: int = 40) -> str:
    if not paragraphs:
        return ""
    cleaned_parts: List[str] = []
    for p in paragraphs:
        if not p:
            continue
        cp = clean_text(p)
        if not cp:
            continue
        if len(cp) < 8:
            continue
        cleaned_parts.append(cp)
    content = " ".join(cleaned_parts).strip()
    content = _MULTI_WS_RE.sub(" ", content)
    if len(content) < min_total_length:
        return ""
    return content

__all__ = ["parse_date_to_iso", "clean_text", "clean_paragraphs"]
