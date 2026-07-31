"""Data Explorer dialog — browse, search, analyze, import, and log all data from one place."""

import json
import time
from collections import Counter
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QLineEdit, QListWidget, QListWidgetItem, QTabWidget,
    QWidget, QGroupBox, QProgressBar, QMessageBox, QFileDialog,
    QFrame, QSplitter, QInputDialog, QComboBox,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont

from core.translations import T

from src.data_analyzer import analyze_entries
from src.data_logger import ImportLog

from ui.knowledge.map_view import KnowledgeMapView
from ui.knowledge.detail_view import ContentDetailPanel


class DataExplorerDialog(QDialog):
    """Unified data hub: import, browse, search, analyze, and log all data.

    Toolbar at top with import action buttons for every source type.
    Tabs below show overview stats, browsable entries, search, analysis,
    import history, and corrections.
    """

    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, parent=None, kb=None, llm=None, scraper=None,
                 settings=None):
        super().__init__(parent)
        self.setWindowTitle(T("Centro de Datos — Importación y Exploración"))
        self.setMinimumSize(950, 700)
        self.resize(1050, 750)
        self.kb = kb
        self.llm = llm
        self.scraper = scraper
        self.settings = settings
        self.log = ImportLog()
        self._closing = False

        self.log_signal.connect(self._append_log)
        self.finished_signal.connect(self._on_import_finished)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # ── Import toolbar ────────────────────────────────────
        toolbar = QWidget()
        toolbar.setStyleSheet("background: #f5f5f5; border-radius: 4px; padding: 4px;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(4, 4, 4, 4)

        tb_layout.addWidget(QLabel(T("<b>Importar:</b>")))

        self.import_mirror_btn = QPushButton("🌐 Duplicar Foro")
        self.import_mirror_btn.setToolTip("Duplicar todas las categorías del foro Lathe Trolls")
        self.import_mirror_btn.clicked.connect(self._import_mirror)
        tb_layout.addWidget(self.import_mirror_btn)

        self.import_markdown_btn = QPushButton("📂 Archivos Markdown")
        self.import_markdown_btn.setToolTip("Importar desde directorio markdown extraído con Playwright")
        self.import_markdown_btn.clicked.connect(self._import_markdown)
        tb_layout.addWidget(self.import_markdown_btn)

        self.import_ltkb_btn = QPushButton("📁 base_de_conocimiento_lathetrolls")
        self.import_ltkb_btn.setStyleSheet("font-weight: bold;")
        self.import_ltkb_btn.setToolTip("Importación directa desde ~/lathetrolls_knowledge_base/")
        self.import_ltkb_btn.clicked.connect(self._import_ltkb)
        tb_layout.addWidget(self.import_ltkb_btn)

        self.import_pdf_btn = QPushButton("📄 PDF / Libros Escaneados")
        self.import_pdf_btn.setToolTip("Importar libros escaneados, carpetas de imágenes, ZIP/RAR")
        self.import_pdf_btn.clicked.connect(self._import_pdf)
        tb_layout.addWidget(self.import_pdf_btn)

        self.import_cache_btn = QPushButton("💾 Carpeta de Caché")
        self.import_cache_btn.setToolTip("Importar archivos JSON en caché desde forum_cache")
        self.import_cache_btn.clicked.connect(self._import_cache)
        tb_layout.addWidget(self.import_cache_btn)

        tb_layout.addStretch()
        layout.addWidget(toolbar)

        # ── Main tabs ─────────────────────────────────────────
        tabs = QTabWidget()

        # Tab 0: Map View (mind-map navigation)
        map_tab = QWidget()
        map_layout = QVBoxLayout(map_tab)
        map_layout.setContentsMargins(0, 0, 0, 0)

        map_splitter = QSplitter(Qt.Horizontal)
        self.map_view = KnowledgeMapView()
        self.map_view.setToolTip("Vista de mapa mental de la base de conocimiento. Usa rueda del ratón para zoom, arrastra para navegar, doble clic para expandir/colapsar nodos")
        map_splitter.addWidget(self.map_view)

        self.map_detail = ContentDetailPanel()
        self.map_detail.setToolTip("Detalle del nodo seleccionado en el mapa de conocimiento")
        self.map_detail.setMinimumWidth(280)
        self.map_detail.show_info(
            "🗺 Vista de Mapa",
            "Haz clic en un nodo de entrada para previsualizar su contenido aquí.<br><br>"
            "💡 <b>Consejos de navegación:</b><br>"
            "• Rueda del ratón → acercar/alejar<br>"
            "• Arrastrar con clic central → panorámica<br>"
            "• Clic en nodo de entrada → mostrar vista previa<br>"
            "• Doble clic en importación/categoría → expandir/colapsar entradas<br>"
            "• Clic derecho → menú contextual (editar/eliminar)"
        )
        map_splitter.addWidget(self.map_detail)
        map_splitter.setSizes([600, 300])
        map_layout.addWidget(map_splitter, 1)

        map_toolbar = QHBoxLayout()
        map_fit_btn = QPushButton(T("⊞ Ajustar Todo"))
        map_fit_btn.setToolTip("Ajusta la vista del mapa al tamaño de la ventana")
        map_fit_btn.clicked.connect(lambda: self.map_view.fit_all())
        map_toolbar.addWidget(map_fit_btn)
        map_collapse_btn = QPushButton(T("⊟ Colapsar Todo"))
        map_collapse_btn.setToolTip("Colapsa todos los nodos del mapa")
        map_collapse_btn.clicked.connect(self._map_collapse_all)
        map_toolbar.addWidget(map_collapse_btn)
        map_toolbar.addStretch()
        map_layout.addLayout(map_toolbar)

        self.map_view.entry_clicked.connect(self._map_entry_clicked)
        self.map_view.category_clicked.connect(self._map_category_clicked)
        self.map_view.rebuild_requested.connect(self._rebuild_map)

        tabs.addTab(map_tab, T("🗺 Vista de Mapa"))

        # Tab 1: Overview
        overview = QWidget()
        overview_layout = QVBoxLayout(overview)
        self.stats_area = QTextEdit()
        self.stats_area.setReadOnly(True)
        self.stats_area.setToolTip("Estadísticas de la base de conocimiento: número de entradas por tipo y categoría")
        overview_layout.addWidget(self.stats_area, 1)
        refresh_btn = QPushButton(T("Actualizar Estadísticas"))
        refresh_btn.setToolTip("Actualiza las estadísticas")
        refresh_btn.clicked.connect(self._refresh_stats)
        overview_layout.addWidget(refresh_btn)
        tabs.addTab(overview, T("Resumen"))

        # Tab 2: Browse
        browse = QWidget()
        browse_layout = QVBoxLayout(browse)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(T("Filtro:")))
        self.browse_filter = QLineEdit()
        self.browse_filter.setToolTip("Filtra entradas por palabra clave")
        self.browse_filter.setPlaceholderText(T("categoría, título u origen..."))
        self.browse_filter.textChanged.connect(self._populate_browse)
        filter_row.addWidget(self.browse_filter, 1)
        self.browse_source_filter = QLineEdit()
        self.browse_source_filter.setToolTip("Filtra entradas por fuente de importación")
        self.browse_source_filter.setPlaceholderText(T("tipo de origen"))
        self.browse_source_filter.textChanged.connect(self._populate_browse)
        filter_row.addWidget(self.browse_source_filter, 1)
        browse_layout.addLayout(filter_row)
        self.browse_list = QListWidget()
        self.browse_list.setToolTip("Lista de entradas de conocimiento")
        self.browse_list.currentItemChanged.connect(self._on_browse_select)
        browse_layout.addWidget(self.browse_list, 1)
        self.browse_preview = ContentDetailPanel()
        self.browse_preview.setToolTip("Vista previa del contenido de la entrada seleccionada")
        self.browse_preview.setMaximumHeight(220)
        browse_layout.addWidget(self.browse_preview)
        browse_btn_row = QHBoxLayout()
        self.browse_edit_cat_btn = QPushButton(T("✎ Editar Categoría"))
        self.browse_edit_cat_btn.setToolTip("Edita la entrada de conocimiento seleccionada")
        self.browse_edit_cat_btn.clicked.connect(self._browse_edit_category)
        browse_btn_row.addWidget(self.browse_edit_cat_btn)
        self.browse_delete_btn = QPushButton(T("✕ Eliminar Entrada"))
        self.browse_delete_btn.setToolTip("Elimina la entrada de conocimiento seleccionada")
        self.browse_delete_btn.setStyleSheet("color: #e74c3c;")
        self.browse_delete_btn.clicked.connect(self._browse_delete_entry)
        browse_btn_row.addWidget(self.browse_delete_btn)
        browse_btn_row.addStretch()
        self.browse_delete_all_btn = QPushButton(T("🗑 Eliminar Todas las Entradas"))
        self.browse_delete_all_btn.setToolTip("Elimina TODAS las entradas de conocimiento (con confirmación)")
        self.browse_delete_all_btn.setStyleSheet("color: #c0392b; font-weight: bold;")
        self.browse_delete_all_btn.clicked.connect(self._browse_delete_all)
        browse_btn_row.addWidget(self.browse_delete_all_btn)
        browse_layout.addLayout(browse_btn_row)
        tabs.addTab(browse, T("Navegar"))

        # Tab 3: Search
        search = QWidget()
        search_layout = QVBoxLayout(search)
        srow = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setToolTip("Término de búsqueda en la base de conocimiento")
        self.search_input.setPlaceholderText(T("Buscar en todo el conocimiento..."))
        self.search_input.returnPressed.connect(self._do_search)
        srow.addWidget(self.search_input)
        sbtn = QPushButton(T("Buscar"))
        sbtn.setToolTip("Ejecuta la búsqueda")
        sbtn.clicked.connect(self._do_search)
        srow.addWidget(sbtn)
        srow.addWidget(QLabel(T("Máx:")))
        self.search_max = QLineEdit("20")
        self.search_max.setToolTip("Máximo de resultados a mostrar")
        self.search_max.setMaximumWidth(50)
        srow.addWidget(self.search_max)
        search_layout.addLayout(srow)
        self.search_results = QListWidget()
        self.search_results.setToolTip("Resultados de la búsqueda")
        self.search_results.currentItemChanged.connect(self._on_search_select)
        search_layout.addWidget(self.search_results, 1)
        self.search_preview = ContentDetailPanel()
        self.search_preview.setToolTip("Vista previa del resultado seleccionado")
        self.search_preview.setMaximumHeight(220)
        search_layout.addWidget(self.search_preview)
        tabs.addTab(search, T("Buscar"))

        # Tab 4: Analysis
        analysis = QWidget()
        analysis_layout = QVBoxLayout(analysis)
        self.analysis_area = QTextEdit()
        self.analysis_area.setReadOnly(True)
        self.analysis_area.setToolTip("Análisis y estadísticas del contenido de la base de conocimiento")
        analysis_layout.addWidget(self.analysis_area, 1)
        analyze_btn = QPushButton(T("Ejecutar Análisis de Compatibilidad"))
        analyze_btn.setToolTip("Ejecuta el análisis de la base de conocimiento")
        analyze_btn.clicked.connect(self._run_analysis)
        analysis_layout.addWidget(analyze_btn)
        tabs.addTab(analysis, T("Análisis"))

        # Tab 5: Import Log
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setToolTip("Registro histórico de todas las importaciones realizadas")
        log_layout.addWidget(self.log_area, 1)
        log_refresh_btn = QPushButton(T("Actualizar Registro"))
        log_refresh_btn.setToolTip("Actualiza el registro de importación")
        log_refresh_btn.clicked.connect(self._refresh_log)
        log_layout.addWidget(log_refresh_btn)
        log_clear_btn = QPushButton(T("Limpiar Registro"))
        log_clear_btn.setToolTip("Limpia el registro de importación")
        log_clear_btn.clicked.connect(self._clear_log)
        log_layout.addWidget(log_clear_btn)
        tabs.addTab(log_tab, T("Registro de Importación"))

        # Tab 6: Corrections
        corr_tab = QWidget()
        corr_layout = QVBoxLayout(corr_tab)
        self.corr_list = QListWidget()
        self.corr_list.setToolTip("Lista de correcciones aplicadas a la base de conocimiento")
        self.corr_list.currentItemChanged.connect(self._on_corr_select)
        corr_layout.addWidget(self.corr_list)
        self.corr_preview = QTextEdit()
        self.corr_preview.setReadOnly(True)
        self.corr_preview.setToolTip("Vista previa de la corrección seleccionada")
        self.corr_preview.setMaximumHeight(150)
        corr_layout.addWidget(self.corr_preview)
        corr_del = QPushButton(T("Eliminar Corrección Seleccionada"))
        corr_del.setToolTip("Elimina la corrección seleccionada")
        corr_del.clicked.connect(self._delete_correction)
        corr_layout.addWidget(corr_del)
        tabs.addTab(corr_tab, T("Correcciones"))

        # Tab 7: Organize
        org_tab = QWidget()
        org_layout = QVBoxLayout(org_tab)

        org_instructions = QTextEdit()
        org_instructions.setReadOnly(True)
        org_instructions.setToolTip("Instrucciones para organizar la base de conocimiento")
        org_instructions.setMaximumHeight(200)
        org_instructions.setStyleSheet("font-size: 11px; background: #fafafa;")
        org_instructions.setHtml(
            "<h3>¿Por qué organizar tu base de conocimiento?</h3>"
            "<p>Una base de conocimiento bien organizada produce <b>mejores resultados RAG</b>. "
            "El LM encuentra información relevante más rápido y da respuestas más precisas.</p>"
            "<ul>"
            "<li><b>Desduplicar</b> — las entradas repetidas desperdician la ventana de contexto y confunden al LM</li>"
            "<li><b>Eliminar ruido</b> — las entradas muy cortas o vacías no aportan valor</li>"
            "<li><b>Categorizar consistentemente</b> — ayuda a la búsqueda a priorizar entradas relevantes</li>"
            "</ul>"
            "<p><b>Flujo de trabajo típico:</b> Importar datos → Desduplicar → Eliminar ruido → "
            "Recategorizar → Exportar listo para RAG → Hacer preguntas</p>"
        )
        org_layout.addWidget(org_instructions)

        org_tools = QGroupBox(T("Herramientas de Organización"))
        org_tools_layout = QVBoxLayout(org_tools)

        org_btn_row1 = QHBoxLayout()
        self.org_dedup_btn = QPushButton(T("🔍 Desduplicar por Título"))
        self.org_dedup_btn.setToolTip("Elimina entradas duplicadas de la base de conocimiento")
        self.org_dedup_btn.clicked.connect(self._org_deduplicate)
        org_btn_row1.addWidget(self.org_dedup_btn)
        self.org_clean_btn = QPushButton(T("🧹 Eliminar Entradas < 100 caracteres"))
        self.org_clean_btn.setToolTip("Limpia y normaliza el formato de las entradas")
        self.org_clean_btn.clicked.connect(self._org_remove_short)
        org_btn_row1.addWidget(self.org_clean_btn)
        org_tools_layout.addLayout(org_btn_row1)

        org_btn_row2 = QHBoxLayout()
        self.org_recat_btn = QPushButton(T("🏷 Recategorizar por Origen"))
        self.org_recat_btn.setToolTip("Recategoriza entradas según su contenido")
        self.org_recat_btn.clicked.connect(self._org_recategorize)
        org_btn_row2.addWidget(self.org_recat_btn)
        org_tools_layout.addLayout(org_btn_row2)

        org_layout.addWidget(org_tools)

        self.org_log = QTextEdit()
        self.org_log.setReadOnly(True)
        self.org_log.setToolTip("Registro de operaciones de organización")
        self.org_log.setPlaceholderText(T("Los resultados de organización aparecerán aquí..."))
        org_layout.addWidget(self.org_log, 1)

        tabs.addTab(org_tab, T("Organizar"))

        # Tab 8: Export RAG
        export_tab = QWidget()
        export_layout = QVBoxLayout(export_tab)

        export_instructions = QTextEdit()
        export_instructions.setReadOnly(True)
        export_instructions.setToolTip("Instrucciones para exportar la base de conocimiento en formato RAG")
        export_instructions.setMaximumHeight(200)
        export_instructions.setStyleSheet("font-size: 11px; background: #fafafa;")
        export_instructions.setHtml(
            "<h3>Exportación de Base de Conocimiento lista para RAG</h3>"
            "<p>Exporta tu base de conocimiento en un formato directamente utilizable por un LLM para "
            "<b>Generación Aumentada por Recuperación (RAG)</b>.</p>"
            "<ul>"
            "<li><b>JSONL</b> — una entrada por línea, ideal para carga programática</li>"
            "<li><b>Markdown</b> — formato legible, cada entrada como encabezados + texto</li>"
            "<li><b>Texto Fragmentado</b> — texto plano con encabezados de metadatos, listo para "
            "inyección de contexto a través de la API de LM Studio</li>"
            "</ul>"
            "<p><b>Cómo usar con LM Studio:</b> Carga el archivo markdown exportado como "
            "contexto en la interfaz de chat, o apunta tu pipeline RAG al archivo JSONL. "
            "Para mejores resultados, desduplica y organiza tu BC primero (pestaña Organizar).</p>"
        )
        export_layout.addWidget(export_instructions)

        export_opts = QHBoxLayout()
        export_opts.addWidget(QLabel(T("Formato de exportación:")))
        self.export_format = QComboBox()
        self.export_format.setToolTip("Formato de exportación: JSONL, Markdown o Texto Fragmentado")
        self.export_format.addItems(["JSONL", "Markdown", "Texto Fragmentado"])
        export_opts.addWidget(self.export_format)
        export_opts.addStretch()
        self.export_btn = QPushButton(T("📦 Exportar Base de Conocimiento RAG"))
        self.export_btn.setToolTip(T("Exporta la base de conocimiento al formato seleccionado"))
        self.export_btn.setStyleSheet("background: #2196F3; color: white; padding: 6px 16px; font-weight: bold;")
        self.export_btn.clicked.connect(self._export_rag)
        export_opts.addWidget(self.export_btn)
        self.export_open_btn = QPushButton(T("📂 Abrir Carpeta de Exportación"))
        self.export_open_btn.setToolTip("Abre la carpeta donde se exportaron los archivos")
        self.export_open_btn.clicked.connect(self._export_open_folder)
        export_opts.addWidget(self.export_open_btn)
        export_layout.addLayout(export_opts)

        self.export_log = QTextEdit()
        self.export_log.setReadOnly(True)
        self.export_log.setToolTip("Registro de la operación de exportación")
        self.export_log.setPlaceholderText(T("El registro de exportación aparecerá aquí..."))
        export_layout.addWidget(self.export_log, 1)

        tabs.addTab(export_tab, T("Exportar RAG"))

        layout.addWidget(tabs, 1)

        # Bottom: progress bar + close
        self.progress_bar = QProgressBar()
        self.progress_bar.setToolTip("Progreso de la operación actual")
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        btn_row = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setToolTip("Estado de la operación actual")
        btn_row.addWidget(self.status_label, 1)
        close_btn = QPushButton(T("Cerrar"))
        close_btn.setToolTip("Cierra el explorador de datos")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumWidth(120)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        # Initial load
        self._refresh_stats()
        self._populate_browse()
        self._run_analysis()
        self._refresh_log()
        self._populate_corrections()
        self._rebuild_map()

    # ═══════════════════════════════════════════════════════════
    # IMPORT ACTIONS
    # ═══════════════════════════════════════════════════════════

    def _append_log(self, msg: str):
        """Append a message to the Overview area as a running log."""
        if self._closing:
            return
        current = self.stats_area.toPlainText()
        self.stats_area.setPlainText(current + "\n" + msg)
        # Scroll to bottom
        cursor = self.stats_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.stats_area.setTextCursor(cursor)

    def _on_import_finished(self):
        if self._closing:
            return
        self._refresh_all()
        self.progress_bar.setVisible(False)

    def _import_mirror(self):
        """Open the full Data Import dialog (mirror tab is the most complex)."""
        from gui.data_import import DataImportWidget
        dlg = QDialog(self)
        dlg.setWindowTitle(T("Duplicar Foro"))
        dlg.setMinimumSize(800, 600)
        dlayout = QVBoxLayout(dlg)
        # Create a DataImportWidget and switch to mirror tab
        w = DataImportWidget(llm=self.llm, kb=self.kb, settings=self.settings)
        w._tabs.setCurrentIndex(4)  # Forum Mirror tab
        dlayout.addWidget(w)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cb = QPushButton(T("Cerrar"))
        cb.clicked.connect(dlg.accept)
        btn_row.addWidget(cb)
        dlayout.addLayout(btn_row)
        dlg.exec()
        self._refresh_all()

    def _import_markdown(self):
        """Browse for a markdown directory and import (replace or append)."""
        path = QFileDialog.getExistingDirectory(self, T("Seleccionar directorio markdown"), "")
        if not path:
            return
        self._do_import_markdown(path)

    def _import_ltkb(self):
        """Directly import from the known lathetrolls_knowledge_base path."""
        path = str(Path.home() / "lathetrolls_knowledge_base")
        if not Path(path).is_dir():
            QMessageBox.warning(self, T("Ruta No Encontrada"),
                                T("Directorio no encontrado:") + f"\n{path}\n\n"
                                + T("Ejecuta primero el raspador independiente para poblarlo."))
            return
        self._do_import_markdown(path)

    def _do_import_markdown(self, path: str):
        """Import markdown files from *path* with replace/append choice."""
        from pathlib import Path as _Path
        md_files = list(_Path(path).glob("*.md"))
        if not md_files:
            QMessageBox.information(self, T("Sin Datos"), f"{T('No se encontraron archivos .md en')} {path}")
            return

        msg = QMessageBox(self)
        msg.setWindowTitle(T("Importar Markdown"))
        msg.setText(f"{T('Se encontraron')} {len(md_files)} {T('archivos en')} {path}.\n\n"
                    + T("Reemplazar limpia la BC actual. Añadir agrega a los datos existentes."))
        replace_btn = msg.addButton(T("Reemplazar"), QMessageBox.ActionRole)
        append_btn = msg.addButton(T("Añadir"), QMessageBox.ActionRole)
        cancel_btn = msg.addButton(T("Cancelar"), QMessageBox.RejectRole)
        msg.setDefaultButton(cancel_btn)
        msg.exec()
        if msg.clickedButton() == cancel_btn:
            return

        mode = "replace" if msg.clickedButton() == replace_btn else "append"
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self._append_log(f"── Importando {len(md_files)} archivos markdown ({mode}) ──")

        import threading
        def _load():
            def prog(msg):
                if not self._closing:
                    self.log_signal.emit(msg)
            if mode == "replace":
                n = self.kb.build_from_markdown_dir(path, progress_callback=prog)
            else:
                n = self.kb.append_from_markdown_dir(path, progress_callback=prog)
            self.log.add("markdown_import", f"{mode}: {n} entradas",
                         {"entries": n, "mode": mode}, path)
            if not self._closing:
                self.finished_signal.emit()

        threading.Thread(target=_load, daemon=False).start()

    def _import_pdf(self):
        """Open the PDF import dialog."""
        from gui.data_import import DataImportWidget
        dlg = QDialog(self)
        dlg.setWindowTitle(T("Importar PDF / Libros Escaneados"))
        dlg.setMinimumSize(800, 600)
        dlayout = QVBoxLayout(dlg)
        w = DataImportWidget(llm=self.llm, kb=self.kb, settings=self.settings)
        w._tabs.setCurrentIndex(6)  # Scanned Books tab
        dlayout.addWidget(w)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cb = QPushButton(T("Cerrar"))
        cb.clicked.connect(dlg.accept)
        btn_row.addWidget(cb)
        dlayout.addLayout(btn_row)
        dlg.exec()
        self._refresh_all()

    def _import_cache(self):
        """Import cached JSON files from a folder."""
        folder = QFileDialog.getExistingDirectory(
            self, T("Seleccionar carpeta de caché"),
            str(Path("data/forum_cache").resolve())
        )
        if not folder:
            return
        if not self.scraper:
            QMessageBox.warning(self, T("Sin Raspador"),
                                T("El raspador del foro no está disponible en este contexto."))
            return
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        cache_files = list(Path(folder).glob("*.json"))
        self._append_log(f"── Importando {len(cache_files)} archivos de caché desde {folder} ──")

        from gui.data_import import CacheImportJob
        from PySide6.QtCore import QThread

        thread = QThread(self)
        job = CacheImportJob(self.scraper, folder)
        job.moveToThread(thread)
        thread.started.connect(job.run)
        job.finished.connect(lambda posts: (
            self._on_cache_done(posts),
            thread.quit(),
        ))
        job.error.connect(lambda err: (
            self._append_log(f"ERROR: {err}"),
            thread.quit(),
        ))
        job.progress.connect(self._append_log)
        thread.finished.connect(job.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self.progress_bar.setVisible(False))
        thread.start()

    def _on_cache_done(self, posts):
        if not posts:
            self._append_log("No se encontraron archivos de caché válidos.")
            return
        self._append_log(f"Añadiendo {len(posts)} publicaciones a la base de conocimiento...")
        self.kb.build_from_posts(posts)
        self.log.add("cache_import", f"{len(posts)} publicaciones",
                     {"posts": len(posts)}, "forum_cache")
        cats = Counter(p.category for p in posts)
        for cat, count in cats.most_common():
            self._append_log(f"  {cat}: {count} publicaciones")
        self._append_log(f"✓ Importadas {len(posts)} publicaciones ({self.kb.total_chunks} fragmentos)")
        self._refresh_all()

    # ═══════════════════════════════════════════════════════════
    # REFRESH
    # ═══════════════════════════════════════════════════════════

    def _refresh_all(self):
        self._refresh_stats()
        self._populate_browse()
        self._run_analysis()
        self._refresh_log()
        self._populate_corrections()
        self._rebuild_map()
        if self.kb:
            self.status_label.setText(f"{T('BC:')} {len(self.kb.entries)} {T('entradas')}")

    def _rebuild_map(self):
        if self.kb:
            self.map_view.build(self.kb.entries, kb=self.kb)

    def _map_entry_clicked(self, entry):
        if not entry:
            return
        self.map_detail.show_entry(entry)

    def _map_category_clicked(self, cat_name: str, count: int):
        self.map_detail.show_info(
            cat_name,
            f"{count} entradas<br><br>"
            f"<span style='font-size:12px; color:#aaa;'>"
            f"Doble clic para expandir entradas · Clic en entradas individuales para previsualizar"
            f"</span>"
        )

    def _map_collapse_all(self):
        for node in self.map_view._import_nodes.values():
            node.expanded = False
            for child in node.children:
                child.setVisible(False)
            for cat_nodes in self.map_view._category_nodes.values():
                for cn in cat_nodes:
                    cn.expanded = False
                    for gchild in cn.children:
                        gchild.setVisible(False)
            for edge in self.map_view._edges:
                if edge._source == node:
                    edge.setVisible(False)
        self.map_view._animating = False

    # ═══════════════════════════════════════════════════════════
    # STATS
    # ═══════════════════════════════════════════════════════════

    def _refresh_stats(self):
        if not self.kb:
            self.stats_area.setPlainText(
                "No hay base de conocimiento cargada.\n\n"
                "Usa los botones de importación de arriba para añadir datos:\n"
                "  • 🌐 Duplicar Foro — extraer lathetrolls.com\n"
                "  • 📁 Archivos Markdown — importar extracciones .md externas\n"
                "  • 📄 PDF / Libros Escaneados — OCR de páginas escaneadas\n"
                "  • 💾 Carpeta de Caché — importar archivos JSON en caché"
            )
            return
        entries = self.kb.entries
        total = len(entries)
        cats = Counter(e.category for e in entries)
        sources = Counter(
            e.source.split("/")[2] if "//" in e.source else e.source[:40]
            for e in entries if e.source
        )
        with_img = sum(1 for e in entries if e.image_paths)
        avg_len = sum(len(e.content) for e in entries) / max(total, 1)

        text = (
            f"Total de entradas: {total}\n"
            f"Categorías: {len(cats)}\n"
            f"Fuentes únicas: {len(sources)}\n"
            f"Con imágenes: {with_img}\n"
            f"Longitud promedio de contenido: {avg_len:.0f} caracteres\n\n"
            f"── Categorías ──\n"
        )
        for cat, n in cats.most_common(15):
            pct = n / max(total, 1) * 100
            text += f"  {cat}: {n} ({pct:.1f}%)\n"

        text += f"\n── Fuentes (top 10) ──\n"
        for src, n in sources.most_common(10):
            text += f"  {src}: {n}\n"

        self.stats_area.setPlainText(text)

    # ═══════════════════════════════════════════════════════════
    # BROWSE
    # ═══════════════════════════════════════════════════════════

    def _populate_browse(self):
        self.browse_list.clear()
        if not self.kb:
            return
        filt = self.browse_filter.text().lower().strip()
        src_filt = self.browse_source_filter.text().lower().strip()
        for entry in self.kb.entries:
            if filt:
                if (filt not in entry.category.lower() and
                    filt not in entry.title.lower() and
                    filt not in entry.source.lower()):
                    continue
            if src_filt and src_filt not in entry.source.lower():
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
            self.browse_preview.show_entry(entry)

    # ═══════════════════════════════════════════════════════════
    # SEARCH
    # ═══════════════════════════════════════════════════════════

    def _do_search(self):
        q = self.search_input.text().strip()
        if not q or not self.kb:
            return
        try:
            n = int(self.search_max.text())
        except ValueError:
            n = 20
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
            self.search_preview.show_entry(entry)

    # ═══════════════════════════════════════════════════════════
    # ANALYSIS
    # ═══════════════════════════════════════════════════════════

    def _run_analysis(self):
        if not self.kb:
            self.analysis_area.setPlainText("No hay base de conocimiento cargada.")
            return
        report = analyze_entries(self.kb.entries)
        text = self._format_report(report)
        self.analysis_area.setPlainText(text)

    def _format_report(self, r: dict) -> str:
        s = r.get("summary", {})
        text = (
            f"═══ INFORME DE COMPATIBILIDAD DE DATOS ═══\n\n"
            f"Puntuación de Preparación RAG: {s.get('rag_readiness', '?')}/10\n\n"
            f"── Resumen ──\n"
            f"  Total de entradas: {s.get('total', 0)}\n"
            f"  Categorías: {s.get('categories', 0)}\n"
            f"  Fuentes: {s.get('sources', 0)}\n"
            f"  Longitud promedio de contenido: {s.get('avg_content_length', 0):.0f} caracteres\n"
            f"  Longitud mediana de contenido: {s.get('median_content_length', 0)} caracteres\n"
            f"  Con imágenes: {s.get('with_images', 0)}\n\n"
        )
        la = r.get("length_analysis", {})
        text += (
            f"── Distribución de Longitud de Contenido ──\n"
            f"  Vacías: {la.get('empty', 0)}\n"
            f"  Muy cortas (<100): {la.get('very_short_<100', 0)}\n"
            f"  Cortas (100-500): {la.get('short_100-500', 0)}\n"
            f"  Medianas (500-2000): {la.get('medium_500-2000', 0)}\n"
            f"  Largas (2000-5000): {la.get('long_2000-5000', 0)}\n"
            f"  Muy largas (>5000): {la.get('very_long_>5000', 0)}\n\n"
        )
        text += "── Categorías ──\n"
        for cat, n in r.get("categories", {}).items():
            text += f"  {cat}: {n}\n"
        dups = r.get("duplicates", [])
        if dups:
            text += f"\n── Entradas Duplicadas ({len(dups)}) ──\n"
            for title, count in dups[:10]:
                text += f"  '{title}' aparece {count}x\n"
        text += "\n── Cobertura de Temas ──\n"
        for topic, info in r.get("coverage", {}).items():
            bar = "▓" * info["found"] + "░" * (info["total"] - info["found"])
            text += f"  {topic:20s} {bar} ({info['found']}/{info['total']})\n"
            if info["keywords_found"]:
                text += f"  {'':20s} encontrados: {', '.join(info['keywords_found'][:5])}\n"
        if r.get("sources"):
            text += f"\n── Fuentes ──\n"
            for src, n in list(r["sources"].items())[:10]:
                text += f"  {src}: {n}\n"
        return text

    # ═══════════════════════════════════════════════════════════
    # LOG
    # ═══════════════════════════════════════════════════════════

    def _refresh_log(self):
        self.log_area.clear()
        self.log = ImportLog()
        if not self.log.entries:
            self.log_area.setPlainText("No hay entradas de registro de importación todavía.\n"
                                        "Las entradas aparecen después de duplicar foro, importar PDF, etc.")
            return
        text = ""
        for entry in reversed(self.log.entries[-200:]):
            t = entry.get("timestamp", 0)
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(t))
            action = entry.get("action", "")
            detail = entry.get("detail", "")
            counts = entry.get("counts", {})
            counts_str = " | ".join(f"{k}={v}" for k, v in counts.items()) if counts else ""
            source = entry.get("source", "")
            line = f"[{ts}] {action}"
            if counts_str:
                line += f" ({counts_str})"
            if detail:
                line += f" — {detail[:100]}"
            if source:
                line += f" [{source[:60]}]"
            text += line + "\n"
        self.log_area.setPlainText(text)

    def _clear_log(self):
        reply = QMessageBox.question(self, T("Limpiar Registro"),
                                      T("¿Eliminar todas las entradas del registro de importación?"),
                                      QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.log.clear()
            self._refresh_log()

    # ═══════════════════════════════════════════════════════════
    # CORRECTIONS
    # ═══════════════════════════════════════════════════════════

    def _populate_corrections(self):
        self.corr_list.clear()
        if not self.llm or not hasattr(self.llm, 'corrections'):
            return
        for c in self.llm.corrections.corrections:
            item = QListWidgetItem(f"Q: {c.question[:70]}")
            item.setData(Qt.UserRole, c)
            self.corr_list.addItem(item)

    def _on_corr_select(self, curr, prev):
        if not curr:
            return
        c = curr.data(Qt.UserRole)
        if c:
            self.corr_preview.setPlainText(
                f"Q: {c.question}\n\nWrong: {c.wrong_answer[:300]}\n\n"
                f"Correct: {c.correct_answer}"
            )

    def closeEvent(self, event):
        self._closing = True
        super().closeEvent(event)

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

    # ═══════════════════════════════════════════════════════════
    # BROWSE: EDIT / DELETE
    # ═══════════════════════════════════════════════════════════

    def _get_selected_entry(self):
        curr = self.browse_list.currentItem()
        if not curr or not self.kb:
            return None
        return curr.data(Qt.UserRole)

    def _browse_edit_category(self):
        entry = self._get_selected_entry()
        if not entry:
            QMessageBox.information(self, T("Sin Selección"), T("Selecciona una entrada en la lista primero."))
            return
        new_cat, ok = QInputDialog.getText(
            self, T("Editar Categoría"),
            f"{T('Categoría actual:')} {entry.category}\n{T('Nueva categoría:')}",
            text=entry.category,
        )
        if ok and new_cat:
            entry.category = new_cat.strip()
            self.kb.save()
            self._populate_browse()
            self._on_browse_select(self.browse_list.currentItem(), None)

    def _browse_delete_entry(self):
        entry = self._get_selected_entry()
        if not entry:
            QMessageBox.information(self, T("Sin Selección"), T("Selecciona una entrada en la lista primero."))
            return
        reply = QMessageBox.question(
            self, T("Eliminar Entrada"),
            f"{T('¿Eliminar')} '{entry.title[:60]}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.kb.entries.remove(entry)
            self.kb.save()
            self._refresh_all()

    def _browse_delete_all(self):
        if not self.kb or not self.kb.entries:
            return
        reply = QMessageBox.question(
            self, T("Eliminar Todas las Entradas"),
            f"{T('¿Eliminar TODAS las')} {len(self.kb.entries)} {T('entradas de la base de conocimiento?')}\n\n"
            + T("¡Esto no se puede deshacer!"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.kb.entries.clear()
            self.kb.save()
            self._refresh_all()

    # ═══════════════════════════════════════════════════════════
    # ORGANIZE
    # ═══════════════════════════════════════════════════════════

    def _org_log(self, msg: str):
        self.org_log.append(msg)
        self.org_log.verticalScrollBar().setValue(
            self.org_log.verticalScrollBar().maximum()
        )

    def _org_deduplicate(self):
        if not self.kb or not self.kb.entries:
            return
        seen = {}
        dups = []
        for e in self.kb.entries:
            key = e.title.lower().strip()
            if key in seen:
                dups.append(e)
            else:
                seen[key] = e
        if not dups:
            self._org_log("✓ No se encontraron títulos duplicados.")
            return
        for e in dups:
            self.kb.entries.remove(e)
        self.kb.save()
        self._org_log(f"✓ Se eliminaron {len(dups)} entradas duplicadas (se mantuvo la primera aparición).")
        self._refresh_all()

    def _org_remove_short(self):
        if not self.kb or not self.kb.entries:
            return
        before = len(self.kb.entries)
        self.kb.entries[:] = [e for e in self.kb.entries if len(e.content.strip()) >= 100]
        removed = before - len(self.kb.entries)
        if removed:
            self.kb.save()
            self._org_log(f"✓ Se eliminaron {removed} entradas con contenido < 100 caracteres.")
            self._refresh_all()
        else:
            self._org_log("✓ No hay entradas cortas para eliminar.")

    def _org_recategorize(self):
        if not self.kb or not self.kb.entries:
            return
        changes = 0
        for e in self.kb.entries:
            src = e.source.lower()
            if "patent" in src and e.category != "patent":
                e.category = "patent"
                changes += 1
            elif "scanned book" in src or "pdf" in src and e.category != "book":
                e.category = "book"
                changes += 1
            elif "forum" in src or "lathe trolls" in src or "lathetrolls" in src:
                if e.category == "general":
                    e.category = "forum"
                    changes += 1
        if changes:
            self.kb.save()
            self._org_log(f"✓ Se recategorizaron {changes} entradas según el origen.")
            self._refresh_all()
        else:
            self._org_log("✓ Ninguna entrada necesitó recategorización.")

    # ═══════════════════════════════════════════════════════════
    # EXPORT RAG
    # ═══════════════════════════════════════════════════════════

    def _export_rag(self):
        if not self.kb or not self.kb.entries:
            QMessageBox.information(self, T("BC Vacía"), T("Nada que exportar."))
            return
        export_dir = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de exportación", str(Path("data").resolve())
        )
        if not export_dir:
            return
        fmt = self.export_format.currentText()
        self.export_log.clear()
        self.export_log.append(f"Exportando {len(self.kb.entries)} entradas como {fmt}...")

        try:
            if fmt == "JSONL":
                path = Path(export_dir) / "rag_knowledge_base.jsonl"
                with open(path, "w", encoding="utf-8") as f:
                    for e in self.kb.entries:
                        obj = {
                            "source": e.source,
                            "title": e.title,
                            "category": e.category,
                            "content": e.content,
                            "keywords": e.keywords,
                            "image_paths": e.image_paths,
                        }
                        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                self.export_log.append(f"✓ Escrito {path} ({path.stat().st_size / 1024:.0f} KB)")

            elif fmt == "Markdown":
                path = Path(export_dir) / "rag_knowledge_base.md"
                with open(path, "w", encoding="utf-8") as f:
                    f.write("# RAG Knowledge Base\n\n")
                    for e in self.kb.entries:
                        f.write(f"## {e.title}\n\n")
                        f.write(f"- **Source:** {e.source}\n")
                        f.write(f"- **Category:** {e.category}\n")
                        if e.keywords:
                            f.write(f"- **Keywords:** {', '.join(e.keywords[:10])}\n")
                        f.write(f"\n{e.content}\n\n---\n\n")
                self.export_log.append(f"✓ Escrito {path} ({path.stat().st_size / 1024:.0f} KB)")

            else:  # Chunked Text
                path = Path(export_dir) / "rag_knowledge_base.txt"
                with open(path, "w", encoding="utf-8") as f:
                    for i, e in enumerate(self.kb.entries, 1):
                        f.write(f"=== ENTRY {i} ===\n")
                        f.write(f"SOURCE: {e.source}\n")
                        f.write(f"TITLE: {e.title}\n")
                        f.write(f"CATEGORY: {e.category}\n")
                        if e.keywords:
                            f.write(f"KEYWORDS: {', '.join(e.keywords[:10])}\n")
                        f.write("---BEGIN CONTENT---\n")
                        f.write(e.content)
                        f.write("\n---END CONTENT---\n\n")
                self.export_log.append(f"✓ Escrito {path} ({path.stat().st_size / 1024:.0f} KB)")

            self.export_log.append("\nListo. Ahora puedes:\n"
                                   "  • Cargar el archivo en LM Studio como contexto\n"
                                   "  • Apuntar tu pipeline RAG al archivo\n"
                                   "  • Usar el formato Texto Fragmentado para inyección directa por API")
            self.log.add("rag_export", f"{fmt}: {len(self.kb.entries)} entries",
                         {"entries": len(self.kb.entries), "format": fmt}, export_dir)
        except Exception as e:
            self.export_log.append(f"ERROR: {e}")

    def _export_open_folder(self):
        path = str(Path("data").resolve())
        import subprocess
        subprocess.Popen(["xdg-open", path])
