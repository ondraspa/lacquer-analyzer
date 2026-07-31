"""Widget de etapa de pipeline reutilizable para el flujo de trabajo de fabricación de vinilo.

Cada etapa muestra: información de la etapa, conocimiento del foro, solución de problemas y P&R.
La etapa de Corte extiende esto con edición de recetas + navegador de ingredientes.
"""

import json
from pathlib import Path
from typing import Optional, List, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QTextEdit, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QGroupBox,
    QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QTreeWidget, QTreeWidgetItem, QMessageBox, QComboBox,
    QDialog, QDialogButtonBox, QSpinBox, QDoubleSpinBox, QCheckBox,
)
from PySide6.QtCore import Qt, QSize, Signal, QThread
from PySide6.QtGui import QFont, QColor, QBrush

from src.troubleshooting import (
    STAGE_INFO, DEFECT_DATABASE, Defect, get_defects_by_stage, search_defects
)
from src.llm_integration import LocalLLM, ForumKnowledgeBase
from src.rag_config import RAGSettings
from ui.knowledge.settings_dialog import RAGSettingsDialog
from core.translations import T


class TroubleshootingPanel(QWidget):
    """Navegador de base de datos de defectos para una etapa de pipeline específica."""

    defect_selected = Signal(str)

    def __init__(self, stage: str, parent=None):
        super().__init__(parent)
        self.stage = stage
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel(T("Guía de Solución de Problemas"))
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(T("Buscar síntomas, causas, defectos..."))
        self.search_input.setToolTip(T("Busca defectos por nombre o síntoma. Filtra la lista en tiempo real"))
        self.search_input.textChanged.connect(self._filter_defects)
        search_row.addWidget(self.search_input)

        self.all_stage_btn = QPushButton(T("Todas las Etapas"))
        self.all_stage_btn.setCheckable(True)
        self.all_stage_btn.setToolTip(T("Alterna entre ver defectos de todas las etapas o solo de la etapa actual"))
        self.all_stage_btn.toggled.connect(self._filter_defects)
        search_row.addWidget(self.all_stage_btn)
        layout.addLayout(search_row)

        self.defect_tree = QTreeWidget()
        self.defect_tree.setHeaderLabels([T("Defecto"), T("Severidad")])
        self.defect_tree.setToolTip(T("Árbol de defectos con severidad (🟢 baja, 🟡 media, 🔴 alta). Haz clic para ver detalles"))
        self.defect_tree.setAlternatingRowColors(True)
        self.defect_tree.itemClicked.connect(self._on_defect_clicked)
        layout.addWidget(self.defect_tree, 1)

        self.detail_area = QTextEdit()
        self.detail_area.setReadOnly(True)
        self.detail_area.setMaximumHeight(200)
        self.detail_area.setToolTip(T("Descripción detallada del defecto: síntomas, causas, soluciones y referencias del foro"))
        layout.addWidget(self.detail_area)

        self._populate()

    def _populate(self):
        self.defect_tree.clear()
        defects = get_defects_by_stage(self.stage)
        if self.all_stage_btn.isChecked():
            all_defects = []
            for s in ["cutting", "silvering", "plating", "pressing", "qc"]:
                all_defects.extend(get_defects_by_stage(s))
            defects = all_defects
        for d in defects:
            item = QTreeWidgetItem([d.name, d.severity.upper()])
            item.setData(0, Qt.UserRole, d.id)
            color = {"low": "green", "medium": "#cc8800",
                     "high": "#cc3300", "critical": "red"}.get(d.severity, "gray")
            item.setForeground(1, QBrush(QColor(color)))
            self.defect_tree.addTopLevelItem(item)

    def _filter_defects(self):
        query = self.search_input.text().strip()
        self.defect_tree.clear()
        if self.all_stage_btn.isChecked():
            defects = []
            for s in ["cutting", "silvering", "plating", "pressing", "qc"]:
                defects.extend(get_defects_by_stage(s))
        else:
            defects = get_defects_by_stage(self.stage)
        if query:
            defects = search_defects(query, stage=None if self.all_stage_btn.isChecked() else self.stage)
        for d in defects:
            item = QTreeWidgetItem([d.name, d.severity.upper()])
            item.setData(0, Qt.UserRole, d.id)
            color = {"low": "green", "medium": "#cc8800",
                     "high": "#cc3300", "critical": "red"}.get(d.severity, "gray")
            item.setForeground(1, QBrush(QColor(color)))
            self.defect_tree.addTopLevelItem(item)

    def _on_defect_clicked(self, item, col):
        defect_id = item.data(0, Qt.UserRole)
        if not defect_id:
            return
        from src.troubleshooting import get_defect_by_id
        d = get_defect_by_id(defect_id)
        if not d:
            return
        self.defect_selected.emit(defect_id)
        html = f"<h3>{d.name}</h3>"
        html += f"<p><b>Etapa:</b> {d.stage} | <b>Severidad:</b> {d.severity}</p>"
        html += f"<p>{d.description}</p>"
        if d.symptoms:
            html += "<h4>Síntomas</h4><ul>"
            for s in d.symptoms:
                html += f"<li>{s}</li>"
            html += "</ul>"
        if d.causes:
            html += "<h4>Causas</h4><ul>"
            for c in d.causes:
                html += f"<li>{c}</li>"
            html += "</ul>"
        if d.solutions:
            html += "<h4>Soluciones</h4><ul>"
            for s in d.solutions:
                html += f"<li>{s}</li>"
            html += "</ul>"
        if d.forum_refs:
            html += "<h4>Referencias del Foro</h4><ul>"
            for r in d.forum_refs:
                html += f"<li>{r}</li>"
            html += "</ul>"
        self.detail_area.setHtml(html)


