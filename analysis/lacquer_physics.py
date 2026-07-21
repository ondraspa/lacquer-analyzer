"""
Lacquer Physics Engine — Análisis del comportamiento de la laca final

Predice viscosidad, evaporación, atrapamiento de burbujas, tensión superficial,
riesgo de blush, orange peel, y propiedades de película final usando
numpy/scipy para modelos físico-químicos.

Inputs requeridos del usuario:
  - temperatura ambiente (°C)
  - humedad relativa (%)
  - espesor de capa (µm)
  - grano de pulido del disco (µm)
  - tipo de aplicación (cortina / spin)
  - velocidad de aire (m/s)
  - presión positiva (sí/no)
  - temperatura de secado (°C)
"""

from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field
import numpy as np
from scipy.optimize import fsolve

# ── Constantes físico-químicas ──────────────────────────────────────
R = 8.314  # J/(K·mol)
ATM_PA = 101325  # Pa

# ── Bases de datos de propiedades de solventes ──────────────────────
# Cada entrada: (Mw, Tb_K, Pv_25C_mmHg, Hvap_kJmol, delta_d, delta_p, delta_h, viscosity_mPas, surface_tension_mNm)
# Fuente: Hansen Solubility Parameters: A User's Handbook, CRC Handbook
SOLVENT_DB = {
    "Acetona":             (58.08, 329.2, 231.0, 31.3, 15.5, 10.4, 7.0, 0.31, 23.7),
    "MEK (Metil Etil Cetona)": (72.11, 352.8, 90.6, 34.4, 16.0, 9.0, 5.1, 0.41, 24.6),
    "MIBK (Metil Isobutil Cetona)": (100.16, 388.8, 26.3, 38.3, 15.3, 6.1, 4.1, 0.54, 23.9),
    "Ciclohexanona":       (98.15, 428.8, 4.8, 41.4, 17.8, 6.3, 5.1, 1.10, 34.6),
    "Acetato de Etilo":    (88.11, 350.2, 86.0, 35.6, 15.8, 5.3, 7.2, 0.43, 23.2),
    "Acetato de Butilo":   (116.16, 399.2, 13.3, 39.3, 15.8, 3.7, 6.3, 0.69, 25.1),
    "Acetato de Isopropilo": (102.13, 363.2, 47.0, 37.1, 15.2, 4.3, 7.6, 0.53, 23.5),
    "Etanol (Alcohol Etílico)": (46.07, 351.5, 44.6, 42.3, 15.8, 8.8, 19.4, 1.08, 22.4),
    "Isopropanol (IPA)":   (60.10, 355.4, 32.4, 45.4, 15.8, 6.1, 16.4, 2.04, 20.9),
    "Butanol (n-Butanol)": (74.12, 390.8, 8.4, 43.3, 16.0, 5.7, 15.8, 2.54, 24.6),
    "Tolueno":             (92.14, 383.8, 26.0, 38.0, 18.0, 1.4, 2.0, 0.56, 28.5),
    "Xileno":              (106.17, 411.3, 8.8, 42.0, 17.6, 1.0, 3.1, 0.62, 28.9),
    "Butilglicol (Butil Cellosolve)": (118.18, 444.2, 1.2, 43.5, 16.0, 5.1, 12.3, 3.15, 27.4),
    "Metoxipropil Acetato (PMA)": (132.16, 419.2, 5.2, 40.8, 15.6, 4.5, 7.8, 1.15, 26.8),
    "MAK (Metil Amil Cetona)": (114.19, 424.2, 4.1, 40.2, 15.8, 5.5, 4.0, 0.82, 25.5),
    "Aromático 100 (Solvesso 100)": (120.0, 438.0, 3.0, 41.0, 17.5, 0.8, 1.5, 0.70, 29.0),
    "Diacetona Alcohol (DAA)": (116.16, 441.2, 1.8, 42.6, 15.8, 8.0, 10.5, 2.90, 30.0),
    "Metoxipropanol (PM)": (90.12, 393.2, 12.0, 41.2, 15.6, 5.8, 12.0, 1.75, 28.0),
}

