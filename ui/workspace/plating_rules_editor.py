"""Editor de reglas de recubrimiento — editar parámetros de solventes, límites de aditivos, parámetros de proceso."""

from pathlib import Path
from typing import Dict, List
import yaml

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QTextEdit, QListWidget,
    QListWidgetItem, QPushButton, QGroupBox,
    QFormLayout, QSpinBox, QDoubleSpinBox, QCheckBox,
    QMessageBox, QWidget, QSplitter,
)
from PySide6.QtCore import Qt


RULES_PATH = str(Path(__file__).parent.parent / "config" / "plating_compatibility.yaml")


class ListEditor(QWidget):
    """Lista editable de cadenas con añadir/quitar/editar."""

    def __init__(self, items: List[str] = None, placeholder: str = ""):
        super().__init__()
        self.placeholder = placeholder
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Añadir")
        self.add_btn.clicked.connect(self._add)
        self.remove_btn = QPushButton("Quitar")
        self.remove_btn.clicked.connect(self._remove)
        self.edit_btn = QPushButton("Editar")
        self.edit_btn.clicked.connect(self._edit)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.remove_btn)
        layout.addLayout(btn_row)

        if items:
            for item in items:
                self.list_widget.addItem(QListWidgetItem(item))

    def _add(self):
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "Añadir Elemento", self.placeholder or "Ingrese valor:")
        if ok and text.strip():
            self.list_widget.addItem(QListWidgetItem(text.strip()))

    def _remove(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))

    def _edit(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(
            self, "Editar Elemento", "Valor:", text=item.text()
        )
        if ok and text.strip():
            item.setText(text.strip())

    def get_items(self) -> List[str]:
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]


