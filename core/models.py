"""Core data models for Lacquer Analyzer"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import yaml


class IngredientType(Enum):
    BASE_RESIN = "base_resin"
    ACTIVE_SOLVENT = "active_solvent"
    TAIL_SOLVENT = "tail_solvent"
    LEVELING = "leveling"
    DEFOAMER = "defoamer"
    ADHESION = "adhesion"
    UV_STABILIZER = "uv_stabilizer"
    WETTING = "wetting"
    WHITE_PIGMENT = "white_pigment"
    BLACK_PIGMENT = "black_pigment"
    COLOR_PIGMENT = "color_pigment"
    SILVERING = "silvering"
    NICKEL_SULFAMATE = "nickel_sulfamate"
    PROCESS = "process"


class ApplicationMethod(Enum):
    CURTAIN = "curtain"
    SPIN = "spin"
    FLOW = "flow"


@dataclass
class IngredientProperties:
    surface_tension_dynes: float = 35.0
    solids_content_pct: Optional[float] = None
    viscosity_mpas: Optional[float] = None
    evaporation_rate: Optional[float] = None
    solvency_parameter: Optional[float] = None
    notes: str = ""


@dataclass
class Ingredient:
    id: str
    name: str
    type: IngredientType
    properties: Dict[str, Any] = field(default_factory=dict)
    coating_properties: IngredientProperties = field(default_factory=IngredientProperties)
    dosage_pct: Optional[float] = None
    max_concentration_pct: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_yaml(cls, data: dict) -> 'Ingredient':
        props = data.get('properties', {})
        coating = IngredientProperties(
            surface_tension_dynes=props.get('surface_tension_dynes', data.get('surface_tension_dynes', 35.0)),
            solids_content_pct=props.get('solids_content_pct', data.get('solids_content')),
            viscosity_mpas=props.get('viscosity_mpas', data.get('viscosity_mpas')),
            evaporation_rate=props.get('evaporation_rate', data.get('evaporation_rate')),
            solvency_parameter=props.get('solvency_parameter', data.get('solvency_parameter')),
            notes=props.get('notes', '')
        )
        return cls(
            id=data['id'],
            name=data['name'],
            type=IngredientType(data['type']),
            coating_properties=coating,
            properties={k: v for k, v in data.items()
                       if k not in ['id', 'name', 'type', 'compatible_plating',
                                   'dosage_pct', 'max_concentration_pct', 'warnings', 'notes']},
            dosage_pct=data.get('dosage_pct'),
            max_concentration_pct=data.get('max_concentration_pct'),
            warnings=data.get('warnings', []),
            notes=data.get('notes', '')
        )


@dataclass
class RecipeComponent:
    ingredient: Ingredient
    concentration_pct: float
    notes: str = ""

    @property
    def is_within_limits(self) -> bool:
        if self.ingredient.max_concentration_pct:
            return self.concentration_pct <= self.ingredient.max_concentration_pct
        return True


@dataclass
class LacquerRecipe:
    id: str
    name: str
    components: List[RecipeComponent] = field(default_factory=list)
    target_viscosity_mpas: Optional[float] = None
    target_solids_pct: Optional[float] = None
    application_method: str = "curtain_coater"
    coater_type: str = "burkle"
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def total_solids(self) -> float:
        total_concentration = sum(c.concentration_pct for c in self.components) or 100
        total = 0.0
        for comp in self.components:
            if comp.ingredient.type in (IngredientType.BASE_RESIN, IngredientType.WHITE_PIGMENT, IngredientType.BLACK_PIGMENT, IngredientType.COLOR_PIGMENT):
                solids = comp.ingredient.coating_properties.solids_content_pct
                if solids is None:
                    solids = comp.ingredient.properties.get('solids_content', 100)
            else:
                solids = 0
            total += comp.concentration_pct * (solids / 100)
        return total / total_concentration * 100

    def estimated_viscosity(self) -> float:
        total = 0.0
        weight_sum = 0.0
        for comp in self.components:
            ing = comp.ingredient
            visc = ing.coating_properties.viscosity_mpas
            if visc is None:
                visc = ing.properties.get('viscosity_mpas', 1000)
            total += comp.concentration_pct * visc
            weight_sum += comp.concentration_pct
        return total / weight_sum if weight_sum > 0 else 0

    def get_composition_by_type(self) -> Dict[IngredientType, float]:
        result = {}
        for comp in self.components:
            t = comp.ingredient.type
            result[t] = result.get(t, 0) + comp.concentration_pct
        return result


@dataclass
class CoatingAnalysis:
    solvent_balance: str = "balanced"
    blush_risk: str = "low"
    solvency_quality: str = "good"
    estimated_solids_pct: float = 0.0
    estimated_viscosity_mpas: float = 0.0
    leveling_quality: str = "good"
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    @property
    def overall_risk(self) -> str:
        if self.blush_risk == "high" or self.solvency_quality == "poor":
            return "HIGH"
        if self.blush_risk == "medium" or self.solvency_quality == "fair":
            return "MEDIUM"
        return "LOW"


@dataclass
class AnalysisResult:
    recipe: LacquerRecipe
    coating_analysis: CoatingAnalysis
    overall_risk: str = "LOW"
    suggested_modifications: List[str] = field(default_factory=list)
    formulation_issues: List[str] = field(default_factory=list)
