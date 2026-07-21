"""Patent import — fetch and parse patents from Google Patents."""

import re
import logging
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup

logger = logging.getLogger("patent_import")

_log_initialized = False


def _ensure_log():
    global _log_initialized
    if _log_initialized:
        return
    Path("data/logs").mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler("data/logs/patent_import.log", mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    _log_initialized = True


_ensure_log()

BASE_URL = "https://patents.google.com/patent/{patent}/en"


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fetch_patent(patent_number: str) -> Optional[str]:
    patent_number = patent_number.strip().replace(" ", "")
    if not patent_number:
        return None
    url = BASE_URL.format(patent=patent_number)
    logger.info("Fetching patent %s from %s", patent_number, url)
    try:
        resp = requests.get(url, timeout=30, headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        })
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        logger.error("Failed to fetch patent %s: %s", patent_number, e)
        return None


def parse_patent(html: str) -> Optional[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")

    # Title — use the first <h1> with the patent number mention
    title_el = soup.select_one("h1")
    title = clean_text(title_el.get_text()) if title_el else ""

    # Patent number from the title (first token before dash) or meta
    number = ""
    meta_num = soup.select_one('meta[name="citation_patent_number"]')
    if meta_num and meta_num.get("content"):
        number = meta_num["content"]
    if not number and title_el:
        number = title_el.get_text().split("-")[0].strip()

    # Abstract
    abstract_el = soup.select_one('[itemprop="abstract"]')
    if not abstract_el:
        abstract_el = soup.select_one("section.abstract")
    if not abstract_el:
        abstract_el = soup.select_one("div#abstract")
    abstract = clean_text(abstract_el.get_text()) if abstract_el else ""

    # Claims
    claims_section = soup.select_one("div.claims")
    if not claims_section:
        claims_section = soup.select_one("section.claims")
    if not claims_section:
        claims_section = soup.select_one("div#claims")
    claims = ""
    if claims_section:
        claim_texts = []
        for claim_div in claims_section.select("div.claim, div.claim-text, p"):
            t = clean_text(claim_div.get_text())
            if t:
                claim_texts.append(t)
        claims = "\n\n".join(claim_texts) if claim_texts else clean_text(claims_section.get_text())

    # Description
    desc_section = soup.select_one('[itemprop="description"]')
    if not desc_section:
        desc_section = soup.select_one("section.description")
    if not desc_section:
        desc_section = soup.select_one("div#description")
    description = ""
    if desc_section:
        desc_texts = []
        for p in desc_section.select("p, div.description-paragraph"):
            t = clean_text(p.get_text())
            if t:
                desc_texts.append(t)
        description = "\n\n".join(desc_texts) if desc_texts else clean_text(desc_section.get_text())

    if not title and not abstract:
        logger.warning("Could not parse patent — may be an invalid page")
        return None

    patent_data = {
        "number": number,
        "title": title,
        "abstract": abstract,
        "claims": claims,
        "description": description,
    }
    logger.info("Parsed patent %s: title=%s, abstract_len=%d, claims_len=%d, desc_len=%d",
                number, title[:60], len(abstract), len(claims), len(description))
    return patent_data


def patent_to_markdown(data: Dict[str, Any]) -> str:
    parts = []
    if data.get("number"):
        parts.append(f"# Patent {data['number']}")
    if data.get("title"):
        parts.append(f"## {data['title']}")
    if data.get("abstract"):
        parts.append(f"### Abstract\n\n{data['abstract']}")
    if data.get("claims"):
        parts.append(f"### Claims\n\n{data['claims']}")
    if data.get("description"):
        parts.append(f"### Description\n\n{data['description']}")
    return "\n\n".join(parts)


def import_patent_to_kb(
    patent_data: Dict[str, Any],
    kb,
    source_prefix: str = "Google Patent",
    progress_callback=None,
) -> int:
    from knowledge.base import KnowledgeEntry

    md = patent_to_markdown(patent_data)
    title = patent_data.get("title") or patent_data.get("number", "Unknown")
    number = patent_data.get("number", "")

    entry = KnowledgeEntry(
        source=f"{source_prefix}: {number}",
        title=title[:200],
        content=md[:6000],
        category="patent",
        image_paths=[],
    )
    kb.entries.append(entry)
    if progress_callback:
        progress_callback(f"  ✓ Added patent {number}")
    return 1
