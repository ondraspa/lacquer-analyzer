"""Mind-map style knowledge base navigator using QGraphicsView."""

import math
from collections import Counter
from typing import Optional, List

from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsObject, QMenu, QInputDialog, QMessageBox,
)
from PySide6.QtCore import (
    Qt, QRectF, QPointF, QPropertyAnimation, QEasingCurve,
    Signal, QTimer, QParallelAnimationGroup,
)
from PySide6.QtGui import (
    QBrush, QPen, QColor, QFont, QPainter,
    QFontMetrics, QLinearGradient, QAction,
)


# ── Colour palette per category ─────────────────────────────────────
CAT_COLORS = {
    "patent":    QColor("#2196F3"),  # blue
    "forum":     QColor("#4CAF50"),  # green
    "book":      QColor("#FF9800"),  # orange
    "general":   QColor("#9E9E9E"),  # grey
    "correction": QColor("#AB47BC"), # purple
    "paper":     QColor("#26C6DA"),  # cyan
    "article":   QColor("#26C6DA"),
}

def _color_for(cat: str) -> QColor:
    return CAT_COLORS.get(cat.lower(), QColor("#78909C"))


# ── Graphics items ──────────────────────────────────────────────────

class NodeItem(QGraphicsObject):
    """A rounded-rectangle node with title and optional subtitle.
    Dimensions auto-size to fit content."""

    def __init__(self, label: str, subtitle: str = "",
                 color: QColor = QColor("#2196F3"),
                 node_type: str = "category",
                 data=None):
        super().__init__()
        self._label = label
        self._subtitle = subtitle
        self._color = color
        self._node_type = node_type
        self._data = data
        self._expanded = False
        self._children: List[NodeItem] = []
        self._parent_node: Optional[NodeItem] = None

        self.setFlags(
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self._hovered = False

        # Font sizing
        if node_type == "root":
            self._title_size = 15
            self._sub_size = 11
        elif node_type == "import_type":
            self._title_size = 13
            self._sub_size = 10
        elif node_type == "category":
            self._title_size = 12
            self._sub_size = 10
        else:
            self._title_size = 11
            self._sub_size = 0

        # Compute dimensions from text
        tf = QFont("Segoe UI", self._title_size, QFont.Bold)
        tmf = QFontMetrics(tf)
        tw = tmf.horizontalAdvance(self._label[:40]) + 20
        self._w = max(tw, 100)
        self._h = 46 if self._subtitle and self._sub_size > 0 else 34

    def boundingRect(self):
        return QRectF(-self._w/2 - 4, -self._h/2 - 4,
                      self._w + 8, self._h + 8)

    def paint(self, painter, option, widget):
        r = QRectF(-self._w/2, -self._h/2, self._w, self._h)
        painter.setRenderHint(QPainter.Antialiasing)

        # Shadow
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 50))
        painter.drawRoundedRect(r.translated(2, 3), 10, 10)

        # Main fill
        base = self._color if not self._hovered else self._color.lighter(130)
        grad = QLinearGradient(r.topLeft(), r.bottomLeft())
        grad.setColorAt(0, base.lighter(120))
        grad.setColorAt(1, base)
        painter.setBrush(grad)

        # Border
        if self.isSelected():
            painter.setPen(QPen(QColor("#FFD700"), 2.5))
        elif self._hovered:
            painter.setPen(QPen(base.lighter(180), 2))
        else:
            painter.setPen(QPen(base.darker(130), 1))
        painter.drawRoundedRect(r, 10, 10)

        # Title text — upper portion
        painter.setPen(Qt.white)
        font = QFont("Segoe UI", self._title_size, QFont.Bold)
        painter.setFont(font)
        fm = QFontMetrics(font)
        text = self._label[:40]
        if fm.horizontalAdvance(text) > self._w - 14:
            text = fm.elidedText(text, Qt.ElideRight, self._w - 14)
        title_rect = r.adjusted(4, 4, -4, -4)
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, text)

        # Subtitle — bottom-right
        if self._subtitle:
            painter.setFont(QFont("Segoe UI", self._sub_size))
            painter.setPen(QColor(255, 255, 255, 200))
            painter.drawText(r.adjusted(6, 0, -6, -4),
                             Qt.AlignRight | Qt.AlignBottom, self._subtitle)

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged and self._children:
            for c in self._children:
                c.setSelected(value)
        return super().itemChange(change, value)

    # ── Tree helpers ──
    def add_child(self, node):
        self._children.append(node)
        node._parent_node = self

    @property
    def children(self):
        return self._children

    @property
    def node_type(self):
        return self._node_type

    @property
    def data(self):
        return self._data

    @property
    def expanded(self):
        return self._expanded

    @expanded.setter
    def expanded(self, val):
        self._expanded = val

    @property
    def label(self):
        return self._label


