# 🤝 Model Handoff — Continuity Memory

> **Purpose**: ANY AI model or human can read this file and continue work seamlessly, with zero prior context. This file is the single source of truth for project state. **UPDATE IT AT THE END OF EVERY SESSION** — it's how models hand off to each other.

---

## ⚡ QUICK STATUS (read first)

**Branch**: `ui-refinement` — ALL work pushed. Latest commit: `b369a11 feat: integrate FormulaWindow into main app (toolbar + menu)`

**COMPLETED** (14 commits, all pushed):
- Initial app, bug fixes, tooltips, welcome screen, dark theme, signal-slot audit
- Process manuals popup (4 processes, history tabs)
- Full T() translation wrapping + live EN/ES switching (`retranslate()` on all tabs)
- UX pass: vertical (West) workflow sidebar, live `WelcomeScreen.update_status()` via `MainWindow._update_welcome_status()`, sidebar orientation for import dialog + knowledge explorer
- **Formula pipeline redesign (Steps 1–3 done)**: `docs/FORMULA_PIPELINE_REDESIGN.md` design doc; `core/formula_store.py` git-like store (library/history/snapshots + `formula_log.json`); `ui/formula/formula_window.py` FormulaWindow (MDI editors, version history, snapshot gallery, undo, autosave, dirty tracking); MainWindow toolbar "🧪 Formula Studio" + menu action; translations added. 17 tests green (plain asserts, `QT_QPA_PLATFORM=offscreen`)
- **Research doc (NEW)**: `docs/SCIENTIFIC_FORMULATION_AI.md` — modern AI/science approaches for lacquer/coater prediction + de-novo formulation (physics: UNIFAC/Jouyban–Acree/HSP/Tg; ML: GNN+COSMO-RS, PEGAT/HASolGNN, FDS2S/FG formulation graphs, Bgolearn BO, active learning, ToolMol/AI4S-SDS agentic design; tooling table; hybrid architecture proposal). Mistral answered fully; Perplexity hit sign-in wall (flaky free tier)

**REMAINING**:
- Step 4 of pipeline: verify formula translations + final polish
- Optional end-to-end manual run (`./run.sh`)
- Update AGENTS.md/MODEL_HANDOFF (this file) at end of each session

---

## 1. PROJECT OVERVIEW

**Lacquer Analyzer** — desktop app (PySide6) for lacquer disc formulation, analysis, electroplating (galvánica), pressing, and RAG knowledge-base Q&A. Built for the disc-cutting / vinyl industry. Spanish-first UI, EN/ES bilingual.

**Repo**: `github.com/ondraspa/lacquer-analyzer` | Branch: `ui-refinement`

