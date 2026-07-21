"""Panel de resultados de análisis que muestra propiedades de recubrimiento de laca y problemas de formulación"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QTextEdit, QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QSplitter, QFrame, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont

from core.models import AnalysisResult, CoatingAnalysis


class AnalysisPanelWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.risk_label = QLabel("Aún no se ha realizado ningún análisis")
        self.risk_label.setAlignment(Qt.AlignCenter)
        self.risk_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 10px; "
            "background: #e0e0e0; border-radius: 5px;"
        )
        layout.addWidget(self.risk_label)

        compat_layout = QHBoxLayout()

        self.solvent_group = QGroupBox("Análisis del Sistema de Solventes")
        solvent_layout = QVBoxLayout()
        self.solvent_text = QTextEdit()
        self.solvent_text.setReadOnly(True)
        solvent_layout.addWidget(self.solvent_text)
        self.solvent_group.setLayout(solvent_layout)
        compat_layout.addWidget(self.solvent_group)

        self.coating_group = QGroupBox("Propiedades del Recubrimiento")
        coating_layout = QVBoxLayout()
        self.coating_text = QTextEdit()
        self.coating_text.setReadOnly(True)
        coating_layout.addWidget(self.coating_text)
        self.coating_group.setLayout(coating_layout)
        compat_layout.addWidget(self.coating_group)

        layout.addLayout(compat_layout)

        self.formulation_group = QGroupBox("Problemas y Sugerencias de Formulación")
        form_layout = QVBoxLayout()
        self.formulation_text = QTextEdit()
        self.formulation_text.setReadOnly(True)
        form_layout.addWidget(self.formulation_text)
        self.formulation_group.setLayout(form_layout)
        layout.addWidget(self.formulation_group)

        self.stats_group = QGroupBox("Estadísticas de la Receta")
        stats_layout = QGridLayout()
        self.solids_label = QLabel("Sólidos: --")
        self.viscosity_label = QLabel("Viscosidad: --")
        self.components_label = QLabel("Componentes: --")
        self.coater_note = QLabel("Aplicador: Cortina Burkle")
        stats_layout.addWidget(self.solids_label, 0, 0)
        stats_layout.addWidget(self.viscosity_label, 0, 1)
        stats_layout.addWidget(self.components_label, 1, 0)
        stats_layout.addWidget(self.coater_note, 1, 1)
        self.stats_group.setLayout(stats_layout)
        layout.addWidget(self.stats_group)

    def show_results(self, result: AnalysisResult):
        risk_colors = {
            "LOW": "#4CAF50",
            "MEDIUM": "#FFC107",
            "HIGH": "#FF9800",
            "CRITICAL": "#F44336"
        }
        color = risk_colors.get(result.overall_risk, "#e0e0e0")
        self.risk_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; padding: 10px; "
            f"background: {color}; color: white; border-radius: 5px;"
        )
        self.risk_label.setText(
            f"Riesgo General: {result.overall_risk} "
            f"{'✅' if result.overall_risk in ['LOW', 'MEDIUM'] else '⚠️'}"
        )

        c = result.coating_analysis

        solvent_text = "<h3>Sistema de Solventes</h3>"
        balance_icons = {"fast": "⚡", "balanced": "✅", "slow": "🐢"}
        solvent_text += f"<p><b>Balance de Evaporación:</b> {balance_icons.get(c.solvent_balance, '')} {c.solvent_balance.title()}</p>"
        blush_colors = {"low": "green", "medium": "orange", "high": "red"}
        solvent_text += f"<p><b>Riesgo de Empañamiento:</b> <span style='color:{blush_colors.get(c.blush_risk, 'black')};'>{c.blush_risk.title()}</span></p>"
        solvency_colors = {"good": "green", "fair": "orange", "poor": "red"}
        solvent_text += f"<p><b>Calidad de Solvencia:</b> <span style='color:{solvency_colors.get(c.solvency_quality, 'black')};'>{c.solvency_quality.title()}</span></p>"

        if c.recommendations:
            solvent_text += "<p><b>Recomendaciones:</b></p><ul>"
            for r in c.recommendations:
                solvent_text += f"<li style='color:#1565C0;'>{r}</li>"
            solvent_text += "</ul>"

        if c.issues:
            solvent_text += "<p><b>Problemas:</b></p><ul>"
            for issue in c.issues:
                solvent_text += f"<li style='color:red;'>{issue}</li>"
            solvent_text += "</ul>"

        self.solvent_text.setHtml(solvent_text)

        coating_text = "<h3>Propiedades del Recubrimiento</h3>"
        coating_text += f"<p><b>Sólidos Estimados:</b> {c.estimated_solids_pct:.1f}%</p>"
        coating_text += f"<p><b>Viscosidad Estimada:</b> {c.estimated_viscosity_mpas:.0f} mPa·s</p>"
        leveling_icons = {"excellent": "🌟", "good": "✅", "fair": "⚠️", "poor": "❌"}
        coating_text += f"<p><b>Calidad de Nivelación:</b> {leveling_icons.get(c.leveling_quality, '')} {c.leveling_quality.title()}</p>"

        self.coating_text.setHtml(coating_text)

        formulation_text = "<h3>Análisis de Formulación</h3>"
        if result.formulation_issues:
            formulation_text += "<p><b>Problemas Encontrados:</b></p><ul>"
            for issue in result.formulation_issues:
                formulation_text += f"<li style='color:red;'>{issue}</li>"
            formulation_text += "</ul>"
        else:
            formulation_text += "<p style='color:green;'>No se encontraron problemas de formulación</p>"

        if result.suggested_modifications:
            formulation_text += "<p><b>Modificaciones Sugeridas:</b></p><ul>"
            for s in result.suggested_modifications:
                formulation_text += f"<li style='color:#1565C0;'>{s}</li>"
            formulation_text += "</ul>"

        self.formulation_text.setHtml(formulation_text)

        recipe = result.recipe
        self.solids_label.setText(f"Sólidos Estimados: {recipe.total_solids():.1f}%")
        self.viscosity_label.setText(f"Visc. Estimada: {recipe.estimated_viscosity():.0f} mPa·s")
        self.components_label.setText(f"Componentes: {len(recipe.components)}")

    def clear_results(self):
        self.risk_label.setText("Aún no se ha realizado ningún análisis")
        self.risk_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px; background: #e0e0e0; border-radius: 5px;")
        self.solvent_text.clear()
        self.coating_text.clear()
        self.formulation_text.clear()
        self.solids_label.setText("Sólidos: --")
        self.viscosity_label.setText("Viscosidad: --")
        self.components_label.setText("Componentes: --")
