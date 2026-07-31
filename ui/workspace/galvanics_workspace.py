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
from core.translations import T
from ui.dialogs.process_manual_dialog import ProcessManualDialog


class GalvanicsWorkspace(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        header_row = QHBoxLayout()
        self.header = QLabel(T("⚡ Galvánica — Metalizado y Baños Electrolíticos"))
        self.header.setStyleSheet("font-weight: bold; font-size: 16px; padding: 4px;")
        header_row.addWidget(self.header)
        header_row.addStretch()
        self.manual_btn = QPushButton(T("📖 Manual — Galvánica"))
        self.manual_btn.setToolTip("Guía completa de galvanoplastia: historia, baños y procesos")
        self.manual_btn.clicked.connect(lambda: self._open_manual("electroplating"))
        self.manual_btn.setMaximumHeight(28)
        header_row.addWidget(self.manual_btn)
        layout.addLayout(header_row)

        self.tabs = QTabWidget()

        # Tab 1: Parámetros de baño
        bath_tab = QWidget()
        bath_layout = QHBoxLayout(bath_tab)

        self.silver_group = QGroupBox(T("Baño de Plata (Plateado)"))
        self.silver_form = QFormLayout()
        self.silver_temp = QDoubleSpinBox()
        self.silver_temp.setRange(15, 40)
        self.silver_temp.setSuffix(T(" °C"))
        self.silver_temp.setValue(25)
        self.silver_temp.setToolTip(T("Temperatura del baño de plata en °C. Rango típico: 40-60°C"))
        self.silver_form.addRow(T("Temperatura:"), self.silver_temp)

        self.silver_ph = QDoubleSpinBox()
        self.silver_ph.setRange(0, 14)
        self.silver_ph.setDecimals(1)
        self.silver_ph.setValue(9.5)
        self.silver_ph.setToolTip(T("pH del baño de plata. Rango típico: 8.5-9.5"))
        self.silver_form.addRow(T("pH:"), self.silver_ph)

        self.silver_density = QDoubleSpinBox()
        self.silver_density.setRange(0.5, 10)
        self.silver_density.setSuffix(T(" A/dm²"))
        self.silver_density.setValue(3.0)
        self.silver_density.setToolTip(T("Densidad de corriente del baño de plata en A/dm²"))
        self.silver_form.addRow(T("Densidad de corriente:"), self.silver_density)

        self.silver_time = QSpinBox()
        self.silver_time.setRange(10, 600)
        self.silver_time.setSuffix(T(" s"))
        self.silver_time.setValue(120)
        self.silver_time.setToolTip(T("Tiempo de inmersión en el baño de plata en minutos"))
        self.silver_form.addRow(T("Tiempo:"), self.silver_time)

        self.silver_group.setLayout(self.silver_form)
        bath_layout.addWidget(self.silver_group)

        self.nickel_group = QGroupBox(T("Baño de Sulfamato de Níquel"))
        self.nickel_form = QFormLayout()
        self.nickel_temp = QDoubleSpinBox()
        self.nickel_temp.setRange(30, 70)
        self.nickel_temp.setSuffix(T(" °C"))
        self.nickel_temp.setValue(50)
        self.nickel_temp.setToolTip(T("Temperatura del baño de níquel sulfamato en °C. Rango típico: 40-60°C"))
        self.nickel_form.addRow(T("Temperatura:"), self.nickel_temp)

        self.nickel_ph = QDoubleSpinBox()
        self.nickel_ph.setRange(0, 14)
        self.nickel_ph.setDecimals(1)
        self.nickel_ph.setValue(4.0)
        self.nickel_ph.setToolTip(T("pH del baño de níquel. Rango típico: 3.5-4.5"))
        self.nickel_form.addRow(T("pH:"), self.nickel_ph)

        self.nickel_density = QDoubleSpinBox()
        self.nickel_density.setRange(0.5, 20)
        self.nickel_density.setSuffix(T(" A/dm²"))
        self.nickel_density.setValue(5.0)
        self.nickel_density.setToolTip(T("Densidad de corriente del baño de níquel en A/dm²"))
        self.nickel_form.addRow(T("Densidad de corriente:"), self.nickel_density)

        self.nickel_thickness = QDoubleSpinBox()
        self.nickel_thickness.setRange(10, 1000)
        self.nickel_thickness.setSuffix(T(" μm"))
        self.nickel_thickness.setValue(300)
        self.nickel_thickness.setToolTip(T(" Espesor de la capa de níquel objetivo en µm"))
        self.nickel_form.addRow(T("Grosor objetivo:"), self.nickel_thickness)

        self.nickel_group.setLayout(self.nickel_form)
        bath_layout.addWidget(self.nickel_group)

        self.prep_group = QGroupBox(T("Preparación de Superficie"))
        self.prep_form = QFormLayout()
        self.prep_method = QComboBox()
        self.prep_method.addItems([
            T("Desengrase alcalino"),
            T("Desengrase ácido"),
            T("Limpieza por plasma"),
            T("Activación ácida (H₂SO₄ 10%)"),
        ])
        self.prep_method.setToolTip(T("Método de preparación superficial: desengrase, decapado o activación"))
        self.prep_form.addRow(T("Método:"), self.prep_method)

        self.prep_time = QSpinBox()
        self.prep_time.setRange(10, 600)
        self.prep_time.setSuffix(T(" s"))
        self.prep_time.setValue(60)
        self.prep_time.setToolTip(T("Tiempo de preparación superficial en minutos"))
        self.prep_form.addRow(T("Tiempo:"), self.prep_time)

        self.rinse_cycles = QSpinBox()
        self.rinse_cycles.setRange(1, 5)
        self.rinse_cycles.setValue(3)
        self.rinse_cycles.setToolTip(T("Número de ciclos de enjuague después del baño"))
        self.prep_form.addRow(T("Ciclos de enjuague:"), self.rinse_cycles)

        self.prep_group.setLayout(self.prep_form)
        bath_layout.addWidget(self.prep_group)

        self.tabs.addTab(bath_tab, T("Parámetros de Baño"))

        # Tab 2: Matriz de compatibilidad
        compat_tab = PlatingOverviewWidget()
        self.tabs.addTab(compat_tab, T("Compatibilidad y Prevención"))

        # Tab 3: Q&A
        self.qa_galvanics = KnowledgeQAPanel("galvanics")
        self.tabs.addTab(self.qa_galvanics, T("P&R — Galvánica"))

        self.tabs.setToolTip(T("Pestañas de galvanoplastia:\n• Parámetros de Baño — configuración de baños\n• Compatibilidad — matriz de compatibilidad\n• P&R — consultas sobre galvanoplastia"))
        layout.addWidget(self.tabs)

    def retranslate(self):
        self.header.setText(T("⚡ Galvánica — Metalizado y Baños Electrolíticos"))
        self.manual_btn.setText(T("📖 Manual — Galvánica"))
        self.manual_btn.setToolTip("Guía completa de galvanoplastia: historia, baños y procesos")
        self.silver_group.setTitle(T("Baño de Plata (Plateado)"))
        self.nickel_group.setTitle(T("Baño de Sulfamato de Níquel"))
        self.prep_group.setTitle(T("Preparación de Superficie"))
        for w, key in (
            (self.silver_temp, "Temperatura:"), (self.silver_ph, "pH:"),
            (self.silver_density, "Densidad de corriente:"), (self.silver_time, "Tiempo:"),
            (self.nickel_temp, "Temperatura:"), (self.nickel_ph, "pH:"),
            (self.nickel_density, "Densidad de corriente:"), (self.nickel_thickness, "Grosor objetivo:"),
            (self.prep_method, "Método:"), (self.prep_time, "Tiempo:"),
            (self.rinse_cycles, "Ciclos de enjuague:"),
        ):
            lbl = self._label_for(w)
            if lbl:
                lbl.setText(T(key))
        for w, suffix in (
            (self.silver_temp, " °C"), (self.silver_density, " A/dm²"), (self.silver_time, " s"),
            (self.nickel_temp, " °C"), (self.nickel_density, " A/dm²"), (self.nickel_thickness, " μm"),
            (self.prep_time, " s"),
        ):
            w.setSuffix(T(suffix))
        self.prep_method.setItemText(0, T("Desengrase alcalino"))
        self.prep_method.setItemText(1, T("Desengrase ácido"))
        self.prep_method.setItemText(2, T("Limpieza por plasma"))
        self.prep_method.setItemText(3, T("Activación ácida (H₂SO₄ 10%)"))
        self.tabs.setTabText(0, T("Parámetros de Baño"))
        self.tabs.setTabText(1, T("Compatibilidad y Prevención"))
        self.tabs.setTabText(2, T("P&R — Galvánica"))

    @staticmethod
    def _label_for(widget):
        if widget is None:
            return None
        parent = widget.parentWidget()
        if parent is None:
            return None
        layout = parent.layout()
        if layout and hasattr(layout, 'labelForField'):
            try:
                return layout.labelForField(widget)
            except Exception:
                return None
        return None

    def set_llm(self, llm):
        self.qa_galvanics.set_llm(llm)

    def set_knowledge_base(self, kb):
        self.qa_galvanics.set_knowledge_base(kb)

    def set_settings(self, settings):
        self.qa_galvanics.set_settings(settings)

    def abort_llm(self):
        self.qa_galvanics.abort_llm()

    def _open_manual(self, process_key):
        dlg = ProcessManualDialog(process_key, self)
        dlg.exec()
