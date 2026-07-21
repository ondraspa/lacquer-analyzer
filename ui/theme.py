DARK_THEME = """
/* ── Global ── */
QMainWindow, QWidget {
    background-color: #0d1b3a;
    color: #e0e0e0;
    font-size: 13px;
}

/* ── Toolbar ── */
QToolBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0b1a3a, stop:1 #1a2a5a);
    border: none;
    border-bottom: 1px solid #2a3a6a;
    spacing: 6px;
    padding: 4px;
}
QToolBar QPushButton {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 6px;
    padding: 6px 14px;
    color: #e0e0e0;
    font-size: 12px;
}
QToolBar QPushButton:hover {
    background: rgba(255,255,255,0.15);
    border-color: rgba(255,255,255,0.3);
}
QToolBar QPushButton:pressed {
    background: rgba(255,255,255,0.05);
}
QToolBar QLabel {
    color: #c0c0c0;
}
QToolBar QComboBox {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 4px;
    padding: 4px 8px;
    color: #e0e0e0;
    min-width: 60px;
}
QToolBar QComboBox::drop-down {
    border: none;
    width: 20px;
}

/* ── Menu Bar ── */
QMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0b1a3a, stop:1 #1a2a5a);
    border: none;
    color: #c0c0c0;
    padding: 2px;
}
QMenuBar::item {
    padding: 4px 12px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background: rgba(255,255,255,0.12);
}
QMenu {
    background: #121e3e;
    border: 1px solid #2a3a6a;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px 6px 16px;
    border-radius: 4px;
    color: #e0e0e0;
}
QMenu::item:selected {
    background: #1a3a6a;
}
QMenu::separator {
    height: 1px;
    background: #2a3a6a;
    margin: 4px 8px;
}

/* ── Status Bar ── */
QStatusBar {
    background: #0b1a3a;
    border-top: 1px solid #2a3a6a;
    color: #a0a0a0;
    font-size: 12px;
}

/* ── Tab Widget ── */
QTabWidget::pane {
    border: none;
    background: transparent;
}
QTabBar::tab {
    background: rgba(255,255,255,0.05);
    border: 1px solid transparent;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 18px;
    margin-right: 2px;
    color: #888;
    font-size: 12px;
}
QTabBar::tab:selected {
    background: #0d1b3a;
    border-color: #2a3a6a;
    color: #fff;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    background: rgba(255,255,255,0.08);
    color: #ccc;
}

/* ── Group Box ── */
QGroupBox {
    background: rgba(255,255,255,0.04);
    border: 1px solid #2a3a6a;
    border-radius: 8px;
    margin-top: 14px;
    padding: 16px 12px 12px 12px;
    font-weight: bold;
    color: #d0d0d0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    background: #1a2a5a;
    border-radius: 4px;
    color: #e0e0e0;
}

/* ── Buttons ── */
QPushButton {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 6px;
    padding: 6px 16px;
    color: #e0e0e0;
    font-size: 12px;
}
QPushButton:hover {
    background: rgba(255,255,255,0.14);
    border-color: rgba(255,255,255,0.3);
}
QPushButton:pressed {
    background: rgba(255,255,255,0.05);
}
QPushButton:disabled {
    background: rgba(255,255,255,0.03);
    color: #555;
    border-color: rgba(255,255,255,0.05);
}

/* ── Inputs ── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background: rgba(0,0,0,0.25);
    border: 1px solid #2a3a6a;
    border-radius: 5px;
    padding: 4px 8px;
    color: #e0e0e0;
    selection-background-color: #1a4a8a;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #4a7aaa;
}

/* ── Spin Boxes ── */
QDoubleSpinBox, QSpinBox {
    background: rgba(0,0,0,0.25);
    border: 1px solid #2a3a6a;
    border-radius: 5px;
    padding: 3px 6px;
    color: #e0e0e0;
    min-height: 22px;
}
QDoubleSpinBox:focus, QSpinBox:focus {
    border-color: #4a7aaa;
}
QDoubleSpinBox::up-button, QSpinBox::up-button,
QDoubleSpinBox::down-button, QSpinBox::down-button {
    border: none;
    background: rgba(255,255,255,0.08);
    width: 18px;
}
QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover,
QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {
    background: rgba(255,255,255,0.15);
}

/* ── Combo Box ── */
QComboBox {
    background: rgba(0,0,0,0.25);
    border: 1px solid #2a3a6a;
    border-radius: 5px;
    padding: 4px 8px;
    color: #e0e0e0;
    min-height: 22px;
}
QComboBox:hover {
    border-color: #4a7aaa;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QComboBox::down-arrow {
    image: none;
    border: none;
}
QComboBox QAbstractItemView {
    background: #121e3e;
    border: 1px solid #2a3a6a;
    border-radius: 4px;
    color: #e0e0e0;
    selection-background-color: #1a3a6a;
    outline: none;
}

/* ── Check Box ── */
QCheckBox {
    color: #e0e0e0;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #4a6a9a;
    border-radius: 3px;
    background: rgba(0,0,0,0.3);
}
QCheckBox::indicator:checked {
    background: #2a5a9a;
    border-color: #4a8aba;
}
QCheckBox::indicator:hover {
    border-color: #6a9aba;
}

/* ── Progress Bar ── */
QProgressBar {
    background: rgba(0,0,0,0.3);
    border: 1px solid #2a3a6a;
    border-radius: 4px;
    text-align: center;
    color: #e0e0e0;
    font-size: 11px;
    min-height: 18px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2a5a9a, stop:1 #4a8aba);
    border-radius: 3px;
}

/* ── List / Tree / Table ── */
QListWidget, QTreeWidget, QTableWidget {
    background: rgba(0,0,0,0.2);
    border: 1px solid #2a3a6a;
    border-radius: 6px;
    color: #e0e0e0;
    outline: none;
    selection-background-color: #1a3a6a;
    selection-color: #fff;
}
QListWidget::item, QTreeWidget::item, QTableWidget::item {
    padding: 4px 6px;
    border-radius: 3px;
}
QListWidget::item:hover, QTreeWidget::item:hover, QTableWidget::item:hover {
    background: rgba(255,255,255,0.05);
}
QHeaderView::section {
    background: #1a2a5a;
    border: none;
    border-right: 1px solid #2a3a6a;
    border-bottom: 1px solid #2a3a6a;
    padding: 6px 8px;
    color: #c0c0c0;
    font-weight: bold;
    font-size: 11px;
}

/* ── Scroll Bars ── */
QScrollBar:vertical {
    background: rgba(0,0,0,0.15);
    width: 10px;
    border-radius: 5px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.15);
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(255,255,255,0.25);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: rgba(0,0,0,0.15);
    height: 10px;
    border-radius: 5px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: rgba(255,255,255,0.15);
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(255,255,255,0.25);
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Splitter ── */
QSplitter::handle {
    background: #2a3a6a;
    width: 2px;
    height: 2px;
}
QSplitter::handle:hover {
    background: #4a7aaa;
}

/* ── Dialog ── */
QDialog {
    background: #0d1b3a;
    color: #e0e0e0;
}

/* ── Tooltip ── */
QToolTip {
    background: #1a2a5a;
    border: 1px solid #4a7aaa;
    border-radius: 5px;
    padding: 6px 10px;
    color: #e0e0e0;
    font-size: 12px;
}

/* ── Scroll Area ── */
QScrollArea {
    background: transparent;
    border: none;
}
"""
