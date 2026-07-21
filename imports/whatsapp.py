"""WhatsApp chat export parser for the lacquer manufacturing knowledge base.

Parses WhatsApp .txt export files and converts messages into KnowledgeEntry
objects compatible with ForumKnowledgeBase.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class WhatsAppMessage:
    """A single parsed message from a WhatsApp export."""
    timestamp: Optional[datetime]
    sender: str
    text: str
    is_system_message: bool = False


STAGE_KEYWORDS = {
    "cutting": [
        "lacquer", "cut", "stylus", "nitrocellulose", "burkle", "coating",
        "viscosity", "solvent", "resin", "chip", "groove", "tearing", "curl",
        "formulation", "recipe", "plasticizer", "castor oil", "dibutyl",
    ],
    "silvering": [
        "silver", "silvering", "nitrate", "chicken feet", "honeycomb",
        "conductive", "spray", "tannin", "ammonia", "worm",
        "degrease", "rinse", "activation",
    ],
    "plating": [
        "nickel", "sulfamate", "electroform", "bath", "current",
        "father", "mother", "stamper", "pitting", "orange peel",
        "anode", "cathode", "rectifier", "amps", "volts",
    ],
    "pressing": [
        "pressing", "vinyl", "pvc", "mold", "stamper", "press",
        "biscuit", "temperature", "pressure", "non-fill", "flash",
        "warp", "cooling", "injection",
    ],
    "qc": [
        "noise", "warp", "defect", "inspection", "quality",
        "click", "pop", "surface", "test", "playback",
        "thickness", "flatness", "weight",
    ],
}


def detect_stage(text: str) -> str:
    """Heuristically determine which pipeline stage a message relates to."""
    scores = {s: 0 for s in STAGE_KEYWORDS}
    text_lower = text.lower()
    for stage, keywords in STAGE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                scores[stage] += 1
    if max(scores.values()) == 0:
        return "general"
    return max(scores, key=scores.get)


# Regex patterns for WhatsApp message formats
# Pattern 1: [MM/DD/YYYY, HH:MM AM/PM] - US/Canada style
PATTERN_AMPM = re.compile(
    r'^\[?(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*([APap][Mm])'  # date + time
    r'\]?\s*-\s*'  # separator
    r'(.+?):\s*'  # sender
    r'(.*)$'  # message text
)

# Pattern 2: [DD/MM/YYYY, HH:MM] - European style (24h)
PATTERN_24H = re.compile(
    r'^\[?(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?::\d{2})?)'  # date + time (no AM/PM)
    r'\]?\s*-\s*'  # separator
    r'(.+?):\s*'  # sender
    r'(.*)$'  # message text
)

# Pattern for continuation lines (no timestamp, just indented text)
PATTERN_CONTINUATION = re.compile(r'^\s+(.+)$')


def parse_date(date_str: str, time_str: str, ampm: Optional[str] = None) -> Optional[datetime]:
    """Try to parse a date/time string from WhatsApp export with various formats."""
    formats = []
    date_normalized = date_str.strip()
    time_normalized = time_str.strip()

    if ampm:
        # US format: MM/DD/YYYY or M/D/YY
        formats.append(f"%m/%d/%y %I:%M %p")
        formats.append(f"%m/%d/%Y %I:%M %p")
        formats.append(f"%m/%d/%y %I:%M:%S %p")
        formats.append(f"%m/%d/%Y %I:%M:%S %p")
        datetime_str = f"{date_normalized} {time_normalized} {ampm}"
    else:
        # European format: DD/MM/YYYY
        formats.append(f"%d/%m/%y %H:%M")
        formats.append(f"%d/%m/%Y %H:%M")
        formats.append(f"%d/%m/%y %H:%M:%S")
        formats.append(f"%d/%m/%Y %H:%M:%S")
        datetime_str = f"{date_normalized} {time_normalized}"

    for fmt in formats:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue
    return None


def parse_whatsapp_export(file_path: str) -> List[WhatsAppMessage]:
    """Parse a WhatsApp chat export .txt file into structured messages.

    Handles both US (MM/DD/YYYY, 12h) and European (DD/MM/YYYY, 24h) formats,
    system messages, media placeholders, and multi-line messages.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    text = path.read_text(encoding="utf-8", errors="replace")

    lines = text.split("\n")
    messages: List[WhatsAppMessage] = []
    current_msg: Optional[WhatsAppMessage] = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Try US format first (AM/PM)
        m = PATTERN_AMPM.match(line)
        if m:
            if current_msg:
                messages.append(current_msg)
            date_str, time_str, ampm, sender, msg_text = m.groups()

            # Detect system messages
            is_system = is_system_message(sender, msg_text)

            ts = parse_date(date_str, time_str, ampm)
            current_msg = WhatsAppMessage(
                timestamp=ts,
                sender=sender.strip() if not is_system else "System",
                text=msg_text.strip(),
                is_system_message=is_system,
            )
            continue

        # Try European format (24h)
        m = PATTERN_24H.match(line)
        if m:
            if current_msg:
                messages.append(current_msg)
            date_str, time_str, sender, msg_text = m.groups()

            is_system = is_system_message(sender, msg_text)

            ts = parse_date(date_str, time_str)
            current_msg = WhatsAppMessage(
                timestamp=ts,
                sender=sender.strip() if not is_system else "System",
                text=msg_text.strip(),
                is_system_message=is_system,
            )
            continue

        # Continuation of previous message
        if current_msg is not None:
            current_msg.text += "\n" + line

    if current_msg:
        messages.append(current_msg)

    return messages


