# UI Architecture Map — Lacquer Chemical Analyzer

## Main Window (`ui/main_window.py`)
- **Size**: 1200x800 default
- **Layout**: VBox → Toolbar + QTabWidget + StatusBar
- **5 Tabs**:
  0. 🧪 Formulación (`CuttingStageWidget`)
  1. ⚡ Galvánica (`GalvanicsWorkspace`)
  2. 🔄 Prensado (`PressingWorkspace`)
  3. 🔍 Control de Calidad (`PipelineStageWidget("qc")`)
  4. 🧠 Conocimiento (`KnowledgeHub`)
- **Toolbar** (7 items): LLM status, KB status, Expert Notes, RAG Config, Generate Recipe, Language EN/ES
- **Menus**: Archivo (Import/Export/Salir), Herramientas (9 items), Ayuda (Acerca de)

## Tab 0: Formulación (`ui/pipeline/cutting_stage.py`)
- **Horizontal QSplitter [400, 500]**
- **Left Panel**:
  - QTabWidget:
    - Tab 0: `IngredientBrowserWidget` (tree + search + edit/add)
    - Tab 1: `PigmentSearchWidget` (search + add to recipe)
    - Tab 2: `SpecialChemSearchWidget` (PubChem/Wikipedia/SpecialChem multi-source)
  - `TroubleshootingPanel` (stretch)
- **Right Panel**:
  - QTabWidget:
    - Tab 0: `RecipeEditorWidget` (4 sub-tabs)
    - Tab 1: `AnalysisPanelWidget` (analysis results)
  - `KnowledgeQAPanel` (LLM Q&A, stretch)

## Recipe Editor (`ui/workspace/recipe_editor.py`)
- **Header**: Preset selector dropdown + recipe name + target viscosity/solids
- **4 Internal Tabs**:
  1. **Componentes**: Ingredient selector combo + add button + 4-column table (Ingredient, Type, Conc%, Max%) + remove/clear/save-preset buttons
  2. **Pros/Contras & Hardware**: Metadata display (read-only QTextEdit) + translate button
  3. **Análisis de Laca**: `RecipeAnalysisPanel` (scrollable: input params → analyze button → results)
  4. **Comparar Recetas**: `RecipeComparisonWidget` (two selectors + compare button + 3 sub-tabs: composition/properties/full analysis)

## Analysis Panel (`ui/workspace/recipe_analysis_panel.py`)
- **AnalysisInputPanel**: 7 fields (temp, humidity, thickness, polish, airflow, application type, pressure checkbox)
- **AnalysisResultWidget**: 4 result tabs (viscosity/film, evaporation, defects, wetting/Hansen) + score bar + warnings with translate

## Comparison Widget (`ui/workspace/recipe_comparison.py`)
- Two recipe selectors + compare button
- 3 sub-tabs: Composition (5-col diff table), Properties (14-row table), Full Analysis (side-by-side)

## Tab 1: Galvánica (`ui/workspace/galvanics_workspace.py`)
- 3 tabs: Bath Parameters (silver + nickel + surface prep), Compatibility Overview, Q&A

## Tab 2: Prensado (`ui/workspace/pressing_workspace.py`)
- Parameters (press temp/pressure/time, cooling, mold, release agent, disc size/thickness/weight, stamper life)
- Production log (record/clear) + defect references
- Q&A panel

## Tab 3: Control de Calidad (`ui/pipeline/base_stage.py`)
- Common pipeline stage with QA panel

## Tab 4: Conocimiento (`ui/workspace/knowledge_hub.py`)
- 3 tabs: Import (6 buttons for different sources), Q&A, KB Browser (search + list + preview)

## Import Dialog (`ui/imports/import_dialog.py`) - 9 tabs
0. Lathe Trolls scraping
1. PubChem search + enrich
2. Wikipedia search
3. File import (YAML/JSON/CSV/Markdown)
4. Forum mirror (Playwright)
5. WhatsApp import
6. Scanned books (PDF/OCR)
7. Patents (Google Patents)
8. LLM Q&A + RAG pipeline

## Knowledge Explorer (`ui/knowledge/explorer.py`) - 9 tabs
Map view, overview stats, browse, search, analysis, import log, corrections, organize, export

## RAG Settings Dialog (`ui/knowledge/settings_dialog.py`) - 2 tabs
Base config (LLM connection, generation, retrieval, scraper, system prompt) + Agents

## Key Signal Flows
- IngredientBrowser.ingredients_changed → RecipeEditor.refresh_selector
- PigmentSearch.add_to_recipe_requested → CuttingStage._on_pigment_add_to_recipe → dialog → add_ingredient_by_name
- SpecialChemSearch.add_to_recipe_requested → CuttingStage._on_source_add_to_recipe → add_ingredient_by_name
- RecipeEditor.analysis_requested → CuttingStage._on_analyze → analyzer.analyze_recipe → analysis_panel
- RecipeEditor.translate_requested → CuttingStage → MainWindow._on_translate_requested → LLM thread → QMessageBox

## Known Issues
- `gui/` directory is legacy but still imported by main.py and several files in `ui/`
- Threading: mixed QThread + threading.Thread patterns
- No validation on recipe component percentages summing to 100%
- IngredientBrowserWidget uses QTreeWidget; SpecialChemSearchWidget uses QListWidget
- AnalysisInputPanel uses QFormLayout; results use QGridLayout — layout inconsistency
