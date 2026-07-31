"""Editor de recetas para crear y modificar formulaciones de laca"""

import json
import os
import time
import yaml
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QLineEdit, QDoubleSpinBox,
    QComboBox, QGroupBox, QFormLayout, QHeaderView, QMessageBox,
    QTextEdit, QSplitter, QTabWidget,
)
from PySide6.QtCore import Signal, Qt

from src.models import (
    LacquerRecipe, RecipeComponent, Ingredient, IngredientType
)
from src.ingredient_loader import IngredientLoader
from ui.workspace.recipe_analysis_panel import RecipeAnalysisPanel
from ui.workspace.recipe_comparison import RecipeComparisonWidget
from core.translations import T, translator

PRESET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "preset_recipes.yaml"
)
CUSTOM_PRESET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "custom_presets.yaml"
)
SETTINGS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", ".recipe_settings.json"
)


class RecipeEditorWidget(QWidget):
    analysis_requested = Signal()
    translate_requested = Signal(str, str)  # (text, target_lang)

    def __init__(self, ingredient_loader: IngredientLoader):
        super().__init__()
        self.loader = ingredient_loader
        self.current_recipe: Optional[LacquerRecipe] = None
        self._presets: List[Dict] = []
        self._load_presets()
        self._init_ui()
        self._load_settings()

    def _load_presets(self):
        path = os.path.abspath(PRESET_PATH)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    self._presets = yaml.safe_load(f) or []
            except Exception as e:
                print(f"Error loading presets: {e}")
                self._presets = []

        # Cargar presets personalizados
        custom_path = os.path.abspath(CUSTOM_PRESET_PATH)
        if os.path.exists(custom_path):
            try:
                with open(custom_path) as f:
                    custom = yaml.safe_load(f) or []
                for p in custom:
                    p["_custom"] = True
                self._presets.extend(custom)
            except Exception as e:
                print(f"Error loading custom presets: {e}")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        header_group = QGroupBox(T("Información de la Receta"))
        header_group.setToolTip(T("Define el nombre y los parámetros objetivo de la receta (viscosidad, sólidos)"))

        header_layout = QFormLayout()

        preset_row = QHBoxLayout()
        self.preset_selector = QComboBox()
        self.preset_selector.setMinimumWidth(300)
        self._populate_presets()
        self.preset_selector.currentIndexChanged.connect(self._on_preset_selected)
        self.preset_selector.setToolTip(T("Selecciona una receta predefinida como punto de partida. Las recetas se cargan desde preset_recipes.yaml"))
        preset_row.addWidget(QLabel(T("Predefinidas:")))
        preset_row.addWidget(self.preset_selector)
        preset_row.addStretch()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(T("Nombre de la receta"))
        self.name_input.setToolTip(T("Nombre descriptivo para tu receta. Aparecerá en la lista de recetas y en los análisis"))
        self.target_viscosity = QDoubleSpinBox()
        self.target_viscosity.setRange(50, 5000)
        self.target_viscosity.setSuffix(" mPa·s")
        self.target_viscosity.setValue(500)
        self.target_viscosity.setToolTip(T("Viscosidad objetivo en mPa·s. Se usa como referencia en el análisis"))
        self.target_solids = QDoubleSpinBox()
        self.target_solids.setRange(0, 80)
        self.target_solids.setSuffix(" %")
        self.target_solids.setValue(35)
        self.target_solids.setDecimals(1)
        self.target_solids.setSpecialValueText("N/A")
        self.target_solids.setToolTip(T("Porcentaje de sólidos objetivo. Ayuda a calcular la formulación esperada"))

        header_layout.addRow(preset_row)
        header_layout.addRow(T("Nombre:"), self.name_input)
        header_layout.addRow(T("Viscosidad Objetivo:"), self.target_viscosity)
        header_layout.addRow(T("Sólidos Objetivo:"), self.target_solids)
        header_group.setLayout(header_layout)
        layout.addWidget(header_group)

        # Tabs: componentes + metadata + análisis + comparación
        tabs = QTabWidget()
        tabs.setToolTip(T("Tabs del editor de recetas:\n• Componentes — gestiona los ingredientes\n• Pros/Contras & Hardware — metadatos y notas\n• Análisis de Laca — análisis físico completo\n• Comparar Recetas — comparación lado a lado"))

        # Tab de componentes
        comp_widget = QWidget()
        comp_layout = QVBoxLayout(comp_widget)

        add_row = QHBoxLayout()
        self.ingredient_selector = QComboBox()
        self.ingredient_selector.setMinimumWidth(300)
        self.ingredient_selector_ingredients = []
        self._populate_selector()
        self.ingredient_selector.setToolTip(T("Selecciona un ingrediente de la base de datos para añadirlo a la receta. Los ingredientes se filtran automáticamente"))
        self.add_btn = QPushButton(T("Añadir Componente"))
        self.add_btn.clicked.connect(self._add_component)
        self.add_btn.setToolTip(T("Añade el ingrediente seleccionado a la tabla de componentes con la concentración indicada"))
        add_row.addWidget(QLabel(T("Añadir desde BD:")))
        add_row.addWidget(self.ingredient_selector)
        add_row.addWidget(self.add_btn)
        add_row.addStretch()
        comp_layout.addLayout(add_row)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            T("Ingrediente"), T("Tipo"), T("Concentración %"), T("Máx %")
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setToolTip(T("Tabla de componentes de la receta. Cada fila es un ingrediente con su tipo, concentración y concentración máxima recomendada"))
        comp_layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.remove_btn = QPushButton(T("Quitar Seleccionado"))
        self.remove_btn.clicked.connect(self._remove_component)
        self.remove_btn.setToolTip(T("Elimina el componente seleccionado de la tabla"))
        self.clear_btn = QPushButton(T("Limpiar Todo"))
        self.clear_btn.clicked.connect(self._clear_recipe)
        self.clear_btn.setToolTip(T("Elimina todos los componentes de la receta"))
        self.save_preset_btn = QPushButton(T("Guardar como Preset"))
        self.save_preset_btn.setStyleSheet(
            "background-color: #FF9800; color: white; font-weight: bold; padding: 6px;"
        )
        self.save_preset_btn.clicked.connect(self._save_custom_preset)
        self.save_preset_btn.setToolTip(T("Guarda la receta actual como un preset personalizado para usarlo después"))
        btn_row.addWidget(self.remove_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.save_preset_btn)
        comp_layout.addLayout(btn_row)

        tabs.addTab(comp_widget, T("Componentes"))

        # Tab de metadatos (pros/cons/hardware)
        meta_widget = QWidget()
        meta_layout = QVBoxLayout(meta_widget)

        meta_header = QHBoxLayout()
        meta_header.addWidget(QLabel(""))
        self.translate_meta_btn = QPushButton(T("🌐 Traducir"))
        self.translate_meta_btn.setMaximumWidth(120)
        self.translate_meta_btn.clicked.connect(self._on_translate_meta)
        self.translate_meta_btn.setToolTip(T("Traduce el contenido de metadatos al idioma seleccionado usando el LLM"))
        meta_header.addWidget(self.translate_meta_btn)
        meta_header.addStretch()
        meta_layout.addLayout(meta_header)
        self.metadata_text = QTextEdit()
        self.metadata_text.setReadOnly(True)
        self.metadata_text.setPlaceholderText(T(
            "Carga una receta predefinida para ver sus pros, contras, "
            "hardware recomendado y casos de uso."
        ))
        self.metadata_text.setToolTip(T("Metadatos de la receta: mejores usos, pros, contras y notas de aplicación. Esta información se guarda con la receta"))
        meta_layout.addWidget(self.metadata_text)
        tabs.addTab(meta_widget, T("Pros/Contras & Hardware"))

        # Tab de análisis
        self.analysis_panel = RecipeAnalysisPanel()
        self.analysis_panel.analyze_btn.clicked.connect(self._on_analyze)
        self.analysis_panel.result_widget.translate_requested.connect(
            lambda text, lang: self.translate_requested.emit(text, lang)
        )
        tabs.addTab(self.analysis_panel, T("Análisis de Laca"))

        # Tab de comparación
        self.comparison = RecipeComparisonWidget()
        tabs.addTab(self.comparison, T("Comparar Recetas"))

        layout.addWidget(tabs)

        # Inicializar comparador con presets
        self._update_comparison_list()

    def _load_settings(self):
        """Carga settings persistentes de la última sesión."""
        path = os.path.abspath(SETTINGS_PATH)
        if not os.path.exists(path):
            return
        try:
            with open(path) as f:
                settings = json.load(f)

            ap = self.analysis_panel.input_panel
            if "temperature" in settings:
                ap.temp_input.setValue(settings["temperature"])
            if "humidity" in settings:
                ap.humidity_input.setValue(settings["humidity"])
            if "thickness" in settings:
                ap.thickness_input.setValue(settings["thickness"])
            if "polish" in settings:
                ap.polish_input.setValue(settings["polish"])
            if "air_velocity" in settings:
                ap.air_velocity.setValue(settings["air_velocity"])
            if "positive_pressure" in settings:
                ap.positive_pressure.setChecked(settings["positive_pressure"])
            if "application" in settings:
                idx = ap.application.findText(settings["application"])
                if idx >= 0:
                    ap.application.setCurrentIndex(idx)

        except Exception as e:
            print(f"Error loading settings: {e}")

    def _save_settings(self):
        """Guarda settings actuales para próxima sesión."""
        ap = self.analysis_panel.input_panel
        settings = {
            "temperature": ap.temp_input.value(),
            "humidity": ap.humidity_input.value(),
            "thickness": ap.thickness_input.value(),
            "polish": ap.polish_input.value(),
            "air_velocity": ap.air_velocity.value(),
            "positive_pressure": ap.positive_pressure.isChecked(),
            "application": ap.application.currentText(),
        }
        try:
            os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
            with open(SETTINGS_PATH, "w") as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def _save_custom_preset(self):
        """Guarda la receta actual como preset personalizado."""
        recipe = self.get_recipe()
        if not recipe:
            QMessageBox.warning(self, T("Guardar Preset"), T("No hay receta para guardar"))
            return

        from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle(T("Guardar como Preset Personalizado"))
        dialog.setMinimumWidth(450)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        name_input = QLineEdit(recipe.name)
        form.addRow(T("Nombre:"), name_input)

        id_input = QLineEdit(f"CUSTOM-{int(time.time())}")
        form.addRow(T("ID:"), id_input)

        notes_input = QTextEdit()
        notes_input.setPlaceholderText(T("Notas sobre esta receta..."))
        form.addRow(T("Notas:"), notes_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        preset = {
            "id": id_input.text().strip() or f"CUSTOM-{int(time.time())}",
            "name": name_input.text().strip() or recipe.name,
            "target_viscosity_mpas": recipe.target_viscosity_mpas,
            "target_solids_pct": recipe.target_solids_pct,
            "application": recipe.application_method or "curtain_coater",
            "coater": recipe.coater_type or "burkle",
            "notes": notes_input.toPlainText().strip(),
            "metadata": {
                "best_for": T("Preset personalizado"),
                "pros": [T("Creado por el usuario")],
                "cons": [],
            },
            "components": [
                {
                    "id": c.ingredient.id,
                    "name": c.ingredient.name,
                    "type": c.ingredient.type.value,
                    "concentration_pct": c.concentration_pct,
                }
                for c in recipe.components
            ],
        }

        # Cargar presets existentes
        custom = []
        custom_path = os.path.abspath(CUSTOM_PRESET_PATH)
        if os.path.exists(custom_path):
            try:
                with open(custom_path) as f:
                    custom = yaml.safe_load(f) or []
            except Exception:
                custom = []

        # Reemplazar si ya existe un preset con el mismo ID
        existing = None
        for i, p in enumerate(custom):
            if p.get("id") == preset["id"]:
                existing = i
                break
        if existing is not None:
            custom[existing] = preset
        else:
            custom.append(preset)

        try:
            os.makedirs(os.path.dirname(custom_path), exist_ok=True)
            with open(custom_path, "w") as f:
                yaml.dump(custom, f, default_flow_style=False, allow_unicode=True)

            # Update in-memory selector immediately
            preset["_custom"] = True
            for i, p in enumerate(self._presets):
                if p.get("id") == preset["id"]:
                    self._presets[i] = preset
                    break
            else:
                self._presets.append(preset)
            self._populate_presets()
            self._update_comparison_list()

            QMessageBox.information(
                self, T("Guardado"),
                T("Preset '{name}' guardado.").format(name=preset['name'])
            )
        except Exception as e:
            QMessageBox.critical(self, T("Error"), T("No se pudo guardar: {error}").format(error=e))

    def _populate_presets(self):
        self.preset_selector.blockSignals(True)
        self.preset_selector.clear()
        self.preset_selector.addItem(T("— Cargar receta predefinida —"), None)
        for p in self._presets:
            self.preset_selector.addItem(
                f"{p.get('name', '?')}  ({p.get('id', '')})", p
            )
        self.preset_selector.blockSignals(False)

    def _on_preset_selected(self, idx):
        if idx <= 0:
            return
        preset = self.preset_selector.currentData()
        if not preset:
            return

        self.set_recipe_from_preset(preset)

    def set_recipe_from_preset(self, data: dict):
        """Carga una receta desde datos de preset."""
        components = []
        for comp_data in data.get("components", []):
            ing = self.loader.get_by_id(comp_data.get("id", ""))
            if not ing:
                ing = self.loader.get_by_name(comp_data.get("name", "").lower())
            if ing:
                components.append(RecipeComponent(
                    ingredient=ing,
                    concentration_pct=comp_data.get("concentration_pct", comp_data.get("concentration", 10))
                ))

        recipe = LacquerRecipe(
            id=data.get("id", "preset"),
            name=data.get("name", T("Receta Predefinida")),
            components=components,
            target_viscosity_mpas=data.get("target_viscosity_mpas"),
            target_solids_pct=data.get("target_solids_pct"),
            application_method=data.get("application", "curtain_coater"),
            coater_type=data.get("coater", "burkle"),
            notes=data.get("notes", ""),
            metadata=data.get("metadata", {}),
        )
        self.set_recipe(recipe)

    def _update_metadata_display(self):
        meta = {}
        if self.current_recipe and self.current_recipe.metadata:
            meta = self.current_recipe.metadata

        if not meta:
            self.metadata_text.setPlainText(T(
                "Esta receta no tiene metadatos asociados.\n"
                "Los metadatos están disponibles solo para recetas predefinidas."
            ))
            return

        lines = []
        if meta.get("best_for"):
            lines.append(T("🎯 MEJOR PARA:"))
            lines.append(f"   {meta['best_for']}")
            lines.append("")

        if meta.get("pros"):
            lines.append(T("✅ VENTAJAS:"))
            for p in meta["pros"]:
                lines.append(f"   • {p}")
            lines.append("")

        if meta.get("cons"):
            lines.append(T("⚠️  DESVENTAJAS:"))
            for c in meta["cons"]:
                lines.append(f"   • {c}")
            lines.append("")

        if meta.get("hardware"):
            hw = meta["hardware"]
            lines.append(T("🔧 HARDWARE RECOMENDADO:"))
            if hw.get("coater_type"):
                lines.append(f"   {T('Cortinado:')} {hw['coater_type']}")
            if hw.get("drying"):
                lines.append(f"   {T('Secado:')} {hw['drying']}")
            if hw.get("curing"):
                lines.append(f"   {T('Curado:')} {hw['curing']}")
            if hw.get("cutting_lathe"):
                lines.append(f"   {T('Torno:')} {hw['cutting_lathe']}")
            if hw.get("stylus"):
                lines.append(f"   {T('Aguja:')} {hw['stylus']}")
            if hw.get("rectifier"):
                lines.append(f"   {T('Rectificador:')} {hw['rectifier']}")
            if hw.get("tank"):
                lines.append(f"   {T('Tanque:')} {hw['tank']}")
            if hw.get("anodes"):
                lines.append(f"   {T('Ánodos:')} {hw['anodes']}")
            if hw.get("filtration"):
                lines.append(f"   {T('Filtración:')} {hw['filtration']}")
            if hw.get("temperature"):
                lines.append(f"   {T('Temperatura:')} {hw['temperature']}")
            lines.append("")

        if meta.get("common_issues"):
            lines.append(T("🔴 PROBLEMAS COMUNES Y SOLUCIONES:"))
            for issue in meta["common_issues"]:
                lines.append(f"   • {issue}")
            lines.append("")

        if self.current_recipe and self.current_recipe.notes:
            lines.append(T("📝 NOTAS:"))
            lines.append(f"   {self.current_recipe.notes}")

        self.metadata_text.setPlainText("\n".join(lines))

    def _update_comparison_list(self):
        """Actualiza el comparador con todas las recetas disponibles (presets + actual)."""
        recipes = []
        # Add current recipe first
        if self.current_recipe:
            recipes.append(self.current_recipe)
        # Add all presets
        for p in self._presets:
            try:
                components = []
                for comp_data in p.get("components", []):
                    ing = self.loader.get_by_id(comp_data.get("id", ""))
                    if not ing:
                        ing = self.loader.get_by_name(comp_data.get("name", "").lower())
                    if ing:
                        components.append(RecipeComponent(
                            ingredient=ing,
                            concentration_pct=comp_data.get("concentration_pct", 10)
                        ))
                if components:
                    recipes.append(LacquerRecipe(
                        id=p.get("id", ""),
                        name=p.get("name", ""),
                        components=components,
                    ))
            except Exception:
                pass
        self.comparison.set_recipes(recipes)

    def _populate_selector(self):
        self.ingredient_selector.clear()
        self.ingredient_selector_ingredients.clear()
        for ing in self.loader.all_types().values():
            for item in ing:
                label = f"[{item.type.value}] {item.name} ({item.id})"
                self.ingredient_selector.addItem(label, item)
                self.ingredient_selector_ingredients.append(item)

    def refresh_selector(self):
        current = self.ingredient_selector.currentText()
        self.loader.load_all()
        self._populate_selector()
        idx = self.ingredient_selector.findText(current)
        if idx >= 0:
            self.ingredient_selector.setCurrentIndex(idx)

    def add_ingredient_by_name(self, name: str) -> bool:
        """Busca un ingrediente por nombre en el selector y lo añade a la tabla."""
        self.refresh_selector()
        for i in range(self.ingredient_selector.count()):
            ing = self.ingredient_selector.itemData(i)
            if ing and ing.name.lower() == name.lower():
                self.ingredient_selector.setCurrentIndex(i)
                self._add_component()
                return True
        return False

    def _add_component(self):
        ingredient = self.ingredient_selector.currentData()
        if not ingredient:
            return

        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(ingredient.name))
        self.table.setItem(row, 1, QTableWidgetItem(ingredient.type.value))
        conc = QDoubleSpinBox()
        conc.setRange(0.1, 100)
        conc.setDecimals(2)
        conc.setSuffix(" %")
        conc.setSingleStep(0.1)
        conc.setValue(10)
        conc.valueChanged.connect(lambda: self._on_data_changed())
        self.table.setCellWidget(row, 2, conc)

        max_conc = ingredient.max_concentration_pct
        if max_conc:
            max_item = QTableWidgetItem(f"{max_conc}%")
            max_item.setFlags(max_item.flags() & ~Qt.ItemIsEditable)
        else:
            max_item = QTableWidgetItem("N/D")
            max_item.setFlags(max_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 3, max_item)

    def _remove_component(self):
        rows = set(i.row() for i in self.table.selectedIndexes())
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)

    def _clear_recipe(self):
        self.table.setRowCount(0)
        self.name_input.clear()

    def _on_data_changed(self):
        self._update_comparison_list()

    def get_recipe(self) -> Optional[LacquerRecipe]:
        if self.table.rowCount() == 0:
            return None

        components = []
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text()
            ingredient = self.loader.get_by_name(name.lower())
            if not ingredient:
                for ing in self.loader.all_types().values():
                    for i in ing:
                        if i.name == name:
                            ingredient = i
                            break
            if ingredient:
                conc_widget = self.table.cellWidget(row, 2)
                conc = conc_widget.value() if conc_widget else 10
                components.append(RecipeComponent(
                    ingredient=ingredient,
                    concentration_pct=conc
                ))

        return LacquerRecipe(
            id="manual",
            name=self.name_input.text() or T("Receta sin Título"),
            components=components,
            target_viscosity_mpas=self.target_viscosity.value(),
            target_solids_pct=self.target_solids.value()
        )

    def _on_analyze(self):
        """Ejecuta el análisis completo sobre la receta actual."""
        self._save_settings()
        recipe = self.get_recipe()
        if recipe:
            self.analysis_panel.analyze_recipe(recipe)
            self.analysis_requested.emit()

    def _on_translate_meta(self):
        text = self.metadata_text.toPlainText()
        if text.strip():
            target = "en" if translator.current_language == "es" else "es"
            self.translate_requested.emit(text, target)

    def set_recipe(self, recipe: LacquerRecipe):
        self._clear_recipe()
        self.current_recipe = recipe
        self.name_input.setText(recipe.name)
        if recipe.target_viscosity_mpas:
            self.target_viscosity.setValue(recipe.target_viscosity_mpas)
        if recipe.target_solids_pct is not None:
            self.target_solids.setValue(recipe.target_solids_pct)

        for comp in recipe.components:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(comp.ingredient.name))
            self.table.setItem(row, 1, QTableWidgetItem(comp.ingredient.type.value))
            conc = QDoubleSpinBox()
            conc.setRange(0.1, 100)
            conc.setDecimals(2)
            conc.setSuffix(" %")
            conc.setSingleStep(0.1)
            conc.setValue(comp.concentration_pct)
            conc.valueChanged.connect(lambda: self._on_data_changed())
            self.table.setCellWidget(row, 2, conc)

            max_conc = comp.ingredient.max_concentration_pct
            if max_conc:
                max_item = QTableWidgetItem(f"{max_conc}%")
                max_item.setFlags(max_item.flags() & ~Qt.ItemIsEditable)
            else:
                max_item = QTableWidgetItem("N/D")
                max_item.setFlags(max_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 3, max_item)
        self._update_metadata_display()
        self._update_comparison_list()

    def import_recipe(self, path: str):
        try:
            with open(path) as f:
                if path.endswith(".json"):
                    data = json.load(f)
                else:
                    data = yaml.safe_load(f)

            components = []
            for comp_data in data.get("components", []):
                ing = self.loader.get_by_name(comp_data.get("name", "").lower())
                if not ing:
                    ing = self.loader.get_by_id(comp_data.get("id", ""))
                if ing:
                    components.append(RecipeComponent(
                        ingredient=ing,
                        concentration_pct=comp_data.get("concentration_pct",
                                                       comp_data.get("concentration", 10))
                    ))

            recipe = LacquerRecipe(
                id=data.get("id", "imported"),
                name=data.get("name", T("Receta Importada")),
                components=components,
                target_viscosity_mpas=data.get("target_viscosity_mpas"),
                target_solids_pct=data.get("target_solids_pct"),
                application_method=data.get("application", "curtain_coater"),
                coater_type=data.get("coater", "burkle"),
                notes=data.get("notes", ""),
                metadata=data.get("metadata", {}),
            )
            self.set_recipe(recipe)

        except Exception as e:
            QMessageBox.critical(self, T("Error de Importación"), str(e))

    def export_recipe(self, path: str):
        recipe = self.get_recipe()
        if not recipe:
            QMessageBox.warning(self, T("Exportar"), T("No hay receta para exportar"))
            return
        data = {
            "id": recipe.id,
            "name": recipe.name,
            "target_viscosity_mpas": recipe.target_viscosity_mpas,
            "target_solids_pct": recipe.target_solids_pct,
            "application": recipe.application_method,
            "coater": recipe.coater_type,
            "notes": recipe.notes,
            "metadata": recipe.metadata,
            "components": [
                {
                    "id": c.ingredient.id,
                    "name": c.ingredient.name,
                    "type": c.ingredient.type.value,
                    "concentration_pct": c.concentration_pct
                }
                for c in recipe.components
            ]
        }
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