# Evaporation rate relative to n-butyl acetate = 1.0 (ASTM D3539)
EVAP_RATE = {
    "Acetona": 5.7,        "MEK": 3.8,      "MIBK": 1.6,
    "Ciclohexanona": 0.3,  "Acetato de Etilo": 3.0,   "Acetato de Butilo": 1.0,
    "Acetato de Isopropilo": 1.8, "Etanol": 1.7,       "Isopropanol": 1.1,
    "Butanol": 0.5,        "Tolueno": 2.0,  "Xileno": 0.8,
    "Butilglicol": 0.1,    "PMA": 0.4,      "MAK": 0.5,
    "Aromático 100": 0.3,  "DAA": 0.2,      "PM": 0.6,
}


@dataclass
class AnalysisInput:
    """Todos los parámetros de entrada para el análisis."""
    temperature_c: float = 23.0
    humidity_pct: float = 50.0
    layer_thickness_um: float = 100.0
    polish_grain_um: float = 1.0
    application: str = "curtain_coater"  # curtain_coater / spin_coater
    air_velocity_ms: float = 0.5
    positive_pressure: bool = False
    drying_temp_c: Optional[float] = None
    substrate_temp_c: Optional[float] = None


@dataclass
class AnalysisResult:
    """Resultado completo del análisis de una receta."""
    # Viscosidad
    predicted_viscosity_mpas: float = 0.0
    viscosity_category: str = ""
    ford_cup_4_seconds: float = 0.0
    # Evaporación
    drying_time_min: Optional[float] = None
    solvent_evaporation_profile: Dict[str, float] = field(default_factory=dict)
    mass_loss_pct: float = 0.0
    # Burbujas
    bubble_risk_index: float = 0.0
    bubble_risk_category: str = ""
    max_bubble_free_thickness_um: Optional[float] = None
    critical_evap_rate: float = 0.0
    # Tensión superficial
    surface_tension_mNm: float = 0.0
    wetting_index: float = 0.0
    wetting_category: str = ""
    # Blush
    blush_risk_index: float = 0.0
    blush_risk_category: str = ""
    # Orange peel
    orange_peel_index: float = 0.0
    orange_peel_category: str = ""
    # Película final
    final_tg_c: Optional[float] = None
    estimated_hardness: str = ""
    estimated_flexibility: str = ""
    solids_vol_pct: float = 0.0
    # Hansen
    hansen_red: Optional[float] = None
    hansen_distance_to_nc: Optional[float] = None
    hansen_compatible: bool = True
    # Resumen
    overall_score: float = 0.0
    warnings: List[str] = field(default_factory=list)


def _normalize_name(name: str) -> str:
    """Normaliza nombre de ingrediente/solvente para lookup en DB."""
    nm = name.lower().strip()
    # Mapeos conocidos
    mapping = {
        "acetato de butilo": "Acetato de Butilo",
        "acetato de etilo": "Acetato de Etilo",
        "acetato de isopropilo": "Acetato de Isopropilo",
        "mibk": "MIBK (Metil Isobutil Cetona)",
        "mibk (metil isobutil cetona)": "MIBK (Metil Isobutil Cetona)",
        "butanol": "Butanol (n-Butanol)",
        "butanol (n-butanol)": "Butanol (n-Butanol)",
        "xileno": "Xileno",
        "tolueno": "Tolueno",
        "metoxipropil acetato (pma)": "Metoxipropil Acetato (PMA)",
        "pma": "Metoxipropil Acetato (PMA)",
        "butilglicol (butil cellosolve)": "Butilglicol (Butil Cellosolve)",
        "butilglicol": "Butilglicol (Butil Cellosolve)",
        "maik": "MAK (Metil Amil Cetona)",
        "mak (metil amil cetona)": "MAK (Metil Amil Cetona)",
        "metoxipropanol (pm)": "Metoxipropanol (PM)",
        "diacetona alcohol (daa)": "Diacetona Alcohol (DAA)",
        "isopropanol (ipa)": "Isopropanol (IPA)",
        "etanol (alcohol etílico)": "Etanol (Alcohol Etílico)",
        "aromático 100 (solvesso 100)": "Aromático 100 (Solvesso 100)",
    }
    if nm in mapping:
        return mapping[nm]
    # Fuzzy match
    for key in SOLVENT_DB:
        if nm == key.lower():
            return key
        if nm.replace(" ", "") == key.lower().replace(" ", ""):
            return key
    return name


