from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen, QBrush


class SectionCard(QFrame):
    clicked = Signal(int)

    def __init__(self, icon: str, title: str, description: str, features: list, tab_index: int, color: str):
        super().__init__()
        self.tab_index = tab_index
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            SectionCard {{
                background-color: {color};
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            SectionCard:hover {{
                border: 2px solid white;
                background-color: {color};
            }}
        """)
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        header = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_font = QFont()
        icon_font.setPointSize(32)
        icon_label.setFont(icon_font)
        header.addWidget(icon_label)
        header.addStretch()
        layout.addLayout(header)

        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white;")
        layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px;")
        layout.addWidget(desc_label)

        layout.addStretch()

        for feat in features:
            feat_label = QLabel(f"  ✓  {feat}")
            feat_label.setStyleSheet("color: rgba(255,255,255,0.9); font-size: 11px;")
            layout.addWidget(feat_label)

        hint = QLabel("🖱️ Haz clic para abrir")
        hint.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 10px; font-style: italic;")
        hint.setAlignment(Qt.AlignRight)
        layout.addWidget(hint)

        # All child clicks must pass through to the card
        for child in self.findChildren(QLabel):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def mousePressEvent(self, event):
        self.clicked.emit(self.tab_index)
        super().mousePressEvent(event)


class StatusIndicator(QFrame):
    def __init__(self, icon: str, label: str, status: str, status_color: str):
        super().__init__()
        self.setStyleSheet("background: rgba(255,255,255,0.08); border-radius: 8px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 18px;")
        layout.addWidget(icon_lbl)
        text = QLabel(label)
        text.setStyleSheet("font-size: 12px;")
        layout.addWidget(text)
        layout.addStretch()
        status_lbl = QLabel(status)
        status_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {status_color};")
        layout.addWidget(status_lbl)


class WelcomeScreen(QWidget):
    navigate_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0b1a3a, stop:1 #1a2a5a);")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(40, 30, 40, 40)
        main_layout.setSpacing(16)

        # ── Header ──
        header = QLabel("🏭  Lacquer Analyzer")
        hf = QFont()
        hf.setPointSize(28)
        hf.setBold(True)
        header.setFont(hf)
        header.setStyleSheet("color: white;")
        main_layout.addWidget(header)

        subtitle = QLabel("Plataforma integral para formulación, análisis y control de calidad de lacas de corte")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 14px;")
        main_layout.addWidget(subtitle)

        # ── Quick status bar ──
        status_row = QHBoxLayout()
        status_row.setSpacing(12)
        status_items = [
            ("🧪", "Ingredientes en BD", "—", "#aaa"),
            ("📋", "Recetas cargadas", "—", "#aaa"),
            ("🧠", "Base de Conocimiento", "—", "#aaa"),
            ("🔗", "LLM", "No verificado", "#ff9800"),
        ]
        for icon, label, status, color in status_items:
            s = StatusIndicator(icon, label, status, color)
            status_row.addWidget(s)
        main_layout.addLayout(status_row)

        main_layout.addSpacing(12)

        # ── Section cards grid ──
        grid_label = QLabel("Módulos del sistema")
        gf = QFont()
        gf.setPointSize(14)
        gf.setBold(True)
        grid_label.setFont(gf)
        grid_label.setStyleSheet("color: rgba(255,255,255,0.9);")
        main_layout.addWidget(grid_label)

        cards = [
            SectionCard(
                "🧪", "Formulación de Laca",
                "Crea, analiza y optimiza recetas de laca. Busca ingredientes, "
                "ejecuta análisis físico-químico completo y compara variantes lado a lado.",
                ["Editor de recetas con tabla de componentes", "Análisis: viscosidad, evaporación, defectos, mojado",
                 "Comparador de recetas lado a lado", "Búsqueda multi-fuente (PubChem, Wikipedia, SpecialChem)"],
                1, "#1a3a6a"
            ),
            SectionCard(
                "🚀", "Mejorador de Fórmulas (Enhancer)",
                "Potencia tus formulaciones con análisis inteligente. "
                "Recibe sugerencias de optimización basadas en propiedades objetivo.",
                ["Análisis de compatibilidad Hansen", "Puntuación global 0-100 con desglose",
                 "Sugerencias de modificación automáticas", "Traducción de advertencias con LLM"],
                1, "#1a5a3a"
            ),
            SectionCard(
                "🔧", "Solucionador de Problemas",
                "Diagnostica y resuelve defectos de formulación con la ayuda "
                "de la base de conocimiento y el LLM.",
                ["Base de datos de defectos por etapa del proceso", "Buscador con filtros por severidad y etapa",
                 "P&R con LLM sobre causas y soluciones", "Referencias del foro Lathe Trolls"],
                4, "#5a3a1a"
            ),
            SectionCard(
                "⚡", "Galvanoplastia",
                "Configura y optimiza baños galvánicos de plata y níquel sulfamato "
                "para procesos de electroformado.",
                ["Parámetros de baño: temperatura, pH, densidad de corriente", "Matriz de compatibilidad de solventes",
                 "Guías de prevención de defectos galvánicos", "P&R especializado en galvanoplastia"],
                2, "#3a1a5a"
            ),
            SectionCard(
                "🔄", "Prensado",
                "Gestiona parámetros de prensado, especificaciones de disco y "
                "lleva el registro histórico de producción.",
                ["Temperatura, presión y tiempos de prensado/enfriamiento", "Especificaciones: tamaño, grosor, peso",
                 "Registro de producción con historial", "Referencias de defectos de prensado"],
                3, "#1a3a5a"
            ),
            SectionCard(
                "🧠", "RAG & Base de Conocimiento",
                "Construye y consulta tu base de conocimiento con RAG. "
                "Importa datos del foro, PDFs, patentes y haz preguntas con LLM.",
                ["Importación multi-fuente (foro, PDF, Wikipedia, PubChem)", "Pipeline RAG completo con fragmentación",
                 "Q&A inteligente con contexto recuperado", "Explorador de datos con mapa mental"],
                5, "#2a4a3a"
            ),
        ]

        grid = QGridLayout()
        grid.setSpacing(16)
        for i, card in enumerate(cards):
            row, col = divmod(i, 3)
            card.clicked.connect(self._on_card_clicked)
            grid.addWidget(card, row, col)
        main_layout.addLayout(grid)

        main_layout.addStretch()

        # ── Footer ──
        footer = QLabel(
            "💡 Pasa el ratón sobre cualquier elemento para ver ayuda  ·  "
            "Usa el menú Ayuda → Guía de uso para una explicación detallada  ·  "
            "Selecciona 🇪🇸/🇬🇧 en la barra para cambiar idioma"
        )
        footer.setWordWrap(True)
        footer.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 11px;")
        footer.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(footer)

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _on_card_clicked(self, tab_index: int):
        self.navigate_requested.emit(tab_index)

    def update_status(self, status_data: dict):
        """Update status indicators: {'ingredients': N, 'recipes': N, 'kb': N, 'llm': str}"""
        pass  # TODO wire up with actual data
