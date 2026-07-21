"""Local LLM client for communicating with LM Studio / OpenAI-compatible APIs."""
from typing import List, Optional
from .corrections import CorrectionStore
from knowledge.base import KnowledgeEntry


DEFAULT_API_URL = "http://localhost:1234/v1"
DEFAULT_MODEL = "google/gemma-4-26b-a4b-qat"


class LocalLLM:
    """Wrapper around LM Studio's OpenAI-compatible API."""

    def __init__(self, api_url: str = DEFAULT_API_URL, model: str = DEFAULT_MODEL):
        self.api_url = api_url.rstrip("/")
        self.model = model
        self.corrections = CorrectionStore()
        self._active_agent = None

    def apply_agent(self, agent) -> None:
        """Configure this LLM instance from an Agent config."""
        self.api_url = agent.api_url.rstrip("/")
        self.model = agent.model
        self._active_agent = agent

    @property
    def active_agent(self):
        return self._active_agent

    def list_models(self) -> List[str]:
        """Fetch available models from the API."""
        try:
            import requests
            resp = requests.get(f"{self.api_url}/models", timeout=5)
            if resp.status_code == 200:
                return [m["id"] for m in resp.json().get("data", [])]
        except Exception:
            pass
        return []

    def ask(self, question: str, context: str = "",
            max_tokens: int = 1024, temperature: float = 0.3,
            context_chars: int = 24000,
            system_prompt: str = "") -> str:
        """Ask a question with optional context. Returns the answer text.

        Checks user corrections first — if a matching correction exists,
        the corrected answer is returned directly without calling the LLM.

        If *system_prompt* is provided it overrides the default prompt.
        The string '{context}' in the prompt is replaced with the actual context.
        """
        # Check corrections first
        match = self.corrections.find_match(question)
        if match:
            return f"[Corrected based on user feedback]\n{match.correct_answer}"

        import requests
        messages = []

        if context:
            sp = system_prompt or (
                "You are an expert on lacquer disc chemistry, silvering, "
                "and electroplating for vinyl record mastering. "
                "Answer questions based ONLY on the forum knowledge provided below. "
                "If the information isn't in the provided context, say so.\n\n"
                "FORUM KNOWLEDGE:\n{context}"
            )
            sp = sp.replace("{context}", context[:context_chars])
            messages.append({
                "role": "system",
                "content": sp,
            })

        messages.append({
            "role": "user",
            "content": question,
        })

        try:
            resp = requests.post(
                f"{self.api_url}/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            msg = data["choices"][0]["message"]
            answer = msg.get("content", "")
            return answer.strip() if answer else "(no response)"
        except requests.Timeout:
            return "ERROR: Request timed out (model may be too slow, try a smaller model)"
        except Exception as e:
            return f"ERROR: {e}"

    def is_available(self) -> bool:
        """Check if LM Studio API is reachable."""
        try:
            import requests
            resp = requests.get(f"{self.api_url}/models", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    # ── Knowledge sanitization ──────────────────────────────────

    def sanitize_entry(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        """Send one knowledge entry to the LLM for cleanup and standardization.

        The LLM fixes typos, standardizes units/chemical names, removes
        irrelevant noise, and returns a cleaner version.
        """
        prompt = (
            "Clean up and standardize the following technical knowledge entry "
            "about lacquer chemistry, silvering, or plating.\n"
            "- Fix typos and formatting\n"
            "- Standardize chemical names and units (mL → ml, °C, etc.)\n"
            "- Remove irrelevant noise\n"
            "- Keep all technical information intact\n"
            "- Return ONLY the cleaned text, no explanations\n\n"
            f"Category: {entry.category}\n"
            f"Title: {entry.title}\n"
            f"Content:\n{entry.content[:4000]}"
        )
        try:
            cleaned = self.ask(question=prompt, max_tokens=2000, temperature=0.1)
            if cleaned.startswith("ERROR"):
                return entry
            return KnowledgeEntry(
                source=entry.source,
                title=entry.title,
                content=cleaned,
                category=entry.category,
                keywords=entry.keywords,
                image_paths=list(entry.image_paths),
            )
        except Exception:
            return entry

    def sanitize_batch(self, entries: List[KnowledgeEntry],
                       progress_callback=None) -> List[KnowledgeEntry]:
        """Sanitize a batch of entries, returning cleaned versions."""
        result = []
        for i, entry in enumerate(entries):
            if progress_callback:
                progress_callback(f"Sanitizing {i+1}/{len(entries)}: {entry.title[:40]}...")
            cleaned = self.sanitize_entry(entry)
            result.append(cleaned)
        return result
