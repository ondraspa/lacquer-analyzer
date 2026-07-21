"""Editor de base de datos de defectos — añadir/editar/eliminar entradas de solución de problemas."""

from typing import Optional
from dataclasses import asdict

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QTextEdit, QListWidget,
    QListWidgetItem, QPushButton, QGroupBox,
    QFormLayout, QComboBox, QMessageBox,
    QWidget, QSplitter,
)
from PySide6.QtCore import Qt

from src.troubleshooting import (
    DEFECT_DATABASE, Defect, get_defects_by_stage,
)


STAGES = ["cutting", "silvering", "plating", "pressing", "qc"]
SEVERITIES = ["low", "medium", "high", "critical"]


class ListEditWidget(QWidget):
    """Widget de lista editable en línea para síntomas, causas, soluciones, referencias."""

    def __init__(self, items=None, placeholder=""):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.list_widget = QListWidget()
        self.list_widget.setMaximumHeight(100)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("+")
        self.add_btn.setMaximumWidth(30)
        self.add_btn.clicked.connect(self._add)
        self.remove_btn = QPushButton("-")
        self.remove_btn.setMaximumWidth(30)
        self.remove_btn.clicked.connect(self._remove)
        self.edit_btn = QPushButton("Editar")
        self.edit_btn.clicked.connect(self._edit)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.remove_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        if items:
            for item in items:
                self.list_widget.addItem(QListWidgetItem(item))

    def _add(self):
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "Añadir", "Ingrese texto:")
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
        text, ok = QInputDialog.getText(self, "Editar", "Valor:", text=item.text())
        if ok and text.strip():
            item.setText(text.strip())

    def get_items(self):
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]


