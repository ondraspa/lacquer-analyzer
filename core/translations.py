"""Sistema de traducción EN/ES para toda la aplicación.

Uso:
  from core.translations import T, translator

  # En cualquier widget:
  label = QLabel(T("Nombre:"))
  button = QPushButton(T("Guardar"))

  # Conectar al cambio de idioma:
  translator.language_changed.connect(self._retranslate)

  # Traducir con LLM:
  # resultado = await translator.translate_with_llm(texto, target_lang, llm_client)
"""

import json
import os
from typing import Dict, Optional, Callable
from PySide6.QtCore import QObject, Signal


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
        self._strings = {
            # ── General ──
            "app_title": {"en": "Lacquer Analyzer — Lacquer Disc Manufacturing", "es": "Analizador de Laca — Fabricación de Discos de Laca"},
            "file": {"en": "File", "es": "Archivo"},
            "edit": {"en": "Edit", "es": "Editar"},
            "help": {"en": "Help", "es": "Ayuda"},
            "save": {"en": "Save", "es": "Guardar"},
            "cancel": {"en": "Cancel", "es": "Cancelar"},
            "close": {"en": "Close", "es": "Cerrar"},
            "delete": {"en": "Delete", "es": "Eliminar"},
            "search": {"en": "Search", "es": "Buscar"},
            "add": {"en": "Add", "es": "Añadir"},
            "remove": {"en": "Remove", "es": "Quitar"},
            "clear": {"en": "Clear", "es": "Limpiar"},
            "name": {"en": "Name", "es": "Nombre"},
            "type": {"en": "Type", "es": "Tipo"},
            "notes": {"en": "Notes", "es": "Notas"},
            "warning": {"en": "Warning", "es": "Advertencia"},
            "error": {"en": "Error", "es": "Error"},
            "loading": {"en": "Loading...", "es": "Cargando..."},
            "language": {"en": "Language", "es": "Idioma"},
            "translate": {"en": "Translate", "es": "Traducir"},
            "translate_help": {"en": "Translate text using local AI", "es": "Traducir texto usando IA local"},

            # ── Recipe Editor ──
            "recipe_info_group": {"en": "Recipe Info", "es": "Información de la Receta"},
            "recipe_name": {"en": "Name:", "es": "Nombre:"},
            "target_viscosity": {"en": "Target Viscosity:", "es": "Viscosidad Objetivo:"},
            "target_solids": {"en": "Target Solids:", "es": "Sólidos Objetivo:"},
            "preset_load": {"en": "Load Preset:", "es": "Predefinidas:"},
            "preset_placeholder": {"en": "— Load a preset recipe —", "es": "— Cargar receta predefinida —"},
            "add_from_db": {"en": "Add from DB:", "es": "Añadir desde BD:"},
            "add_component": {"en": "Add Component", "es": "Añadir Componente"},
            "remove_selected": {"en": "Remove Selected", "es": "Quitar Seleccionado"},
            "clear_all": {"en": "Clear All", "es": "Limpiar Todo"},
            "save_as_preset": {"en": "Save as Preset", "es": "Guardar como Preset"},
            "save_preset_title": {"en": "Save as Custom Preset", "es": "Guardar como Preset Personalizado"},
            "save_preset_ok": {"en": "Preset saved. Reload the app to see it in the selector.", "es": "Preset guardado. Recarga la app para verlo en el selector."},
            "no_recipe_to_save": {"en": "No recipe to save", "es": "No hay receta para guardar"},
            "export_recipe": {"en": "Export Recipe", "es": "Exportar Receta"},
            "import_recipe": {"en": "Import Recipe", "es": "Importar Receta"},
            "run_analysis": {"en": "Run Analysis", "es": "Ejecutar Análisis Completo"},
            "ingredient": {"en": "Ingredient", "es": "Ingrediente"},
            "concentration": {"en": "Concentration %", "es": "Concentración %"},
            "max_conc": {"en": "Max %", "es": "Máx %"},

            # ── Metadata / Pros & Cons ──
            "pros_cons_tab": {"en": "Pros/Cons & Hardware", "es": "Pros/Contras & Hardware"},
            "best_for": {"en": "BEST FOR:", "es": "MEJOR PARA:"},
            "advantages": {"en": "ADVANTAGES:", "es": "VENTAJAS:"},
            "disadvantages": {"en": "DISADVANTAGES:", "es": "DESVENTAJAS:"},
            "recommended_hardware": {"en": "RECOMMENDED HARDWARE:", "es": "HARDWARE RECOMENDADO:"},
            "common_issues": {"en": "COMMON ISSUES & SOLUTIONS:", "es": "PROBLEMAS COMUNES Y SOLUCIONES:"},
            "no_metadata": {"en": "This recipe has no associated metadata.", "es": "Esta receta no tiene metadatos asociados."},
            "no_metadata_details": {"en": "Metadata is only available for preset recipes.", "es": "Los metadatos están disponibles solo para recetas predefinidas."},
            "coater_type": {"en": "Coater:", "es": "Cortinado:"},
            "drying": {"en": "Drying:", "es": "Secado:"},
            "curing": {"en": "Curing:", "es": "Curado:"},
            "cutting_lathe": {"en": "Lathe:", "es": "Torno:"},
            "stylus": {"en": "Stylus:", "es": "Aguja:"},

            # ── Analysis Tab ──
            "analysis_tab": {"en": "Lacquer Analysis", "es": "Análisis de Laca"},
            "ambient_temp": {"en": "Ambient Temperature:", "es": "Temperatura ambiente:"},
            "relative_humidity": {"en": "Relative Humidity:", "es": "Humedad relativa:"},
            "layer_thickness": {"en": "Lacquer Layer Thickness:", "es": "Espesor capa laca:"},
            "polish_grain": {"en": "Disk Polish Grain:", "es": "Grano pulido disco:"},
            "air_flow": {"en": "Air Flow:", "es": "Flujo de aire:"},
            "application_method": {"en": "Application:", "es": "Aplicación:"},
            "positive_pressure": {"en": "Positive Pressure Chamber", "es": "Cámara de presión positiva"},
            "mist_um": {"en": " µm", "es": " µm"},
            "m_per_s": {"en": " m/s", "es": " m/s"},

            # ── Analysis Results ──
            "viscosity_tab": {"en": "Viscosity & Film", "es": "Viscosidad & Película"},
            "evaporation_tab": {"en": "Evaporation", "es": "Evaporación"},
            "defects_tab": {"en": "Defects", "es": "Defectos"},
            "wetting_tab": {"en": "Wetting & Hansen", "es": "Mojado & Hansen"},
            "predicted_viscosity": {"en": "Predicted Viscosity:", "es": "Viscosidad predicha:"},
            "category": {"en": "Category:", "es": "Categoría:"},
            "ford_cup": {"en": "Ford Cup #4:", "es": "Ford Cup #4:"},
            "solids_vol": {"en": "Solids vol:", "es": "Sólidos vol.:"},
            "final_tg": {"en": "Final Tg:", "es": "Tg final:"},
            "hardness": {"en": "Hardness:", "es": "Dureza:"},
            "flexibility": {"en": "Flexibility:", "es": "Flexibilidad:"},
            "drying_time": {"en": "Estimated Drying Time:", "es": "Tiempo de secado estimado:"},
            "bubble_trapping": {"en": "Bubble Trapping", "es": "Atrapamiento de Burbujas"},
            "blush_risk": {"en": "Blush Risk", "es": "Blush (Blanqueamiento)"},
            "orange_peel": {"en": "Orange Peel", "es": "Orange Peel (Piel de Naranja)"},
            "risk": {"en": "Risk:", "es": "Riesgo:"},
            "surface_tension": {"en": "Surface Tension:", "es": "Tensión superficial:"},
            "wetting": {"en": "Wetting:", "es": "Mojado:"},
            "hansen_red": {"en": "Hansen dist. (RED):", "es": "Hansen dist. (RED):"},
            "hansen_compat": {"en": "Compatible with NC:", "es": "Compatible con NC:"},
            "global_score": {"en": "Global Score:", "es": "Puntuación global:"},
            "warnings": {"en": "Warnings:", "es": "Advertencias:"},
            "no_warnings": {"en": "No warnings — balanced recipe", "es": "Sin advertencias — receta equilibrada"},
            "max_bubble_free": {"en": "Max no-bubble thickness:", "es": "Espesor máx sin burbujas:"},
            "dew_point": {"en": "Dew point", "es": "Punto de rocío"},
            "surface_cooling": {"en": "Surface cooling", "es": "Enfriamiento superficial"},

            # ── Comparison Tab ──
            "comparison_tab": {"en": "Compare Recipes", "es": "Comparar Recetas"},
            "compare_placeholder_a": {"en": "— Recipe A —", "es": "— Receta A —"},
            "compare_placeholder_b": {"en": "— Recipe B —", "es": "— Receta B —"},
            "compare": {"en": "Compare", "es": "Comparar"},
            "composition_tab": {"en": "Composition", "es": "Composición"},
            "properties_tab": {"en": "Properties", "es": "Propiedades"},
            "full_analysis_tab": {"en": "Full Analysis", "es": "Análisis Completo"},
            "component": {"en": "Component", "es": "Componente"},
            "recipe_a": {"en": "Recipe A (%)", "es": "Receta A (%)"},
            "recipe_b": {"en": "Recipe B (%)", "es": "Receta B (%)"},
            "difference": {"en": "Difference", "es": "Diferencia"},
            "diff_notes": {"en": "Notes", "es": "Notas"},
            "property": {"en": "Property", "es": "Propiedad"},

            # ── Components Tab ──
            "components_tab": {"en": "Components", "es": "Componentes"},

            # ── Plating ──
            "plating_recipes": {"en": "Plating Recipes", "es": "Recetas de Galvanoplastia"},

            # ── SpecialChem ──
            "setup_cookies": {"en": "Set up Cookies", "es": "Configurar Cookies"},
            "sc_search": {"en": "Search SpecialChem...", "es": "Buscar en SpecialChem..."},
            "sc_add_to_recipe": {"en": "Add to Recipe", "es": "Añadir a la Receta"},

            # ── Pigment Search ──
            "pigment_search": {"en": "Search Pigments...", "es": "Buscar Pigmentos..."},
            "add_pigment": {"en": "Add Pigment", "es": "Añadir Pigmento"},

            # ── Ingredient Editor ──
            "ingredient_editor_title": {"en": "Ingredient Editor", "es": "Editor de Ingredientes"},
            "add_ingredient": {"en": "Add Ingredient", "es": "Añadir Ingrediente"},
            "edit_ingredient": {"en": "Edit Ingredient", "es": "Editar Ingrediente"},
        }

    @property
    def current_language(self) -> str:
        return self._current_lang

    def set_language(self, lang: str):
        if lang not in ("en", "es"):
            return
        self._current_lang = lang
        self.language_changed.emit(lang)

    def get(self, key: str) -> str:
        entry = self._strings.get(key)
        if entry is None:
            return key
        return entry.get(self._current_lang, entry.get("en", key))

    def get_all(self, key: str) -> Dict[str, str]:
        return self._strings.get(key, {"en": key, "es": key})

    async def translate_with_llm(self, text: str, target_lang: str, llm_client) -> str:
        """Traduce un texto usando el LLM local."""
        if not text.strip():
            return text
        lang_name = "Spanish" if target_lang == "es" else "English"
        prompt = (
            f"Translate the following text to {lang_name}. "
            f"Preserve all formatting, emoji, and technical terms exactly.\n\n"
            f"---\n{text}\n---"
        )
        try:
            result = await llm_client.chat(prompt)
            return result.strip()
        except Exception:
            return text


# ── Global singleton access ──
translator = Translator.instance()
T = translator.get
