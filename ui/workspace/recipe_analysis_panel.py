"""Panel de análisis del comportamiento de la laca final con campos de entrada ambientales."""

from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QDoubleSpinBox, QComboBox, QLabel, QPushButton, QTextEdit,
    QCheckBox, QGridLayout, QProgressBar, QTabWidget, QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from core.translations import T
from analysis.lacquer_physics import (
    analyze_lacquer, AnalysisInput, AnalysisResult,
)

from src.models import LacquerRecipe, RecipeComponent, IngredientType


class AnalysisInputPanel(QWidget):
    """Panel de entrada para condiciones de análisis."""

    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)

        self.temp_input = QDoubleSpinBox()
        self.temp_input.setRange(10, 50)
        self.temp_input.setValue(23)
        self.temp_input.setSuffix(" °C")
        self.temp_input.setDecimals(1)
        self.temp_input.setToolTip(T("Temperatura ambiente en °C. Afecta la velocidad de evaporación y la viscosidad"))
        layout.addRow(T("Temperatura ambiente:"), self.temp_input)

        self.humidity_input = QDoubleSpinBox()
        self.humidity_input.setRange(10, 100)
        self.humidity_input.setValue(50)
        self.humidity_input.setSuffix(" %")
        self.humidity_input.setToolTip(T("Humedad relativa en %. Humedades altas pueden causar bloom o problemas de secado"))
        layout.addRow(T("Humedad relativa:"), self.humidity_input)

        self.thickness_input = QDoubleSpinBox()
        self.thickness_input.setRange(10, 500)
        self.thickness_input.setValue(100)
        self.thickness_input.setSuffix(" µm")
        self.thickness_input.setDecimals(0)
        self.thickness_input.setToolTip(T("Espesor de la capa de laca en µm. Influye en el tiempo de secado"))
        layout.addRow(T("Espesor capa laca:"), self.thickness_input)

        self.polish_input = QDoubleSpinBox()
        self.polish_input.setRange(0.1, 20)
        self.polish_input.setValue(1.0)
        self.polish_input.setSuffix(" µm")
        self.polish_input.setDecimals(1)
        self.polish_input.setToolTip(T("Granulado del pulido en µm. Afecta la rugosidad superficial"))
        layout.addRow(T("Grano pulido disco:"), self.polish_input)

        self.air_velocity = QDoubleSpinBox()
        self.air_velocity.setRange(0, 5)
        self.air_velocity.setValue(0.5)
        self.air_velocity.setSuffix(" m/s")
        self.air_velocity.setSingleStep(0.1)
        self.air_velocity.setToolTip(T("Velocidad del aire en m/s. Controla la tasa de evaporación"))
        layout.addRow(T("Flujo de aire:"), self.air_velocity)

        self.application = QComboBox()
        self.application.addItems(["curtain_coater", "spin_coater"])
        self.application.setToolTip(T("Método de aplicación: cortina (curtain_coater) o spin (spin_coater)"))
        layout.addRow(T("Aplicación:"), self.application)

        self.positive_pressure = QCheckBox(T("Cámara de presión positiva"))
        self.positive_pressure.setToolTip(T("Activa cámara de presión positiva para reducir defectos por polvo"))
        layout.addRow("", self.positive_pressure)


