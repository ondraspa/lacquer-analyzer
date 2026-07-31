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
- Pending: end-to-end run test, commit/push of process manual work
