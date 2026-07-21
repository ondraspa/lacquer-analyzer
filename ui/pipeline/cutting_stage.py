"""Widget de etapa de corte — el espacio de trabajo principal de formulación.

Integra editor de recetas, navegador de ingredientes, análisis,
más conocimiento y solución de problemas específicos de la etapa.
"""

from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QSplitter, QPushButton, QMessageBox,
    QLineEdit, QListWidget, QListWidgetItem, QTextEdit,
    QDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ui.workspace.ingredient_editor import IngredientEditorDialog
from ui.workspace.recipe_editor import RecipeEditorWidget
from ui.workspace.ingredient_browser import IngredientBrowserWidget
from ui.pipeline.base_stage import PipelineStageWidget, KnowledgeQAPanel, TroubleshootingPanel
from src.ingredient_loader import IngredientLoader
from materials import PigmentDatabase
from imports.specialchem_scraper import ChemicalIngredientSearch
from imports.specialchem_scraper import COOKIE_PATH as SPECIALCHEM_COOKIE_PATH
import threading
import subprocess
import os


class PigmentSearchWidget(QWidget):
    """Pestaña de búsqueda de pigmentos y solventes por nombre comercial."""

    add_to_recipe_requested = Signal(dict)

    def __init__(self):
        super().__init__()
        self.db = PigmentDatabase()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        info = QLabel(
            "<b>Base de datos de pigmentos</b> — busca por nombre comercial, "
            "C.I. Name, C.I. Number o clase química.<br>"
            "<i>Ej: T67, PV 23, dioxazine, phthalocyanine, DPP</i>"
        )
        info.setWordWrap(True)
        info.setToolTip("Busca pigmentos en la base de datos local por nombre, C.I. o clase química")
        layout.addWidget(info)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar pigmento (nombre comercial, C.I., clase)...")
        self.search_input.setToolTip("Escribe al menos 2 caracteres para buscar pigmentos")
        self.search_input.textChanged.connect(self._search)
        search_row.addWidget(self.search_input)

        clear_btn = QPushButton("Limpiar")
        clear_btn.setToolTip("Limpia el campo de búsqueda y la lista de resultados")
        clear_btn.clicked.connect(lambda: (self.search_input.clear(), self.results_list.clear()))
        search_row.addWidget(clear_btn)
        layout.addLayout(search_row)

        self.results_list = QListWidget()
        self.results_list.setToolTip("Resultados de la búsqueda de pigmentos. Haz clic para ver detalles.")
        self.results_list.itemClicked.connect(self._show_detail)
        layout.addWidget(self.results_list)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(300)
        self.detail_text.setToolTip("Propiedades detalladas del pigmento seleccionado")
        self.detail_text.setPlaceholderText("Selecciona un pigmento para ver sus propiedades...")
        layout.addWidget(self.detail_text)

        button_row = QHBoxLayout()
        self.add_btn = QPushButton("Añadir a la receta")
        self.add_btn.setToolTip("Abre el editor de ingredientes con los datos del pigmento para añadirlo a la receta")
        self.add_btn.setEnabled(False)
        self.add_btn.clicked.connect(self._add_to_recipe)
        button_row.addStretch()
        button_row.addWidget(self.add_btn)
        layout.addLayout(button_row)

    def _search(self):
        q = self.search_input.text().strip()
        self.results_list.clear()
        self.detail_text.clear()
        self.add_btn.setEnabled(False)
        if len(q) < 2:
            return
        for p in self.db.search(q):
            name = p.get("ci_name") or p["common_names"][0]
            cls = p.get("chemical_class", "")
            item = QListWidgetItem(f"{name:35s}  [{cls}]")
            item.setData(Qt.UserRole, p)
            self.results_list.addItem(item)

    def _show_detail(self, item):
        p = item.data(Qt.UserRole)
        if not p:
            return
        self.detail_text.setHtml(
            f"<pre>{self.db.summary(p)}</pre>"
        )
        self.add_btn.setEnabled(True)

    def _add_to_recipe(self):
        item = self.results_list.currentItem()
        if not item:
            return
        p = item.data(Qt.UserRole)
        if not p:
            return
        self.add_to_recipe_requested.emit(p)