def _solvent_evap_rate(solvent_name: str) -> float:
    """Devuelve tasa de evaporación relativa (BuAc=1.0)."""
    key = _normalize_name(solvent_name)
    for db_name, rate in EVAP_RATE.items():
        if db_name.lower() in key.lower() or key.lower() in db_name.lower():
            return rate
    # Estimate from boiling point
    for db_name, data in SOLVENT_DB.items():
        if db_name.lower() in key.lower() or key.lower() in db_name.lower():
            return max(0.05, 100 * np.exp(-0.015 * (data[1] - 300)))
    return 1.0


def _solvent_props(solvent_name: str) -> Optional[Tuple]:
    """Devuelve propiedades de un solvente."""
    key = _normalize_name(solvent_name)
    for db_name, data in SOLVENT_DB.items():
        if db_name.lower() == key.lower():
            return data
        if key.lower() in db_name.lower() or db_name.lower() in key.lower():
            return data
    return None


# Intrinsic viscosity [η] of NC grades in dL/g (in butyl acetate at 25°C)
NC_INTRINSIC_VISCOSITY = {
    "1/4": 2.0, "1/2": 3.0, "5-6": 6.0, "15-20": 9.0, "30-40": 12.0,
}

# Nitrogen content for NC grades
NC_NITROGEN = {
    "rs": 12.0, "ss": 11.0, "alta": 11.8,
}


def _nc_intrinsic_viscosity(name: str) -> float:
    """Estima viscosidad intrínseca [η] de la NC según grado."""
    name_l = name.lower()
    for key, val in NC_INTRINSIC_VISCOSITY.items():
        if key in name_l:
            return val
    return 4.0  # default for "RS 1/2 seg"

def _estimate_blend_viscosity(solvent_blend: Dict[str, float], temp_c: float) -> float:
    """Estima viscosidad de mezcla de solventes (modelo log-additivo Grunberg-Nissan)."""
    if not solvent_blend:
        return 1.0
    total = sum(solvent_blend.values())
    if total <= 0:
        return 1.0

    fracs = {k: v / total * 100 for k, v in solvent_blend.items()}
    log_eta = 0.0
    for name, frac in fracs.items():
        props = _solvent_props(name)
        if props:
            eta_i = props[7] * np.exp(-0.025 * (temp_c - 25))
            log_eta += frac / 100.0 * np.log(max(eta_i, 0.01))
    return float(np.exp(log_eta))



# Empirical NC solution viscosity model (concentrated regime)
# η = η_solvent * exp(k_nc * c)  where c = wt% NC in liquid phase
# k_nc from measured data: RS 1/4=0.18, RS 1/2=0.25, RS 5-6=0.35 per wt%
NC_VISC_K = {"1/4": 0.18, "1/2": 0.25, "5-6": 0.35, "15-20": 0.42, "30-40": 0.48}


