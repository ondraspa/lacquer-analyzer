"""Base de datos de defectos y solución de problemas para el proceso completo de fabricación de vinilo.

Cada etapa tiene defectos conocidos con causas, soluciones y referencias
a conocimientos del foro (hilos de Lathe Trolls).
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Defect:
    id: str
    name: str
    stage: str  # corte, plateado, prensado, control de calidad
    description: str
    symptoms: List[str]
    causes: List[str]
    solutions: List[str]
    forum_refs: List[str] = field(default_factory=list)
    severity: str = "medium"  # bajo, medio, alto, crítico


# Base de datos completa de defectos organizada por etapa del proceso
DEFECT_DATABASE = [
    Defect(
        id="orange_peel",
        name="Piel de Naranja",
        stage="coating",
        severity="medium",
        description="Textura superficial irregular que recuerda a la piel de naranja. Causada por un balance de solventes inadecuado, viscosidad incorrecta o parámetros de recubrimiento incorrectos.",
        symptoms=["Apariencia de superficie ondulada", "Rugosidad superficial medible >2µm", "Brillo reducido"],
        causes=["El solvente se evapora demasiado rápido", "Viscosidad demasiado alta", "Recubrimiento demasiado grueso", "Presión de atomización incorrecta"],
        solutions=["Ajustar la mezcla de solventes con solventes de evaporación más lenta", "Reducir la viscosidad", "Reducir el espesor del recubrimiento", "Verificar la configuración de la recubridora por cortina"],
        forum_refs=["Guía de formulación de laca §4.2", "Manual de recubridora Burkle §3.5"],
    ),
    Defect(
        id="pinholes",
        name="Poros / Pinchazos",
        stage="coating",
        severity="high",
        description="Pequeños agujeros en la superficie de la laca que llegan hasta el aluminio. Catastrófico para el corte y el posterior plateado.",
        symptoms=["Pequeños agujeros con forma de cráter visibles bajo 10x de aumento", "La plata penetra durante el plateado"],
        causes=["Burbujas de aire en la laca", "Polvo/partículas sobre el sustrato", "Contaminación por humedad", "Tiempo de desgasificación inadecuado"],
        solutions=["Aumentar el tiempo de desgasificación después de la mezcla", "Mejorar las condiciones de la sala limpia", "Filtrar la laca a través de malla de 5µm", "Pre-secar el sustrato"],
        forum_refs=["Análisis de defectos de laca §2.1", "Protocolos de sala limpia §1.3"],
    ),
    Defect(
        id="cratering",
        name="Cráteres",
        stage="coating",
        severity="medium",
        description="Pequeñas depresiones en forma de tazón en la superficie del recubrimiento. Frecuentemente causadas por contaminación superficial o contaminación por silicona.",
        symptoms=["Depresiones redondas de 0.1-2mm de diámetro", "Distribución aleatoria", "Frecuentemente en el centro del disco"],
        causes=["Contaminación por aceite de silicona", "Contaminante de baja tensión superficial", "Limpieza inadecuada del sustrato", "Niebla de aceite en el aire"],
        solutions=["Eliminar fuentes de silicona de la instalación", "Mejorar la limpieza del sustrato", "Verificar los filtros HVAC", "Usar aditivo anti-cráteres 0.1-0.5%"],
        forum_refs=["Manual de defectos superficiales §3.2", "Control de contaminación §5.1"],
    ),
    Defect(
        id="haze",
        name="Veladura / Empañamiento",
        stage="curing",
        severity="medium",
        description="Apariencia translúcida o lechosa en la laca seca. Causada por condensación de humedad durante el secado.",
        symptoms=["Película blanca/lechosa", "Transparencia reducida", "Superficie blanda"],
        causes=["Alta humedad durante el curado", "Enfriamiento rápido de la superficie", "Humedad en el sistema de solventes", "Evaporación del solvente demasiado rápida"],
        solutions=["Controlar el ambiente de curado a <50% HR", "Reducir la tasa de evaporación del solvente", "Usar aditivos captadores de agua", "Aumentar la tasa de intercambio de aire"],
        forum_refs=["Condiciones de curado §6.2", "Diseño del sistema de solventes §3.4"],
    ),
    Defect(
        id="solvent_pop",
        name="Estallido de Solvente",
        stage="curing",
        severity="high",
        description="Ampollas o burbujas que estallan durante el secado, dejando defectos con forma de cráter. El solvente atrapado irrumpe a través de la superficie.",
        symptoms=["Cráteres en forma de volcán de 0.5-3mm", "Bordes de recubrimiento más gruesos alrededor del cráter", "Se encuentra más en secciones gruesas"],
        causes=["Recubrimiento aplicado demasiado grueso", "Secado demasiado rápido", "Sistema de solventes incorrecto", "Tiempo de evaporación insuficiente"],
        solutions=["Reducir el espesor de película húmeda", "Reducir la velocidad de secado inicial", "Ajustar la mezcla de solventes para evaporación más lenta", "Permitir mayor tiempo de evaporación entre pasadas"],
        forum_refs=["Defectos de secado §4.1", "Análisis de retención de solvente §2.3"],
    ),
    Defect(
        id="adhesion_failure",
        name="Fallo de Adhesión",
        stage="qc",
        severity="high",
        description="La laca se desprende del sustrato de aluminio. Falla completa del disco.",
        symptoms=["La laca se levanta del aluminio", "Desprendimiento en los bordes", "Formación de ampollas", "Prueba de cinta de corte cruzado <4B"],
        causes=["Limpieza inadecuada del sustrato", "Aleación de aluminio incorrecta", "Humedad en el sustrato", "Promotor de adhesión incompatible", "Temperatura de curado demasiado alta"],
        solutions=["Mejorar el protocolo de desengrase", "Usar promotor de adhesión de silano al 0.5%", "Asegurar que el sustrato esté completamente seco", "Controlar la rampa de temperatura de curado"],
        forum_refs=["Pruebas de adhesión §5.1", "Preparación del sustrato §2.2"],
    ),
    Defect(
        id="crazing",
        name="Agrietamiento",
        stage="curing",
        severity="high",
        description="Grietas finas en la superficie de la laca, a menudo en patrón de telaraña. Hace que el disco sea inutilizable para el corte.",
        symptoms=["Grietas finas capilares", "Patrón de telaraña", "A menudo en los bordes del disco"],
        causes=["Estrés interno excesivo", "Demasiado plastificante", "Temperatura de curado demasiado alta", "Desajuste de expansión térmica del sustrato"],
        solutions=["Aumentar el contenido de plastificante", "Reducir la temperatura de curado", "Reducir la velocidad de enfriamiento", "Usar un grado de NC más flexible"],
        forum_refs=["Agrietamiento por estrés §3.1", "Selección de plastificante §4.3"],
    ),
    Defect(
        id="fish_eyes",
        name="Ojos de Pescado",
        stage="coating",
        severity="medium",
        description="Pequeñas áreas redondas donde el recubrimiento se retira, dejando puntos descubiertos. Se asemeja a ojos de pescado.",
        symptoms=["Áreas redondas descubiertas de 0.5-5mm", "Apariencia de desmojado", "A menudo alrededor de partículas contaminantes"],
        causes=["Contaminación por silicona/grasa", "Aditivos mal mezclados", "Surfactante incompatible", "Contaminante de baja energía superficial"],
        solutions=["Eliminar fuentes de contaminación", "Mejorar el protocolo de mezclado", "Verificar la pureza de la materia prima", "Limpiar el sustrato más a fondo"],
        forum_refs=["Defectos de tensión superficial §2.4", "Operación de sala limpia §1.5"],
    ),
    Defect(
        id="thickness_variation",
        name="Espesor No Uniforme",
        stage="coating",
        severity="medium",
        description="Variación en el espesor del recubrimiento en toda la superficie del disco. Afecta la consistencia del corte y la profundidad del surco.",
        symptoms=["Patrón visible de bandas o cuñas", "Variación de espesor >±20µm", "Franjas de color en luz reflejada"],
        causes=["Variación de velocidad de la recubridora por cortina", "Fluctuación de viscosidad", "Sujeción desigual del sustrato", "Desnivel del cabezal de recubrimiento"],
        solutions=["Calibrar la velocidad de la recubridora por cortina", "Monitorear y controlar la viscosidad", "Verificar la sujeción del sustrato", "Nivelar el conjunto del cabezal de recubrimiento"],
        forum_refs=["Uniformidad de recubrimiento §5.3", "Calibración de recubridora Burkle §3.2"],
    ),
    Defect(
        id="surface_roughness",
        name="Rugosidad Superficial Excesiva",
        stage="qc",
        severity="medium",
        description="Superficie demasiado rugosa para un corte de calidad. Medida como Ra >0.5µm.",
        symptoms=["Apariencia de superficie mate", "Ra medida >0.5µm", "El lápiz óptico salta durante el control de calidad"],
        causes=["Superficie del sustrato deficiente", "Viscosidad de la laca demasiado alta", "Contaminación por polvo", "Parámetros de recubrimiento incorrectos"],
        solutions=["Mejorar el acabado superficial del sustrato", "Reducir la viscosidad", "Mejorar las condiciones de la sala limpia", "Optimizar los parámetros de recubrimiento"],
        forum_refs=["Requisitos de acabado superficial §1.2", "Especificaciones del sustrato §2.1"],
    ),
    Defect(
        id="edge_bead",
        name="Cordón en el Borde",
        stage="coating",
        severity="low",
        description="Acumulación gruesa de laca en los bordes del disco. Normal hasta cierto grado, pero un cordón excesivo afecta la manipulación.",
        symptoms=["Borde elevado visible y palpable", "Más grueso en la periferia", "Puede agrietarse durante la manipulación"],
        causes=["La tensión superficial atrae el recubrimiento al borde", "Velocidad de giro demasiado baja (recubrimiento por giro)", "Superposición de cortina en los bordes"],
        solutions=["Recortar el cordón del borde después del curado", "Optimizar el perfil de giro", "Ajustar la pulverización excesiva de la recubridora por cortina", "Aceptar hasta 5mm de cordón en el borde"],
        forum_refs=["Efectos de borde §4.4", "Selección del método de recubrimiento §3.1"],
    ),
    Defect(
        id="contamination",
        name="Contaminación Superficial / Suciedad",
        stage="qc",
        severity="high",
        description="Partículas extrañas incrustadas en o sobre la superficie de la laca. Causa pops y clics durante la reproducción.",
        symptoms=["Partículas visibles bajo luz", "Protuberancias táctiles", "Causa ruido en el corte"],
        causes=["Polvo en el ambiente de recubrimiento", "Fuga del filtro", "Contaminación del contenedor", "Contaminación del operador"],
        solutions=["Sala limpia Clase 1000 o mejor", "Usar filtro final de 5µm en la laca", "Protocolos estrictos de sala limpia", "Ionizar el aire para reducir la atracción estática"],
        forum_refs=["Especificaciones de sala limpia §1.1", "Prevención de contaminación §5.3"],
    ),
    Defect(
        id="soft_coating",
        name="Dureza Insuficiente / Recubrimiento Blando",
        stage="curing",
        severity="high",
        description="La laca permanece demasiado blanda después del curado. No puede mantener el patrón de surco durante el corte.",
        symptoms=["Marcas de uñas fácilmente", "Shore D <60", "Deformación del surco durante el corte"],
        causes=["Subcurado", "Demasiado plastificante", "Grado de NC incorrecto", "Evaporación insuficiente del solvente"],
        solutions=["Aumentar el tiempo/temperatura de curado", "Reducir el contenido de plastificante", "Usar un grado NC de mayor viscosidad", "Mejorar el intercambio de aire durante el secado"],
        forum_refs=["Perfiles de curado §6.1", "Especificaciones de dureza §1.4"],
    ),
]


def get_defects_by_stage(stage: str) -> List[Defect]:
    """Obtener todos los defectos para una etapa del proceso."""
    return [d for d in DEFECT_DATABASE if d.stage == stage]


def get_defect_by_id(defect_id: str) -> Optional[Defect]:
    """Buscar un defecto por su ID."""
    for d in DEFECT_DATABASE:
        if d.id == defect_id:
            return d
    return None


def search_defects(query: str, stage: Optional[str] = None) -> List[Defect]:
    """Buscar defectos por palabra clave."""
    q = query.lower()
    results = []
    for d in DEFECT_DATABASE:
        if stage and d.stage != stage:
            continue
        if (q in d.name.lower() or
            q in d.description.lower() or
            any(q in s.lower() for s in d.symptoms) or
            any(q in c.lower() for c in d.causes)):
            results.append(d)
    return results


STAGE_INFO = {
    "substrate": {
        "title": "Preparación del Sustrato",
        "icon": "⏺️",
        "description": (
            "Preparación de núcleos de aluminio para recubrimiento de laca. "
            "Incluye limpieza, desengrase, tratamiento superficial, "
            "y promoción de adhesión para asegurar una unión adecuada de la laca."
        ),
        "key_parameters": [
            ("Rugosidad Superficial", "Ra 0.2-0.5 µm"),
            ("Solvente de Limpieza", "MEK or acetone"),
            ("Tiempo de Desengrase", "5-10 min ultrasonic"),
            ("Promotor de Adhesión", "Silane-based optional"),
            ("Almacenamiento", "Cleanroom, <40% RH"),
        ],
    },
    "formulation": {
        "title": "Formulación de Laca",
        "icon": "🧪",
        "description": (
            "Formulación de laca de nitrocelulosa para recubrimiento de discos. "
            "Mezcla de nitrocelulosa con solventes (ésteres, cetonas, alcoholes), "
            "plastificantes y aditivos para lograr la viscosidad objetivo, "
            "el contenido de sólidos y las propiedades de recubrimiento."
        ),
        "key_parameters": [
            ("Grado de Nitrocelulosa", "RS 1/4 sec - 1/2 sec"),
            ("Contenido de Sólidos", "25-35%"),
            ("Viscosidad", "800-2000 mPa·s"),
            ("Proporción de Solventes", "Esters:Ketones:Alcohols 5:3:2"),
            ("Plastificante", "DOP/DBP 10-20% of NC weight"),
        ],
    },
    "coating": {
        "title": "Aplicación de Recubrimiento",
        "icon": "🎨",
        "description": (
            "Aplicación de laca formulada sobre núcleos de aluminio. "
            "Utiliza recubridora por cortina Burkle o recubrimiento por giro para un "
            "espesor de capa uniforme. Ambiente controlado para recubrimiento libre de polvo."
        ),
        "key_parameters": [
            ("Método de Recubrimiento", "Curtain coating / Spin coating"),
            ("Espesor de Capa (húmedo)", "150-300 µm"),
            ("Velocidad de Cortina", "50-100 m/min"),
            ("Temperatura", "20-25°C"),
            ("Humedad", "<50% RH"),
        ],
    },
    "curing": {
        "title": "Curado y Secado",
        "icon": "🌡️",
        "description": (
            "Evaporación controlada de solventes y curado de laca. "
            "Secado gradual para prevenir empañamiento, piel de naranja, "
            "y estallido de solvente. Desarrollo de dureza final durante 24-48 horas."
        ),
        "key_parameters": [
            ("Secado Inicial", "1-2 hours at 20°C"),
            ("Curado Final", "24-48 hours at 20-25°C"),
            ("Intercambio de Aire", "10-15 vol/h"),
            ("Vapor de Solvente", "<50 ppm exhaust"),
            ("Dureza Final", "Shore D 65-75"),
        ],
    },
    "qc": {
        "title": "Control de Calidad",
        "icon": "🔍",
        "description": (
            "Inspección y pruebas de discos de laca terminados. "
            "Calidad superficial, uniformidad de espesor, adhesión, dureza, "
            "y defectos visuales. Discos clasificados para uso en corte."
        ),
        "key_parameters": [
            ("Inspección Visual", "100% under diffused light"),
            ("Tolerancia de Espesor", "±20 µm"),
            ("Defectos Superficiales", "Zero pinholes in center 200mm"),
            ("Prueba de Adhesión", "Cross-hatch tape test 4B+"),
            ("Dureza", "Shore D 65-75"),
        ],
    },
}
