"""Prensado — parámetros y configuración del proceso de prensado de discos de laca."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QFormLayout, QDoubleSpinBox, QSpinBox,
    QTextEdit, QPushButton, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox,
)
from PySide6.QtCore import Qt
from ui.pipeline.base_stage import KnowledgeQAPanel


class PressingWorkspace(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("🔄 Prensado — Parámetros del Proceso")
        header.setStyleSheet("font-weight: bold; font-size: 16px; padding: 4px;")
        layout.addWidget(header)

        top_row = QHBoxLayout()

        params_group = QGroupBox("Parámetros de Prensado")
        params_form = QFormLayout()

        self.press_temp = QDoubleSpinBox()
        self.press_temp.setRange(80, 250)
        self.press_temp.setSuffix(" °C")
        self.press_temp.setValue(150)
        self.press_temp.setToolTip("Temperatura de prensado en °C")
        params_form.addRow("Temperatura de prensa:", self.press_temp)

        self.press_pressure = QDoubleSpinBox()
        self.press_pressure.setRange(10, 500)
        self.press_pressure.setSuffix(" bar")
        self.press_pressure.setValue(120)
        self.press_pressure.setToolTip("Presión de prensado en bar")
        params_form.addRow("Presión de prensa:", self.press_pressure)

        self.press_time = QDoubleSpinBox()
        self.press_time.setRange(5, 300)
        self.press_time.setSuffix(" s")
        self.press_time.setValue(30)
        self.press_time.setToolTip("Tiempo de prensado en segundos")
        params_form.addRow("Tiempo de prensado:", self.press_time)

        self.cool_time = QDoubleSpinBox()
        self.cool_time.setRange(5, 300)
        self.cool_time.setSuffix(" s")
        self.cool_time.setValue(20)
        self.cool_time.setToolTip("Tiempo de enfriamiento después del prensado en segundos")
        params_form.addRow("Tiempo de enfriamiento:", self.cool_time)

        self.mold_type = QComboBox()
        self.mold_type.addItems(["Estándar 12\"", "Estándar 7\"", "Custom"])
        self.mold_type.setToolTip("Tipo de molde utilizado en el prensado")
        params_form.addRow("Tipo de molde:", self.mold_type)

        self.release_agent = QComboBox()
        self.release_agent.addItems(["Ninguno", "Cera de silicona", "PTFE spray", "Agente desmoldante líquido"])
        self.release_agent.setToolTip("Agente desmoldante utilizado")
        params_form.addRow("Agente desmoldante:", self.release_agent)

        params_group.setLayout(params_form)
        top_row.addWidget(params_group)

        spec_group = QGroupBox("Especificaciones del Disco")
        spec_form = QFormLayout()

        self.disc_size = QComboBox()
        self.disc_size.addItems(["12\" (30cm)", "7\" (17.5cm)", "10\" (25cm)"])
        self.disc_size.setToolTip("Tamaño del disco (pulgadas)")
        spec_form.addRow("Tamaño:", self.disc_size)

        self.disc_thickness = QDoubleSpinBox()
        self.disc_thickness.setRange(0.5, 5.0)
        self.disc_thickness.setSuffix(" mm")
        self.disc_thickness.setDecimals(2)
        self.disc_thickness.setValue(1.8)
        self.disc_thickness.setToolTip("Grosor del disco en mm")
        spec_form.addRow("Grosor:", self.disc_thickness)

        self.disc_weight = QDoubleSpinBox()
        self.disc_weight.setRange(80, 250)
        self.disc_weight.setSuffix(" g")
        self.disc_weight.setValue(140)
        self.disc_weight.setToolTip("Peso del disco en gramos")
        spec_form.addRow("Peso del disco:", self.disc_weight)

        self.stamper_life = QSpinBox()
        self.stamper_life.setRange(1, 10000)
        self.stamper_life.setSuffix(" prensadas")
        self.stamper_life.setValue(1000)
        self.stamper_life.setToolTip("Vida útil del estampador en número de prensadas")
        spec_form.addRow("Vida útil del estampador:", self.stamper_life)

        spec_group.setLayout(spec_form)
        top_row.addWidget(spec_group)

        layout.addLayout(top_row)

        mid_row = QHBoxLayout()

        log_group = QGroupBox("Registro de Producción")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Registro de prensadas anteriores...")
        self.log_text.setToolTip("Registro histórico de producciones de prensado con fechas y parámetros")
        log_layout.addWidget(self.log_text)

        log_btn_row = QHBoxLayout()
        record_btn = QPushButton("Registrar Prensada")
        record_btn.clicked.connect(self._record_press)
        record_btn.setToolTip("Registra la prensada actual en el historial de producción")
        clear_log = QPushButton("Limpiar Registro")
        clear_log.clicked.connect(self.log_text.clear)
        clear_log.setToolTip("Limpia todo el registro de producción")
        log_btn_row.addWidget(record_btn)
        log_btn_row.addWidget(clear_log)
        log_btn_row.addStretch()
        log_layout.addLayout(log_btn_row)

        log_group.setLayout(log_layout)
        mid_row.addWidget(log_group)

        ref_group = QGroupBox("Referencias — Defectos de Prensado")
        ref_layout = QVBoxLayout()
        self.ref_text = QTextEdit()
        self.ref_text.setReadOnly(True)
        self.ref_text.setHtml("""
        <h4>Defectos comunes de prensado</h4>
        <ul>
        <li><b>No llena</b> — temperatura o presión insuficientes</li>
        <li><b>Rebaba excesiva</b> — exceso de material o presión demasiado alta</li>
        <li><b>Disco pegado al molde</b> — agente desmoldante insuficiente</li>
        <li><b>Deformación (warp)</b> — enfriamiento desigual o humedad en el material</li>
        <li><b>Marca de estampador</b> — estampador desgastado o dañado</li>
        <li><b>Burbujas atrapadas</b> — desgasificado insuficiente o material húmedo</li>
        </ul>
        """)
        self.ref_text.setToolTip("Guía de referencia de defectos de prensado: causas y soluciones")
        ref_layout.addWidget(self.ref_text)
        ref_group.setLayout(ref_layout)
        mid_row.addWidget(ref_group)

        layout.addLayout(mid_row)

        self.qa = KnowledgeQAPanel("pressing")
        layout.addWidget(self.qa)

    def _record_press(self):
        import datetime
        entry = (
            f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] "
            f"Prensada: {self.disc_size.currentText()}, "
            f"{self.press_temp.value():.0f}°C, {self.press_pressure.value():.0f}bar, "
            f"{self.press_time.value():.0f}s / enf.{self.cool_time.value():.0f}s\n"
        )
        self.log_text.append(entry)

    def set_llm(self, llm):
        self.qa.set_llm(llm)

    def set_knowledge_base(self, kb):
        self.qa.set_knowledge_base(kb)

    def set_settings(self, settings):
        self.qa.set_settings(settings)

    def abort_llm(self):
        self.qa.abort_llm()
