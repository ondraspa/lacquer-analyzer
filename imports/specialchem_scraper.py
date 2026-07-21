"""Buscador multi-fuente de ingredientes para recubrimientos.

Fuentes (en orden de prioridad):
  1. PigmentDatabase local — 25 pigmentos conocidos
  2. PubChem API — datos químicos (gratuito, fiable, sin WAF)
  3. Wikipedia API — compuestos conocidos
  4. SpecialChem (coatings.specialchem.com) — 89,000+ ingredientes comerciales
     (protegido por Cloudflare/Imperva; requiere cookies manuales o fallback a requests)
"""

import json
import logging
import os
import re
import time
from typing import Dict, List, Optional, Any
from urllib.parse import quote

logger = logging.getLogger("ingredient_search")

COOKIE_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "specialchem_auth.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _load_specialchem_cookies() -> Dict[str, str]:
    """Carga cookies de SpecialChem guardadas manualmente."""
    try:
        if os.path.exists(COOKIE_PATH):
            with open(COOKIE_PATH) as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading SpecialChem cookies: {e}")
    return {}


class ChemicalIngredientSearch:
    """Buscador multi-fuente de ingredientes para recubrimientos."""

    SPECIALCHEM_BASE = "https://coatings.specialchem.com"

    def __init__(self):
        self._pigment_db = None
        self._rsc_catalog = None

    # ── RSC Catalog Cache ───────────────────────────────────────

    def _ensure_rsc_catalog(self):
        """Carga el catálogo de familias de productos de SpecialChem desde el RSC."""
        if self._rsc_catalog is not None:
            return self._rsc_catalog

        import requests

        self._rsc_catalog = []
        try:
            url = f"{self.SPECIALCHEM_BASE}/coatings/selectors"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                return self._rsc_catalog

            chunks = re.findall(
                r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', resp.text
            )
            decoded = ""
            for c in chunks:
                try:
                    decoded += c.encode().decode("unicode_escape")
                except Exception:
                    decoded += c

            for match in re.finditer(
                r'\{"name":"([^"]+)","count":(\d+),"slug":"([^"]+)"\}',
                decoded,
            ):
                name = match.group(1)
                count = int(match.group(2))
                slug = match.group(3)
                prefix = slug.split("-")[0] if "-" in slug else slug
                self._rsc_catalog.append({
                    "name": name,
                    "count": count,
                    "slug": slug,
                    "url": f"{self.SPECIALCHEM_BASE}/coatings/selectors?{prefix}={slug}",
                })
            logger.info(f"Cargadas {len(self._rsc_catalog)} familias de productos de SpecialChem")
        except Exception as e:
            logger.warning(f"Error cargando catálogo SpecialChem: {e}")

        return self._rsc_catalog

    # ── pigment DB ──────────────────────────────────────────────

    def _get_pigment_db(self):
        if self._pigment_db is None:
            try:
                from materials import PigmentDatabase
                self._pigment_db = PigmentDatabase()
            except ImportError:
                self._pigment_db = False
        return self._pigment_db if self._pigment_db else None

    def _search_pigment_db(self, query: str) -> List[Dict]:
        db = self._get_pigment_db()
        if db is None:
            return []
        results = db.search(query)
        return [{
            "name": p.get("ci_name", ""),
            "supplier": p.get("common_names", ""),
            "description": f"C.I. Number: {p.get('ci_number', '')}, "
                           f"Clase: {p.get('chemical_class', '')}, "
                           f"Nombres comerciales: {p.get('trade_names', '')}",
            "source": "pigment_db",
            "url": "",
            "properties": {
                "ci_name": p.get("ci_name", ""),
                "ci_number": p.get("ci_number", ""),
                "common_names": p.get("common_names", ""),
                "trade_names": p.get("trade_names", ""),
                "chemical_class": p.get("chemical_class", ""),
            },
        } for p in results]

    # ── PubChem API ─────────────────────────────────────────────

    def _search_pubchem(self, query: str) -> List[Dict]:
        import requests
        clean = query.strip()
        if not clean:
            return []

        # Try direct name lookup
        try:
            url = (
                f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
                f"{quote(clean)}/property/"
                f"MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName,"
                f"XLogP,HBondDonorCount,HBondAcceptorCount,"
                f"RotatableBondCount,MonoisotopicMass/JSON"
            )
            resp = requests.get(url, headers=HEADERS, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                props = data["PropertyTable"]["Properties"][0]
                return [{
                    "name": props.get("IUPACName", props.get("CID", clean)),
                    "supplier": "PubChem",
                    "description": (
                        f"Fórmula: {props.get('MolecularFormula', '?')}, "
                        f"MW: {props.get('MolecularWeight', '?')}, "
                        f"XLogP: {props.get('XLogP', '?')}"
                    ),
                    "source": "pubchem",
                    "url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{props['CID']}",
                    "properties": props,
                }]
        except requests.RequestException:
            pass
        except (KeyError, ValueError, IndexError):
            pass

        # Try similarity/substructure search
        try:
            url = (
                f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/"
                f"name/{quote(clean)}/cids/TXT"
            )
            resp = requests.get(url, headers=HEADERS, timeout=8)
            if resp.status_code == 200:
                cids = resp.text.strip().split()
                if cids:
                    cid = cids[0]
                    url2 = (
                        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/"
                        f"{cid}/property/"
                        f"MolecularFormula,MolecularWeight,CanonicalSMILES,"
                        f"IUPACName,XLogP/JSON"
                    )
                    resp2 = requests.get(url2, headers=HEADERS, timeout=8)
                    if resp2.status_code == 200:
                        props = resp2.json()["PropertyTable"]["Properties"][0]
                        return [{
                            "name": props.get("IUPACName", clean),
                            "supplier": "PubChem",
                            "description": (
                                f"Fórmula: {props.get('MolecularFormula', '?')}, "
                                f"MW: {props.get('MolecularWeight', '?')}"
                            ),
                            "source": "pubchem",
                            "url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
                            "properties": props,
                        }]
        except requests.RequestException:
            pass
        except (KeyError, ValueError, IndexError):
            pass

        return []

    # ── Wikipedia API ───────────────────────────────────────────

    def _search_wikipedia(self, query: str) -> List[Dict]:
        import requests
        clean = query.strip()
        if not clean:
            return []

        try:
            # Search for the term
            url = (
                "https://en.wikipedia.org/w/api.php?"
                f"action=query&list=search&srsearch={quote(clean)}%20chemical&"
                f"format=json&srlimit=5"
            )
            resp = requests.get(url, headers=HEADERS, timeout=8)
            if resp.status_code != 200:
                return []

            data = resp.json()
            results = []
            for page in data.get("query", {}).get("search", [])[:3]:
                title = page["title"]
                snippet = re.sub(r"<[^>]+>", "", page.get("snippet", ""))
                results.append({
                    "name": title,
                    "supplier": "Wikipedia",
                    "description": snippet[:300],
                    "source": "wikipedia",
                    "url": f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}",
                    "properties": {},
                })

            # Try direct page lookup for exact match
            url2 = (
                "https://en.wikipedia.org/w/api.php?"
                f"action=query&prop=extracts&exintro=&explaintext=&"
                f"titles={quote(clean)}&format=json"
            )
            resp2 = requests.get(url2, headers=HEADERS, timeout=8)
            if resp2.status_code == 200:
                pages = resp2.json().get("query", {}).get("pages", {})
                for pid, pdata in pages.items():
                    if pid != "-1" and "extract" in pdata:
                        extract = pdata["extract"][:500]
                        if not any(r["name"] == pdata["title"] for r in results):
                            results.insert(0, {
                                "name": pdata["title"],
                                "supplier": "Wikipedia",
                                "description": extract[:300],
                                "source": "wikipedia",
                                "url": f"https://en.wikipedia.org/wiki/{quote(pdata['title'].replace(' ', '_'))}",
                                "properties": {},
                            })
            return results
        except requests.RequestException:
            return []
        except (KeyError, ValueError) as e:
            logger.warning(f"Wikipedia error: {e}")
            return []

    # ── SpecialChem (cookie-based or fallback) ──────────────────

    def _check_specialchem(self) -> bool:
        """Verifica si tenemos cookies válidas para SpecialChem."""
        cookies = _load_specialchem_cookies()
        if cookies:
            return True
        # Also check playwright auth state
        auth_path = os.path.join(os.path.dirname(__file__), "..", "config", "specialchem_auth_state.json")
        if os.path.exists(auth_path):
            return True
        return False

    def _specialchem_session(self):
        """Crea una session de requests con cookies de SpecialChem."""
        import requests
        sess = requests.Session()
        sess.headers.update(HEADERS)

        cookies = _load_specialchem_cookies()
        for key, value in cookies.items():
            sess.cookies.set(key, value)

        return sess

    def _search_specialchem(self, query: str, max_results: int = 10) -> List[Dict]:
        """Busca en SpecialChem con cookies o fallback a requests simple."""
        import requests
        from bs4 import BeautifulSoup

        clean = query.strip()
        if len(clean) < 2:
            return []

        sess = self._specialchem_session()
        url = f"{self.SPECIALCHEM_BASE}/search?q={quote(clean)}"

        try:
            resp = sess.get(url, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"SpecialChem HTTP {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            results = []

            # Try to parse RSC payload for product data
            results = self._parse_rsc_payload(resp.text, clean, max_results)

            if not results:
                # Fallback: look for product-like links
                results = self._fallback_specialchem(soup, max_results)

            # Tag results
            for r in results:
                r["source"] = "specialchem"

            return results

        except requests.Timeout:
            logger.warning("SpecialChem timeout")
            return []
        except Exception as e:
            logger.warning(f"SpecialChem error: {e}")
            return []

    def _parse_rsc_payload(self, html: str, query: str, max_results: int) -> List[Dict]:
        """Intenta extraer datos de productos del payload RSC de Next.js.

        El RSC (React Server Components) usa un formato de serialización propio
        con entradas como: {"name":"EPON™","count":"63","slug":"tr-epon"}
        """
        import json

        results = []
        clean = query.lower()

        # Extract all RSC chunks and decode them
        chunks = re.findall(
            r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', html
        )
        decoded = ""
        for c in chunks:
            try:
                decoded += c.encode().decode("unicode_escape")
            except Exception:
                decoded += c

        if not decoded:
            return results

        # Extract structured entries: {"name":"...","count":...,"slug":"..."}
        # These are product family catalog entries from the RSC payload
        for entry_match in re.finditer(
            r'\{"name":"([^"]+)","count":(\d+),"slug":"([^"]+)"\}',
            decoded,
        ):
            name = entry_match.group(1)
            count = int(entry_match.group(2))
            slug = entry_match.group(3)

            if clean in name.lower() or clean in slug.lower():
                if not any(r["name"] == name for r in results):
                    prefix = slug.split("-")[0] if "-" in slug else slug
                    url = f"{self.SPECIALCHEM_BASE}/coatings/selectors?{prefix}={slug}"
                    results.append({
                        "name": name,
                        "supplier": "SpecialChem",
                        "description": f"{count} productos en esta categoría",
                        "url": url,
                        "source": "specialchem",
                        "properties": {"slug": slug, "count": count, "type": "product_family"},
                    })
                    if len(results) >= max_results:
                        return results

        if results:
            return results

        # Fallback: look for product-like links
        for match in re.finditer(r'"productName":"([^"]+)"', decoded):
            name = match.group(1)
            if clean in name.lower():
                if not any(r["name"] == name for r in results):
                    results.append({
                        "name": name,
                        "supplier": "",
                        "description": "",
                        "url": "",
                        "source": "specialchem",
                        "properties": {},
                    })
                    if len(results) >= max_results:
                        break

        return results

    def _fallback_specialchem(self, soup, max_results: int) -> List[Dict]:
        """Fallback: parse any navigation links that look product-related."""
        results = []
        for a in soup.select("a[href*='product']"):
            name = a.get_text(strip=True)
            if not name or len(name) < 3:
                continue
            href = a.get("href", "")
            if href and not href.startswith("http"):
                href = self.SPECIALCHEM_BASE + href
            if not any(r["url"] == href for r in results):
                results.append({
                    "name": name,
                    "supplier": "",
                    "description": "",
                    "url": href,
                    "source": "specialchem",
                    "properties": {},
                })
                if len(results) >= max_results:
                    break
        return results

    def get_product_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """Obtiene la ficha técnica detallada desde SpecialChem (requiere cookies)."""
        import requests
        from bs4 import BeautifulSoup

        sess = self._specialchem_session()

        try:
            resp = sess.get(url, timeout=12)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            data = {"url": url}

            name_el = soup.select_one("h1, .product-title, .title")
            data["name"] = name_el.get_text(strip=True) if name_el else ""

            supp_el = soup.select_one(".supplier a, .brand a, .manufacturer-name")
            data["supplier"] = supp_el.get_text(strip=True) if supp_el else ""

            props = {}
            for row in soup.select("table.properties tr, .specs tr, .data-table tr"):
                cells = row.select("td, th")
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).rstrip(":")
                    val = cells[1].get_text(strip=True)
                    if key and val:
                        props[key] = val
            data["properties"] = props

            desc_el = soup.select_one(
                ".description, #description, .product-description"
            )
            data["description"] = desc_el.get_text(strip=True)[:1000] if desc_el else ""
            data["source"] = "specialchem"

            return data

        except Exception as e:
            logger.warning(f"SpecialChem detail error for {url}: {e}")
            return None

    # ── Public API ──────────────────────────────────────────────

    def search(self, query: str, max_results_per_source: int = 5) -> List[Dict]:
        """Busca un ingrediente en todas las fuentes disponibles.

        Retorna lista de resultados combinados, cada uno con:
          name, supplier, description, source, url, properties
        """
        clean = query.strip()
        if not clean or len(clean) < 2:
            return []

        all_results = []

        # 1. Pigment DB (local, instant)
        all_results.extend(self._search_pigment_db(clean))

        # 2. PubChem API
        all_results.extend(self._search_pubchem(clean))

        # 3. Wikipedia
        all_results.extend(self._search_wikipedia(clean))

        # 4. SpecialChem (catálogo RSC de familias de productos)
        catalog = self._ensure_rsc_catalog()
        for entry in catalog:
            if clean in entry["name"].lower() or clean in entry["slug"].lower():
                all_results.append({
                    "name": entry["name"],
                    "supplier": "SpecialChem",
                    "description": f"{entry['count']} productos — familias de recubrimientos",
                    "source": "specialchem",
                    "url": entry["url"],
                    "properties": {
                        "slug": entry["slug"],
                        "count": entry["count"],
                        "type": "product_family",
                    },
                })
                if len([r for r in all_results if r["source"] == "specialchem"]) >= max_results_per_source:
                    break

        # 5. SpecialChem (cookie-based — para datos detallados de productos)
        if self._check_specialchem():
            try:
                sc_results = self._search_specialchem(
                    clean, max_results_per_source
                )
                all_results.extend(sc_results)
            except Exception as e:
                logger.warning(f"SpecialChem cookie-based search error: {e}")

        return all_results

    @staticmethod
    def format_result(r: Dict) -> str:
        lines = [f"  Producto: {r.get('name', '?')}"]
        lines.append(f"  Fuente: {r.get('source', '?')}")
        if r.get("supplier"):
            lines.append(f"  Proveedor: {r['supplier']}")
        if r.get("description"):
            lines.append(f"  Descripción: {r['description'][:200]}")
        if r.get("url"):
            lines.append(f"  URL: {r['url']}")
        props = r.get("properties", {})
        if props:
            for k, v in list(props.items())[:6]:
                if v and k not in ("CID",):
                    lines.append(f"  {k}: {v}")
        return "\n".join(lines) + "\n"


# ── Legacy alias ────────────────────────────────────────────────
class SpecialChemScraper:
    """Legacy wrapper. Usa ChemicalIngredientSearch internamente."""

    def __init__(self):
        self._impl = ChemicalIngredientSearch()

    def search_by_name(self, query: str, max_results: int = 20) -> List[Dict]:
        return self._impl.search(query, max_results_per_source=max_results)

    def get_product_detail(self, url: str) -> Optional[Dict[str, Any]]:
        return self._impl.get_product_detail(url)

    @staticmethod
    def format_result(r: Dict) -> str:
        return ChemicalIngredientSearch.format_result(r)