def parse_whatsapp_web_text(text: str) -> List[WhatsAppMessage]:
    """Parse text copied from WhatsApp Web (copy-paste of the conversation).

    WhatsApp Web copy format (select messages, Ctrl+C):
        Sender Name
        10:30 AM
        Message content

        Sender Name 2
        1/15/24, 2:15 PM
        Message content
    """
    lines = text.strip().split("\n")
    messages: List[WhatsAppMessage] = []
    i = 0

    # Heuristic: a block is Sender line, then Timestamp line, then Content
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # If this looks like a timestamp line, skip it (orphan)
        if _looks_like_timestamp(line):
            i += 1
            continue

        sender = line
        i += 1

        # Next non-empty line should be the timestamp
        ts_line = ""
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i < len(lines):
            ts_line = lines[i].strip()
            i += 1

        ts = None
        if _looks_like_timestamp(ts_line):
            ts = _parse_web_timestamp(ts_line)
        else:
            # The timestamp line wasn't a timestamp — it's part of the content
            ts_line = ""

        # Remaining lines until next blank line or sender pattern are content
        content_parts = []
        if ts_line and not _looks_like_timestamp(ts_line):
            content_parts.append(ts_line)
        while i < len(lines):
            next_line = lines[i].strip()
            if not next_line:
                i += 1
                break
            # Check if next line looks like a new message (sender + timestamp combo)
            if i + 1 < len(lines) and _looks_like_timestamp(lines[i + 1].strip()):
                break
            content_parts.append(next_line)
            i += 1

        content = "\n".join(content_parts).strip()
        if not content:
            continue
        if _is_system_line(f"{sender}: {content}"):
            continue

        msg = WhatsAppMessage(
            timestamp=ts,
            sender=sender,
            text=content,
            is_system_message=False,
        )
        messages.append(msg)

    return messages


def _looks_like_timestamp(text: str) -> bool:
    """Heuristic check if a line looks like a WhatsApp timestamp."""
    if not text:
        return False
    # Pattern: HH:MM or HH:MM AM/PM (possibly with date prefix)
    ts_pattern = re.match(
        r'^(\d{1,2}/\d{1,2}/\d{2,4},\s*)?\d{1,2}:\d{2}(:\d{2})?\s*([APap][Mm])?$',
        text.strip()
    )
    return bool(ts_pattern)


def _parse_web_timestamp(text: str) -> Optional[datetime]:
    """Parse a WhatsApp Web timestamp string."""
    text = text.strip()
    ampm = _extract_ampm(text)
    # Remove AM/PM from time string so parse_date doesn't double-append it
    time_clean = re.sub(r'\s*[APap][Mm]', '', text).strip()
    # Try with date prefix: "1/15/24, 10:30 AM"
    m = re.match(r'(\d{1,2}/\d{1,2}/\d{2,4}),\s*(.+)', text)
    if m:
        date_part = m.group(1)
        time_part = re.sub(r'\s*[APap][Mm]', '', m.group(2)).strip()
        return parse_date(date_part, time_part, ampm)
    # Just time: "10:30 AM"
    return parse_date("01/01/24", time_clean, ampm)


