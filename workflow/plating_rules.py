"""Lacquer coating formulation analysis"""

from typing import List, Optional
from dataclasses import dataclass, field

from core.models import (
    RecipeComponent, LacquerRecipe, CoatingAnalysis,
    AnalysisResult, Ingredient, IngredientType
)


class LacquerAnalyzer:
    """Analyzes lacquer formulations for coating compatibility, solvent balance, and defect risk."""

    def __init__(self):
        self._solvent_types = {
            IngredientType.ACTIVE_SOLVENT,
            IngredientType.TAIL_SOLVENT,
        }

    def analyze_recipe(self, recipe: LacquerRecipe) -> AnalysisResult:
        coating = self._analyze_coating(recipe)
        issues = list(coating.issues)
        suggestions = list(coating.recommendations)
        return AnalysisResult(
            recipe=recipe,
            coating_analysis=coating,
            overall_risk=coating.overall_risk,
            formulation_issues=issues,
            suggested_modifications=suggestions,
        )

    def _analyze_coating(self, recipe: LacquerRecipe) -> CoatingAnalysis:
        issues: List[str] = []
        recommendations: List[str] = []

        solids = recipe.total_solids()
        viscosity = recipe.estimated_viscosity()
        solvent_balance = self._classify_solvent_balance(recipe)
        blush_risk = self._estimate_blush_risk(recipe)
        solvency = self._check_solvency(recipe)

        if solvent_balance == "fast":
            issues.append("Solvent blend evaporates too fast — may cause blush, orange peel")
            recommendations.append("Add tail solvent (e.g., butyl acetate, ethylene glycol) to slow evaporation")
        elif solvent_balance == "slow":
            issues.append("Solvent blend evaporates too slowly — may cause runs, sagging")
            recommendations.append("Add active solvent (e.g., ethyl acetate, MEK) to speed evaporation")

        if blush_risk == "high":
            issues.append("High blush risk — condensate may form in humid conditions")
            recommendations.append("Use slower-evaporating solvents or raise ambient temperature")
        elif blush_risk == "medium":
            recommendations.append("Monitor humidity during coating — moderate blush risk")

        if solvency == "poor":
            issues.append("Poor solvency — resin may not fully dissolve")
            recommendations.append("Add active solvent (ethyl acetate, MEK) to improve solvency")
        elif solvency == "fair":
            recommendations.append("Consider boosting solvency with additional active solvent")

        if recipe.target_solids_pct:
            diff = solids - recipe.target_solids_pct
            if abs(diff) > 2:
                issues.append(f"Solids content {solids:.1f}% differs from target {recipe.target_solids_pct:.1f}%")
                if diff > 0:
                    recommendations.append(f"Dilute with {diff:.1f} pts solvent to reach target")
                else:
                    recommendations.append(f"Add {-diff:.1f} pts resin solids to reach target")

        if recipe.target_viscosity_mpas:
            vr = viscosity / recipe.target_viscosity_mpas
            if vr < 0.7:
                issues.append(f"Viscosity {viscosity:.0f} mPa·s is below target {recipe.target_viscosity_mpas:.0f} mPa·s")
                recommendations.append("Increase resin or thickener concentration")
            elif vr > 1.3:
                issues.append(f"Viscosity {viscosity:.0f} mPa·s is above target {recipe.target_viscosity_mpas:.0f} mPa·s")
                recommendations.append("Dilute with solvent to reduce viscosity")

        if solids < 15:
            recommendations.append("Low solids — may need multiple coats for coverage")
        elif solids > 50:
            recommendations.append("High solids — check leveling and film uniformity")

        leveling = self._estimate_leveling(recipe)

        return CoatingAnalysis(
            solvent_balance=solvent_balance,
            blush_risk=blush_risk,
            solvency_quality=solvency,
            estimated_solids_pct=solids,
            estimated_viscosity_mpas=viscosity,
            leveling_quality=leveling,
            issues=issues,
            recommendations=recommendations,
        )

    def _classify_solvent_balance(self, recipe: LacquerRecipe) -> str:
        fast = 0.0
        slow = 0.0
        for comp in recipe.components:
            ing = comp.ingredient
            if ing.type not in self._solvent_types:
                continue
            ev = ing.coating_properties.evaporation_rate
            if ev is None:
                continue
            if ev > 3.0:
                fast += comp.concentration_pct
            elif ev < 1.0:
                slow += comp.concentration_pct
        total = fast + slow
        if total == 0:
            return "balanced"
        fast_ratio = fast / total
        if fast_ratio > 0.6:
            return "fast"
        if fast_ratio < 0.2:
            return "slow"
        return "balanced"

    def _estimate_blush_risk(self, recipe: LacquerRecipe) -> str:
        fast_pct = 0.0
        total_solvent = 0.0
        for comp in recipe.components:
            ing = comp.ingredient
            if ing.type not in self._solvent_types:
                continue
            total_solvent += comp.concentration_pct
            ev = ing.coating_properties.evaporation_rate
            if ev is None or ev <= 3.0:
                continue
            fast_pct += comp.concentration_pct
        if total_solvent == 0:
            return "low"
        ratio = fast_pct / total_solvent
        if ratio > 0.5:
            return "high"
        if ratio > 0.3:
            return "medium"
        return "low"

    def _check_solvency(self, recipe: LacquerRecipe) -> str:
        has_active = False
        for comp in recipe.components:
            if comp.ingredient.type == IngredientType.ACTIVE_SOLVENT:
                has_active = True
                break
        if not has_active:
            return "poor"
        active_pct = sum(
            comp.concentration_pct for comp in recipe.components
            if comp.ingredient.type == IngredientType.ACTIVE_SOLVENT
        )
        if active_pct < 10:
            return "fair"
        return "good"

    def _estimate_leveling(self, recipe: LacquerRecipe) -> str:
        has_leveling = any(
            comp.ingredient.type == IngredientType.LEVELING
            for comp in recipe.components
        )
        has_wetting = any(
            comp.ingredient.type == IngredientType.WETTING
            for comp in recipe.components
        )
        if has_leveling and has_wetting:
            return "excellent"
        if has_leveling or has_wetting:
            return "good"
        viscosity = recipe.estimated_viscosity()
        if viscosity < 200:
            return "good"
        if viscosity < 800:
            return "fair"
        return "poor"

    def is_ingredient_allowed(self, ingredient: Ingredient) -> bool:
        return True