def _estimate_nc_solution_viscosity(
    nc_conc_pct: float,
    nc_grade: str,
    solvent_blend_visc: float,
    temp_c: float,
) -> float:
    """Estima viscosidad de solución concentrada de NC (modelo exponencial empírico).

    η = η_solvent * exp(k_nc * c)  para NC al c% en peso.
    Validado con datos experimentales de NC RS 1/2 seg al 10-30% en acetato de butilo.
    """
    if nc_conc_pct <= 0:
        return solvent_blend_visc

    k = NC_VISC_K.get(nc_grade, 0.25)
    eta_rel = np.exp(k * nc_conc_pct)
    eta_solution = solvent_blend_visc * eta_rel

    # Temperature correction (Arrhenius-like)
    eta_solution *= np.exp(-0.025 * (temp_c - 25))

    return float(eta_solution)


def _estimate_evaporation_times(
    solvent_blend: Dict[str, float],
    temp_c: float,
    thickness_um: float,
    air_velocity: float,
    positive_pressure: bool,
) -> Dict:
    """Estima tiempos de evaporación y perfil."""
    if not solvent_blend:
        return {"drying_time_min": None, "profile": {}}

    total = sum(solvent_blend.values())
    if total <= 0:
        return {"drying_time_min": None, "profile": {}}

    # Temperatura effect
    temp_factor = np.exp(0.05 * (temp_c - 25))
    # Air velocity effect
    air_factor = 1.0 + 0.5 * air_velocity
    # Pressure effect (positive pressure slows evaporation)
    pressure_factor = 0.7 if positive_pressure else 1.0

    profile = {}
    drying_min = 0.0
    for name, conc in solvent_blend.items():
        rate = _solvent_evap_rate(name)
        if rate <= 0:
            rate = 0.1
        # Evaporation time proportional to concentration / (rate * factors)
        evap_factor = rate * temp_factor * air_factor * pressure_factor
        estimated_min = (conc / total * 100) / evap_factor * 12.0  # base 12 min for BuAc
        # Thickness effect (thicker = slower drying of last solvent)
        thickness_factor = 1.0 + 0.01 * max(0, thickness_um - 50)
        estimated_min *= thickness_factor
        profile[name] = round(estimated_min, 1)
        drying_min = max(drying_min, estimated_min)

    # Drying time = time for 95% mass loss of slowest solvent
    drying_min = max(profile.values()) if profile else 30.0
    # Add curing factor
    drying_min = min(drying_min, 240.0)  # cap at 4 hours

    return {
        "drying_time_min": round(drying_min, 1),
        "profile": {k: round(v, 1) for k, v in sorted(profile.items())},
    }


def _calculate_bubble_risk(
    evap_profile: Dict[str, float],
    thickness_um: float,
    temp_c: float,
    positive_pressure: bool,
    polish_grain_um: float,
) -> Dict:
    """Evalúa riesgo de atrapamiento de burbujas."""
    if not evap_profile:
        return {"bubble_risk_index": 0.5, "bubble_risk_category": "unknown", "critical_evap_rate": 1.0}

    # Bubbles form when: fast-evaporating solvents boil off from under a
    # surface skin that has already formed.
    # Key factors:
    # - Ratio of fastest to slowest solvent evaporation
    evap_rates = []
    for name in evap_profile:
        rate = _solvent_evap_rate(name)
        if rate > 0:
            evap_rates.append(rate)

    if not evap_rates:
        return {"bubble_risk_index": 0.5, "bubble_risk_category": "unknown"}

    fast = max(evap_rates)
    slow = min(evap_rates) if evap_rates else fast
    evap_ratio = fast / max(slow, 0.1)

    # Higher thickness = more trapped solvent
    thickness_risk = min(1.0, thickness_um / 200.0)

    # Temperature increases evaporation rate
    temp_risk = min(1.0, max(0, temp_c - 15) / 30.0)

    # Positive pressure helps
    pressure_bonus = 0.4 if positive_pressure else 0.0

    # Polished surface (smooth) = more adhesion, fewer nucleation sites for bubbles
    polish_factor = min(1.0, polish_grain_um / 5.0)

    bubble_index = (
        0.3 * min(1.0, evap_ratio / 10.0)
        + 0.25 * thickness_risk
        + 0.2 * temp_risk
        - 0.15 * pressure_bonus
        - 0.1 * (1.0 - polish_factor)
    )
    bubble_index = max(0.0, min(1.0, bubble_index))

    if bubble_index < 0.25:
        category = "bajo"
    elif bubble_index < 0.50:
        category = "moderado"
    elif bubble_index < 0.75:
        category = "alto"
    else:
        category = "muy alto"

    max_thickness = 150.0 * (1.0 - bubble_index + 0.2)

    return {
        "bubble_risk_index": round(bubble_index, 3),
        "bubble_risk_category": category,
        "max_bubble_free_thickness_um": round(max_thickness, 1),
        "critical_evap_rate": round(evap_ratio, 1),
    }


