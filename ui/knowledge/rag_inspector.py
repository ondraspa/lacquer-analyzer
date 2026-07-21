"""RAG Inspector — show what knowledge was used to generate an answer."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QListWidget, QListWidgetItem, QTabWidget, QSplitter,
    QGroupBox,
)
from PySide6.QtCore import Qt


class RagInspectorDialog(QDialog):
    """Inspect the knowledge used for a specific Q&A session.

    Shows retrieved chunks, context sent to the LLM, and the answer,
    so the user can verify which sources influenced the response.
    """

    def __init__(self, parent=None, question="", answer="",
                 retrieved_chunks=None, context="", stage=""):
        super().__init__(parent)
        self.setWindowTitle("Inspector RAG")
        self.setMinimumSize(800, 600)
        self.resize(900, 650)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"<b>Etapa:</b> {stage or 'todas'}  |  "
                        f"<b>Fragmentos usados:</b> {len(retrieved_chunks or [])}")
        layout.addWidget(header)

        tabs = QTabWidget()

        # ── 1. Question & Answer ──
        qa_tab = QWidget()
        qa_layout = QVBoxLayout(qa_tab)
        qa_layout.addWidget(QLabel("<b>Pregunta:</b>"))
        self.question_area = QTextEdit()
        self.question_area.setReadOnly(True)
        self.question_area.setPlainText(question)
        self.question_area.setMaximumHeight(80)
        self.question_area.setToolTip("Pregunta que se envió al LLM")
        qa_layout.addWidget(self.question_area)
        qa_layout.addWidget(QLabel("<b>Respuesta:</b>"))
        self.answer_area = QTextEdit()
        self.answer_area.setReadOnly(True)
        self.answer_area.setPlainText(answer)
        self.answer_area.setToolTip("Respuesta generada por el LLM")
        qa_layout.addWidget(self.answer_area, 1)
        tabs.addTab(qa_tab, "P&R")

        # ── 2. Retrieved Chunks ──
        chunks_tab = QWidget()
        chunks_layout = QVBoxLayout(chunks_tab)
        chunks_layout.addWidget(QLabel(
            "Entradas de conocimiento recuperadas como contexto para esta pregunta:"
        ))
        self.chunk_list = QListWidget()
        self.chunk_list.currentItemChanged.connect(self._on_chunk_select)
        self.chunk_list.setToolTip("Fragmentos de conocimiento recuperados y usados como contexto")
        chunks_layout.addWidget(self.chunk_list, 1)
        self.chunk_preview = QTextEdit()
        self.chunk_preview.setReadOnly(True)
        self.chunk_preview.setMaximumHeight(200)
        self.chunk_preview.setToolTip("Vista previa del fragmento de conocimiento seleccionado")
        chunks_layout.addWidget(self.chunk_preview)
        tabs.addTab(chunks_tab, "Fragmentos Recuperados")

        # ── 3. Full Context (system prompt) ──
        context_tab = QWidget()
        context_layout = QVBoxLayout(context_tab)
        context_layout.addWidget(QLabel(
            "El prompt del sistema + contexto enviado al LLM:"
        ))
        self.context_area = QTextEdit()
        self.context_area.setReadOnly(True)
        self.context_area.setPlainText(context[:10000] if context else "(sin contexto)")
        self.context_area.setToolTip("Contexto completo enviado al LLM (fragmentos + pregunta)")
        context_layout.addWidget(self.context_area, 1)
        tabs.addTab(context_tab, "Contexto del LLM")

        layout.addWidget(tabs, 1)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumWidth(120)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        # Populate chunks
        self._retrieved = retrieved_chunks or []
        self._populate_chunks()

    def _populate_chunks(self):
        self.chunk_list.clear()
        for i, chunk in enumerate(self._retrieved):
            cat = chunk.get("category", "?")
            title = chunk.get("title", "?")[:60]
            score = chunk.get("score", 0)
            length = chunk.get("length", 0)
            label = f"[{i+1}] [{cat}] {title}  (puntuación={score}, {length} caracteres)"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, chunk)
            self.chunk_list.addItem(item)

    def _on_chunk_select(self, curr, prev):
        if not curr:
            return
        chunk = curr.data(Qt.UserRole)
        if chunk:
            self.chunk_preview.setPlainText(
                f"Origen: {chunk.get('source', '?')}\n"
                f"Categoría: {chunk.get('category', '?')}\n"
                f"Título: {chunk.get('title', '?')}\n"
                f"Palabras clave: {', '.join(chunk.get('keywords', [])[:10])}\n"
                f"{'─'*40}\n"
                f"{chunk.get('content', '')[:2000]}"
            )
