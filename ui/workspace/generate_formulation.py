"""Diálogo para generar una formulación a partir de especificaciones de alto nivel"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QDoubleSpinBox, QComboBox, QGroupBox,
    QPushButton, QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt

from src.models import (
    LacquerRecipe, RecipeComponent, Ingredient, IngredientType
)
from src.ingredient_loader import IngredientLoader


class GenerateFormulationDialog(QDialog):
    def __init__(self, loader: IngredientLoader, parent=None):
        super().__init__(parent)
        self.loader = loader
        self._generated_recipe = None
        self.setWindowTitle("Generar Formulación desde Especificación")
        self.setMinimumWidth(500)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        req_group = QGroupBox("Requisitos")
        req_layout = QFormLayout()

        self.application = QComboBox()
        self.application.addItems(["curtain_coater", "spray", "dip", "roller"])
        self.application.setToolTip("Método de aplicación objetivo: cortina (curtain_coater) o spin (spin_coater)")
        req_layout.addRow("Aplicación:", self.application)

        self.target_viscosity = QDoubleSpinBox()
        self.target_viscosity.setRange(100, 3000)
        self.target_viscosity.setValue(600)
        self.target_viscosity.setSuffix(" mPa·s")
        self.target_viscosity.setToolTip("Viscosidad objetivo deseada en mPa·s")
        req_layout.addRow("Viscosidad objetivo:", self.target_viscosity)

        self.target_solids = QDoubleSpinBox()
        self.target_solids.setRange(10, 60)
        self.target_solids.setValue(35)
        self.target_solids.setSuffix(" %")
        self.target_solids.setToolTip("Porcentaje de sólidos objetivo en la formulación final")
        req_layout.addRow("Sólidos objetivo:", self.target_solids)

        self.cure_type = QComboBox()
        self.cure_type.addItems(["ambient_dry", "forced_air_80C", "oven_150C", "uv_cure"])
        self.cure_type.setToolTip("Tipo de curado: temperatura ambiente (ambient) u horno (oven)")
        req_layout.addRow("Tipo de curado:", self.cure_type)

        self.film_type = QComboBox()
        self.film_type.addItems(["clear", "white", "black", "color"])
        self.film_type.setToolTip("Tipo de película: transparente (clear) o pigmentada (pigmented)")
        req_layout.addRow("Tipo de película:", self.film_type)

        req_group.setLayout(req_layout)
        layout.addWidget(req_group)

        gen_btn = QPushButton("Generar Formulación")
        gen_btn.clicked.connect(self._generate)
        gen_btn.setToolTip("Genera una formulación sugerida basada en las especificaciones ingresadas")
        layout.addWidget(gen_btn)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setToolTip("Formulación generada: lista de ingredientes sugeridos con concentraciones")
        layout.addWidget(self.result_text)

        btn_layout = QHBoxLayout()
        self.accept_btn = QPushButton("Usar Esta Formulación")
        self.accept_btn.clicked.connect(self.accept)
        self.accept_btn.setEnabled(False)
        self.accept_btn.setToolTip("Usa la formulación generada como receta actual")
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.accept_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _generate(self):
        components = []

        resins = self.loader.get_by_type(IngredientType.BASE_RESIN)
        active_solvents = self.loader.get_by_type(IngredientType.ACTIVE_SOLVENT)
        tail_solvents = self.loader.get_by_type(IngredientType.TAIL_SOLVENT)
        leveling = self.loader.get_by_type(IngredientType.LEVELING)
        defoamer = self.loader.get_by_type(IngredientType.DEFOAMER)

        if not resins:
            QMessageBox.warning(self, "Generación", "No se encontraron resinas base")
            return

        if resins:
            components.append(RecipeComponent(resins[0], 25.0))

        if active_solvents:
            components.append(RecipeComponent(active_solvents[0], 40.0))

        if tail_solvents:
            components.append(RecipeComponent(tail_solvents[0], 15.0))

        if leveling:
            components.append(RecipeComponent(leveling[0], 0.5))

        if defoamer:
            components.append(RecipeComponent(defoamer[0], 0.3))

        remaining = 100 - sum(c.concentration_pct for c in components)
        if remaining > 0 and active_solvents:
            components.append(RecipeComponent(active_solvents[0], remaining))

        self._generated_recipe = LacquerRecipe(
            id="generated",
            name=f"Formulación {self.film_type.currentText()} Generada",
            components=components,
            target_viscosity_mpas=self.target_viscosity.value(),
            target_solids_pct=self.target_solids.value()
        )

        text = "<h3>Formulación Generada</h3>"
        text += f"<p>Tipo de película: {self.film_type.currentText()}</p>"
        text += f"<p>Sólidos Est.: {self._generated_recipe.total_solids():.1f}%</p>"
        text += f"<p>Visc. Est.: {self._generated_recipe.estimated_viscosity():.0f} mPa·s</p>"
        text += "<ul>"
        for comp in components:
            text += f"<li>{comp.ingredient.name}: {comp.concentration_pct}%</li>"
        text += "</ul>"
        self.result_text.setHtml(text)
        self.accept_btn.setEnabled(True)

    def get_recipe(self) -> LacquerRecipe:
        return self._generated_recipe