class AnalysisResultWidget(QWidget):
    """Muestra los resultados del análisis en formato estructurado."""

    translate_requested = Signal(str, str)  # (text, target_lang)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        # Tab 1: Viscosidad y flujo
        visc_widget = QWidget()
        visc_grid = QGridLayout(visc_widget)
        self.visc_label = QLabel("—")
        self.visc_cat = QLabel("")
        self.ford_label = QLabel("—")
        self.solids_label = QLabel("—")
        self.tg_label = QLabel("—")
        self.hardness_label = QLabel("—")
        self.flex_label = QLabel("—")
        visc_grid.addWidget(QLabel(T("Viscosidad predicha:")), 0, 0)
        visc_grid.addWidget(self.visc_label, 0, 1)
        visc_grid.addWidget(QLabel(T("Categoría:")), 1, 0)
        visc_grid.addWidget(self.visc_cat, 1, 1)
        visc_grid.addWidget(QLabel(T("Ford Cup #4:")), 2, 0)
        visc_grid.addWidget(self.ford_label, 2, 1)
        visc_grid.addWidget(QLabel(T("Sólidos vol.:")), 3, 0)
        visc_grid.addWidget(self.solids_label, 3, 1)
        visc_grid.addWidget(QLabel(T("Tg final:")), 4, 0)
        visc_grid.addWidget(self.tg_label, 4, 1)
        visc_grid.addWidget(QLabel(T("Dureza:")), 5, 0)
        visc_grid.addWidget(self.hardness_label, 5, 1)
        visc_grid.addWidget(QLabel(T("Flexibilidad:")), 6, 0)
        visc_grid.addWidget(self.flex_label, 6, 1)
        tabs.addTab(visc_widget, T("Viscosidad & Película"))

        # Tab 2: Evaporación
        evap_widget = QWidget()
        evap_layout = QVBoxLayout(evap_widget)
        self.dry_label = QLabel("—")
        evap_layout.addWidget(QLabel(T("Tiempo de secado estimado:")))
        evap_layout.addWidget(self.dry_label)
        self.evap_profile = QTextEdit()
        self.evap_profile.setReadOnly(True)
        self.evap_profile.setMaximumHeight(150)
        evap_layout.addWidget(QLabel(T("Perfil de evaporación por solvente:")))
        evap_layout.addWidget(self.evap_profile)
        tabs.addTab(evap_widget, T("Evaporación"))

        # Tab 3: Defectos
        defect_widget = QWidget()
        defect_layout = QVBoxLayout(defect_widget)

        # Bubble
        bubble_group = QGroupBox(T("Atrapamiento de Burbujas"))
        bubble_f = QFormLayout(bubble_group)
        self.bubble_bar = QProgressBar()
        self.bubble_bar.setRange(0, 100)
        self.bubble_bar.setToolTip(T("Riesgo de burbujas por arrastre de aire"))
        self.bubble_cat = QLabel("—")
        self.bubble_max = QLabel("—")
        bubble_f.addRow(T("Riesgo:"), self.bubble_bar)
        bubble_f.addRow(T("Categoría:"), self.bubble_cat)
        bubble_f.addRow(T("Espesor máx sin burbujas:"), self.bubble_max)
        defect_layout.addWidget(bubble_group)

        # Blush
        blush_group = QGroupBox(T("Blush (Blanqueamiento)"))
        blush_f = QFormLayout(blush_group)
        self.blush_bar = QProgressBar()
        self.blush_bar.setRange(0, 100)
        self.blush_bar.setToolTip(T("Riesgo de bloom/blanqueo por condensación de humedad"))
        self.blush_cat = QLabel("—")
        blush_f.addRow(T("Riesgo:"), self.blush_bar)
        blush_f.addRow(T("Categoría:"), self.blush_cat)
        defect_layout.addWidget(blush_group)

        # Orange peel
        op_group = QGroupBox(T("Orange Peel (Piel de Naranja)"))
        op_f = QFormLayout(op_group)
        self.op_bar = QProgressBar()
        self.op_bar.setRange(0, 100)
        self.op_bar.setToolTip(T("Riesgo de sobre-curvatura (orange peel) por tensión superficial"))
        self.op_cat = QLabel("—")
        op_f.addRow(T("Riesgo:"), self.op_bar)
        op_f.addRow(T("Categoría:"), self.op_cat)
        defect_layout.addWidget(op_group)

        tabs.addTab(defect_widget, T("Defectos"))

        # Tab 4: Mojado y Hansen
        surf_widget = QWidget()
        surf_grid = QGridLayout(surf_widget)
        self.st_label = QLabel("—")
        self.wetting_cat = QLabel("—")
        self.hansen_label = QLabel("—")
        self.hansen_compat = QLabel("—")
        surf_grid.addWidget(QLabel(T("Tensión superficial:")), 0, 0)
        surf_grid.addWidget(self.st_label, 0, 1)
        surf_grid.addWidget(QLabel(T("Mojado:")), 1, 0)
        surf_grid.addWidget(self.wetting_cat, 1, 1)
        surf_grid.addWidget(QLabel(T("Hansen dist. (RED):")), 2, 0)
        surf_grid.addWidget(self.hansen_label, 2, 1)
        surf_grid.addWidget(QLabel(T("Compatible con NC:")), 3, 0)
        surf_grid.addWidget(self.hansen_compat, 3, 1)
        tabs.addTab(surf_widget, T("Mojado & Hansen"))

        layout.addWidget(tabs)

        # Score global
        score_widget = QWidget()
        score_layout = QHBoxLayout(score_widget)
        score_layout.addWidget(QLabel(T("Puntuación global:")))
        self.score_bar = QProgressBar()
        self.score_bar.setRange(0, 100)
        self.score_bar.setFormat("%v/10")
        self.score_bar.setToolTip(T("Puntuación global del análisis. Más alto = mejor formulación"))
        score_layout.addWidget(self.score_bar)
        layout.addWidget(score_widget)

        # Warnings
        warn_header = QHBoxLayout()
        warn_header.addWidget(QLabel(T("Advertencias:")))
        self.translate_btn = QPushButton(T("🌐 Traducir"))
        self.translate_btn.setMaximumWidth(120)
        self.translate_btn.clicked.connect(self._on_translate)
        self.translate_btn.setToolTip(T("Traduce las advertencias al idioma seleccionado usando el LLM"))
        warn_header.addWidget(self.translate_btn)
        warn_header.addStretch()
        layout.addLayout(warn_header)
        self.warnings_text = QTextEdit()
        self.warnings_text.setReadOnly(True)
        self.warnings_text.setPlaceholderText(T("Advertencias y recomendaciones"))
        self.warnings_text.setMaximumHeight(100)
        self.warnings_text.setToolTip(T("Advertencias y problemas detectados en la formulación"))
        layout.addWidget(self.warnings_text)

    def _on_translate(self):
        text = self.warnings_text.toPlainText()
        if text.strip():
            self.translate_requested.emit(text, "en")

    def display_result(self, result: AnalysisResult):
        self.visc_label.setText(f"{result.predicted_viscosity_mpas} mPa·s")
        self.visc_cat.setText(result.viscosity_category)
        self.ford_label.setText(f"{result.ford_cup_4_seconds} s")
        self.solids_label.setText(f"{result.solids_vol_pct}%")
        self.tg_label.setText(f"{result.final_tg_c} °C" if result.final_tg_c else "—")
        self.hardness_label.setText(result.estimated_hardness)
        self.flex_label.setText(result.estimated_flexibility)

        self.dry_label.setText(f"{result.drying_time_min} min" if result.drying_time_min else "—")
        profile_lines = []
        for name, time in sorted(result.solvent_evaporation_profile.items(),
                                  key=lambda x: x[1], reverse=True):
            profile_lines.append(f"  {name}: {time} min")
        self.evap_profile.setPlainText("\n".join(profile_lines) if profile_lines else "—")

        self.bubble_bar.setValue(int(result.bubble_risk_index * 100))
        self.bubble_cat.setText(result.bubble_risk_category)
        self.bubble_max.setText(
            f"{result.max_bubble_free_thickness_um} µm" if result.max_bubble_free_thickness_um else "—"
        )

        self.blush_bar.setValue(int(result.blush_risk_index * 100))
        self.blush_cat.setText(result.blush_risk_category)

        self.op_bar.setValue(int(result.orange_peel_index * 100))
        self.op_cat.setText(result.orange_peel_category)

        self.st_label.setText(f"{result.surface_tension_mNm} mN/m")
        self.wetting_cat.setText(f"{result.wetting_category} (idx={result.wetting_index})")
        self.hansen_label.setText(str(result.hansen_distance_to_nc) if result.hansen_distance_to_nc else "—")
        self.hansen_compat.setText(T("Sí") if result.hansen_compatible else T("NO — REVISAR"))

        self.score_bar.setValue(int(result.overall_score * 10))

        if result.warnings:
            self.warnings_text.setPlainText("\n".join(f"⚠ {w}" for w in result.warnings))
        else:
            self.warnings_text.setPlainText(T("Sin advertencias — receta equilibrada"))


