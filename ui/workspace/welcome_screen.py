from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen, QBrush
from core.translations import T


class SectionCard(QFrame):
    clicked = Signal(int)

    def __init__(self, icon: str, title: str, description: str, features: list, tab_index: int, color: str):
        super().__init__()
        self.tab_index = tab_index
        self.title_key = title
        self.desc_key = description
        self.feature_keys = list(features)
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
        self.icon_label = QLabel(icon)
        icon_font = QFont()
        icon_font.setPointSize(32)
        self.icon_label.setFont(icon_font)
        header.addWidget(self.icon_label)
        header.addStretch()
        layout.addLayout(header)

        self.title_label = QLabel(T(title))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: white;")
        layout.addWidget(self.title_label)

        self.desc_label = QLabel(T(description))
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px;")
        layout.addWidget(self.desc_label)

        layout.addStretch()

        self.feat_labels = []
        for feat in self.feature_keys:
            feat_label = QLabel(f"  ✓  {T(feat)}")
            feat_label.setStyleSheet("color: rgba(255,255,255,0.9); font-size: 11px;")
            layout.addWidget(feat_label)
            self.feat_labels.append(feat_label)

        self.hint = QLabel(T("🖱️ Haz clic para abrir"))
        self.hint.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 10px; font-style: italic;")
        self.hint.setAlignment(Qt.AlignRight)
        layout.addWidget(self.hint)

        # All child clicks must pass through to the card
        for child in self.findChildren(QLabel):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def retranslate(self):
        self.title_label.setText(T(self.title_key))
        self.desc_label.setText(T(self.desc_key))
        for label, key in zip(self.feat_labels, self.feature_keys):
            label.setText(f"  ✓  {T(key)}")
        self.hint.setText(T("🖱️ Haz clic para abrir"))

    def mousePressEvent(self, event):
        self.clicked.emit(self.tab_index)
        super().mousePressEvent(event)


class StatusIndicator(QFrame):
    def __init__(self, icon: str, label: str, status: str, status_color: str):
        super().__init__()
        self.label_key = label
        self.setStyleSheet("background: rgba(255,255,255,0.08); border-radius: 8px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setStyleSheet("font-size: 18px;")
        layout.addWidget(self.icon_lbl)
        self.text = QLabel(T(label))
        self.text.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.text)
        layout.addStretch()
        self.status_lbl = QLabel(status)
        self.status_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {status_color};")
        layout.addWidget(self.status_lbl)

    def retranslate(self):
        self.text.setText(T(self.label_key))


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
        self.header = QLabel(T("🏭  Lacquer Analyzer"))
        hf = QFont()
        hf.setPointSize(28)
        hf.setBold(True)
        self.header.setFont(hf)
        self.header.setStyleSheet("color: white;")
        main_layout.addWidget(self.header)

        self.subtitle = QLabel(T("Plataforma integral para formulación, análisis y control de calidad de lacas de corte"))
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 14px;")
        main_layout.addWidget(self.subtitle)

        # ── Quick status bar ──
        status_row = QHBoxLayout()
        status_row.setSpacing(12)
        status_items = [
            ("🧪", "Ingredientes en BD", "—", "#aaa"),
            ("📋", "Recetas cargadas", "—", "#aaa"),
            ("🧠", "Base de Conocimiento", "—", "#aaa"),
            ("🔗", "LLM", "No verificado", "#ff9800"),
        ]
        self.status_indicators = []
        for icon, label, status, color in status_items:
            s = StatusIndicator(icon, label, status, color)
            self.status_indicators.append(s)
            status_row.addWidget(s)
        main_layout.addLayout(status_row)

        main_layout.addSpacing(12)

        # ── Section cards grid ──
        self.grid_label = QLabel(T("Módulos del sistema"))
        gf = QFont()
        gf.setPointSize(14)
        gf.setBold(True)
        self.grid_label.setFont(gf)
        self.grid_label.setStyleSheet("color: rgba(255,255,255,0.9);")
        main_layout.addWidget(self.grid_label)

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

        self.cards = cards
        grid = QGridLayout()
        grid.setSpacing(16)
        for i, card in enumerate(cards):
            row, col = divmod(i, 3)
            card.clicked.connect(self._on_card_clicked)
            grid.addWidget(card, row, col)
        main_layout.addLayout(grid)

        main_layout.addStretch()

        # ── Footer ──
        self.footer = QLabel(T(
            "💡 Pasa el ratón sobre cualquier elemento para ver ayuda  ·  "
            "Usa el menú Ayuda → Guía de uso para una explicación detallada  ·  "
            "Selecciona 🇪🇸/🇬🇧 en la barra para cambiar idioma"
        ))
        self.footer.setWordWrap(True)
        self.footer.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 11px;")
        self.footer.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.footer)

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def retranslate(self):
        self.header.setText(T("🏭  Lacquer Analyzer"))
        self.subtitle.setText(T("Plataforma integral para formulación, análisis y control de calidad de lacas de corte"))
        self.grid_label.setText(T("Módulos del sistema"))
        self.footer.setText(T(
            "💡 Pasa el ratón sobre cualquier elemento para ver ayuda  ·  "
            "Usa el menú Ayuda → Guía de uso para una explicación detallada  ·  "
            "Selecciona 🇪🇸/🇬🇧 en la barra para cambiar idioma"
        ))
        for card in self.cards:
            card.retranslate()
        for s in self.status_indicators:
            s.retranslate()

    def _on_card_clicked(self, tab_index: int):
        self.navigate_requested.emit(tab_index)

    def update_status(self, status_data: dict):
        """Update status indicators: {'ingredients': N, 'recipes': N, 'kb': N, 'llm': str}
        The llm value should be 'connected', 'checking' or 'offline'."""
        status_map = {
            'ingredients': 0,
            'recipes': 1,
            'kb': 2,
            'llm': 3,
        }
        for key, idx in status_map.items():
            if key not in status_data:
                continue
            s = self.status_indicators[idx]
            if key == 'llm':
                state = status_data[key]
                if state == 'connected':
                    s.status_lbl.setText(T("Conectado"))
                    s.status_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #4CAF50;")
                elif state == 'checking':
                    s.status_lbl.setText(T("Verificando..."))
                    s.status_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #ff9800;")
                else:
                    s.status_lbl.setText(T("Desconectado"))
                    s.status_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #f44336;")
            else:
                value = status_data[key]
                s.status_lbl.setText(str(value))
                s.status_lbl.setStyleSheet(
                    "font-size: 13px; font-weight: bold; color: #4CAF50;" if value and value != "—"
                    else "font-size: 13px; font-weight: bold; color: #ff9800;")