class KnowledgeQAPanel(QWidget):
    """Navegador de conocimiento del foro y P&R del LLM para una etapa de pipeline.

    Muestra el pipeline RAG completo: fragmentos recuperados → inyección de contexto → respuesta.
    El botón de Configuración abre RAGSettingsDialog para ajustar modelo, temperatura, etc.
    """

    def __init__(self, stage: str, parent=None):
        super().__init__(parent)
        self.stage = stage
        self.llm: Optional[LocalLLM] = None
        self.kb: Optional[ForumKnowledgeBase] = None
        self.settings = RAGSettings()
        self._last_question = ""
        self._last_answer = ""
        self._last_context = ""
        self._last_matches = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel(T("Conocimiento y P&R"))
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        self.kb_status = QLabel(T("Base de conocimiento: no cargada"))
        self.kb_status.setToolTip(T("Estado de la base de conocimiento: número de entradas cargadas"))
        self.kb_status.setStyleSheet("color: #aaa; font-style: italic;")
        layout.addWidget(self.kb_status)

        self.knowledge_list = QListWidget()
        self.knowledge_list.setAlternatingRowColors(True)
        self.knowledge_list.setToolTip(T("Entradas de conocimiento relevantes para la consulta actual"))
        layout.addWidget(self.knowledge_list, 1)

        # ── RAG Details (collapsible) ──
        self.rag_details_btn = QPushButton(T("▶ Mostrar detalles del pipeline RAG"))
        self.rag_details_btn.setToolTip(T("Muestra/oculta los detalles del pipeline RAG (fragmentos, prompt, contexto)"))
        self.rag_details_btn.setStyleSheet("text-align: left; border: none; color: #999;")
        self.rag_details_btn.setCheckable(True)
        self.rag_details_btn.toggled.connect(self._toggle_rag_details)
        layout.addWidget(self.rag_details_btn)

        self.rag_details_area = QWidget()
        rag_details_layout = QVBoxLayout(self.rag_details_area)
        rag_details_layout.setContentsMargins(8, 0, 0, 0)

        self.rag_chunks_label = QLabel(T("Fragmentos recuperados: ninguno"))
        self.rag_chunks_label.setStyleSheet("font-size: 11px; color: #aaa;")
        rag_details_layout.addWidget(self.rag_chunks_label)

        self.rag_chunks_area = QTextEdit()
        self.rag_chunks_area.setReadOnly(True)
        self.rag_chunks_area.setMaximumHeight(100)
        self.rag_chunks_area.setToolTip(T("Fragmentos de conocimiento recuperados por el pipeline RAG para la consulta"))
        self.rag_chunks_area.setPlaceholderText(T("Fragmentos de conocimiento recuperados para la última pregunta..."))
        self.rag_chunks_area.setStyleSheet("font-size: 10px; color: #999;")
        rag_details_layout.addWidget(self.rag_chunks_area)

        self.rag_prompt_label = QLabel(T("Prompt enviado al modelo:"))
        self.rag_prompt_label.setStyleSheet("font-size: 11px; color: #aaa;")
        rag_details_layout.addWidget(self.rag_prompt_label)

        self.rag_prompt_area = QTextEdit()
        self.rag_prompt_area.setReadOnly(True)
        self.rag_prompt_area.setMaximumHeight(120)
        self.rag_prompt_area.setToolTip(T("Prompt completo enviado al LLM, incluyendo el contexto recuperado"))
        self.rag_prompt_area.setPlaceholderText(T("El array completo de mensajes enviado a /v1/chat/completions..."))
        self.rag_prompt_area.setStyleSheet("font-size: 10px; color: #999;")
        rag_details_layout.addWidget(self.rag_prompt_area)

        self.rag_details_area.setVisible(False)
        layout.addWidget(self.rag_details_area)

        # ── Q&A ──
        qa_group = QGroupBox(T("Haz una pregunta sobre esta etapa"))
        qa_layout = QVBoxLayout(qa_group)
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText(T("Ej: ¿Qué grado de NC es mejor para 30% de sólidos?"))
        self.question_input.setToolTip(T("Escribe tu pregunta sobre el proceso o los defectos. El LLM responderá usando la base de conocimiento"))
        self.question_input.returnPressed.connect(self._ask_question)
        qa_layout.addWidget(self.question_input)

        btn_row = QHBoxLayout()
        self.ask_btn = QPushButton(T("Preguntar al LLM"))
        self.ask_btn.setToolTip(T("Envía la pregunta al LLM usando el contexto RAG de la base de conocimiento"))
        self.ask_btn.clicked.connect(self._ask_question)
        btn_row.addWidget(self.ask_btn)

        self.settings_btn = QPushButton(T("⚙ Configuración"))
        self.settings_btn.setToolTip(T("Abre la configuración del RAG: API URL, modelo, parámetros de generación y recuperación"))
        self.settings_btn.clicked.connect(self._open_settings)
        btn_row.addWidget(self.settings_btn)

        self.agent_combo = QComboBox()
        self.agent_combo.setToolTip(T("Selecciona el agente LLM especializado para el dominio (formulación, galvanoplastia, prensado, etc.)"))
        self.agent_combo.currentIndexChanged.connect(self._on_agent_changed)
        btn_row.addWidget(self.agent_combo)

        self.kb_refresh_btn = QPushButton(T("Actualizar BC"))
        self.kb_refresh_btn.setToolTip(T("Recarga la base de conocimiento desde el disco"))
        self.kb_refresh_btn.clicked.connect(self._refresh_kb)
        btn_row.addWidget(self.kb_refresh_btn)

        self.llm_status = QLabel("")
        self.llm_status.setToolTip(T("Estado de conexión con el LLM (conectado/desconectado)"))
        self.llm_status.setStyleSheet("color: #aaa;")
        btn_row.addWidget(self.llm_status, 1)
        qa_layout.addLayout(btn_row)

        self.answer_area = QTextEdit()
        self.answer_area.setReadOnly(True)
        self.answer_area.setPlaceholderText(T("La respuesta aparecerá aquí..."))
        self.answer_area.setMaximumHeight(160)
        self.answer_area.setToolTip(T("Respuesta del LLM basada en el contexto recuperado de la base de conocimiento"))
        qa_layout.addWidget(self.answer_area)

        inspect_row = QHBoxLayout()
        self.inspect_btn = QPushButton(T("🔍 Inspeccionar contexto RAG"))
        self.inspect_btn.setToolTip(T("Abre el inspector RAG para ver en detalle los fragmentos recuperados y el contexto enviado al LLM"))
        self.inspect_btn.clicked.connect(self._open_rag_inspector)
        self.inspect_btn.setVisible(False)
        inspect_row.addWidget(self.inspect_btn)
        inspect_row.addStretch()
        qa_layout.addLayout(inspect_row)

        layout.addWidget(qa_group)

    def _toggle_rag_details(self, visible: bool):
        self.rag_details_area.setVisible(visible)
        self.rag_details_btn.setText(
            T("▼ Ocultar detalles del pipeline RAG") if visible
            else T("▶ Mostrar detalles del pipeline RAG")
        )

    def set_llm(self, llm: LocalLLM):
        self.llm = llm
        # Update LLM's API URL and model from our settings
        if llm:
            llm.api_url = self.settings.api_url
            llm.model = self.settings.model
        self.llm_status.setText(T("LLM conectado"))
        self._populate_agents()

    def set_knowledge_base(self, kb: ForumKnowledgeBase):
        self.kb = kb
        self.kb_status.setText(T("Base de conocimiento: {count} entradas").format(count=len(kb.entries)))
        self._populate_knowledge()

    def set_settings(self, settings: RAGSettings):
        """Receive a shared RAGSettings object (from MainWindow)."""
        self.settings = settings
        if self.llm:
            self.llm.api_url = settings.api_url
            self.llm.model = settings.model
        self._populate_agents()

    def _open_settings(self):
        models = []
        if self.llm and self.llm.is_available():
            try:
                models = self.llm.list_models()
            except Exception:
                pass
        dlg = RAGSettingsDialog(self.settings, models, self)
        if dlg.exec():
            # Apply changes to LLM
            if self.llm:
                self.llm.api_url = self.settings.api_url
                self.llm.model = self.settings.model

    def _populate_agents(self):
        """Fill the agent combo from settings.agents."""
        current = self.agent_combo.currentText()
        self.agent_combo.blockSignals(True)
        self.agent_combo.clear()
        for a in self.settings.agents:
            self.agent_combo.addItem(f"{a.name} ({a.domain})", a)
        # Restore selection
        idx = self.agent_combo.findText(current)
        if idx >= 0:
            self.agent_combo.setCurrentIndex(idx)
        self.agent_combo.blockSignals(False)
        self._on_agent_changed()

    def _on_agent_changed(self):
        """Apply the selected agent's model/api_url/system_prompt to the LLM."""
        a = self.agent_combo.currentData()
        if a and self.llm:
            self.llm.api_url = a.api_url.rstrip("/")
            self.llm.model = a.model

    def _get_active_system_prompt(self) -> str:
        """Return the selected agent's system prompt, falling back to the default."""
        a = self.agent_combo.currentData()
        if a and a.system_prompt:
            return a.system_prompt
        return self.settings.system_prompt

    def _populate_knowledge(self):
        self.knowledge_list.clear()
        if not self.kb:
            return
        stage_keywords = {
            "substrate": ["aluminum", "aluminium", "substrate", "cleaning", "degrease", "adhesion", "core"],
            "formulation": ["nitrocellulose", "nc", "solvent", "ester", "ketone", "alcohol", "plasticizer", "viscosity", "lacquer", "formulation", "resin"],
            "coating": ["burkle", "curtain", "coating", "spin", "flow", "layer", "thickness", "application"],
            "curing": ["cure", "drying", "solvent", "evaporation", "hardness", "blush", "haze", "crosslink"],
            "qc": ["defect", "inspection", "pinhole", "adhesion", "roughness", "quality", "test"],
            "galvanics": ["silver", "nickel", "sulfamate", "electroform", "bath", "plating", "current", "galvanic", "anode", "cathode"],
            "pressing": ["press", "mold", "stamper", "stamp", "temperature", "pressure", "cooling"],
        }
        keywords = stage_keywords.get(self.stage, [self.stage])
        found = set()
        for entry in self.kb.entries:
            is_general = entry.category == "general"
            is_this_stage = entry.category == self.stage
            matches_keyword = any(kw.lower() in entry.content.lower() for kw in keywords)
            if is_general or is_this_stage or matches_keyword:
                if entry.title not in found:
                    found.add(entry.title)
                    item = QListWidgetItem(f"{entry.title}")
                    item.setToolTip(entry.content[:200])
                    self.knowledge_list.addItem(item)
        if self.knowledge_list.count() == 0:
                    self.knowledge_list.addItem(T("No se encontró conocimiento relevante para esta etapa. Prueba a duplicar el foro primero."))

    def _refresh_kb(self):
        self._populate_knowledge()
        self.kb_status.setText(T("Base de conocimiento actualizada ({count} entradas)").format(count=len(self.knowledge_list)))

    def _ask_question(self):
        q = self.question_input.text().strip()
        if not q:
            return
        self.answer_area.setHtml("<i>Pensando...</i>")
        self.ask_btn.setEnabled(False)
        self.inspect_btn.setVisible(False)

        # 1. Retrieve
        top_k = self.settings.top_k
        matches = self.kb.search(q, max_results=top_k) if self.kb else []
        self.rag_chunks_label.setText(
            T("Fragmentos recuperados: {count} (top-{top_k})").format(count=len(matches), top_k=top_k)
        )

        # Store RAG context for the inspector
        self._last_question = q
        self._last_matches = matches

        # 2. Build context
        context_str = ""
        if matches:
            context_parts = []
            for m in matches:
                context_parts.append(f"[{m.category}] {m.title}\n{m.content[:800]}")
            context_str = "\n\n---\n\n".join(context_parts)
            self.rag_chunks_area.setPlainText(
                "\n\n".join(
                    f"[{m.category}] {m.title} ({len(m.content)} caracteres)\n"
                    f"  {m.content[:200]}..."
                    for m in matches
                )
            )
        else:
            self.rag_chunks_area.setPlainText(T("(no se encontró conocimiento coincidente)"))

        self._last_context = context_str

        # 3. Build and show messages
        system_prompt = self._get_active_system_prompt()
        system_content = system_prompt.replace(
            "{context}", context_str[:self.settings.context_chars]
        )
        messages = []
        if context_str:
            messages.append({"role": "system", "content": system_content})
        user_question = (
            f"Pregunta sobre {self.stage}: {q}" if context_str else q
        )
        messages.append({"role": "user", "content": user_question})
        self.rag_prompt_area.setPlainText(
            json.dumps(messages, indent=2, ensure_ascii=False)
        )
        if self.settings.show_rag_details:
            self.rag_details_area.setVisible(True)
            self.rag_details_btn.setText(T("▼ Ocultar detalles del pipeline RAG"))

        # 4. Check LLM
        if not self.llm or not self.llm.is_available():
            self.answer_area.setHtml(
                "<b>LLM no disponible.</b> Asegúrate de que LM Studio esté ejecutándose<br>"
                "<i>Los detalles del pipeline RAG arriba muestran lo que se enviaría.</i>"
            )
            self.ask_btn.setEnabled(True)
            return

        # 5. Ask via background thread (prevents UI freeze + SIGSEGV)
        from gui.data_import import LLMAskJob
        self._llm_thread = QThread(self)
        self._llm_job = LLMAskJob(
            self.llm, user_question, context_str,
            max_tokens=self.settings.max_tokens,
            temperature=self.settings.temperature,
            context_chars=self.settings.context_chars,
            system_prompt=system_prompt,
        )
        self._llm_job.moveToThread(self._llm_thread)
        self._llm_thread.started.connect(self._llm_job.run)
        self._llm_job.finished.connect(self._on_llm_answer, Qt.QueuedConnection)
        self._llm_job.error.connect(self._on_llm_error, Qt.QueuedConnection)
        self._llm_thread.finished.connect(self._llm_job.deleteLater)
        self._llm_thread.finished.connect(self._llm_thread.deleteLater)
        self._llm_thread.finished.connect(self._cleanup_llm_thread)
        self._llm_thread.start()

    def _open_rag_inspector(self):
        from ui.knowledge.rag_inspector import RagInspectorDialog
        chunks = []
        for m in getattr(self, '_last_matches', []):
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
            question=getattr(self, '_last_question', ''),
            answer=getattr(self, '_last_answer', ''),
            retrieved_chunks=chunks,
            context=getattr(self, '_last_context', ''),
            stage=self.stage,
        )
        dlg.exec()

    def _on_llm_answer(self, answer: str):
        self.answer_area.setHtml(answer.replace("\n", "<br>"))
        self.ask_btn.setEnabled(True)
        self._last_answer = answer
        self.inspect_btn.setVisible(True)

    def _on_llm_error(self, err: str):
        self.answer_area.setHtml(f"<b>Error:</b> {err}")
        self.ask_btn.setEnabled(True)
        self._last_answer = ""

    def _cleanup_llm_thread(self):
        self._llm_thread = None
        self._llm_job = None

    def abort_llm(self):
        """Cancel any running LLM request. Safe to call from closeEvent."""
        if hasattr(self, '_llm_job') and self._llm_job:
            self._llm_job._abort = True
        if hasattr(self, '_llm_thread') and self._llm_thread:
            self._llm_thread.quit()
            self._llm_thread.wait(2000)