**Key numbers**:
- Knowledge base: `data/knowledge_base.json` — **10,285 entries** (list of dicts: `source,title,content,category,keywords,image_paths`)
- Forum cache: `data/forum_cache/` — **568 scraped Lathe Trolls threads** (4.3MB)
- Forum images: `data/forum_images/` — 122 files
- Extracted book pages: `data/extracted_images/` — ~813 PNGs (OCR'd books, PDFs, brochures)
- Ingredient DB: `config/ingredients.yaml` — 2,277 lines (67KB)
- Translations: ~700 lines in `core/translations.py`

## 2. ARCHITECTURE MAP

```
main.py → ui/main_window.py (MainWindow, applies DARK_THEME)
│
├── Tab 0: Inicio (welcome_screen.py) — 6 section cards, navigation, status indicators
├── Tab 1: Formulación (ui/pipeline/cutting_stage.py)
│     left: IngredientBrowser + PigmentSearch + SpecialChemSearch + Troubleshooting
│     right: RecipeEditor + KnowledgeQAPanel("cutting")
├── Tab 2: Galvánica (ui/workspace/galvanics_workspace.py) — baths, PlatingOverviewWidget, Q&A
├── Tab 3: Prensado (ui/workspace/pressing_workspace.py) — params, disc specs, log, defects ref
├── Tab 4: RAG/Conocimiento (ui/workspace/knowledge_hub.py) — KB browser, RAG inspector, tools
└── Tab 5: Herramientas (tool dialogs)

Support modules:
  core/          translations.py, analyzer.py, models.py (FormulationAnalysisResult)
  ui/theme.py    DARK_THEME QSS (353 lines)
  ui/dialogs/    process_manual_dialog.py (NEW)
  ui/pipeline/   base_stage.py (PipelineStageWidget, KnowledgeQAPanel, TroubleshootingPanel, StageParamEditDialog)
  ui/workspace/  recipe_editor, ingredient_editor, ingredient_browser, recipe_analysis_panel,
                 recipe_comparison, defect_editor, expert_notes, plating_rules_editor,
                 generate_formulation, welcome_screen
  ui/knowledge/  explorer.py, rag_inspector.py, settings_dialog.py, map_view.py, detail_view.py
  ui/imports/    import_dialog.py, tool_dialogs.py (DataImportDialog, ExpertNotesDialog, KnowledgeBrowserDialog)
  knowledge/     base.py (ForumKnowledgeBase), settings.py (RAGSettings), agents.py
  llm/           client.py (local API, synchronous ask()), corrections.py
  workflow/      ingredients.py, plating_rules.py, defects.py
  analysis/      lacquer_physics.py (725 lines)
  materials/     pigment_db.py (25 pigments)
  imports/       forum.py, pdf_book.py, patent.py, whatsapp.py, specialchem_scraper.py, jobs.py
  data/          knowledge_base.json, forum_cache/, forum_images/, extracted_images/, recipes yaml
  config/        ingredients.yaml, plating_compatibility.yaml, rag_settings.json, auth files
  gui/ src/      LEGACY duplicates (stubs re-exporting) — prefer ui/ and core/ for new code
```

## 3. COMPLETE WORK LOG (everything done so far)

### 3.1 Initial commit (`90638b6`) — app skeleton
- Full app: formulation analysis, ingredient DB, plating rules, RAG knowledge base, LLM client, PDF/forum/patent importers, legacy `gui/` + `src/` stubs, run scripts

### 3.2 Bug-fix batch (`9fa4889`) — 12 files, 175 insertions
| Bug | Fix |
|---|---|
| `Ingredient` save path wrong | `ingredient_editor.py` now saves to `parent.parent.parent / config/` |
| `density_spin` missing (CRITICAL) | Added to `IngredientEditorDialog` |
| `boiling_point` field mismatch | → `boiling_point_c` |
| `dosage_pct` KeyError | → `getattr()` with fallback |
| `solids_content_pct` missing | fallback added |
| `compatible_plating` data loss (HIGH) | Added `Dict[str,bool]` field to `Ingredient` dataclass |
| `AnalysisResult` name clash | → `FormulationAnalysisResult` in `core/models.py`, ALL imports updated |
| plasticizer detection fragile | `IngredientType.PLASTICIZER` enum + 5 YAML entries updated; removed name-matching in `recipe_analysis_panel.py` |
| `analyze_lacquer` crashes | try/except with `FormulationAnalysisResult(issues={})` fallback in `recipe_comparison.py` + `recipe_analysis_panel.py` |
| plasticizer category | `"plasticizer": "additives"` added to `CATEGORY_MAP` in `ingredient_editor.py` |
| preset concentration | fallback to `comp_data.get("concentration", 10)` in `recipe_editor.py` |
| `set_recipe_from_preset` | verified `drying_temp_c`, `substrate_temp_c` exist in `AnalysisInput` |
| plating rules | `workflow/plating_rules.py` + `plating_overview.py` + `core/translations.py` fixes |
| **UI_MAP created** | `docs/UI_MAP.md` (88 lines) — tab structure, signal flows, known issues |

### 3.3 Cleanup (`3d0bfe3`)
- Removed dead `AnalysisPanelWidget` tab and `LacquerAnalyzer` usage from cutting stage (2 files)

### 3.4 Tooltips + usage guide (`a3adf71`) — 24+ UI files
- ~450 `.setToolTip()` (Spanish) across all UI files
- Help → "📖 Guía de uso" HTML usage-guide dialog
- Files: base_stage, cutting_stage, plating_overview, import_dialog, tool_dialogs, explorer, rag_inspector, settings_dialog, main_window, all workspaces, recipe_editor, recipe_comparison, ingredient_editor/browser, defect_editor, plating_rules_editor, expert_notes, generate_formulation, knowledge_hub, welcome_screen, galvanics, pressing

### 3.5 Welcome screen (`390226f`) — NEW TAB 0
- `ui/workspace/welcome_screen.py`: `SectionCard` (6 cards: Formulación, Enhancer, Solucionador, Galvánica, Prensado, RAG) + `StatusIndicator` (BD ingredientes, recetas, KB, LLM)
- Signals: `navigate_requested = Signal(int)` → `MainWindow._navigate_to_tab()`
- Cards clickable (children set `WA_TransparentForMouseEvents`)
- ALL tab index references updated (+1) across app

### 3.6 Dark theme (`6541f72`) — `ui/theme.py`
- 353-line `DARK_THEME` QSS: dark blue palette, covers tabs/toolbar/menus/buttons/inputs/tables/lists/scrollbars/spinboxes/combos/tooltips
- Applied: `MainWindow.setStyleSheet(DARK_THEME)`
- Inline light color values fixed across 8 files

### 3.7 Signal-slot audit (`4a8c127`) — ~220 connections
- Fixed `knowledge_hub.py` `SanitizeJob`: constructor args were SWAPPED; `start()` on QObject → proper `QThread` wiring (`moveToThread`, `started→run`, `finished→quit+deleteLater`)
- Fixed `import_dialog.py`: `_tabs` → `tabs` (so knowledge_hub can call `dlg.data_import.tabs.setCurrentIndex()`)
- Fixed `tool_dialogs.py`: missing `QWidget` import → `NameError` in `KnowledgeBrowserDialog`

### 3.8 AttributeError fixes (`0f1ce19`)
- `knowledge_hub.py` sanitize job errors + `tool_dialogs.py` NameError (see 3.7)

### 3.9 UNCOMMITTED — Process manuals (current session)
- **NEW** `ui/dialogs/process_manual_dialog.py` (564 lines): `MANUALS` dict with 4 processes, each 3-4 HTML tabs:
  - **lacquer_formulation** (4 tabs): Overview / 1920–1950 / 1950–2000 / 2000–Presente
  - **electroplating** (3 tabs): Overview / 1930–1970 / 1970–Presente
  - **pressing** (3 tabs): Overview / 1900–1960 / 1960–Presente
  - **cutting** (3 tabs): Overview / 1920–1960 / 1960–Presente
  - Content: how it works (chemistry, components, parameters, defects) + industry evolution (eras, manufacturers: Apollo/Transco, Westrex, Neumann, Toolex Alpha, Warmtone...) + tech updates
- Buttons: `cutting_stage.py` (📖 Manual — Formulación + 📖 Manual — Corte), `galvanics_workspace.py`, `pressing_workspace.py` — each opens `ProcessManualDialog(key, self).exec()` via `_open_manual()`
- **MANUAL CONTENT IS SPANISH HTML** — intentionally NOT translated (reference content); UI chrome uses T()

### 3.10 UNCOMMITTED — Translations (current session)
- T() wrapping completed: `welcome_screen.py` (all 6 cards: titles, 24 features, footer, status items), `galvanics_workspace.py` (all labels/combos/tabs/tooltips), `pressing_workspace.py` (all labels/combos/tooltips/HTML via T() on whole block)
- `core/translations.py` expanded: welcome, galvanics, pressing labels/combos/tooltips, analysis panel strings (solvent system, coating properties HTML fragments, risk levels LOW/MEDIUM/HIGH/CRITICAL, quality descriptors), pressing HTML defect list, process manual titles/tabs/buttons
- New strings added for: "🖱️ Haz clic para abrir", "No verificado", all card descriptions/features, form labels, spinbox suffixes (" °C", " bar", " s", " mm", " g", " prensadas", " A/dm²", " μm", " min"), combo items (mold types, release agents, disc sizes, surface prep methods), tab titles, HTML content

### 3.11 DONE — Live language switching (`6d43b92`)
- **`retranslate()` methods added** to: `WelcomeScreen`, `CuttingStageWidget`, `GalvanicsWorkspace`, `PressingWorkspace`, `KnowledgeHub`
- **`SectionCard`/`StatusIndicator`** (welcome_screen): store original string keys, `retranslate()` re-sets text via T()
- **`GalvanicsWorkspace`/`PressingWorkspace`**: all widgets stored as `self.*` (groups, forms, buttons, combos); form labels found via `_label_for(widget)` static helper (widget.parentWidget().layout().labelForField())
- **`CuttingStageWidget`**: fixed no-op `lambda: None` → `translator.language_changed.connect(self.retranslate)`; `left_tabs`/`right_tabs` stored
- **`MainWindow._retranslate_ui()` implemented** (was `pass`): retitles window, toolbar buttons (`self.expert_btn`, `self.rag_btn`, `self.gen_btn`), 6 tab titles, all menu titles/actions (stored as `self.*_menu`/`self.*_action`), calls `retranslate()` on 5 tab widgets, refreshes LLM/KB status, resets statusbar
- **Translation dict additions**: emoji-prefixed KH button keys ("📂 Importar Markdown" etc. — note: emoji versions are SEPARATE keys from plain versions), full pressing HTML block as exact-match key, "Centro de Conocimiento" full header
- Verified: EN→ES→EN cycles, form labels, combos, suffixes, HTML, menus, tabs all switch live

## 4. TRANSLATION SYSTEM (CRITICAL TO UNDERSTAND)

```python
from core.translations import T, translator
label = QLabel(T("Guardar"))   # Spanish string = KEY
T = translator.get              # returns EN when lang=EN, else the key itself
translator.language_changed.connect(self._retranslate_ui)   # live refresh
```

**Rules**:
1. Spanish strings ARE the dictionary keys; EN is the value in `_build_dict()` (`core/translations.py`)
2. `T()` with a key not in dict returns the key (Spanish) — safe fallback
3. `T(f"...{var}...")` is BROKEN (f-string evaluated before T) — pre-existing in cutting_stage.py; do NOT "fix" unless asked
4. Don't wrap identifiers/keys: `KnowledgeQAPanel("cutting")` — never T()
5. Manual/reference content (process manuals HTML) intentionally stays Spanish
6. `translator.language_changed` — cutting_stage.py currently has a NO-OP connection (`lambda: None`) — proper `_retranslate_ui()` not yet implemented

## 5. NEXT STEPS (in priority order)

1. **Wire `WelcomeScreen.update_status()`** — currently a no-op `pass`; feed real data (ingredient count, recipe count, KB entries, LLM status) from MainWindow
2. **Update `docs/UI_MAP.md`** — add process manuals + retranslate features
3. **Optional**: `retranslate()` for `PipelineStageWidget` (qc_stage tab) if its labels need switching
4. Update this file (MODEL_HANDOFF.md) after each milestone

## 6. GOTCHAS / TRAPS (memorize these)

- `T(f"...{var}...")` broken pattern in cutting_stage.py — leave it
- `ui/workspace/analysis_panel.py` DOES exist (4 lines, re-export stub!) — `ui/pipeline/analysis_panel.py` does NOT. Check paths carefully
- Legacy `gui/` + `src/` contain stub re-exports (`from ui.xxx import *`) — editing them is fine but prefer real modules
- `ingredient_editor.py` save path: `parent.parent.parent / config/ingredients.yaml` — fragile, do not restructure
- `SanitizeJob` in knowledge_hub.py: args order matters (file path first, then settings)
- `ImportDialog.tabs` (not `_tabs`) — public attribute used by knowledge_hub
- Knowledge base JSON: list of dicts; categories: "Plating and Pressing" (487), "Secrets of the Lathe Trolls" (2757), "The Reference Archive" (290), "Vinyl Mastering, Lacquer cutting..." (419), "book" (574), "patent" (12)
- LLM: local API, synchronous — never use async/await with llm_client
- `KnowledgeQAPanel(category)` — category string is first positional arg
- Tab indices: 0=Inicio, 1=Formulación, 2=Galvánica, 3=Prensado, 4=RAG, 5=Herramientas
- Data files referenced by absolute-ish relative paths — don't move without updating references
- Auth files (specialchem, lathe trolls) in config/ — never commit real credentials

## 7. VERIFICATION COMMANDS

```bash
# Quick import test (must pass after ANY change):
QT_QPA_PLATFORM=offscreen python3 -c "
import sys; sys.path.insert(0,'.')
from ui.dialogs.process_manual_dialog import ProcessManualDialog, MANUALS
from ui.workspace.pressing_workspace import PressingWorkspace
from ui.workspace.galvanics_workspace import GalvanicsWorkspace
from ui.pipeline.cutting_stage import CuttingStageWidget
from core.translations import T, translator
assert T('Guardar') == 'Guardar'  # ES mode
print('ALL IMPORTS OK')"

# Full app smoke test:
QT_QPA_PLATFORM=offscreen ./run.sh   # or python3 main.py

# Git:
git status && git diff --stat && git log --oneline -5
```

## 8. USEFUL DATA REFERENCES

- `data/preset_recipes.yaml` — 15+ preset recipes (target viscosity, solids %, components, pros/cons)
- `data/example_recipes.yaml` — Burkle curtain coater recipes ("Standard NC Lacquer for Silvering")
- `data/plating_recipes.yaml` — nickel sulfamate + silvering parameters
- `config/plating_compatibility.yaml` — forbidden chemicals, surface prep, critical params per plating type
- `materials/pigment_db.py` — 25 pigments, search by C.I./trade name/class
- `config/rag_settings.json` — local API endpoint, gemma-4-26b, 4 agents (General, Chemistry, Physics, Patent Analyst)
- `knowledge/agents.py` — agent profile definitions
- Importers: `imports/forum.py` (Playwright Lathe Trolls), `imports/pdf_book.py` (PyMuPDF+Tesseract OCR), `imports/patent.py` (Google Patents), `imports/specialchem_scraper.py` (89k commercial ingredients, Cloudflare bypass)
