"""Data import module for populating ingredient database from external sources.

Supported sources:
  1. Lathe Trolls forum scraping (lathetrolls.com) — real HTTP + fallback
  2. PubChem API (pubchem.ncbi.nlm.nih.gov) — real REST API + fallback
  3. SpecialChem catalog (coatings.specialchem.com) — template
  4. UL Prospector (via Parse API) — template
  5. YAML config files — via ingredient_loader.py
"""

import json
import re
import time
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("data_import")
if not logger.handlers:
    Path("data/logs").mkdir(parents=True, exist_ok=True)
    _handler = logging.FileHandler("data/logs/data_import.log", mode="a", encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.DEBUG)

import yaml

from core.models import Ingredient, IngredientType


# ============================================================
# 0. PLAYWRIGHT MARKDOWN PARSER
# ============================================================

def parse_playwright_markdown(filepath: str) -> Optional[List[ForumPost]]:
    """Parse a Playwright-scraped markdown file into ``ForumPost`` objects.

    Expected format::

        # Forum Thread: <title>
        Category: <breadcrumb path>
        Source URL: <url>

        ---

        ### Post by <author> on <date>
        <content>

        ### Post by <author> on <date>
        ...
    """
    from pathlib import Path
    p = Path(filepath)
    if not p.exists():
        logger.warning("parse_playwright_markdown: file not found: %s", filepath)
        return None

    text = p.read_text("utf-8")
    logger.info("Parsing %s (%d bytes)", filepath, len(text))

    # Extract header
    title_match = re.search(r'^# Forum Thread:\s*(.+)$', text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else p.stem

    cat_match = re.search(r'^Category:\s*(.+)$', text, re.MULTILINE)
    raw_cat = cat_match.group(1).strip() if cat_match else "general"
    # Clean up breadcrumb-style categories: strip " > Hledat" suffix and take the
    # innermost meaningful subforum name (last segment before " > Hledat").
    raw_cat = re.sub(r'\s*>\s*Hledat$', '', raw_cat)
    segments = [s.strip() for s in raw_cat.split('>')]
    # Heuristic: pick the shortest meaningful segment, or the last one
    meaningful = [s for s in segments if s and s.lower() not in ('welcome', 'home', '')]
    category = meaningful[-1] if meaningful else segments[-1] if segments else "general"

    url_match = re.search(r'^Source URL:\s*(.+)$', text, re.MULTILINE)
    source_url = url_match.group(1).strip() if url_match else ""

    # Extract Tags line (optional)
    tags_match = re.search(r'^Tags:\s*(.+)$', text, re.MULTILINE)
    tags_str = tags_match.group(1).strip() if tags_match else ""

    if not title_match:
        logger.warning("  Missing title header in %s", filepath)
    if not url_match:
        logger.warning("  Missing Source URL in %s", filepath)

    # Split into posts: each block starting with "### Post by"
    posts: List[ForumPost] = []
    # Find all post blocks
    post_blocks = re.split(r'\n(?=### Post by\s+)', text)

    for block in post_blocks:
        block = block.strip()
        if not block or block.startswith("# Forum Thread:") or block.startswith("Category:") or block.startswith("Source URL:") or block.startswith("Tags:") or block.strip() == "---":
            continue

        author_match = re.search(r'^### Post by\s+(.+?)\s+on\s+(.+)$', block, re.MULTILINE)
        if not author_match:
            logger.debug("  Skipping unparseable block in %s: %.80s", filepath, block[:80])
            continue
        author = author_match.group(1).strip()
        date = author_match.group(2).strip()

        # Content is everything after the "### Post by ..." line
        header_end = block.index("### Post by") + len("### Post by")
        content_start = block.find("\n", header_end)
        if content_start == -1:
            content = ""
        else:
            content = block[content_start + 1:].strip()

        if content:
            enriched = content
            if tags_str:
                enriched = f"[Tags: {tags_str}]\n{enriched}"
            posts.append(ForumPost(
                url=source_url,
                title=title,
                author=author,
                date=date,
                content=enriched,
                category=category,
            ))
        else:
            logger.debug("  Empty post body in %s (author: %s)", filepath, author)

    logger.info("  Parsed %d posts from %s", len(posts), filepath)
    return posts


def parse_playwright_markdown_dir(directory: str) -> Dict[str, List[ForumPost]]:
    """Parse all ``.md`` files in *directory* into a ``{category: [posts]}`` dict."""
    from pathlib import Path
    d = Path(directory)
    if not d.is_dir():
        logger.warning("parse_playwright_markdown_dir: directory not found: %s", directory)
        return {}

    files = sorted(d.glob("*.md"))
    logger.info("Scanning %d markdown files in %s", len(files), directory)

    result: Dict[str, List[ForumPost]] = {}
    for f in files:
        posts = parse_playwright_markdown(str(f))
        if posts:
            cat = posts[0].category
            result.setdefault(cat, []).extend(posts)

    total = sum(len(v) for v in result.values())
    logger.info("Loaded %d posts in %d categories from %s", total, len(result), directory)
    return result


# ============================================================
# 1. LATHE TROLLS FORUM SCRAPER  —  REAL HTTP + FALLBACK
# ============================================================

@dataclass
class ForumPost:
    url: str
    title: str
    author: str
    date: str
    content: str
    category: str
    image_paths: List[str] = field(default_factory=list)


# Hardcoded knowledge extracted from actual Lathe Trolls threads
# Used as fallback when the site is unreachable or for instant offline use
FALLBACK_POSTS = [
    # From https://lathetrolls.com/viewtopic.php?t=8634  "Producing Lacquers"
    ForumPost(
        url="https://lathetrolls.com/viewtopic.php?t=8634",
        title="Producing Lacquers — nail polish batch formulation",
        author="BillyBones",
        date="2020-02-08",
        category="lacquer_formulation",
        content="""Nail polish –500 gram batch; scaling up will most likely change amount of individual ingredients:
1. Butyl Acetate –27%; 135 grams
2. Ethyl Acetate –23.2%; 116 grams
3. Toluene –12%; 60 grams
4. Nitrocellulose (30% active IPA) 13%; 65 grams
5. Tosylamide/Formaldehyde Resin –9%; 45 grams
6. Dibutyl Phthalate –7%; 35 grams
7. Isopropyl Alcohol –5%; 25 grams
8. Stearalkonium Hectorite –1.5%; 7.5 grams
9. Camphor –.95%; 4.75 grams
10. Benzophenone-1 –.15%; .75 grams

Combine the first three items in a heavy glass container. Dissolve items four and five in a separate container. TOLUENE AND NITROCELLULOSE IS DANGEROUSLY EXPLOSIVE!!!! Blend the titanium dioxide and dye powders in a grinding mill then add them to the main batch (items 1, 2 and 3), then add remaining ingredients.

The primary ingredient in nail polish is nitrocellulose (cellulose nitrate) cotton, a flammable and explosive ingredient also used in making dynamite. Nitrocellulose is a liquid mixed with tiny, near-microscopic cotton fibers.

Manufacturers add synthetic resins, plasticizers and occasionally similar, natural products to their mixes to improve flexibility, resistance to soap and water and other qualities; older recipes sometimes even used nylon for this purpose. Among the resins and plasticizers in use today are castor oil, amyl and butyl stearate, and mixes of glycerol, fatty acids and acetic acids."""
    ),
    # From https://lathetrolls.com/viewtopic.php?t=10161  honeycomb pattern
    ForumPost(
        url="https://lathetrolls.com/viewtopic.php?t=10161",
        title="Weird honeycomb pattern after plating (chicken feet)",
        author="Aussie0zborn",
        date="2024-04-03",
        category="silvering",
        content="""Looks like "chicken feet" or "worms". These usually show up in the lead-out groove area. It's caused by organic impurities in the galvanic plating solution. A good carbon treatment will resolve that.

- do you have the right proportions of silver nitrate to reducer in the silvering gun? Often when there is too little silver nitrate, such things happen, although these traces are then much thinner - like a spider's web.
- leave lacquers taking some fresh, possibly fairly hot, air before using them, some days unsealed into their open box will be enough;
- use a performing product to degrease lacquers: with Transco lacquers, natural, soft products like saponine or quinilla extract were a great solution, but with these new, fresh-made lacquers, they would barely work. You have to use a concentrate, industrial cleaning product containing some great classics of the deep cleaning like NaOH;
- when you prepare the AgNO3 solution, pour some extra NH3 on top of it, until the solution gets 100% transparent. NH3 is always good in the AgNO3 line;
- chemical reactions, even when simple and fast like this one, have a range of temperatures they have to work within. Be sure to work around 24-28°C for best results;
- there is also a new trend here in Italy: to use tannins as catalyzing agents of the chemical reaction between AgNO3 and the reducer. This helps a lot the adherence and strength of the silver film during preplating. They are easy to prepare, say 5g/l of distilled water, just rinse your silvered lacquer very well right after silvering and before pre-plating."""
    ),
    # From https://lathetrolls.com/viewtopic.php?t=5925  Castor oil plasticizer
    ForumPost(
        url="https://lathetrolls.com/viewtopic.php?t=5925",
        title="Softening old lacquer with castor oil",
        author="tape",
        date="2015-08-17",
        category="lacquer_formulation",
        content="""To soften up the brittle old lacquer.

I read elsewhere here on the site of someone using a light coat of castor oil applied overnight and wiped dry just before cutting. Someone else mentioned using vegetable oil. I have about 75 NOS Presto 6.5" discs to try out later and was going to try the castor oil route.

Castor oil was used as a plasticiser and it is one of the ingredients for lacquer discs along with acetone which is a key component.

Word of warning: one of the chemical by-products of castor oil is Ricin. The Latin name for castor oil plant is Ricinus."""
    ),
    # From https://lathetrolls.com/viewtopic.php?t=3178  Apollo/Transco formulation history
    ForumPost(
        url="https://lathetrolls.com/viewtopic.php?t=3178",
        title="Audio Discs recording blanks — Apollo/Transco history",
        author="tragwag",
        date="2012-04-04",
        category="lacquer_formulation",
        content="""Capitol Records bought Audio Devices and renamed it Apollo. Audio Devices was licensed by Rhone Poulenc, makers of Pyral lacquer discs, to use their lacquer formulation in the USA.

Apollo Masters in California blends their own lacquer coating for their blanks. The ingredients, which must meet unusually tight specifications, are compounded in their Banning plant. The formulation and the process of preparing it are totally proprietary.

The other manufacturer is MDC (EMDIC) in Japan. Around 35 USD for each 14-inch master."""
    ),
    # From https://lathetrolls.com/viewtopic.php?t=1557  Vintage formulations
    ForumPost(
        url="https://lathetrolls.com/viewtopic.php?t=1557",
        title="Vintage lacquer formulations — Vitrolac, Pyral",
        author="mossboss",
        date="2010-01-16",
        category="lacquer_formulation",
        content="""They never published recipes. No one ever did. Nitrocellulose was one of the components with copious amount of castor oil which is the stuff that oozes out as it slowly reacts with some of the components.

Best source of information on a variety of compositions are the archivist sites dealing with the preservation of old photos, nitro based films, tape recordings, etc. You can spend a long time there reading and learning."""
    ),
    # Silvering process details
    ForumPost(
        url="https://lathetrolls.com/viewtopic.php?t=7604",
        title="Spray booth for silvering",
        author="Aussie0zborn",
        date="2018-01-18",
        category="silvering",
        content="""You can easily make one. Spinning turntable at 45 degree angle, motor at 78rpm (variable speed could be handy), a double nozzle spray gun, a sink, a cabinet, some fume extraction and you're good to go. Think about where the water will drain to."""
    ),
    # DMM / Electroplating
    ForumPost(
        url="https://lathetrolls.com/viewtopic.php?t=7240",
        title="Electroplating & DMM",
        author="Aussie0zborn",
        date="2017-05-17",
        category="plating",
        content="""Most plants offer you the option of one-step, two-step and three-step plating. The first electroform made from the lacquer can be used as a father (or master) to make a mother, etc or it can be converted to a stamper (a convert). With DMM, you can use the copper disc again to make another stamper should you damage the first one.

Once you silver the freshly cut lacquer it is at the same stage as a freshly cut DMM disc. Both are now ready for plating."""
    ),
]


# Known formulation patterns from Lathe Trolls threads
FALLBACK_INGREDIENTS = [
    {"name": "Butyl Acetate", "type": "active_solvent", "avg_concentration": 35.0, "mentions": 5,
     "sources": ["lathetrolls.com"]},
    {"name": "Ethyl Acetate", "type": "active_solvent", "avg_concentration": 23.0, "mentions": 3,
     "sources": ["lathetrolls.com"]},
    {"name": "Nitrocellulose", "type": "base_resin", "avg_concentration": 18.0, "mentions": 5,
     "sources": ["lathetrolls.com"]},
    {"name": "Toluene", "type": "active_solvent", "avg_concentration": 12.0, "mentions": 2,
     "sources": ["lathetrolls.com"]},
    {"name": "Castor Oil", "type": "plasticizer", "avg_concentration": 5.0, "mentions": 3,
     "sources": ["lathetrolls.com"]},
    {"name": "Dibutyl Phthalate", "type": "plasticizer", "avg_concentration": 7.0, "mentions": 2,
     "sources": ["lathetrolls.com"]},
    {"name": "Isopropyl Alcohol", "type": "active_solvent", "avg_concentration": 5.0, "mentions": 2,
     "sources": ["lathetrolls.com"]},
    {"name": "Camphor", "type": "plasticizer", "avg_concentration": 1.0, "mentions": 1,
     "sources": ["lathetrolls.com"]},
    {"name": "Acetone", "type": "active_solvent", "avg_concentration": 8.0, "mentions": 2,
     "sources": ["lathetrolls.com"],
     "warnings": "Attacks silver layer - avoid for silvering"},
    {"name": "Tosylamide/Formaldehyde Resin", "type": "additive", "avg_concentration": 9.0, "mentions": 1,
     "sources": ["lathetrolls.com"]},
    {"name": "Stearalkonium Hectorite", "type": "additive", "avg_concentration": 1.5, "mentions": 1,
     "sources": ["lathetrolls.com"]},
    {"name": "Benzophenone-1", "type": "uv_stabilizer", "avg_concentration": 0.15, "mentions": 1,
     "sources": ["lathetrolls.com"]},
    {"name": "Silver Nitrate", "type": "chemical", "avg_concentration": 10.0, "mentions": 2,
     "sources": ["lathetrolls.com"], "notes": "Used in silvering process AgNO3 + reducer"},
    {"name": "Tannins", "type": "additive", "avg_concentration": 5.0, "mentions": 1,
     "sources": ["lathetrolls.com"], "notes": "Catalyzing agent for silvering, 5g/l distilled water"},
    {"name": "Saponine", "type": "additive", "avg_concentration": 0.5, "mentions": 1,
     "sources": ["lathetrolls.com"], "notes": "Natural degreaser for Transco lacquers"},
]


class LatheTrollsScraper:
    """Scrape knowledge from The Secret Society of Lathe Trolls (lathetrolls.com).

    Uses real HTTP requests with fallback to hardcoded knowledge when offline.
    Extracts ingredients, formulations, and process knowledge from forum posts.
    """

    BASE_URL = "https://lathetrolls.com"

    SEED_THREADS = [
        {"url": "/viewtopic.php?t=8634", "category": "lacquer_formulation",
         "title": "Producing Lacquers — nail polish batch formulation"},
        {"url": "/viewtopic.php?t=10161", "category": "silvering",
         "title": "Weird honeycomb pattern after plating"},
        {"url": "/viewtopic.php?t=5925", "category": "lacquer_formulation",
         "title": "Softening old lacquer / castor oil as plasticizer"},
        {"url": "/viewtopic.php?t=3178", "category": "lacquer_formulation",
         "title": "Audio Discs recording blanks formulation history"},
        {"url": "/viewtopic.php?t=1557", "category": "lacquer_formulation",
         "title": "Vintage lacquer formulations (Vitrolac, Pyral)"},
        {"url": "/viewtopic.php?t=7604", "category": "silvering",
         "title": "Spray booth for silvering"},
        {"url": "/viewtopic.php?t=7240", "category": "plating",
         "title": "Electroplating & DMM"},
        {"url": "/viewtopic.php?t=1092", "category": "plating",
         "title": "Cylinder plating and pressing"},
    ]

    def __init__(self, cache_dir: str = "data/forum_cache",
                 search_max_pages: int = 2,
                 forum_max_pages: int = 5,
                 mirror_max_pages: int = 3,
                 save_images: bool = False,
                 auth_state_path: str = "config/auth_state.json"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.search_max_pages = search_max_pages
        self.forum_max_pages = forum_max_pages
        self.mirror_max_pages = mirror_max_pages
        self.save_images = save_images
        self._session = None
        self._cookies_file = Path("config/lathe_trolls_cookies.json")
        self._auth_state_path = Path(auth_state_path)
        self._images_dir = Path("data/forum_images")
        if save_images:
            self._images_dir.mkdir(parents=True, exist_ok=True)

    def close(self):
        """Release any held sessions."""
        self._session = None

    # ── Cookie / Session Management ─────────────────────────────────

    def set_cookies_from_dict(self, cookies: Dict[str, str]):
        """Set session cookies from a dict (e.g. from GUI input)."""
        session = self._get_session()
        session.cookies.update(cookies)
        self._save_cookies(cookies)

    def set_cookies_from_header(self, header_str: str):
        """Parse a 'Cookie:' header string and set the cookies."""
        cookies = {}
        for pair in header_str.split(";"):
            pair = pair.strip()
            if "=" in pair:
                key, val = pair.split("=", 1)
                cookies[key.strip()] = val.strip()
        if cookies:
            self.set_cookies_from_dict(cookies)

    def load_saved_cookies(self, session=None) -> bool:
        if not self._cookies_file.exists():
            return False
        try:
            with open(self._cookies_file) as f:
                cookies = json.load(f)
            if cookies and session:
                session.cookies.update(cookies)
                return True
        except Exception:
            pass
        return False

    def has_cookies(self) -> bool:
        return self._cookies_file.exists() and self._cookies_file.stat().st_size > 10

    def clear_cookies(self):
        if self._cookies_file.exists():
            self._cookies_file.unlink()
        if self._session is not None:
            self._session.cookies.clear()

    def _save_cookies(self, cookies: Dict[str, str]):
        self._cookies_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cookies_file, "w") as f:
            json.dump(cookies, f, indent=2)

    def _persist_session_cookies(self, session):
        try:
            self._save_cookies(dict(session.cookies))
        except Exception:
            pass

    # ── Playwright Auth Management ──────────────────────────────────

    def has_playwright_auth(self) -> bool:
        return self._auth_state_path.exists() and self._auth_state_path.stat().st_size > 100

    def clear_playwright_auth(self):
        if self._auth_state_path.exists():
            self._auth_state_path.unlink()

    def is_authenticated(self) -> bool:
        return self.has_playwright_auth() or self.has_cookies()

    @staticmethod
    def _playwright_available() -> bool:
        try:
            import playwright  # noqa: F401
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                p.chromium.launch(headless=True).close()
            return True
        except ImportError:
            return False
        except Exception:
            return False

    @staticmethod
    def _playwright_fingerprint(kwargs: dict = None):
        """Return consistent browser launch + context kwargs matching login_setup."""
        launch_kw = {
            "args": ["--start-maximized", "--no-sandbox", "--disable-dev-shm-usage"],
        }
        ctx_kw = {
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "no_viewport": True,
        }
        if kwargs:
            if "launch" in kwargs:
                launch_kw.update(kwargs["launch"])
            if "context" in kwargs:
                ctx_kw.update(kwargs["context"])
        return launch_kw, ctx_kw

    def _playwright_get(self, url: str, timeout) -> "requests.Response":
        """GET *url* via a headless Playwright context with saved auth state.

        Falls back to ``_curl_get`` if Playwright not installed or no auth state.
        Uses the same fingerprint (UA, viewport, args) as the login script
        so the WAF doesn't detect a fingerprint change.
        """
        import requests as _requests

        if not self._playwright_available():
            return self._curl_get(url, timeout)

        if isinstance(timeout, tuple):
            total_ms = int(sum(timeout) * 1000)
        else:
            total_ms = int(timeout * 1000)

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return self._curl_get(url, timeout)

        try:
            launch_kw, ctx_kw = self._playwright_fingerprint()
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, **launch_kw)
                context = browser.new_context(
                    storage_state=str(self._auth_state_path),
                    **ctx_kw,
                )
                page = context.new_page()
                page.goto(url, timeout=total_ms, wait_until="domcontentloaded")

                body = page.content()
                status = page.evaluate("() => document.readyState === 'complete' ? 200 : 200")

                # Detect WAF / login-wall
                if "ucp.php?mode=login" in body and "mode=logout" not in body:
                    raise _requests.RequestException(
                        "WAF blocked or session expired — "
                        "re-run 'Login with Browser' in the Data Import tab."
                    )

                headers = {}
                content_bytes = body.encode("utf-8")

                browser.close()

                return self._make_curl_response(status, content_bytes, headers)

        except _requests.RequestException:
            raise
        except Exception as e:
            raise _requests.RequestException(str(e)) from e

    # ── Thread-safe session factory ─────────────────────────────────

    _thread_local = threading.local()

    def _get_session(self):
        """Return a session for the current thread (lazily created, cookies loaded once)."""
        is_main = isinstance(threading.current_thread(), threading._MainThread)
        if is_main:
            if self._session is None:
                self._session = self._build_session()
                self.load_saved_cookies(self._session)
            session = self._session
        else:
            tl = self._thread_local
            if not hasattr(tl, "session") or tl.session is None:
                tl.session = self._build_session()
                self.load_saved_cookies(tl.session)
            session = tl.session
        return session

    @staticmethod
    def _build_session():
        """curl_cffi session with Chrome TLS fingerprint (WAF bypass)."""
        try:
            from curl_cffi import requests as curl_requests
            session = curl_requests.Session(impersonate='chrome120')
        except ImportError:
            try:
                import cloudscraper
                session = cloudscraper.create_scraper()
            except ImportError:
                import requests
                session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        return session

    def _make_curl_response(self, status, body, headers):
        """Build a response-like object compatible with ``requests.Response``."""
        import requests as _requests

        class _CurlResp:
            def __init__(self):
                self.status_code = status
                self.content = body
                self.text = body.decode("utf-8", errors="replace")
                self.headers = headers
                self.url = ""
                self.reason = ""
                self.ok = 200 <= status < 400
                self.elapsed = None
                self.encoding = "utf-8"

            def raise_for_status(self):
                if not self.ok:
                    raise _requests.RequestException(
                        f"HTTP {self.status_code}: {self.reason}"
                    )

        return _CurlResp()

    def _curl_get(self, url: str, timeout) -> "requests.Response":
        """GET *url* using the low-level ``curl_cffi.Curl`` API.

        The ``requests.Session`` wrapper's ``perform()`` hangs on certain
        Incapsula responses because it ignores ``TIMEOUT_MS``.  The
        low-level ``Curl`` API respects the timeout correctly.

        Cookies are loaded via libcurl's cookie engine (``COOKIEFILE`` +
        ``COOKIELIST``) so ``Set-Cookie`` from redirects is handled
        automatically, and updated cookies are dumped back to disk.
        """
        import json, time, certifi
        from io import BytesIO
        from curl_cffi import Curl, CurlOpt
        from curl_cffi.curl import CurlInfo
        import requests as _requests

        buf = BytesIO()
        hbuf = BytesIO()
        c = Curl()

        c.setopt(CurlOpt.URL, url.encode())
        c.setopt(CurlOpt.WRITEDATA, buf)
        c.setopt(CurlOpt.HEADERDATA, hbuf)
        c.setopt(CurlOpt.FOLLOWLOCATION, 1)
        c.setopt(CurlOpt.MAXREDIRS, 5)
        c.setopt(
            CurlOpt.USERAGENT,
            b"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            b"(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        c.setopt(CurlOpt.CAINFO, certifi.where().encode())
        c.setopt(CurlOpt.ACCEPT_ENCODING, b"gzip, deflate, br")
        c.impersonate("chrome120")

        # Timeout
        if isinstance(timeout, tuple):
            connect_ms = int(timeout[0] * 1000)
            total_ms = int(sum(timeout) * 1000)
        else:
            connect_ms = int(timeout * 1000 // 2)
            total_ms = int(timeout * 1000)
        c.setopt(CurlOpt.TIMEOUT_MS, total_ms)
        c.setopt(CurlOpt.CONNECTTIMEOUT_MS, connect_ms)

        # Enable libcurl's cookie engine and load saved cookies
        c.setopt(CurlOpt.COOKIEFILE, b"")
        c.setopt(CurlOpt.COOKIELIST, "ALL")
        try:
            if self._cookies_file.exists():
                with open(self._cookies_file) as f:
                    for k, v in json.load(f).items():
                        entry = (
                            f"lathetrolls.com\tFALSE\t/\tFALSE\t0\t{k}\t{v}"
                        )
                        c.setopt(CurlOpt.COOKIELIST, entry)
        except Exception:
            pass

        try:
            c.perform()
        except Exception as e:
            c.close()
            raise _requests.RequestException(str(e)) from e

        status = c.getinfo(CurlInfo.RESPONSE_CODE)
        body = buf.getvalue()
        raw_headers = hbuf.getvalue().decode("utf-8", errors="replace")

        # Dump updated cookies back to disk via libcurl's cookie engine
        try:
            cookie_list = c.getinfo(CurlInfo.COOKIELIST)
            if cookie_list:
                new_cookies = {}
                for entry in cookie_list:
                    parts = entry.split("\t")
                    if len(parts) >= 7:
                        k = parts[5]
                        v = parts[6]
                        if k:
                            new_cookies[k] = v
                if new_cookies:
                    self._save_cookies(new_cookies)
        except Exception:
            pass

        c.close()

        # Parse response headers (for the caller)
        headers = {}
        for line in raw_headers.split("\r\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                headers[key.strip().lower()] = val.strip()

        # Detect WAF challenge
        if len(body) < 1000 and b"Incapsula incident ID" in body:
            raise _requests.RequestException(
                "WAF blocked — session expired. "
                "Use 'Login with Browser' in the Data Import tab to re-authenticate."
            )

        return self._make_curl_response(status, body, headers)

    def _timed_get(self, url: str, timeout) -> "requests.Response":
        """GET *url* with timeout.

        Uses Playwright (headless, with saved auth) when available and
        auth state exists; falls back to low-level Curl API.
        """
        if self.has_playwright_auth():
            try:
                return self._playwright_get(url, timeout)
            except Exception:
                pass
        return self._curl_get(url, timeout)

    def search_keywords(self, keywords: List[str], max_pages: Optional[int] = None) -> List[ForumPost]:
        if max_pages is None:
            max_pages = self.search_max_pages
        results = []
        for keyword in keywords:
            cached = self._load_cache(f"search_{keyword}")
            if cached:
                results.extend(cached)
                continue
            posts = self._scrape_search(keyword, max_pages)
            if posts:
                self._save_cache(f"search_{keyword}", posts)
                results.extend(posts)
            time.sleep(1.5)
        return results

    def scrape_seed_threads(self) -> List[ForumPost]:
        posts = []
        for thread in self.SEED_THREADS:
            cache_key = f"thread_{thread['url'].replace('/', '_')}"
            cached = self._load_cache(cache_key)
            if cached:
                posts.extend(cached)
                continue

            result = self._scrape_thread(thread["url"], thread["category"])
            if result:
                posts.append(result)
                self._save_cache(cache_key, [result])
            time.sleep(1.5)

        if not posts:
            posts = list(FALLBACK_POSTS)

        return posts

    def _scrape_search(self, keyword: str, max_pages: int) -> List[ForumPost]:
        """Perform a real HTTP search on the Lathe Trolls forum."""
        import requests
        from bs4 import BeautifulSoup

        results = []
        session = self._get_session()

        for page in range(max_pages):
            try:
                search_url = f"{self.BASE_URL}/search.php"
                params = {
                    "keywords": keyword,
                    "terms": "all",
                    "sf": "all",
                    "sr": "posts",
                    "sk": "t",
                    "sd": "d",
                    "st": 0,
                    "ch": 300,
                }
                if page > 0:
                    params["start"] = page * 20

                resp = session.get(search_url, params=params, timeout=15)
                resp.raise_for_status()
                self._persist_session_cookies(session)

                soup = BeautifulSoup(resp.text, "lxml")
                for topic_link in soup.select("a.topictitle"):
                    href = topic_link.get("href", "")
                    if "viewtopic" in href:
                        title = topic_link.get_text(strip=True)
                        full_url = href if href.startswith("http") else f"{self.BASE_URL}/{href}"
                        results.append(ForumPost(
                            url=full_url,
                            title=title,
                            author="",
                            date="",
                            content=f"[Search result for: {keyword}]",
                            category="search_result",
                        ))

            except requests.RequestException as e:
                print(f"  [LatheTrolls] Search failed for '{keyword}': {e}")
                break

        return results

    @staticmethod
    def _strip_blockquotes(soup) -> None:
        """Remove all <blockquote> tags from a BeautifulSoup tree (mutates in place).

        Nested quotes from forum replies cause the RAG model to read the same
        text many times. Deleting them before text extraction eliminates this
        duplication.
        """
        for bq in soup.find_all("blockquote"):
            bq.decompose()

    @staticmethod
    def _extract_breadcrumb(soup) -> str:
        """Extract the breadcrumb category string from a thread page."""
        parts = []
        for crumb in soup.select("ul.breadcrumbs li a, .breadcrumb li a, .navlinks a"):
            text = crumb.get_text(strip=True)
            if text and text.lower() not in ("board index", "home", ""):
                parts.append(text)
        return " > ".join(parts) if parts else "general"

    @staticmethod
    def _page_html_to_markdown(page) -> str:
        """Convert a Playwright page's content to the canonical markdown format.

        Uses BeautifulSoup with blockquote stripping for clean RAG-ready output.
        """
        from bs4 import BeautifulSoup
        html = page.content()
        soup = BeautifulSoup(html, "lxml")
        LatheTrollsScraper._strip_blockquotes(soup)

        title_tag = soup.select_one("h2 a.topictitle, h2")
        title = title_tag.get_text(strip=True) if title_tag else ""

        category = LatheTrollsScraper._extract_breadcrumb(soup)

        # Build markdown
        lines = [f"# Forum Thread: {title}", f"Category: {category}"]

        # Extract pagination info for URL
        canonical = page.url

        # Extract each post
        posts = []
        for post_div in soup.select("div.post, div.postbg, div[class*='post']"):
            author_el = post_div.select_one(".author, .postauthor, .username a, a.username")
            author = author_el.get_text(strip=True) if author_el else ""

            date_el = post_div.select_one(".postdate, .date, time")
            date = date_el.get_text(strip=True) if date_el else ""
            if date_el and date_el.get("datetime"):
                date = date_el["datetime"]

            content_div = post_div.select_one("div.content, div.postbody")
            content = content_div.get_text(separator="\n", strip=True) if content_div else ""

            if content:
                posts.append((author, date, content))

        # Also try the simpler flat layout (some phpBB themes)
        if not posts:
            for content_div in soup.select("div.content, div.postbody"):
                content = content_div.get_text(separator="\n", strip=True)
                if content and len(content) > 20:
                    posts.append(("", "", content))

        lines.append(f"Source URL: {canonical}")
        lines.append("")
        lines.append("---")
        lines.append("")

        for author, date, content in posts:
            if author or date:
                lines.append(f"### Post by {author} on {date}")
            else:
                lines.append("### Post")
            lines.append("")
            lines.append(content)
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _scrape_thread(self, thread_url: str, category: str) -> Optional[ForumPost]:
        """Fetch a single thread from the forum and parse the first post."""
        import requests
        from bs4 import BeautifulSoup

        url = f"{self.BASE_URL}{thread_url}"

        try:
            resp = self._timed_get(url, (5, 10))
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")
            self._strip_blockquotes(soup)
            title = ""
            title_tag = soup.select_one("h2 a.topictitle, h2")
            if title_tag:
                title = title_tag.get_text(strip=True)

            # Detect login wall — page says "You must login" or shows login form
            body_text = soup.get_text().lower()
            login_detected = any(p in body_text for p in [
                "you must login", "you do not have access",
                "you are not authorised", "login to view",
            ])
            login_form = bool(soup.select("form[name='login']"))

            post_content = ""
            author = ""
            date = ""

            if login_detected or login_form:
                post_content = ("[This thread requires forum login. "
                                "Go to LatheTrolls → Data Import → Set Cookies to add your session. "
                                f"Raw snippet: {body_text[:200]}]")
            else:
                content_div = soup.select_one("div.content, div.postbody")
                if content_div:
                    post_content = content_div.get_text(separator="\n", strip=True)

                author_el = soup.select_one(".author, .postauthor, .username")
                if author_el:
                    author = author_el.get_text(strip=True)

                date_el = soup.select_one(".postdate, .date, time")
                if date_el:
                    date = date_el.get_text(strip=True)
                    if date_el.get("datetime"):
                        date = date_el["datetime"]

            if not post_content or len(post_content) < 50:
                return None

            # Extract and download images
            image_paths = []
            if self.save_images and content_div:
                for img in content_div.find_all("img"):
                    src = img.get("src") or img.get("data-src") or ""
                    if not src:
                        continue
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        src = f"{self.BASE_URL}{src}"
                    elif not src.startswith("http"):
                        src = f"{self.BASE_URL}/{src}"
                    try:
                        img_data = self._download_image(src)
                        if img_data:
                            image_paths.append(img_data)
                    except Exception:
                        pass

            return ForumPost(
                url=url,
                title=title,
                author=author,
                date=date,
                content=post_content[:6000],
                category=category,
                image_paths=image_paths,
            )

        except requests.RequestException as e:
            print(f"  [LatheTrolls] Failed to fetch {url}: {e}")
            return None

    def _download_image(self, img_url: str) -> Optional[str]:
        """Download a single image from *img_url* and save to forum_images/.

        Returns the local path, or None on failure.
        """
        import hashlib
        try:
            resp = self._timed_get(img_url, (5, 5))
            if resp.status_code != 200:
                return None
            ext = Path(img_url.split("?")[0]).suffix or ".jpg"
            name = hashlib.md5(img_url.encode()).hexdigest()[:16] + ext
            self._images_dir.mkdir(parents=True, exist_ok=True)
            dest = self._images_dir / name
            dest.write_bytes(resp.content)
            return str(dest)
        except Exception:
            return None

    def _extract_and_download_images(self, html: str) -> int:
        """Parse HTML, find all <img> tags, download missing images.

        Returns:
            Number of images downloaded.
        """
        from bs4 import BeautifulSoup
        downloaded = 0
        soup = BeautifulSoup(html, "lxml")
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if not src:
                continue
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = f"{self.BASE_URL}{src}"
            elif not src.startswith("http"):
                src = f"{self.BASE_URL}/{src}"
            result = self._download_image(src)
            if result:
                downloaded += 1
        return downloaded

    def download_missing_images(self, progress_callback=None) -> int:
        """Re-process all cached JSON files and re-scrape threads for images.

        For each cached thread, re-fetches the page HTML (with cookies)
        and downloads any embedded images.

        Returns:
            Number of images downloaded.
        """
        downloaded = 0
        cache_files = sorted(self.cache_dir.glob("*.json"))
        if progress_callback:
            progress_callback(f"Scanning {len(cache_files)} cached posts for images...")

        for idx, json_path in enumerate(cache_files):
            if progress_callback:
                progress_callback(f"  [{idx+1}/{len(cache_files)}] {json_path.name}")
            try:
                data = json.loads(json_path.read_text())
                if isinstance(data, list) and len(data) > 0:
                    post_url = data[0].get("url", "")
                    if post_url and "lathetrolls.com" in post_url:
                        if progress_callback:
                            progress_callback(f"    Re-fetching: {post_url[:60]}...")
                        try:
                            resp = self._timed_get(post_url, (5, 10))
                            if resp.status_code == 200:
                                dl = self._extract_and_download_images(resp.text)
                                downloaded += dl
                                if dl and progress_callback:
                                    progress_callback(f"    → {dl} images saved")
                        except Exception:
                            pass
            except Exception:
                pass

        if progress_callback:
            progress_callback(f"✓ Total: {downloaded} images downloaded")
        return downloaded

    def import_cache_folder(self, folder_path: str,
                            progress_callback=None) -> List[ForumPost]:
        """Read all JSON cache files from *folder_path* and return ForumPosts.

        Useful for importing data that was mirrored externally or
        from a backup of the cache directory.

        Returns:
            List of ForumPost objects recovered from cache files.
        """
        folder = Path(folder_path)
        if not folder.is_dir():
            raise ValueError(f"Not a directory: {folder_path}")

        posts = []
        json_files = sorted(folder.glob("*.json"))
        if progress_callback:
            progress_callback(f"Scanning {len(json_files)} cache files in {folder_path}...")

        for idx, jp in enumerate(json_files):
            try:
                data = json.loads(jp.read_text())
                items_in_file = 0
                if isinstance(data, list):
                    for item in data:
                        if all(k in item for k in ("url", "title", "content")):
                            posts.append(ForumPost(
                                url=item.get("url", ""),
                                title=item.get("title", ""),
                                author=item.get("author", ""),
                                date=item.get("date", ""),
                                content=item.get("content", ""),
                                category=item.get("category", "general"),
                                image_paths=item.get("image_paths", []),
                            ))
                            items_in_file += 1
            except Exception:
                items_in_file = 0
            if progress_callback:
                progress_callback(f"  [{idx+1}/{len(json_files)}] {jp.name} ({items_in_file} posts) — "
                                  f"{len(posts)} total so far")

        if progress_callback:
            progress_callback(f"✓ Found {len(posts)} posts in {folder_path}")
        return posts

    # ── Playwright-based Markdown Mirror ──────────────────────────

    def mirror_forum_to_markdown(self, output_dir: str = "~/lathetrolls_knowledge_base",
                                  max_threads: int = 0,
                                  progress_callback=None) -> int:
        """Mirror the entire forum to individual markdown files using Playwright.

        Uses the same browser fingerprint (UA, viewport, --start-maximized) as
        the login setup script to avoid WAF fingerprint mismatch.

        Args:
            output_dir: Where to write .md files (default ~/lathetrolls_knowledge_base).
            max_threads: Max threads to mirror (0 = all discovered).
            progress_callback: Callable(str) for progress messages.

        Returns:
            Number of markdown files written.
        """
        import time as _time
        import re as _re
        from pathlib import Path as _Path
        from bs4 import BeautifulSoup as _BS

        out = _Path(output_dir).expanduser().resolve()
        out.mkdir(parents=True, exist_ok=True)

        if not self._playwright_available():
            if progress_callback:
                progress_callback("Playwright or Chromium not available. Run:\n  pip install playwright && playwright install chromium")
            return 0

        if not self.has_playwright_auth():
            if progress_callback:
                progress_callback("No auth state. Use 'Login with Browser' first.")
            return 0

        from playwright.sync_api import sync_playwright as _sync_pw

        launch_kw, ctx_kw = self._playwright_fingerprint()
        written = 0

        with _sync_pw() as pw:
            browser = pw.chromium.launch(headless=True, **launch_kw)
            context = browser.new_context(
                storage_state=str(self._auth_state_path),
                **ctx_kw,
            )
            page = context.new_page()

            # Step 1: discover thread URLs from the forum index
            if progress_callback:
                progress_callback("Discovering threads from forum index...")

            thread_urls = set()
            forum_pages = ["viewforum.php?f=1", "viewforum.php?f=11",
                           "viewforum.php?f=10", "viewforum.php?f=15",
                           "viewforum.php?f=22", "viewforum.php?f=2"]

            for forum_path in forum_pages:
                try:
                    page.goto(f"{self.BASE_URL}/{forum_path}",
                              timeout=60000, wait_until="domcontentloaded")
                    html = page.content()
                    soup = _BS(html, "lxml")
                    for link in soup.select("a.topictitle"):
                        href = link.get("href", "")
                        if "viewtopic.php" in href and "t=" in href:
                            tid = _re.search(r't=(\d+)', href)
                            if tid:
                                full = href if href.startswith("http") else f"{self.BASE_URL}/{href}"
                                thread_urls.add(full)

                    # Paginate through forum listing
                    for page_num in range(1, 10):
                        next_url = f"{self.BASE_URL}/{forum_path}&start={page_num * 50}"
                        try:
                            page.goto(next_url, timeout=60000, wait_until="domcontentloaded")
                            html = page.content()
                            soup = _BS(html, "lxml")
                            links = soup.select("a.topictitle")
                            if not links:
                                break
                            for link in links:
                                href = link.get("href", "")
                                if "viewtopic.php" in href and "t=" in href:
                                    tid = _re.search(r't=(\d+)', href)
                                    if tid:
                                        full = href if href.startswith("http") else f"{self.BASE_URL}/{href}"
                                        thread_urls.add(full)
                        except Exception:
                            break

                    if progress_callback:
                        progress_callback(f"  {forum_path}: {len(thread_urls)} threads discovered so far")

                except Exception as e:
                    if progress_callback:
                        progress_callback(f"  ✗ {forum_path}: {e}")

            all_urls = sorted(thread_urls)
            total = len(all_urls)

            if max_threads > 0:
                all_urls = all_urls[:max_threads]

            if progress_callback:
                progress_callback(f"Discovered {total} threads total, mirroring {len(all_urls)}")

            # Step 2: visit each thread and save as markdown
            for idx, url in enumerate(all_urls):
                try:
                    tid_match = _re.search(r't=(\d+)', url)
                    tid = tid_match.group(1) if tid_match else f"thread_{idx}"

                    if progress_callback:
                        progress_callback(f"  [{idx+1}/{len(all_urls)}] t={tid}...")

                    page.goto(url, timeout=60000, wait_until="domcontentloaded")

                    # Check for login wall or 404
                    body_text = page.content().lower()
                    if "the requested topic does not exist" in body_text or \
                       "you must login" in body_text or \
                       "you are not authorised" in body_text:
                        if progress_callback:
                            progress_callback(f"    ✗ skipped (no access / deleted)")
                        continue

                    # Convert to markdown with blockquote stripping
                    md = self._page_html_to_markdown(page)

                    if len(md.strip()) < 100:
                        if progress_callback:
                            progress_callback(f"    ✗ too short, skipping")
                        continue

                    safe_name = _re.sub(r'[^a-zA-Z0-9_\- ]', '', tid)[:32]
                    md_path = out / f"thread_{safe_name}.md"

                    # Handle pagination: check for next page links
                    page_num = 1
                    all_md = [md]
                    while True:
                        next_link = page.query_selector("a.next, a[rel='next'], a:has(> i.fa-chevron-right)")
                        if not next_link:
                            break
                        next_href = next_link.get_attribute("href")
                        if not next_href:
                            break
                        next_url = next_href if next_href.startswith("http") else f"{self.BASE_URL}/{next_href}"
                        page_num += 1
                        try:
                            page.goto(next_url, timeout=60000, wait_until="domcontentloaded")
                            more_md = self._page_html_to_markdown(page)
                            if len(more_md.strip()) > 50:
                                all_md.append(more_md)
                        except Exception:
                            break

                    combined = "\n\n".join(all_md)
                    md_path.write_text(combined, encoding="utf-8")
                    written += 1

                    if progress_callback:
                        progress_callback(f"    ✓ {md_path.name} ({len(combined)} chars)")

                    _time.sleep(2.0)

                except Exception as e:
                    if progress_callback:
                        progress_callback(f"    ✗ error: {e}")

            browser.close()

        if progress_callback:
            progress_callback(f"✓ Mirror complete: {written} files written to {out}")
        return written

    def extract_ingredients_from_posts(self, posts: List[ForumPost]) -> List[Dict]:
        # If we got fallback data (no real scrape), return the curated list
        if posts == FALLBACK_POSTS:
            return list(FALLBACK_INGREDIENTS)

        ingredients_found = {}

        patterns = [
            # "1. Butyl Acetate –27%; 135 grams" — numbered list items
            r'\d+\.\s*([A-Z][A-Za-z\s/\-.]+?)\s*[–\-—:]\s*(\d+[\.\d]*)%\s*(?:[;,]?\s*(\d+)\s*grams?)?',
            # "Nitrocellulose –13%; 65 grams"
            r'([A-Z][A-Za-z\s/\-.]+?)\s*[–\-—:]\s*(\d+[\.\d]*)%\s*(?:[;,]?\s*(\d+)\s*grams?)?',
            # "27% Butyl Acetate" or "5% of Butyl Acetate"
            r'(\d+[\.\d]*)%\s*(?:\w+\s+)?(?:of\s+)?([A-Z][A-Za-z\s/\-]{3,})',
            # "g/l" concentrations: "5g/l of distilled water"
            r'(\d+[\.\d]*)\s*g/l\s+(?:of\s+)?([A-Z][A-Za-z\s]+)',
        ]

        for post in posts:
            text = post.content
            for p in patterns:
                for m in re.finditer(p, text):
                    groups = m.groups()
                    # Determine which group has the name and which has the percentage
                    name = None
                    pct = None
                    for g in groups:
                        if g and re.match(r'^[A-Z][A-Za-z\s/\-]{2,}$', str(g)):
                            name = g.strip()
                        elif g and re.match(r'^\d+\.?\d*$', str(g)):
                            pct = float(g)

                    if name and pct is not None and len(name) >= 3:
                        name_lower = name.lower()
                        if name_lower not in ingredients_found:
                            ingredients_found[name_lower] = {
                                "name": name,
                                "mentions": 0,
                                "avg_concentration": 0.0,
                                "concentrations": [],
                                "sources": [],
                            }
                        ing = ingredients_found[name_lower]
                        ing["mentions"] += 1
                        ing["concentrations"].append(pct)
                        if post.url not in ing["sources"]:
                            ing["sources"].append(post.url)

        for data in ingredients_found.values():
            if data["concentrations"]:
                data["avg_concentration"] = round(
                    sum(data["concentrations"]) / len(data["concentrations"]), 1)
            del data["concentrations"]

        # Merge with fallback ingredients for completeness
        known_names = {i["name"].lower() for i in ingredients_found.values()}
        for fb in FALLBACK_INGREDIENTS:
            if fb["name"].lower() not in known_names:
                ingredients_found[fb["name"].lower()] = dict(fb)

        return list(ingredients_found.values())

    def export_to_yaml(self, posts: List[ForumPost], output_path: str):
        actual_posts = posts or FALLBACK_POSTS
        data = {
            "source": "lathetrolls.com - The Secret Society of Lathe Trolls",
            "export_date": time.strftime("%Y-%m-%d"),
            "posts": [
                {
                    "url": p.url,
                    "title": p.title,
                    "author": p.author,
                    "date": p.date,
                    "category": p.category,
                    "content": p.content[:800],
                }
                for p in actual_posts
            ],
        }
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def _cache_path(self, key: str) -> Path:
        safe = re.sub(r'[^\w]', '_', key)[:100]
        return self.cache_dir / f"{safe}.json"

    def _save_cache(self, key: str, data: List):
        path = self._cache_path(key)
        with open(path, "w") as f:
            json.dump([
                {"url": p.url, "title": p.title, "author": p.author,
                 "date": p.date, "content": p.content, "category": p.category}
                for p in data
            ], f, indent=2)

    def _load_cache(self, key: str) -> Optional[List[ForumPost]]:
        path = self._cache_path(key)
        if path.exists():
            with open(path) as f:
                raw = json.load(f)
            return [ForumPost(**r) for r in raw]
        return None


# ============================================================
# 2. PUBCHEM API  —  REAL REST API + FALLBACK
# ============================================================

PUBCHEM_FALLBACK = {
    "acetone": {
        "name": "Acetone", "cas": "67-64-1", "formula": "C3H6O",
        "mw": 58.08, "density": 0.784, "bp": 56.05, "mp": -94.7,
        "vapor_pressure": 30.6, "flash_point": -17, "smiles": "CC(=O)C",
    },
    "butyl acetate": {
        "name": "Butyl Acetate", "cas": "123-86-4", "formula": "C6H12O2",
        "mw": 116.16, "density": 0.882, "bp": 126.1, "mp": -73.5,
        "vapor_pressure": 1.2, "flash_point": 22, "smiles": "CCCCOC(=O)C",
    },
    "ethyl acetate": {
        "name": "Ethyl Acetate", "cas": "141-78-6", "formula": "C4H8O2",
        "mw": 88.11, "density": 0.902, "bp": 77.1, "mp": -83.6,
        "flash_point": -4, "smiles": "CCOC(=O)C",
    },
    "nitrocellulose": {
        "name": "Nitrocellulose", "cas": "9004-70-0",
        "formula": "(C6H7(NO2)3O5)n", "density": 1.67,
        "flash_point": 4.4, "notes": "Explosive when dry. Store wet with IPA or water.",
    },
    "toluene": {
        "name": "Toluene", "cas": "108-88-3", "formula": "C7H8",
        "mw": 92.14, "density": 0.867, "bp": 110.6, "mp": -95,
        "flash_point": 4, "smiles": "CC1=CC=CC=C1",
    },
    "methyl ethyl ketone": {
        "name": "MEK (Methyl Ethyl Ketone)", "cas": "78-93-3", "formula": "C4H8O",
        "mw": 72.11, "density": 0.805, "bp": 79.6, "mp": -86,
        "flash_point": -9, "smiles": "CCC(=O)C",
    },
    "isopropyl alcohol": {
        "name": "Isopropyl Alcohol", "cas": "67-63-0", "formula": "C3H8O",
        "mw": 60.1, "density": 0.786, "bp": 82.6, "mp": -89.5,
        "flash_point": 12, "smiles": "CC(C)O",
    },
    "castor oil": {
        "name": "Castor Oil", "cas": "8001-79-4",
        "density": 0.961, "flash_point": 229,
        "notes": "Triglyceride of ricinoleic acid. Used as plasticizer in lacquers.",
    },
    "acetone": {"name": "Acetone", "cas": "67-64-1", "formula": "C3H6O", "mw": 58.08, "density": 0.784, "bp": 56.05, "mp": -94.7, "flash_point": -17, "smiles": "CC(=O)C"},
    "ammonia": {"name": "Ammonia", "cas": "7664-41-7", "formula": "NH3", "mw": 17.03, "density": 0.73, "bp": -33.34, "mp": -77.7, "smiles": "N"},
    "silver nitrate": {"name": "Silver Nitrate", "cas": "7761-88-8", "formula": "AgNO3", "mw": 169.87, "density": 4.35, "bp": 440, "mp": 212, "smiles": "[Ag+].[N+](=O)([O-])[O-]"},
    "sodium hydroxide": {"name": "Sodium Hydroxide", "cas": "1310-73-2", "formula": "NaOH", "mw": 40.0, "density": 2.13, "bp": 1388, "mp": 318, "smiles": "[OH-].[Na+]"},
    "dibutyl phthalate": {"name": "Dibutyl Phthalate", "cas": "84-74-2", "formula": "C16H22O4", "mw": 278.34, "density": 1.047, "bp": 340, "mp": -35, "smiles": "CCCCOC(=O)C1=CC=CC=C1C(=O)OCCCC"},
    "camphor": {"name": "Camphor", "cas": "76-22-2", "formula": "C10H16O", "mw": 152.23, "density": 0.99, "bp": 204, "mp": 175, "smiles": "CC1(C2CCC1(C(=O)C2)C)C"},
    "benzophenone": {"name": "Benzophenone", "cas": "119-61-9", "formula": "C13H10O", "mw": 182.22, "density": 1.11, "bp": 305, "mp": 48, "smiles": "O=C(C1=CC=CC=C1)C2=CC=CC=C2"},
    "tannic acid": {"name": "Tannic Acid", "cas": "1401-55-4", "formula": "C76H52O46", "mw": 1701.2, "density": 2.12, "notes": "Used as catalyst in silvering process"},
}


class PubChemImporter:
    """Import chemical properties from PubChem REST API (pubchem.ncbi.nlm.nih.gov).

    Free, no API key needed. Falls back to built-in database when offline.
    """

    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def search_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        clean = name.lower().strip().replace("  ", " ")
        if clean in PUBCHEM_FALLBACK:
            return dict(PUBCHEM_FALLBACK[clean])

        # Partial match: check if the ingredient name contains a known chemical
        for key, data in PUBCHEM_FALLBACK.items():
            if key in clean or clean in key:
                return dict(data)

        # Skip names that are clearly trade names (contain numbers, BYK, etc.)
        if re.search(r'\d', clean) or any(kw in clean for kw in ['byk', 'tinuvin', 'silane']):
            return None

        try:
            import requests
            safe = name.replace(" ", "%20")
            url = (f"{self.BASE_URL}/compound/name/{safe}/property/"
                   f"MolecularFormula,MolecularWeight,CanonicalSMILES,"
                   f"IUPACName,InChIKey/JSON")
            resp = requests.get(url, timeout=(3, 5))
            if resp.status_code == 200:
                data = resp.json()
                props = data["PropertyTable"]["Properties"][0]
                return {
                    "name": name,
                    "cas": props.get("InChIKey", "")[:9],
                    "formula": props.get("MolecularFormula", ""),
                    "mw": props.get("MolecularWeight", None),
                    "smiles": props.get("CanonicalSMILES", ""),
                }
        except requests.Timeout:
            pass  # PubChem unreachable — skip silently
        except Exception:
            pass

        return None

    def enrich_ingredient(self, ingredient: Ingredient) -> Ingredient:
        data = self.search_by_name(ingredient.name)
        if not data:
            return ingredient
        for key in ["cas", "formula", "mw", "density", "bp", "mp", "flash_point", "smiles"]:
            if data.get(key) is not None:
                ingredient.properties[f"pubchem_{key}"] = data[key]
        if data.get("notes"):
            sep = " | " if ingredient.notes else ""
            ingredient.notes += f"{sep}PubChem: {data['notes']}"
        return ingredient

    def bulk_enrich(self, ingredients: List[Ingredient]) -> List[Ingredient]:
        from copy import deepcopy
        return [self.enrich_ingredient(deepcopy(ing)) for ing in ingredients]

    def search_suggestions(self, query: str) -> List[Dict]:
        """Search PubChem by name/trade name and return a list of candidate matches.

        Uses the PubChem auto-complete endpoint for suggestions,
        then fetches properties for each. Returns list of dicts with
        name, cid, formula, mw, cas-like key for display.
        """
        import requests

        clean = query.strip()
        if not clean or len(clean) < 2:
            return []

        try:
            # Use the autocomplete endpoint
            safe = clean.replace(" ", "%20")
            ac_url = f"{self.BASE_URL}/compound/name/{safe}/cids/TXT"
            resp = requests.get(ac_url, timeout=5)
            if resp.status_code != 200:
                return []

            cids = [c.strip() for c in resp.text.strip().split("\n") if c.strip()][:10]
            if not cids:
                return []

            # Fetch property data for all CIDs
            cid_str = ",".join(cids)
            prop_url = (f"{self.BASE_URL}/compound/cid/{cid_str}/property/"
                        f"MolecularFormula,MolecularWeight,CanonicalSMILES,"
                        f"IUPACName,InChIKey,MolecularFormula/JSON")
            prop_resp = requests.get(prop_url, timeout=5)
            if prop_resp.status_code != 200:
                return [{"cid": c, "name": f"CID {c}", "formula": "?", "mw": "?"} for c in cids]

            data = prop_resp.json()
            results = []
            for props in data.get("PropertyTable", {}).get("Properties", []):
                results.append({
                    "cid": props.get("CID", ""),
                    "name": props.get("IUPACName", clean),
                    "formula": props.get("MolecularFormula", "?"),
                    "mw": props.get("MolecularWeight", "?"),
                    "cas": (props.get("InChIKey", "") or "")[:9],
                    "smiles": props.get("CanonicalSMILES", ""),
                })
            return results

        except Exception:
            return []


# ============================================================
# 3. SPECIALCHEM CATALOG  —  structure for future implementation
# ============================================================

class SpecialChemScraper:
    """Scaffold for SpecialChem coating ingredients catalog (coatings.specialchem.com).
    89,134+ ingredients. No public API — requires web scraping.
    """

    BASE_URL = "https://coatings.specialchem.com"

    def search_product_family(self, category: str) -> List[Dict]:
        slug = self.PRODUCT_CATEGORIES.get(category, category)
        print(f"[SpecialChem] Would scrape: {self.BASE_URL}/{slug}")
        return []

    def search_by_supplier(self, supplier: str) -> List[Dict]:
        print(f"[SpecialChem] Would search supplier: {supplier}")
        return []


# ============================================================
# 4. UL PROSPECTOR  —  requires Parse API key (commercial)
# ============================================================

class ULProspectorImporter:
    """UL Prospector material database via Parse API (commercial)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.parse.bot/v1/ulprospector"

    def search_materials(self, query: str, industry: str = "Coatings") -> List[Dict]:
        if not self.api_key:
            return []
        print(f"[ULProspector] Would search: {query} in {industry}")
        return []


# ============================================================
# 5. WIKIPEDIA  —  free API, no key needed
# ============================================================

class WikipediaChemicalImporter:
    """Import chemical properties from Wikipedia via their REST API.

    Free, no API key. Good fallback when PubChem doesn't have data.
    Uses the Wikipedia action API to search and parse the HTML for infobox data.
    """

    API_URL = "https://en.wikipedia.org/w/api.php"
    HEADERS = {
        "User-Agent": "LacquerAnalyzer/1.0 (chemical database tool; contact@example.com)",
        "Accept": "application/json",
    }

    def search(self, query: str) -> List[Dict]:
        """Search Wikipedia for chemical articles. Returns list of {title, page_id, snippet}."""
        import requests
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 10,
            "format": "json",
            "srwhat": "text",
        }
        try:
            resp = requests.get(self.API_URL, params=params, headers=self.HEADERS, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for hit in data.get("query", {}).get("search", []):
                results.append({
                    "title": hit["title"],
                    "page_id": hit["pageid"],
                    "snippet": hit.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", ""),
                })
            return results
        except Exception:
            return []

    def get_chemical_properties(self, title: str) -> Optional[Dict]:
        """Fetch a Wikipedia page and extract chemical properties from the infobox HTML."""
        import requests
        import re
        from bs4 import BeautifulSoup

        try:
            safe = title.replace(" ", "_")
            params = {
                "action": "parse",
                "page": safe,
                "prop": "text",
                "section": 0,
                "format": "json",
            }
            resp = requests.get(self.API_URL, params=params, headers=self.HEADERS, timeout=5)
            if resp.status_code != 200:
                return None
            data = resp.json()
            html = data.get("parse", {}).get("text", {}).get("*", "")
            if not html:
                return None

            props = {
                "name": title,
                "source": "wikipedia",
            }

            soup = BeautifulSoup(html, "lxml")
            infobox = soup.find("table", class_=re.compile(r"infobox", re.I))
            if not infobox:
                return None

            # Wikipedia infobox has labels in <td> with the value in the next sibling <td>
            for row in infobox.find_all("tr"):
                tds = row.find_all("td")
                if len(tds) < 2:
                    continue
                # Label is in the first td, value in the second td
                label = tds[0].get_text(" ", strip=True).lower()
                value = tds[1].get_text(" ", strip=True)

                if "cas number" in label:
                    cas_m = re.search(r'(\d{2,7}-\d{2}-\d)', value)
                    if cas_m:
                        props["cas"] = cas_m.group(1)
                elif "chemical formula" in label or label in ("formula",):
                    cleaned = re.sub(r'\s+', '', value)  # remove spaces in formula
                    props["formula"] = cleaned
                elif "molar mass" in label:
                    mw_m = re.search(r'([\d.]+)', value)
                    if mw_m:
                        props["mw"] = mw_m.group(1)
                elif label == "density":
                    den_m = re.search(r'([\d.]+)', value)
                    if den_m:
                        props["density"] = den_m.group(1)
                elif "boiling point" in label:
                    bp_m = re.search(r'([\d.−-]+)\s*°?C', value)
                    if bp_m:
                        props["bp"] = bp_m.group(1).replace("−", "-")
                elif "melting point" in label:
                    mp_m = re.search(r'([\d.−-]+)\s*°?C', value)
                    if mp_m:
                        props["mp"] = mp_m.group(1).replace("−", "-")
                elif "flash point" in label:
                    fp_m = re.search(r'([\d.−-]+)\s*°?C', value)
                    if fp_m:
                        props["flash_point"] = fp_m.group(1).replace("−", "-")

            if "cas" not in props and "formula" not in props:
                return None

            return props

        except Exception:
            return None

    def search_chemicals(self, query: str) -> List[Dict]:
        """Search and return chemical property data for the top result."""
        results = self.search(query)
        chemicals = []
        for r in results:
            props = self.get_chemical_properties(r["title"])
            if props:
                chemicals.append(props)
            if len(chemicals) >= 5:
                break
        return chemicals


# ============================================================
# 6. SAVE TO CUSTOM INGREDIENTS
# ============================================================

def save_to_custom_ingredients(
    name: str,
    category: str,
    properties: dict = None,
    config_dir: str = "config",
) -> bool:
    """Add a new ingredient to custom_ingredients.yaml.

    Args:
        name: Ingredient name.
        category: One of 'resins', 'solvents', 'additives', 'pigments'.
        properties: Dict of additional properties (cas, formula, mw, etc.).
        config_dir: Path to config directory.

    Returns:
        True if saved successfully.
    """
    path = Path(config_dir) / "custom_ingredients.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = {}
    if path.exists():
        with open(path) as f:
            existing = yaml.safe_load(f) or {}

    if category not in existing:
        existing[category] = []

    # Auto-generate ID
    prefixes = {"resins": "RES", "solvents": "SOL", "additives": "ADD", "pigments": "PIG"}
    prefix = prefixes.get(category, "CUS")
    existing_ids = {i.get("id", "") for i in existing.get(category, [])}
    counter = 1
    while f"{prefix}-C{counter:03d}" in existing_ids:
        counter += 1
    new_id = f"{prefix}-C{counter:03d}"

    entry = {
        "id": new_id,
        "name": name,
        "type": category.rstrip("s"),  # 'resins' -> 'base_resin', need mapping
    }

    # Fix the type field
    type_map = {
        "resins": "base_resin",
        "solvents": "active_solvent",
        "additives": "leveling",
        "pigments": "white_pigment",
    }
    entry["type"] = type_map.get(category, "additive")

    if properties:
        # Map common property names
        prop_map = {
            "cas": "cas_number",
            "formula": "chemical_formula",
            "mw": "molecular_weight",
            "density": "density_g_cm3",
            "bp": "boiling_point_c",
            "mp": "melting_point_c",
            "flash_point": "flash_point_c",
            "smiles": "smiles",
        }
        for src_key, dest_key in prop_map.items():
            if properties.get(src_key):
                entry[dest_key] = properties[src_key]
        if properties.get("notes"):
            entry["notes"] = properties["notes"]

    existing[category].append(entry)

    with open(path, "w") as f:
        yaml.dump(existing, f, default_flow_style=False, allow_unicode=True)

    return True


# ============================================================
# 7. INGEST PIPELINE
# ============================================================

def run_ingest_pipeline(
    config_dir: str = "config",
    output_path: str = "data/ingested_knowledge.yaml",
    scrape_lathe_trolls: bool = True,
    use_pubchem: bool = False,
    lathe_trolls_keywords: List[str] = None,
) -> Dict:
    """Run the full ingestion pipeline.

    Returns dict with summary of what was ingested.
    """
    result = {"lathe_trolls_posts": 0, "pubchem_enriched": 0}
    if lathe_trolls_keywords is None:
        lathe_trolls_keywords = [
            "nitrocellulose", "butyl acetate", "silver nitrate",
            "lacquer formulation", "castor oil",
        ]

    if scrape_lathe_trolls:
        scraper = LatheTrollsScraper(auth_state_path="config/auth_state.json")
        posts = scraper.scrape_seed_threads()
        ingredients = scraper.extract_ingredients_from_posts(posts)
        scraper.export_to_yaml(posts, output_path)
        result["lathe_trolls_posts"] = len(posts)
        result["ingredients_found"] = len(ingredients)

    if use_pubchem:
        importer = PubChemImporter()
        loader = __import__('workflow.ingredients', fromlist=['IngredientLoader'])
        loader = loader.IngredientLoader(config_dir)
        ingredients = loader.load_all()
        enriched = importer.bulk_enrich(ingredients)
        result["pubchem_enriched"] = len(enriched)

    return result
