"""RAG settings persistence."""
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
import json
from .agents import Agent, DEFAULT_AGENTS


@dataclass
class RAGSettings:
    api_url: str = "http://localhost:1234/v1"
    model: str = ""
    max_tokens: int = 1024
    temperature: float = 0.3
    top_k: int = 5
    context_chars: int = 24000
    chunk_size: int = 1500
    show_rag_details: bool = False
    scrape_search_max_pages: int = 2
    scrape_forum_max_pages: int = 5
    scrape_mirror_max_pages: int = 3
    forum_cache_dir: str = "data/forum_cache"
    system_prompt: str = "You are an expert on lacquer disc chemistry, silvering, and electroplating for vinyl record mastering.\n\nFORUM KNOWLEDGE:\n{context}"
    agents: List[Agent] = field(default_factory=lambda: list(DEFAULT_AGENTS))

    _path: Path = Path("config/rag_settings.json")

    def save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "api_url": self.api_url,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_k": self.top_k,
            "context_chars": self.context_chars,
            "chunk_size": self.chunk_size,
            "show_rag_details": self.show_rag_details,
            "scrape_search_max_pages": self.scrape_search_max_pages,
            "scrape_forum_max_pages": self.scrape_forum_max_pages,
            "scrape_mirror_max_pages": self.scrape_mirror_max_pages,
            "forum_cache_dir": self.forum_cache_dir,
            "system_prompt": self.system_prompt,
            "agents": [{"name": a.name, "domain": a.domain, "model": a.model, "api_url": a.api_url, "system_prompt": a.system_prompt} for a in self.agents],
        }
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, path: str = "config/rag_settings.json") -> "RAGSettings":
        p = Path(path)
        if not p.exists():
            s = cls()
            s._path = p
            return s
        try:
            data = json.loads(p.read_text())
            agents_data = data.pop("agents", [])
            s = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            s._path = p
            s.agents = [Agent(**a) for a in agents_data] if agents_data else list(DEFAULT_AGENTS)
            return s
        except Exception:
            return cls()
