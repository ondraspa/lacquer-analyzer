"""Analyze imported data for LLM/RAG compatibility and coverage."""

from collections import Counter
from typing import List, Dict, Tuple
from knowledge.base import KnowledgeEntry


def analyze_entries(entries: List[KnowledgeEntry]) -> Dict:
    """Run a full compatibility analysis on KB entries.

    Returns a dict with:
        - summary: basic counts
        - length_analysis: short/long entry counts
        - categories: per-category breakdown
        - duplicates: list of (title, count) pairs
        - empty_entries: count of entries with no content
        - coverage: topic keyword coverage
        - readability: average content length etc.
        - rag_readiness: score /10
    """
    total = len(entries)
    if total == 0:
        return {"summary": {"total": 0, "rag_readiness": 0}}

    # Category breakdown
    cats = Counter(e.category for e in entries)

    # Length analysis
    lengths = [len(e.content) for e in entries if e.content]
    empty_entries = sum(1 for e in entries if not e.content.strip())
    very_short = sum(1 for l in lengths if 0 < l < 100)
    short = sum(1 for l in lengths if 100 <= l < 500)
    medium = sum(1 for l in lengths if 500 <= l < 2000)
    long = sum(1 for l in lengths if 2000 <= l < 5000)
    very_long = sum(1 for l in lengths if l >= 5000)

    avg_len = sum(lengths) / len(lengths) if lengths else 0
    median_len = sorted(lengths)[len(lengths)//2] if lengths else 0

    # Duplicate detection by title+source
    seen = {}
    duplicates = []
    for e in entries:
        key = (e.title.lower().strip(), e.source.lower().strip())
        seen.setdefault(key, []).append(e)
    for key, dups in seen.items():
        if len(dups) > 1:
            duplicates.append((key[0], len(dups)))

    # Coverage analysis — topic keywords
    topic_keywords = {
        "lacquer formulation": ["nitrocellulose", "castor oil", "butyl acetate",
                                 "ethyl acetate", "toluene", "acetone",
                                 "plasticizer", "resin", "solvent"],
        "substrate prep": ["aluminum", "aluminium", "degrease", "cleaning",
                            "adhesion", "surface tension", "wetting"],
        "coating": ["curtain", "burkle", "coating", "layer", "thickness",
                     "application", "flow", "spin"],
        "curing": ["cure", "drying", "solvent", "evaporation", "hardness",
                    "blush", "haze", "crosslink", "temperature"],
        "quality control": ["defect", "pinhole", "adhesion", "roughness",
                             "inspection", "orange peel", "viscosity"],
    }

    all_text = " ".join(e.content.lower() for e in entries)
    coverage = {}
    for topic, kws in topic_keywords.items():
        found = [kw for kw in kws if kw in all_text]
        coverage[topic] = {
            "found": len(found),
            "total": len(kws),
            "keywords_found": found,
        }

    # Source breakdown
    sources = Counter(
        e.source.split("/")[2] if "//" in e.source else e.source[:30]
        for e in entries
    )

    # Entries with images
    with_images = sum(1 for e in entries if e.image_paths)

    # RAG readiness score (0-10)
    score = 10
    if total < 10:
        score -= 3
    elif total < 50:
        score -= 1
    if empty_entries / max(total, 1) > 0.1:
        score -= 1
    if very_short / max(total, 1) > 0.2:
        score -= 1
    if avg_len < 200:
        score -= 1
    if len(cats) < 2:
        score -= 1
    if len(duplicates) > max(total * 0.05, 2):
        score -= 1
    score = max(0, min(10, score))

    return {
        "summary": {
            "total": total,
            "categories": len(cats),
            "sources": len(sources),
            "avg_content_length": round(avg_len, 0),
            "median_content_length": median_len,
            "with_images": with_images,
            "rag_readiness": score,
        },
        "length_analysis": {
            "empty": empty_entries,
            "very_short_<100": very_short,
            "short_100-500": short,
            "medium_500-2000": medium,
            "long_2000-5000": long,
            "very_long_>5000": very_long,
        },
        "categories": dict(cats.most_common()),
        "duplicates": duplicates[:20],
        "coverage": coverage,
        "sources": dict(sources.most_common(10)),
    }
