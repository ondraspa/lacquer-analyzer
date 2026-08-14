"""Data import GUI tab - scrape Lathe Trolls, PubChem enrichment, etc."""

import sys
import json
import yaml
import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger("data_import_gui")
_log_initialized = False
def _ensure_log():
    global _log_initialized
    if _log_initialized:
        return
    Path("data/logs").mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler("data/logs/data_import_gui.log", mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    _log_initialized = True

_ensure_log()
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QGroupBox, QCheckBox, QSpinBox, QProgressBar,
    QMessageBox, QListWidget, QListWidgetItem, QTabWidget,
    QLineEdit, QFormLayout, QFileDialog, QComboBox, QSplitter,
    QPlainTextEdit,
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QObject, QTimer
from PySide6.QtGui import QFont

from core.translations import T

from imports.forum import (
    LatheTrollsScraper, PubChemImporter, WikipediaChemicalImporter,
    ForumPost, save_to_custom_ingredients, run_ingest_pipeline
)
from knowledge.base import ForumKnowledgeBase
from llm.client import LocalLLM
from knowledge.settings import RAGSettings
from imports.data_logger import ImportLog
from ui.knowledge.settings_dialog import RAGSettingsDialog
from imports.whatsapp import (
    parse_whatsapp_export, import_whatsapp_to_kb,
    parse_whatsapp_web_text, import_whatsapp_text_to_kb,
    detect_stage, messages_to_knowledge_entries,
)
from imports.pdf_book import (
    ocr_pdf_pages, import_pdf_to_kb, import_image_folder_to_kb,
    import_archive_to_kb, bulk_import_pdfs, get_available_languages,
    check_dependencies as check_pdf_deps,
)

from imports.jobs import *


class DataImportWidget(QWidget):
    pdf_install_log_signal = Signal(str)
    pdf_dep_status_signal = Signal(str)
    pdf_deps_check_signal = Signal()
    pdf_install_done_signal = Signal()

    def __init__(self, llm: Optional[LocalLLM] = None,
                 kb: Optional[ForumKnowledgeBase] = None,
                 settings: Optional[RAGSettings] = None):
        super().__init__()
        self.pdf_install_log_signal.connect(self._on_pdf_install_log)
        self.pdf_dep_status_signal.connect(lambda s: self.pdf_dep_status.setText(s))
        self.pdf_deps_check_signal.connect(self._pdf_check_deps)
        self.pdf_install_done_signal.connect(self._on_pdf_install_done)
        self.scraper = LatheTrollsScraper(
            cache_dir=getattr(settings, 'forum_cache_dir', 'data/forum_cache') if settings else 'data/forum_cache',
            search_max_pages=getattr(settings, 'scrape_search_max_pages', 2) if settings else 2,
            forum_max_pages=getattr(settings, 'scrape_forum_max_pages', 5) if settings else 5,
            mirror_max_pages=getattr(settings, 'scrape_mirror_max_pages', 3) if settings else 3,
            auth_state_path="config/auth_state.json",
        )
        self.config_dir = str(Path(__file__).parent.parent / "config")
        self._threads = []
        self._abort_enrich = False

        self.llm = llm or LocalLLM()
        self.kb = kb or ForumKnowledgeBase()
        self.settings = settings or RAGSettings()
        self._kb_built = bool(kb and kb.entries)
        self.import_log = ImportLog()
        self._last_llm_question = ""
        self._last_llm_answer = ""
        self._last_llm_context = ""
        self._last_llm_matches = []

        self._init_ui()

    def cleanup(self):
        """Stop all background threads and operations. Call from parent closeEvent."""
        self._abort_enrich = True
        for t in self._threads:
            t.quit()
            t.wait(2000)
        self._threads.clear()
        if hasattr(self, '_mirror_job') and self._mirror_job:
            self._mirror_job._abort = True
        if hasattr(self, '_mirror_thread') and self._mirror_thread:
            self._mirror_thread.join(timeout=2)
        if hasattr(self, '_llm_job') and self._llm_job:
            self._llm_job._abort = True
        if hasattr(self, '_llm_thread') and self._llm_thread:
            self._llm_thread.quit()
            self._llm_thread.wait(2000)
        if hasattr(self, '_patent_job') and self._patent_job:
            self._patent_job._abort = True

    # ── Auth / Session Management ────────────────────────────

    def update_auth_status(self):
        """Update the auth status indicator based on Playwright auth state."""
        if self.scraper.is_authenticated():
            self.auth_status.setText("Conectado")
            self.auth_status.setStyleSheet(
                "background: #4CAF50; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;"
            )
        else:
            self.auth_status.setText("No conectado")
            self.auth_status.setStyleSheet(
                "background: #f44336; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;"
            )

    def _open_login_browser(self):
        """Open a real Chromium window for the user to log into lathetrolls.com interactively.

        Handles the entire flow within the GUI — no terminal input needed.
        """
        from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QPushButton, QLabel
        from PySide6.QtCore import Qt

        info = QMessageBox(self)
        info.setIcon(QMessageBox.Information)
        info.setWindowTitle(T("Inicio de Sesión en Lathe Trolls"))
        info.setText(
            T("Se abrirá una ventana del navegador Chromium.\n\n"
            "1. Inicia sesión en lathetrolls.com\n"
            "2. Marca 'Recordarme automáticamente en cada visita'\n"
            "3. Haz clic en Iniciar Sesión y espera a que cargue la página principal\n"
            "4. Vuelve a esta ventana y haz clic en 'Guardar Sesión'")
        )
        info.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        if info.exec() != QMessageBox.Ok:
            return

        if not LatheTrollsScraper._playwright_available():
            QMessageBox.warning(self, T("Playwright"),
                T("Playwright o Chromium no instalados.\n"
                "Ejecuta:  pip install playwright && playwright install chromium"))
            return

        from playwright.sync_api import sync_playwright

        auth_file = self.scraper._auth_state_path
        auth_file.parent.mkdir(parents=True, exist_ok=True)

        browser = None
        context = None

        try:
            pw = sync_playwright().start()
            launch_kw, ctx_kw = LatheTrollsScraper._playwright_fingerprint()
            browser = pw.chromium.launch(headless=False, **launch_kw)
            context = browser.new_context(**ctx_kw)
            page = context.new_page()
            page.goto("https://www.lathetrolls.com/ucp.php?mode=login")

            # Show a modal dialog that waits for the user to confirm login
            confirm = QDialog(self)
            confirm.setWindowTitle(T("Confirmar Inicio de Sesión"))
            confirm.setModal(True)
            confirm.setMinimumWidth(400)
            layout = QVBoxLayout(confirm)
            label = QLabel(
                "El navegador está abierto. Completa estos pasos:\n\n"
                "1. Ingresa tu nombre de usuario y contraseña\n"
                "2. Marca 'Recordarme automáticamente en cada visita'\n"
                "3. Haz clic en Iniciar Sesión\n"
                "4. Espera a que la página principal del foro cargue completamente\n\n"
                "Luego haz clic en 'Guardar Sesión' abajo."
            )
            label.setWordWrap(True)
            layout.addWidget(label)
            btn_row = QHBoxLayout()
            save_btn = QPushButton(T("✓ Guardar Sesión"))
            save_btn.setStyleSheet("background: #4CAF50; color: white; padding: 8px 16px; font-size: 14px;")
            save_btn.clicked.connect(confirm.accept)
            cancel_btn = QPushButton(T("Cancelar"))
            cancel_btn.clicked.connect(confirm.reject)
            btn_row.addStretch()
            btn_row.addWidget(save_btn)
            btn_row.addWidget(cancel_btn)
            layout.addLayout(btn_row)
            confirm.exec()

            if confirm.result() == QDialog.Accepted:
                context.storage_state(path=str(auth_file))
                # Verify cookies
                import json
                with open(auth_file) as f:
                    state = json.load(f)
                ccount = len(state.get("cookies", []))
                if ccount > 0:
                    self.scrape_log.append(f"✓ Inicio de sesión exitoso — {ccount} cookies guardadas")
                else:
                    self.scrape_log.append("⚠ El inicio de sesión no generó cookies — inténtalo de nuevo")
            else:
                self.scrape_log.append("Inicio de sesión cancelado")

        except Exception as e:
            self.scrape_log.append(f"⚠ Error de inicio de sesión: {e}")
        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
            try:
                pw.stop()
            except Exception:
                pass
        self.update_auth_status()

    def _clear_auth(self):
        """Remove saved session data."""
        self.scraper.clear_playwright_auth()
        self.scraper.clear_cookies()
        self.update_auth_status()
        self.scrape_log.append("✓ Estado de autenticación limpiado")

    def _run_in_thread(self, job_class, job_args, on_finished,
                        on_error=None, on_done=None, on_progress=None,
                        on_page_progress=None):
        """Run a QObject worker in a background thread.

        The job object stays in the main thread (no moveToThread) to avoid
        the "shared QObject was deleted directly" crash when Python GC runs
        from the main thread on an object with worker-thread affinity.

        Signals emitted from inside job.run() are automatically queued to the
        main thread because the sender (job) lives in the main thread and the
        worker thread is a different thread → Qt.AutoConnection → QueuedConnection.
        """
        thread = QThread(self)
        job = job_class(*job_args)
        # NOTE: do NOT call job.moveToThread(thread) — keep job in main thread

        thread.started.connect(job.run, Qt.DirectConnection)
        job.finished.connect(thread.quit)
        job.finished.connect(on_finished, Qt.QueuedConnection)
        thread.finished.connect(job.deleteLater)
        thread.finished.connect(thread.deleteLater)

        if on_error:
            job.error.connect(on_error, Qt.QueuedConnection)
        if on_done:
            job.finished.connect(on_done, Qt.QueuedConnection)
            # NOTE: error does NOT trigger on_done — the job keeps running
            # through remaining items, and finished() will restore UI when done.
        if on_progress:
            job.progress.connect(on_progress, Qt.QueuedConnection)
        if on_page_progress:
            job.page_progress.connect(on_page_progress, Qt.QueuedConnection)

        self._threads.append(thread)
        thread._scrape_job = job
        thread.finished.connect(lambda: self._threads.remove(thread)
                                if thread in self._threads else None)
        thread.start()
        return job, thread

    def _init_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        self.tabs = tabs
        tabs.setTabPosition(QTabWidget.West)
        tabs.setDocumentMode(True)
        tabs.setStyleSheet("QTabBar { alignment: left; }")
        tabs.setToolTip(T("Fuentes de importación organizadas por flujo de trabajo (sidebar)."))

        # === Tab 1: Lathe Trolls Scraper ===
        troll_tab = QWidget()
        troll_layout = QVBoxLayout(troll_tab)

        info_label = QLabel(T(
            "<b>Importación de Lathe Trolls</b><br>"
            "Extrae conocimiento de <a href='https://lathetrolls.com'>lathetrolls.com</a> — "
            "el foro sobre corte de lacas para discos, plateado y electroconformado.<br>"
            "Extrae menciones de ingredientes, recetas de formulaciones y conocimiento de procesos."
        ))
        info_label.setWordWrap(True)
        info_label.setOpenExternalLinks(True)
        troll_layout.addWidget(info_label)

        # Keyword input
        kw_layout = QHBoxLayout()
        self.keyword_input = QLineEdit()
        self.keyword_input.setToolTip("Palabras clave para buscar en el foro de Lathe Trolls")
        self.keyword_input.setPlaceholderText(T("Palabras clave (separadas por comas, ej. nitrocellulose, silver nitrate)"))
        self.keyword_input.setText("nitrocellulose, butyl acetate, lacquer, silver nitrate, castor oil")
        kw_layout.addWidget(QLabel(T("Palabras clave:")))
        kw_layout.addWidget(self.keyword_input)
        troll_layout.addLayout(kw_layout)

        # Options
        opts_layout = QHBoxLayout()
        self.use_seed_threads = QCheckBox(T("Usar solo hilos semilla (sin búsqueda)"))
        self.use_seed_threads.setChecked(True)
        self.use_seed_threads.setToolTip("Raspar hilos de formulación conocidos sin buscar")
        opts_layout.addWidget(self.use_seed_threads)
        troll_layout.addLayout(opts_layout)

        # Max pages
        pages_layout = QHBoxLayout()
        pages_layout.addWidget(QLabel(T("Máx. páginas de búsqueda:")))
        self.scrape_search_pages = QSpinBox()
        self.scrape_search_pages.setRange(1, 100)
        self.scrape_search_pages.setToolTip("Número máximo de páginas de resultados de búsqueda a procesar (1–100)")
        self.scrape_search_pages.setValue(self.settings.scrape_search_max_pages)
        pages_layout.addWidget(self.scrape_search_pages)
        pages_layout.addWidget(QLabel(T("Máx. páginas del foro:")))
        self.scrape_forum_pages = QSpinBox()
        self.scrape_forum_pages.setRange(1, 100)
        self.scrape_forum_pages.setValue(self.settings.scrape_forum_max_pages)
        self.scrape_forum_pages.setToolTip("Número máximo de páginas de cada hilo del foro a procesar (1–100)")
        pages_layout.addWidget(self.scrape_forum_pages)
        pages_layout.addStretch()
        troll_layout.addLayout(pages_layout)

        # Auth status row
        auth_layout = QHBoxLayout()
        self.auth_status = QLabel()
        self.auth_status.setStyleSheet("padding: 4px 8px; border-radius: 4px;")
        self.auth_status.setToolTip("Estado de la sesión en Lathe Trolls")
        self.update_auth_status()
        self.login_btn = QPushButton(T("Iniciar Sesión con el Navegador"))
        self.login_btn.setToolTip(
            "Abrir un navegador Chromium real para iniciar sesión en lathetrolls.com interactivamente"
        )
        self.login_btn.clicked.connect(self._open_login_browser)
        self.clear_auth_btn = QPushButton(T("Limpiar Autenticación"))
        self.clear_auth_btn.clicked.connect(self._clear_auth)
        self.clear_auth_btn.setToolTip("Eliminar estado de inicio de sesión guardado")
        auth_layout.addWidget(QLabel(T("Sesión:")))
        auth_layout.addWidget(self.auth_status)
        auth_layout.addStretch()
        auth_layout.addWidget(self.login_btn)
        auth_layout.addWidget(self.clear_auth_btn)
        troll_layout.addLayout(auth_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.scrape_btn = QPushButton(T("Raspar Lathe Trolls"))
        self.scrape_btn.setToolTip("Inicia el raspado de Lathe Trolls para extraer conocimiento del foro")
        self.scrape_btn.clicked.connect(self._run_scrape)
        self.export_btn = QPushButton(T("Exportar a YAML"))
        self.export_btn.setToolTip("Exporta los mensajes raspados a un archivo YAML/JSON")
        self.export_btn.clicked.connect(self._export_scraped)
        self.export_btn.setEnabled(False)
        self.scrape_stop_btn = QPushButton(T("Detener"))
        self.scrape_stop_btn.setToolTip("Detiene la operación de raspado en curso")
        self.scrape_stop_btn.clicked.connect(self._stop_scrape)
        self.scrape_stop_btn.setStyleSheet("background: #f44336; color: white; font-weight: bold;")
        self.scrape_stop_btn.setVisible(False)
        btn_layout.addWidget(self.scrape_btn)
        btn_layout.addWidget(self.scrape_stop_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addStretch()
        troll_layout.addLayout(btn_layout)

        self.scrape_progress = QProgressBar()
        self.scrape_progress.setVisible(False)
        self.scrape_progress.setToolTip("Progreso de la operación de raspado")
        troll_layout.addWidget(self.scrape_progress)

        self.scrape_log = QTextEdit()
        self.scrape_log.setReadOnly(True)
        self.scrape_log.setToolTip("Registro de eventos y mensajes durante el raspado")
        self.scrape_log.setPlaceholderText(T("El resultado del raspado aparecerá aquí..."))
        troll_layout.addWidget(self.scrape_log)

        # Extracted ingredients list
        self.ingredient_list = QListWidget()
        self.ingredient_list.setMaximumHeight(200)
        self.ingredient_list.setToolTip("Lista de ingredientes extraídos de los mensajes del foro, ordenados por número de menciones")
        troll_layout.addWidget(QLabel(T("Ingredientes Extraídos:")))
        troll_layout.addWidget(self.ingredient_list)

        tabs.addTab(troll_tab, T("Lathe Trolls"))

        # === Tab 2: PubChem ===
        chem_tab = QWidget()
        chem_layout = QVBoxLayout(chem_tab)

        # Search area
        search_layout = QHBoxLayout()
        self.pubchem_search = QLineEdit()
        self.pubchem_search.setToolTip("Busca compuestos químicos en PubChem por nombre")
        self.pubchem_search.setPlaceholderText(T("Buscar en PubChem por nombre químico (ej. nitrocellulose, butyl acetate)..."))
        self.pubchem_search.returnPressed.connect(self._pubchem_search)
        self.pubchem_search_btn = QPushButton(T("Buscar"))
        self.pubchem_search_btn.setToolTip("Ejecuta la búsqueda en PubChem")
        self.pubchem_search_btn.clicked.connect(self._pubchem_search)
        search_layout.addWidget(self.pubchem_search)
        search_layout.addWidget(self.pubchem_search_btn)
        chem_layout.addLayout(search_layout)

        # Results list
        chem_layout.addWidget(QLabel(T("Resultados de Búsqueda:")))
        self.pubchem_results = QListWidget()
        self.pubchem_results.setMaximumHeight(200)
        self.pubchem_results.setToolTip("Resultados de la búsqueda en PubChem")
        chem_layout.addWidget(self.pubchem_results)

        # Add selected to ingredients
        add_layout = QHBoxLayout()
        self.pubchem_add_btn = QPushButton(T("Añadir Seleccionado a BD de Ingredientes"))
        self.pubchem_add_btn.setToolTip("Añade el compuesto seleccionado a la base de datos de ingredientes")
        self.pubchem_add_btn.clicked.connect(self._pubchem_add)
        self.pubchem_add_btn.setStyleSheet("background: #4CAF50; color: white; padding: 6px;")
        self.pubchem_add_btn.setEnabled(False)
        self.pubchem_category = QComboBox()
        self.pubchem_category.setToolTip("Categoría química del compuesto a añadir")
        self.pubchem_category.addItems(["resins", "solvents", "additives", "pigments"])
        add_layout.addWidget(QLabel(T("Categoría:")))
        add_layout.addWidget(self.pubchem_category)
        add_layout.addWidget(self.pubchem_add_btn)
        add_layout.addStretch()
        chem_layout.addLayout(add_layout)

        # Enrichment area
        sep = QLabel("<hr><b>Enriquecimiento por Lotes</b> — enriquece todos tus ingredientes existentes")
        sep.setWordWrap(True)
        chem_layout.addWidget(sep)

        chem_btn_layout = QHBoxLayout()
        self.enrich_btn = QPushButton(T("Enriquecer Ingredientes desde PubChem"))
        self.enrich_btn.setToolTip("Enriquece todos los ingredientes existentes con datos fisicoquímicos de PubChem")
        self.enrich_btn.clicked.connect(self._run_enrich)
        self.enrich_stop_btn = QPushButton(T("Detener"))
        self.enrich_stop_btn.setToolTip("Detiene el enriquecimiento por lotes en curso")
        self.enrich_stop_btn.clicked.connect(self._stop_enrich)
        self.enrich_stop_btn.setStyleSheet("background: #f44336; color: white; font-weight: bold;")
        self.enrich_stop_btn.setVisible(False)
        chem_btn_layout.addWidget(self.enrich_btn)
        chem_btn_layout.addWidget(self.enrich_stop_btn)
        chem_btn_layout.addStretch()
        chem_layout.addLayout(chem_btn_layout)

        self.chem_log = QTextEdit()
        self.chem_log.setReadOnly(True)
        self.chem_log.setToolTip("Registro de eventos y resultados de PubChem")
        chem_layout.addWidget(self.chem_log)

        tabs.addTab(chem_tab, T("PubChem"))

        # === Tab 3: Wikipedia Chemical Search ===
        wiki_tab = QWidget()
        wiki_layout = QVBoxLayout(wiki_tab)

        wiki_info = QLabel(
            "<b>Base de Datos Química de Wikipedia</b><br>"
            "Busca propiedades químicas desde artículos de Wikipedia "
            "(CAS#, fórmula, peso molecular, punto de ebullición/fusión, etc.)<br>"
            "Gratuito, no requiere clave API. Buen respaldo cuando PubChem no tiene datos."
        )
        wiki_info.setWordWrap(True)
        wiki_layout.addWidget(wiki_info)

        wiki_search_layout = QHBoxLayout()
        self.wiki_search = QLineEdit()
        self.wiki_search.setToolTip("Busca propiedades químicas en Wikipedia por nombre")
        self.wiki_search.setPlaceholderText(T("Buscar en Wikipedia un químico (ej. nitrocellulose, acetone)..."))
        self.wiki_search.returnPressed.connect(self._wiki_search)
        self.wiki_search_btn = QPushButton(T("Buscar"))
        self.wiki_search_btn.setToolTip("Ejecuta la búsqueda en Wikipedia")
        self.wiki_search_btn.clicked.connect(self._wiki_search)
        wiki_search_layout.addWidget(self.wiki_search)
        wiki_search_layout.addWidget(self.wiki_search_btn)
        wiki_layout.addLayout(wiki_search_layout)

        wiki_layout.addWidget(QLabel(T("Resultados de Búsqueda:")))
        self.wiki_results = QListWidget()
        self.wiki_results.setMaximumHeight(200)
        self.wiki_results.setToolTip("Resultados de la búsqueda en Wikipedia")
        wiki_layout.addWidget(self.wiki_results)

        wiki_add_layout = QHBoxLayout()
        self.wiki_add_btn = QPushButton(T("Añadir Seleccionado a BD de Ingredientes"))
        self.wiki_add_btn.setToolTip("Añade el artículo químico seleccionado a la base de datos de ingredientes")
        self.wiki_add_btn.clicked.connect(self._wiki_add)
        self.wiki_add_btn.setStyleSheet("background: #4CAF50; color: white; padding: 6px;")
        self.wiki_add_btn.setEnabled(False)
        self.wiki_category = QComboBox()
        self.wiki_category.setToolTip("Categoría química del artículo a añadir")
        self.wiki_category.addItems(["resins", "solvents", "additives", "pigments"])
        wiki_add_layout.addWidget(QLabel(T("Categoría:")))
        wiki_add_layout.addWidget(self.wiki_category)
        wiki_add_layout.addWidget(self.wiki_add_btn)
        wiki_add_layout.addStretch()
        wiki_layout.addLayout(wiki_add_layout)

        self.wiki_log = QTextEdit()
        self.wiki_log.setReadOnly(True)
        self.wiki_log.setToolTip("Registro de eventos y resultados de Wikipedia")
        wiki_layout.addWidget(self.wiki_log)

        tabs.addTab(wiki_tab, T("Wikipedia"))

        # === Tab 3: Import from File ===
        file_tab = QWidget()
        file_layout = QVBoxLayout(file_tab)

        file_info = QLabel(
            "<b>Importar desde Archivos Externos</b><br>"
            "Importar ingredientes desde:\n"
            "• Archivos YAML/JSON (cualquier formato)\n"
            "• Hojas de cálculo CSV de proveedores\n"
            "• Archivos Excel (.xlsx) con datos de ingredientes"
        )
        file_info.setWordWrap(True)
        file_layout.addWidget(file_info)

        file_btn_layout = QHBoxLayout()
        self.import_yaml_btn = QPushButton(T("Importar YAML/JSON"))
        self.import_yaml_btn.setToolTip("Importa ingredientes desde un archivo YAML o JSON")
        self.import_yaml_btn.clicked.connect(self._import_file)
        self.import_csv_btn = QPushButton(T("Importar CSV"))
        self.import_csv_btn.setToolTip("Importa ingredientes desde un archivo CSV de proveedores")
        self.import_csv_btn.clicked.connect(self._import_csv)
        file_btn_layout.addWidget(self.import_yaml_btn)
        file_btn_layout.addWidget(self.import_csv_btn)

        self.import_markdown_btn = QPushButton(T("Examinar Markdown..."))
        self.import_markdown_btn.setStyleSheet("background: #FF9800; color: white; padding: 6px;")
        self.import_markdown_btn.setToolTip(
            "Examinar archivos markdown raspados por troll_scraper_stealth.py"
        )
        self.import_markdown_btn.clicked.connect(self._load_playwright_markdown)
        file_btn_layout.addWidget(self.import_markdown_btn)

        self.import_ltkb_btn = QPushButton(T("Importar base_de_conocimiento_lathetrolls"))
        self.import_ltkb_btn.setStyleSheet("background: #4CAF50; color: white; padding: 6px; font-weight: bold;")
        self.import_ltkb_btn.setToolTip(
            "Importar directamente desde /home/ondra/lathetrolls_knowledge_base/ "
            "(la salida del raspador independiente)"
        )
        self.import_ltkb_btn.clicked.connect(self._import_ltkb)
        file_btn_layout.addWidget(self.import_ltkb_btn)

        file_btn_layout.addStretch()
        file_layout.addLayout(file_btn_layout)

        self.file_log = QTextEdit()
        self.file_log.setReadOnly(True)
        self.file_log.setToolTip("Registro de eventos y resultados de la importación de archivos")
        file_layout.addWidget(self.file_log)

        tabs.addTab(file_tab, T("Importar Archivo"))

        # === Tab 4: Forum Mirror ===
        mirror_tab = QWidget()
        mirror_layout = QVBoxLayout(mirror_tab)

        mirror_info = QLabel(
            "<b>Duplicar Foro</b><br>"
            "Duplica todas las categorías de lathetrolls.com a archivos markdown.<br>"
            "Ejecuta el script externo <code>troll_scraper_stealth.py</code> que usa "
            "Playwright con Chromium real para evadir Imperva Incapsula WAF.<br>"
            "Requiere inicio de sesión — usa <b>Iniciar Sesión con el Navegador</b> en la pestaña Lathe Trolls primero.<br>"
            "Salida: ~/lathetrolls_knowledge_base/ — cargado automáticamente en la base de conocimiento al finalizar."
        )
        mirror_info.setWordWrap(True)
        mirror_layout.addWidget(mirror_info)

        # Thread ID range
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel(T("Rango de hilos:")))
        self.mirror_start_id = QSpinBox()
        self.mirror_start_id.setRange(1, 999999)
        self.mirror_start_id.setValue(2)
        self.mirror_start_id.setPrefix("Inicio: ")
        self.mirror_start_id.setFixedWidth(160)
        self.mirror_start_id.setToolTip("ID del primer hilo del foro a duplicar")
        range_layout.addWidget(self.mirror_start_id)
        self.mirror_end_id = QSpinBox()
        self.mirror_end_id.setRange(0, 999999)
        self.mirror_end_id.setValue(100)
        self.mirror_end_id.setPrefix("Fin: ")
        self.mirror_end_id.setFixedWidth(160)
        self.mirror_end_id.setSpecialValueText("Automático")
        self.mirror_end_id.setToolTip("ID del último hilo a duplicar (0 = descubrir automáticamente)")
        range_layout.addWidget(self.mirror_end_id)
        range_layout.addWidget(QLabel(T("(0 = descubrir automáticamente)")))
        range_layout.addStretch()
        mirror_layout.addLayout(range_layout)

        mirror_btn_layout = QHBoxLayout()
        self.mirror_btn = QPushButton(T("Duplicar Todas las Categorías"))
        self.mirror_btn.setToolTip("Duplica todas las categorías del foro a archivos markdown mediante Playwright")
        self.mirror_btn.clicked.connect(self._run_mirror)
        self.mirror_export_btn = QPushButton(T("Exportar Todo a YAML"))
        self.mirror_export_btn.setToolTip("Exporta el contenido duplicado a un archivo YAML")
        self.mirror_export_btn.clicked.connect(self._export_mirror)
        self.mirror_export_btn.setEnabled(False)
        self.mirror_stop_btn = QPushButton(T("Detener"))
        self.mirror_stop_btn.setToolTip("Detiene la operación de duplicación en curso")
        self.mirror_stop_btn.clicked.connect(self._stop_mirror)
        self.mirror_stop_btn.setStyleSheet("background: #f44336; color: white; font-weight: bold;")
        self.mirror_stop_btn.setVisible(False)
        mirror_btn_layout.addWidget(self.mirror_btn)
        mirror_btn_layout.addWidget(self.mirror_stop_btn)
        mirror_btn_layout.addWidget(self.mirror_export_btn)
        mirror_btn_layout.addStretch()
        mirror_layout.addLayout(mirror_btn_layout)

        mirror_btn_row2 = QHBoxLayout()
        self.mirror_import_btn = QPushButton(T("Importar carpeta de caché..."))
        self.mirror_import_btn.setToolTip("Importa una carpeta de caché con archivos JSON del foro a la base de conocimiento")
        self.mirror_import_btn.clicked.connect(self._mirror_import_cache)
        self.mirror_import_btn.setStyleSheet("background: #2196F3; color: white; padding: 4px;")
        mirror_btn_row2.addWidget(self.mirror_import_btn)
        self.mirror_backfill_btn = QPushButton(T("Rellenar imágenes desde caché"))
        self.mirror_backfill_btn.setToolTip("Descarga imágenes faltantes desde los mensajes del foro en caché")
        self.mirror_backfill_btn.clicked.connect(self._mirror_backfill_images)
        self.mirror_backfill_btn.setStyleSheet("background: #FF9800; color: white; padding: 4px;")
        mirror_btn_row2.addWidget(self.mirror_backfill_btn)
        mirror_btn_row2.addStretch()
        mirror_layout.addLayout(mirror_btn_row2)

        self.mirror_progress = QProgressBar()
        self.mirror_progress.setVisible(False)
        self.mirror_progress.setToolTip("Progreso de la duplicación del foro")
        mirror_layout.addWidget(self.mirror_progress)

        self.mirror_log = QTextEdit()
        self.mirror_log.setReadOnly(True)
        self.mirror_log.setToolTip("Registro de eventos durante la duplicación del foro")
        self.mirror_log.setPlaceholderText(T("El resultado de la duplicación aparecerá aquí...\n1. Inicia Sesión con el Navegador en la pestaña Lathe Trolls\n2. Haz clic en Duplicar Todas las Categorías"))
        self.mirror_log.setStyleSheet("font-family: monospace; font-size: 11px;")
        mirror_layout.addWidget(self.mirror_log, 1)

        tabs.addTab(mirror_tab, T("Duplicar Foro"))

        # === Tab 5b: WhatsApp Import ===
        wa_tab = QWidget()
        wa_layout = QVBoxLayout(wa_tab)

        wa_info = QLabel(
            "<b>Importación de Conocimiento de WhatsApp</b><br>"
            "Importa discusiones de fabricación de vinilos desde WhatsApp.<br>"
            "<b>Método A</b> — Archivo de exportación: En WhatsApp → ⋮ → Más → Exportar chat (sin medios)<br>"
            "<b>Método B</b> — Copiar desde WhatsApp Web: Seleccionar mensajes (Ctrl+A), copiar (Ctrl+C), pegar abajo"
        )
        wa_info.setWordWrap(True)
        wa_layout.addWidget(wa_info)

        # Splitter: file import (top) / paste area (bottom)
        wa_splitter = QSplitter(Qt.Vertical)

        # ── Top: File import ──
        wa_file_group = QGroupBox(T("Método A: Importar Archivo .txt Exportado"))
        wa_file_layout = QVBoxLayout(wa_file_group)

        wa_file_row = QHBoxLayout()
        self.wa_file_path = QLineEdit()
        self.wa_file_path.setToolTip("Ruta del archivo .txt exportado de WhatsApp")
        self.wa_file_path.setPlaceholderText(T("Seleccionar archivo .txt exportado de WhatsApp..."))
        self.wa_file_path.setReadOnly(True)
        wa_file_row.addWidget(self.wa_file_path)

        wa_browse_btn = QPushButton(T("Examinar..."))
        wa_browse_btn.setToolTip("Selecciona un archivo .txt exportado de WhatsApp")
        wa_browse_btn.clicked.connect(self._wa_browse)
        wa_file_row.addWidget(wa_browse_btn)

        self.wa_preview_file_btn = QPushButton(T("Vista Previa"))
        self.wa_preview_file_btn.setToolTip("Muestra una vista previa de los mensajes del archivo seleccionado")
        self.wa_preview_file_btn.clicked.connect(self._wa_preview_file)
        self.wa_preview_file_btn.setEnabled(False)
        wa_file_row.addWidget(self.wa_preview_file_btn)
        wa_file_layout.addLayout(wa_file_row)
        wa_splitter.addWidget(wa_file_group)

        # ── Bottom: Paste from clipboard ──
        wa_paste_group = QGroupBox(T("Método B: Pegar desde WhatsApp Web"))
        wa_paste_layout = QVBoxLayout(wa_paste_group)

        self.wa_paste_area = QTextEdit()
        self.wa_paste_area.setToolTip("Área para pegar mensajes copiados desde WhatsApp Web (Ctrl+V)")
        self.wa_paste_area.setPlaceholderText(
            "1. Abre WhatsApp Web, ve al chat del grupo de vinilos\n"
            "2. Haz clic en el chat, presiona Ctrl+A para seleccionar todos los mensajes\n"
            "3. Presiona Ctrl+C para copiar\n"
            "4. Vuelve aquí y presiona Ctrl+V para pegar\n"
            "5. Haz clic en 'Importar Texto Pegado' abajo"
        )
        self.wa_paste_area.setMinimumHeight(120)
        wa_paste_layout.addWidget(self.wa_paste_area)
        wa_splitter.addWidget(wa_paste_group)

        wa_layout.addWidget(wa_splitter, 1)

        # ── Options + buttons ──
        wa_opts = QHBoxLayout()
        wa_opts.addWidget(QLabel(T("Etiqueta de origen:")))
        self.wa_source = QLineEdit("Grupo de Vinilos WhatsApp")
        self.wa_source.setToolTip("Etiqueta de origen para los mensajes importados")
        wa_opts.addWidget(self.wa_source)

        wa_opts.addWidget(QLabel(T("Filtro de etapa:")))
        self.wa_stage_filter = QComboBox()
        self.wa_stage_filter.setToolTip("Filtra los mensajes por etapa del proceso de fabricación")
        self.wa_stage_filter.addItems(["auto", "cutting", "silvering", "plating", "pressing", "qc", "general"])
        wa_opts.addWidget(self.wa_stage_filter)
        wa_layout.addLayout(wa_opts)

        wa_btn_layout = QHBoxLayout()
        self.wa_import_btn = QPushButton(T("Importar Archivo Seleccionado"))
        self.wa_import_btn.setToolTip("Importa el archivo de WhatsApp seleccionado a la base de conocimiento")
        self.wa_import_btn.clicked.connect(self._wa_import)
        self.wa_import_btn.setStyleSheet("background: #4CAF50; color: white; padding: 6px;")
        self.wa_import_btn.setEnabled(False)
        wa_btn_layout.addWidget(self.wa_import_btn)

        self.wa_import_paste_btn = QPushButton(T("Importar Texto Pegado"))
        self.wa_import_paste_btn.setToolTip("Importa el texto pegado desde WhatsApp Web a la base de conocimiento")
        self.wa_import_paste_btn.clicked.connect(self._wa_import_paste)
        self.wa_import_paste_btn.setStyleSheet("background: #2196F3; color: white; padding: 6px;")
        self.wa_import_paste_btn.setEnabled(True)
        wa_btn_layout.addWidget(self.wa_import_paste_btn)

        wa_btn_layout.addStretch()
        wa_layout.addLayout(wa_btn_layout)

        self.wa_log = QTextEdit()
        self.wa_log.setReadOnly(True)
        self.wa_log.setToolTip("Registro de eventos durante la importación de WhatsApp")
        self.wa_log.setPlaceholderText(T("El registro de importación aparecerá aquí..."))
        self.wa_log.setMaximumHeight(80)
        wa_layout.addWidget(self.wa_log)

        wa_layout.addWidget(QLabel(T("Vista Previa de Mensajes:")))
        self.wa_preview = QListWidget()
        self.wa_preview.setMaximumHeight(150)
        self.wa_preview.setToolTip("Vista previa de los mensajes de WhatsApp analizados")
        wa_layout.addWidget(self.wa_preview)

        tabs.addTab(wa_tab, T("WhatsApp"))

        # === Tab 6: Scanned Books / PDF / Image Folders ===
        pdf_tab = QWidget()
        pdf_layout = QVBoxLayout(pdf_tab)

        pdf_info = QLabel(
            "<b>Importación de Libros Escaneados</b><br>"
            "Importa libros escaneados desde archivos PDF o carpetas de imágenes de páginas.<br>"
            "Extrae imágenes, ejecuta OCR (Tesseract) y añade a la base de conocimiento.<br>"
            "Soportados: PDF, JPG, PNG, TIFF, BMP, WebP."
        )
        pdf_info.setWordWrap(True)
        pdf_layout.addWidget(pdf_info)

        self.pdf_dep_status = QLabel("")
        pdf_layout.addWidget(self.pdf_dep_status)

        # File / folder selection
        pdf_file_row = QHBoxLayout()
        self.pdf_file_list = QListWidget()
        self.pdf_file_list.setMaximumHeight(80)
        self.pdf_file_list.setToolTip(
            "Archivos PDF, carpetas de imágenes y archivos ZIP/RAR añadidos aquí.\n"
            "Carpetas mostradas con 📁, archivos con prefijo 🗜."
        )
        pdf_file_row.addWidget(self.pdf_file_list, 1)

        pdf_btn_col = QVBoxLayout()
        pdf_add_pdf = QPushButton(T("Añadir PDF..."))
        pdf_add_pdf.setToolTip("Añade uno o más archivos PDF a la lista de importación")
        pdf_add_pdf.clicked.connect(self._pdf_add_pdf)
        pdf_add_dir = QPushButton(T("Añadir Carpeta de Imágenes..."))
        pdf_add_dir.setToolTip("Añade una carpeta con imágenes de páginas escaneadas")
        pdf_add_dir.clicked.connect(self._pdf_add_folder)
        pdf_add_zip = QPushButton(T("Añadir ZIP/RAR..."))
        pdf_add_zip.setToolTip("Añade un archivo ZIP/RAR con imágenes de páginas")
        pdf_add_zip.clicked.connect(self._pdf_add_archive)
        pdf_clear_btn = QPushButton(T("Limpiar"))
        pdf_clear_btn.setToolTip("Limpia la lista de archivos")
        pdf_clear_btn.clicked.connect(self.pdf_file_list.clear)
        pdf_btn_col.addWidget(pdf_add_pdf)
        pdf_btn_col.addWidget(pdf_add_dir)
        pdf_btn_col.addWidget(pdf_add_zip)
        pdf_btn_col.addWidget(pdf_clear_btn)
        pdf_file_row.addLayout(pdf_btn_col)
        pdf_layout.addLayout(pdf_file_row)

        # Source label + language selector
        pdf_opts_row = QHBoxLayout()
        pdf_opts_row.addWidget(QLabel(T("Etiqueta de origen:")))
        self.pdf_source_input = QLineEdit("Libro Escaneado")
        self.pdf_source_input.setToolTip("Etiqueta de origen para los libros importados")
        pdf_opts_row.addWidget(self.pdf_source_input, 1)

        pdf_opts_row.addWidget(QLabel(T("Idioma OCR:")))
        self.pdf_lang_combo = QComboBox()
        self.pdf_lang_combo.setEditable(True)
        self.pdf_lang_combo.addItems(["ces", "eng", "deu", "fra", "spa", "rus", "eng+ces", "deu+eng", "ces+slk"])
        self.pdf_lang_combo.setCurrentText("ces")
        self.pdf_lang_combo.setToolTip(
            "Código(s) de idioma de Tesseract.\n"
            "Ejemplos: eng, ces, deu, fra, spa, rus\n"
            "Combinar con +: eng+ces\n"
            "Instalar paquetes: apt install tesseract-ocr-{lang}"
        )
        pdf_opts_row.addWidget(self.pdf_lang_combo)
        pdf_layout.addLayout(pdf_opts_row)

        # Buttons
        pdf_btn_row = QHBoxLayout()
        self.pdf_import_btn = QPushButton(T("Importar Seleccionado"))
        self.pdf_import_btn.setToolTip("Importa los archivos seleccionados a la base de conocimiento mediante OCR")
        self.pdf_import_btn.clicked.connect(self._pdf_import)
        self.pdf_import_btn.setStyleSheet("background: #4CAF50; color: white; padding: 6px;")
        self.pdf_import_btn.setEnabled(False)
        pdf_btn_row.addWidget(self.pdf_import_btn)

        self.pdf_check_btn = QPushButton(T("Verificar Dependencias"))
        self.pdf_check_btn.setToolTip("Verifica que las dependencias de OCR (Tesseract, PyMuPDF) estén instaladas")
        self.pdf_check_btn.clicked.connect(self._pdf_check_deps)
        pdf_btn_row.addWidget(self.pdf_check_btn)

        self.pdf_install_btn = QPushButton(T("Instalar Dependencias"))
        self.pdf_install_btn.setStyleSheet("background: #FF9800; color: white; padding: 6px;")
        self.pdf_install_btn.setToolTip("Instalar PyMuPDF y pytesseract faltantes mediante pip")
        self.pdf_install_btn.clicked.connect(self._pdf_install_deps)
        pdf_btn_row.addWidget(self.pdf_install_btn)

        pdf_btn_row.addStretch()
        pdf_layout.addLayout(pdf_btn_row)

        self.pdf_progress = QProgressBar()
        self.pdf_progress.setVisible(False)
        self.pdf_progress.setToolTip("Progreso de la importación de libros escaneados")
        pdf_layout.addWidget(self.pdf_progress)

        # Live preview during import
        pdf_preview_split = QSplitter(Qt.Horizontal)

        self.pdf_preview_image = QLabel(T("Sin imagen"))
        self.pdf_preview_image.setToolTip("Vista previa de la imagen de la página escaneada")
        self.pdf_preview_image.setAlignment(Qt.AlignCenter)
        self.pdf_preview_image.setMinimumHeight(200)
        self.pdf_preview_image.setStyleSheet("background: #1e1e1e; color: #aaa; border: 1px solid #444;")
        self.pdf_preview_image.setScaledContents(False)
        pdf_preview_split.addWidget(self.pdf_preview_image)

        self.pdf_preview_ocr = QTextEdit()
        self.pdf_preview_ocr.setReadOnly(True)
        self.pdf_preview_ocr.setToolTip("Texto extraído mediante OCR de la página actual")
        self.pdf_preview_ocr.setPlaceholderText(T("El texto OCR aparecerá aquí..."))
        self.pdf_preview_ocr.setStyleSheet("font-size: 11px;")
        pdf_preview_split.addWidget(self.pdf_preview_ocr)

        pdf_preview_split.setSizes([300, 400])
        pdf_layout.addWidget(pdf_preview_split, 2)

        # Preview controls
        pdf_preview_ctrl = QHBoxLayout()
        self.pdf_prev_btn = QPushButton(T("◀ Anterior"))
        self.pdf_prev_btn.setToolTip("Muestra la página anterior del libro")
        self.pdf_prev_btn.setEnabled(False)
        self.pdf_prev_btn.clicked.connect(self._pdf_prev_page)
        pdf_preview_ctrl.addWidget(self.pdf_prev_btn)
        self.pdf_next_btn = QPushButton(T("Siguiente ▶"))
        self.pdf_next_btn.setToolTip("Muestra la página siguiente del libro")
        self.pdf_next_btn.setEnabled(False)
        self.pdf_next_btn.clicked.connect(self._pdf_next_page)
        pdf_preview_ctrl.addWidget(self.pdf_next_btn)
        self.pdf_remove_btn = QPushButton(T("✕ Quitar"))
        self.pdf_remove_btn.setToolTip("Elimina la página actual de la base de conocimiento")
        self.pdf_remove_btn.setEnabled(False)
        self.pdf_remove_btn.setStyleSheet("color: #e74c3c;")
        self.pdf_remove_btn.clicked.connect(self._pdf_remove_page)
        pdf_preview_ctrl.addWidget(self.pdf_remove_btn)
        self.pdf_preview_page_label = QLabel("")
        self.pdf_preview_page_label.setToolTip("Indicador de la página actual y total")
        pdf_preview_ctrl.addWidget(self.pdf_preview_page_label)
        pdf_preview_ctrl.addStretch()
        self.pdf_stop_btn = QPushButton(T("⏹ Detener"))
        self.pdf_stop_btn.setToolTip("Detiene la importación de libros en curso")
        self.pdf_stop_btn.setStyleSheet("background: #f44336; color: white; padding: 4px 12px;")
        self.pdf_stop_btn.clicked.connect(self._pdf_stop_import)
        self.pdf_stop_btn.setVisible(False)
        pdf_preview_ctrl.addWidget(self.pdf_stop_btn)
        self.pdf_undo_btn = QPushButton(T("↩ Deshacer Última Importación"))
        self.pdf_undo_btn.setToolTip("Deshace la última importación eliminando las entradas añadidas")
        self.pdf_undo_btn.setVisible(False)
        self.pdf_undo_btn.clicked.connect(self._pdf_undo_import)
        pdf_preview_ctrl.addWidget(self.pdf_undo_btn)
        pdf_layout.addLayout(pdf_preview_ctrl)

        self.pdf_undo_label = QLabel("")
        self.pdf_undo_label.setToolTip("Información sobre la última importación realizada")
        pdf_layout.addWidget(self.pdf_undo_label)

        # Import log
        self.pdf_log = QTextEdit()
        self.pdf_log.setReadOnly(True)
        self.pdf_log.setToolTip("Registro de eventos durante la importación de libros escaneados")
        self.pdf_log.setPlaceholderText(T("Registro de importación..."))
        pdf_layout.addWidget(self.pdf_log, 1)

        tabs.addTab(pdf_tab, T("Libros Escaneados"))

        # === Tab 7: LLM Q&A ===
        llm_tab = QWidget()
        llm_layout = QVBoxLayout(llm_tab)

        llm_info = QLabel(
            "<b>LLM Local de P&R de Conocimiento</b><br>"
            "Haz preguntas sobre química de lacas, plateado y enchapado "
            "basadas en el conocimiento del foro duplicado.<br>"
            "Usa la API de LM Studio (localhost:1234).<br>"
            "Primero duplica el foro (pestaña Duplicar Foro), luego haz preguntas aquí."
        )
        llm_info.setWordWrap(True)
        llm_layout.addWidget(llm_info)

        # Status + model selection
        llm_top = QHBoxLayout()
        self.llm_status = QLabel("🔴 LM Studio no conectado")
        self.llm_status.setStyleSheet("padding: 4px 8px;")
        self.llm_status.setToolTip("Estado de conexión con LM Studio")
        self.llm_refresh_btn = QPushButton(T("Actualizar"))
        self.llm_refresh_btn.setToolTip("Actualiza el estado de conexión con LM Studio")
        self.llm_refresh_btn.clicked.connect(self._llm_refresh)
        self.llm_settings_btn = QPushButton(T("⚙ Configuración"))
        self.llm_settings_btn.setToolTip("Abre la configuración del modelo LLM y RAG")
        self.llm_settings_btn.clicked.connect(self._llm_open_settings)
        llm_top.addWidget(self.llm_status)
        llm_top.addStretch()
        self.llm_sanitize_btn = QPushButton(T("🧹 Sanitizar base de conocimiento"))
        self.llm_sanitize_btn.setToolTip("Limpia y normaliza las entradas de la base de conocimiento usando el LLM")
        self.llm_sanitize_btn.setStyleSheet("color: #9C27B0;")
        self.llm_sanitize_btn.clicked.connect(self._llm_sanitize)
        llm_top.addWidget(self.llm_sanitize_btn)
        llm_top.addWidget(self.llm_settings_btn)
        llm_top.addWidget(self.llm_refresh_btn)
        llm_layout.addLayout(llm_top)

        # Knowledge source info
        self.llm_kb_label = QLabel("Base de conocimiento: vacía (duplica el foro primero)")
        self.llm_kb_label.setToolTip("Información sobre el estado de la base de conocimiento")
        llm_layout.addWidget(self.llm_kb_label)

        # Question input
        q_layout = QHBoxLayout()
        self.llm_question = QLineEdit()
        self.llm_question.setToolTip("Escribe tu pregunta sobre química de lacas aquí")
        self.llm_question.setPlaceholderText(T("Haz una pregunta sobre química de lacas..."))
        self.llm_question.returnPressed.connect(self._llm_ask)
        self.llm_ask_btn = QPushButton(T("Preguntar"))
        self.llm_ask_btn.setToolTip("Envía la pregunta al LLM para obtener respuesta basada en la base de conocimiento")
        self.llm_ask_btn.clicked.connect(self._llm_ask)
        q_layout.addWidget(self.llm_question)
        q_layout.addWidget(self.llm_ask_btn)
        llm_layout.addLayout(q_layout)

        self.llm_answer = QTextEdit()
        self.llm_answer.setReadOnly(True)
        self.llm_answer.setToolTip("Respuesta generada por el LLM basada en la base de conocimiento")
        self.llm_answer.setPlaceholderText(T("La respuesta aparecerá aquí..."))
        llm_layout.addWidget(self.llm_answer)

        # Correction / feedback row
        correction_row = QHBoxLayout()
        self.llm_correct_btn = QPushButton(T("✏ Corregir esta respuesta"))
        self.llm_correct_btn.setToolTip("Permite corregir la respuesta actual del LLM")
        self.llm_correct_btn.clicked.connect(self._llm_start_correct)
        self.llm_correct_btn.setEnabled(False)
        self.llm_correct_btn.setStyleSheet("color: #FF9800;")
        correction_row.addWidget(self.llm_correct_btn)
        self.llm_inspect_btn = QPushButton(T("🔍 Inspeccionar contexto RAG"))
        self.llm_inspect_btn.setToolTip("Mostrar qué entradas de conocimiento se usaron para esta respuesta")
        self.llm_inspect_btn.clicked.connect(self._llm_open_inspector)
        self.llm_inspect_btn.setVisible(False)
        correction_row.addWidget(self.llm_inspect_btn)
        self.llm_corrections_label = QLabel("")
        self.llm_corrections_label.setToolTip("Número de correcciones guardadas")
        correction_row.addWidget(self.llm_corrections_label)
        correction_row.addStretch()
        llm_layout.addLayout(correction_row)

        # Correction editor (hidden initially)
        self.llm_correct_widget = QWidget()
        correct_edit_layout = QVBoxLayout(self.llm_correct_widget)
        correct_edit_layout.setContentsMargins(8, 0, 0, 0)
        self.llm_correct_edit = QTextEdit()
        self.llm_correct_edit.setToolTip("Edita la respuesta correcta aquí")
        self.llm_correct_edit.setPlaceholderText(T("Edita la respuesta correcta aquí..."))
        self.llm_correct_edit.setMaximumHeight(120)
        correct_edit_layout.addWidget(QLabel(T("Respuesta corregida:")))
        correct_edit_layout.addWidget(self.llm_correct_edit)
        corr_btn_row = QHBoxLayout()
        self.llm_correct_save_btn = QPushButton(T("✓ Guardar corrección"))
        self.llm_correct_save_btn.setToolTip("Guarda la corrección de la respuesta")
        self.llm_correct_save_btn.setStyleSheet("background: #4CAF50; color: white;")
        self.llm_correct_save_btn.clicked.connect(self._llm_save_correction)
        self.llm_correct_cancel_btn = QPushButton(T("Cancelar"))
        self.llm_correct_cancel_btn.setToolTip("Cancela la edición de la corrección")
        self.llm_correct_cancel_btn.clicked.connect(self._llm_cancel_correct)
        corr_btn_row.addWidget(self.llm_correct_save_btn)
        corr_btn_row.addWidget(self.llm_correct_cancel_btn)
        corr_btn_row.addStretch()
        correct_edit_layout.addLayout(corr_btn_row)
        self.llm_correct_widget.setVisible(False)
        llm_layout.addWidget(self.llm_correct_widget)

        # RAG details
        self.llm_rag_details_btn = QPushButton(T("▶ Mostrar detalles del pipeline RAG"))
        self.llm_rag_details_btn.setToolTip("Muestra u oculta los detalles del pipeline RAG")
        self.llm_rag_details_btn.setStyleSheet("text-align: left; border: none; color: #999; font-size: 11px;")
        self.llm_rag_details_btn.setCheckable(True)
        self.llm_rag_details_btn.toggled.connect(self._llm_toggle_rag)
        llm_layout.addWidget(self.llm_rag_details_btn)

        self.llm_rag_widget = QWidget()
        llm_rag_layout = QVBoxLayout(self.llm_rag_widget)
        llm_rag_layout.setContentsMargins(8, 0, 0, 0)

        self.llm_rag_chunks = QTextEdit()
        self.llm_rag_chunks.setReadOnly(True)
        self.llm_rag_chunks.setMaximumHeight(80)
        self.llm_rag_chunks.setToolTip("Fragmentos de conocimiento recuperados para la respuesta")
        self.llm_rag_chunks.setPlaceholderText(T("Fragmentos de conocimiento recuperados..."))
        self.llm_rag_chunks.setStyleSheet("font-size: 10px; color: #aaa;")
        llm_rag_layout.addWidget(self.llm_rag_chunks)

        self.llm_rag_prompt = QTextEdit()
        self.llm_rag_prompt.setReadOnly(True)
        self.llm_rag_prompt.setMaximumHeight(100)
        self.llm_rag_prompt.setToolTip("Prompt completo enviado al modelo LLM")
        self.llm_rag_prompt.setPlaceholderText(T("Prompt completo enviado al modelo..."))
        self.llm_rag_prompt.setStyleSheet("font-size: 10px; color: #aaa;")
        llm_rag_layout.addWidget(self.llm_rag_prompt)

        self.llm_rag_widget.setVisible(False)
        llm_layout.addWidget(self.llm_rag_widget)

        # Knowledge browser
        llm_layout.addWidget(QLabel(T("Fragmentos de conocimiento relevantes:")))
        self.llm_snippets = QListWidget()
        self.llm_snippets.setMaximumHeight(120)
        self.llm_snippets.setToolTip("Fragmentos de conocimiento relevantes para la pregunta actual")
        llm_layout.addWidget(self.llm_snippets)

        # === Patent Import tab ===
        patent_tab = QWidget()
        patent_layout = QVBoxLayout(patent_tab)

        patent_info = QLabel(
            "<b>Importación de Patentes</b><br>"
            "Importa patentes desde Google Patents. Ingresa números de patente (uno por línea) "
            "y haz clic en Importar. Cada patente se obtiene, analiza y añade a la "
            "base de conocimiento."
        )
        patent_info.setWordWrap(True)
        patent_layout.addWidget(patent_info)

        self.patent_input = QPlainTextEdit()
        self.patent_input.setToolTip("Números de patente a importar (uno por línea)")
        self.patent_input.setPlainText(
            "CZ301692B6\nUS3846361A\nUS4069363A\nUS4081223A\nUS4123489A\n"
            "GB219873A\nGB390145A\nGB529235A\nUS2522138A\nUS2573798A\n"
            "US2636857A\nUS2648724A"
        )
        self.patent_input.setMaximumHeight(200)
        patent_layout.addWidget(QLabel(T("Números de patente (uno por línea):")))
        patent_layout.addWidget(self.patent_input)

        patent_btn_row = QHBoxLayout()
        self.patent_import_btn = QPushButton(T("Importar Seleccionado"))
        self.patent_import_btn.setToolTip("Importa las patentes desde Google Patents a la base de conocimiento")
        self.patent_import_btn.setStyleSheet("background: #4CAF50; color: white; padding: 6px;")
        self.patent_import_btn.clicked.connect(self._patent_import)
        patent_btn_row.addWidget(self.patent_import_btn)

        patent_btn_row.addStretch()
        patent_layout.addLayout(patent_btn_row)

        self.patent_progress = QProgressBar()
        self.patent_progress.setVisible(False)
        self.patent_progress.setToolTip("Progreso de la importación de patentes")
        patent_layout.addWidget(self.patent_progress)

        self.patent_log = QTextEdit()
        self.patent_log.setReadOnly(True)
        self.patent_log.setToolTip("Registro de eventos durante la importación de patentes")
        self.patent_log.setMaximumHeight(200)
        patent_layout.addWidget(QLabel(T("Registro:")))
        patent_layout.addWidget(self.patent_log)

        tabs.addTab(patent_tab, T("Patentes"))

        tabs.addTab(llm_tab, T("LLM P&R"))

        layout.addWidget(tabs)

        # Initialise OCR language combo with actually installed languages
        self._pdf_check_deps()

        self._pdf_job = None
        self._pdf_thread = None
        self._pdf_pages = []
        self._pdf_current_page = -1
        self._pdf_entry_count_before = 0
        self._pdf_last_import_count = 0
        self._patent_job = None
        self._patent_thread = None

        # Store scraped posts
        self._last_posts = []
        self._last_llm_question = ""

    def _run_scrape(self):
        self.scrape_log.clear()
        self.ingredient_list.clear()
        self.scrape_btn.setVisible(False)
        self.scrape_stop_btn.setVisible(True)
        self.scrape_progress.setVisible(True)
        self.scrape_progress.setRange(0, 0)

        use_seed = self.use_seed_threads.isChecked()
        keywords = [k.strip() for k in self.keyword_input.text().split(",")] if not use_seed else []

        # Apply current max pages from spinboxes to scraper
        self.scraper.search_max_pages = self.scrape_search_pages.value()
        self.scraper.forum_max_pages = self.scrape_forum_pages.value()

        if use_seed:
            self.scrape_log.append("Iniciando raspado de Lathe Trolls (hilos semilla)...")
        else:
            self.scrape_log.append(f"Buscando: {', '.join(keywords)}")

        self._run_in_thread(
            job_class=ScrapeJob,
            job_args=(self.scraper, use_seed, keywords, self.settings),
            on_finished=self._on_scrape_finished,
            on_error=self._on_scrape_error,
            on_done=self._enable_scrape_btn,
            on_progress=self._append_scrape_log,
        )

    @Slot(str)
    def _append_scrape_log(self, msg: str):
        self.scrape_log.append(msg)

    @Slot(str)
    def _on_scrape_error(self, msg: str):
        self.scrape_log.append(f"ERROR: {msg}")

    @Slot()
    def _enable_scrape_btn(self):
        self.scrape_btn.setVisible(True)
        self.scrape_stop_btn.setVisible(False)
        self.scrape_progress.setVisible(False)

    def _on_scrape_finished(self, posts):
        self._last_posts = posts
        self.scrape_progress.setVisible(False)
        self.scrape_btn.setVisible(True)
        self.scrape_stop_btn.setVisible(False)
        self.export_btn.setEnabled(True)

        self.scrape_log.append(f"\n=== Raspado Completado ===")
        self.scrape_log.append(f"Encontrados {len(posts)} mensajes")

        # Extract ingredients
        ingredients = self.scraper.extract_ingredients_from_posts(posts)
        self.ingredient_list.clear()
        for ing in sorted(ingredients, key=lambda x: x["mentions"], reverse=True):
            item = QListWidgetItem(
                f"{ing['name']} — {ing['mentions']} menciones, "
                f"promedio {ing['avg_concentration']:.1f}%"
            )
            if ing['mentions'] >= 2:
                item.setBackground(Qt.green)
            self.ingredient_list.addItem(item)

        self.scrape_log.append(f"Encontrados {len(ingredients)} ingredientes únicos")
        self.import_log.add("forum_scrape", f"{len(posts)} mensajes, {len(ingredients)} ingredientes",
                            {"posts": len(posts), "ingredients": len(ingredients)})

    def _stop_scrape(self):
        """Stop the current scrape operation."""
        for t in self._threads:
            job = getattr(t, '_scrape_job', None)
            if job and hasattr(job, '_abort'):
                job._abort = True
                self.scrape_log.append("⏹ Raspado detenido por el usuario")
            t.quit()
            t.wait(1000)
        self._threads.clear()
        self.scrape_btn.setVisible(True)
        self.scrape_stop_btn.setVisible(False)
        self.scrape_progress.setVisible(False)

    def _export_scraped(self):
        if not self._last_posts:
            QMessageBox.warning(self, T("Exportar"), T("No hay datos para exportar"))
            return

        path, _ = QFileDialog.getSaveFileName(
            self, T("Exportar Conocimiento"), "data/lathe_trolls_knowledge.yaml",
            T("YAML (*.yaml);;JSON (*.json)")
        )
        if path:
            self.scraper.export_to_yaml(self._last_posts, path)
            self.scrape_log.append(f"\nExportado a: {path}")

    def _run_enrich(self):
        self.chem_log.clear()
        self.enrich_btn.setVisible(False)
        self.enrich_stop_btn.setVisible(True)
        self._abort_enrich = False

        try:
            from src.ingredient_loader import IngredientLoader
            from src.data_import import PubChemImporter

            self._enrich_loader = IngredientLoader(self.config_dir)
            self._enrich_ingredients = self._enrich_loader.load_all()
            self._enrich_importer = PubChemImporter()
            self._enrich_idx = 0
            self._enrich_preview = []
            self._enrich_found = 0
            self._enrich_skipped = 0
        except Exception as e:
            self.chem_log.append(f"ERROR cargando ingredientes: {e}")
            self._enrich_done()
            return

        self.chem_log.append(f"Enriqueciendo {len(self._enrich_ingredients)} ingredientes con PubChem...")
        QTimer.singleShot(0, self._enrich_next)

    @Slot()
    def _enrich_next(self):
        if self._abort_enrich:
            self.chem_log.append("⏹ Enriquecimiento detenido por el usuario")
            self._enrich_done()
            return
        if self._enrich_idx >= len(self._enrich_ingredients):
            self.chem_log.append(
                f"Completado. Datos encontrados para {self._enrich_found}/"
                f"{len(self._enrich_ingredients)} ingredientes "
                f"({self._enrich_skipped} no en PubChem)")
            self.chem_log.append(f"\n=== Enriquecimiento Completado ===")
            for line in self._enrich_preview:
                self.chem_log.append(f"  {line}")
            if not self._enrich_preview:
                self.chem_log.append("No se encontraron datos de PubChem para los ingredientes actuales.")
                self.chem_log.append("Intenta añadir nombres químicos más comunes a ingredients.yaml")
            self._enrich_done()
            return

        ing = self._enrich_ingredients[self._enrich_idx]
        self._enrich_idx += 1
        self.chem_log.append(f"  [{self._enrich_idx}/{len(self._enrich_ingredients)}] {ing.name}...")

        try:
            enriched = self._enrich_importer.enrich_ingredient(ing)
            chem_data = {k: v for k, v in enriched.properties.items()
                         if k.startswith("pubchem_")}
            if chem_data:
                self._enrich_found += 1
                self._enrich_preview.append(
                    f"{enriched.name}: CAS={chem_data.get('pubchem_cas','?')} "
                    f"MW={chem_data.get('pubchem_mw','?')}")
            else:
                self._enrich_skipped += 1
        except Exception as e:
            self.chem_log.append(f"  ERROR en {ing.name}: {e}")
            self._enrich_skipped += 1

        QTimer.singleShot(0, self._enrich_next)

    def _enrich_done(self):
        self.enrich_btn.setVisible(True)
        self.enrich_stop_btn.setVisible(False)

    def _stop_enrich(self):
        self._abort_enrich = True
        self.chem_log.append("⏏ Deteniendo después del ingrediente actual...")

    # ── PubChem Manual Search & Add ─────────────────────────

    def _pubchem_search(self):
        query = self.pubchem_search.text().strip()
        if not query or len(query) < 2:
            self.chem_log.append("Ingresa al menos 2 caracteres para buscar")
            return
        self.pubchem_results.clear()
        self.pubchem_add_btn.setEnabled(False)
        self.chem_log.append(f"Buscando en PubChem '{query}'...")

        try:
            importer = PubChemImporter()
            results = importer.search_suggestions(query)
            self._pubchem_last_results = results
            if not results:
                self.chem_log.append("  No se encontraron resultados. Prueba un nombre químico más común.")
                return
            for r in results:
                mw = r.get("mw", "?")
                formula = r.get("formula", "?")
                name = r.get("name", "?")
                text = f"{name}  |  {formula}  |  MW={mw}"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, r)
                self.pubchem_results.addItem(item)
            self.chem_log.append(f"  Encontrados {len(results)} resultados")
            self.pubchem_add_btn.setEnabled(True)
        except Exception as e:
            self.chem_log.append(f"ERROR: {e}")

    def _pubchem_add(self):
        item = self.pubchem_results.currentItem()
        if not item:
            self.chem_log.append("Selecciona un resultado primero")
            return
        data = item.data(Qt.UserRole)
        cat = self.pubchem_category.currentText()
        try:
            save_to_custom_ingredients(
                name=data.get("name", data.get("cid", "Unknown")),
                category=cat,
                properties=data,
            )
            self.chem_log.append(f"✓ Añadido '{data.get('name')}' a custom_ingredients.yaml [{cat}]")
        except Exception as e:
            self.chem_log.append(f"ERROR al guardar: {e}")

    # ── Wikipedia Search & Add ──────────────────────────────

    def _wiki_search(self):
        query = self.wiki_search.text().strip()
        if not query or len(query) < 2:
            self.wiki_log.append("Ingresa al menos 2 caracteres para buscar")
            return
        self.wiki_results.clear()
        self.wiki_add_btn.setEnabled(False)
        self.wiki_log.append(f"Buscando en Wikipedia '{query}'...")

        try:
            importer = WikipediaChemicalImporter()
            results = importer.search_chemicals(query)
            self._wiki_last_results = results
            if not results:
                self.wiki_log.append("  No se encontraron datos químicos. Prueba un nombre diferente.")
                return
            for r in results:
                cas = r.get("cas", "?")
                formula = r.get("formula", "?")
                mw = r.get("mw", "?")
                name = r.get("name", "?")
                text = f"{name}  |  {formula}  |  CAS={cas}  |  MW={mw}"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, r)
                self.wiki_results.addItem(item)
            self.wiki_log.append(f"  Encontrados {len(results)} artículos químicos")
            self.wiki_add_btn.setEnabled(True)
        except Exception as e:
            self.wiki_log.append(f"ERROR: {e}")

    def _wiki_add(self):
        item = self.wiki_results.currentItem()
        if not item:
            self.wiki_log.append("Selecciona un resultado primero")
            return
        data = item.data(Qt.UserRole)
        cat = self.wiki_category.currentText()
        try:
            save_to_custom_ingredients(
                name=data.get("name", "Unknown"),
                category=cat,
                properties=data,
            )
            self.wiki_log.append(f"✓ Añadido '{data.get('name')}' a custom_ingredients.yaml [{cat}]")
        except Exception as e:
            self.wiki_log.append(f"ERROR al guardar: {e}")

    def _import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, T("Importar Archivo de Ingredientes"), "",
            T("Data Files (*.yaml *.json);;All Files (*)")
        )
        if not path:
            return

        try:
            with open(path) as f:
                if path.endswith(".json"):
                    data = json.load(f)
                else:
                    data = yaml.safe_load(f)

            self.file_log.append(f"Cargado {path}")
            self.file_log.append(f"Claves raíz: {list(data.keys()) if isinstance(data, dict) else 'lista'}")

            # If it looks like an ingredient list, offer to merge
            if isinstance(data, dict) and any(k in data for k in ["resins", "solvents", "additives"]):
                out_path = str(Path(self.config_dir) / "custom_ingredients.yaml")
                with open(out_path) as f:
                    existing = yaml.safe_load(f) or {}

                for category in ["resins", "solvents", "additives", "pigments"]:
                    if category in data:
                        if category not in existing:
                            existing[category] = []
                        count_before = len(existing[category])
                        existing[category].extend(data[category])
                        self.file_log.append(
                            f"  Añadidos {len(data[category])} {category} "
                            f"(era {count_before}, ahora {len(existing[category])})"
                        )

                with open(out_path, "w") as f:
                    yaml.dump(existing, f, default_flow_style=False)

                self.file_log.append(f"Guardado en {out_path}")

            self.file_log.append("Completado.")

        except Exception as e:
            self.file_log.append(f"ERROR: {e}")

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, T("Importar CSV"), "", T("CSV Files (*.csv);;All Files (*)")
        )
        if not path:
            return

        try:
            import csv
            with open(path, newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            self.file_log.append(f"Cargadas {len(rows)} filas desde {path}")
            if rows:
                self.file_log.append(f"Columnas: {list(rows[0].keys())}")

            # Try to map common CSV columns to our ingredient model
            col_map = {
                'name': ['name', 'product name', 'product_name', 'ingredient', 'material'],
                'type': ['type', 'category', 'function', 'product type'],
                'supplier': ['supplier', 'manufacturer', 'vendor', 'company'],
                'cas': ['cas', 'cas no', 'cas number', 'cas#'],
                'notes': ['notes', 'description', 'comments', 'remarks'],
            }

            self.file_log.append("\nMapeo de columnas sugerido:")
            for target, candidates in col_map.items():
                for col in rows[0].keys():
                    if col.lower() in candidates:
                        self.file_log.append(f"  {target} ← '{col}'")
                        break

            self.file_log.append("\nImportación CSV completada. Para persistir, copia los datos a custom_ingredients.yaml")

        except ImportError:
            self.file_log.append("ERROR: módulo csv no disponible")
        except Exception as e:
            self.file_log.append(f"ERROR: {e}")

    # ── Playwright Markdown Import ──────────────────────────

    def _import_markdown_dir(self, path: str, mode: str = "replace"):
        """Parse markdown files at *path* and load into KB."""
        self.file_log.clear()
        self.file_log.append(f"── Importando archivos markdown desde: {path} ──")
        try:
            import threading as _threading
            def _load():
                def prog(msg):
                    QTimer.singleShot(0, lambda: self.file_log.append(msg))
                if mode == "replace":
                    n = self.kb.build_from_markdown_dir(path, progress_callback=prog)
                else:
                    n = self.kb.append_from_markdown_dir(path, progress_callback=prog)
                self._kb_built = True
                QTimer.singleShot(0, lambda: self.file_log.append(
                    f"✓ {mode.title()} — {n} entradas — "
                    f"{self.kb.total_chunks} fragmentos totales"
                ))
                QTimer.singleShot(0, lambda: self.llm_kb_label.setText(
                    f"Base de conocimiento: {self.kb.total_chunks} fragmentos "
                    f"(desde Playwright markdown)"
                ) if hasattr(self, 'llm_kb_label') else None)
                self.import_log.add("markdown_import", f"{mode}: {n} entradas",
                                    {"entries": n, "mode": mode}, path)

            _threading.Thread(target=_load, daemon=False).start()
        except Exception as e:
            self.file_log.append(f"ERROR: {e}")
            import traceback
            self.file_log.append(traceback.format_exc())

    def _load_playwright_markdown(self):
        from PySide6.QtWidgets import QMessageBox
        path = QFileDialog.getExistingDirectory(
            self, T("Seleccionar directorio de lathetrolls_knowledge_base"), "",
        )
        if not path:
            return

        msg = QMessageBox(self)
        msg.setWindowTitle(T("Modo de Importación"))
        msg.setText(T("Reemplazar limpia la BC antes de importar.\nAñadir agrega a los datos existentes."))
        replace_btn = msg.addButton("Reemplazar", QMessageBox.ActionRole)
        append_btn = msg.addButton("Añadir", QMessageBox.ActionRole)
        cancel_btn = msg.addButton("Cancelar", QMessageBox.RejectRole)
        msg.setDefaultButton(cancel_btn)
        msg.exec()

        if msg.clickedButton() == cancel_btn:
            return
        mode = "replace" if msg.clickedButton() == replace_btn else "append"
        self._import_markdown_dir(path, mode)

    def _import_ltkb(self):
        """Directly import the known lathetrolls knowledge base directory."""
        from PySide6.QtWidgets import QMessageBox
        path = str(Path.home() / "lathetrolls_knowledge_base")
        if not Path(path).is_dir():
            self.file_log.append(f"ERROR: ruta no encontrada: {path}")
            return

        msg = QMessageBox(self)
        msg.setWindowTitle(T("Importar Base de Conocimiento de Lathe Trolls"))
        msg.setText(
            f"{T('Importar desde:')}\n{path}\n\n"
            f"{T('Reemplazar limpia la BC actual antes de importar.')}\n"
            f"{T('Añadir agrega a la BC existente (sin pérdida de datos).')}"
        )
        replace_btn = msg.addButton(T("Reemplazar"), QMessageBox.ActionRole)
        append_btn = msg.addButton(T("Añadir"), QMessageBox.ActionRole)
        cancel_btn = msg.addButton(T("Cancelar"), QMessageBox.RejectRole)
        msg.setDefaultButton(cancel_btn)
        msg.exec()

        if msg.clickedButton() == cancel_btn:
            return

        self.file_log.clear()
        self.file_log.append(f"Analizando archivos markdown en: {path}")
        try:
            from src.data_import import parse_playwright_markdown_dir
            results = parse_playwright_markdown_dir(path)
            if not results:
                self.file_log.append("No se encontraron archivos markdown en ese directorio.")
                return

            total = sum(len(v) for v in results.values())
            self.file_log.append(f"Encontrados {total} mensajes en {len(results)} categorías")

            mode = "replace" if msg.clickedButton() == replace_btn else "append"

            import threading as _threading
            def _load():
                if mode == "replace":
                    n = self.kb.build_from_markdown_dir(path)
                else:
                    n = self.kb.append_from_markdown_dir(path)
                self._kb_built = True
                QTimer.singleShot(0, lambda: self.file_log.append(
                    f"✓ {mode.title()} — {n} entradas — "
                    f"{self.kb.total_chunks} fragmentos totales"
                ))
                QTimer.singleShot(0, lambda: self.llm_kb_label.setText(
                    f"Base de conocimiento: {self.kb.total_chunks} fragmentos "
                    f"(desde lathetrolls_knowledge_base)"
                ) if hasattr(self, 'llm_kb_label') else None)
                self.import_log.add("lathetrolls_import", f"{mode}: {n} entradas",
                                    {"entries": n, "mode": mode}, path)

            _threading.Thread(target=_load, daemon=False).start()
        except Exception as e:
            self.file_log.append(f"ERROR: {e}")
            import traceback
            self.file_log.append(traceback.format_exc())

    # ── Forum Mirror ─────────────────────────────────────────

    def _run_mirror(self):
        import faulthandler, sys, time as _time, threading as _threading

        self.mirror_log.clear()
        self.mirror_btn.setVisible(False)
        self.mirror_stop_btn.setVisible(True)
        self.mirror_progress.setVisible(True)
        self.mirror_progress.setRange(0, 0)

        self.mirror_log.append("Iniciando duplicación del foro mediante Playwright...")
        self.mirror_log.append("Verificando estado de autenticación...")
        if self.scraper.is_authenticated():
            self.mirror_log.append("✓ Autenticado — se abrirá un navegador Chromium para evadir WAF")
        else:
            self.mirror_log.append("⚠ No autenticado. Usa 'Iniciar Sesión con el Navegador' en la pestaña Lathe Trolls primero.")

        self.mirror_log.append("Creando hilo de fondo...")
        sys.stderr.write("[DEBUG _run_mirror] creating MirrorJob + thread\n")
        sys.stderr.flush()

        self._mirror_stop_requested = False

        # Save thread range to settings so MirrorJob can read them
        self.settings.mirror_start_id = self.mirror_start_id.value()
        self.settings.mirror_end_id = self.mirror_end_id.value()

        job = MirrorJob(
            on_progress=self._append_mirror_log,
            on_finished=self._on_mirror_finished,
            on_error=self._on_mirror_error,
            on_done=self._enable_mirror_btn,
            settings=self.settings,
            save_images=False,
            auth_state_path=str(self.scraper._auth_state_path),
        )
        self._mirror_job = job
        self._mirror_thread = _threading.Thread(target=job.run, daemon=True)
        self._mirror_thread.start()

        sys.stderr.write("[DEBUG _run_mirror] thread started\n")
        sys.stderr.flush()
        self.mirror_log.append("(hilo de fondo ejecutándose)")

        # ── Watchdog: if no progress for 120s, dump stacks ──
        self._mirror_watchdog_armed = True
        self._mirror_last_progress = _time.monotonic()

        def watchdog():
            if not self._mirror_watchdog_armed:
                return
            elapsed = _time.monotonic() - self._mirror_last_progress
            if elapsed < 120:
                QTimer.singleShot(5000, watchdog)
                return
            sys.stderr.write("[WATCHDOG] No mirror progress for 120s — dumping stacks\n")
            sys.stderr.flush()
            faulthandler.dump_traceback(file=sys.stderr)
            sys.stderr.flush()
            self.mirror_log.append(
                f"⚠ Sin progreso durante {elapsed:.0f}s — volcando pilas de hilos a stderr"
            )
            self.mirror_log.append(
                "⚠ El navegador puede estar esperando el desafío WAF. Revisa la ventana de Chromium."
            )

        QTimer.singleShot(120000, watchdog)

    @Slot(str)
    def _append_mirror_log(self, msg: str):
        import sys as _sys, time as _time
        _sys.stderr.write(f"[mirror] {msg}\n")
        _sys.stderr.flush()
        self.mirror_log.append(msg)
        # Reset watchdog
        self._mirror_last_progress = _time.monotonic()
        # Auto-scroll to bottom so user always sees latest progress
        scrollbar = self.mirror_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @Slot(str)
    def _on_mirror_error(self, msg: str):
        import sys as _sys
        _sys.stderr.write(f"[mirror ERROR] {msg}\n")
        _sys.stderr.flush()
        self.mirror_log.append(f"ERROR: {msg}")
        self._mirror_watchdog_armed = False

    @Slot()
    def _enable_mirror_btn(self):
        self._mirror_watchdog_armed = False
        self.mirror_btn.setVisible(True)
        self.mirror_stop_btn.setVisible(False)
        self.mirror_progress.setVisible(False)
        self.mirror_progress.setRange(0, 100)

    def _on_mirror_finished(self, md_count: int):
        import sys as _sys
        _sys.stderr.write("[mirror] FINISHED — %d markdown files\n" % md_count)
        _sys.stderr.flush()
        self._mirror_watchdog_armed = False
        self.mirror_progress.setVisible(False)
        self.mirror_btn.setVisible(True)
        self.mirror_stop_btn.setVisible(False)
        self.mirror_export_btn.setEnabled(False)  # export removed — markdown files are the output

        self.mirror_log.append(f"\n=== Duplicación Completada ===")
        self.mirror_log.append(f"  {md_count} archivos markdown escritos en ~/lathetrolls_knowledge_base/")

        if not md_count:
            self.mirror_log.append("  No se escribieron archivos — revisa los registros de Playwright arriba")
            return

        # Auto-load markdown files into the knowledge base
        self.mirror_log.append("")
        self.mirror_log.append("── Cargando en la base de conocimiento ──")
        import threading as _threading
        md_dir = str(Path.home() / "lathetrolls_knowledge_base")
        if not Path(md_dir).is_dir():
            md_dir = str(Path.cwd() / "lathetrolls_knowledge_base")
        def _load():
            try:
                n = self.kb.build_from_markdown_dir(md_dir)
                self._kb_built = True
                QTimer.singleShot(0, lambda: self.mirror_log.append(
                    f"✓ Base de conocimiento construida: {n} entradas listas para P&R"
                ))
                QTimer.singleShot(0, lambda: self.llm_kb_label.setText(
                    f"Base de conocimiento: {self.kb.total_chunks} fragmentos "
                    f"(desde Playwright markdown)"
                ) if hasattr(self, 'llm_kb_label') else None)
                QTimer.singleShot(0, lambda: self.import_log.add(
                    "forum_mirror", f"{md_count} archivos, {n} entradas",
                    {"files": md_count, "entries": n},
                ))
            except Exception as e:
                QTimer.singleShot(0, lambda: self.mirror_log.append(
                    f"✗ Error de importación de BC: {e}"
                ))
            finally:
                QTimer.singleShot(0, self._enable_mirror_btn)
        _threading.Thread(target=_load, daemon=False).start()

    def _stop_mirror(self):
        """Stop the current mirror operation."""
        if hasattr(self, '_mirror_job') and self._mirror_job:
            self._mirror_job._abort = True
            self.mirror_log.append("⏹ Duplicación detenida por el usuario")
        self._mirror_watchdog_armed = False
        self.mirror_btn.setVisible(True)
        self.mirror_stop_btn.setVisible(False)
        self.mirror_progress.setVisible(False)

    # (unified with _run_mirror / _on_mirror_finished above)

    def _export_mirror(self):
        """No-op: markdown files are the output. Button kept for layout but does nothing."""
        QMessageBox.information(self, T("Exportar"),
            T("Los archivos Markdown ya están en el disco en ~/lathetrolls_knowledge_base/\n\n"
            "Para cargarlos en la base de conocimiento RAG, haz clic en 'Duplicar Todas las Categorías' "
            "que ahora importa automáticamente a la BC."))

    def _mirror_import_cache(self):
        """Import a folder of cached JSON files into the knowledge base."""
        folder = QFileDialog.getExistingDirectory(
            self, T("Seleccionar carpeta con archivos JSON en caché"),
            str(self.scraper.cache_dir)
        )
        if not folder:
            return

        import glob
        cache_count = len(glob.glob(f"{folder}/*.json"))
        self.mirror_log.append(f"── Importando {cache_count} archivos de caché desde: {folder} ──")
        self.mirror_import_btn.setEnabled(False)

        self._run_in_thread(
            job_class=CacheImportJob,
            job_args=(self.scraper, folder),
            on_finished=lambda posts: self._on_cache_import_done(posts),
            on_error=lambda err: self.mirror_log.append(f"ERROR: {err}\n"),
            on_done=lambda: self.mirror_import_btn.setEnabled(True),
            on_progress=lambda msg: self.mirror_log.append(msg),
        )

    def _on_cache_import_done(self, posts):
        if not posts:
            self.mirror_log.append("No se encontraron archivos de caché válidos.")
            return
        self.mirror_log.append(f"Añadiendo {len(posts)} mensajes a la base de conocimiento...")
        self.kb.build_from_posts(posts)
        self._kb_built = True
        self.mirror_export_btn.setEnabled(False)  # markdown is the output format
        from collections import Counter
        for cat, count in Counter(p.category for p in posts).most_common():
            self.mirror_log.append(f"  {cat}: {count} mensajes")
        self.mirror_log.append(
            f"\n✓ Importados {len(posts)} mensajes ({self.kb.total_chunks} fragmentos)")
        if hasattr(self, 'llm_kb_label'):
            self.llm_kb_label.setText(
                f"Base de conocimiento: {self.kb.total_chunks} fragmentos")
        self.import_log.add("cache_import", f"{len(posts)} mensajes",
                            {"posts": len(posts)}, "forum_cache")

    def _mirror_backfill_images(self):
        """Download images for all already-cached forum posts (background)."""
        self.mirror_log.append("Rellenando imágenes desde mensajes en caché (fondo)...")
        self.mirror_backfill_btn.setEnabled(False)

        self._run_in_thread(
            job_class=BackfillJob,
            job_args=(self.scraper,),
            on_finished=lambda total: self.mirror_log.append(
                f"\n✓ Descargadas {total} imágenes a data/forum_images/"),
            on_error=lambda err: self.mirror_log.append(f"ERROR: {err}\n"),
            on_done=lambda: self.mirror_backfill_btn.setEnabled(True),
            on_progress=lambda msg: self.mirror_log.append(msg),
        )

    # ── WhatsApp Import ──────────────────────────────────────

    def _wa_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, T("Seleccionar Exportación de WhatsApp"), "", T("Text Files (*.txt);;All Files (*)")
        )
        if path:
            self.wa_file_path.setText(path)
            self.wa_import_btn.setEnabled(True)
            self.wa_preview_file_btn.setEnabled(True)
            self.wa_log.clear()
            self.wa_preview.clear()
            self.wa_log.append(f"Seleccionado: {path}")

    def _wa_preview_file(self):
        fpath = self.wa_file_path.text()
        if not fpath:
            return
        self.wa_preview.clear()
        try:
            msgs = parse_whatsapp_export(fpath)
            self._show_preview(msgs)
        except Exception as e:
            self.wa_log.append(f"ERROR: {e}")

    def _wa_preview_paste(self):
        text = self.wa_paste_area.toPlainText().strip()
        if not text:
            self.wa_log.append("⚠ Pega algo de texto desde WhatsApp Web primero")
            return
        self.wa_preview.clear()
        try:
            msgs = parse_whatsapp_web_text(text)
            self._show_preview(msgs)
        except Exception as e:
            self.wa_log.append(f"ERROR: {e}")

    def _show_preview(self, msgs):
        """Populate the preview list from parsed WhatsAppMessage list."""
        real = [m for m in msgs if not m.is_system_message]
        self.wa_log.append(f"Analizados {len(msgs)} bloques, {len(real)} mensajes reales")
        for m in real[:50]:
            stage = detect_stage(m.text)
            ts = m.timestamp.strftime("%m/%d %H:%M") if m.timestamp else "??"
            text = f"[{ts}] {m.sender} ({stage}): {m.text[:80]}"
            item = QListWidgetItem(text)
            self.wa_preview.addItem(item)
        if len(real) > 50:
            self.wa_preview.addItem(f"... y {len(real) - 50} mensajes más")

    def _wa_import(self):
        fpath = self.wa_file_path.text()
        if not fpath:
            return
        source = self.wa_source.text().strip() or "WhatsApp"
        stage_filter = self.wa_stage_filter.currentText()
        try:
            total, added = import_whatsapp_to_kb(
                fpath, self.kb, source, stage_filter
            )
            self._on_wa_import_done(total, added, source)
        except Exception as e:
            self.wa_log.append(f"ERROR: {e}")
            import traceback
            self.wa_log.append(traceback.format_exc())

    def _wa_import_paste(self):
        text = self.wa_paste_area.toPlainText().strip()
        if not text:
            self.wa_log.append("⚠ Pega algo de texto desde WhatsApp Web primero")
            return
        source = self.wa_source.text().strip() or "WhatsApp Web"
        stage_filter = self.wa_stage_filter.currentText()
        try:
            total, added = import_whatsapp_text_to_kb(
                text, self.kb, source, stage_filter
            )
            self._on_wa_import_done(total, added, source)
        except Exception as e:
            self.wa_log.append(f"ERROR: {e}")
            import traceback
            self.wa_log.append(traceback.format_exc())

    def _on_wa_import_done(self, total: int, added: int, source: str):
        """Common handler after WhatsApp import (file or paste)."""
        self._kb_built = True
        self.wa_log.append(f"✓ Importados {added} mensajes a la base de conocimiento (de {total})")
        if hasattr(self, 'llm_kb_label'):
            self.llm_kb_label.setText(
                f"Base de conocimiento: {len(self.kb.entries)} entradas "
                f"(incluye WhatsApp: {source})")
        from collections import Counter
        stages = Counter(e.category for e in self.kb.entries[-added:])
        self.wa_log.append(f"  Distribución de etapas: {dict(stages)}")
        self.wa_log.append("✓ Conocimiento de WhatsApp listo para P&R en todas las etapas del pipeline")

    # ── LLM Q&A ─────────────────────────────────────────────

    def _llm_refresh(self):
        """Check LM Studio connection status."""
        if self.llm.is_available():
            models = self.llm.list_models()
            status = "🟢 Conectado"
            if models:
                status += f" ({models[0][:50]})"
            self.llm_status.setText(status)
            self.llm_status.setStyleSheet(
                "background: #4CAF50; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;")
            self.llm_answer.append("✓ LM Studio conectado")
        else:
            self.llm_status.setText("🔴 LM Studio no conectado")
            self.llm_status.setStyleSheet(
                "background: #f44336; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;")
            self.llm_answer.append("✗ No se puede alcanzar LM Studio en localhost:1234")

        # Show correction count
        n = len(self.llm.corrections.corrections)
        self.llm_corrections_label.setText(f"{n} correcciones guardadas" if n else "")

        # Update KB status
        if self._kb_built:
            self.llm_kb_label.setText(
                f"Base de conocimiento: {self.kb.total_chunks} fragmentos listos")
        else:
            self.llm_kb_label.setText(
                "Base de conocimiento: vacía (duplica el foro en la pestaña Duplicar Foro primero)")

    def _llm_open_settings(self):
        """Open RAG settings dialog."""
        models = []
        if self.llm and self.llm.is_available():
            try:
                models = self.llm.list_models()
            except Exception:
                pass
        dlg = RAGSettingsDialog(self.settings, models, self)
        if dlg.exec():
            self.llm.api_url = self.settings.api_url
            self.llm.model = self.settings.model

    def _llm_toggle_rag(self, visible: bool):
        self.llm_rag_widget.setVisible(visible)
        self.llm_rag_details_btn.setText(
            "▼ Ocultar detalles del pipeline RAG" if visible
            else "▶ Mostrar detalles del pipeline RAG"
        )

    def _llm_ask(self):
        """Ask a question to the LLM with forum knowledge as context."""
        question = self.llm_question.text().strip()
        if not question:
            return
        self._last_llm_question = question

        if not self._kb_built:
            self.kb.build_from_fallback()
            self._kb_built = True
            self.llm_answer.append("ℹ Usando conocimiento incorporado (duplica el foro para más profundidad)")

        # Search
        top_k = self.settings.top_k
        snippets = self.kb.search(question, max_results=top_k)
        self._last_llm_matches = snippets
        self.llm_snippets.clear()
        context_parts = []
        for entry in snippets:
            context_parts.append(
                f"[{entry.category}] {entry.title}\n{entry.content[:500]}"
            )
            item = QListWidgetItem(f"[{entry.category}] {entry.title[:60]}")
            self.llm_snippets.addItem(item)

        context = "\n\n---\n\n".join(context_parts) if context_parts else ""
        self._last_llm_context = context

        # Show RAG details
        self.llm_rag_chunks.setPlainText(
            "\n".join(
                f"[{e.category}] {e.title} ({len(e.content)} chars)\n"
                f"  {e.content[:150]}..."
                for e in snippets
            ) if snippets else "(no hay conocimiento coincidente)"
        )
        messages = []
        if context:
            sys_content = self.settings.system_prompt.replace(
                "{context}", context[:self.settings.context_chars]
            )
            messages.append({"role": "system", "content": sys_content})
        messages.append({"role": "user", "content": question})
        self.llm_rag_prompt.setPlainText(
            json.dumps(messages, indent=2, ensure_ascii=False)
        )
        if self.settings.show_rag_details:
            self.llm_rag_details_btn.setText("▼ Ocultar detalles del pipeline RAG")
            self.llm_rag_widget.setVisible(True)

        self.llm_answer.append(f"\n--- P: {question} ---")
        self.llm_answer.append("Pensando...")
        self.llm_ask_btn.setEnabled(False)
        self.llm_question.setEnabled(False)

        # Run LLM in background thread (no QTimer — avoids SIGSEGV on dialog close)
        self._llm_thread = QThread(self)
        self._llm_job = LLMAskJob(
            self.llm, question, context,
            max_tokens=self.settings.max_tokens,
            temperature=self.settings.temperature,
            context_chars=self.settings.context_chars,
        )
        self._llm_job.moveToThread(self._llm_thread)
        self._llm_thread.started.connect(self._llm_job.run)
        self._llm_job.finished.connect(self._on_llm_answer, Qt.QueuedConnection)
        self._llm_job.error.connect(self._on_llm_error, Qt.QueuedConnection)
        self._llm_thread.finished.connect(self._llm_job.deleteLater)
        self._llm_thread.finished.connect(self._llm_thread.deleteLater)
        self._llm_thread.start()

    def _on_llm_answer(self, answer: str):
        text = self.llm_answer.toPlainText()
        text = text.replace("\nPensando...", "")
        self.llm_answer.setPlainText(text)
        self.llm_answer.append(f"\n{answer}")
        self.llm_ask_btn.setEnabled(True)
        self.llm_question.setEnabled(True)
        self.llm_correct_btn.setEnabled(True)
        self.llm_correct_widget.setVisible(False)
        self.llm_inspect_btn.setVisible(True)
        self._last_llm_answer = answer
        # Update correction count
        n = len(self.llm.corrections.corrections)
        self.llm_corrections_label.setText(f"{n} correcciones" if n else "")

    def _llm_open_inspector(self):
        from .rag_inspector import RagInspectorDialog
        chunks = []
        for m in getattr(self, '_last_llm_matches', []):
            chunks.append({
                "source": m.source,
                "title": m.title,
                "content": m.content,
                "category": m.category,
                "keywords": m.keywords,
                "score": 0,
                "length": len(m.content),
            })
        dlg = RagInspectorDialog(
            self,
            question=getattr(self, '_last_llm_question', ''),
            answer=getattr(self, '_last_llm_answer', ''),
            retrieved_chunks=chunks,
            context=getattr(self, '_last_llm_context', ''),
            stage="all",
        )
        dlg.exec()

    def _on_llm_error(self, err: str):
        self.llm_answer.append(f"ERROR: {err}")
        self.llm_ask_btn.setEnabled(True)
        self.llm_question.setEnabled(True)

    # ── Correction / Feedback ──────────────────────────────────

    def _llm_start_correct(self):
        answer = self.llm_answer.toPlainText()
        if not answer:
            return
        self.llm_correct_edit.setPlainText(answer)
        self.llm_correct_widget.setVisible(True)
        self.llm_correct_btn.setEnabled(False)

    def _llm_cancel_correct(self):
        self.llm_correct_widget.setVisible(False)
        self.llm_correct_btn.setEnabled(True)

    def _llm_save_correction(self):
        question = self._last_llm_question
        wrong = self.llm_answer.toPlainText()
        correct = self.llm_correct_edit.toPlainText().strip()
        if not correct:
            return
        self.llm.corrections.add(question, wrong, correct)
        self.llm_correct_widget.setVisible(False)
        self.llm_correct_btn.setEnabled(False)
        n = len(self.llm.corrections.corrections)
        self.llm_corrections_label.setText(f"{n} correcciones guardadas")
        self.llm_answer.append(
            f"\n\n✓ Corrección guardada — las respuestas futuras usarán la versión corregida"
        )

    # ── Knowledge sanitization ─────────────────────────────────

    def _llm_sanitize(self):
        if not self._kb_built or not self.kb.entries:
            self.llm_answer.append("⚠ No hay entradas de conocimiento para sanitizar.")
            return
        if not self.llm.is_available():
            self.llm_answer.append("⚠ LLM no conectado. Inicia LM Studio primero.")
            return

        self.llm_sanitize_btn.setEnabled(False)
        total_entries = len(self.kb.entries)
        self.llm_answer.append(f"\n🧹 Sanitizando {total_entries} entradas (fondo)...")

        self._run_in_thread(
            job_class=SanitizeJob,
            job_args=(self.llm, self.kb.entries),
            on_finished=lambda n: (
                self.llm_answer.append(f"\n✓ Sanitización completada — {n} entradas limpiadas"),
                self.import_log.add("sanitize", f"{n}/{total_entries} entradas limpiadas",
                                    {"cleaned": n, "total": total_entries}),
            ),
            on_error=lambda err: self.llm_answer.append(f"ERROR: {err}\n"),
            on_done=lambda: self.llm_sanitize_btn.setEnabled(True),
            on_progress=lambda msg: self.llm_answer.append(msg),
        )

    # ── PDF / Scanned Books ──────────────────────────────────

    def _pdf_deps_and_files_ok(self) -> bool:
        ok, _ = check_pdf_deps()
        return ok and self.pdf_file_list.count() > 0

    def _update_pdf_import_btn(self):
        self.pdf_import_btn.setEnabled(self._pdf_deps_and_files_ok())

    def _pdf_check_deps(self):
        target_lang = self.pdf_lang_combo.currentText().strip() or None
        ok, msg = check_pdf_deps(target_langs=[target_lang] if target_lang else None)
        self.pdf_dep_status.setText(msg)
        self._update_pdf_import_btn()
        # Populate language combo with installed Tesseract languages
        if ok:
            try:
                langs = get_available_languages()
                self.pdf_lang_combo.clear()
                self.pdf_lang_combo.addItems(langs)
                # Select eng by default if available
                idx = self.pdf_lang_combo.findText("eng")
                if idx >= 0:
                    self.pdf_lang_combo.setCurrentIndex(idx)
            except Exception:
                pass

    def _pdf_install_deps(self):
        """Install missing PDF/OCR dependencies via pip in a background thread."""
        import threading, subprocess, sys as _sys
        from pathlib import Path as _Path
        self.pdf_dep_status.setText("Instalando dependencias...")
        self.pdf_install_btn.setEnabled(False)
        self.pdf_install_btn.setText("Instalando...")

        def _install():
            try:
                target_lang = self.pdf_lang_combo.currentText().strip() or None
                pkgs = []
                ok, msg = check_pdf_deps(target_langs=[target_lang] if target_lang else None)
                if "PyMuPDF" in msg:
                    pkgs.append("PyMuPDF")
                if "pytesseract" in msg:
                    pkgs.append("pytesseract")

                if pkgs:
                    label = " ".join(pkgs)
                    self._append_pdf_log(f"Instalando paquetes Python: {label}")
                    cmd = [_sys.executable, "-m", "pip", "install", "--break-system-packages"] + pkgs
                    proc = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, bufsize=1,
                    )
                    for line in proc.stdout:
                        line = line.rstrip()
                        if line:
                            self._append_pdf_log(f"  {line}")
                    proc.wait()
                    if proc.returncode != 0:
                        self.pdf_dep_status_signal.emit(f"pip install falló (exit {proc.returncode})")
                        return
                    self._append_pdf_log("✓ Paquetes Python instalados.")

                # Install missing Tesseract language packs
                tess_dir = _Path.home() / ".tesseract" / "tessdata"
                tess_dir.mkdir(parents=True, exist_ok=True)
                if target_lang:
                    from src.pdf_import import get_available_languages
                    installed = set(get_available_languages())
                    for part in target_lang.split("+"):
                        part = part.strip()
                        if part and part not in installed:
                            url = f"https://github.com/tesseract-ocr/tessdata/raw/main/{part}.traineddata"
                            dest = tess_dir / f"{part}.traineddata"
                            self._append_pdf_log(f"Descargando idioma '{part}'...")
                            try:
                                import urllib.request
                                urllib.request.urlretrieve(url, str(dest))
                                self._append_pdf_log(f"  ✓ {part}.traineddata ({dest.stat().st_size // 1024} KB)")
                            except Exception as e:
                                self._append_pdf_log(f"  ✗ Descarga fallida: {e}")

                self._append_pdf_log("✓ Instalación completada.")
                self.pdf_dep_status_signal.emit("Verificando dependencias...")
                self.pdf_deps_check_signal.emit()
            except Exception as e:
                self.pdf_dep_status_signal.emit(f"Error de instalación: {e}")
            finally:
                self.pdf_install_done_signal.emit()

        threading.Thread(target=_install, daemon=False).start()

    def _on_pdf_install_log(self, msg: str):
        self.pdf_log.append(msg)
        self.pdf_log.verticalScrollBar().setValue(
            self.pdf_log.verticalScrollBar().maximum()
        )

    def _on_pdf_install_done(self):
        self.pdf_install_btn.setEnabled(True)
        self.pdf_install_btn.setText("Instalar Dependencias")

    def _append_pdf_log(self, msg: str):
        self.pdf_install_log_signal.emit(msg)

    def _pdf_add_pdf(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, T("Seleccionar archivos PDF"), "", T("PDF Files (*.pdf)")
        )
        for f in files:
            item = QListWidgetItem(f)
            self.pdf_file_list.addItem(item)
        self._update_pdf_import_btn()

    def _pdf_add_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, T("Seleccionar carpeta con imágenes de páginas escaneadas")
        )
        if not folder:
            return
        from src.pdf_import import SUPPORTED_IMAGE_EXTS
        folder_path = Path(folder)
        images = [p for p in folder_path.iterdir()
                  if p.suffix.lower() in SUPPORTED_IMAGE_EXTS]
        item = QListWidgetItem(f"📁 {folder}  ({len(images)} imágenes)")
        item.setData(Qt.UserRole, ("folder", folder))
        self.pdf_file_list.addItem(item)
        self._update_pdf_import_btn()

    def _pdf_add_archive(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, T("Seleccionar archivos ZIP/RAR"), "",
            T("Archives (*.zip *.rar)")
        )
        from src.pdf_import import SUPPORTED_ARCHIVE_EXTS
        for f in files:
            f_path = Path(f)
            item = QListWidgetItem(f"🗜 {f}  ({f_path.suffix})")
            item.setData(Qt.UserRole, ("archive", f))
            self.pdf_file_list.addItem(item)
        self._update_pdf_import_btn()

    def _pdf_import(self):
        if self._pdf_job is not None:
            self.pdf_log.append("⚠ Importación ya en progreso — espera a que termine.\n")
            return
        count = self.pdf_file_list.count()
        if not count:
            return
        logger.info("PDF import start items=%d lang=%s", count, self.pdf_lang_combo.currentText())

        self.pdf_import_btn.setEnabled(False)
        self.pdf_check_btn.setEnabled(False)
        self.pdf_progress.setVisible(True)
        self.pdf_progress.setRange(0, 0)
        self.pdf_log.clear()
        labels = []
        for idx in range(count):
            item = self.pdf_file_list.item(idx)
            labels.append(item.text().rsplit("/", 1)[-1][:40])
        self.pdf_log.append(f"── Importando {count} elementos ──")
        for lbl in labels:
            self.pdf_log.append(f"  • {lbl}")
        self.pdf_log.append("")

        source_prefix = self.pdf_source_input.text().strip() or "Scanned Book"
        lang = self.pdf_lang_combo.currentText().strip() or "eng"

        self._pdf_entry_count_before = len(self.kb.entries)

        items = []
        for idx in range(count):
            item = self.pdf_file_list.item(idx)
            kind = "pdf"
            path = item.text()
            user_data = item.data(Qt.UserRole)
            if user_data:
                kind, path = user_data
            items.append((kind, path))

        job, thread = self._run_in_thread(
            job_class=PdfImportJob,
            job_args=(items, self.kb, source_prefix, lang),
            on_finished=lambda total: self._on_pdf_done(total, source_prefix),
            on_error=self._on_pdf_error,
            on_done=self._on_pdf_always,
            on_progress=self._on_pdf_progress,
            on_page_progress=self._on_pdf_page_progress,
        )
        self._pdf_job = job
        self._pdf_thread = thread
        self._pdf_start_preview()

    def _pdf_start_preview(self):
        self.pdf_preview_image.clear()
        self.pdf_preview_image.setText("Esperando páginas...")
        self.pdf_preview_ocr.clear()
        self.pdf_preview_page_label.setText("")
        self.pdf_prev_btn.setEnabled(False)
        self.pdf_next_btn.setEnabled(False)
        self.pdf_remove_btn.setEnabled(False)
        self.pdf_undo_btn.setVisible(False)
        self.pdf_undo_label.setText("")
        self._pdf_pages.clear()
        self._pdf_current_page = -1
        self.pdf_stop_btn.setVisible(True)
        self.pdf_import_btn.setEnabled(False)
        self.pdf_check_btn.setEnabled(False)

    def _pdf_stop_import(self, force_kill_after_ms=5000):
        logger.warning("PDF import stop requested by user")
        if self._pdf_job:
            self._pdf_job._abort = True
        self.pdf_stop_btn.setEnabled(False)
        self.pdf_stop_btn.setText("⏹ Deteniendo...")
        self.pdf_log.append("⏹ Detención solicitada, finalizando página actual...\n")

        if self._pdf_thread and self._pdf_thread.isRunning():
            from PySide6.QtCore import QTimer, QThread
            QTimer.singleShot(force_kill_after_ms, lambda: self._pdf_force_kill())

    def _pdf_force_kill(self):
        if self._pdf_thread and self._pdf_thread.isRunning():
            logger.warning("PDF import thread did not finish after abort — force terminating")
            self.pdf_log.append("⏹ Forzando terminación de hilo atascado...\n")
            self._pdf_thread.terminate()
            self._pdf_thread.wait(3000)
            # Ensure the "always" cleanup runs regardless
            self._on_pdf_always()

    def _on_pdf_page_progress(self, image_path: str, page_num: int, ocr_text: str):
        logger.debug("page progress page=%d img=%s ocr_len=%d", page_num, image_path, len(ocr_text))
        self._pdf_pages.append((image_path, page_num, ocr_text))
        self._pdf_current_page = len(self._pdf_pages) - 1
        self._pdf_show_page(self._pdf_current_page)

    def _pdf_show_page(self, idx: int):
        if idx < 0 or idx >= len(self._pdf_pages):
            return
        self._pdf_current_page = idx
        image_path, page_num, ocr_text = self._pdf_pages[idx]
        self.pdf_prev_btn.setEnabled(idx > 0)
        self.pdf_next_btn.setEnabled(idx < len(self._pdf_pages) - 1)
        self.pdf_remove_btn.setEnabled(True)
        if image_path:
            try:
                from PySide6.QtGui import QPixmap
                try:
                    from PIL import Image as _PIL
                    _PIL.open(image_path).verify()
                except Exception:
                    self.pdf_preview_image.setText(f"[Imagen: {Path(image_path).name}]")
                else:
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(
                            400, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                        self.pdf_preview_image.setPixmap(scaled)
                    else:
                        self.pdf_preview_image.setText(f"[Imagen: {Path(image_path).name}]")
            except Exception as e:
                logger.error("page progress image load error: %s", e)
                self.pdf_preview_image.setText(f"[Imagen: {Path(image_path).name}]")
        self.pdf_preview_ocr.setPlainText(ocr_text[:2000])
        self.pdf_preview_page_label.setText(f"Página {page_num} ({idx + 1}/{len(self._pdf_pages)})")

    def _pdf_prev_page(self):
        self._pdf_show_page(self._pdf_current_page - 1)

    def _pdf_next_page(self):
        self._pdf_show_page(self._pdf_current_page + 1)

    def _pdf_remove_page(self):
        idx = self._pdf_current_page
        if idx < 0 or idx >= len(self._pdf_pages):
            return
        entry_idx = self._pdf_entry_count_before + idx
        if entry_idx < len(self.kb.entries):
            removed = self.kb.entries.pop(entry_idx)
            self.pdf_log.append(f"✕ Página eliminada: {removed.title}\n")
        self._pdf_pages.pop(idx)
        if not self._pdf_pages:
            self.pdf_preview_image.clear()
            self.pdf_preview_image.setText("Sin imagen")
            self.pdf_preview_ocr.clear()
            self.pdf_preview_page_label.setText("")
            self.pdf_prev_btn.setEnabled(False)
            self.pdf_next_btn.setEnabled(False)
            self.pdf_remove_btn.setEnabled(False)
            self._pdf_current_page = -1
        else:
            self._pdf_show_page(min(idx, len(self._pdf_pages) - 1))

    def _pdf_undo_import(self):
        count = self._pdf_last_import_count
        if count <= 0 or self._pdf_entry_count_before < 0:
            return
        while len(self.kb.entries) > self._pdf_entry_count_before:
            self.kb.entries.pop()
        self.pdf_log.append(f"↩ Última importación deshecha — {count} entradas eliminadas\n")
        self.pdf_undo_btn.setVisible(False)
        self.pdf_undo_label.setText("")
        self._pdf_pages.clear()
        self._pdf_current_page = -1
        self.pdf_preview_image.clear()
        self.pdf_preview_image.setText("Sin imagen")
        self.pdf_preview_ocr.clear()
        self.pdf_preview_page_label.setText("")
        self.pdf_prev_btn.setEnabled(False)
        self.pdf_next_btn.setEnabled(False)
        self.pdf_remove_btn.setEnabled(False)

    def _on_pdf_progress(self, msg: str):
        self.pdf_log.append(msg + "\n")
        self.pdf_log.verticalScrollBar().setValue(
            self.pdf_log.verticalScrollBar().maximum()
        )

    def _on_pdf_error(self, err: str):
        logger.error("PDF import error: %s", err)
        self.pdf_log.append(f"ERROR: {err}\n")

    def _on_pdf_always(self):
        self.pdf_import_btn.setEnabled(True)
        self.pdf_check_btn.setEnabled(True)
        self.pdf_progress.setRange(0, 1)
        self.pdf_progress.setValue(1)
        self.pdf_stop_btn.setVisible(False)
        self.pdf_stop_btn.setEnabled(True)
        self.pdf_stop_btn.setText("⏹ Detener")
        self._pdf_job = None
        self._pdf_thread = None

    def _on_pdf_done(self, total_pages: int, source_prefix: str):
        self._kb_built = True
        self.kb.save()
        logger.info("PDF import done total_pages=%d source=%s", total_pages, source_prefix)
        self.pdf_log.append(f"\n✓ ¡Completado! {total_pages} páginas añadidas a la base de conocimiento")
        if hasattr(self, 'llm_kb_label'):
            self.llm_kb_label.setText(
                f"Base de conocimiento: {len(self.kb.entries)} entradas "
                f"(incluye PDF: {source_prefix})")
        self.import_log.add("pdf_import", f"{total_pages} páginas",
                            {"pages": total_pages},
                            source_prefix)
        self._pdf_last_import_count = len(self.kb.entries) - self._pdf_entry_count_before
        if self._pdf_last_import_count > 0:
            self.pdf_undo_btn.setVisible(True)
            self.pdf_undo_label.setText(
                f"La última importación añadió {self._pdf_last_import_count} entradas — haz clic en Deshacer para eliminarlas"
            )

    # ── Patent import ───────────────────────────────────────

    def _patent_import(self):
        text = self.patent_input.toPlainText().strip()
        if not text:
            return
        numbers = [line.strip() for line in text.splitlines() if line.strip()]
        numbers = [n.replace(" ", "") for n in numbers]
        if not numbers:
            return

        logger.info("Patent import start count=%d", len(numbers))
        self.patent_import_btn.setEnabled(False)
        self.patent_progress.setVisible(True)
        self.patent_progress.setRange(0, 0)
        self.patent_log.clear()
        self.patent_log.append(f"── Importando {len(numbers)} patentes ──")

        job, thread = self._run_in_thread(
            job_class=PatentImportJob,
            job_args=(numbers, self.kb, "Google Patent"),
            on_finished=self._on_patent_done,
            on_error=self._on_patent_error,
            on_done=self._on_patent_always,
            on_progress=self._on_patent_progress,
        )
        self._patent_job = job
        self._patent_thread = thread

    def _on_patent_progress(self, msg: str):
        self.patent_log.append(msg + "\n")
        self.patent_log.verticalScrollBar().setValue(
            self.patent_log.verticalScrollBar().maximum()
        )

    def _on_patent_error(self, err: str):
        logger.error("Patent import error: %s", err)
        self.patent_log.append(f"ERROR: {err}\n")

    def _on_patent_always(self):
        self.patent_import_btn.setEnabled(True)
        self.patent_progress.setRange(0, 1)
        self.patent_progress.setValue(1)
        self._patent_job = None
        self._patent_thread = None

    def _on_patent_done(self, total: int):
        self.kb.save()
        logger.info("Patent import done total=%d", total)
        self.patent_log.append(f"\n✓ ¡Completado! {total} patentes añadidas a la base de conocimiento")
        self._kb_built = True
