"""Widget de vista general de compatibilidad de recubrimiento"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QTextEdit, QLabel, QGridLayout, QFrame, QTreeWidget,
    QTreeWidgetItem, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont

from core.models import AnalysisResult


class PlatingOverviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        seq_group = QGroupBox("Parámetros de Recubrimiento Recomendados")
        seq_layout = QVBoxLayout()
        self.seq_text = QTextEdit()
        self.seq_text.setReadOnly(True)
        self.seq_text.setHtml("""
        <h3>Rangos de Parámetros de Recubrimiento</h3>
        <table border='1' cellpadding='5'>
        <tr><th>Parámetro</th><th>Rango Típico</th><th>Notas</th></tr>
        <tr><td>Contenido de Sólidos</td><td>25–40%</td>
          <td>Menor para películas delgadas, mayor para opacidad</td></tr>
        <tr><td>Viscosidad</td><td>100–800 mPa·s</td>
          <td>Cortina Burkle: 150–400 mPa·s</td></tr>
        <tr><td>Tensión Superficial</td><td>28–38 dinas/cm</td>
          <td>Por debajo de 35 para buena humectación del sustrato</td></tr>
        <tr><td>Espesor de Película</td><td>50–150 μm húmedo</td>
          <td>Película seca 15–60 μm según sólidos</td></tr>
        <tr><td>Tasa de Evap. de Solvente</td><td>0.5–3.0 (BuOAc=1)</td>
          <td>Mezcla rápida/media/lenta para prevenir empañamiento</td></tr>
        </table>
        """)
        seq_layout.addWidget(self.seq_text)
        seq_group.setLayout(seq_layout)
        layout.addWidget(seq_group)

        cross_group = QGroupBox("Matriz de Compatibilidad de Solventes")
        cross_layout = QVBoxLayout()

        self.cross_table = QTableWidget()
        self.cross_table.setColumnCount(4)
        self.cross_table.setHorizontalHeaderLabels([
            "Componente", "Solvente Activo", "Solvente de Cola", "Aditivo"
        ])

        data = [
            ["Nitrocelulosa", "Acetato de etilo, MEK", "BuOAc, EGBE", "-"],
            ["Plastificante", "Acetato de etilo", "BuOAc", "-"],
            ["Pigmento", "MEK", "Tolueno, Xileno", "Dispersante"],
            ["Agente Nivelante", "-", "BuOAc", "Silicona/acrílico"],
        ]

        self.cross_table.setRowCount(4)
        for row in range(4):
            for col in range(4):
                item = QTableWidgetItem(data[row][col])
                if "Silicona" in data[row][col]:
                    item.setBackground(QColor(255, 193, 7))
                elif data[row][col] == "-":
                    item.setBackground(QColor(240, 240, 240))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.cross_table.setItem(row, col, item)

        self.cross_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        cross_layout.addWidget(self.cross_table)
        cross_group.setLayout(cross_layout)
        layout.addWidget(cross_group)

        mit_group = QGroupBox("Guías de Prevención de Defectos")
        mit_layout = QVBoxLayout()
        self.mit_text = QTextEdit()
        self.mit_text.setReadOnly(True)
        self.mit_text.setHtml("""
        <h3>Prevención de Defectos Comunes de Recubrimiento</h3>
        <h4>Piel de Naranja:</h4>
        <ul>
          <li>Evaporación lenta con solvente de cola (BuOAc, EGBE)</li>
          <li>Añadir agente nivelante (0.1–0.5%)</li>
          <li>Reducir viscosidad, aumentar espesor de película</li>
        </ul>
        <h4>Poros / Cráteres:</h4>
        <ul>
          <li>Eliminar contaminación por silicona</li>
          <li>Añadir antiespumante (0.1–0.3%)</li>
          <li>Reducir tensión superficial con agente humectante</li>
          <li>Verificar limpieza del sustrato</li>
        </ul>
        <h4>Veladura / Empañamiento:</h4>
        <ul>
          <li>Disminuir tasa de evaporación del solvente</li>
          <li>Controlar humedad (40–60% HR)</li>
          <li>Evitar fracciones altas de solvente rápido</li>
        </ul>
        """)
        mit_layout.addWidget(self.mit_text)
        mit_group.setLayout(mit_layout)
        layout.addWidget(mit_group)

    def show_results(self, result: AnalysisResult):
        c = result.coating_analysis
        self.seq_text.append(
            f"\n<h3>Receta Actual: {result.recipe.name}</h3>"
            f"<p>Balance de Solventes: <b>{c.solvent_balance.title()}</b></p>"
            f"<p>Riesgo de Empañamiento: <b>{c.blush_risk.title()}</b></p>"
            f"<p>Solvencia: <b>{c.solvency_quality.title()}</b></p>"
            f"<p>Riesgo General: <b>{result.overall_risk}</b></p>"
        )
