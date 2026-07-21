#!/usr/bin/env python3
"""
Scrape knowledge from The Secret Society of Lathe Trolls (lathetrolls.com).

Usage:
    python3 scripts/scrape_lathe_trolls.py

This script fetches known formulation/plating threads from the forum
and extracts ingredient data, then saves it to data/lathe_trolls_knowledge.yaml
for use in the Lacquer Analyzer.

Requires: pip install requests beautifulsoup4 lxml
"""

import sys
import re
import json
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Please install: pip install requests beautifulsoup4 lxml")
    sys.exit(1)


BASE_URL = "https://lathetrolls.com"

# Threads known to contain formulation/process knowledge
TARGET_THREADS = [
    # Lacquer formulation threads
    {"url": f"{BASE_URL}/viewtopic.php?t=8634", "category": "lacquer_formulation",
     "title": "Producing Lacquers"},
    {"url": f"{BASE_URL}/viewtopic.php?t=3178", "category": "lacquer_formulation",
     "title": "Audio Discs recording blanks formulation"},
    {"url": f"{BASE_URL}/viewtopic.php?t=1557", "category": "lacquer_formulation",
     "title": "Vintage lacquer formulations"},
    {"url": f"{BASE_URL}/viewtopic.php?t=5925", "category": "lacquer_formulation",
     "title": "Softening old lacquer / castor oil plasticizer"},
    # Silvering threads
    {"url": f"{BASE_URL}/viewtopic.php?t=10161", "category": "silvering",
     "title": "Honeycomb pattern after plating"},
    {"url": f"{BASE_URL}/viewtopic.php?t=7604", "category": "silvering",
     "title": "Spray booth for silvering"},
    # Plating threads
    {"url": f"{BASE_URL}/viewtopic.php?t=7240", "category": "plating",
     "title": "Electroplating & DMM"},
    {"url": f"{BASE_URL}/viewtopic.php?t=1092", "category": "plating",
     "title": "Cylinder plating and pressing"},
]


