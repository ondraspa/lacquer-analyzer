"""Galvánica — procesos de metalizado, baños de níquel y plata, compatibilidad."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QTabWidget, QPushButton, QFormLayout,
    QDoubleSpinBox, QSpinBox, QTextEdit, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ui.pipeline.plating_overview import PlatingOverviewWidget
from ui.pipeline.base_stage import KnowledgeQAPanel


class GalvanicsWorkspace(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("⚡ Galvánica — Metalizado y Baños Electrolíticos")
        header.setStyleSheet("font-weight: bold; font-size: 16px; padding: 4px;")
        layout.addWidget(header)

        tabs = QTabWidget()

        # Tab 1: Parámetros de baño
        bath_tab = QWidget()
        bath_layout = QHBoxLayout(bath_tab)

        silver_group = QGroupBox("Baño de Plata (Plateado)")
        silver_form = QFormLayout()
        self.silver_temp = QDoubleSpinBox()
        self.silver_temp.setRange(15, 40)
        self.silver_temp.setSuffix(" °C")
        self.silver_temp.setValue(25)
        self.silver_temp.setToolTip("Temperatura del baño de plata en °C. Rango típico: 40-60°C")
        silver_form.addRow("Temperatura:", self.silver_temp)

        self.silver_ph = QDoubleSpinBox()
        self.silver_ph.setRange(0, 14)
        self.silver_ph.setDecimals(1)
        self.silver_ph.setValue(9.5)
        self.silver_ph.setToolTip("pH del baño de plata. Rango típico: 8.5-9.5")
        silver_form.addRow("pH:", self.silver_ph)

        self.silver_density = QDoubleSpinBox()
        self.silver_density.setRange(0.5, 10)
        self.silver_density.setSuffix(" A/dm²")
        self.silver_density.setValue(3.0)
        self.silver_density.setToolTip("Densidad de corriente del baño de plata en A/dm²")
        silver_form.addRow("Densidad de corriente:", self.silver_density)

        self.silver_time = QSpinBox()
        self.silver_time.setRange(10, 600)
        self.silver_time.setSuffix(" s")
        self.silver_time.setValue(120)
        self.silver_time.setToolTip("Tiempo de inmersión en el baño de plata en minutos")
        silver_form.addRow("Tiempo:", self.silver_time)

        silver_group.setLayout(silver_form)
        bath_layout.addWidget(silver_group)

        nickel_group = QGroupBox("Baño de Sulfamato de Níquel")
        nickel_form = QFormLayout()
        self.nickel_temp = QDoubleSpinBox()
        self.nickel_temp.setRange(30, 70)
        self.nickel_temp.setSuffix(" °C")
        self.nickel_temp.setValue(50)
        self.nickel_temp.setToolTip("Temperatura del baño de níquel sulfamato en °C. Rango típico: 40-60°C")
        nickel_form.addRow("Temperatura:", self.nickel_temp)

        self.nickel_ph = QDoubleSpinBox()
        self.nickel_ph.setRange(0, 14)
        self.nickel_ph.setDecimals(1)
        self.nickel_ph.setValue(4.0)
        self.nickel_ph.setToolTip("pH del baño de níquel. Rango típico: 3.5-4.5")
        nickel_form.addRow("pH:", self.nickel_ph)

        self.nickel_density = QDoubleSpinBox()
        self.nickel_density.setRange(0.5, 20)
        self.nickel_density.setSuffix(" A/dm²")
        self.nickel_density.setValue(5.0)
        self.nickel_density.setToolTip("Densidad de corriente del baño de níquel en A/dm²")
        nickel_form.addRow("Densidad de corriente:", self.nickel_density)

        self.nickel_thickness = QDoubleSpinBox()
        self.nickel_thickness.setRange(10, 1000)
        self.nickel_thickness.setSuffix(" μm")
        self.nickel_thickness.setValue(300)
        self.nickel_thickness.setToolTip(" Espesor de la capa de níquel objetivo en µm")
        nickel_form.addRow("Grosor objetivo:", self.nickel_thickness)

        nickel_group.setLayout(nickel_form)
        bath_layout.addWidget(nickel_group)

        prep_group = QGroupBox("Preparación de Superficie")
        prep_form = QFormLayout()
        self.prep_method = QComboBox()
        self.prep_method.addItems([
            "Desengrase alcalino",
            "Desengrase ácido",
            "Limpieza por plasma",
            "Activación ácida (H₂SO₄ 10%)",
        ])
        self.prep_method.setToolTip("Método de preparación superficial: desengrase, decapado o activación")
        prep_form.addRow("Método:", self.prep_method)

        self.prep_time = QSpinBox()
        self.prep_time.setRange(10, 600)
        self.prep_time.setSuffix(" s")
        self.prep_time.setValue(60)
        self.prep_time.setToolTip("Tiempo de preparación superficial en minutos")
        prep_form.addRow("Tiempo:", self.prep_time)

        self.rinse_cycles = QSpinBox()
        self.rinse_cycles.setRange(1, 5)
        self.rinse_cycles.setValue(3)
        self.rinse_cycles.setToolTip("Número de ciclos de enjuague después del baño")
        prep_form.addRow("Ciclos de enjuague:", self.rinse_cycles)

        prep_group.setLayout(prep_form)
        bath_layout.addWidget(prep_group)

        tabs.addTab(bath_tab, "Parámetros de Baño")

        # Tab 2: Matriz de compatibilidad
        compat_tab = PlatingOverviewWidget()
        tabs.addTab(compat_tab, "Compatibilidad y Prevención")

        # Tab 3: Q&A
        self.qa_galvanics = KnowledgeQAPanel("galvanics")
        tabs.addTab(self.qa_galvanics, "P&R — Galvánica")

        tabs.setToolTip("Pestañas de galvanoplastia:\n• Parámetros de Baño — configuración de baños\n• Compatibilidad — matriz de compatibilidad\n• P&R — consultas sobre galvanoplastia")
        layout.addWidget(tabs)

    def set_llm(self, llm):
        self.qa_galvanics.set_llm(llm)

    def set_knowledge_base(self, kb):
        self.qa_galvanics.set_knowledge_base(kb)

    def set_settings(self, settings):
        self.qa_galvanics.set_settings(settings)

    def abort_llm(self):
        self.qa_galvanics.abort_llm()
