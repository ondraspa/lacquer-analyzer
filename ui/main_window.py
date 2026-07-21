"""Ventana principal de la GUI — organizada por áreas funcionales."""

import sys
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QStatusBar, QMessageBox,
    QSplitter, QToolBar, QPushButton, QDialog, QComboBox,
)
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QAction, QIcon, QFont

from ui.pipeline.cutting_stage import CuttingStageWidget
from ui.pipeline.base_stage import PipelineStageWidget
from ui.workspace.galvanics_workspace import GalvanicsWorkspace
from ui.workspace.pressing_workspace import PressingWorkspace
from ui.workspace.knowledge_hub import KnowledgeHub
from ui.imports.tool_dialogs import DataImportDialog, ExpertNotesDialog
from ui.knowledge.explorer import DataExplorerDialog
from src.ingredient_loader import IngredientLoader
from src.llm_integration import LocalLLM, ForumKnowledgeBase
from src.rag_config import RAGSettings
from core.translations import T, translator


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.rag_settings = RAGSettings.load()
        self.ingredient_loader = IngredientLoader(
            str(Path(__file__).parent.parent / "config")
        )
        self.llm = LocalLLM(
            api_url=self.rag_settings.api_url,
            model=self.rag_settings.model,
        )
        self.kb = ForumKnowledgeBase(
            cache_dir=self.rag_settings.forum_cache_dir,
            chunk_size=self.rag_settings.chunk_size,
            persist_path="data/knowledge_base.json",
        )
        self.current_recipe_path: Optional[str] = None
        self._data_import_dialog: Optional[DataImportDialog] = None
        self._init_ui()
        self._init_menu()
        self._load_data()
        # Conectar cambio de idioma
        translator.language_changed.connect(self._on_language_changed)

    def _init_ui(self):
        self.setWindowTitle("Analizador de Laca — Fabricación de Discos de Laca")
        self.setMinimumSize(1400, 900)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QToolBar("Herramientas")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))

        self.llm_status_btn = QPushButton("LLM: verificar")
        self.llm_status_btn.clicked.connect(self._check_llm)
        self.llm_status_btn.setToolTip("Verifica la conexión con el servidor LLM (LM Studio). Muestra el estado en el botón")
        toolbar.addWidget(self.llm_status_btn)

        self.kb_status_btn = QPushButton("BC: vacía")
        self.kb_status_btn.clicked.connect(self._open_kb_browser)
        self.kb_status_btn.setToolTip("Abre el navegador de la base de conocimiento: busca, navega y gestiona entradas")
        toolbar.addWidget(self.kb_status_btn)

        toolbar.addSeparator()

        expert_btn = QPushButton("📝 Notas de Experto")
        expert_btn.setToolTip("Abre el bloc de notas de experto: temas de referencia y notas personales")
        expert_btn.clicked.connect(self._open_expert_notes)
        toolbar.addWidget(expert_btn)

        rag_btn = QPushButton("⚙ Configuración RAG")
        rag_btn.clicked.connect(self._open_rag_settings)
        rag_btn.setToolTip("Configura el pipeline RAG: conexión LLM, generación, recuperación y agentes")
        toolbar.addWidget(rag_btn)

        toolbar.addSeparator()

        gen_btn = QPushButton("🎯 Generar Receta")
        gen_btn.clicked.connect(self._generate_from_spec)
        gen_btn.setToolTip("Genera una formulación automática a partir de especificaciones (viscosidad, sólidos, curado)")
        toolbar.addWidget(gen_btn)

        toolbar.addSeparator()

        # Language selector
        import sys as _sys
        from PySide6.QtWidgets import QComboBox
        self.lang_selector = QComboBox()
        self.lang_selector.addItem("EN", "en")
        self.lang_selector.addItem("ES", "es")
        self.lang_selector.setCurrentIndex(1)  # ES por defecto
        self.lang_selector.setToolTip("Cambia el idioma de la interfaz entre Español e Inglés")
        self.lang_selector.currentIndexChanged.connect(
            lambda i: translator.set_language(self.lang_selector.itemData(i))
        )
        toolbar.addWidget(QLabel("  🌐 "))
        toolbar.addWidget(self.lang_selector)

        layout.addWidget(toolbar)

        # Main area tabs
        self.main_tabs = QTabWidget()
        self.main_tabs.setToolTip("Pestañas principales del flujo de trabajo:\n• Formulación — formulación de lacas\n• Galvánica — parámetros de baños\n• Prensado — parámetros de prensado\n• Control de Calidad — defectos y solución de problemas\n• Conocimiento — base de conocimiento y RAG")
        self.main_tabs.currentChanged.connect(self._on_tab_changed)

        # Tab 1: Formulación
        self.cutting_stage = CuttingStageWidget(self.ingredient_loader)
        self.cutting_stage.analysis_requested.connect(self._on_analysis_complete)
        self.cutting_stage.translate_requested.connect(self._on_translate_requested)
        self.main_tabs.addTab(self.cutting_stage, "🧪 Formulación")

        # Tab 2: Galvánica
        self.galvanics_tab = GalvanicsWorkspace()
        self.main_tabs.addTab(self.galvanics_tab, "⚡ Galvánica")

        # Tab 3: Prensado
        self.pressing_tab = PressingWorkspace()
        self.main_tabs.addTab(self.pressing_tab, "🔄 Prensado")

        # Tab 4: Control de Calidad
        self.qc_stage = PipelineStageWidget("qc")
        self.main_tabs.addTab(self.qc_stage, "🔍 Control de Calidad")

        # Tab 5: Conocimiento
        self.knowledge_hub = KnowledgeHub()
        self.main_tabs.addTab(self.knowledge_hub, "🧠 Conocimiento")

        layout.addWidget(self.main_tabs, 1)

        self.statusBar().showMessage("Listo")

    def _init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Archivo")
        import_action = QAction("Importar Receta (JSON/YAML)", self)
        import_action.setToolTip("Importa una receta desde un archivo YAML o JSON")
        import_action.triggered.connect(self._import_recipe)
        file_menu.addAction(import_action)

        export_action = QAction("Exportar Receta", self)
        export_action.setToolTip("Exporta la receta actual a un archivo YAML")
        export_action.triggered.connect(self._export_recipe)
        file_menu.addAction(export_action)

        file_menu.addSeparator()
        exit_action = QAction("Salir", self)
        exit_action.setToolTip("Cierra la aplicación")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        tools_menu = menubar.addMenu("Herramientas")
        data_action = QAction("Importar Datos...", self)
        data_action.setToolTip("Abre el importador de datos: foros, PubChem, Wikipedia, PDFs, etc.")
        data_action.triggered.connect(self._open_data_import)
        tools_menu.addAction(data_action)

        expert_action = QAction("Notas de Experto...", self)
        expert_action.setToolTip("Abre el bloc de notas de experto con temas de referencia")
        expert_action.triggered.connect(self._open_expert_notes)
        tools_menu.addAction(expert_action)

        tools_menu.addSeparator()

        ing_action = QAction("Editor de Ingredientes...", self)
        ing_action.setToolTip("Abre el editor para añadir o modificar ingredientes en la base de datos")
        ing_action.triggered.connect(self._open_ingredient_editor)
        tools_menu.addAction(ing_action)

        plating_action = QAction("Editor de Reglas de Galvánica...", self)
        plating_action.setToolTip("Edita las reglas de formulación para baños galvánicos (plata, níquel)")
        plating_action.triggered.connect(self._open_plating_rules)
        tools_menu.addAction(plating_action)

        defect_action = QAction("Editor de Defectos...", self)
        defect_action.setToolTip("Gestiona la base de datos de defectos: añade, edita o elimina entradas")
        defect_action.triggered.connect(self._open_defect_editor)
        tools_menu.addAction(defect_action)

        tools_menu.addSeparator()

        gen_action = QAction("Generar Formulación desde Especificación...", self)
        gen_action.setToolTip("Genera una receta automática a partir de especificaciones técnicas")
        gen_action.triggered.connect(self._generate_from_spec)
        tools_menu.addAction(gen_action)

        settings_action = QAction("Configuración RAG...", self)
        settings_action.setToolTip("Configura el pipeline RAG, los agentes LLM y los parámetros de búsqueda")
        settings_action.triggered.connect(self._open_rag_settings)
        tools_menu.addAction(settings_action)

        help_menu = menubar.addMenu("Ayuda")
        guide_action = QAction("📖 Guía de uso", self)
        guide_action.setToolTip("Abre una guía completa sobre cómo usar cada sección de la aplicación")
        guide_action.triggered.connect(self._show_usage_guide)
        help_menu.addAction(guide_action)
        about_action = QAction("Acerca de", self)
        about_action.setToolTip("Muestra información sobre la aplicación y la versión")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _load_data(self):
        self.ingredient_loader.load_all()
        self.cutting_stage.ingredient_browser.refresh()
        self.cutting_stage.recipe_editor.refresh_selector()
        self._update_stage_settings()
        self._check_llm()
        self._retranslate_ui()

    def _on_language_changed(self, lang: str):
        self._retranslate_ui()

    def _retranslate_ui(self):
        self.setWindowTitle(T("app_title"))
        self.main_tabs.setTabText(0, "🧪 " + T("components_tab"))
        self.main_tabs.setTabText(1, "⚡ " + T("plating_recipes"))
        self.statusBar().showMessage(T("loading") if False else "Listo" if translator.current_language == "es" else "Ready")

    def _update_stage_settings(self):
        for tab_name in ("cutting_stage", "galvanics_tab", "pressing_tab", "qc_stage", "knowledge_hub"):
            w = getattr(self, tab_name, None)
            if w and hasattr(w, 'set_settings'):
                w.set_settings(self.rag_settings)

    def _update_stage_knowledge(self):
        for tab_name in ("cutting_stage", "galvanics_tab", "pressing_tab", "qc_stage", "knowledge_hub"):
            w = getattr(self, tab_name, None)
            if w:
                if hasattr(w, 'set_llm'):
                    w.set_llm(self.llm)
                if hasattr(w, 'set_knowledge_base'):
                    w.set_knowledge_base(self.kb)

    def _on_tab_changed(self, index):
        w = self.main_tabs.widget(index)
        if w:
            if hasattr(w, 'set_llm'):
                w.set_llm(self.llm)
            if hasattr(w, 'set_knowledge_base'):
                w.set_knowledge_base(self.kb)
            if isinstance(w, KnowledgeHub):
                w.set_kb_and_llm(self.kb, self.llm, self.rag_settings)

    # ── Dialog actions ──

    def _open_data_import(self):
        dlg = DataImportDialog(self, self.llm, self.kb, self.rag_settings)
        self._data_import_dialog = dlg
        dlg.finished.connect(self._on_data_import_closed)
        dlg.show()

    def _on_data_import_closed(self, result):
        if self._data_import_dialog:
            self._update_kb_status()
            self._update_stage_knowledge()
            n = len(self.kb.entries) if self.kb else 0
            self.statusBar().showMessage(f"Base de conocimiento actualizada ({n} entradas totales)")
            self._data_import_dialog = None

    def _open_expert_notes(self):
        dlg = ExpertNotesDialog(self)
        dlg.exec()

    def _open_ingredient_editor(self):
        from ui.workspace.ingredient_editor import IngredientEditorDialog
        dlg = IngredientEditorDialog(self.ingredient_loader, self)
        if dlg.exec():
            self.ingredient_loader.load_all()
            self.cutting_stage.ingredient_browser.refresh()
            self.cutting_stage.recipe_editor.refresh_selector()
            self.statusBar().showMessage("Base de datos de ingredientes actualizada")

    def _open_plating_rules(self):
        from ui.workspace.plating_rules_editor import PlatingRulesEditorDialog
        dlg = PlatingRulesEditorDialog(self)
        dlg.exec()

    def _open_defect_editor(self):
        from ui.workspace.defect_editor import DefectEditorDialog
        dlg = DefectEditorDialog(self)
        dlg.exec()

    def _generate_from_spec(self):
        from ui.workspace.generate_formulation import GenerateFormulationDialog
        dlg = GenerateFormulationDialog(self.ingredient_loader, self)
        if dlg.exec():
            recipe = dlg.get_recipe()
            self.cutting_stage.recipe_editor.set_recipe(recipe)
            self.main_tabs.setCurrentIndex(0)
            self.statusBar().showMessage("Formulación generada cargada en etapa de Formulación")

    def _check_llm(self):
        if self.llm.is_available():
            models = self.llm.list_models()
            label = "LLM"
            if models:
                label += f" ({models[0][:40]})"
            self.llm_status_btn.setText(label)
            self.llm_status_btn.setStyleSheet(
                "background: #4CAF50; color: white; padding: 4px 8px; border-radius: 4px;")
        else:
            self.llm_status_btn.setText("LLM desconectado")
            self.llm_status_btn.setStyleSheet(
                "background: #f44336; color: white; padding: 4px 8px; border-radius: 4px;")
        self._update_kb_status()
        self._update_stage_knowledge()

    def _update_kb_status(self):
        n = self.kb.total_chunks if self.kb else 0
        corr = len(self.llm.corrections.corrections) if self.llm and hasattr(self.llm, 'corrections') else 0
        label = f"BC: {n} fragmentos"
        if corr:
            label += f" (+{corr} correcciones)"
        self.kb_status_btn.setText(label)
        self.kb_status_btn.setStyleSheet("color: #333; padding: 4px 8px;")

    def _open_kb_browser(self):
        from ui.imports.tool_dialogs import KnowledgeBrowserDialog
        dlg = KnowledgeBrowserDialog(self, kb=self.kb, llm=self.llm)
        dlg.exec()

    def _open_data_explorer(self):
        try:
            scraper = None
            if hasattr(self, '_data_import_dialog') and self._data_import_dialog:
                scraper = getattr(self._data_import_dialog.data_import, 'scraper', None)
            dlg = DataExplorerDialog(self, kb=self.kb, llm=self.llm,
                                     scraper=scraper, settings=self.rag_settings)
            dlg.exec()
            self._update_kb_status()
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Error del Explorador de Datos",
                                 f"Error al abrir el Explorador de Datos:\n{e}\n\n{traceback.format_exc()}")
            traceback.print_exc()

    def _open_rag_settings(self):
        from ui.knowledge.settings_dialog import RAGSettingsDialog
        models = []
        if self.llm and self.llm.is_available():
            try:
                models = self.llm.list_models()
            except Exception:
                pass
        dlg = RAGSettingsDialog(self.rag_settings, models, self)
        if dlg.exec():
            self.llm.api_url = self.rag_settings.api_url
            self.llm.model = self.rag_settings.model
            self.kb.chunk_size = self.rag_settings.chunk_size
            self.kb.cache_dir = Path(self.rag_settings.forum_cache_dir)
            self.kb.cache_dir.mkdir(parents=True, exist_ok=True)
            self._update_stage_settings()
            self.statusBar().showMessage(
                f"RAG: modelo={self.rag_settings.model}, "
                f"top_k={self.rag_settings.top_k}, "
                f"temp={self.rag_settings.temperature}, "
                f"chunk={self.rag_settings.chunk_size}"
            )

    def _on_analysis_complete(self, result):
        self.statusBar().showMessage("Análisis completo")

    def _on_translate_requested(self, text: str, target_lang: str):
        self.statusBar().showMessage("Traduciendo...")

        class Worker(QObject):
            finished = Signal(str)

            def __init__(self, text, target_lang, llm):
                super().__init__()
                self.text = text
                self.target_lang = target_lang
                self.llm = llm

            def run(self):
                result = translator.translate_with_llm(self.text, self.target_lang, self.llm)
                self.finished.emit(result)

        thread = QThread(self)
        worker = Worker(text, target_lang, self.llm)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda res: self._show_translation(res, thread))
        worker.finished.connect(lambda: self.statusBar().showMessage("Traducción completa"))
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _show_translation(self, translated: str, thread: QThread):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Traducción")
        dialog.setText(translated)
        dialog.exec()
        thread.quit()
        thread.wait()

    def _import_recipe(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar Receta", "", "Formulaciones (*.yaml *.json)"
        )
        if path:
            self.cutting_stage.recipe_editor.import_recipe(path)
            self.main_tabs.setCurrentIndex(0)

    def _export_recipe(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Receta", "recipe.yaml", "Formulaciones (*.yaml)"
        )
        if path:
            self.cutting_stage.recipe_editor.export_recipe(path)

    def _show_usage_guide(self):
        guide = QMessageBox(self)
        guide.setWindowTitle("📖 Guía de Uso — Lacquer Analyzer")
        guide.setTextFormat(Qt.RichText)
        guide.setText(
            "<h2>🧪 Lacquer Analyzer — Guía de Uso</h2>"
            "<hr>"
            "<h3>🔹 Flujo de trabajo principal</h3>"
            "<p>1️⃣ <b>Formulación:</b> Crea recetas en el editor → Ejecuta análisis → Compara variantes</p>"
            "<p>2️⃣ <b>Galvánica:</b> Configura parámetros de baños de plata y níquel</p>"
            "<p>3️⃣ <b>Prensado:</b> Ajusta parámetros de prensado y lleva registro de producción</p>"
            "<p>4️⃣ <b>Control de Calidad:</b> Consulta defectos, causas y soluciones</p>"
            "<p>5️⃣ <b>Conocimiento:</b> Importa datos del foro, busca en la base de conocimiento, Q&A con LLM</p>"
            "<hr>"
            "<h3>🧪 Pestaña de Formulación</h3>"
            "<p><b>Panel izquierdo — BD de Ingredientes:</b></p>"
            "<p>• <b>BD de Ingredientes:</b> Explora, filtra y edita la base de datos completa de ingredientes. "
            "Usa el buscador para encontrar por nombre. El filtro de tipo te permite ver solo resinas, solventes, pigmentos, etc. "
            "Selecciona un ingrediente para ver sus propiedades. Botón <i>Editar</i> para modificar, <i>Añadir</i> para crear uno nuevo.</p>"
            "<p>• <b>Pigmentos y Solventes:</b> Busca pigmentos por nombre comercial, C.I. Name/Number o clase química. "
            "Selecciona un resultado para ver propiedades detalladas. Usa <i>Añadir a la receta</i> para importarlo como ingrediente.</p>"
            "<p>• <b>SpecialChem:</b> Búsqueda multi-fuente (pigmentos locales + PubChem + Wikipedia + SpecialChem). "
            "Si no hay cookies de SpecialChem, configura las cookies con el botón 🔑 para habilitar esa fuente.</p>"
            "<p><b>Panel derecho — Editor de Recetas:</b></p>"
            "<p>• <b>Componentes:</b> Selecciona ingredientes y ajústalos con concentraciones. "
            "Usa los presets como punto de partida. La tabla muestra ingrediente, tipo, concentración y concentración máxima.</p>"
            "<p>• <b>Pros/Contras & Hardware:</b> Metadatos de la receta: mejores usos, pros, contras. "
            "Usa el botón <i>Traducir</i> para traducir al idioma seleccionado.</p>"
            "<p>• <b>Análisis de Laca:</b> Configura condiciones ambientales (temperatura, humedad, espesor) "
            "y ejecuta el análisis completo. Evalúa: viscosidad y película, perfil de evaporación, "
            "riesgo de defectos (burbujas, bloom, orange peel), mojado y compatibilidad Hansen. "
            "Puntuación global 0-100. Advertencias traducibles con el botón <i>Traducir</i>.</p>"
            "<p>• <b>Comparar Recetas:</b> Selecciona dos recetas para compararlas lado a lado. "
            "Muestra diferencias en composición (componente a componente), propiedades físico-químicas, "
            "y análisis completo de ambas formulaciones simultáneamente.</p>"
            "<hr>"
            "<h3>⚡ Pestaña de Galvánica</h3>"
            "<p>• <b>Parámetros de Baño:</b> Configura temperatura, pH, densidad de corriente y tiempo "
            "para baños de plata y níquel sulfamato. Ajusta la preparación superficial.</p>"
            "<p>• <b>Compatibilidad:</b> Matriz de compatibilidad de solventes y guías de prevención de defectos.</p>"
            "<p>• <b>P&R:</b> Consulta la base de conocimiento sobre procesos galvánicos.</p>"
            "<hr>"
            "<h3>🔄 Pestaña de Prensado</h3>"
            "<p>• Configura temperatura, presión, tiempos de prensado y enfriamiento.</p>"
            "<p>• Especificaciones del disco: tamaño, grosor, peso, vida del estampador.</p>"
            "<p>• Registro de producción: guarda un historial de cada prensada con sus parámetros.</p>"
            "<p>• Referencias de defectos de prensado con causas y soluciones.</p>"
            "<hr>"
            "<h3>🔍 Pestaña de Control de Calidad</h3>"
            "<p>• Navega defectos por etapa del proceso.</p>"
            "<p>• Cada defecto muestra severidad (🟢🟡🔴), síntomas, causas, soluciones y referencias del foro.</p>"
            "<p>• P&R con LLM sobre la base de conocimiento de defectos.</p>"
            "<hr>"
            "<h3>🧠 Pestaña de Conocimiento</h3>"
            "<p>• <b>Importación:</b> Importa datos del foro Lathe Trolls, Markdown, PDFs, libros escaneados, patentes. "
            "Usa el <i>Importador Completo</i> para acceso a todas las fuentes.</p>"
            "<p>• <b>P&R:</b> Haz preguntas sobre cualquier tema de lacas. El LLM responde usando la base de conocimiento.</p>"
            "<p>• <b>Navegador BC:</b> Busca y explora entradas de la base de conocimiento.</p>"
            "<hr>"
            "<h3>⚙️ Consejos rápidos</h3>"
            "<p>• <b>Pasar el ratón</b> sobre cualquier elemento de la interfaz para ver un tooltip explicativo.</p>"
            "<p>• <b>Traducción:</b> Usa el selector de idioma (🇪🇸/🇬🇧) en la barra de herramientas. "
            "Los botones <i>Traducir</i> en análisis y metadatos traducen contenido específico.</p>"
            "<p>• <b>Presets:</b> Usa recetas predefinidas como punto de partida. Guarda tus propias recetas como presets personalizados.</p>"
            "<p>• <b>LLM:</b> Verifica la conexión con LM Studio usando el botón <i>LLM</i> en la barra. "
            "Configura la URL y el modelo en <i>Configuración RAG</i>.</p>"
            "<p>• <b>Atajos:</b> Archivo → Importar/Exportar receta para compartir formulaciones.</p>"
        )
        guide.setStandardButtons(QMessageBox.Ok)
        guide.exec()

    def _show_about(self):
        QMessageBox.about(
            self, "Acerca de",
            "Analizador Químico de Laca v0.3\n"
            "Áreas de trabajo:\n"
            "🧪 Formulación → ⚡ Galvánica → 🔄 Prensado → 🔍 Control de Calidad\n"
            "🧠 Base de Conocimiento RAG integrada\n"
            "Análisis de formulación: química de NC, sistemas de solventes, pigmentos"
        )

    def closeEvent(self, event):
        self.rag_settings.save()
        if self.kb and not self.kb._loading and (self.kb._built or self.kb.entries):
            self.kb.save()
        for tab_name in ("cutting_stage", "galvanics_tab", "pressing_tab", "qc_stage", "knowledge_hub"):
            w = getattr(self, tab_name, None)
            if w and hasattr(w, 'abort_llm'):
                w.abort_llm()
        if self._data_import_dialog:
            self._data_import_dialog.cleanup()
        super().closeEvent(event)
