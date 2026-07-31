# 🔬 Formula Pipeline Redesign — Research & Design Document

> **Status**: Research complete. Design proposal v1. Checkpoint created: **git tag `v0.4-pre-pipeline-rework`** (all current work pushed).

---

## 1. USER REQUIREMENTS

1. **Persistence** — formula changes monitored persistently (autosave, change log)
2. **Restore to any point** — full version history with rollback (like git for formulas)
3. **Save multiple formulas** — named formula library
4. **Save images per formula** — screenshots/snapshots (analysis results, charts) to compare outcomes later
5. **Formula pipeline as a SEPARATE WINDOW** — not a tab inside main window

## 2. INDUSTRY RESEARCH (what real apps do)

### 2.1 Chemical PLM — ChemCopilot (version control in PLM)
Key practices for formulation change management:
- **Digital timeline per product**: every change recorded (who, why, when, approved)
- **Rollback** to older versions at any time
- **Audit log** of all formula changes
- **Version linking**: each version linked to results/documents (SDS, test data)
- **AI on history**: version history enables trend analysis ("what worked and what didn't")
- Core insight: *"R&D teams can revisit previous iterations, understand what worked, and avoid re-inventing the wheel"*

### 2.2 Labii Formulation Management (ELN/LIMS)
- **Ingredient versioning** (each ingredient has its own version history)
- **Optimization engine** with constraints (min cost, max performance)
- **What-if scenarios** — compare alternatives side by side
- **Batch management with COA testing** — every batch tested, results tracked
- **Data-driven decision reports** — composition, cost breakdown, comparisons
- **Historical versions stored** for audits

### 2.3 BatchMaster FMS (ERP formula management)
- Effective **version control**
- **Automatic formula resizing** (batch scaling)
- **Instant roll-back** to older versions
- Material substitution tracking
- **Audit log** — "all formula changes and approvals are captured"
- **User-defined approval workflow**

### 2.4 Other formulation apps (Formulator, Datacor)
- Secure sandbox for R&D iteration
- Cost roll-ups, version control
- Shift from spreadsheet recordkeeping → **regulated workflows with version control + electronic audit trails**

### 2.5 Common Feature Set (synthesis)
| Feature | ChemCopilot | Labii | BatchMaster | Required? |
|---|---|---|---|---|
| Version history + rollback | ✅ | ✅ | ✅ | **YES** (core) |
| Change log (who/when/why) | ✅ | ✅ | ✅ | **YES** |
| Compare versions/formulas | ✅ | ✅ | ✅ | **YES** |
| Save/name multiple formulas | ✅ | ✅ | ✅ | **YES** |
| Attach results/docs to version | ✅ | ✅ | — | **YES** (images) |
| Batch scaling | — | ✅ | ✅ | Later |
| Approval workflow | ✅ | ✅ | ✅ | Later |
| Ingredient versioning | — | ✅ | — | Later |

## 2.6 AI Model Feedback (design consultation, free web providers)

Asked the same product-designer question to free AI chat providers via headless browser automation (`/tmp/opencode/ask_ai4.py` + `ask_ai5.py` + `ask_ai6.py`, results in `/tmp/opencode/ai_answers/`).

**Answers received** (full text: `perplexity.txt`, `mistral_vibe.txt`):

