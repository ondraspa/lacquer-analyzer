"""Sistema de traducción EN/ES para toda la aplicación.

Uso:
  from core.translations import T, translator

  # Texto estático en cualquier widget — usa la cadena original como clave:
  label = QLabel(T("Guardar"))

  # Conectar al cambio de idioma para refrescar la UI:
  translator.language_changed.connect(self._retranslate_ui)
"""

import os
from typing import Dict, Optional
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QComboBox, QGroupBox, QTabWidget


class Translator(QObject):
    language_changed = Signal(str)

    _instance: Optional["Translator"] = None

    def __init__(self):
        super().__init__()
        self._current_lang: str = "es"
        self._strings: Dict[str, Dict[str, str]] = {}
        self._load()

    @classmethod
    def instance(cls) -> "Translator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self):
        self._strings = self._BUILD_DICT()

    @property
    def current_language(self) -> str:
        return self._current_lang

    def set_language(self, lang: str):
        if lang not in ("en", "es"):
            return
        self._current_lang = lang
        self.language_changed.emit(lang)

    def get(self, key: str) -> str:
        if self._current_lang == "es":
            return key
        entry = self._strings.get(key)
        if entry is None:
            return key
        return entry.get("en", key)

    def get_all(self, key: str) -> Dict[str, str]:
        entry = self._strings.get(key)
        if entry is None:
            return {"es": key, "en": key}
        return {"es": key, "en": entry.get("en", key)}

    def translate_with_llm(self, text: str, target_lang: str, llm_client) -> str:
        if not text.strip():
            return text
        lang_name = "Spanish" if target_lang == "es" else "English"
        prompt = (
            f"Translate the following text to {lang_name}. "
            f"Preserve all formatting, emoji, and technical terms exactly.\n\n"
            f"---\n{text}\n---"
        )
        try:
            result = llm_client.ask(question=prompt, max_tokens=2048, temperature=0.1)
            return result.strip()
        except Exception:
            return text

    def retranslate_widget(self, widget: QWidget):
        """Recursively refreshes text on a widget subtree using stored originals."""
        if hasattr(widget, '_tr_originals'):
            for attr, orig in widget._tr_originals.items():
                if hasattr(widget, attr):
                    if isinstance(getattr(widget, attr), (QLabel, QPushButton)):
                        getattr(widget, attr).setText(self.get(orig))
        for child in widget.findChildren(QWidget):
            self.retranslate_widget(child)

    def _BUILD_DICT(self) -> Dict[str, Dict[str, str]]:
        """Build translation dictionary keyed by Spanish string."""
        d = {}

        def _(es: str, en: str):
            d[es] = {"en": en}

        # ── General / Menus ──
        _("Archivo", "File")
        _("Herramientas", "Tools")
        _("Ayuda", "Help")
        _("Guardar", "Save")
        _("Cancelar", "Cancel")
        _("Cerrar", "Close")
        _("Eliminar", "Delete")
        _("Buscar", "Search")
        _("Añadir", "Add")
        _("Quitar", "Remove")
        _("Limpiar", "Clear")
        _("Salir", "Exit")
        _("Nombre:", "Name:")
        _("Tipo", "Type")
        _("Notas", "Notes")
        _("Advertencia", "Warning")
        _("Error", "Error")
        _("Idioma", "Language")
        _("Traducir", "Translate")
        _("Importar Receta (JSON/YAML)", "Import Recipe (JSON/YAML)")
        _("Exportar Receta", "Export Recipe")
        _("Importar Datos...", "Import Data...")
        _("Notas de Experto...", "Expert Notes...")
        _("Editor de Ingredientes...", "Ingredient Editor...")
        _("Editor de Reglas de Galvánica...", "Galvanic Rules Editor...")
        _("Editor de Defectos...", "Defect Editor...")
        _("Generar Formulación desde Especificación...", "Generate Formulation from Specification...")
        _("Configuración RAG...", "RAG Settings...")
        _("Acerca de", "About")
        _("📖 Guía de uso", "📖 Usage Guide")
        _("Listo", "Ready")
        _("Análisis completo", "Analysis complete")
        _("Traduciendo...", "Translating...")
        _("LLM: verificar", "LLM: check")
        _("BC: vacía", "KB: empty")
        _("Notas de Experto", "Expert Notes")
        _("Configuración RAG", "RAG Settings")
        _("Generar Receta", "Generate Recipe")
        _("Confirmar", "Confirm")
        _("Sí", "Yes")
        _("No", "No")

        # ── Main tabs ──
        _("🏠 Inicio", "🏠 Home")
        _("🧪 Formulación", "🧪 Formulation")
        _("⚡ Galvánica", "⚡ Galvanics")
        _("🔄 Prensado", "🔄 Pressing")
        _("🔍 Control de Calidad", "🔍 Quality Control")
        _("🧠 Conocimiento", "🧠 Knowledge")

        # ── Toolbar tooltips ──
        _("Verifica la conexión con el servidor LLM (LM Studio). Muestra el estado en el botón", "Check LLM server connection (LM Studio). Shows status on the button")
        _("Abre el navegador de la base de conocimiento: busca, navega y gestiona entradas", "Open knowledge base browser: search, navigate and manage entries")
        _("Abre el bloc de notas de experto: temas de referencia y notas personales", "Open expert notebook: reference topics and personal notes")
        _("Configura el pipeline RAG: conexión LLM, generación, recuperación y agentes", "Configure RAG pipeline: LLM connection, generation, retrieval and agents")
        _("Genera una formulación automática a partir de especificaciones (viscosidad, sólidos, curado)", "Generate automatic formulation from specifications (viscosity, solids, cure)")
        _("Cambia el idioma de la interfaz entre Español e Inglés", "Switch interface language between Spanish and English")

        # ── Cutting stage ──
        _("🧪 Formulación de Laca — Ingredientes, Recetas y Análisis", "🧪 Lacquer Formulation — Ingredients, Recipes & Analysis")
        _("BD de Ingredientes", "Ingredient DB")
        _("Pigmentos y Solventes", "Pigments & Solvents")
        _("SpecialChem", "SpecialChem")
        _("Editor de Recetas", "Recipe Editor")

        # ── Pigment Search ──
        _("Base de datos de pigmentos", "Pigment database")
        _("Limpiar", "Clear")
        _("Añadir a la receta", "Add to recipe")
        _("Buscar pigmento (nombre comercial, C.I., clase)...", "Search pigment (trade name, C.I., class)...")

        # ── SpecialChem Search ──
        _("Búsqueda Multi-Fuente", "Multi-Source Search")
        _("🔑 Configurar cookies de SpecialChem", "🔑 Set up SpecialChem cookies")
        _("🔄 Renovar cookies", "🔄 Renew cookies")
        _("Buscar", "Search")
        _("Añadir a la Receta", "Add to Recipe")
        _("Nombre comercial, químico o pigmento...", "Trade name, chemical or pigment...")
        _("Sin resultados en ninguna fuente.", "No results from any source.")

        # ── Recipe Editor ──
        _("Información de la Receta", "Recipe Information")
        _("Predefinidas:", "Presets:")
        _("Viscosidad Objetivo:", "Target Viscosity:")
        _("Sólidos Objetivo:", "Target Solids:")
        _("Añadir Componente", "Add Component")
        _("Quitar Seleccionado", "Remove Selected")
        _("Limpiar Todo", "Clear All")
        _("Guardar como Preset", "Save as Preset")
        _("Guardar como Preset Personalizado", "Save as Custom Preset")
        _("Concentración %", "Concentration %")
        _("Máx %", "Max %")
        _("Componentes", "Components")
        _("Análisis de Laca", "Lacquer Analysis")
        _("Comparar Recetas", "Compare Recipes")
        _("Receta sin Título", "Untitled Recipe")
        _("Nombre de la receta", "Recipe name")
        _("Ejecutar Análisis Completo", "Run Full Analysis")
        _("Aún no se ha definido ninguna receta", "No recipe has been defined yet")
        _("Receta guardada", "Recipe saved")
        _("No hay receta para guardar", "No recipe to save")

        # ── Metadata tab ──
        _("Pros/Contras & Hardware", "Pros/Cons & Hardware")
        _("Traducir metadatos", "Translate metadata")
        _("MEJOR PARA:", "BEST FOR:")
        _("VENTAJAS:", "ADVANTAGES:")
        _("DESVENTAJAS:", "DISADVANTAGES:")
        _("HARDWARE RECOMENDADO:", "RECOMMENDED HARDWARE:")
        _("PROBLEMAS COMUNES Y SOLUCIONES:", "COMMON ISSUES & SOLUTIONS:")

        # ── Ingredient Browser ──
        _("Filtrar ingredientes...", "Filter ingredients...")
        _("Todos los Tipos", "All Types")
        _("Editar Seleccionado", "Edit Selected")
        _("Añadir Nuevo Ingrediente", "Add New Ingredient")
        _("Detalles del Ingrediente", "Ingredient Details")

        # ── Ingredient Editor ──
        _("Editor de Ingredientes", "Ingredient Editor")
        _("Añadir Ingrediente", "Add Ingredient")
        _("Editar Ingrediente", "Edit Ingredient")
        _("Información Básica", "Basic Information")
        _("Propiedades del Recubrimiento", "Coating Properties")
        _("Advertencias", "Warnings")
        _("Sólidos %", "Solids %")
        _("Viscosidad (mPa·s)", "Viscosity (mPa·s)")
        _("Concentración Máx %", "Max Concentration %")
        _("Dosificación %", "Dosage %")
        _("Densidad (g/cm³)", "Density (g/cm³)")
        _("Índice de Evaporación", "Evaporation Rate")
        _("Punto de Ebullición (°C)", "Boiling Point (°C)")
        _("Tensión Superficial (dynes/cm)", "Surface Tension (dynes/cm)")

        # ── Analysis Input ──
        _("Temperatura ambiente:", "Ambient Temperature:")
        _("Humedad relativa:", "Relative Humidity:")
        _("Espesor capa laca:", "Lacquer Layer Thickness:")
        _("Grano pulido disco:", "Disk Polish Grain:")
        _("Flujo de aire:", "Air Flow:")
        _("Aplicación:", "Application:")
        _("Cámara de presión positiva", "Positive Pressure Chamber")
        _("°C", "°C")
        _("%", "%")
        _("µm", "µm")
        _("m/s", "m/s")

        # ── Analysis Results ──
        _("Viscosidad & Película", "Viscosity & Film")
        _("Evaporación", "Evaporation")
        _("Defectos", "Defects")
        _("Mojado & Hansen", "Wetting & Hansen")
        _("Viscosidad predicha:", "Predicted Viscosity:")
        _("Categoría:", "Category:")
        _("Ford Cup #4:", "Ford Cup #4:")
        _("Sólidos vol.:", "Solids vol.:")
        _("Tg final:", "Final Tg:")
        _("Dureza:", "Hardness:")
        _("Flexibilidad:", "Flexibility:")
        _("Tiempo de secado estimado:", "Estimated Drying Time:")
        _("Atrapamiento de Burbujas", "Bubble Trapping")
        _("Blush (Blanqueamiento)", "Blush Risk")
        _("Orange Peel (Piel de Naranja)", "Orange Peel")
        _("Riesgo:", "Risk:")
        _("Tensión superficial:", "Surface Tension:")
        _("Mojado:", "Wetting:")
        _("Hansen dist. (RED):", "Hansen dist. (RED):")
        _("Compatible con NC:", "Compatible with NC:")
        _("Puntuación global:", "Global Score:")
        _("Advertencias:", "Warnings:")
        _("Sin advertencias — receta equilibrada", "No warnings — balanced recipe")
        _("Espesor máx sin burbujas:", "Max no-bubble thickness:")
        _("Punto de rocío", "Dew point")
        _("Enfriamiento superficial", "Surface cooling")

        # ── Comparison ──
        _("— Receta A —", "— Recipe A —")
        _("— Receta B —", "— Recipe B —")
        _("Comparar", "Compare")
        _("Composición", "Composition")
        _("Propiedades", "Properties")
        _("Componente", "Component")
        _("Receta A (%)", "Recipe A (%)")
        _("Receta B (%)", "Recipe B (%)")
        _("Diferencia", "Difference")
        _("Propiedad", "Property")

        # ── Troubleshooting ──
        _("🔍 Solución de problemas — {stage}", "🔍 Troubleshooting — {stage}")
        _("Buscar defecto...", "Search defect...")
        _("Todas las Etapas", "All Stages")
        _("Defecto", "Defect")
        _("Severidad", "Severity")
        _("Síntomas", "Symptoms")
        _("Causas", "Causes")
        _("Soluciones", "Solutions")
        _("Referencias del Foro", "Forum References")
        _("Sin selección", "No selection")

        # ── Knowledge QA ──
        _("💡 Base de conocimiento y Q&A con LLM — {stage}", "💡 Knowledge base & LLM Q&A — {stage}")
        _("Preguntar al LLM", "Ask LLM")
        _("Configuración", "Settings")
        _("Actualizar BC", "Refresh KB")
        _("Inspeccionar contexto RAG", "Inspect RAG context")
        _("Escribe tu pregunta...", "Type your question...")
        _("Conectado", "Connected")
        _("Desconectado", "Disconnected")
        _("Verificando...", "Checking...")
        _("Flujo de trabajo", "Workflow")
        _("Siguiente paso →", "Next step →")

        # ── Galvanics ──
        _("⚡ Galvánica — Metalizado y Baños Electrolíticos", "⚡ Galvanics — Metallizing & Electrolytic Baths")
        _("Parámetros de Baño", "Bath Parameters")
        _("Baño de Plata (Plateado)", "Silver Bath (Plating)")
        _("Baño de Plata", "Silver Bath")
        _("Baño de Sulfamato de Níquel", "Nickel Sulfamate Bath")
        _("Preparación de Superficie", "Surface Preparation")
        _("Temperatura:", "Temperature:")
        _("pH:", "pH:")
        _("Densidad de corriente:", "Current Density:")
        _("Tiempo:", "Time:")
        _("Grosor objetivo:", "Target Thickness:")
        _("Método:", "Method:")
        _("Ciclos de enjuague:", "Rinse Cycles:")
        _(" °C", " °C")
        _(" A/dm²", " A/dm²")
        _(" s", " s")
        _(" μm", " μm")
        _(" min", " min")
        _("A/dm²", "A/dm²")
        _("Galvánica", "Galvanics")
        _("Compatibilidad y Prevención", "Compatibility & Prevention")
        _("P&R — Galvánica", "Q&A — Galvanics")
        _("Desengrase alcalino", "Alkaline degreasing")
        _("Desengrase ácido", "Acid degreasing")
        _("Limpieza por plasma", "Plasma cleaning")
        _("Activación ácida (H₂SO₄ 10%)", "Acid activation (H₂SO₄ 10%)")
        _("Temperatura del baño de plata en °C. Rango típico: 40-60°C", "Silver bath temperature in °C. Typical range: 40-60°C")
        _("pH del baño de plata. Rango típico: 8.5-9.5", "Silver bath pH. Typical range: 8.5-9.5")
        _("Densidad de corriente del baño de plata en A/dm²", "Silver bath current density in A/dm²")
        _("Tiempo de inmersión en el baño de plata en minutos", "Silver bath immersion time in minutes")
        _("Temperatura del baño de níquel sulfamato en °C. Rango típico: 40-60°C", "Nickel sulfamate bath temperature in °C. Typical range: 40-60°C")
        _("pH del baño de níquel. Rango típico: 3.5-4.5", "Nickel bath pH. Typical range: 3.5-4.5")
        _("Densidad de corriente del baño de níquel en A/dm²", "Nickel bath current density in A/dm²")
        _(" Espesor de la capa de níquel objetivo en µm", "Target nickel layer thickness in µm")
        _("Método de preparación superficial: desengrase, decapado o activación", "Surface preparation method: degreasing, pickling or activation")
        _("Tiempo de preparación superficial en minutos", "Surface preparation time in minutes")
        _("Número de ciclos de enjuague después del baño", "Number of rinse cycles after the bath")
        _("Pestañas de galvanoplastia:\n• Parámetros de Baño — configuración de baños\n• Compatibilidad — matriz de compatibilidad\n• P&R — consultas sobre galvanoplastia",
          "Galvanoplastia tabs:\n• Bath Parameters — bath configuration\n• Compatibility — compatibility matrix\n• Q&A — galvanoplastia queries")

        # ── Pressing ──
        _("🔄 Prensado — Parámetros del Proceso", "🔄 Pressing — Process Parameters")
        _("Parámetros de Prensado", "Pressing Parameters")
        _("Especificaciones del Disco", "Disc Specifications")
        _("Registro de Producción", "Production Log")
        _("Referencias — Defectos de Prensado", "References — Pressing Defects")
        _("Temperatura de prensa:", "Press Temperature:")
        _("Presión de prensa:", "Press Pressure:")
        _("Tiempo de prensado:", "Pressing Time:")
        _("Tiempo de enfriamiento:", "Cooling Time:")
        _("Tipo de molde:", "Mold Type:")
        _("Agente desmoldante:", "Release Agent:")
        _("Tamaño:", "Size:")
        _("Grosor:", "Thickness:")
        _("Peso del disco:", "Disc Weight:")
        _("Vida útil del estampador:", "Stamper Life:")
        _(" °C", " °C")
        _(" bar", " bar")
        _(" s", " s")
        _(" mm", " mm")
        _(" g", " g")
        _(" prensadas", " pressings")
        _("Registrar Prensada", "Log Pressing")
        _("Limpiar Registro", "Clear Log")
        _("Prensado", "Pressing")
        _("P&R — Prensado", "Q&A — Pressing")
        _("Estándar 12\"", "Standard 12\"")
        _("Estándar 7\"", "Standard 7\"")
        _("Custom", "Custom")
        _("Ninguno", "None")
        _("Cera de silicona", "Silicone wax")
        _("PTFE spray", "PTFE spray")
        _("Agente desmoldante líquido", "Liquid release agent")
        _("12\" (30cm)", "12\" (30cm)")
        _("7\" (17.5cm)", "7\" (17.5cm)")
        _("10\" (25cm)", "10\" (25cm)")
        _("Temperatura de prensado en °C", "Pressing temperature in °C")
        _("Presión de prensado en bar", "Pressing pressure in bar")
        _("Tiempo de prensado en segundos", "Pressing time in seconds")
        _("Tiempo de enfriamiento después del prensado en segundos", "Cooling time after pressing in seconds")
        _("Tipo de molde utilizado en el prensado", "Mold type used in pressing")
        _("Agente desmoldante utilizado", "Release agent used")
        _("Tamaño del disco (pulgadas)", "Disc size (inches)")
        _("Grosor del disco en mm", "Disc thickness in mm")
        _("Peso del disco en gramos", "Disc weight in grams")
        _("Vida útil del estampador en número de prensadas", "Stamper life in number of pressings")
        _("Registro histórico de producciones de prensado con fechas y parámetros", "Historical pressing production log with dates and parameters")
        _("Registra la prensada actual en el historial de producción", "Record current pressing in production history")
        _("Limpia todo el registro de producción", "Clear the entire production log")
        _("Guía de referencia de defectos de prensado: causas y soluciones", "Pressing defect reference guide: causes and solutions")
        _("Registro de prensadas anteriores...", "Previous pressing records...")
        _("<h4>Defectos comunes de prensado</h4>", "<h4>Common pressing defects</h4>")
        _("<li><b>No llena</b> — temperatura o presión insuficientes</li>", "<li><b>Short fill</b> — insufficient temperature or pressure</li>")
        _("<li><b>Rebaba excesiva</b> — exceso de material o presión demasiado alta</li>", "<li><b>Excessive flash</b> — excess material or pressure too high</li>")
        _("<li><b>Disco pegado al molde</b> — agente desmoldante insuficiente</li>", "<li><b>Stuck disc</b> — insufficient release agent</li>")
        _("<li><b>Deformación (warp)</b> — enfriamiento desigual o humedad en el material</li>", "<li><b>Warping</b> — uneven cooling or material moisture</li>")
        _("<li><b>Marca de estampador</b> — estampador desgastado o dañado</li>", "<li><b>Stamper mark</b> — worn or damaged stamper</li>")
        _("<li><b>Burbujas atrapadas</b> — desgasificado insuficiente o material húmedo</li>", "<li><b>Trapped bubbles</b> — insufficient degassing or wet material</li>")

        # ── Knowledge Hub ──
        _("🧠 Centro de Conocimiento", "🧠 Knowledge Center")
        _("Importación", "Import")
        _("P&R — Base de Conocimiento", "Q&A — Knowledge Base")
        _("Navegador BC", "KB Browser")
        _("Duplicar Foro", "Mirror Forum")
        _("Importar Markdown", "Import Markdown")
        _("lathetrolls_knowledge_base", "lathetrolls_knowledge_base")
        _("Libros Escaneados", "Scanned Books")
        _("Importador Completo", "Full Importer")
        _("Sanitizar BC", "Sanitize KB")
        _("Explorador de Datos", "Data Explorer")
        _("Buscar en BC...", "Search KB...")
        _("Sin resultados", "No results")
        _("🧠 Centro de Conocimiento — Base de Conocimiento RAG", "🧠 Knowledge Center — RAG Knowledge Base")
        _("🌐 Duplicar Foro (Lathe Trolls)", "🌐 Mirror Forum (Lathe Trolls)")
        _("📂 Importar Markdown", "📂 Import Markdown")
        _("📁 lathetrolls_knowledge_base", "📁 lathetrolls_knowledge_base")
        _("📄 Libros Escaneados", "📄 Scanned Books")
        _("🔧 Importador Completo...", "🔧 Full Importer...")
        _("🧹 Sanitizar BC", "🧹 Sanitize KB")
        _("📊 Explorador de Datos", "📊 Data Explorer")
        _("Buscar en la base de conocimiento...", "Search the knowledge base...")
        _("Selecciona una entrada para ver su contenido...", "Select an entry to view its content...")
        _("""
        <h4>Defectos comunes de prensado</h4>
        <ul>
        <li><b>No llena</b> — temperatura o presión insuficientes</li>
        <li><b>Rebaba excesiva</b> — exceso de material o presión demasiado alta</li>
        <li><b>Disco pegado al molde</b> — agente desmoldante insuficiente</li>
        <li><b>Deformación (warp)</b> — enfriamiento desigual o humedad en el material</li>
        <li><b>Marca de estampador</b> — estampador desgastado o dañado</li>
        <li><b>Burbujas atrapadas</b> — desgasificado insuficiente o material húmedo</li>
        </ul>
        """,
        """
        <h4>Common pressing defects</h4>
        <ul>
        <li><b>Short fill</b> — insufficient temperature or pressure</li>
        <li><b>Excessive flash</b> — excess material or pressure too high</li>
        <li><b>Stuck disc</b> — insufficient release agent</li>
        <li><b>Warping</b> — uneven cooling or material moisture</li>
        <li><b>Stamper mark</b> — worn or damaged stamper</li>
        <li><b>Trapped bubbles</b> — insufficient degassing or wet material</li>
        </ul>
        """)

        # ── Pipeline Stage ──
        _("Editar Parámetros", "Edit Parameters")
        _("Parámetros Clave", "Key Parameters")
        _("Control de Calidad", "Quality Control")
        _("P&R — Control de Calidad", "Q&A — Quality Control")

        # ── Welcome Screen ──
        _("🏭  Lacquer Analyzer", "🏭  Lacquer Analyzer")
        _("Plataforma integral para formulación, análisis y control de calidad de lacas de corte",
          "Comprehensive platform for cut lacquer formulation, analysis and quality control")
        _("Módulos del sistema", "System Modules")
        _("Formulación de Laca", "Lacquer Formulation")
        _("Crea, analiza y optimiza recetas de laca. Busca ingredientes, ejecuta análisis físico-químico completo y compara variantes lado a lado.",
          "Create, analyze and optimize lacquer recipes. Search ingredients, run full physicochemical analysis and compare variants side by side.")
        _("Editor de recetas con tabla de componentes", "Recipe editor with component table")
        _("Análisis: viscosidad, evaporación, defectos, mojado", "Analysis: viscosity, evaporation, defects, wetting")
        _("Comparador de recetas lado a lado", "Side-by-side recipe comparison")
        _("Búsqueda multi-fuente (PubChem, Wikipedia, SpecialChem)", "Multi-source search (PubChem, Wikipedia, SpecialChem)")
        _("Mejorador de Fórmulas (Enhancer)", "Formula Enhancer")
        _("Potencia tus formulaciones con análisis inteligente. Recibe sugerencias de optimización basadas en propiedades objetivo.",
          "Boost your formulations with intelligent analysis. Get optimization suggestions based on target properties.")
        _("Análisis de compatibilidad Hansen", "Hansen compatibility analysis")
        _("Puntuación global 0-100 con desglose", "Global score 0-100 with breakdown")
        _("Sugerencias de modificación automáticas", "Automatic modification suggestions")
        _("Traducción de advertencias con LLM", "LLM-powered warning translation")
        _("Solucionador de Problemas", "Problem Solver")
        _("Diagnostica y resuelve defectos de formulación con la ayuda de la base de conocimiento y el LLM.",
          "Diagnose and solve formulation defects with help from the knowledge base and LLM.")
        _("Base de datos de defectos por etapa del proceso", "Defect database by process stage")
        _("Buscador con filtros por severidad y etapa", "Search with severity and stage filters")
        _("P&R con LLM sobre causas y soluciones", "LLM Q&A on causes and solutions")
        _("Referencias del foro Lathe Trolls", "Lathe Trolls forum references")
        _("Galvanoplastia", "Galvanoplastia")
        _("Configura y optimiza baños galvánicos de plata y níquel sulfamato para procesos de electroformado.",
          "Configure and optimize silver and nickel sulfamate galvanic baths for electroforming processes.")
        _("Parámetros de baño: temperatura, pH, densidad de corriente", "Bath parameters: temperature, pH, current density")
        _("Matriz de compatibilidad de solventes", "Solvent compatibility matrix")
        _("Guías de prevención de defectos galvánicos", "Galvanic defect prevention guides")
        _("P&R especializado en galvanoplastia", "Specialized galvanoplastia Q&A")
        _("Prensado", "Pressing")
        _("Gestiona parámetros de prensado, especificaciones de disco y lleva el registro histórico de producción.",
          "Manage pressing parameters, disc specifications and keep a historical production log.")
        _("Temperatura, presión y tiempos de prensado/enfriamiento", "Temperature, pressure and pressing/cooling times")
        _("Especificaciones: tamaño, grosor, peso", "Specifications: size, thickness, weight")
        _("Registro de producción con historial", "Production log with history")
        _("Referencias de defectos de prensado", "Pressing defect references")
        _("RAG & Base de Conocimiento", "RAG & Knowledge Base")
        _("Construye y consulta tu base de conocimiento con RAG. Importa datos del foro, PDFs, patentes y haz preguntas con LLM.",
          "Build and query your knowledge base with RAG. Import forum data, PDFs, patents and ask questions with LLM.")
        _("Importación multi-fuente (foro, PDF, Wikipedia, PubChem)", "Multi-source import (forum, PDF, Wikipedia, PubChem)")
        _("Pipeline RAG completo con fragmentación", "Full RAG pipeline with chunking")
        _("Q&A inteligente con contexto recuperado", "Intelligent Q&A with retrieved context")
        _("Explorador de datos con mapa mental", "Data explorer with mind map")
        _("🖱️ Haz clic para abrir", "🖱️ Click to open")
        _("Ingredientes en BD", "Ingredients in DB")
        _("Recetas cargadas", "Recipes loaded")
        _("Base de Conocimiento", "Knowledge Base")
        _("LLM", "LLM")
        _("No verificado", "Not verified")
        _("—", "—")
        _("💡 Pasa el ratón sobre cualquier elemento para ver ayuda  ·  Usa el menú Ayuda → Guía de uso para una explicación detallada  ·  Selecciona 🇪🇸/🇬🇧 en la barra para cambiar idioma",
          "💡 Hover over any element for help  ·  Use Help → Usage Guide for a detailed explanation  ·  Select 🇪🇸/🇬🇧 in the toolbar to switch language")

        # ── Plating Overview ──
        _("Parámetros de Recubrimiento Recomendados", "Recommended Coating Parameters")
        _("Matriz de Compatibilidad de Solventes", "Solvent Compatibility Matrix")
        _("Guías de Prevención de Defectos", "Defect Prevention Guides")

        # ── Generate Formulation ──
        _("Generar Formulación desde Especificación", "Generate Formulation from Specification")
        _("Requisitos", "Requirements")
        _("Método de Aplicación:", "Application Method:")
        _("Viscosidad Objetivo (mPa·s):", "Target Viscosity (mPa·s):")
        _("Sólidos Objetivo (%):", "Target Solids (%):")
        _("Tipo de Curado:", "Cure Type:")
        _("Tipo de Película:", "Film Type:")
        _("Generar Formulación", "Generate Formulation")
        _("Usar Esta Formulación", "Use This Formulation")
        _("curtain_coater", "curtain_coater")
        _("spin_coater", "spin_coater")
        _("Ambient", "Ambient")
        _("Oven", "Oven")
        _("Transparente", "Clear")
        _("Pigmentada", "Pigmented")

        # ── Defect Editor ──
        _("Editor de Defectos", "Defect Editor")
        _("Añadir Nuevo Defecto", "Add New Defect")
        _("Guardar Cambios", "Save Changes")
        _("Descripción:", "Description:")

        # ── Plating Rules Editor ──
        _("Plateado", "Silver Plating")
        _("Sulfamato de Níquel", "Nickel Sulfamate")
        _("Secuencias de Proceso", "Process Sequences")

        # ── RAG Settings ──
        _("Configuración Base", "Base Settings")
        _("Agentes", "Agents")
        _("Conexión LLM", "LLM Connection")
        _("Generación", "Generation")
        _("Recuperación de Conocimiento", "Knowledge Retrieval")
        _("Raspador del Foro", "Forum Scraper")
        _("Prompt del Sistema", "System Prompt")

        # ── Analysis Panel (legacy) ──
        _("Aún no se ha realizado ningún análisis", "No analysis has been performed yet")
        _("Sólidos: --", "Solids: --")
        _("Viscosidad: --", "Viscosity: --")
        _("Componentes: --", "Components: --")
        _("Aplicador: Cortina Burkle", "Applicator: Burkle Curtain")
        _("Análisis del Sistema de Solventes", "Solvent System Analysis")
        _("Propiedades del Recubrimiento", "Coating Properties")
        _("Problemas y Sugerencias de Formulación", "Formulation Issues & Suggestions")
        _("Estadísticas de la Receta", "Recipe Statistics")
        _("Riesgo General:", "Overall Risk:")
        _("Sólidos Estimados:", "Estimated Solids:")
        _("Visc. Estimada:", "Est. Viscosity:")
        _("Componentes:", "Components:")
        _("<h3>Sistema de Solventes</h3>", "<h3>Solvent System</h3>")
        _("<p><b>Balance de Evaporación:</b> ", "<p><b>Evaporation Balance:</b> ")
        _("<p><b>Riesgo de Empañamiento:</b> ", "<p><b>Blush Risk:</b> ")
        _("<p><b>Calidad de Solvencia:</b> ", "<p><b>Solvency Quality:</b> ")
        _("<p><b>Recomendaciones:</b></p><ul>", "<p><b>Recommendations:</b></p><ul>")
        _("<p><b>Problemas:</b></p><ul>", "<p><b>Issues:</b></p><ul>")
        _("<h3>Propiedades del Recubrimiento</h3>", "<h3>Coating Properties</h3>")
        _("<p><b>Sólidos Estimados:</b> ", "<p><b>Estimated Solids:</b> ")
        _("<p><b>Viscosidad Estimada:</b> ", "<p><b>Estimated Viscosity:</b> ")
        _("<p><b>Calidad de Nivelación:</b> ", "<p><b>Leveling Quality:</b> ")
        _("<h3>Análisis de Formulación</h3>", "<h3>Formulation Analysis</h3>")
        _("<p><b>Problemas Encontrados:</b></p><ul>", "<p><b>Issues Found:</b></p><ul>")
        _("<p style='color:green;'>No se encontraron problemas de formulación</p>", "<p style='color:green;'>No formulation issues found</p>")
        _("<p><b>Modificaciones Sugeridas:</b></p><ul>", "<p><b>Suggested Modifications:</b></p><ul>")
        _("LOW", "BAJO")
        _("MEDIUM", "MEDIO")
        _("HIGH", "ALTO")
        _("CRITICAL", "CRÍTICO")
        _("fast", "rápido")
        _("balanced", "equilibrado")
        _("slow", "lento")
        _("good", "buena")
        _("fair", "regular")
        _("poor", "mala")
        _("excellent", "excelente")
        _("low", "bajo")
        _("medium", "medio")
        _("high", "alto")

        # ── Usage Guide dialog ──
        _("📖 Guía de Uso — Lacquer Analyzer", "📖 Usage Guide — Lacquer Analyzer")

        # ── Process Manual dialog ──
        _("📖 Manual: Formulación de Laca", "📖 Manual: Lacquer Formulation")
        _("📖 Manual: Galvánica", "📖 Manual: Electroplating")
        _("📖 Manual: Prensado", "📖 Manual: Pressing")
        _("📖 Manual: Corte", "📖 Manual: Cutting")
        _("Visión General", "Overview")
        _("Historia — 1920–1950", "History — 1920–1950")
        _("Historia — 1950–2000", "History — 1950–2000")
        _("Historia — 2000–Presente", "History — 2000–Present")
        _("Historia — 1930–1970", "History — 1930–1970")
        _("Historia — 1970–Presente", "History — 1970–Present")
        _("Historia — 1900–1960", "History — 1900–1960")
        _("Historia — 1960–Presente", "History — 1960–Present")
        _("Historia — 1920–1960", "History — 1920–1960")
        _("Historia — 1960–Presente", "History — 1960–Present")
        _("Manual no disponible para este proceso.", "Manual not available for this process.")
        _("📖 Manual — Formulación", "📖 Manual — Formulation")
        _("📖 Manual — Corte", "📖 Manual — Cutting")
        _("📖 Manual — Galvánica", "📖 Manual — Electroplating")
        _("📖 Manual — Prensado", "📖 Manual — Pressing")
        _("Guía completa del proceso de prensado: historia, parámetros y defectos", "Complete pressing guide: history, parameters and defects")
        _("Guía completa de galvanoplastia: historia, baños y procesos", "Complete electroplating guide: history, baths and processes")
        _("Guía completa de formulación de lacas: historia, componentes y evolución", "Complete lacquer formulation guide: history, components and evolution")
        _("Guía completa del corte de lacas: historia, cabezas y tecnología", "Complete lacquer cutting guide: history, cutterheads and technology")

        # ── Ventana de Fórmulas (formula_window.py) ──
        _("Ventana de Fórmulas", "Formula Window")
        _("Ventana de Fórmulas...", "Formula Window...")
        _("🧪 Formula Studio", "🧪 Formula Studio")
        _("Abre el estudio de fórmulas: biblioteca, versiones con restauración y capturas", "Opens the formula studio: library, versions with restore and snapshots")
        _("Nueva Fórmula", "New Formula")
        _("Nombre de la nueva fórmula:", "Name of the new formula:")
        _("Guardar Versión", "Save Version")
        _("Motivo del cambio (opcional):", "Reason for the change (optional):")
        _("Sin motivo", "No reason")
        _("Versión guardada", "Version saved")
        _("Guardado", "Saved")
        _("Deshacer", "Undo")
        _("Rehacer", "Redo")
        _("Captura de Pantalla", "Screenshot")
        _("Captura guardada", "Screenshot saved")
        _("Buscar fórmulas...", "Search formulas...")
        _("Filtra la biblioteca por nombre o etiqueta", "Filter the library by name or tag")
        _("Biblioteca de Fórmulas", "Formula Library")
        _("Historial de Versiones", "Version History")
        _("Capturas", "Snapshots")
        _("✏ Info", "✏ Info")
        _("Gestiona la fórmula seleccionada: información, favorita o eliminar", "Manage the selected formula: info, favorite or delete")
        _("Doble clic abre la fórmula. La lista se filtra con el buscador", "Double click opens the formula. The list is filtered by the search box")
        _("Historial de versiones de la fórmula seleccionada. Cada versión guarda un motivo y el resumen de cambios", "Version history of the selected formula. Each version stores a reason and a change summary")
        _("Capturas de pantalla de la fórmula seleccionada, guardadas por versión", "Screenshots of the selected formula, saved per version")
        _("Vista Previa", "Preview")
        _("Restaurar", "Restore")
        _("Eliminar Captura", "Delete Snapshot")
        _("Comparar", "Compare")
        _("Vista Previa de Versión", "Version Preview")
        _("Versión", "Version")
        _("Cambios:", "Changes:")
        _("Comparar Capturas", "Compare Snapshots")
        _("Selecciona dos capturas para compararlas.", "Select two snapshots to compare them.")
        _("Información de la Fórmula", "Formula Info")
        _("Descripción:", "Description:")
        _("Etiquetas (separadas por coma):", "Tags (comma separated):")
        _("⭐ Marcar como Favorita", "⭐ Mark as Favorite")
        _("Nombre de la fórmula. Se guarda al terminar de editar", "Formula name. Saved when editing finishes")
        _("Concentración del nuevo componente en porcentaje", "Concentration of the new component in percent")
        _("Añadir desde BD:", "Add from DB:")
        _("Ingrediente", "Ingredient")
        _("Análisis", "Analysis")
        _("Añade al menos un componente antes de analizar.", "Add at least one component before analyzing.")
        _("Editar fórmula", "Edit formula")
        _("Cambios sin guardar", "Unsaved changes")
        _("La fórmula tiene cambios sin guardar. ¿Guardarlos antes de cerrar?", "The formula has unsaved changes. Save them before closing?")
        _("¿Restaurar la versión {v}?\nLa versión actual se guardará automáticamente como punto de seguridad.", "Restore version {v}?\nThe current version will be saved automatically as a safety point.")
        _("Restauración manual", "Manual restore")
        _("Versión restaurada", "Version restored")
        _("Eliminar Fórmula", "Delete Formula")
        _("¿Eliminar la fórmula '{name}'?\nEsta acción no se puede deshacer.", "Delete formula '{name}'?\nThis action cannot be undone.")
        _("Fórmula abierta:", "Formula open:")

        return d


# ── Global singleton access ──
translator = Translator.instance()
T = translator.get