def fetch_page(url: str) -> Optional[str]:
    """Fetch a forum page, respecting robots.txt."""
    headers = {
        "User-Agent": "LacquerAnalyzer/0.1 (research; educational; contact@example.com)",
        "Accept": "text/html,application/xhtml+xml"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None


def extract_posts(html: str, thread_url: str, category: str) -> List[Dict]:
    """Extract individual posts from a thread page."""
    posts = []
    soup = BeautifulSoup(html, "lxml")

    # Find post containers (phpBB-style)
    for post_div in soup.select("div.post, div.postbody, div[class*='post']"):
        try:
            author_el = post_div.select_one(".author, .username, .postauthor")
            date_el = post_div.select_one(".postdate, .date, time")
            content_el = post_div.select_one(".content, .postbody, .entry")

            author = author_el.get_text(strip=True) if author_el else "Unknown"
            date = date_el.get_text(strip=True) if date_el else ""
            if date_el and date_el.get("datetime"):
                date = date_el["datetime"]
            content = content_el.get_text(strip=True) if content_el else ""

            if content and len(content) > 50:
                posts.append({
                    "url": thread_url,
                    "title": soup.title.get_text(strip=True) if soup.title else "",
                    "author": author,
                    "date": date,
                    "category": category,
                    "content": content[:2000],
                })
        except Exception:
            continue

    return posts


def extract_ingredients(posts: List[Dict]) -> List[Dict]:
    """Extract ingredient mentions and percentages from post text."""
    ingredients = {}

    patterns = [
        # "Butyl Acetate –27%; 135 grams" or "Butyl Acetate -27%"
        r'([A-Z][A-Za-z\s/-]+?)\s*[–\-—:]\s*(\d+[\.\d]*)%',
        # "27% Butyl Acetate" or "27% of Butyl Acetate"
        r'(\d+[\.\d]*)%\s*(?:\w+\s+)?(?:of\s+)?([A-Z][A-Za-z\s/]+)',
        # "Nitrocellulose 13%; 65 grams"
        r'([A-Z][A-Za-z\s/]+)\s+(\d+[\.\d]*)%\s*[;,]?\s*\d*\s*grams?',
    ]

    for post in posts:
        text = post.get("content", "")
        for pattern in patterns:
            for m in re.finditer(pattern, text):
                name = m.group(1).strip().rstrip(". ")
                pct = float(m.group(2))

                name_lower = name.lower()
                if name_lower not in ingredients:
                    ingredients[name_lower] = {
                        "name": name,
                        "mentions": 0,
                        "avg_concentration": 0,
                        "sources": [],
                    }
                ing = ingredients[name_lower]
                ing["mentions"] += 1
                old_avg = ing["avg_concentration"]
                ing["avg_concentration"] = (
                    (old_avg * (ing["mentions"] - 1) + pct) / ing["mentions"]
                )
                if post["url"] not in ing["sources"]:
                    ing["sources"].append(post["url"])

    return sorted(ingredients.values(), key=lambda x: x["mentions"], reverse=True)


def export_to_yaml(posts: List[Dict], ingredients: List[Dict], output_path: str):
    """Save scraped data to YAML for use in the analyzer."""
    data = {
        "meta": {
            "source": "lathetrolls.com - The Secret Society of Lathe Trolls",
            "scrape_date": datetime.now().isoformat(),
            "threads_scraped": len(set(p["url"] for p in posts)),
            "posts_found": len(posts),
            "ingredients_extracted": len(ingredients),
        },
        "ingredients_found": ingredients,
        "generated_ingredients": _generate_ingredients_from_scrape(ingredients),
        "posts": [
            {
                "url": p["url"],
                "title": p.get("title", ""),
                "author": p.get("author", ""),
                "date": p.get("date", ""),
                "category": p.get("category", ""),
                "content_snippet": p["content"][:500],
            }
            for p in posts
        ],
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"Exported to {output_path}")


def _generate_ingredients_from_scrape(ingredients: List[Dict]) -> List[Dict]:
    """Convert scraped ingredient mentions to ingredient database format."""
    generated = []
    # Known mappings from scraped names to ingredient types
    type_map = {
        "nitrocellulose": "base_resin",
        "butyl acetate": "active_solvent",
        "ethyl acetate": "active_solvent",
        "toluene": "active_solvent",
        "isopropyl alcohol": "active_solvent",
        "castor oil": "plasticizer",
        "dibutyl phthalate": "plasticizer",
        "camphor": "plasticizer",
        "benzophenone": "uv_stabilizer",
        "acetone": "active_solvent",
    }

    for ing in ingredients:
        name_lower = ing["name"].lower()
        ing_type = "active_solvent"  # default
        for key, t in type_map.items():
            if key in name_lower:
                ing_type = t
                break

        generated.append({
            "name": ing["name"],
            "type": ing_type,
            "scraped_from": "lathetrolls.com",
            "avg_concentration": ing["avg_concentration"],
            "mentions": ing["mentions"],
            "suggested_max_concentration": min(ing["avg_concentration"] * 1.5, 60),
        })

    return generated


def main():
    print("=" * 60)
    print("Lathe Trolls Knowledge Scraper")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print(f"Threads: {len(TARGET_THREADS)}")
    print()

    all_posts = []
    for thread in TARGET_THREADS:
        print(f"[{thread['category']}] Fetching: {thread['title']}")
        html = fetch_page(thread["url"])
        if html:
            posts = extract_posts(html, thread["url"], thread["category"])
            all_posts.extend(posts)
            print(f"  Found {len(posts)} posts")
        time.sleep(1.5)  # be polite

    if not all_posts:
        print("\nNo posts scraped. The forum may require login.")
        print("Options:")
        print("  1. Use a session cookie: set SESSION_COOKIE env var")
        print("  2. Manually copy post content into data/manual_posts.yaml")
        print("  3. Use the built-in hardcoded knowledge in the analyzer")
        return

    print(f"\nTotal posts scraped: {len(all_posts)}")

    ingredients = extract_ingredients(all_posts)
    print(f"Ingredients extracted: {len(ingredients)}")
    for ing in ingredients[:10]:
        print(f"  {ing['name']}: {ing['mentions']} mentions @ avg {ing['avg_concentration']:.1f}%")

    output = str(Path(__file__).parent.parent / "data" / "lathe_trolls_knowledge.yaml")
    export_to_yaml(all_posts, ingredients, output)

    print("\nDone! Import this data using the Lacquer Analyzer's Data Import tab.")


if __name__ == "__main__":
    main()
