# Lacquer Analyzer — Project Memory

Lacquer disc formulation & mastering assistant: recipes, analysis, plating (galvánica), pressing, RAG knowledge base, LLM Q&A.

## Commands
- Run: `./run.sh` (or `QT_QPA_PLATFORM=offscreen venv/bin/python main.py` for headless test)
- Test import: `QT_QPA_PLATFORM=offscreen python3 -c "..."` (use system python3 + `sys.path.insert(0,'.')` from project root)
- Git: repo `github.com/ondraspa/lacquer-analyzer`, current branch `ui-refinement`, push via `git push origin ui-refinement`

## Architecture
- Entry: `main.py` → `MainWindow` in `ui/main_window.py` (applies `DARK_THEME` from `ui/theme.py`)
- 6 tabs: Inicio (welcome, index 0) → Formulación (`cutting_stage.py`) → Galvánica → Prensado → RAG → Herramientas
- Pipelines: `ui/pipeline/` (base_stage.py, cutting_stage.py); Workspaces: `ui/workspace/`
- Knowledge: `knowledge/base.py` (ForumKnowledgeBase), `data/knowledge_base.json` (10,285 entries, 9.1MB), `data/forum_cache/` (568 threads), `data/extracted_images/` (scraped book pages)
- LLM: `llm/client.py` local API; `core/translations.py` translator
- Ingredient DB: `config/ingredients.yaml`; presets: `data/preset_recipes.yaml`; plating rules: `config/plating_compatibility.yaml`

## Conventions
- **UI language**: Spanish primary, EN/ES via `from core.translations import T`; `T("Español")` looks up English in dict in `core/translations.py`; keys = Spanish strings
- **Dark theme**: `ui/theme.py` 353-line QSS; never hardcode light colors — use theme vars
- Tooltips: every widget gets `.setToolTip()` (Spanish)
- Avoid emojis in code unless user-facing UI (icons ok)
- NO comments in code unless asked
- Legacy duplicate code in `gui/` and `src/` — prefer `ui/` and `core/`
- Always run offscreen import test after changes before commit

## Known Issues / Gotchas
- `T(f"...{var}...")` in cutting_stage.py doesn't translate (f-string evaluated first) — pre-existing, leave unless asked
- Translator: Spanish strings ARE keys; EN lookup in dict; add missing pairs to `_build_dict()` in `core/translations.py`
- Recipes save to `config/ingredients.yaml` via `ingredient_editor.py`; data files referenced by path — don't move without updating references
- LLM: `translate_with_llm` is synchronous (llm_client.ask) — no async
- Analysis uses `FormulationAnalysisResult` (core/models.py) — not `AnalysisResult`

## Current State (ui-refinement branch)
- Welcome screen, dark theme, signal-slot fixes, tooltips, EN/ES translations all done and pushed
- Process Manual Dialog: `ui/dialogs/process_manual_dialog.py` — 4 manuals (formulation, electroplating, pressing, cutting) with history tabs; buttons in cutting_stage/galvanics/pressing headers
- Translation T() wrapping complete for welcome_screen, galvanics, pressing; analysis_panel.py does NOT exist at ui/pipeline/ (legacy `gui/analysis_panel.py` only)
- UX pass: vertical (West) workflow sidebar; live `WelcomeScreen.update_status()` via `MainWindow._update_welcome_status()`; import dialog + knowledge explorer mega-tabs use sidebar (West) orientation
- **Formula pipeline redesign (Steps 1–3 DONE, all pushed)**: design doc `docs/FORMULA_PIPELINE_REDESIGN.md` (commits `cea5af5`, `1a55c6b`, `b369a11`)
  - `core/formula_store.py`: git-like store at `data/formulas/{library,history,snapshots}/` + `formula_log.json`; create/list/get/save/commit/list/get_version/restore/diff/snapshot image save/list/delete/get_thumbnail/set_favorite/update_meta/rename/delete; `_slug()` ID derivation; opaque dict recipe shape (preset YAML shape)
  - `ui/formula/formula_window.py`: FormulaWindow (MDI), FormulaEditorWidget (ingredient combo + table, RecipeAnalysisPanel tab, QUndoStack, autosave, dirty tracking), FormulaSubWindow (closeEvent dirty prompt), version history + diff, snapshot gallery (IconMode, compare/delete), info dialog; EN/ES retranslate; QSettings geometry
  - MainWindow: toolbar "🧪 Formula Studio" btn + menu action "Ventana de Fórmulas...", single instance `_open_formula_window()`
  - Tests: `tests/test_formula_store.py` (10), `tests/test_formula_window.py` (7, offscreen; cannot monkeypatch QMessageBox — call `store.restore_version` + `editor.load_from_store` directly)
  - Gotchas: `IngredientLoader.load_all()` must be called explicitly; dirty baseline = `get_data()` after load; Spanish keys ARE keys; emoji-prefixed strings are separate translation keys
- **Research (NEW)**: `docs/SCIENTIFIC_FORMULATION_AI.md` — modern AI/science for lacquer prediction + de-novo formulation (physics UNIFAC/Jouyban–Acree/HSP/Tg, GNN+COSMO-RS, PEGAT/HASolGNN, FDS2S/FG graphs, Bgolearn BO, active learning, ToolMol/AI4S-SDS, tooling table, hybrid architecture). AI answers: Mistral full; Perplexity flaky sign-in wall
- Remaining: Step 4 (translations verification), optional `./run.sh` smoke test, final commit