class DefectEditorDialog(QDialog):
    """Añadir, editar o eliminar defectos de la base de datos de solución de problemas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editor de Base de Datos de Defectos")
        self.setMinimumSize(800, 600)
        self._current_defect: Optional[Defect] = None
        self._init_ui()
        self._populate_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.stage_filter = QComboBox()
        self.stage_filter.addItems(["Todas"] + STAGES)
        self.stage_filter.currentTextChanged.connect(self._populate_list)
        left_layout.addWidget(QLabel("Filtrar por etapa:"))
        left_layout.addWidget(self.stage_filter)

        self.defect_list = QListWidget()
        self.defect_list.currentItemChanged.connect(self._on_select)
        left_layout.addWidget(self.defect_list, 1)

        list_btn_row = QHBoxLayout()
        add_new_btn = QPushButton("Añadir Nuevo")
        add_new_btn.clicked.connect(self._add_new)
        delete_btn = QPushButton("Eliminar")
        delete_btn.setStyleSheet("color: red;")
        delete_btn.clicked.connect(self._delete)
        list_btn_row.addWidget(add_new_btn)
        list_btn_row.addWidget(delete_btn)
        left_layout.addLayout(list_btn_row)

        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nombre del defecto...")
        form.addRow("Nombre:", self.name_input)

        self.stage_combo = QComboBox()
        self.stage_combo.addItems(STAGES)
        form.addRow("Etapa:", self.stage_combo)

        self.severity_combo = QComboBox()
        self.severity_combo.addItems(SEVERITIES)
        form.addRow("Gravedad:", self.severity_combo)

        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(60)
        self.desc_input.setPlaceholderText("Descripción...")
        form.addRow("Descripción:", self.desc_input)

        right_layout.addLayout(form)

        sym_group = QGroupBox("Síntomas")
        sym_layout = QVBoxLayout(sym_group)
        self.symptoms_editor = ListEditWidget()
        sym_layout.addWidget(self.symptoms_editor)
        right_layout.addWidget(sym_group)

        cause_group = QGroupBox("Causas")
        cause_layout = QVBoxLayout(cause_group)
        self.causes_editor = ListEditWidget()
        cause_layout.addWidget(self.causes_editor)
        right_layout.addWidget(cause_group)

        sol_group = QGroupBox("Soluciones")
        sol_layout = QVBoxLayout(sol_group)
        self.solutions_editor = ListEditWidget()
        sol_layout.addWidget(self.solutions_editor)
        right_layout.addWidget(sol_group)

        ref_group = QGroupBox("Referencias del Foro")
        ref_layout = QVBoxLayout(ref_group)
        self.refs_editor = ListEditWidget(placeholder="ej. viewtopic.php?t=8634")
        ref_layout.addWidget(self.refs_editor)
        right_layout.addWidget(ref_group)

        save_btn = QPushButton("Guardar Cambios")
        save_btn.clicked.connect(self._save_current)
        save_btn.setStyleSheet("background: #4CAF50; color: white; font-weight: bold;")
        right_layout.addWidget(save_btn)

        splitter.addWidget(right_widget)
        splitter.setSizes([300, 500])
        layout.addWidget(splitter, 1)

    def _populate_list(self):
        self.defect_list.clear()
        stage = self.stage_filter.currentText()

        defects = DEFECT_DATABASE
        if stage != "Todas":
            defects = get_defects_by_stage(stage)

        for d in defects:
            item = QListWidgetItem(f"[{d.stage.upper()}] {d.name} ({d.severity})")
            item.setData(Qt.UserRole, d)
            self.defect_list.addItem(item)

    def _on_select(self, current, previous):
        if not current:
            self._current_defect = None
            return
        d = current.data(Qt.UserRole)
        if not d:
            return
        self._current_defect = d
        self.name_input.setText(d.name)
        idx = self.stage_combo.findText(d.stage)
        if idx >= 0:
            self.stage_combo.setCurrentIndex(idx)
        idx2 = self.severity_combo.findText(d.severity)
        if idx2 >= 0:
            self.severity_combo.setCurrentIndex(idx2)
        self.desc_input.setPlainText(d.description)

        self.symptoms_editor.list_widget.clear()
        for s in d.symptoms:
            self.symptoms_editor.list_widget.addItem(QListWidgetItem(s))

        self.causes_editor.list_widget.clear()
        for c in d.causes:
            self.causes_editor.list_widget.addItem(QListWidgetItem(c))

        self.solutions_editor.list_widget.clear()
        for s in d.solutions:
            self.solutions_editor.list_widget.addItem(QListWidgetItem(s))

        self.refs_editor.list_widget.clear()
        for r in d.forum_refs:
            self.refs_editor.list_widget.addItem(QListWidgetItem(r))

    def _add_new(self):
        existing_ids = {d.id for d in DEFECT_DATABASE}
        counter = len(DEFECT_DATABASE) + 1
        while f"CUS-{counter:03d}" in existing_ids:
            counter += 1
        new_id = f"CUS-{counter:03d}"

        new_defect = Defect(
            id=new_id,
            name="Nuevo Defecto",
            stage="cutting",
            description="",
            symptoms=[],
            causes=[],
            solutions=[],
            forum_refs=[],
            severity="medium",
        )
        DEFECT_DATABASE.append(new_defect)
        self._populate_list()
        for i in range(self.defect_list.count()):
            item = self.defect_list.item(i)
            if item.data(Qt.UserRole) and item.data(Qt.UserRole).id == new_id:
                self.defect_list.setCurrentItem(item)
                break

    def _delete(self):
        if not self._current_defect:
            return
        reply = QMessageBox.question(
            self, "Eliminar Defecto",
            f"¿Eliminar '{self._current_defect.name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            DEFECT_DATABASE[:] = [
                d for d in DEFECT_DATABASE if d.id != self._current_defect.id
            ]
            self._current_defect = None
            self._populate_list()

    def _save_current(self):
        if not self._current_defect:
            QMessageBox.warning(self, "Guardar", "No hay defecto seleccionado")
            return

        d = self._current_defect
        d.name = self.name_input.text().strip() or "Sin Nombre"
        d.stage = self.stage_combo.currentText()
        d.severity = self.severity_combo.currentText()
        d.description = self.desc_input.toPlainText().strip()
        d.symptoms = self.symptoms_editor.get_items()
        d.causes = self.causes_editor.get_items()
        d.solutions = self.solutions_editor.get_items()
        d.forum_refs = self.refs_editor.get_items()

        QMessageBox.information(self, "Guardado", f"Defecto '{d.name}' guardado")
        self._populate_list()
