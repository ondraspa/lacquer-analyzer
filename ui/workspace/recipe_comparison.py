"""Comparador de recetas side-by-side — compara composición y propiedades."""

from typing import List, Optional, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QComboBox, QPushButton, QHeaderView, QGroupBox, QScrollArea,
    QGridLayout, QProgressBar, QTabWidget,
)
from PySide6.QtCore import Qt

from src.models import LacquerRecipe
from analysis.lacquer_physics import (
    analyze_lacquer, AnalysisInput, AnalysisResult,
)
from ui.workspace.recipe_analysis_panel import AnalysisResultWidget


class RecipeComparisonWidget(QWidget):
    """Compara dos o más recetas lado a lado."""

    def __init__(self):
        super().__init__()
        self._recipes: List[LacquerRecipe] = []
        self._results: List[Optional[AnalysisResult]] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Selectors
        row1 = QHBoxLayout()
        self.recipe_a = QComboBox()
        self.recipe_a.setMinimumWidth(250)
        self.recipe_b = QComboBox()
        self.recipe_b.setMinimumWidth(250)
        self.recipe_a.addItem("— Receta A —", None)
        self.recipe_b.addItem("— Receta B —", None)
        row1.addWidget(QLabel("Comparar:"))
        row1.addWidget(self.recipe_a)
        row1.addWidget(QLabel("vs"))
        row1.addWidget(self.recipe_b)
        self.compare_btn = QPushButton("Comparar")
        self.compare_btn.setStyleSheet(
            "background-color: #FF9800; color: white; font-weight: bold; padding: 6px;"
        )
        self.compare_btn.clicked.connect(self._run_comparison)
        row1.addWidget(self.compare_btn)
        row1.addStretch()
        layout.addLayout(row1)

        # Results tabs
        self.tabs = QTabWidget()

        # Tab: Composición
        comp_widget = QWidget()
        comp_layout = QVBoxLayout(comp_widget)
        self.comp_table = QTableWidget()
        self.comp_table.setColumnCount(5)
        self.comp_table.setHorizontalHeaderLabels([
            "Componente", "Receta A (%)", "Receta B (%)", "Diferencia", "Notas"
        ])
        self.comp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        comp_layout.addWidget(self.comp_table)
        self.tabs.addTab(comp_widget, "Composición")

        # Tab: Propiedades analíticas
        prop_widget = QWidget()
        prop_layout = QVBoxLayout(prop_widget)
        self.prop_table = QTableWidget()
        self.prop_table.setColumnCount(3)
        self.prop_table.setHorizontalHeaderLabels(["Propiedad", "Receta A", "Receta B"])
        self.prop_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        prop_layout.addWidget(self.prop_table)
        self.tabs.addTab(prop_widget, "Propiedades")

        # Tab: Resultados visuales
        self.result_a = AnalysisResultWidget()
        self.result_b = AnalysisResultWidget()
        vis_widget = QWidget()
        vis_layout = QHBoxLayout(vis_widget)
        vis_layout.addWidget(self.result_a)
        vis_layout.addWidget(self.result_b)
        self.tabs.addTab(vis_widget, "Análisis Completo")

        layout.addWidget(self.tabs)

    def set_recipes(self, recipes: List[LacquerRecipe]):
        """Actualiza la lista de recetas disponibles."""
        self._recipes = recipes
        self.recipe_a.clear()
        self.recipe_b.clear()
        self.recipe_a.addItem("— Receta A —", None)
        self.recipe_b.addItem("— Receta B —", None)
        for r in recipes:
            label = f"{r.name} ({r.id})"
            self.recipe_a.addItem(label, r)
            self.recipe_b.addItem(label, r)
        # Auto-select first two
        if len(recipes) >= 1:
            self.recipe_a.setCurrentIndex(1)
        if len(recipes) >= 2:
            self.recipe_b.setCurrentIndex(2)

    def _run_comparison(self):
        a = self.recipe_a.currentData()
        b = self.recipe_b.currentData()
        if not a or not b:
            return

        inputs = AnalysisInput()

        def extract_blends(recipe):
            solvent = {}
            resin = {}
            plast = {}
            add = {}
            for comp in recipe.components:
                ing = comp.ingredient
                c = comp.concentration_pct
                n = ing.name.lower()
                t = ing.type.value
                if t in ("active_solvent", "tail_solvent"):
                    solvent[ing.name] = c
                elif any(p in n for p in ["ftalato", "ricino", "alcanfor",
                                           "tripolifosfato", "estearato"]):
                    plast[ing.name] = c
                elif t == "base_resin":
                    resin[ing.name] = c
                else:
                    add[ing.name] = c
            return solvent, resin, plast, add

        s_a, r_a, p_a, ad_a = extract_blends(a)
        s_b, r_b, p_b, ad_b = extract_blends(b)
        res_a = analyze_lacquer(s_a, r_a, p_a, ad_a, inputs)
        res_b = analyze_lacquer(s_b, r_b, p_b, ad_b, inputs)

        self.result_a.display_result(res_a)
        self.result_b.display_result(res_b)

        # Composition table
        all_ingredients = {}
        for comp in a.components:
            name = comp.ingredient.name
            if name not in all_ingredients:
                all_ingredients[name] = {"type": comp.ingredient.type.value, "a": 0.0, "b": 0.0}
            all_ingredients[name]["a"] += comp.concentration_pct
        for comp in b.components:
            name = comp.ingredient.name
            if name not in all_ingredients:
                all_ingredients[name] = {"type": comp.ingredient.type.value, "a": 0.0, "b": 0.0}
            all_ingredients[name]["b"] += comp.concentration_pct

        self.comp_table.setRowCount(len(all_ingredients))
        for i, (name, data) in enumerate(sorted(all_ingredients.items())):
            self.comp_table.setItem(i, 0, QTableWidgetItem(f"[{data['type']}] {name}"))
            self.comp_table.setItem(i, 1, QTableWidgetItem(f"{data['a']:.1f}" if data['a'] else "—"))
            self.comp_table.setItem(i, 2, QTableWidgetItem(f"{data['b']:.1f}" if data['b'] else "—"))
            diff = data['a'] - data['b']
            diff_str = f"{diff:+.1f}" if abs(diff) > 0.1 else "="
            self.comp_table.setItem(i, 3, QTableWidgetItem(diff_str))

            # Notas sobre diferencias significativas
            notes = ""
            if abs(diff) > 5:
                notes = "Diferencia significativa"
            if data['a'] == 0:
                notes = "Solo en B"
            elif data['b'] == 0:
                notes = "Solo en A"
            self.comp_table.setItem(i, 4, QTableWidgetItem(notes))

        # Properties table
        props = [
            ("Viscosidad (mPa·s)", str(res_a.predicted_viscosity_mpas), str(res_b.predicted_viscosity_mpas)),
            ("Ford Cup #4 (s)", str(res_a.ford_cup_4_seconds), str(res_b.ford_cup_4_seconds)),
            ("Sólidos vol.%", str(res_a.solids_vol_pct), str(res_b.solids_vol_pct)),
            ("Secado (min)", str(res_a.drying_time_min), str(res_b.drying_time_min)),
            ("Tg final (°C)", str(res_a.final_tg_c), str(res_b.final_tg_c)),
            ("Tensión superficial (mN/m)", str(res_a.surface_tension_mNm), str(res_b.surface_tension_mNm)),
            ("Riesgo burbujas", f"{res_a.bubble_risk_category} ({res_a.bubble_risk_index:.2f})",
             f"{res_b.bubble_risk_category} ({res_b.bubble_risk_index:.2f})"),
            ("Riesgo blush", f"{res_a.blush_risk_category} ({res_a.blush_risk_index:.2f})",
             f"{res_b.blush_risk_category} ({res_b.blush_risk_index:.2f})"),
            ("Orange peel", f"{res_a.orange_peel_category} ({res_a.orange_peel_index:.2f})",
             f"{res_b.orange_peel_category} ({res_b.orange_peel_index:.2f})"),
            ("Mojado", res_a.wetting_category, res_b.wetting_category),
            ("Dureza", res_a.estimated_hardness, res_b.estimated_hardness),
            ("Flexibilidad", res_a.estimated_flexibility, res_b.estimated_flexibility),
            ("Hansen RED", f"{res_a.hansen_distance_to_nc}", f"{res_b.hansen_distance_to_nc}"),
            ("Score global", f"{res_a.overall_score}/10", f"{res_b.overall_score}/10"),
        ]
        self.prop_table.setRowCount(len(props))
        for i, (name, va, vb) in enumerate(props):
            self.prop_table.setItem(i, 0, QTableWidgetItem(name))
            self.prop_table.setItem(i, 1, QTableWidgetItem(va))
            self.prop_table.setItem(i, 2, QTableWidgetItem(vb))
