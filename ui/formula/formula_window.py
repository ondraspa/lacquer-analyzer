"""Ventana de Fórmulas — biblioteca con versiones, capturas y editor MDI."""

import os
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QSize, QSettings, QBuffer, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap, QUndoCommand, QUndoStack, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QDoubleSpinBox, QComboBox, QGroupBox, QFormLayout, QHeaderView, QMessageBox,
    QDialog, QDialogButtonBox, QSplitter, QMdiArea, QMdiSubWindow, QTabWidget,
    QToolBar, QInputDialog,
)

from core.formula_store import FormulaStore
from core.translations import T, translator
from src.ingredient_loader import IngredientLoader
from core.models import LacquerRecipe, RecipeComponent
from ui.workspace.recipe_analysis_panel import RecipeAnalysisPanel
from ui.theme import DARK_THEME


class FormulaEditCommand(QUndoCommand):
    def __init__(self, editor, before: dict, after: dict, text: str = ""):
        super().__init__(text)
        self.editor = editor
        self.before = before
        self.after = after

    def undo(self):
        self.editor._apply_data(self.before, from_undo=True)

    def redo(self):
        self.editor._apply_data(self.after, from_undo=True)


class FormulaEditorWidget(QWidget):
    dirty_changed = Signal(bool)
    data_changed = Signal(str)

    def __init__(self, loader: IngredientLoader):
        super().__init__()
        self.loader = loader
        self.formula_id = ""
        self._updating = False
        self._last_saved: dict = {}
        self._snapshot: dict = {}
        self.undo_stack = QUndoStack(self)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        header = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.editingFinished.connect(self._push_change)
        self.name_input.setToolTip(T("Nombre de la fórmula. Se guarda al terminar de editar"))
        self.target_viscosity = QDoubleSpinBox()
        self.target_viscosity.setRange(50, 5000)
        self.target_viscosity.setSuffix(" mPa·s")
        self.target_viscosity.setValue(500)
        self.target_viscosity.valueChanged.connect(self._push_change)
        self.target_viscosity.setToolTip(T("Viscosidad objetivo en mPa·s"))
        self.target_solids = QDoubleSpinBox()
        self.target_solids.setRange(0, 80)
        self.target_solids.setSuffix(" %")
        self.target_solids.setValue(18)
        self.target_solids.setDecimals(1)
        self.target_solids.valueChanged.connect(self._push_change)
        self.target_solids.setToolTip(T("Porcentaje de sólidos objetivo"))
        header.addRow(T("Nombre:"), self.name_input)
        header.addRow(T("Viscosidad Objetivo:"), self.target_viscosity)
        header.addRow(T("Sólidos Objetivo:"), self.target_solids)
        layout.addLayout(header)

        tabs = QTabWidget()

        comp_widget = QWidget()
        comp_layout = QVBoxLayout(comp_widget)

        add_row = QHBoxLayout()
        self.ingredient_selector = QComboBox()
        self.ingredient_selector.setMinimumWidth(280)
        self._populate_selector()
        self.ingredient_selector.setToolTip(T("Selecciona un ingrediente de la base de datos para añadirlo a la fórmula"))
        self.conc_input = QDoubleSpinBox()
        self.conc_input.setRange(0.1, 100)
        self.conc_input.setDecimals(2)
        self.conc_input.setSuffix(" %")
        self.conc_input.setValue(10)
        self.conc_input.setToolTip(T("Concentración del nuevo componente en porcentaje"))
        self.add_btn = QPushButton(T("Añadir Componente"))
        self.add_btn.clicked.connect(self._add_component)
        self.add_btn.setToolTip(T("Añade el ingrediente seleccionado a la tabla"))
        add_row.addWidget(QLabel(T("Añadir desde BD:")))
        add_row.addWidget(self.ingredient_selector)
        add_row.addWidget(self.conc_input)
        add_row.addWidget(self.add_btn)
        add_row.addStretch()
        comp_layout.addLayout(add_row)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            T("Ingrediente"), T("Tipo"), T("Concentración %"), T("Máx %")
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setToolTip(T("Tabla de componentes de la fórmula. Cada fila es un ingrediente con su concentración"))
        self.table.cellChanged.connect(self._on_table_edit)
        comp_layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.remove_btn = QPushButton(T("Quitar Seleccionado"))
        self.remove_btn.clicked.connect(self._remove_component)
        self.remove_btn.setToolTip(T("Elimina el componente seleccionado de la tabla"))
        self.analyze_btn = QPushButton(T("Ejecutar Análisis Completo"))
        self.analyze_btn.clicked.connect(self._run_analysis)
        self.analyze_btn.setToolTip(T("Ejecuta el análisis físico-químico completo de la fórmula actual"))
        btn_row.addWidget(self.remove_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.analyze_btn)
        comp_layout.addLayout(btn_row)

        tabs.addTab(comp_widget, T("Componentes"))

        self.analysis_panel = RecipeAnalysisPanel()
        tabs.addTab(self.analysis_panel, T("Análisis de Laca"))

        layout.addWidget(tabs, 1)

    def _populate_selector(self):
        self.ingredient_selector.clear()
        for ing_type, items in self.loader.all_types().items():
            for item in items:
                label = f"[{item.type.value}] {item.name} ({item.id})"
                self.ingredient_selector.addItem(label, item)

    def load_from_store(self, store: FormulaStore, formula_id: str):
        data = store.get_formula(formula_id)
        if data is None:
            return
        self.formula_id = formula_id
        self.undo_stack.clear()
        self._updating = True
        self._apply_data(data)
        self._updating = False
        baseline = self.get_data()
        self._last_saved = baseline
        self._snapshot = baseline
        self.dirty_changed.emit(False)

    def _apply_data(self, data: dict, from_undo: bool = False):
        self._updating = True
        self.name_input.setText(data.get("name", self.formula_id))
        self.target_viscosity.setValue(float(data.get("target_viscosity_mpas", 500) or 500))
        self.target_solids.setValue(float(data.get("target_solids_pct", 18) or 18))
        self.table.setRowCount(0)
        for comp in data.get("components", []):
            row = self.table.rowCount()
            self.table.insertRow(row)
            name_item = QTableWidgetItem(comp.get("name", comp.get("id", "")))
            name_item.setData(Qt.UserRole, comp.get("id", ""))
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(comp.get("type", "")))
            conc = QDoubleSpinBox()
            conc.setRange(0.1, 100)
            conc.setDecimals(2)
            conc.setSuffix(" %")
            conc.setSingleStep(0.1)
            conc.setValue(float(comp.get("concentration_pct", 10)))
            conc.valueChanged.connect(self._push_change)
            self.table.setCellWidget(row, 2, conc)
            max_conc = comp.get("max_concentration_pct")
            max_item = QTableWidgetItem(f"{max_conc}%" if max_conc else "N/D")
            max_item.setFlags(max_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 3, max_item)
        self._updating = False
        if from_undo:
            self._snapshot = dict(data)
            self._emit_changed()

    def get_data(self) -> dict:
        components = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            ing_id = name_item.data(Qt.UserRole) if name_item else ""
            conc_widget = self.table.cellWidget(row, 2)
            max_item = self.table.item(row, 3)
            max_text = max_item.text() if max_item else "N/D"
            components.append({
                "id": ing_id,
                "name": name_item.text() if name_item else "",
                "concentration_pct": conc_widget.value() if conc_widget else 10,
                "max_concentration_pct": float(max_text.rstrip("%")) if max_text.endswith("%") else None,
            })
        return {
            "id": f"USER-{self.formula_id}",
            "name": self.name_input.text().strip() or self.formula_id,
            "components": components,
            "target_viscosity_mpas": self.target_viscosity.value(),
            "target_solids_pct": self.target_solids.value(),
            "application": "curtain_coater",
            "coater": "burkle",
            "notes": "",
            "metadata": {},
        }

    def _push_change(self):
        if self._updating:
            return
        after = self.get_data()
        if self._snapshot == after:
            return
        before = self._snapshot
        self.undo_stack.push(FormulaEditCommand(
            self, before, after, T("Editar fórmula")
        ))
        self._snapshot = after
        self._emit_changed()

    def _on_table_edit(self, row: int, col: int):
        if col == 0:
            self._push_change()

    def _add_component(self):
        ingredient = self.ingredient_selector.currentData()
        if not ingredient:
            return
        if self._updating:
            return
        data = self.get_data()
        data["components"] = data["components"] + [{
            "id": ingredient.id,
            "name": ingredient.name,
            "type": ingredient.type.value,
            "concentration_pct": round(self.conc_input.value(), 2),
            "max_concentration_pct": ingredient.max_concentration_pct,
        }]
        self._updating = True
        self._apply_data(data)
        self._updating = False
        self._push_change()

    def _remove_component(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            return
        if self._updating:
            return
        data = self.get_data()
        for row in rows:
            if row < len(data["components"]):
                data["components"].pop(row)
        self._updating = True
        self._apply_data(data)
        self._updating = False
        self._push_change()

    def _run_analysis(self):
        recipe = self._build_recipe()
        if not recipe or not recipe.components:
            QMessageBox.information(
                self, T("Análisis"),
                T("Añade al menos un componente antes de analizar.")
            )
            return
        self.analysis_panel.analyze_recipe(recipe)

    def _build_recipe(self) -> Optional[LacquerRecipe]:
        components = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            name = name_item.text() if name_item else ""
            ingredient = self.loader.get_by_name(name.lower())
            if not ingredient:
                for items in self.loader.all_types().values():
                    for ing in items:
                        if ing.name == name:
                            ingredient = ing
                            break
            if not ingredient:
                continue
            conc_widget = self.table.cellWidget(row, 2)
            components.append(RecipeComponent(
                ingredient=ingredient,
                concentration_pct=conc_widget.value() if conc_widget else 10,
            ))
        return LacquerRecipe(
            id=f"USER-{self.formula_id}",
            name=self.name_input.text().strip() or self.formula_id,
            components=components,
            target_viscosity_mpas=self.target_viscosity.value(),
            target_solids_pct=self.target_solids.value(),
        )

    def mark_saved(self, data: dict):
        self._last_saved = dict(data)
        self._snapshot = dict(data)
        self._emit_changed()

    def is_dirty(self) -> bool:
        return self.get_data() != self._last_saved

    def _emit_changed(self):
        self.dirty_changed.emit(self.is_dirty())
        self.data_changed.emit(self.formula_id)

    def retranslate(self):
        self.name_input.setToolTip(T("Nombre de la fórmula. Se guarda al terminar de editar"))
        self.target_viscosity.setToolTip(T("Viscosidad objetivo en mPa·s"))
        self.target_solids.setToolTip(T("Porcentaje de sólidos objetivo"))
        self.ingredient_selector.setToolTip(T("Selecciona un ingrediente de la base de datos para añadirlo a la fórmula"))
        self.conc_input.setToolTip(T("Concentración del nuevo componente en porcentaje"))
        self.add_btn.setText(T("Añadir Componente"))
        self.add_btn.setToolTip(T("Añade el ingrediente seleccionado a la tabla"))
        self.remove_btn.setText(T("Quitar Seleccionado"))
        self.remove_btn.setToolTip(T("Elimina el componente seleccionado de la tabla"))
        self.analyze_btn.setText(T("Ejecutar Análisis Completo"))
        self.analyze_btn.setToolTip(T("Ejecuta el análisis físico-químico completo de la fórmula actual"))
        self.table.setHorizontalHeaderLabels([
            T("Ingrediente"), T("Tipo"), T("Concentración %"), T("Máx %")
        ])
        self.table.setToolTip(T("Tabla de componentes de la fórmula. Cada fila es un ingrediente con su concentración"))


class FormulaSubWindow(QMdiSubWindow):
    def __init__(self, editor: FormulaEditorWidget):
        super().__init__()
        self.editor = editor
        self.setWidget(editor)

    def closeEvent(self, event):
        if self.editor.is_dirty():
            answer = QMessageBox.question(
                self, T("Cambios sin guardar"),
                T("La fórmula tiene cambios sin guardar. ¿Guardarlos antes de cerrar?"),
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if answer == QMessageBox.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.Save:
                self.editor.data_changed.emit(self.editor.formula_id)
        super().closeEvent(event)


class VersionPreviewDialog(QDialog):
    def __init__(self, store: FormulaStore, formula_id: str, version: int,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("Vista Previa de Versión"))
        self.resize(640, 480)
        layout = QVBoxLayout(self)
        data = store.get_version(formula_id, version) or {}
        versions = store.list_versions(formula_id)
        info = ""
        for v in versions:
            if v.number == version:
                info = f"{T('Versión')} {v.number} — {v.timestamp}"
                if v.reason:
                    info += f" — {v.reason}"
                if v.diff.get("summary"):
                    info += f"\n{T('Cambios:')} {v.diff['summary']}"
        info_label = QLabel(info)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels([
            T("Ingrediente"), T("Concentración %"), T("Máx %")
        ])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for comp in data.get("components", []):
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(comp.get("name", "")))
            table.setItem(row, 1, QTableWidgetItem(str(comp.get("concentration_pct", ""))))
            table.setItem(row, 2, QTableWidgetItem(
                f"{comp.get('max_concentration_pct')}%" if comp.get("max_concentration_pct") else "N/D"
            ))
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class CompareImagesDialog(QDialog):
    def __init__(self, left: str, right: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("Comparar Capturas"))
        self.resize(900, 600)
        layout = QHBoxLayout(self)
        self._left_label = QLabel()
        self._right_label = QLabel()
        for label, path in ((self._left_label, left), (self._right_label, right)):
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("border: 1px solid #444;")
            self._set_pixmap(label, path)
            layout.addWidget(label, 1)

    def _set_pixmap(self, label: QLabel, path: str):
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            label.setPixmap(pixmap.scaled(
                420, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = (self.width() - 60) // 2
        h = self.height() - 80
        for label in (self._left_label, self._right_label):
            pixmap = label.pixmap()
            if pixmap and not pixmap.isNull():
                label.setPixmap(pixmap.scaled(
                    max(w, 100), max(h, 100), Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))


class FormulaInfoDialog(QDialog):
    def __init__(self, name: str, description: str, tags: List[str],
                 favorite: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("Información de la Fórmula"))
        self.resize(420, 260)
        layout = QFormLayout(self)
        self.description_input = QLineEdit(description)
        self.tags_input = QLineEdit(", ".join(tags))
        self.favorite_check = QPushButton(T("⭐ Marcar como Favorita"))
        self.favorite_check.setCheckable(True)
        self.favorite_check.setChecked(favorite)
        self.favorite_check.setStyleSheet(
            "background-color: #FFB300; color: black; font-weight: bold;"
            if favorite else ""
        )
        layout.addRow(T("Descripción:"), self.description_input)
        layout.addRow(T("Etiquetas (separadas por coma):"), self.tags_input)
        layout.addRow("", self.favorite_check)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def description(self) -> str:
        return self.description_input.text().strip()

    def tags(self) -> List[str]:
        return [t.strip() for t in self.tags_input.text().split(",") if t.strip()]

    def favorite(self) -> bool:
        return self.favorite_check.isChecked()


class FormulaWindow(QMainWindow):
    def __init__(self, loader: Optional[IngredientLoader] = None,
                 store: Optional[FormulaStore] = None):
        super().__init__()
        self.setStyleSheet(DARK_THEME)
        self.store = store or FormulaStore()
        self.loader = loader or IngredientLoader(
            os.path.join(os.path.dirname(__file__), "..", "..", "config")
        )
        self.loader.load_all()
        self._settings = QSettings("LacquerAnalyzer", "FormulaWindow")
        self._editors: Dict[str, FormulaEditorWidget] = {}
        self._subwindows: Dict[str, FormulaSubWindow] = {}
        self._init_ui()
        self._retranslate_ui()
        self._restore_geometry()
        self._refresh_library()
        translator.language_changed.connect(self._retranslate_ui)

    def _init_ui(self):
        self.setMinimumSize(1200, 760)
        toolbar = QToolBar(T("Fórmulas"))
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))

        self.new_action = QAction(T("Nueva Fórmula"), self)
        self.new_action.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_N))
        self.new_action.triggered.connect(self._new_formula)
        toolbar.addAction(self.new_action)

        self.save_action = QAction(T("Guardar"), self)
        self.save_action.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_S))
        self.save_action.triggered.connect(self._save_current)
        toolbar.addAction(self.save_action)

        self.version_action = QAction(T("Guardar Versión"), self)
        self.version_action.triggered.connect(self._commit_current)
        toolbar.addAction(self.version_action)

        toolbar.addSeparator()

        self.undo_action = self._make_undo_action()
        self.redo_action = self._make_redo_action()
        toolbar.addAction(self.undo_action)
        toolbar.addAction(self.redo_action)

        toolbar.addSeparator()

        self.capture_action = QAction(T("Captura de Pantalla"), self)
        self.capture_action.setShortcut(QKeySequence(Qt.CTRL | Qt.SHIFT | Qt.Key_S))
        self.capture_action.triggered.connect(self._capture_current)
        toolbar.addAction(self.capture_action)

        self.addToolBar(toolbar)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)

        self.library_group = QGroupBox(T("Biblioteca de Fórmulas"))
        library_layout = QVBoxLayout(self.library_group)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(T("Buscar fórmulas..."))
        self.search_input.textChanged.connect(self._refresh_library)
        search_row.addWidget(self.search_input)
        library_layout.addLayout(search_row)

        self.library_list = QListWidget()
        self.library_list.currentItemChanged.connect(self._on_library_selection)
        self.library_list.itemDoubleClicked.connect(
            lambda item: self._open_formula(item.data(Qt.UserRole))
        )
        self.library_list.setToolTip(T("Doble clic abre la fórmula. La lista se filtra con el buscador"))
        library_layout.addWidget(self.library_list, 1)

        lib_buttons = QHBoxLayout()
        self.info_btn = QPushButton(T("✏ Info"))
        self.info_btn.clicked.connect(self._edit_info)
        self.fav_btn = QPushButton(T("⭐"))
        self.fav_btn.clicked.connect(self._toggle_favorite)
        self.del_btn = QPushButton(T("Eliminar"))
        self.del_btn.clicked.connect(self._delete_formula)
        for b in (self.info_btn, self.fav_btn, self.del_btn):
            b.setToolTip(T("Gestiona la fórmula seleccionada: información, favorita o eliminar"))
            lib_buttons.addWidget(b)
        library_layout.addLayout(lib_buttons)

        left_layout.addWidget(self.library_group, 1)

        self.history_group = QGroupBox(T("Historial de Versiones"))
        history_layout = QVBoxLayout(self.history_group)
        self.history_list = QListWidget()
        self.history_list.setToolTip(T("Historial de versiones de la fórmula seleccionada. Cada versión guarda un motivo y el resumen de cambios"))
        history_layout.addWidget(self.history_list, 1)
        hist_buttons = QHBoxLayout()
        self.preview_btn = QPushButton(T("Vista Previa"))
        self.preview_btn.clicked.connect(self._preview_version)
        self.restore_btn = QPushButton(T("Restaurar"))
        self.restore_btn.clicked.connect(self._restore_version)
        hist_buttons.addWidget(self.preview_btn)
        hist_buttons.addWidget(self.restore_btn)
        history_layout.addLayout(hist_buttons)

        left_layout.addWidget(self.history_group, 1)

        self.snap_group = QGroupBox(T("Capturas"))
        snap_layout = QVBoxLayout(self.snap_group)
        self.snapshots_list = QListWidget()
        self.snapshots_list.setViewMode(QListWidget.IconMode)
        self.snapshots_list.setIconSize(QSize(96, 72))
        self.snapshots_list.setResizeMode(QListWidget.Adjust)
        self.snapshots_list.setMovement(QListWidget.Static)
        self.snapshots_list.setToolTip(T("Capturas de pantalla de la fórmula seleccionada, guardadas por versión"))
        snap_layout.addWidget(self.snapshots_list, 1)
        snap_buttons = QHBoxLayout()
        self.compare_btn = QPushButton(T("Comparar"))
        self.compare_btn.clicked.connect(self._compare_images)
        self.del_snap_btn = QPushButton(T("Eliminar Captura"))
        self.del_snap_btn.clicked.connect(self._delete_snapshot)
        snap_buttons.addWidget(self.compare_btn)
        snap_buttons.addWidget(self.del_snap_btn)
        snap_layout.addLayout(snap_buttons)

        left_layout.addWidget(self.snap_group, 1)
        splitter.addWidget(left)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.mdi = QMdiArea()
        self.mdi.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mdi.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        splitter.addWidget(self.mdi)

        layout.addWidget(splitter, 1)

        self.statusBar().showMessage(T("Listo"))
        self.setWindowTitle(T("Ventana de Fórmulas"))

    def _make_undo_action(self) -> QAction:
        action = QAction(T("Deshacer"), self)
        action.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_Z))
        action.triggered.connect(self._undo_current)
        return action

    def _make_redo_action(self) -> QAction:
        action = QAction(T("Rehacer"), self)
        action.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_Y))
        action.triggered.connect(self._redo_current)
        return action

    def _restore_geometry(self):
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        self._settings.setValue("geometry", self.saveGeometry())
        for subwindow in list(self._subwindows.values()):
            if subwindow.editor.is_dirty():
                subwindow.close()
        super().closeEvent(event)

    def _active_editor(self) -> Optional[FormulaEditorWidget]:
        subwindow = self.mdi.currentSubWindow()
        if isinstance(subwindow, FormulaSubWindow):
            return subwindow.editor
        return None

    def _open_formula(self, formula_id: str):
        if formula_id in self._subwindows:
            self._subwindows[formula_id].show()
            self._subwindows[formula_id].raise_()
            self.mdi.setActiveSubWindow(self._subwindows[formula_id])
            return
        if not self.store.formula_exists(formula_id):
            return
        editor = FormulaEditorWidget(self.loader)
        editor.load_from_store(self.store, formula_id)
        editor.data_changed.connect(self._on_editor_data_changed)
        editor.dirty_changed.connect(lambda dirty: self._on_dirty_changed(formula_id, dirty))
        subwindow = FormulaSubWindow(editor)
        subwindow.setWindowTitle(f"🧪 {editor.name_input.text()}")
        subwindow.resize(680, 520)
        self.mdi.addSubWindow(subwindow)
        subwindow.show()
        self._subwindows[formula_id] = subwindow
        self._editors[formula_id] = editor
        self._refresh_history(formula_id)
        self._refresh_snapshots(formula_id)
        self.statusBar().showMessage(T("Fórmula abierta:") + f" {formula_id}", 3000)

    def _new_formula(self):
        name, ok = QInputDialog.getText(
            self, T("Nueva Fórmula"),
            T("Nombre de la nueva fórmula:"),
        )
        if not ok or not name.strip():
            return
        template = {
            "id": "NEW",
            "name": name.strip(),
            "components": [],
            "target_viscosity_mpas": 500,
            "target_solids_pct": 18,
            "application": "curtain_coater",
            "coater": "burkle",
            "notes": "",
            "metadata": {},
        }
        try:
            ref = self.store.create_formula(name.strip(), template)
        except ValueError as e:
            QMessageBox.warning(self, T("Error"), str(e))
            return
        self._refresh_library()
        self._open_formula(ref.id)

    def _save_current(self):
        editor = self._active_editor()
        if not editor:
            return
        data = editor.get_data()
        self.store.save_formula(editor.formula_id, data)
        editor.mark_saved(data)
        self._refresh_library()
        self.statusBar().showMessage(T("Guardado"), 3000)

    def _commit_current(self):
        editor = self._active_editor()
        if not editor:
            return
        reason, ok = QInputDialog.getText(
            self, T("Guardar Versión"),
            T("Motivo del cambio (opcional):"),
        )
        if not ok:
            return
        data = editor.get_data()
        self.store.save_formula(editor.formula_id, data)
        self.store.commit_version(editor.formula_id, reason.strip() or T("Sin motivo"), data=data)
        editor.mark_saved(data)
        self._refresh_library()
        self._refresh_history(editor.formula_id)
        self.statusBar().showMessage(T("Versión guardada"), 3000)

    def _capture_current(self):
        editor = self._active_editor()
        if not editor:
            return
        pixmap = editor.grab()
        buffer = QBuffer()
        buffer.open(QBuffer.WriteOnly)
        pixmap.save(buffer, "PNG")
        version = self.store.get_formula_meta(editor.formula_id).get("version", 1)
        self.store.save_snapshot_image(editor.formula_id, version, bytes(buffer.data()))
        self._refresh_snapshots(editor.formula_id)
        self.statusBar().showMessage(T("Captura guardada"), 3000)

    def _undo_current(self):
        editor = self._active_editor()
        if editor:
            editor.undo_stack.undo()

    def _redo_current(self):
        editor = self._active_editor()
        if editor:
            editor.undo_stack.redo()

    def _on_editor_data_changed(self, formula_id: str):
        if not self.store.formula_exists(formula_id):
            return
        editor = self._editors.get(formula_id)
        if not editor:
            return
        data = editor.get_data()
        self.store.save_formula(formula_id, data)
        self._subwindows[formula_id].setWindowTitle(
            f"🧪 {data.get('name', formula_id)}"
        )
        self._refresh_library()

    def _on_dirty_changed(self, formula_id: str, dirty: bool):
        subwindow = self._subwindows.get(formula_id)
        if not subwindow:
            return
        title = f"🧪 {subwindow.editor.name_input.text()}"
        if dirty:
            title += " ●"
        subwindow.setWindowTitle(title)

    def _on_library_selection(self, current, previous):
        if current:
            formula_id = current.data(Qt.UserRole)
            self._refresh_history(formula_id)
            self._refresh_snapshots(formula_id)

    def _refresh_library(self):
        query = self.search_input.text().strip().lower()
        current_id = None
        if self.library_list.currentItem():
            current_id = self.library_list.currentItem().data(Qt.UserRole)
        self.library_list.blockSignals(True)
        self.library_list.clear()
        for ref in sorted(self.store.list_formulas(), key=lambda r: r.name.lower()):
            if query and query not in ref.name.lower() and not any(
                query in t.lower() for t in ref.tags
            ):
                continue
            label = f"⭐ {ref.name}  [v{ref.version}]" if ref.favorite else f"{ref.name}  [v{ref.version}]"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, ref.id)
            self.library_list.addItem(item)
            if ref.id == current_id:
                self.library_list.setCurrentItem(item)
        self.library_list.blockSignals(False)

    def _refresh_history(self, formula_id: str):
        self.history_list.clear()
        if not formula_id:
            return
        for v in reversed(self.store.list_versions(formula_id)):
            text = f"v{v.number}  {v.timestamp}"
            if v.reason:
                text += f"  «{v.reason}»"
            if v.diff.get("summary"):
                text += f"  ({v.diff['summary']})"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, v.number)
            self.history_list.addItem(item)

    def _refresh_snapshots(self, formula_id: str):
        self.snapshots_list.clear()
        if not formula_id:
            return
        for v in self.store.list_versions(formula_id):
            for path in v.images:
                pixmap = QPixmap(path)
                item = QListWidgetItem(QIcon(pixmap), f"v{v.number}")
                item.setData(Qt.UserRole, path)
                item.setToolTip(f"v{v.number} — {os.path.basename(path)}")
                self.snapshots_list.addItem(item)

    def _selected_formula_id(self) -> Optional[str]:
        item = self.library_list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _preview_version(self):
        formula_id = self._selected_formula_id()
        if not formula_id:
            return
        item = self.history_list.currentItem()
        if not item:
            return
        dialog = VersionPreviewDialog(
            self.store, formula_id, item.data(Qt.UserRole), self
        )
        dialog.exec()

    def _restore_version(self):
        formula_id = self._selected_formula_id()
        if not formula_id:
            return
        item = self.history_list.currentItem()
        if not item:
            return
        version = item.data(Qt.UserRole)
        answer = QMessageBox.question(
            self, T("Restaurar Versión"),
            T("¿Restaurar la versión {v}?\nLa versión actual se guardará automáticamente como punto de seguridad.").format(v=version),
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if answer != QMessageBox.Yes:
            return
        self.store.restore_version(formula_id, version, T("Restauración manual"))
        editor = self._editors.get(formula_id)
        if editor:
            editor.load_from_store(self.store, formula_id)
            self._subwindows[formula_id].setWindowTitle(f"🧪 {editor.name_input.text()}")
        self._refresh_library()
        self._refresh_history(formula_id)
        self.statusBar().showMessage(T("Versión restaurada"), 3000)

    def _compare_images(self):
        formula_id = self._selected_formula_id()
        if not formula_id:
            return
        paths = []
        for item in self.snapshots_list.selectedItems():
            paths.append(item.data(Qt.UserRole))
        if len(paths) < 2:
            QMessageBox.information(
                self, T("Comparar Capturas"),
                T("Selecciona dos capturas para compararlas.")
            )
            return
        CompareImagesDialog(paths[0], paths[1], self).exec()

    def _delete_snapshot(self):
        formula_id = self._selected_formula_id()
        if not formula_id:
            return
        item = self.snapshots_list.currentItem()
        if not item:
            return
        path = item.data(Qt.UserRole)
        filename = os.path.basename(path)
        version = int(item.text().lstrip("v"))
        self.store.delete_snapshot_image(formula_id, version, filename)
        self._refresh_snapshots(formula_id)

    def _toggle_favorite(self):
        formula_id = self._selected_formula_id()
        if not formula_id:
            return
        meta = self.store.get_formula_meta(formula_id)
        self.store.set_favorite(formula_id, not meta.get("favorite", False))
        self._refresh_library()

    def _edit_info(self):
        formula_id = self._selected_formula_id()
        if not formula_id:
            return
        meta = self.store.get_formula_meta(formula_id)
        data = self.store.get_formula(formula_id)
        dialog = FormulaInfoDialog(
            data.get("name", formula_id),
            meta.get("description", ""),
            meta.get("tags", []),
            meta.get("favorite", False),
            self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        self.store.update_meta(
            formula_id,
            favorite=dialog.favorite(),
            description=dialog.description(),
            tags=dialog.tags(),
        )
        self._refresh_library()

    def _delete_formula(self):
        formula_id = self._selected_formula_id()
        if not formula_id:
            return
        answer = QMessageBox.question(
            self, T("Eliminar Fórmula"),
            T("¿Eliminar la fórmula '{name}'?\nEsta acción no se puede deshacer.").format(
                name=self.store.get_formula(formula_id).get("name", formula_id)
            ),
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if answer != QMessageBox.Yes:
            return
        subwindow = self._subwindows.get(formula_id)
        if subwindow:
            subwindow.close()
            if subwindow.isVisible():
                return
            self.mdi.removeSubWindow(subwindow)
            self._subwindows.pop(formula_id, None)
        self._editors.pop(formula_id, None)
        self.store.delete_formula(formula_id)
        self._refresh_library()
        self.history_list.clear()
        self.snapshots_list.clear()

    def _retranslate_ui(self):
        self.setWindowTitle(T("Ventana de Fórmulas"))
        self.new_action.setText(T("Nueva Fórmula"))
        self.save_action.setText(T("Guardar"))
        self.version_action.setText(T("Guardar Versión"))
        self.undo_action.setText(T("Deshacer"))
        self.redo_action.setText(T("Rehacer"))
        self.capture_action.setText(T("Captura de Pantalla"))
        self.search_input.setPlaceholderText(T("Buscar fórmulas..."))
        self.search_input.setToolTip(T("Filtra la biblioteca por nombre o etiqueta"))
        self.library_list.setToolTip(T("Doble clic abre la fórmula. La lista se filtra con el buscador"))
        self.info_btn.setText(T("✏ Info"))
        self.fav_btn.setText(T("⭐"))
        self.del_btn.setText(T("Eliminar"))
        for b in (self.info_btn, self.fav_btn, self.del_btn):
            b.setToolTip(T("Gestiona la fórmula seleccionada: información, favorita o eliminar"))
        self.history_list.setToolTip(T("Historial de versiones de la fórmula seleccionada. Cada versión guarda un motivo y el resumen de cambios"))
        self.preview_btn.setText(T("Vista Previa"))
        self.restore_btn.setText(T("Restaurar"))
        self.snapshots_list.setToolTip(T("Capturas de pantalla de la fórmula seleccionada, guardadas por versión"))
        self.compare_btn.setText(T("Comparar"))
        self.del_snap_btn.setText(T("Eliminar Captura"))
        self.library_group.setTitle(T("Biblioteca de Fórmulas"))
        self.history_group.setTitle(T("Historial de Versiones"))
        self.snap_group.setTitle(T("Capturas"))
        self.statusBar().showMessage(T("Listo"))
        for editor in self._editors.values():
            editor.retranslate()
