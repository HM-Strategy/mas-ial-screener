import requests
from datetime import datetime
import re
import json
import logging
import os

logger = logging.getLogger(__name__)

MAS_URL = "https://www.mas.gov.sg/api/v1/ialsearch"
FALLBACK_PATH = os.path.join(os.path.dirname(__file__), "data", "ial_fallback.json")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 30


def _normalize_date(raw: str) -> str | None:
    if not raw or raw.strip() in ("-", "N/A", ""):
        return None
    raw = raw.strip()
    formats = [
        "%d %b %Y", "%d %B %Y",
        "%Y-%m-%d",
        "%d/%m/%Y", "%m/%d/%Y",
        "%d-%b-%Y", "%d-%B-%Y",
        "%b %d, %Y", "%B %d, %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    logger.warning("Could not parse date: %s", raw)
    return raw


def _split_aliases(raw: str) -> list[str]:
    if not raw or raw.strip() in ("-", "N/A", ""):
        return []
    parts = re.split(r"[;,]\s*|\n+", raw.strip())
    return [p.strip() for p in parts if p.strip()]


def _do_scrape() -> tuple[list[dict], str]:
    params = {
        "json.nl": "map",
        "wt": "json",
        "sort": "date_dt desc",
        "q": "date_dt:[2017-01-01T00:00:00Z TO *]",
        "rows": 1000,
        "start": 0,
    }
    try:
        resp = requests.get(MAS_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        docs = data.get("response", {}).get("docs", [])
    except Exception as e:
        logger.error("Failed to fetch MAS IAL API: %s", e)
        logger.info("Falling back to local data file...")
        return (_load_fallback(), "fallback")

    entries = []
    for d in docs:
        name = (d.get("unregulatedpersons_s") or "").strip()
        if not name:
            continue

        aliases_raw = d.get("alternativename_s") or ""
        formernames_raw = d.get("formername_s") or ""
        all_aliases = _split_aliases(aliases_raw) + _split_aliases(formernames_raw)

        entries.append({
            "name": name,
            "aliases": all_aliases,
            "type": "Investor Alert List",
            "date_added": _normalize_date(d.get("date_s", "")) or "",
            "description": (d.get("notes_s") or "").strip(),
            "website": (d.get("website_s") or "").strip(),
            "email": (d.get("email_s") or "").strip(),
        })

    if entries:
        logger.info("Scraped %d entries from MAS IAL API.", len(entries))
        return (entries, "live")

    logger.warning("API returned zero entries. Falling back to local data file...")
    return (_load_fallback(), "fallback")


def _load_fallback() -> list[dict]:
    if not os.path.exists(FALLBACK_PATH):
        logger.warning("Fallback file not found at %s", FALLBACK_PATH)
        return []
    try:
        with open(FALLBACK_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Loaded %d entries from fallback file.", len(data))
        return data
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Failed to load fallback file: %s", e)
        return []


def scrape_mas_ial():
    data, _ = _do_scrape()
    return data