class StageParamEditDialog(QDialog):
    """Diálogo simple para editar parámetros clave de una etapa de pipeline."""

    def __init__(self, stage: str, parent=None):
        super().__init__(parent)
        self.stage = stage
        self.setWindowTitle(T("Editar Parámetros — {stage}").format(stage=stage.title()))
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self):
        from copy import deepcopy
        layout = QVBoxLayout(self)
        self._fields = []
        info = STAGE_INFO.get(self.stage, {})
        params = deepcopy(info.get("key_parameters", []))

        form = QFormLayout()
        for name, value in params:
            inp = QLineEdit(str(value))
            form.addRow(f"{name}:", inp)
            self._fields.append((name, inp))
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton(T("Guardar"))
        save_btn.clicked.connect(self._save)
        save_btn.setStyleSheet("background: #4CAF50; color: white;")
        btn_row.addWidget(save_btn)
        cancel_btn = QPushButton(T("Cancelar"))
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _save(self):
        info = STAGE_INFO.get(self.stage, {})
        params = []
        for name, inp in self._fields:
            params.append((name, inp.text().strip()))
        info["key_parameters"] = params
        self.accept()


class PipelineStageWidget(QWidget):
    """Widget de etapa de pipeline general con solución de problemas + conocimiento + P&R."""

    def __init__(self, stage: str, parent=None):
        super().__init__(parent)
        self.stage = stage
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        info = STAGE_INFO.get(self.stage, {})
        header_row = QHBoxLayout()
        header = QLabel(T("{icon} {title}").format(icon=info.get('icon', ''), title=info.get('title', self.stage.title())))
        header.setStyleSheet("font-weight: bold; font-size: 16px; padding: 4px;")
        header.setToolTip(info.get("description", ""))
        header_row.addWidget(header)
        header_row.addStretch()
        edit_params_btn = QPushButton(T("Editar Parámetros"))
        edit_params_btn.setToolTip(T("Edita los parámetros clave de esta etapa del proceso"))
        edit_params_btn.clicked.connect(self._edit_parameters)
        edit_params_btn.setMaximumWidth(120)
        header_row.addWidget(edit_params_btn)
        layout.addLayout(header_row)

        desc = QLabel(info.get("description", ""))
        desc.setWordWrap(True)
        desc.setToolTip(info.get("description", ""))
        desc.setStyleSheet("color: #999; padding: 2px 4px 8px 4px;")
        layout.addWidget(desc)

        self._param_box = QGroupBox(T("Parámetros Clave"))
        self._param_layout = QFormLayout(self._param_box)
        layout.addWidget(self._param_box)
        self._refresh_params()

        splitter = QSplitter(Qt.Horizontal)

        self.troubleshooting = TroubleshootingPanel(self.stage)
        splitter.addWidget(self.troubleshooting)

        self.knowledge_qa = KnowledgeQAPanel(self.stage)
        splitter.addWidget(self.knowledge_qa)

        splitter.setSizes([400, 400])
        layout.addWidget(splitter, 1)

    def _refresh_params(self):
        self._param_layout.removeRow(0) if self._param_layout.rowCount() else None
        while self._param_layout.rowCount():
            self._param_layout.removeRow(0)
        info = STAGE_INFO.get(self.stage, {})
        params = info.get("key_parameters", [])
        if params:
            self._param_box.setVisible(True)
            for name, value in params:
                self._param_layout.addRow(f"{name}:", QLabel(f"<b>{value}</b>"))
        else:
            self._param_box.setVisible(False)

    def _edit_parameters(self):
        dlg = StageParamEditDialog(self.stage, self)
        if dlg.exec():
            self._refresh_params()

    def set_llm(self, llm: Optional[LocalLLM]):
        self.knowledge_qa.set_llm(llm)

    def set_knowledge_base(self, kb: Optional[ForumKnowledgeBase]):
        self.knowledge_qa.set_knowledge_base(kb)

    def set_settings(self, settings):
        self.knowledge_qa.set_settings(settings)

    def abort_llm(self):
        self.knowledge_qa.abort_llm()