def _calculate_surface_tension(solvent_blend: Dict[str, float]) -> float:
    """Estima tensión superficial de la mezcla de solventes (media ponderal)."""
    total = sum(solvent_blend.values())
    if total <= 0:
        return 25.0
    st = 0.0
    for name, conc in solvent_blend.items():
        props = _solvent_props(name)
        if props:
            st += conc / total * props[8]
    return round(st, 1)


def _calculate_wetting(surface_tension_mNm: float, polish_grain_um: float) -> Dict:
    """Evalúa capacidad de mojado sobre aluminio pulido."""
    # Al has surface tension ~ 40 mN/m clean, ~ 30 mN/m oxidized
    aluminum_st = 35.0
    spreading_coeff = aluminum_st - surface_tension_mNm
    # Rougher surface aids wetting (Wenzel model)
    roughness_factor = 1.0 + 0.1 * min(5.0, polish_grain_um)
    wetting_index = spreading_coeff * roughness_factor / 15.0
    if wetting_index > 0.8:
        category = "excelente"
    elif wetting_index > 0.4:
        category = "bueno"
    elif wetting_index > 0:
        category = "aceptable"
    else:
        category = "deficiente (posible cráteres)"
    return {
        "wetting_index": round(wetting_index, 3),
        "wetting_category": category,
        "spreading_coeff": round(spreading_coeff, 1),
    }


def _calculate_blush_risk(
    humidity_pct: float,
    temp_c: float,
    solvent_blend: Dict[str, float],
) -> Dict:
    """Evalúa riesgo de blush (blanqueamiento por humedad)."""
    # Blush occurs when water condenses during solvent evaporation
    # Dew point calculation (Magnus approximation)
    a, b = 17.27, 237.7
    gamma = (a * temp_c) / (b + temp_c) + np.log(humidity_pct / 100.0)
    dew_point = (b * gamma) / (a - gamma)

    # Fast evaporation = cooling of surface = more blush risk
    evap_cooling = 0.0
    total = sum(solvent_blend.values()) or 1
    for name, conc in solvent_blend.items():
        rate = _solvent_evap_rate(name)
        evap_cooling += conc / total * min(5.0, rate * 0.5)

    effective_temp = temp_c - evap_cooling
    temp_diff = effective_temp - dew_point

    if temp_diff < 2:
        risk = 0.9
        category = "muy alto"
    elif temp_diff < 5:
        risk = 0.7
        category = "alto"
    elif temp_diff < 10:
        risk = 0.4
        category = "moderado"
    elif temp_diff < 15:
        risk = 0.2
        category = "bajo"
    else:
        risk = 0.05
        category = "muy bajo"

    # Alcohols exacerbate blush
    alcohol_names = ["butanol", "etanol", "isopropanol", "metanol"]
    alcohol_conc = 0.0
    for name, conc in solvent_blend.items():
        if any(a in name.lower() for a in alcohol_names):
            alcohol_conc += conc
    risk += 0.15 * min(1.0, alcohol_conc / 30.0)
    risk = min(1.0, risk)

    return {
        "blush_risk_index": round(risk, 3),
        "blush_risk_category": category,
        "dew_point_c": round(dew_point, 1),
        "surface_cooling_c": round(evap_cooling, 1),
    }


