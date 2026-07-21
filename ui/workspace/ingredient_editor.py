"""Editor completo de ingredientes — sin necesidad de editar archivos de configuración."""

from pathlib import Path
from typing import Optional
import yaml

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QTextEdit, QGroupBox,
    QPushButton, QMessageBox,
)
from PySide6.QtCore import Qt

from src.models import Ingredient, IngredientType
from src.ingredient_loader import IngredientLoader

TYPE_CHOICES = [t.value for t in IngredientType]
CATEGORY_MAP = {
    "base_resin": "resins",
    "plasticizer": "additives",
    "active_solvent": "solvents",
    "tail_solvent": "solvents",
    "leveling": "additives",
    "defoamer": "additives",
    "adhesion": "additives",
    "uv_stabilizer": "additives",
    "wetting": "additives",
    "white_pigment": "pigments",
    "black_pigment": "pigments",
    "color_pigment": "pigments",
    "silvering": "plating",
    "nickel_sulfamate": "plating",
    "process": "plating",
}


class IngredientEditorDialog(QDialog):
    """Añadir o editar un ingrediente con todas las propiedades, banderas de recubrimiento, etc."""

    def __init__(self, loader: IngredientLoader, parent=None,
                 ingredient: Optional[Ingredient] = None):
        super().__init__(parent)
        self.loader = loader
        self.ingredient = ingredient
        self.is_new = ingredient is None
        self.setWindowTitle("Añadir Ingrediente" if self.is_new else f"Editar {ingredient.name}")
        self.setMinimumWidth(500)
        self._init_ui()
        if not self.is_new:
            self._load_ingredient()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        basic_group = QGroupBox("Información Básica")
        basic_group.setToolTip("Información básica del ingrediente: nombre, tipo y notas")
        basic_form = QFormLayout(basic_group)

        self.name_input = QLineEdit()
        self.name_input.setToolTip("Nombre único del ingrediente. Se usará para identificarlo en las recetas")
        self.name_input.setPlaceholderText("ej. Nitrocelulosa RS 1/2 seg")
        basic_form.addRow("Nombre:", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.setToolTip("Tipo de ingrediente: resina base, solvente, plastificante, pigmento, aditivo, etc. Determina cómo se clasifica en la base de datos")
        self.type_combo.addItems(TYPE_CHOICES)
        basic_form.addRow("Tipo:", self.type_combo)

        self.notes_input = QTextEdit()
        self.notes_input.setToolTip("Notas adicionales: datos del fabricante, CAS, fórmula química, observaciones")
        self.notes_input.setMaximumHeight(60)
        self.notes_input.setPlaceholderText("Notas opcionales...")
        basic_form.addRow("Notas:", self.notes_input)

        layout.addWidget(basic_group)

        props_group = QGroupBox("Propiedades del Recubrimiento")
        props_group.setToolTip("Propiedades físico-químicas del ingrediente para cálculos de formulación y análisis")
        props_form = QFormLayout(props_group)

        self.solids_spin = QDoubleSpinBox()
        self.solids_spin.setToolTip("Porcentaje de sólidos del ingrediente. Afecta al cálculo de sólidos totales de la receta")
        self.solids_spin.setRange(0, 100)
        self.solids_spin.setSuffix(" %")
        self.solids_spin.setValue(100)
        props_form.addRow("Contenido de sólidos:", self.solids_spin)

        self.viscosity_spin = QSpinBox()
        self.viscosity_spin.setToolTip("Viscosidad del ingrediente en mPa·s. Influye en la viscosidad estimada de la mezcla")
        self.viscosity_spin.setRange(0, 50000)
        self.viscosity_spin.setSuffix(" mPa·s")
        props_form.addRow("Viscosidad:", self.viscosity_spin)

        self.max_conc_spin = QDoubleSpinBox()
        self.max_conc_spin.setToolTip("Concentración máxima recomendada en porcentaje. Ayuda a evitar sobre-dosificación")
        self.max_conc_spin.setRange(0, 100)
        self.max_conc_spin.setSuffix(" %")
        props_form.addRow("Concentración máxima:", self.max_conc_spin)

        self.dosage_spin = QDoubleSpinBox()
        self.dosage_spin.setToolTip("Dosificación típica sugerida como punto de partida")
        self.dosage_spin.setRange(0, 100)
        self.dosage_spin.setSuffix(" %")
        self.dosage_spin.setDecimals(2)
        props_form.addRow("Dosis recomendada:", self.dosage_spin)

        self.density_spin = QDoubleSpinBox()
        self.density_spin.setToolTip("Densidad en g/cm³. Se usa para cálculos de formulación")
        self.density_spin.setRange(0, 20)
        self.density_spin.setDecimals(3)
        self.density_spin.setSuffix(" g/cm³")
        props_form.addRow("Densidad:", self.density_spin)

        self.evap_spin = QDoubleSpinBox()
        self.evap_spin.setToolTip("Índice de evaporación relativo (butilacetato=1). Controla la velocidad de secado")
        self.evap_spin.setRange(0, 10)
        self.evap_spin.setSingleStep(0.1)
        self.evap_spin.setDecimals(2)
        props_form.addRow("Tasa de evaporación:", self.evap_spin)

        self.boiling_spin = QSpinBox()
        self.boiling_spin.setToolTip("Punto de ebullición en °C. Importante para el perfil de evaporación")
        self.boiling_spin.setRange(0, 500)
        self.boiling_spin.setSuffix(" °C")
        props_form.addRow("Punto de ebullición:", self.boiling_spin)

        self.surface_tension_spin = QDoubleSpinBox()
        self.surface_tension_spin.setToolTip("Tensión superficial en mN/m. Afecta al mojado y la adhesión")
        self.surface_tension_spin.setRange(0, 100)
        self.surface_tension_spin.setDecimals(1)
        self.surface_tension_spin.setSuffix(" dynes/cm")
        self.surface_tension_spin.setValue(35.0)
        props_form.addRow("Tensión superficial:", self.surface_tension_spin)

        layout.addWidget(props_group)

        warn_group = QGroupBox("Advertencias")
        warn_group.setToolTip("Advertencias y precauciones de seguridad para la manipulación")
        warn_layout = QVBoxLayout(warn_group)
        self.warnings_input = QTextEdit()
        self.warnings_input.setToolTip("Advertencias de seguridad: toxicidad, inflamabilidad, irritación, manipulación requerida")
        self.warnings_input.setMaximumHeight(60)
        self.warnings_input.setPlaceholderText("Uno por línea, ej. Higroscópico — almacenar sellado")
        warn_layout.addWidget(self.warnings_input)
        layout.addWidget(warn_group)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Guardar")
        save_btn.setToolTip("Guarda el ingrediente en la base de datos personal (custom_ingredients.yaml)")
        save_btn.clicked.connect(self._save)
        save_btn.setMinimumWidth(100)
        save_btn.setStyleSheet("background: #4CAF50; color: white; font-weight: bold;")
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setToolTip("Descarta los cambios y cierra el editor")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumWidth(100)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _load_ingredient(self):
        ing = self.ingredient
        self.name_input.setText(ing.name)
        idx = self.type_combo.findText(ing.type.value)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        cp = ing.coating_properties
        self.solids_spin.setValue(float(cp.solids_content_pct or 100))
        self.viscosity_spin.setValue(int(float(cp.viscosity_mpas or 0)))
        self.max_conc_spin.setValue(float(ing.max_concentration_pct or 0))
        self.dosage_spin.setValue(float(getattr(ing, 'dosage_pct', 0) or 0))
        self.density_spin.setValue(float(ing.properties.get("density_gcm3", 0)))
        self.evap_spin.setValue(float(cp.evaporation_rate or 0))
        self.boiling_spin.setValue(int(float(ing.properties.get("boiling_point_c", 0))))
        self.surface_tension_spin.setValue(cp.surface_tension_dynes)
        self.warnings_input.setPlainText("\n".join(ing.warnings))
        self.notes_input.setPlainText(ing.notes)

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Guardar Ingrediente", "El nombre es obligatorio")
            return

        ing_type = self.type_combo.currentText()
        category = CATEGORY_MAP.get(ing_type, "additives")

        warnings_list = [
            w.strip() for w in self.warnings_input.toPlainText().split("\n") if w.strip()
        ]

        if self.is_new:
            custom_path = Path(__file__).parent.parent.parent / "config" / "custom_ingredients.yaml"
        else:
            custom_path = Path(__file__).parent.parent.parent / "config" / "custom_ingredients.yaml"

        existing = {}
        if custom_path.exists():
            with open(custom_path) as f:
                existing = yaml.safe_load(f) or {}

        if category not in existing:
            existing[category] = []

        prefixes = {"resins": "RES", "solvents": "SOL", "additives": "ADD", "pigments": "PIG"}
        prefix = prefixes.get(category, "CUS")
        existing_ids = {i.get("id", "") for i in existing.get(category, [])}
        if self.is_new:
            counter = 1
            while f"{prefix}-C{counter:03d}" in existing_ids:
                counter += 1
            entry_id = f"{prefix}-C{counter:03d}"
        else:
            entry_id = self.ingredient.id

        entry = {
            "id": entry_id,
            "name": name,
            "type": ing_type,
        }

        solids = self.solids_spin.value()
        if solids != 100:
            entry["solids_content"] = solids

        visc = self.viscosity_spin.value()
        if visc:
            entry["viscosity_mpas"] = visc

        maxc = self.max_conc_spin.value()
        if maxc:
            entry["max_concentration_pct"] = maxc

        dosage = self.dosage_spin.value()
        if dosage:
            entry["dosage_pct"] = dosage

        evap = self.evap_spin.value()
        if evap:
            entry["evaporation_rate"] = evap

        bp = self.boiling_spin.value()
        if bp:
            entry["boiling_point_c"] = bp

        density = self.density_spin.value()
        if density:
            entry["density_gcm3"] = density

        st = self.surface_tension_spin.value()
        if st != 35.0:
            entry["surface_tension_dynes"] = st

        if warnings_list:
            entry["warnings"] = warnings_list

        notes = self.notes_input.toPlainText().strip()
        if notes:
            entry["notes"] = notes

        if self.is_new:
            existing[category].append(entry)
        else:
            for i, item in enumerate(existing.get(category, [])):
                if item.get("id") == entry_id:
                    existing[category][i] = entry
                    break
            else:
                existing[category].append(entry)

        custom_path.parent.mkdir(parents=True, exist_ok=True)
        with open(custom_path, "w") as f:
            yaml.dump(existing, f, default_flow_style=False, allow_unicode=True)

        QMessageBox.information(
            self, "Guardado",
            f"Ingrediente '{name}' guardado en custom_ingredients.yaml"
        )
        self.accept()
