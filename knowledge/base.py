"""Knowledge base: storage, chunking, and retrieval of forum knowledge entries."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import json
import re
from imports.forum import ForumPost, FALLBACK_POSTS, parse_playwright_markdown


@dataclass
class KnowledgeEntry:
    """A chunk of knowledge extracted from a forum post or scanned page."""
    source: str
    title: str
    content: str
    category: str
    keywords: List[str] = field(default_factory=list)
    image_paths: List[str] = field(default_factory=list)


class ForumKnowledgeBase:
    """Build a searchable knowledge base from forum posts.

    Entries are auto-persisted to *persist_path* after every build /
    mutation so data survives restarts.
    """

    def __init__(self, cache_dir: str = "data/forum_cache", chunk_size: int = 1500,
                 persist_path: str = "data/knowledge_base.json"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = chunk_size
        self._persist_path = Path(persist_path)
        self.entries: List[KnowledgeEntry] = []
        self._built = False
        self._loading = False
        self.load()

    def build_from_posts(self, posts: List[ForumPost], category: str = "general"):
        """Build from a list of ForumPost objects."""
        self._loading = True
        self.entries.clear()
        for post in posts:
            self._add_post(post, category)
        self._built = True
        self._loading = False
        self.save()

    def build_from_fallback(self):
        """Build from built-in fallback posts."""
        self._loading = True
        self.entries.clear()
        for post in FALLBACK_POSTS:
            self._add_post(post, post.category)
        self._built = True
        self._loading = False
        self.save()

    def build_from_markdown_dir(self, directory: str, category: str = "",
                                 progress_callback=None):
        """Build from Playwright-scraped markdown files in *directory*."""
        from imports.forum import parse_playwright_markdown
        from pathlib import Path
        d = Path(directory)
        files = sorted(d.glob("*.md"))
        if not files:
            if progress_callback:
                progress_callback("No .md files found.")
            return 0
        if progress_callback:
            progress_callback(f"Scanning {len(files)} markdown files in {directory}...")
        self._loading = True
        self.entries.clear()
        count = 0
        for idx, f in enumerate(files):
            posts = parse_playwright_markdown(str(f))
            if posts:
                for post in posts:
                    self._add_post(post, category or post.category)
                    count += 1
            if progress_callback and ((idx + 1) % 100 == 0 or idx == len(files) - 1):
                progress_callback(f"  [{idx+1}/{len(files)}] {count} entries so far...")
        self._built = True
        self._loading = False
        self.save()
        if progress_callback:
            progress_callback(f"✓ Done: {count} entries from {len(files)} files")
        return count

    def append_from_markdown_dir(self, directory: str, category: str = "",
                                  progress_callback=None):
        """Append markdown files to the existing KB without clearing."""
        from imports.forum import parse_playwright_markdown
        from pathlib import Path
        d = Path(directory)
        files = sorted(d.glob("*.md"))
        if not files:
            if progress_callback:
                progress_callback("No .md files found.")
            return 0
        if progress_callback:
            progress_callback(f"Scanning {len(files)} markdown files in {directory}...")
        self._loading = True
        count = 0
        for idx, f in enumerate(files):
            posts = parse_playwright_markdown(str(f))
            if posts:
                for post in posts:
                    self._add_post(post, category or post.category)
                    count += 1
            if progress_callback and ((idx + 1) % 100 == 0 or idx == len(files) - 1):
                progress_callback(f"  [{idx+1}/{len(files)}] {count} entries so far...")
        self._loading = False
        if count:
            self._built = True
            self.save()
        if progress_callback:
            progress_callback(f"✓ Done: {count} entries")
        return count

    def _add_post(self, post: ForumPost, category: str):
        """Split a forum post into knowledge chunks and add them."""
        chunks = self._chunk_text(post.content, title=post.title)
        for chunk in chunks:
            kw = self._extract_keywords(chunk)
            self.entries.append(KnowledgeEntry(
                source=post.url,
                title=post.title,
                content=chunk,
                category=category,
                keywords=kw,
                image_paths=list(post.image_paths),
            ))

    def _chunk_text(self, text: str, title: str = "", max_chars: Optional[int] = None) -> List[str]:
        """Split text into overlapping chunks at paragraph boundaries."""
        max_chars = max_chars or self.chunk_size
        if len(text) <= max_chars:
            return [text]
        chunks = []
        paragraphs = text.split("\n\n")
        current = ""
        for para in paragraphs:
            if len(current) + len(para) < max_chars:
                current += "\n\n" + para if current else para
            else:
                if current:
                    chunks.append(current)
                current = para
        if current:
            chunks.append(current)
        return chunks

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract likely chemical/keyword terms from text."""
        common = [
            "nitrocellulose", "castor oil", "silver nitrate", "butyl acetate",
            "ethyl acetate", "toluene", "acetone", "lacquer", "silvering",
            "plating", "electroform", "stamper", "mother", "father",
            "pressing", "vinyl", "disc", "recipe", "formulation",
            "plasticizer", "resin", "solvent", "pigment", "additive",
            "nickel", "sulfamate", "copper", "silver", "conductive",
        ]
        text_lower = text.lower()
        found = set()
        for kw in common:
            if kw in text_lower:
                found.add(kw)
        chem_pattern = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
        for match in chem_pattern[:5]:
            found.add(match.lower())
        return list(found)

    def search(self, query: str, max_results: int = 5) -> List[KnowledgeEntry]:
        """Simple keyword search over the knowledge base."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for entry in self.entries:
            score = 0
            content_lower = entry.content.lower()
            for word in query_words:
                if len(word) < 3:
                    continue
                if word in content_lower:
                    score += content_lower.count(word) * 2
                if word in entry.title.lower():
                    score += 5
                if word in " ".join(entry.keywords).lower():
                    score += 3
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: -x[0])
        return [entry for _, entry in scored[:max_results]]

    @property
    def total_chunks(self) -> int:
        return len(self.entries)

    # ── Persistence ─────────────────────────────────────────────────

    def save(self):
        """Persist all entries to a JSON file (no-op while loading)."""
        if self._loading:
            return
        data = []
        for e in self.entries:
            data.append({
                "source": e.source,
                "title": e.title,
                "content": e.content,
                "category": e.category,
                "keywords": e.keywords,
                "image_paths": e.image_paths,
            })
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._persist_path.write_text(
            __import__("json").dumps(data, indent=2, ensure_ascii=False)
        )

    def load(self):
        """Load entries from the JSON persistence file."""
        if not self._persist_path.exists():
            return
        try:
            data = __import__("json").loads(self._persist_path.read_text())
            self.entries = [
                KnowledgeEntry(
                    source=e.get("source", ""),
                    title=e.get("title", ""),
                    content=e.get("content", ""),
                    category=e.get("category", ""),
                    keywords=e.get("keywords", []),
                    image_paths=e.get("image_paths", []),
                )
                for e in data
            ]
            self._built = bool(self.entries)
        except Exception:
            self._built = False