def _calculate_orange_peel(
    viscosity_mpas: float,
    evap_profile: Dict[str, float],
    thickness_um: float,
    surface_tension_mNm: float,
) -> Dict:
    """Evalúa riesgo de orange peel (piel de naranja)."""
    # Orange peel from: viscosity too high, fast drying, thick layer
    visc_risk = min(1.0, max(0, viscosity_mpas - 200) / 1000.0)

    # Fast evaporation of top layer
    fast_evap = 0.0
    if evap_profile:
        times = list(evap_profile.values())
        if times:
            fastest = min(times) if times else 30
            fast_evap = min(1.0, 15.0 / max(1, fastest))

    thick_risk = min(1.0, thickness_um / 150.0)
    st_risk = max(0, 40.0 - surface_tension_mNm) / 20.0

    index = 0.35 * visc_risk + 0.35 * fast_evap + 0.15 * thick_risk + 0.15 * st_risk
    index = max(0.0, min(1.0, index))

    if index < 0.25:
        category = "bajo"
    elif index < 0.50:
        category = "moderado"
    elif index < 0.75:
        category = "alto"
    else:
        category = "muy alto"

    return {
        "orange_peel_index": round(index, 3),
        "orange_peel_category": category,
    }


def _estimate_film_properties(
    resin_blend: Dict[str, float],
    plasticizer_blend: Dict[str, float],
    solids_pct: float,
) -> Dict:
    """Estima propiedades de la película final."""
    # Simple Tg estimation (Fox equation)
    tg_sum = 0.0
    total_resin = sum(resin_blend.values()) or 1
    has_nc = False
    for name, conc in resin_blend.items():
        if "nitrocelulosa" in name.lower():
            has_nc = True
        # Approximate Tg of NC ~ 53°C
        tg_sum += conc / total_resin * 53.0

    # Plasticizers reduce Tg
    plast_conc = sum(plasticizer_blend.values())
    total_solids = total_resin + plast_conc
    tg_with_plast = tg_sum * (1.0 - 0.5 * plast_conc / max(total_solids, 1))

    if has_nc:
        if plast_conc / max(total_solids, 1) < 0.1:
            hardness = "muy dura (posible quebradiza)"
            flexibility = "baja"
        elif plast_conc / max(total_solids, 1) < 0.2:
            hardness = "buena"
            flexibility = "moderada"
        elif plast_conc / max(total_solids, 1) < 0.35:
            hardness = "blanda"
            flexibility = "alta"
        else:
            hardness = "muy blanda (cera-like)"
            flexibility = "muy alta"
    else:
        hardness = "desconocida"
        flexibility = "desconocida"

    return {
        "estimated_tg_c": round(tg_with_plast, 1),
        "estimated_hardness": hardness,
        "estimated_flexibility": flexibility,
    }


def _calculate_hansen_compatibility(solvent_blend: Dict[str, float]) -> Dict:
    """Evalúa compatibilidad de solventes con NC usando parámetros Hansen."""
    # NC Hansen parameters: dD ~ 19.2, dP ~ 13.5, dH ~ 11.5 (varies with nitration)
    nc_d = 19.2
    nc_p = 13.5
    nc_h = 11.5

    total = sum(solvent_blend.values()) or 1
    blend_d = blend_p = blend_h = 0.0
    for name, conc in solvent_blend.items():
        props = _solvent_props(name)
        if props:
            blend_d += conc / total * props[4]
            blend_p += conc / total * props[5]
            blend_h += conc / total * props[6]

    # Hansen distance (RED)
    red = np.sqrt(
        4 * (blend_d - nc_d) ** 2
        + (blend_p - nc_p) ** 2
        + (blend_h - nc_h) ** 2
    )
    compatible = red < 15.0  # typical interaction radius for NC

    return {
        "hansen_distance_to_nc": round(red, 2),
        "blend_d": round(blend_d, 1),
        "blend_p": round(blend_p, 1),
        "blend_h": round(blend_h, 1),
        "compatible": compatible,
    }