class EdgeItem(QGraphicsItem):
    """A curved edge connecting two nodes."""

    def __init__(self, source: NodeItem, dest: NodeItem, color=QColor(180, 180, 180, 80)):
        super().__init__()
        self._source = source
        self._dest = dest
        self._color = color
        self.setZValue(-1)

    def boundingRect(self):
        return QRectF(-2000, -2000, 4000, 4000)

    def paint(self, painter, option, widget):
        if not self._source or not self._dest:
            return
        painter.setRenderHint(QPainter.Antialiasing)
        s = self._source.pos()
        d = self._dest.pos()
        painter.setPen(QPen(self._color, 1.5, Qt.DashLine))
        painter.drawLine(s, d)


# ── The map view ────────────────────────────────────────────────────

class KnowledgeMapView(QGraphicsView):
    """Interactive mind-map view of the knowledge base."""

    entry_clicked = Signal(object)   # KnowledgeEntry
    category_clicked = Signal(str, int)  # category_name, count
    rebuild_requested = Signal()      # emitted after delete/edit

    def __init__(self, parent=None):
        super().__init__(parent)
        self._kb = None
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor("#1a1a2e")))
        self.setToolTip("Mapa mental de conocimiento. Rueda = zoom, Arrastrar fondo = mover, Doble clic en nodo = expandir/colapsar, Clic derecho = opciones")

        self._nodes: List[NodeItem] = []
        self._edges: List[EdgeItem] = []
        self._root = None
        self._import_nodes: dict = {}
        self._category_nodes: dict = {}
        self._animating = False

        # Zoom state
        self._min_zoom = 0.08
        self._max_zoom = 8.0
        self._current_zoom = 1.0

    def wheelEvent(self, event):
        factor = 1.1
        delta = event.angleDelta().y()
        if delta > 0:
            zoom = self._current_zoom * factor
            if zoom <= self._max_zoom:
                self._current_zoom = zoom
                self.scale(factor, factor)
        else:
            zoom = self._current_zoom / factor
            if zoom >= self._min_zoom:
                self._current_zoom = zoom
                self.scale(1/factor, 1/factor)

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, NodeItem):
            if item.node_type == "import_type":
                self._toggle_node(item, radius=160)
            elif item.node_type == "category":
                self._toggle_node(item, radius=120)
            elif item.node_type == "entry":
                self.entry_clicked.emit(item.data)
        super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, NodeItem):
                if item.node_type == "entry":
                    self.entry_clicked.emit(item.data)
                elif item.node_type == "category":
                    self.category_clicked.emit(item.label, len(item.children))
                elif item.node_type == "import_type":
                    self.category_clicked.emit(item.label, len(item.children))
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if not isinstance(item, NodeItem):
            return
        menu = QMenu()
        if item.node_type == "entry":
            show_a = QAction("Mostrar Vista Previa", menu)
            show_a.triggered.connect(lambda: self.entry_clicked.emit(item.data))
            menu.addAction(show_a)
            menu.addSeparator()
            edit_cat = QAction("Editar Categoría...", menu)
            edit_cat.triggered.connect(lambda: self._edit_entry_category(item))
            menu.addAction(edit_cat)
            delete_a = QAction("Eliminar Entrada", menu)
            delete_a.triggered.connect(lambda: self._delete_entry(item))
            menu.addAction(delete_a)
        elif item.node_type == "category":
            expand_a = QAction("Alternar Expansión", menu)
            expand_a.triggered.connect(lambda: self._toggle_node(item, radius=120))
            menu.addAction(expand_a)
        elif item.node_type == "import_type":
            expand_a = QAction("Alternar Expansión", menu)
            expand_a.triggered.connect(lambda: self._toggle_node(item, radius=160))
            menu.addAction(expand_a)
        menu.exec(event.globalPos())

    # ── Build the map ───────────────────────────────────────────────

    @staticmethod
    def _import_type(source: str) -> str:
        s = source.lower()
        if "google patent" in s or "patent" in s:
            return "Importación de Patentes"
        if "scanned book" in s or s.startswith("/"):
            return "Libros Escaneados"
        if "lathe trolls" in s or "forum" in s or "lathetrolls" in s:
            return "Duplicado del Foro"
        if source.endswith(".md") or "markdown" in s:
            return "Importación Markdown"
        if "whatsapp" in s:
            return "Importación de WhatsApp"
        return "Otras Fuentes"

    def build(self, entries, kb=None):
        self._kb = kb
        self._scene.clear()
        self._nodes.clear()
        self._edges.clear()
        self._import_nodes.clear()
        self._category_nodes.clear()
        self._root = None
        self._animating = False

        if not entries:
            txt = self._scene.addSimpleText(
                "¡No hay entradas — importa datos primero!",
                QFont("Segoe UI", 18))
            txt.setBrush(QBrush(QColor("#aaa")))
            txt.setPos(-150, -20)
            return

        # Group entries by import type, then by category
        groups: dict = {}
        for e in entries:
            imp = self._import_type(e.source)
            groups.setdefault(imp, {}).setdefault(e.category, []).append(e)

        import_types = list(groups.keys())

        # Root node
        root = NodeItem(
            f"📚 Base de Conocimiento",
            f"{len(entries)} entradas · {len(import_types)} fuentes",
            QColor("#1A237E"), "root")
        self._scene.addItem(root)
        root.setPos(0, 0)
        self._root = root
        self._nodes.append(root)

        # Import-type nodes in a circle
        n_imp = len(import_types)
        radius = 220 if n_imp <= 8 else 180 + n_imp * 20
        angle_step = 2 * math.pi / max(n_imp, 1)
        imp_colors = {
            "Importación de Patentes":    QColor("#1565C0"),
            "Libros Escaneados":    QColor("#E65100"),
            "Duplicado del Foro":     QColor("#2E7D32"),
            "Importación Markdown":  QColor("#6A1B9A"),
            "Importación de WhatsApp":  QColor("#00838F"),
            "Otras Fuentes":    QColor("#546E7A"),
        }

        for i, imp in enumerate(import_types):
            color = imp_colors.get(imp, QColor("#546E7A"))
            cat_counts = groups[imp]
            total = sum(len(v) for v in cat_counts.values())
            imp_node = NodeItem(
                f"{self._icon_for_import(imp)}{imp}",
                f"{total} entradas · {len(cat_counts)} categorías",
                color, "import_type")
            self._scene.addItem(imp_node)
            angle = i * angle_step - math.pi / 2
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            imp_node.setPos(x, y)
            imp_node._import_name = imp
            self._nodes.append(imp_node)
            self._import_nodes[imp] = imp_node

            edge = EdgeItem(root, imp_node, color.darker(120))
            self._scene.addItem(edge)
            self._edges.append(edge)

            # Category nodes under this import type (hidden)
            for j, (cat, cat_entries) in enumerate(cat_counts.items()):
                cat_color = _color_for(cat)
                cat_node = NodeItem(
                    f"{self._icon_for(cat)}{cat}",
                    f"{len(cat_entries)} entradas", cat_color, "category")
                self._scene.addItem(cat_node)
                cat_node.setVisible(False)
                cat_node._parent_import = imp
                self._nodes.append(cat_node)
                self._category_nodes.setdefault(imp, []).append(cat_node)
                imp_node.add_child(cat_node)

                c_edge = EdgeItem(imp_node, cat_node, cat_color.darker(120))
                self._scene.addItem(c_edge)
                c_edge.setVisible(False)
                self._edges.append(c_edge)

                # Entry nodes under this category (hidden)
                for k, entry in enumerate(cat_entries[:30]):
                    title = entry.title[:35] if entry.title else "(sin título)"
                    e_node = NodeItem(
                        title, "", cat_color.lighter(140), "entry", entry)
                    self._scene.addItem(e_node)
                    e_node.setVisible(False)
                    self._nodes.append(e_node)
                    cat_node.add_child(e_node)

                    e_edge = EdgeItem(cat_node, e_node,
                        QColor(cat_color.red(), cat_color.green(), cat_color.blue(), 40))
                    self._scene.addItem(e_edge)
                    e_edge.setVisible(False)
                    self._edges.append(e_edge)

        # Auto-fit after build (deferred so scene rect is calculated)
        QTimer.singleShot(100, self.fit_all)

        if self._kb:
            self._kb.save()

    def _icon_for_import(self, imp: str) -> str:
        icons = {
            "Importación de Patentes": "📜",
            "Libros Escaneados": "📖",
            "Duplicado del Foro": "💬",
            "Importación Markdown": "📁",
            "Importación de WhatsApp": "💬",
            "Otras Fuentes": "📄",
        }
        return icons.get(imp, "📄")

    def _icon_for(self, cat: str) -> str:
        icons = {
            "patent": "📜", "forum": "💬", "book": "📖",
            "general": "📄", "correction": "🔧", "paper": "📝",
            "article": "📰",
        }
        return icons.get(cat.lower(), "📄")

    # ── Toggle expand/collapse ─────────────────────────────────────

    def _toggle_node(self, node: NodeItem, radius=130):
        if self._animating:
            return
        node.expanded = not node.expanded
        children = node.children
        if not children:
            return

        self._animating = True
        angle_step = 2 * math.pi / max(len(children), 1)
        anims = QParallelAnimationGroup()

        for j, child in enumerate(children):
            child.setVisible(True)
            angle = j * angle_step - math.pi / 2
            tx = node.pos().x() + radius * math.cos(angle)
            ty = node.pos().y() + radius * math.sin(angle)

            if node.expanded:
                target = QPointF(tx, ty)
            else:
                target = node.pos()

            anim = QPropertyAnimation(child, b"pos")
            anim.setDuration(400)
            anim.setStartValue(child.pos())
            anim.setEndValue(target)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anims.addAnimation(anim)

            for edge in self._edges:
                if edge._source == node and edge._dest == child:
                    edge.setVisible(node.expanded)

        def _done():
            self._animating = False
            if not node.expanded:
                for child in children:
                    child.setVisible(False)

        anims.finished.connect(_done)
        anims.start()

    # ── Actions ─────────────────────────────────────────────────────

    def _edit_entry_category(self, node: NodeItem):
        entry = node.data
        if not entry:
            return
        new_cat, ok = QInputDialog.getText(
            self, "Editar Categoría",
            f"Categoría actual: {entry.category}\nNueva categoría:",
            text=entry.category)
        if ok and new_cat:
            entry.category = new_cat.strip()
            self.rebuild_requested.emit()

    def _delete_entry(self, node: NodeItem):
        entry = node.data
        if not entry:
            return
        reply = QMessageBox.question(
            self, "Eliminar Entrada",
            f"¿Eliminar '{entry.title[:60]}'?",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self._kb and entry in self._kb.entries:
                self._kb.entries.remove(entry)
                self.rebuild_requested.emit()

    def fit_all(self):
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
        self._current_zoom = 1.0

    def focus_category(self, cat_name: str):
        for nodes in self._category_nodes.values():
            for node in nodes:
                if node.label == cat_name:
                    self.centerOn(node)
                    return
