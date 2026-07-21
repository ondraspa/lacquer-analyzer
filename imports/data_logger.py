"""Append-only import/operation log, persisted to JSON."""

import json
import time
from pathlib import Path
from typing import List, Dict


class ImportLog:
    """Thread-safe (for casual use) append-only log of import operations.

    Each entry has:
        timestamp: float (time.time())
        action: str (e.g. "forum_mirror", "pdf_import", "markdown_import", "sanitize")
        detail: str  (free-text description)
        counts: dict (e.g. {"posts": 5, "chunks": 12})
        source: str (e.g. "lathetrolls.com", "/path/to/file.pdf")
    """

    def __init__(self, path: str = "data/import_log.json"):
        self.path = Path(path)
        self.entries: List[Dict] = []
        self._load()

    def add(self, action: str, detail: str = "",
            counts: dict = None, source: str = ""):
        entry = {
            "timestamp": time.time(),
            "action": action,
            "detail": detail,
            "counts": counts or {},
            "source": source,
        }
        self.entries.append(entry)
        self._save()

    def recent(self, n: int = 50) -> List[Dict]:
        return self.entries[-n:]

    def clear(self):
        self.entries.clear()
        if self.path.exists():
            self.path.unlink()

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                self.entries = data if isinstance(data, list) else []
            except Exception:
                self.entries = []

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.entries, indent=2))