### Perplexity
- **MDI editor windows** (QMdiArea + QMdiSubWindow): tile/cascade/tab multiple formulas side-by-side — *don't nest the editor in tabs, tabs hide context and limit parallel work*
- **Version timeline with diffs**: red strikethrough = removed, green = added (Google Docs / Figma pattern)
- **Library grid/list with thumbnails** + metadata (name, date, ingredients count), searchable
- **Undo/redo stack per formula** complementing version history
- Pitfalls: *avoid opaque versioning* (don't save "v1, v2, v3" without who/when/why); *don't auto-overwrite screenshots* (manual capture or annotations); *don't lose focus context* on restore (show which formula/window it applies to)
- Concrete: **restore preview** (read-only preview before committing restore), batch export of screenshots + analysis PDFs, shortcuts (Ctrl+Shift+V history, Ctrl+Shift+S screenshot, Ctrl+N new formula window)

### Mistral Vibe
- **Timeline/tree version navigation**, visual diffs, **one-click restore**, **version naming** ("v2 – more flexible")
- **Searchable, taggable library** (by solvent type, use case) with thumbnails + hover previews; **favorites** section
- **Auto-capture screenshots** when saving/analyzing; **side-by-side comparison mode**
- Editor window: **modal or always-on-top** for focus, resizable + dockable, **remembers position/size** (re-dockable, multi-monitor)
- Pitfalls: *version clutter* (limit auto-saves, allow manual version creation and pruning); *library overload* (enforce unique names/tags); *screenshot bloat* (compress images, allow deletion); *window chaos*
- Concrete: "Save As" dialog for new library entries with **mandatory name/tag**; **Compare** button opening side-by-side screenshots/analysis; **Revert** button linked to last saved version

### Failed providers (for the record)
| Provider | Result |
|---|---|
| DuckDuckGo AI | rate-limited server-side ("temporarily unavailable", code 84f2) |
| LM Arena | chat app never loads for headless session (invisible 0×0 textarea only) |
| HuggingChat | submit doesn't stick (welcome screen persists) |
| Blackbox.ai | no chat input found on page |
| Kimi | login wall ("Log in with phone number") |
| Phind / You.com | 404 / sign-in wall |

### 2.7 Synthesis — design decisions adopted
1. **MDI sub-windows** inside FormulaWindow (QMdiArea) — supports working multiple formulas side-by-side; editor is already a separate window per requirement 4
2. **Version metadata**: number + timestamp + **user-typed name/reason** ("v2 – more flexible") — fights opaque versioning
3. **Diff summary** shown in history list + **read-only restore preview dialog** before committing
4. **Undo/redo per formula** (QUndoStack) as lightweight iteration complement to versions
5. **Library**: search field + tags, thumbnail cards, unique names enforced, favorites star
6. **Screenshots**: manual capture button (default) + optional auto-capture on analysis; PNG stored per version; side-by-side compare of two snapshots
7. **Window geometry persistence** via QSettings (position/size restored across launches)

## 3. PROPOSED ARCHITECTURE

### 3.1 Data Model — `core/formula_store.py` (NEW)

```
data/formulas/
  library/                  # named formulas (persistent)
    <formula_name>.yaml     # formula data (name, desc, components, meta)
  history/
    <formula_name>/         # per-formula version history (git-like)
      v001_2026-07-31_120000.yaml   # full snapshot per version
      v002_...
      HEAD.yaml             # current pointer
  snapshots/
    <formula_name>/
      v001_screenshot.png   # optional image per version
      v002_chart.png
  formula_log.json          # change log (append-only audit trail)
```

- **Snapshot = full copy** of formula YAML per version (simplest, robust — formulas are small)
- **Version metadata**: `version`, `timestamp`, `change_reason` (user-typed name/reason), `analysis_score` (if analyzed), `image_path`
- **Change log entry**: `{ts, formula, action, diff_summary, version}`
- **Restore = copy snapshot → current** (with read-only preview dialog + confirmation; current state saved as new version first so restore is logged)
- **Diff summary**: per-version delta vs predecessor (added/removed/changed ingredients) stored in version metadata

### 3.2 Separate Window — `ui/formula/formula_window.py` (NEW)

`FormulaWindow(QMainWindow)` — opened from MainWindow toolbar button ("🧪 Formula Studio" / "Ventana de Fórmulas"), NOT a tab. Uses **QMdiArea** inside so each open formula is its own `QMdiSubWindow` (side-by-side comparison):

```
┌─────────────────────────────────────────────────────────────┐
│ Formula Studio — <formula name>                   [Save]    │
├───────────────┬─────────────────────────────────────────────┤
│ FORMULA LIBRARY │ MDI AREA (one subwindow per open formula) │
│ 🔍 [search]    │ ┌─ My Laca 1 ──────────┐ ┌─ My Laca 2 ──┐ │
│ ⭐ [fav] My Laca 1│ │ [Component table: name, │ │ (read-only  │ │
│     My Laca 2 │ │  type, conc, max_conc]│ │  compare)    │ │
│     (draft)   │ │ [Analysis → score,    │ │              │ │
│ [+ New] [Del] │ │  charts, warnings]    │ │              │ │
│               │ └───────────────────────┘ └──────────────┘ │
│ TAGS: [solvent] │                                           │
├───────────────┼─────────────────────────────────────────────┤
│ VERSION HISTORY │  SNAPSHOTS (images)                       │
│ v5 14:02 "best" │  [thumbnails of saved images]             │
│ v4 13:45 ...   │  [click to view] [compare two]             │
│ [Preview] [Restore v3] │  [Save snapshot image]             │
└───────────────┴─────────────────────────────────────────────┘
```

- Window geometry persisted (QSettings) — position/size restored on next launch
- Undo/redo toolbar (Ctrl+Z / Ctrl+Y) backed by QUndoStack per formula

### 3.3 Persistence & Monitoring

- **Autosave**: every N seconds (default 60s) if dirty, plus on window close
- **Dirty tracking**: any component/param edit sets `dirty=True`; status bar shows "● Modified"
- **Manual version commit**: "Save Version" button → asks change reason/name → stores snapshot (avoids auto-save clutter; optional auto-version on analysis run as a setting)
- **Optional auto-version on analysis**: running analysis stores result + score with current version (opt-in, off by default)

### 3.4 Image Snapshots

- **Save screenshot** button (default, manual — no auto noise): captures formula table + analysis result as PNG (`QWidget.grab()` / `QScreen.grabWindow`)
- **Optional auto-capture** on analysis run (setting, off by default)
- Stored per formula per version in `data/formulas/snapshots/`; delete allowed
- Thumbnail gallery panel: click to view full-size; **compare mode** shows two snapshots side by side
- Shortcut: Ctrl+Shift+S

### 3.5 Restore Workflow

1. Select version in history list (shows name, timestamp, diff summary)
2. Click "Restore" → **read-only preview dialog** (formula as it was, diff vs current highlighted)
3. On confirm: current state saved as new version (safety), selected version copied to working state
4. Change-log entry recorded

## 4. IMPLEMENTATION PLAN

| Step | Files | Description |
|---|---|---|
| 1 | `core/formula_store.py` | FormulaStore: save/load/list/version/restore/log/diff + snapshot images |
| 2 | `ui/formula/formula_window.py` | FormulaWindow QMainWindow + QMdiArea subwindows: library (search/tags/favorites), component editor, version history with diffs, image gallery with compare |
| 3 | `ui/main_window.py` | Toolbar button + menu action → opens FormulaWindow (non-modal, persistent single instance) |
| 4 | `core/translations.py` | EN/ES strings for new window |
| 5 | Tests | Import test + store roundtrip test (version, restore, log) |

**Priority**: Step 1 (data layer) → Step 2 (window UI) → Step 3 (integration).

## 5. OPEN QUESTIONS

1. Should version commits be manual ("Save Version") or automatic on every analysis run? *(AI consensus: manual by default, optional auto — adopted as opt-in setting)*
2. Should the Formula Window replace the current Formulación tab, or coexist? *(AI consensus: separate window, MDI for multiple formulas — FormulaWindow complements the tab)*
3. Batch scaling (Labii-style) — needed in v1?
4. Image compare: side-by-side only, or also overlay/blend (flicker) comparison?

## 6. CHECKPOINT

- Tag: `v0.4-pre-pipeline-rework` — pushed to GitHub, working tree clean
- If redesign breaks something, restore: `git checkout v0.4-pre-pipeline-rework`
- AI answers raw captures: `/tmp/opencode/ai_answers/{perplexity,mistral_vibe}.txt`