def _map_pigment_to_ingredient(p, dialog):
    """Mapea datos de un pigmento al IngredientEditorDialog."""
    name = p.get("ci_name") or p.get("common_names", ["?"])[0]
    trade = p.get("trade_names", "")
    if trade and name and trade != name:
        best_name = trade.split(",")[0].strip() or name
    else:
        best_name = name
    dialog.name_input.setText(best_name)

    # Tipo según el nombre
    ci_name = (p.get("ci_name") or "").lower()
    if "white" in ci_name:
        dialog.type_combo.setCurrentText("white_pigment")
    elif "black" in ci_name:
        dialog.type_combo.setCurrentText("black_pigment")
    else:
        dialog.type_combo.setCurrentText("color_pigment")

    density = p.get("density_gcm3")
    if density:
        try:
            dialog.density_spin.setValue(float(str(density).replace(",", ".")))
        except (ValueError, AttributeError):
            pass

    notes_parts = []
    if p.get("ci_name"):
        notes_parts.append(f"C.I. Name: {p['ci_name']}")
    if p.get("ci_number"):
        notes_parts.append(f"C.I. Number: {p['ci_number']}")
    if p.get("chemical_class"):
        notes_parts.append(f"Clase: {p['chemical_class']}")
    if p.get("cas"):
        notes_parts.append(f"CAS: {p['cas']}")
    if p.get("formula"):
        notes_parts.append(f"Fórmula: {p['formula']}")
    if p.get("mw"):
        notes_parts.append(f"MW: {p['mw']}")
    if p.get("density_gcm3"):
        notes_parts.append(f"Densidad: {p['density_gcm3']} g/cm³")
    if p.get("oil_absorption"):
        notes_parts.append(f"Absorción aceite: {p['oil_absorption']}")
    if p.get("heat_stability_c"):
        notes_parts.append(f"Estabilidad térmica: {p['heat_stability_c']}°C")
    if p.get("lightfastness"):
        notes_parts.append(f"Resistencia luz: {p['lightfastness']}")
    if p.get("trade_names"):
        notes_parts.append(f"Nombres comerciales: {p['trade_names']}")
    if p.get("common_names"):
        notes_parts.append(f"Alias: {', '.join(p['common_names'][:4])}")
    if p.get("applications"):
        apps = ", ".join(p["applications"][:4])
        notes_parts.append(f"Aplicaciones: {apps}")
    if p.get("notes"):
        notes_parts.append(f"Notas: {p['notes']}")
    dialog.notes_input.setPlainText("\n".join(notes_parts))


