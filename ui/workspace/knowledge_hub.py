"""Centro de Conocimiento — importación, exploración, RAG Q&A y mapa de conocimiento."""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QTabWidget, QPushButton, QTextEdit,
    QSplitter, QMessageBox, QLineEdit, QListWidget,
    QListWidgetItem,
)
from PySide6.QtCore import Qt


class KnowledgeHub(QWidget):
    def __init__(self):
        super().__init__()
        self.kb = None
        self.llm = None
        self.settings = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("🧠 Centro de Conocimiento — Base de Conocimiento RAG")
        header.setStyleSheet("font-weight: bold; font-size: 16px; padding: 4px;")
        layout.addWidget(header)

        tabs = QTabWidget()

        # Tab 1: Importación rápida
        import_tab = QWidget()
        import_layout = QVBoxLayout(import_tab)

        info = QLabel(
            "<b>Importación rápida</b> — añade datos a la base de conocimiento.<br>"
            "Usa el <b>Importador Completo</b> para opciones avanzadas (Lathe Trolls, Wikipedia, WhatsApp, patentes)."
        )
        info.setWordWrap(True)
        import_layout.addWidget(info)

        btn_row = QHBoxLayout()
        self.import_mirror_btn = QPushButton("🌐 Duplicar Foro (Lathe Trolls)")
        self.import_mirror_btn.clicked.connect(self._import_mirror)
        self.import_mirror_btn.setToolTip("Duplica todas las categorías de lathetrolls.com")
        btn_row.addWidget(self.import_mirror_btn)

        self.import_md_btn = QPushButton("📂 Importar Markdown")
        self.import_md_btn.clicked.connect(self._import_markdown)
        self.import_md_btn.setToolTip("Importa archivos .md raspaños de Playwright")
        btn_row.addWidget(self.import_md_btn)

        self.import_ltkb_btn = QPushButton("📁 lathetrolls_knowledge_base")
        self.import_ltkb_btn.clicked.connect(self._import_ltkb)
        btn_row.addWidget(self.import_ltkb_btn)

        self.import_pdf_btn = QPushButton("📄 Libros Escaneados")
        self.import_pdf_btn.clicked.connect(self._import_pdf)
        btn_row.addWidget(self.import_pdf_btn)

        import_layout.addLayout(btn_row)

        btn_row2 = QHBoxLayout()
        self.full_import_btn = QPushButton("🔧 Importador Completo...")
        self.full_import_btn.clicked.connect(self._open_full_import)
        btn_row2.addWidget(self.full_import_btn)

        self.sanitize_btn = QPushButton("🧹 Sanitizar BC")
        self.sanitize_btn.clicked.connect(self._sanitize_kb)
        btn_row2.addWidget(self.sanitize_btn)

        self.explorer_btn = QPushButton("📊 Explorador de Datos")
        self.explorer_btn.clicked.connect(self._open_explorer)
        btn_row2.addWidget(self.explorer_btn)

        import_layout.addLayout(btn_row2)

        import_layout.addStretch()
        tabs.addTab(import_tab, "Importación")

        # Tab 2: RAG Q&A
        from ui.pipeline.base_stage import KnowledgeQAPanel
        self.qa_hub = KnowledgeQAPanel("general")
        tabs.addTab(self.qa_hub, "P&R — Base de Conocimiento")

        # Tab 3: Navegador KB
        kb_tab = QWidget()
        kb_layout = QVBoxLayout(kb_tab)

        self.kb_search = QLineEdit()
        self.kb_search.setPlaceholderText("Buscar en la base de conocimiento...")
        self.kb_search.textChanged.connect(self._filter_kb_list)
        kb_layout.addWidget(self.kb_search)

        self.kb_list = QListWidget()
        self.kb_list.itemClicked.connect(self._show_kb_preview)
        kb_layout.addWidget(self.kb_list)

        self.kb_preview = QTextEdit()
        self.kb_preview.setReadOnly(True)
        self.kb_preview.setPlaceholderText("Selecciona una entrada para ver su contenido...")
        kb_layout.addWidget(self.kb_preview)

        tabs.addTab(kb_tab, "Navegador BC")

        layout.addWidget(tabs)

    def set_kb_and_llm(self, kb, llm, settings=None):
        self.kb = kb
        self.llm = llm
        self.settings = settings
        self.qa_hub.set_llm(llm)
        self.qa_hub.set_knowledge_base(kb)
        if settings:
            self.qa_hub.set_settings(settings)
        self._refresh_kb_list()

    def _refresh_kb_list(self):
        self.kb_list.clear()
        if not self.kb:
            return
        for entry in self.kb.entries:
            item = QListWidgetItem(f"[{entry.category}] {entry.title[:80]}")
            item.setData(Qt.UserRole, entry)
            self.kb_list.addItem(item)

    def _filter_kb_list(self):
        q = self.kb_search.text().lower()
        for i in range(self.kb_list.count()):
            item = self.kb_list.item(i)
            entry = item.data(Qt.UserRole)
            match = not q or q in entry.title.lower() or q in (entry.content or "").lower()
            item.setHidden(not match)

    def _show_kb_preview(self, item):
        entry = item.data(Qt.UserRole)
        if not entry:
            return
        text = (
            f"<h3>{entry.title}</h3>"
            f"<p><b>Categoría:</b> {entry.category}  |  <b>Fuente:</b> {entry.source}</p>"
            f"<hr>{entry.content[:3000]}"
        )
        self.kb_preview.setHtml(text)

    def _import_mirror(self):
        from ui.imports.tool_dialogs import DataImportDialog
        dlg = DataImportDialog(self, self.llm, self.kb, self.settings)
        dlg.data_import.tabs.setCurrentIndex(4)
        dlg.exec()

    def _import_markdown(self):
        from ui.imports.tool_dialogs import DataImportDialog
        dlg = DataImportDialog(self, self.llm, self.kb, self.settings)
        dlg.data_import.tabs.setCurrentIndex(3)
        dlg.exec()

    def _import_ltkb(self):
        from ui.imports.tool_dialogs import DataImportDialog
        dlg = DataImportDialog(self, self.llm, self.kb, self.settings)
        dlg.data_import.tabs.setCurrentIndex(4)
        dlg.exec()

    def _import_pdf(self):
        from ui.imports.tool_dialogs import DataImportDialog
        dlg = DataImportDialog(self, self.llm, self.kb, self.settings)
        dlg.data_import.tabs.setCurrentIndex(6)
        dlg.exec()

    def _open_full_import(self):
        from ui.imports.tool_dialogs import DataImportDialog
        dlg = DataImportDialog(self, self.llm, self.kb, self.settings)
        dlg.exec()

    def _sanitize_kb(self):
        if not self.llm or not self.llm.is_available():
            QMessageBox.warning(self, "Sanitizar", "LLM no conectado. Inicia LM Studio primero.")
            return
        if not self.kb or not self.kb.entries:
            QMessageBox.warning(self, "Sanitizar", "No hay entradas para sanitizar.")
            return
        from imports.jobs import SanitizeJob
        self.sanitize_job = SanitizeJob(self.kb, self.llm)
        self.sanitize_job.progress.connect(lambda m: self.kb_preview.append(m))
        self.sanitize_job.start()

    def _open_explorer(self):
        from ui.knowledge.explorer import DataExplorerDialog
        dlg = DataExplorerDialog(self, kb=self.kb, llm=self.llm)
        dlg.exec()
