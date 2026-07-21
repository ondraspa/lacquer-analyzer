"""Load ingredients from YAML configuration files"""

from pathlib import Path
from typing import Dict, List, Optional
import yaml
from core.models import Ingredient, IngredientType


class IngredientLoader:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._ingredients: List[Ingredient] = []
        self._ingredients_by_id: Dict[str, Ingredient] = {}
        self._ingredients_by_name: Dict[str, Ingredient] = {}

    def load_all(self) -> List[Ingredient]:
        self._ingredients.clear()
        self._ingredients_by_id.clear()
        self._ingredients_by_name.clear()

        yaml_files = [
            self.config_dir / "ingredients.yaml",
            self.config_dir / "custom_ingredients.yaml",
        ]

        for path in yaml_files:
            if path.exists():
                self._load_file(path)

        return self._ingredients

    def _load_file(self, path: Path):
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        if not data:
            return

        for category in ["resins", "solvents", "additives", "pigments", "plating"]:
            if category not in data:
                continue
            for item in data[category]:
                ingredient = Ingredient.from_yaml(item)
                self._ingredients.append(ingredient)
                self._ingredients_by_id[ingredient.id] = ingredient
                self._ingredients_by_name[ingredient.name.lower()] = ingredient

    def get_by_id(self, id: str) -> Optional[Ingredient]:
        return self._ingredients_by_id.get(id)

    def get_by_name(self, name: str) -> Optional[Ingredient]:
        return self._ingredients_by_name.get(name.lower())

    def get_by_type(self, type: IngredientType) -> List[Ingredient]:
        return [i for i in self._ingredients if i.type == type]

    def all_types(self) -> Dict[str, List[Ingredient]]:
        types = {}
        for ing in self._ingredients:
            key = ing.type.value
            if key not in types:
                types[key] = []
            types[key].append(ing)
        return types