class RecipeAnalysisPanel(QWidget):
    """Panel completo de análisis de laca con inputs ambientales."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        self.input_panel = AnalysisInputPanel()
        scroll_layout.addWidget(self.input_panel)

        self.analyze_btn = QPushButton(T("Ejecutar Análisis Completo"))
        self.analyze_btn.setStyleSheet(
            "background-color: #2196F3; color: white; font-weight: bold; padding: 8px;"
        )
        self.analyze_btn.setToolTip(T("Ejecuta el análisis completo de la receta: viscosidad, evaporación, defectos, mojado y perfil Hansen"))
        scroll_layout.addWidget(self.analyze_btn)

        self.result_widget = AnalysisResultWidget()
        scroll_layout.addWidget(self.result_widget)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        self._result: Optional[AnalysisResult] = None

    def analyze_recipe(self, recipe: LacquerRecipe) -> Optional[AnalysisResult]:
        """Ejecuta análisis completo sobre una receta."""
        if not recipe or not recipe.components:
            return None

        inputs = AnalysisInput(
            temperature_c=self.input_panel.temp_input.value(),
            humidity_pct=self.input_panel.humidity_input.value(),
            layer_thickness_um=self.input_panel.thickness_input.value(),
            polish_grain_um=self.input_panel.polish_input.value(),
            application=self.input_panel.application.currentText(),
            air_velocity_ms=self.input_panel.air_velocity.value(),
            positive_pressure=self.input_panel.positive_pressure.isChecked(),
        )

        solvent_blend = {}
        resin_blend = {}
        plasticizer_blend = {}
        additive_blend = {}

        for comp in recipe.components:
            ing = comp.ingredient
            conc = comp.concentration_pct
            t = ing.type
            name = ing.name

            if t in (IngredientType.ACTIVE_SOLVENT, IngredientType.TAIL_SOLVENT):
                solvent_blend[name] = solvent_blend.get(name, 0) + conc
            elif t == IngredientType.PLASTICIZER:
                plasticizer_blend[name] = plasticizer_blend.get(name, 0) + conc
            elif t == IngredientType.BASE_RESIN:
                    resin_blend[name] = resin_blend.get(name, 0) + conc
            elif t in (IngredientType.LEVELING, IngredientType.DEFOAMER,
                       IngredientType.ADHESION, IngredientType.UV_STABILIZER,
                       IngredientType.WETTING):
                additive_blend[name] = additive_blend.get(name, 0) + conc
            else:
                additive_blend[name] = additive_blend.get(name, 0) + conc

        result = analyze_lacquer(solvent_blend, resin_blend, plasticizer_blend,
                                 additive_blend, inputs)
        self._result = result
        self.result_widget.display_result(result)
        return result

    def get_result(self) -> Optional[AnalysisResult]:
        return self._result
