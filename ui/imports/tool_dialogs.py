"""Dialog wrappers for tools that open on demand from the pipeline GUI."""

from collections import Counter
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QLineEdit, QListWidget, QListWidgetItem, QTabWidget,
    QGroupBox,
)
from PySide6.QtCore import Qt


class DataImportDialog(QDialog):
    """Full Data Import widget wrapped in a dialog."""

    def __init__(self, parent=None, llm=None, kb=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle("Herramientas de Importación de Datos")
        self.setMinimumSize(900, 700)
        self.resize(1000, 750)

        from gui.data_import import DataImportWidget
        from src.llm_integration import LocalLLM, ForumKnowledgeBase
        from src.rag_config import RAGSettings
        layout = QVBoxLayout(self)
        self.data_import = DataImportWidget(llm=llm, kb=kb, settings=settings)
        layout.addWidget(self.data_import, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumWidth(120)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def cleanup(self):
        self.data_import.cleanup()

    def get_knowledge_base(self):
        return self.data_import.kb if hasattr(self.data_import, 'kb') else None

    def get_mirror_results(self):
        return getattr(self.data_import, '_mirror_results', None)


class ExpertNotesDialog(QDialog):
    """Expert Notes widget wrapped in a dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Notas de Experto y Registro de Conversación")
        self.setMinimumSize(600, 500)

        from ui.workspace.expert_notes import ExpertNotesWidget
        layout = QVBoxLayout(self)
        self.expert_notes = ExpertNotesWidget()
        layout.addWidget(self.expert_notes, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumWidth(120)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)


class KnowledgeBrowserDialog(QDialog):
    """Browse all knowledge base entries, corrections, and search across them."""

    def __init__(self, parent=None, kb=None, llm=None):
        super().__init__(parent)
        self.setWindowTitle("Navegador de Base de Conocimiento")
        self.setMinimumSize(750, 550)
        self.kb = kb
        self.llm = llm

        layout = QVBoxLayout(self)

        entries_n = len(kb.entries) if kb else 0
        corr_n = len(llm.corrections.corrections) if llm and hasattr(llm, 'corrections') else 0
        cat_str = ""
        if kb:
            cats = Counter(e.category for e in kb.entries)
            cat_str = "  |  " + " | ".join(f"{c}: {n}" for c, n in cats.most_common(6))

        summary = QHBoxLayout()
        summary.addWidget(QLabel(f"<b>{entries_n}</b> entradas  |  <b>{corr_n}</b> correcciones{cat_str}"))
        summary.addStretch()
        layout.addLayout(summary)

        tabs = QTabWidget()

        # Browse tab
        browse_widget = QWidget()
        browse_layout = QVBoxLayout(browse_widget)
        self.browse_list = QListWidget()
        self.browse_list.currentItemChanged.connect(self._on_browse_select)
        browse_layout.addWidget(self.browse_list)
        self.browse_preview = QTextEdit()
        self.browse_preview.setReadOnly(True)
        self.browse_preview.setMaximumHeight(150)
        browse_layout.addWidget(self.browse_preview)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filtrar:"))
        self.browse_filter = QLineEdit()
        self.browse_filter.setPlaceholderText("categoría o título...")
        self.browse_filter.textChanged.connect(self._populate_browse)
        filter_row.addWidget(self.browse_filter, 1)
        browse_layout.addLayout(filter_row)
        tabs.addTab(browse_widget, "Navegar")

        # Search tab
        search_widget = QWidget()
        search_layout = QVBoxLayout(search_widget)
        srow = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar en todo el conocimiento...")
        self.search_input.returnPressed.connect(self._do_search)
        srow.addWidget(self.search_input)
        sbtn = QPushButton("Buscar")
        sbtn.clicked.connect(self._do_search)
        srow.addWidget(sbtn)
        srow.addWidget(QLabel("Máx:"))
        self.search_max = QLineEdit("10")
        self.search_max.setMaximumWidth(50)
        srow.addWidget(self.search_max)
        search_layout.addLayout(srow)
        self.search_results = QListWidget()
        self.search_results.currentItemChanged.connect(self._on_search_select)
        search_layout.addWidget(self.search_results)
        self.search_preview = QTextEdit()
        self.search_preview.setReadOnly(True)
        self.search_preview.setMaximumHeight(150)
        search_layout.addWidget(self.search_preview)
        tabs.addTab(search_widget, "Buscar")

        # Corrections tab
        corr_widget = QWidget()
        corr_layout = QVBoxLayout(corr_widget)
        self.corr_list = QListWidget()
        corr_layout.addWidget(self.corr_list)
        self.corr_preview = QTextEdit()
        self.corr_preview.setReadOnly(True)
        self.corr_preview.setMaximumHeight(120)
        corr_layout.addWidget(self.corr_preview)
        corr_del = QPushButton("Eliminar corrección seleccionada")
        corr_del.clicked.connect(self._delete_correction)
        corr_layout.addWidget(corr_del)
        tabs.addTab(corr_widget, "Correcciones")

        layout.addWidget(tabs, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        qa_btn = QPushButton("Preguntar al LLM sobre seleccionado")
        qa_btn.clicked.connect(self._ask_llm_selected)
        if llm:
            btn_row.addWidget(qa_btn)
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumWidth(120)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._populate_browse()
        self._populate_corrections()

    def _populate_browse(self):
        self.browse_list.clear()
        if not self.kb:
            return
        filt = self.browse_filter.text().lower().strip()
        for entry in self.kb.entries:
            if filt and filt not in entry.category.lower() and filt not in entry.title.lower():
                continue
            im = " 📷" if entry.image_paths else ""
            item = QListWidgetItem(f"[{entry.category}] {entry.title[:70]}{im}")
            item.setData(Qt.UserRole, entry)
            self.browse_list.addItem(item)

    def _on_browse_select(self, curr, prev):
        if not curr:
            return
        entry = curr.data(Qt.UserRole)
        if entry:
            imgs = "\n".join(f"  📷 {p}" for p in entry.image_paths[:5])
            extra = f"\n\nImages:\n{imgs}" if imgs else ""
            self.browse_preview.setPlainText(
                f"Origen: {entry.source}\n"
                f"Palabras clave: {', '.join(entry.keywords[:10])}\n"
                f"{entry.content[:1500]}{extra}"
            )

    def _do_search(self):
        q = self.search_input.text().strip()
        if not q or not self.kb:
            return
        try:
            n = int(self.search_max.text())
        except ValueError:
            n = 10
        self.search_results.clear()
        for entry in self.kb.search(q, max_results=n):
            im = " 📷" if entry.image_paths else ""
            item = QListWidgetItem(f"[{entry.category}] {entry.title[:70]}{im}")
            item.setData(Qt.UserRole, entry)
            self.search_results.addItem(item)

    def _on_search_select(self, curr, prev):
        if not curr:
            return
        entry = curr.data(Qt.UserRole)
        if entry:
            imgs = "\n".join(f"  📷 {p}" for p in entry.image_paths[:5])
            extra = f"\n\nImages:\n{imgs}" if imgs else ""
            self.search_preview.setPlainText(
                f"Origen: {entry.source}\n{entry.content[:1500]}{extra}"
            )

    def _populate_corrections(self):
        self.corr_list.clear()
        if not self.llm or not hasattr(self.llm, 'corrections'):
            return
        for c in self.llm.corrections.corrections:
            item = QListWidgetItem(f"P: {c.question[:70]}")
            item.setData(Qt.UserRole, c)
            self.corr_list.addItem(item)
        self.corr_list.currentItemChanged.connect(self._on_corr_select)

    def _on_corr_select(self, curr, prev):
        if not curr:
            return
        c = curr.data(Qt.UserRole)
        if c:
            self.corr_preview.setPlainText(
                f"P: {c.question}\n\nIncorrecta: {c.wrong_answer[:300]}\n\n"
                f"Correcta: {c.correct_answer}"
            )

    def _delete_correction(self):
        curr = self.corr_list.currentItem()
        if not curr or not self.llm:
            return
        c = curr.data(Qt.UserRole)
        if c:
            self.llm.corrections.corrections.remove(c)
            self.llm.corrections.save()
            self._populate_corrections()
            self.corr_preview.clear()

    def _ask_llm_selected(self):
        if not self.llm:
            return
        text = ""
        for w in (self.browse_preview, self.search_preview):
            t = w.toPlainText().strip()
            if t:
                text = t
                break
        if not text:
            return
        from PySide6.QtWidgets import QDialog as QD, QVBoxLayout as QVL, QTextEdit as QTE
        from PySide6.QtWidgets import QPushButton as QPB, QHBoxLayout as QHL
        dlg = QD(self)
        dlg.setWindowTitle("Consulta LLM")
        dlg.setMinimumSize(600, 400)
        lay = QVL(dlg)
        qi = QTE()
        qi.setPlainText(f"Explica en el contexto de la química de lacas:\n\n{text[:2000]}")
        lay.addWidget(QLabel("Pregunta:"))
        lay.addWidget(qi, 1)
        ao = QTE()
        ao.setReadOnly(True)
        lay.addWidget(ao, 1)
        br = QHL()
        def _ask():
            ao.setPlainText("Pensando...")
            ao.setPlainText(self.llm.ask(qi.toPlainText(), max_tokens=1024))
        ab = QPB("Preguntar")
        ab.clicked.connect(_ask)
        br.addWidget(ab)
        br.addStretch()
        cb = QPB("Cerrar")
        cb.clicked.connect(dlg.accept)
        br.addWidget(cb)
        lay.addLayout(br)
        dlg.exec()
