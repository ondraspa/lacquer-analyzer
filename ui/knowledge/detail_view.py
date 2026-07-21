"""Adaptive content detail panel — renders entries according to import type."""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser,
    QScrollArea, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap


IMPORT_ICONS = {
    "Importación de Patentes": "📜",
    "Libros Escaneados": "📖",
    "Duplicado del Foro":  "💬",
    "Importación Markdown": "📁",
    "Importación de WhatsApp": "💬",
    "Otras Fuentes":  "📄",
}

CAT_COLORS = {
    "patent": "#2196F3",
    "forum":  "#4CAF50",
    "book":   "#FF9800",
    "general": "#9E9E9E",
    "correction": "#AB47BC",
    "paper":  "#26C6DA",
    "article": "#26C6DA",
}


def _import_type(source: str) -> str:
    s = source.lower()
    if "google patent" in s or "patent" in s:
        return "Importación de Patentes"
    if "scanned book" in s or s.startswith("/"):
        return "Libros Escaneados"
    if "lathe trolls" in s or "forum" in s or "lathetrolls" in s:
        return "Duplicado del Foro"
    if source.endswith(".md") or "markdown" in s:
        return "Importación Markdown"
    if "whatsapp" in s:
        return "Importación de WhatsApp"
    return "Otras Fuentes"


def _format_patent(content: str) -> str:
    """Extract and reformat patent sections from markdown content."""
    parts = []
    sections = {
        "abstract": "",
        "claims": "",
        "description": "",
    }
    current = None
    for line in content.split("\n"):
        ll = line.strip().lower()
        if ll.startswith("### abstract"):
            current = "abstract"
            continue
        elif ll.startswith("### claims"):
            current = "claims"
            continue
        elif ll.startswith("### description"):
            current = "description"
            continue
        if current and current in sections:
            sections[current] += line + "\n"

    for key, label in [("abstract", "Resumen"), ("claims", "Reivindicaciones"), ("description", "Descripción")]:
        text = sections.get(key, "").strip()
        if text:
            text = _clean_markdown(text)
            parts.append(f'<h3 style="color:#1565C0; margin-top:16px;">▸ {label}</h3>'
                         f'<div style="margin-left:8px;">{text}</div>')
    return "\n".join(parts)


def _clean_markdown(text: str) -> str:
    """Basic markdown-to-plaintext conversion for display."""
    import re
    # Escape HTML special chars first
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    # Convert markdown markers to HTML
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("\n\n", "<br><br>")
    text = text.replace("\n", "<br>")
    return text


class ContentDetailPanel(QWidget):
    """Rich detail viewer that adapts to import type."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._browser.setStyleSheet("""
            QTextBrowser {
                background: #fafafa;
                border: none;
                font-size: 13px;
                padding: 12px;
            }
        """)
        layout.addWidget(self._browser)

    def show_info(self, title: str, body: str):
        """Show a simple info page (for category/import-type clicks)."""
        html = (
            f'<div style="padding:20px; color:#555; text-align:center; font-size:14px;'
            f'font-family:\'Segoe UI\',sans-serif;">'
            f'<h2 style="color:#333;">{title}</h2>'
            f'<p>{body}</p>'
            f'</div>'
        )
        self._browser.setHtml(html)

    def show_entry(self, entry) -> None:
        if not entry:
            self._browser.setHtml(
                '<div style="color:#888; text-align:center; padding:40px;">'
                'Selecciona una entrada para ver su contenido.</div>')
            return
        self._browser.setHtml(self._render(entry))

    def _render(self, entry) -> str:
        imp = _import_type(entry.source)
        icon = IMPORT_ICONS.get(imp, "📄")
        cat_color = CAT_COLORS.get(entry.category.lower(), "#78909C")

        title = entry.title or "(sin título)"
        content = entry.content or ""
        source = entry.source or ""
        keywords = ", ".join(entry.keywords[:10]) if entry.keywords else "—"

        # Title and import-type header
        html = f"""
        <table width="100%"><tr>
        <td><span style="font-size:28px;">{icon}</span></td>
        <td width="100%" style="padding-left:10px;">
            <span style="font-size:11px; color:#888;">{imp}</span><br>
            <span style="font-size:18px; font-weight:bold; color:#1a1a2e;">{title[:120]}</span>
        </td></tr></table>
        <hr style="border:none; border-top:2px solid #e0e0e0; margin:8px 0;">
        """

        # Metadata badges
        html += f"""
        <table style="font-size:12px; color:#555; margin:8px 0;">
        <tr><td style="padding-right:20px;"><b>Categoría</b></td>
            <td><span style="background:{cat_color}; color:white; padding:2px 10px; border-radius:4px;">{entry.category}</span></td></tr>
        <tr><td style="padding-right:20px;"><b>Origen</b></td><td>{source[:80]}</td></tr>
        <tr><td style="padding-right:20px;"><b>Palabras clave</b></td><td>{keywords}</td></tr>
        """

        # Image count
        if entry.image_paths:
            html += f'<tr><td style="padding-right:20px;"><b>Imágenes</b></td><td>{len(entry.image_paths)} archivos</td></tr>'

        html += "</table><hr style=\"border:none; border-top:1px solid #eee; margin:8px 0;\">"

        # First image preview
        if entry.image_paths:
            img_path = entry.image_paths[0]
            if Path(img_path).exists():
                html += f'<div style="text-align:center; margin:8px 0;">'
                html += f'<img src="file://{img_path}" style="max-width:300px; max-height:200px; border-radius:6px; border:1px solid #ddd;">'
                html += f'</div>'

        # Type-specific content rendering
        if imp == "Importación de Patentes":
            html += _format_patent(content)
            # Also show raw content if sections weren't parsed
            if "### Abstract" not in content:
                html += _clean_markdown(content[:3000])
        elif imp == "Libros Escaneados":
            html += f'<div style="font-size:13px; line-height:1.5;">{_clean_markdown(content[:4000])}</div>'
        else:
            html += f'<div style="font-size:13px; line-height:1.5;">{_clean_markdown(content[:4000])}</div>'

        # Full content toggle link
        if len(content) > 4000:
            html += f'<br><p style="color:#888; font-size:11px;">Mostrando primeros 4000 caracteres · {len(content)} total</p>'

        return f"""
        <!DOCTYPE html><html><body style="font-family:'Segoe UI',sans-serif; margin:0; padding:0; color:#333;">
        {html}
        </body></html>
        """