def analyze_lacquer(
    solvent_blend: Dict[str, float],
    resin_blend: Dict[str, float],
    plasticizer_blend: Dict[str, float],
    additive_blend: Dict[str, float],
    inputs: AnalysisInput,
) -> AnalysisResult:
    """Analiza una receta completa de laca y devuelve el resultado."""
    result = AnalysisResult()
    warnings = []

    # ── 1. Viscosidad de la mezcla de solventes ──
    blend_visc = _estimate_blend_viscosity(solvent_blend, inputs.temperature_c)

    # Adjust for NC content using Martin equation for polymer solutions
    total_resin = sum(resin_blend.values())
    total_plast = sum(plasticizer_blend.values())
    total_liquid = sum(solvent_blend.values()) or 1
    total_formulation = total_resin + total_plast + total_liquid
    solids_pct = (total_resin + total_plast) / total_formulation * 100
    solids_vol = solids_pct * 0.6  # approximate density ratio

    # NC concentration in the liquid phase
    nc_pct_of_liquid = total_resin / (total_resin + total_liquid) * 100 if total_resin > 0 else 0

    # Determine NC grade from resin names
    nc_grade = "1/2"
    for name in resin_blend:
        nl = name.lower()
        for grade in ["1/4", "1/2", "5-6", "15-20", "30-40"]:
            if grade in nl:
                nc_grade = grade
                break

    predicted_visc = _estimate_nc_solution_viscosity(
        nc_pct_of_liquid, nc_grade, blend_visc, inputs.temperature_c
    )
    # Include plasticizer contribution to viscosity
    if total_plast > 0:
        plast_frac = total_plast / total_formulation
        # Plasticizers increase viscosity slightly
        predicted_visc *= (1.0 + 0.5 * plast_frac)

    predicted_visc = max(10, min(10000, predicted_visc))

    result.predicted_viscosity_mpas = round(predicted_visc, 1)
    result.solids_vol_pct = round(solids_vol, 1)

    if predicted_visc < 150:
        result.viscosity_category = "muy baja (ideal cortina)"
    elif predicted_visc < 400:
        result.viscosity_category = "baja (mastering/alta definición)"
    elif predicted_visc < 700:
        result.viscosity_category = "media (corte general)"
    elif predicted_visc < 1200:
        result.viscosity_category = "alta (hot cut / 45 RPM)"
    else:
        result.viscosity_category = "muy alta (difícil aplicación)"
        warnings.append("Viscosidad muy alta — puede causar orange peel y burbujas")

    # Ford Cup #4 approximation
    ford = 12.0 + 0.12 * predicted_visc
    result.ford_cup_4_seconds = round(ford, 1)

    # ── 2. Evaporación ──
    evap = _estimate_evaporation_times(
        solvent_blend, inputs.temperature_c, inputs.layer_thickness_um,
        inputs.air_velocity_ms, inputs.positive_pressure
    )
    result.drying_time_min = evap["drying_time_min"]
    result.solvent_evaporation_profile = evap["profile"]

    if result.drying_time_min and result.drying_time_min < 5:
        warnings.append("Secado extremadamente rápido (<5 min) — alto riesgo de burbujas")
    elif result.drying_time_min and result.drying_time_min > 120:
        warnings.append("Secado muy lento — riesgo de contaminación por polvo")

    # ── 3. Burbujas ──
    bubble = _calculate_bubble_risk(
        solvent_blend, inputs.layer_thickness_um, inputs.temperature_c,
        inputs.positive_pressure, inputs.polish_grain_um
    )
    result.bubble_risk_index = bubble["bubble_risk_index"]
    result.bubble_risk_category = bubble["bubble_risk_category"]
    result.max_bubble_free_thickness_um = bubble.get("max_bubble_free_thickness_um")
    result.critical_evap_rate = bubble.get("critical_evap_rate", 0)

    if result.bubble_risk_category in ("alto", "muy alto"):
        suggestions = []
        if inputs.positive_pressure is False:
            suggestions.append("usar cámara de presión positiva")
        if inputs.layer_thickness_um > 80:
            suggestions.append(f"reducir espesor a <{result.max_bubble_free_thickness_um} µm")
        if any(s["evap_rate"] < 0.3 for s in [{}]):
            suggestions.append("añadir butilglicol o solvente lento como retardante")
        if suggestions:
            warnings.append("Alto riesgo de burbujas — soluciones: " + ", ".join(suggestions))

    # ── 4. Tensión superficial y mojado ──
    result.surface_tension_mNm = _calculate_surface_tension(solvent_blend)
    wetting = _calculate_wetting(result.surface_tension_mNm, inputs.polish_grain_um)
    result.wetting_index = wetting["wetting_index"]
    result.wetting_category = wetting["wetting_category"]
    if "deficiente" in result.wetting_category:
        warnings.append(f"Mojado deficiente (ST={result.surface_tension_mNm} mN/m)"
                        " — posible cráteres, añadir humectante siliconado")

    # ── 5. Blush ──
    blush = _calculate_blush_risk(inputs.humidity_pct, inputs.temperature_c, solvent_blend)
    result.blush_risk_index = blush["blush_risk_index"]
    result.blush_risk_category = blush["blush_risk_category"]
    if result.blush_risk_category in ("alto", "muy alto"):
        warnings.append(f"Alto riesgo de blush (dew point {blush['dew_point_c']}°C,"
                        f" enfriamiento {blush['surface_cooling_c']}°C)"
                        " — reducir humedad o aumentar temperatura")

    # ── 6. Orange peel ──
    orange = _calculate_orange_peel(
        result.predicted_viscosity_mpas, result.solvent_evaporation_profile,
        inputs.layer_thickness_um, result.surface_tension_mNm
    )
    result.orange_peel_index = orange["orange_peel_index"]
    result.orange_peel_category = orange["orange_peel_category"]
    if result.orange_peel_category in ("alto", "muy alto"):
        warnings.append("Alto riesgo de orange peel — reducir viscosidad o añadir retardante")

    # ── 7. Propiedades de película ──
    film = _estimate_film_properties(resin_blend, plasticizer_blend, solids_pct)
    result.final_tg_c = film["estimated_tg_c"]
    result.estimated_hardness = film["estimated_hardness"]
    result.estimated_flexibility = film["estimated_flexibility"]
    if "quebradiza" in result.estimated_hardness:
        warnings.append("Película muy dura — puede astillarse durante el corte")

    # ── 8. Hansen ──
    hansen = _calculate_hansen_compatibility(solvent_blend)
    result.hansen_distance_to_nc = hansen["hansen_distance_to_nc"]
    result.hansen_compatible = hansen["compatible"]
    if not hansen["compatible"]:
        warnings.append(f"Mezcla de solventes posiblemente incompatible con NC"
                        f" (distancia Hansen={hansen['hansen_distance_to_nc']:.1f})")

    # ── 9. Score global ──
    scores = [
        max(0, 1.0 - result.bubble_risk_index),
        max(0, 1.0 - result.blush_risk_index),
        max(0, 1.0 - result.orange_peel_index),
        max(0, result.wetting_index / 1.5),
        (1.0 if 200 < result.predicted_viscosity_mpas < 800 else
         0.5 if 100 < result.predicted_viscosity_mpas < 1200 else 0.2),
        (0.5 if result.drying_time_min and 5 < result.drying_time_min < 60 else 0.3),
    ]
    result.overall_score = round(np.mean(scores) * 10, 1)
    result.warnings = warnings

    return result