def _extract_ampm(text: str) -> Optional[str]:
    """Extract AM/PM from a time string."""
    m = re.search(r'([APap][Mm])', text)
    return m.group(1) if m else None


def _is_system_line(text: str) -> bool:
    """Quick check if a text block is a system message."""
    indicators = [
        "Messages and calls are end-to-end encrypted",
        "created this group",
        "changed the group",
        "changed this group",
        "security code changed",
        "Your security code",
    ]
    for ind in indicators:
        if ind.lower() in text.lower():
            return True
    return False


def parse_any_whatsapp(text_or_path: str, is_file: bool = True) -> List[WhatsAppMessage]:
    """Auto-detect format: file export or pasted web text, and parse accordingly."""
    if is_file:
        return parse_whatsapp_export(text_or_path)
    return parse_whatsapp_web_text(text_or_path)


def import_whatsapp_text_to_kb(
    text: str,
    kb,
    source_name: str = "whatsapp",
    stage_filter: str = "auto",
) -> Tuple[int, int]:
    """Parse pasted WhatsApp Web text and add entries to a ForumKnowledgeBase."""
    messages = parse_whatsapp_web_text(text)
    entries = messages_to_knowledge_entries(messages, source_name, stage_filter)
    kb.entries.extend(entries)
    kb._built = True
    return len(messages), len(entries)


def is_system_message(sender: str, text: str) -> bool:
    """Detect WhatsApp system messages (not user messages)."""
    system_indicators = [
        "Messages and calls are end-to-end encrypted",
        "created this group",
        "added ",
        "removed ",
        "left ",
        "changed the group",
        "changed this group",
        "security code changed",
        "Your security code",
    ]
    combined = f"{sender}: {text}"
    for indicator in system_indicators:
        if indicator.lower() in combined.lower():
            return True
    return False


def messages_to_knowledge_entries(
    messages: List[WhatsAppMessage],
    source_name: str = "whatsapp",
    default_stage: str = "general",
) -> list:
    """Convert parsed WhatsApp messages to KB-compatible entry dicts.

    Returns list of dicts with keys: source, title, content, category
    for use with ForumKnowledgeBase.
    """
    from knowledge.base import KnowledgeEntry

    entries = []
    for msg in messages:
        if msg.is_system_message:
            continue
        if not msg.text.strip() or msg.text.strip() == "<Media omitted>":
            continue

        stage = detect_stage(msg.text) if default_stage == "auto" else default_stage
        ts_str = msg.timestamp.strftime("%Y-%m-%d %H:%M") if msg.timestamp else "unknown"

        title = f"{source_name} — {msg.sender} ({ts_str})"
        content = f"[{ts_str}] {msg.sender}: {msg.text}"

        entry = KnowledgeEntry(
            source=source_name,
            title=title,
            content=content,
            category=stage,
            keywords=extract_keywords_from_text(msg.text),
        )
        entries.append(entry)

    return entries


def extract_keywords_from_text(text: str) -> List[str]:
    """Simple keyword extraction based on domain terminology."""
    found = set()
    text_lower = text.lower()
    for stage, keywords in STAGE_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                found.add(kw)
    return list(found)


def import_whatsapp_to_kb(
    file_path: str,
    kb,
    source_name: str = "whatsapp",
    stage_filter: str = "auto",
) -> Tuple[int, int]:
    """Parse a WhatsApp export and add entries to a ForumKnowledgeBase.

    Args:
        file_path: Path to WhatsApp .txt export
        kb: ForumKnowledgeBase instance
        source_name: Label for the source
        stage_filter: "auto" to auto-detect, or a specific stage name

    Returns:
        (total_parsed, total_added) tuple
    """
    messages = parse_whatsapp_export(file_path)
    entries = messages_to_knowledge_entries(messages, source_name, stage_filter)
    kb.entries.extend(entries)
    kb._built = True
    return len(messages), len(entries)
