"""User correction store for LLM answers."""
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
import json


@dataclass
class Correction:
    """A user correction to an LLM answer."""
    question: str
    wrong_answer: str
    correct_answer: str
    source: str = "user_feedback"

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "wrong_answer": self.wrong_answer,
            "correct_answer": self.correct_answer,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Correction":
        return cls(
            question=d.get("question", ""),
            wrong_answer=d.get("wrong_answer", ""),
            correct_answer=d.get("correct_answer", ""),
            source=d.get("source", "user_feedback"),
        )


class CorrectionStore:
    """Persistent storage for user corrections to LLM answers.

    Corrections are saved to ``data/corrections.json`` and loaded
    at startup. When the user corrects an answer, it is stored as a
    new knowledge entry so future queries can return the corrected
    information.
    """

    def __init__(self, path: str = "data/corrections.json"):
        self.path = Path(path)
        self.corrections: List[Correction] = []
        self.load()

    def load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                self.corrections = [Correction.from_dict(d) for d in data]
            except Exception:
                self.corrections = []

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(
            [c.to_dict() for c in self.corrections], indent=2
        ))

    def add(self, question: str, wrong_answer: str, correct_answer: str):
        self.corrections.append(Correction(question, wrong_answer, correct_answer))
        self.save()

    def find_match(self, question: str) -> Optional[Correction]:
        """Return the most similar correction, if any."""
        q = question.lower().strip()
        for c in self.corrections:
            if q == c.question.lower().strip():
                return c
            # Simple word overlap
            q_words = set(q.split())
            c_words = set(c.question.lower().split())
            overlap = len(q_words & c_words)
            if overlap >= min(len(q_words), len(c_words)) * 0.7 and overlap >= 2:
                return c
        return None