class SpecialChemSearchWidget(QWidget):
    """Pestaña de búsqueda multi-fuente: pigmentos, PubChem, Wikipedia, SpecialChem."""

    search_finished = Signal(list)
    add_to_recipe_requested = Signal(dict)

    def __init__(self, ingredient_loader=None):
        super().__init__()
        self.searcher = ChemicalIngredientSearch()
        self.ingredient_loader = ingredient_loader
        self.search_finished.connect(self._on_search_finished)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        info = QLabel(
            "<b>Búsqueda Multi-Fuente</b> — busca ingredientes en múltiples bases de datos.<br>"
            "Fuentes: Pigmentos locales, PubChem, Wikipedia, SpecialChem (si hay cookies).<br>"
            "<i>Ej: BYK-307, Tinuvin 400, T67, PV 23, titanium dioxide</i>"
        )
        info.setWordWrap(True)
        info.setToolTip("Busca ingredientes en 4 fuentes simultáneamente: pigmentos locales, PubChem, Wikipedia y SpecialChem")
        layout.addWidget(info)

        cookie_row = QHBoxLayout()
        self.cookie_status = QLabel("")
        self.cookie_status.setStyleSheet("font-size: 11px;")
        self.cookie_status.setToolTip("Estado de las cookies de SpecialChem. Sin cookies, los resultados de SpecialChem no están disponibles.")
        cookie_row.addWidget(self.cookie_status)
        cookie_row.addStretch()
        self.cookie_btn = QPushButton("🔑 Configurar cookies de SpecialChem")
        self.cookie_btn.setToolTip("Abre un navegador para iniciar sesión en SpecialChem y guardar las cookies. Necesario para buscar en SpecialChem.")
        self.cookie_btn.clicked.connect(self._configure_cookies)
        cookie_row.addWidget(self.cookie_btn)
        layout.addLayout(cookie_row)

        row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nombre comercial, químico o pigmento...")
        self.search_input.setToolTip("Escribe el nombre del ingrediente, químico o pigmento a buscar (mín. 2 caracteres)")
        self.search_input.returnPressed.connect(self._search)
        row.addWidget(self.search_input)

        self.search_btn = QPushButton("Buscar")
        self.search_btn.setToolTip("Inicia la búsqueda multi-fuente")
        self.search_btn.clicked.connect(self._search)
        row.addWidget(self.search_btn)
        layout.addLayout(row)

        self.source_label = QLabel("")
        self.source_label.setStyleSheet("color: #aaa; font-size: 11px;")
        self.source_label.setToolTip("Resumen de resultados por fuente (pigmentos, PubChem, Wikipedia, SpecialChem)")
        layout.addWidget(self.source_label)

        self.results_list = QListWidget()
        self.results_list.setToolTip("Resultados de la búsqueda. Cada elemento muestra la fuente y el nombre. Haz clic para ver detalles.")
        self.results_list.itemClicked.connect(self._show_detail)
        layout.addWidget(self.results_list)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setToolTip("Información detallada del resultado seleccionado (propiedades, estructura, usos)")
        self.detail_text.setPlaceholderText("Selecciona un resultado para ver detalles...")
        layout.addWidget(self.detail_text)

        self.add_btn = QPushButton("Añadir a la receta")
        self.add_btn.setToolTip("Abre el editor de ingredientes pre-cargado con los datos de este resultado para añadirlo a tu receta")
        self.add_btn.setEnabled(False)
        self.add_btn.clicked.connect(self._add_to_recipe)
        layout.addWidget(self.add_btn)

        self._update_cookie_status()

    def _update_cookie_status(self):
        if os.path.exists(SPECIALCHEM_COOKIE_PATH):
            try:
                import json
                with open(SPECIALCHEM_COOKIE_PATH) as f:
                    cookies = json.load(f)
                self.cookie_status.setText(
                    f"✓ SpecialChem: {len(cookies)} cookies configuradas"
                )
                self.cookie_status.setStyleSheet("color: green; font-size: 11px;")
                self.cookie_btn.setText("🔄 Renovar cookies")
            except Exception:
                self.cookie_status.setText("✗ Cookies inválidas")
                self.cookie_status.setStyleSheet("color: red; font-size: 11px;")
        else:
            self.cookie_status.setText("✗ SpecialChem: sin cookies (resultados limitados)")
            self.cookie_status.setStyleSheet("color: orange; font-size: 11px;")
            self.cookie_btn.setText("🔑 Configurar cookies de SpecialChem")

    def _configure_cookies(self):
        """Abre el navegador para configurar cookies de SpecialChem."""
        script_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "imports", "login_setup_specialchem.py"
        )
        script_path = os.path.abspath(script_path)

        if not os.path.exists(script_path):
            QMessageBox.warning(
                self, "Error",
                f"No se encuentra el script:\n{script_path}"
            )
            return

        # Try scraper_env python first, then system python
        python_paths = [
            os.path.expanduser("~/scraper_env/bin/python3"),
            os.path.expanduser("~/scraper_env/bin/python"),
            "python3",
            "python",
        ]
        python_cmd = None
        for p in python_paths:
            try:
                subprocess.run(
                    [p, "-c", "import playwright"],
                    capture_output=True, timeout=2
                )
                if os.path.exists(p) or p in ("python3", "python"):
                    python_cmd = p
                    break
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        if not python_cmd:
            QMessageBox.warning(
                self, "Playwright no instalado",
                "No se encontró Playwright. "
                "Instálalo con:\n"
                "  ~/scraper_env/bin/pip install playwright && "
                "~/scraper_env/bin/playwright install chromium"
            )
            return

        QMessageBox.information(
            self, "Configurar cookies",
            "Se abrirá una ventana del navegador.\n\n"
            "1. Resuelve el desafío de Cloudflare manualmente\n"
            "2. Espera a que la página cargue completamente\n"
            "3. Vuelve a esta ventana y presiona Enter en la terminal\n\n"
            "Las cookies se guardarán automáticamente."
        )

        try:
            subprocess.Popen(
                [python_cmd, script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Poll for cookie file creation
            self._poll_cookies()
        except Exception as e:
            QMessageBox.warning(
                self, "Error", f"No se pudo lanzar el script:\n{e}"
            )

    def _poll_cookies(self):
        """Espera a que se creen las cookies y actualiza el estado."""
        import time

        def wait():
            waited = 0
            while waited < 120:
                time.sleep(2)
                waited += 2
                if os.path.exists(SPECIALCHEM_COOKIE_PATH):
                    try:
                        import json
                        with open(SPECIALCHEM_COOKIE_PATH) as f:
                            json.load(f)
                        self._update_cookie_status()
                        return
                    except Exception:
                        continue
            # Timeout
            self.cookie_status.setText("⚠️ Tiempo de espera agotado")
            self.cookie_status.setStyleSheet("color: orange; font-size: 11px;")

        threading.Thread(target=wait, daemon=True).start()

    def _search(self):
        q = self.search_input.text().strip()
        if len(q) < 2:
            return
        self.results_list.clear()
        self.detail_text.setText("Buscando en todas las fuentes...")
        self.search_btn.setEnabled(False)
        self.source_label.setText("")

        def worker():
            results = self.searcher.search(q)
            self.search_finished.emit(results)

        threading.Thread(target=worker, daemon=True).start()

    def _on_search_finished(self, results):
        self.results_list.clear()
        if not results:
            self.detail_text.setText("Sin resultados en ninguna fuente.")
            self.source_label.setText("")
        else:
            source_counts = {}
            for r in results:
                src = r.get("source", "?")
                source_counts[src] = source_counts.get(src, 0) + 1
            sources_str = " | ".join(
                f"{src}: {n}" for src, n in source_counts.items()
            )
            self.source_label.setText(f"Resultados: {sources_str}")
            self.detail_text.setText(
                f"✓ {len(results)} resultados encontrados: {sources_str}"
            )
        for r in results:
            src_tag = r.get("source", "?").upper()
            item = QListWidgetItem(
                f"[{src_tag}] {r.get('name', '?')}  — {r.get('supplier', '?')}"
            )
            item.setData(Qt.UserRole, r)
            self.results_list.addItem(item)
        self.search_btn.setEnabled(True)

    def _show_detail(self, item):
        r = item.data(Qt.UserRole)
        if not r:
            return
        self.detail_text.setText(ChemicalIngredientSearch.format_result(r))
        self.add_btn.setEnabled(True)

    def _add_to_recipe(self):
        item = self.results_list.currentItem()
        if not item:
            return
        r = item.data(Qt.UserRole)
        if not r:
            return

        if self.ingredient_loader is None:
            self.add_to_recipe_requested.emit(r)
            return

        dialog = IngredientEditorDialog(self.ingredient_loader, self)
        self._map_search_result_to_dialog(r, dialog)

        if dialog.exec() == QDialog.Accepted:
            self.add_to_recipe_requested.emit(r)

    @staticmethod
    def _map_search_result_to_dialog(r, dialog):
        """Mapea datos de cualquier fuente (pigment_db, pubchem, wikipedia, specialchem) al editor."""
        source = r.get("source", "")
        name = r.get("name", "")
        props = r.get("properties", {})

        if name:
            dialog.name_input.setText(name)

        # Source-specific mapping
        if source == "pigment_db":
            dialog.type_combo.setCurrentText("color_pigment")
            density = props.get("density_gcm3") or props.get("density", "")
            if density:
                try:
                    dialog.density_spin.setValue(float(str(density).replace(",", ".")))
                except (ValueError, AttributeError):
                    pass
            notes_parts = []
            if props.get("ci_name"):
                notes_parts.append(f"C.I. Name: {props['ci_name']}")
            if props.get("ci_number"):
                notes_parts.append(f"C.I. Number: {props['ci_number']}")
            if props.get("chemical_class"):
                notes_parts.append(f"Clase: {props['chemical_class']}")
            if props.get("cas"):
                notes_parts.append(f"CAS: {props['cas']}")
            if props.get("formula"):
                notes_parts.append(f"Fórmula: {props['formula']}")
            if props.get("trade_names"):
                notes_parts.append(f"Nombres comerciales: {props['trade_names']}")
            if props.get("common_names"):
                notes_parts.append(f"Alias: {', '.join(props['common_names'][:3])}")
            if notes_parts:
                dialog.notes_input.setPlainText("\n".join(notes_parts))

        elif source == "pubchem":
            dialog.type_combo.setCurrentText("active_solvent")
            mw = props.get("MolecularWeight", "")
            formula = props.get("MolecularFormula", "")
            iupac = props.get("IUPACName", "")
            smiles = props.get("CanonicalSMILES", "")
            logp = props.get("XLogP", "")
            notes_parts = []
            if formula:
                notes_parts.append(f"Fórmula: {formula}")
            if mw:
                notes_parts.append(f"MW: {mw}")
            if iupac:
                notes_parts.append(f"IUPAC: {iupac}")
            if smiles:
                notes_parts.append(f"SMILES: {smiles}")
            if logp:
                notes_parts.append(f"XLogP: {logp}")
            if notes_parts:
                dialog.notes_input.setPlainText("\n".join(notes_parts))

        elif source == "wikipedia":
            dialog.type_combo.setCurrentText("base_resin")
            desc = r.get("description", "")
            if desc:
                dialog.notes_input.setPlainText(f"Wikipedia: {desc}")

        elif source == "specialchem":
            dialog.type_combo.setCurrentText("additives")
            notes_parts = []
            if r.get("supplier"):
                notes_parts.append(f"Proveedor: {r['supplier']}")
            if r.get("description"):
                notes_parts.append(r["description"])
            if r.get("url"):
                notes_parts.append(f"URL: {r['url']}")
            if notes_parts:
                dialog.notes_input.setPlainText("\n".join(notes_parts))


class CuttingStageWidget(QWidget):
    """Etapa de formulación: editor de recetas + navegador de ingredientes + análisis + solución de problemas."""

    analysis_requested = Signal(object)
    translate_requested = Signal(str, str)  # (text, target_lang)

    def __init__(self, ingredient_loader: IngredientLoader, parent=None):
        super().__init__(parent)
        self.ingredient_loader = ingredient_loader
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QLabel("🧪 Formulación de Laca — Ingredientes, Recetas y Análisis")
        header.setStyleSheet("font-weight: bold; font-size: 16px; padding: 4px;")
        header.setToolTip("🔹 Panel principal de formulación.\n🔹 Izquierda: ingredientes, pigmentos y búsqueda multi-fuente.\n🔹 Derecha: editor de recetas con análisis y comparación.")
        layout.addWidget(header)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_tabs = QTabWidget()
        left_tabs.setToolTip("Pestañas de ingredientes:\n• BD de Ingredientes — catálogo completo de ingredientes\n• Pigmentos y Solventes — búsqueda local de pigmentos\n• SpecialChem — búsqueda multi-fuente")
        self.ingredient_browser = IngredientBrowserWidget(self.ingredient_loader)
        left_tabs.addTab(self.ingredient_browser, "BD de Ingredientes")
        self.pigment_search = PigmentSearchWidget()
        left_tabs.addTab(self.pigment_search, "Pigmentos y Solventes")
        self.pigment_search.add_to_recipe_requested.connect(self._on_pigment_add_to_recipe)
        self.specialchem_search = SpecialChemSearchWidget(self.ingredient_loader)
        left_tabs.addTab(self.specialchem_search, "SpecialChem")
        self.specialchem_search.add_to_recipe_requested.connect(self._on_source_add_to_recipe)
        left_layout.addWidget(left_tabs)

        self.troubleshooting = TroubleshootingPanel("cutting")
        self.troubleshooting.setToolTip("🔍 Solución de problemas específicos de la etapa de corte. Busca defectos, causas y soluciones.")
        left_layout.addWidget(self.troubleshooting, 1)
        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_tabs = QTabWidget()
        right_tabs.setToolTip("Editor de recetas:\n• Componentes — añade/quita ingredientes\n• Pros/Contras — metadatos de la receta\n• Análisis de Laca — ejecuta análisis completo\n• Comparar Recetas — compara dos recetas lado a lado")
        self.recipe_editor = RecipeEditorWidget(self.ingredient_loader)
        right_tabs.addTab(self.recipe_editor, "Editor de Recetas")
        right_layout.addWidget(right_tabs)

        self.knowledge_qa = KnowledgeQAPanel("cutting")
        self.knowledge_qa.setToolTip("💡 Base de conocimiento y Q&A con LLM para la etapa de formulación. Consulta documentos del foro y haz preguntas.")
        right_layout.addWidget(self.knowledge_qa, 1)
        splitter.addWidget(right_panel)

        splitter.setSizes([400, 500])
        layout.addWidget(splitter, 1)

        self.ingredient_browser.ingredients_changed.connect(self.recipe_editor.refresh_selector)
        self.recipe_editor.analysis_requested.connect(
            lambda: self.analysis_requested.emit(None)
        )
        self.recipe_editor.translate_requested.connect(
            lambda text, lang: self.translate_requested.emit(text, lang)
        )

    def _on_pigment_add_to_recipe(self, pigment_data):
        dialog = IngredientEditorDialog(self.ingredient_loader, self)
        _map_pigment_to_ingredient(pigment_data, dialog)
        if dialog.exec() == QDialog.Accepted:
            name = pigment_data.get("ci_name") or ""
            if not name:
                names = pigment_data.get("common_names", [])
                name = names[0] if names else ""
            self.recipe_editor.add_ingredient_by_name(name)

    def _on_source_add_to_recipe(self, result):
        name = result.get("name", "")
        if name:
            self.recipe_editor.add_ingredient_by_name(name)
        else:
            self.ingredient_browser.refresh()
            self.recipe_editor.refresh_selector()

    def set_llm(self, llm):
        self.knowledge_qa.set_llm(llm)

    def set_knowledge_base(self, kb):
        self.knowledge_qa.set_knowledge_base(kb)

    def set_settings(self, settings):
        self.knowledge_qa.set_settings(settings)

    def abort_llm(self):
        self.knowledge_qa.abort_llm()
