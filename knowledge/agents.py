"""Agent configuration dataclass for domain-specific LLM agents."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Agent:
    name: str = ""
    domain: str = ""
    model: str = ""
    api_url: str = ""
    system_prompt: str = ""


DEFAULT_AGENTS = [
    Agent(name="General Assistant", domain="general", model="", api_url="", system_prompt="You are a helpful vinyl record manufacturing assistant."),
    Agent(name="Chemistry Expert", domain="chemistry", model="", api_url="", system_prompt="You are a chemistry expert specialized in lacquer coatings, silvering, and electroplating for vinyl record manufacturing."),
    Agent(name="Physics Expert", domain="physics", model="", api_url="", system_prompt="You are a physics expert specialized in acoustics, groove geometry, and signal processing for vinyl records."),
    Agent(name="Patent Analyst", domain="patent", model="", api_url="", system_prompt="You are a patent analyst expert in the field of vinyl record manufacturing and chemistry."),
]