class PlatingRulesEditorDialog(QDialog):
    """Editar reglas de formulación de recubrimientos y guardar en plating_compatibility.yaml."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editor de Reglas de Formulación de Recubrimientos")
        self.setMinimumSize(700, 500)
        self._data = self._load()
        self._init_ui()

    def _load(self) -> dict:
        path = Path(RULES_PATH)
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def _save_data(self):
        path = Path(RULES_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        silver_tab = self._build_plating_tab("silvering")
        tabs.addTab(silver_tab, "Plateado")

        nickel_tab = self._build_plating_tab("nickel_sulfamate")
        tabs.addTab(nickel_tab, "Sulfamato de Níquel")

        seq_tab = self._build_sequences_tab()
        tabs.addTab(seq_tab, "Secuencias de Proceso")

        layout.addWidget(tabs, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Guardar Reglas")
        save_btn.clicked.connect(self._save_and_close)
        save_btn.setStyleSheet("background: #4CAF50; color: white; font-weight: bold;")
        save_btn.setMinimumWidth(120)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumWidth(100)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _build_plating_tab(self, key: str) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        config = self._data.get(key, {})

        info_form = QFormLayout()
        self._name_inputs = getattr(self, '_name_inputs', {})
        self._name_inputs[key] = QLineEdit(config.get("name", ""))
        info_form.addRow("Nombre:", self._name_inputs[key])

        desc_input = QTextEdit(config.get("description", ""))
        desc_input.setMaximumHeight(60)
        self._desc_inputs = getattr(self, '_desc_inputs', {})
        self._desc_inputs[key] = desc_input
        info_form.addRow("Descripción:", desc_input)
        layout.addLayout(info_form)

        chem_group = QGroupBox("Químicos Prohibidos")
        chem_layout = QVBoxLayout(chem_group)
        forbidden = config.get("forbidden_chemicals", [])
        le = ListEditor(forbidden, "ej. MEK (Metil Etil Cetona)")
        self._forbidden_lists = getattr(self, '_forbidden_lists', {})
        self._forbidden_lists[key] = le
        chem_layout.addWidget(le)
        layout.addWidget(chem_group)

        bath_group = QGroupBox("Composición del Baño")
        bath_layout = QVBoxLayout(bath_group)
        bath = config.get("bath_composition", [])
        le2 = ListEditor(bath, "ej. Cianuro de plata / Sulfamato de plata")
        self._bath_lists = getattr(self, '_bath_lists', {})
        self._bath_lists[key] = le2
        bath_layout.addWidget(le2)
        layout.addWidget(bath_group)

        prep_group = QGroupBox("Preparación de Superficie Requerida")
        prep_layout = QVBoxLayout(prep_group)
        prep = config.get("required_surface_prep", [])
        le3 = ListEditor(prep)
        self._prep_lists = getattr(self, '_prep_lists', {})
        self._prep_lists[key] = le3
        prep_layout.addWidget(le3)
        layout.addWidget(prep_group)

        req_group = QGroupBox("Requisitos de la Laca")
        req_form = QFormLayout(req_group)
        lacq = config.get("lacquer_requirements", {})
        self._lacq_inputs = getattr(self, '_lacq_inputs', {})

        min_ad = QDoubleSpinBox()
        min_ad.setRange(0, 50)
        min_ad.setSuffix(" MPa")
        min_ad.setValue(float(lacq.get("min_adhesion_mpa", 0)))
        req_form.addRow("Adhesión mínima:", min_ad)

        max_solv = QDoubleSpinBox()
        max_solv.setRange(0, 10)
        max_solv.setSuffix(" %")
        max_solv.setDecimals(2)
        max_solv.setValue(float(lacq.get("max_solvent_retention_pct", 0)))
        req_form.addRow("Retención máxima de solvente:", max_solv)

        cure_temp = QSpinBox()
        cure_temp.setRange(0, 300)
        cure_temp.setSuffix(" °C")
        cure_temp.setValue(int(lacq.get("cure_temp_max_c", 0)))
        req_form.addRow("Temp. máxima de curado:", cure_temp)

        self._lacq_inputs[key] = {
            "min_adhesion_mpa": min_ad,
            "max_solvent_retention_pct": max_solv,
            "cure_temp_max_c": cure_temp,
        }
        layout.addWidget(req_group)

        return tab

    def _build_sequences_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._seq_widgets = {}
        rules = self._data.get("process_sequence_rules", [])

        for i, rule in enumerate(rules):
            seq = rule.get("sequence", [])
            seq_key = " -> ".join(seq)
            group = QGroupBox(f"Secuencia: {seq_key}")
            glayout = QVBoxLayout(group)

            allowed_check = QCheckBox("Permitido")
            allowed_check.setChecked(rule.get("allowed", True))
            glayout.addWidget(allowed_check)

            glayout.addWidget(QLabel("Condiciones:"))
            cond_editor = ListEditor(rule.get("conditions", []))
            glayout.addWidget(cond_editor)

            self._seq_widgets[seq_key] = {
                "check": allowed_check,
                "conditions": cond_editor,
            }
            layout.addWidget(group)

        layout.addStretch()
        return tab

    def _save_and_close(self):
        for key in ("silvering", "nickel_sulfamate"):
            if key not in self._data:
                self._data[key] = {}

            self._data[key]["name"] = self._name_inputs[key].text()
            self._data[key]["description"] = self._desc_inputs[key].toPlainText()
            self._data[key]["forbidden_chemicals"] = self._forbidden_lists[key].get_items()
            self._data[key]["bath_composition"] = self._bath_lists[key].get_items()
            self._data[key]["required_surface_prep"] = self._prep_lists[key].get_items()

            lacq = {}
            for field, widget in self._lacq_inputs[key].items():
                lacq[field] = widget.value()
            self._data[key]["lacquer_requirements"] = lacq

        rules = self._data.get("process_sequence_rules", [])
        for rule in rules:
            seq_key = " -> ".join(rule["sequence"])
            if seq_key in self._seq_widgets:
                w = self._seq_widgets[seq_key]
                rule["allowed"] = w["check"].isChecked()
                rule["conditions"] = w["conditions"].get_items()

        self._save_data()
        QMessageBox.information(self, "Guardado", "Reglas de recubrimiento guardadas en plating_compatibility.yaml")
        self.accept()
