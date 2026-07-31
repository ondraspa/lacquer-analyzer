"""Dialog for tweaking RAG pipeline settings (model, temperature, etc.).
All settings are saved to config/rag_settings.json so no config files
need to be hand-edited.
"""

from typing import List, Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QSpinBox, QDoubleSpinBox, QPushButton,
    QComboBox, QTextEdit, QGroupBox, QCheckBox, QFormLayout,
    QListWidget, QListWidgetItem, QTabWidget, QWidget,
    QMessageBox,
)
from PySide6.QtCore import Qt

from core.translations import T

from src.rag_config import RAGSettings, Agent


class RAGSettingsDialog(QDialog):
    """Edit RAG pipeline settings: model, temperature, context limits, etc."""

    def __init__(self, settings: RAGSettings, available_models: List[str] = None,
                 parent=None):
        super().__init__(parent)
        self.settings = settings
        self._available_models = available_models or []
        self.setWindowTitle(T("Configuración del Pipeline RAG"))
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # ── Tab 1: Base Settings ──
        base_tab = QWidget()
        base_layout = QVBoxLayout(base_tab)

        # ── LLM Connection ──
        conn_group = QGroupBox(T("Conexión LLM"))
        conn_form = QFormLayout(conn_group)

        self.api_url_input = QLineEdit()
        self.api_url_input.setPlaceholderText(T("http://localhost:1234/v1"))
        self.api_url_input.setToolTip("URL del servidor LLM (ej: http://localhost:1234 para LM Studio)")
        conn_form.addRow(T("URL de API:"), self.api_url_input)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setInsertPolicy(QComboBox.NoInsert)
        if self._available_models:
            self.model_combo.addItems(self._available_models)
        self.model_combo.setPlaceholderText(T("p.ej. google/gemma-4-26b-a4b-qat"))
        self.model_combo.setToolTip("Modelo LLM a usar para generación. Los modelos disponibles se cargan desde el servidor")
        conn_form.addRow(T("Modelo:"), self.model_combo)

        refresh_btn = QPushButton(T("Actualizar Modelos"))
        refresh_btn.clicked.connect(self._refresh_models)
        refresh_btn.setToolTip("Actualiza la lista de modelos disponibles desde el servidor")
        conn_form.addRow("", refresh_btn)
        base_layout.addWidget(conn_group)

        # ── Generation Parameters ──
        gen_group = QGroupBox(T("Generación"))
        gen_form = QFormLayout(gen_group)

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(64, 4096)
        self.max_tokens_spin.setSingleStep(64)
        self.max_tokens_spin.setToolTip("Número máximo de tokens en la respuesta del LLM")
        gen_form.addRow(T("Máx. tokens:"), self.max_tokens_spin)

        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.05)
        self.temperature_spin.setDecimals(2)
        self.temperature_spin.setToolTip("Temperatura de generación (0.0=determinista, 1.0=creativo)")
        gen_form.addRow(T("Temperatura:"), self.temperature_spin)
        base_layout.addWidget(gen_group)

        # ── Retrieval ──
        ret_group = QGroupBox(T("Recuperación de Conocimiento"))
        ret_form = QFormLayout(ret_group)

        self.top_k_spin = QSpinBox()
        self.top_k_spin.setRange(1, 20)
        self.top_k_spin.setToolTip("Número de fragmentos de conocimiento más relevantes a recuperar")
        ret_form.addRow(T("Fragmentos Top-K:"), self.top_k_spin)

        self.context_chars_spin = QSpinBox()
        self.context_chars_spin.setRange(1000, 100000)
        self.context_chars_spin.setSingleStep(1000)
        self.context_chars_spin.setSuffix(" caracteres")
        self.context_chars_spin.setToolTip("Máximo de caracteres de contexto a enviar al LLM")
        ret_form.addRow(T("Límite de contexto:"), self.context_chars_spin)

        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(200, 10000)
        self.chunk_size_spin.setSingleStep(100)
        self.chunk_size_spin.setSuffix(" caracteres")
        self.chunk_size_spin.setToolTip("Tamaño de los fragmentos en que se divide el conocimiento")
        ret_form.addRow(T("Tamaño de fragmento:"), self.chunk_size_spin)

        self.show_details_check = QCheckBox(T("Mostrar detalles del pipeline RAG en el panel de P&R"))
        self.show_details_check.setToolTip("Muestra detalles del pipeline RAG en la interfaz (fragmentos, prompt, contexto)")
        ret_form.addRow("", self.show_details_check)
        base_layout.addWidget(ret_group)

        # ── Scraper ──
        scrape_group = QGroupBox(T("Raspador del Foro"))
        scrape_form = QFormLayout(scrape_group)

        self.search_max_pages_spin = QSpinBox()
        self.search_max_pages_spin.setRange(1, 20)
        self.search_max_pages_spin.setToolTip("Máximo de páginas a raspar en búsquedas del foro")
        scrape_form.addRow(T("Máx. páginas de búsqueda:"), self.search_max_pages_spin)

        self.forum_max_pages_spin = QSpinBox()
        self.forum_max_pages_spin.setRange(1, 50)
        self.forum_max_pages_spin.setToolTip("Máximo de páginas por hilo al raspar el foro")
        scrape_form.addRow(T("Páginas de listado del foro:"), self.forum_max_pages_spin)

        self.mirror_max_pages_spin = QSpinBox()
        self.mirror_max_pages_spin.setRange(1, 20)
        self.mirror_max_pages_spin.setToolTip("Máximo de páginas al duplicar el foro completo")
        scrape_form.addRow(T("Páginas de listado de duplicado:"), self.mirror_max_pages_spin)

        self.cache_dir_input = QLineEdit()
        self.cache_dir_input.setPlaceholderText(T("data/forum_cache"))
        self.cache_dir_input.setToolTip("Directorio donde se almacena la caché del rastreador del foro")
        scrape_form.addRow(T("Directorio de caché del foro:"), self.cache_dir_input)

        base_layout.addWidget(scrape_group)

        # ── System Prompt ──
        prompt_group = QGroupBox(T("Prompt del Sistema"))
        prompt_layout = QVBoxLayout(prompt_group)
        prompt_help = QLabel(
            "Usa <code>{context}</code> como marcador de posición para el conocimiento recuperado. "
            "El modelo verá esto antes de tu pregunta."
        )
        prompt_help.setWordWrap(True)
        prompt_help.setStyleSheet("color: #aaa; font-size: 11px;")
        prompt_layout.addWidget(prompt_help)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText(T("Prompt del sistema con marcador {context}..."))
        self.prompt_edit.setMinimumHeight(100)
        self.prompt_edit.setToolTip("Prompt del sistema que define el comportamiento base del LLM")
        prompt_layout.addWidget(self.prompt_edit)
        base_layout.addWidget(prompt_group)
        base_layout.addStretch()
        tabs.addTab(base_tab, T("Configuración Base"))

        # ── Tab 2: Agents ──
        agents_tab = QWidget()
        agents_layout = QHBoxLayout(agents_tab)

        # Agent list on the left
        agent_list_col = QVBoxLayout()
        agent_list_col.addWidget(QLabel(T("<b>Agentes</b>")))
        self.agent_list = QListWidget()
        self.agent_list.currentItemChanged.connect(self._on_agent_select)
        self.agent_list.setToolTip("Lista de agentes LLM especializados por dominio")
        agent_list_col.addWidget(self.agent_list, 1)
        agent_btn_row = QHBoxLayout()
        add_agent_btn = QPushButton(T("➕ Añadir"))
        add_agent_btn.clicked.connect(self._add_agent)
        add_agent_btn.setToolTip("Añade un nuevo agente especializado")
        agent_btn_row.addWidget(add_agent_btn)
        del_agent_btn = QPushButton(T("✕ Eliminar"))
        del_agent_btn.clicked.connect(self._delete_agent)
        del_agent_btn.setToolTip("Elimina el agente seleccionado")
        agent_btn_row.addWidget(del_agent_btn)
        agent_list_col.addLayout(agent_btn_row)
        agents_layout.addLayout(agent_list_col, 1)

        # Agent detail editor on the right
        agent_detail_col = QVBoxLayout()
        agent_detail_col.addWidget(QLabel(T("<b>Detalles del Agente</b>")))
        det_form = QFormLayout()
        self.agent_name_input = QLineEdit()
        self.agent_name_input.setPlaceholderText(T("p.ej. Experto en Química"))
        self.agent_name_input.setToolTip("Nombre del agente")
        det_form.addRow(T("Nombre:"), self.agent_name_input)
        self.agent_domain_input = QLineEdit()
        self.agent_domain_input.setPlaceholderText(T("p.ej. fórmulas químicas, reacciones"))
        self.agent_domain_input.setToolTip("Dominio de especialización del agente (ej: formulacion, galvanoplastia, prensado)")
        det_form.addRow(T("Dominio:"), self.agent_domain_input)
        self.agent_model_input = QComboBox()
        self.agent_model_input.setEditable(True)
        self.agent_model_input.setInsertPolicy(QComboBox.NoInsert)
        if self._available_models:
            self.agent_model_input.addItems(self._available_models)
        self.agent_model_input.setPlaceholderText(T("p.ej. qwen3:14b-q4_K_M"))
        self.agent_model_input.setToolTip("Modelo LLM para este agente (diferente al modelo global si se requiere)")
        det_form.addRow(T("Modelo:"), self.agent_model_input)
        self.agent_url_input = QLineEdit()
        self.agent_url_input.setPlaceholderText(T("http://localhost:1234/v1"))
        self.agent_url_input.setToolTip("URL del servidor LLM para este agente")
        det_form.addRow(T("URL de API:"), self.agent_url_input)

        agent_detail_col.addLayout(det_form)
        agent_detail_col.addWidget(QLabel(T("Prompt del Sistema (usa el marcador {context}):")))
        self.agent_prompt_edit = QTextEdit()
        self.agent_prompt_edit.setPlaceholderText(T("Prompt del sistema específico del dominio..."))
        self.agent_prompt_edit.setMinimumHeight(120)
        self.agent_prompt_edit.setToolTip("Prompt del sistema específico para este agente")
        agent_detail_col.addWidget(self.agent_prompt_edit, 1)
        agents_layout.addLayout(agent_detail_col, 2)

        tabs.addTab(agents_tab, T("Agentes"))
        layout.addWidget(tabs, 1)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton(T("Guardar"))
        save_btn.clicked.connect(self._save)
        save_btn.setMinimumWidth(100)
        save_btn.setStyleSheet("background: #4CAF50; color: white; font-weight: bold;")
        cancel_btn = QPushButton(T("Cancelar"))
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumWidth(100)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _load_settings(self):
        self.api_url_input.setText(self.settings.api_url)
        idx = self.model_combo.findText(self.settings.model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        else:
            self.model_combo.setCurrentText(self.settings.model)
        self.max_tokens_spin.setValue(self.settings.max_tokens)
        self.temperature_spin.setValue(self.settings.temperature)
        self.top_k_spin.setValue(self.settings.top_k)
        self.context_chars_spin.setValue(self.settings.context_chars)
        self.chunk_size_spin.setValue(self.settings.chunk_size)
        self.show_details_check.setChecked(self.settings.show_rag_details)
        self.search_max_pages_spin.setValue(self.settings.scrape_search_max_pages)
        self.forum_max_pages_spin.setValue(self.settings.scrape_forum_max_pages)
        self.mirror_max_pages_spin.setValue(self.settings.scrape_mirror_max_pages)
        self.cache_dir_input.setText(self.settings.forum_cache_dir)
        self.prompt_edit.setPlainText(self.settings.system_prompt)
        self._populate_agents()

    def _populate_agents(self):
        self.agent_list.clear()
        for a in self.settings.agents:
            item = QListWidgetItem(f"  {a.name}")
            item.setData(Qt.UserRole, a)
            self.agent_list.addItem(item)

    def _on_agent_select(self, curr, prev):
        if not curr:
            self._clear_agent_form()
            return
        a = curr.data(Qt.UserRole)
        if a:
            self.agent_name_input.setText(a.name)
            self.agent_domain_input.setText(a.domain)
            idx = self.agent_model_input.findText(a.model)
            if idx >= 0:
                self.agent_model_input.setCurrentIndex(idx)
            else:
                self.agent_model_input.setCurrentText(a.model)
            self.agent_url_input.setText(a.api_url)
            self.agent_prompt_edit.setPlainText(a.system_prompt)

    def _clear_agent_form(self):
        self.agent_name_input.clear()
        self.agent_domain_input.clear()
        self.agent_model_input.setCurrentText("")
        self.agent_url_input.clear()
        self.agent_prompt_edit.clear()

    def _add_agent(self):
        name = self.agent_name_input.text().strip()
        if not name:
            QMessageBox.information(self, T("Añadir Agente"), T("Introduce un nombre primero."))
            return
        a = Agent(
            name=name,
            domain=self.agent_domain_input.text().strip(),
            model=self.agent_model_input.currentText().strip(),
            api_url=self.agent_url_input.text().strip() or "http://localhost:1234/v1",
            system_prompt=self.agent_prompt_edit.toPlainText(),
        )
        self.settings.agents.append(a)
        self._populate_agents()
        # Select the new agent
        for i in range(self.agent_list.count()):
            if self.agent_list.item(i).data(Qt.UserRole) is a:
                self.agent_list.setCurrentRow(i)
                break

    def _delete_agent(self):
        curr = self.agent_list.currentItem()
        if not curr:
            return
        a = curr.data(Qt.UserRole)
        if a and a in self.settings.agents:
            self.settings.agents.remove(a)
            self._populate_agents()
            self._clear_agent_form()

    def _save(self):
        # Save current agent form if editing
        curr = self.agent_list.currentItem()
        if curr:
            a = curr.data(Qt.UserRole)
            if a:
                a.name = self.agent_name_input.text().strip()
                a.domain = self.agent_domain_input.text().strip()
                a.model = self.agent_model_input.currentText().strip()
                a.api_url = self.agent_url_input.text().strip()
                a.system_prompt = self.agent_prompt_edit.toPlainText()
        self.settings.api_url = self.api_url_input.text().strip()
        self.settings.model = self.model_combo.currentText().strip()
        self.settings.max_tokens = self.max_tokens_spin.value()
        self.settings.temperature = self.temperature_spin.value()
        self.settings.top_k = self.top_k_spin.value()
        self.settings.context_chars = self.context_chars_spin.value()
        self.settings.chunk_size = self.chunk_size_spin.value()
        self.settings.show_rag_details = self.show_details_check.isChecked()
        self.settings.scrape_search_max_pages = self.search_max_pages_spin.value()
        self.settings.scrape_forum_max_pages = self.forum_max_pages_spin.value()
        self.settings.scrape_mirror_max_pages = self.mirror_max_pages_spin.value()
        self.settings.forum_cache_dir = self.cache_dir_input.text().strip()
        self.settings.system_prompt = self.prompt_edit.toPlainText()
        self.settings.save()
        self.accept()

    def _refresh_models(self):
        try:
            import requests
            url = self.api_url_input.text().strip() or self.settings.api_url
            resp = requests.get(f"{url}/models", timeout=5)
            if resp.status_code == 200:
                models = [m["id"] for m in resp.json().get("data", [])]
                self.model_combo.clear()
                self.model_combo.addItems(models)
                self.model_combo.setCurrentText(self.settings.model)
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, T("Actualizar Modelos"), f"{T('No se pudo conectar con la API:')}\n{e}")
