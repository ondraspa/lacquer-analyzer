"""Widget de navegación de base de datos de ingredientes"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QLineEdit, QPushButton, QGroupBox, QTextEdit,
    QComboBox, QSplitter
)
from PySide6.QtCore import Qt, Signal

from core.translations import T
from src.models import Ingredient, IngredientType
from src.ingredient_loader import IngredientLoader


class IngredientBrowserWidget(QWidget):
    ingredients_changed = Signal()

    def __init__(self, loader: IngredientLoader):
        super().__init__()
        self.loader = loader
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(T("Buscar ingredientes..."))
        self.search_input.setToolTip(T("Filtra ingredientes por nombre. La búsqueda es incremental"))
        self.search_input.textChanged.connect(self._filter_tree)
        self.type_filter = QComboBox()
        self.type_filter.addItems([T("Todos los Tipos")] + [t.value for t in IngredientType])
        self.type_filter.setToolTip(T("Filtra ingredientes por tipo (base_resin, solvent, pigmento, aditivo, etc.)"))
        self.type_filter.currentTextChanged.connect(self._filter_tree)
        filter_row.addWidget(self.search_input)
        filter_row.addWidget(QLabel(T("Tipo:")))
        filter_row.addWidget(self.type_filter)
        layout.addLayout(filter_row)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels([T("Ingrediente"), T("Tipo"), T("Categoría")])
        self.tree.setAlternatingRowColors(True)
        self.tree.setToolTip(T("Árbol de ingredientes agrupados por tipo. Muestra nombre, tipo y categoría. Haz clic para ver detalles"))
        self.tree.itemClicked.connect(self._show_detail)
        layout.addWidget(self.tree)

        self.detail_group = QGroupBox(T("Detalles del Ingrediente"))
        self.detail_group.setToolTip(T("Información detallada del ingrediente seleccionado. Puedes editar o añadir ingredientes desde aquí"))
        detail_layout = QVBoxLayout()
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(160)
        self.detail_text.setToolTip(T("Propiedades completas del ingrediente seleccionado: punto de ebullición, densidad, viscosidad, etc."))
        detail_layout.addWidget(self.detail_text)

        detail_btn_row = QHBoxLayout()
        self.edit_btn = QPushButton(T("Editar Seleccionado"))
        self.edit_btn.setToolTip(T("Abre el editor para modificar el ingrediente seleccionado"))
        self.edit_btn.clicked.connect(self._edit_selected)
        self.edit_btn.setEnabled(False)
        detail_btn_row.addWidget(self.edit_btn)
        self.add_btn = QPushButton(T("Añadir Nuevo Ingrediente"))
        self.add_btn.setToolTip(T("Abre el editor para añadir un nuevo ingrediente a la base de datos"))
        self.add_btn.clicked.connect(self._add_new)
        self.add_btn.setStyleSheet("background: #4CAF50; color: white;")
        detail_btn_row.addWidget(self.add_btn)
        detail_btn_row.addStretch()
        detail_layout.addLayout(detail_btn_row)

        self.detail_group.setLayout(detail_layout)
        layout.addWidget(self.detail_group)

    def refresh(self):
        self.tree.clear()
        for type_name, ingredients in self.loader.all_types().items():
            parent = QTreeWidgetItem(self.tree, [type_name.upper(), "", ""])
            parent.setExpanded(True)
            font = parent.font(0)
            font.setBold(True)
            parent.setFont(0, font)

            for ing in ingredients:
                item = QTreeWidgetItem([
                    ing.name, ing.type.value, ing.type.name.replace("_", " ").title()
                ])
                item.setData(0, Qt.UserRole, ing)
                parent.addChild(item)

    def _filter_tree(self):
        search = self.search_input.text().lower()
        type_filter = self.type_filter.currentText()

        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            visible_children = 0
            for j in range(parent.childCount()):
                child = parent.child(j)
                ing = child.data(0, Qt.UserRole)
                matches_search = not search or search in ing.name.lower()
                matches_type = type_filter == T("Todos los Tipos") or type_filter == ing.type.value
                child.setHidden(not (matches_search and matches_type))
                if not child.isHidden():
                    visible_children += 1
            parent.setHidden(visible_children == 0)

    def _show_detail(self, item):
        ing = item.data(0, Qt.UserRole)
        if not ing:
            return
        self._last_clicked_ingredient = ing
        self.edit_btn.setEnabled(True)

        text = f"<h3>{ing.name} ({ing.id})</h3>"
        text += f"<p><b>{T('Tipo:')}</b> {ing.type.value}</p>"

        if ing.properties:
            text += f"<p><b>{T('Propiedades:')}</b></p><ul>"
            for k, v in ing.properties.items():
                text += f"<li>{k}: {v}</li>"
            text += "</ul>"

        text += f"<p><b>{T('Propiedades del Recubrimiento:')}</b></p>"
        cp = ing.coating_properties
        text += f"<p>{T('Sólidos:')} {cp.solids_content_pct or 'N/D'}%</p>"
        text += f"<p>{T('Viscosidad:')} {cp.viscosity_mpas or 'N/D'} mPa·s</p>"
        text += f"<p>{T('Tensión Superficial:')} {cp.surface_tension_dynes} dynes/cm</p>"
        text += f"<p>{T('Tasa de Evaporación:')} {cp.evaporation_rate or 'N/D'}</p>"

        if ing.warnings:
            text += f"<p><b>{T('Advertencias:')}</b></p><ul>"
            for w in ing.warnings:
                text += f"<li style='color:red;'>{w}</li>"
            text += "</ul>"

        if ing.notes:
            text += f"<p><b>{T('Notas:')}</b> {ing.notes}</p>"

        self.detail_text.setHtml(text)

    def _edit_selected(self):
        ing = getattr(self, '_last_clicked_ingredient', None)
        if not ing:
            return
        from ui.workspace.ingredient_editor import IngredientEditorDialog
        dlg = IngredientEditorDialog(self.loader, self, ingredient=ing)
        if dlg.exec():
            self.loader.load_all()
            self.refresh()
            self.ingredients_changed.emit()

    def _add_new(self):
        from ui.workspace.ingredient_editor import IngredientEditorDialog
        dlg = IngredientEditorDialog(self.loader, self, ingredient=None)
        if dlg.exec():
            self.loader.load_all()
            self.refresh()
            self.ingredients_changed.emit()
