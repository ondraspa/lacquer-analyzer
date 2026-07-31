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
- **Version metadata**: `version`, `timestamp`, `change_reason`, `analysis_score` (if analyzed), `image_path`
- **Change log entry**: `{ts, formula, action, diff_summary, version}`
- **Restore = copy snapshot → current** (with confirmation + new version entry so restore itself is logged)

### 3.2 Separate Window — `ui/formula/formula_window.py` (NEW)

`FormulaWindow(QMainWindow)` — opened from MainWindow toolbar button ("🧪 Formula Studio" / "Ventana de Fórmulas"), NOT a tab:

```
┌─────────────────────────────────────────────────┐
│ Formula Studio — <formula name>        [Save]   │
├───────────────┬─────────────────────────────────┤
│ FORMULA LIBRARY │  WORKSPACE                     │
│ ┌───────────┐ │  ┌────────────────────────────┐ │
│ │ My Laca 1 │ │  │ [Component table: name,     │ │
│ │ My Laca 2 │ │  │  type, conc, max_conc]      │ │
│ │ (draft)   │ │  ├────────────────────────────┤ │
│ │           │ │  │ [Analysis panel → score,    │ │
│ └───────────┘ │  │  charts, warnings]          │ │
│ [+ New] [Del] │  └────────────────────────────┘ │
├───────────────┼─────────────────────────────────┤
│ VERSION HISTORY │  SNAPSHOTS (images)           │
│ v5 14:02 best  │  [thumbnails of saved images]  │
│ v4 13:45 ...   │  [click to view/compare]       │
│ [Restore v3]   │  [Save snapshot image]         │
└───────────────┴─────────────────────────────────┘
```

### 3.3 Persistence & Monitoring

- **Autosave**: every N seconds (default 60s) if dirty, plus on window close
- **Dirty tracking**: any component/param edit sets `dirty=True`; status bar shows "● Modified"
- **Manual version commit**: "Save Version" button → asks change reason → stores snapshot
- **Optional auto-version on analysis**: running analysis stores result + score with current version

### 3.4 Image Snapshots

- **Save screenshot** button: captures formula table + analysis result as PNG (`QWidget.grab()` / `QScreen.grabWindow`)
- Stored per formula per version in `data/formulas/snapshots/`
- Thumbnail gallery panel: click to view full-size; double-click to compare two versions side by side

### 3.5 Restore Workflow

1. Select version in history list
2. Click "Restore" → confirmation dialog showing diff (what changes vs current)
3. On confirm: current state saved as new version (safety), selected version copied to working state
4. Change-log entry recorded

## 4. IMPLEMENTATION PLAN

| Step | Files | Description |
|---|---|---|
| 1 | `core/formula_store.py` | FormulaStore: save/load/list/version/restore/log + snapshot images |
| 2 | `ui/formula/formula_window.py` | FormulaWindow QMainWindow: library pane, component editor, version history, image gallery |
| 3 | `ui/main_window.py` | Toolbar button + menu action → opens FormulaWindow (non-modal, persistent single instance) |
| 4 | `core/translations.py` | EN/ES strings for new window |
| 5 | Tests | Import test + store roundtrip test (version, restore, log) |

**Priority**: Step 1 (data layer) → Step 2 (window UI) → Step 3 (integration).

## 5. OPEN QUESTIONS

1. Should version commits be manual ("Save Version") or automatic on every analysis run?
2. Should the Formula Window replace the current Formulación tab, or coexist?
3. Batch scaling (Labii-style) — needed in v1?

## 6. CHECKPOINT

- Tag: `v0.4-pre-pipeline-rework` — pushed to GitHub, working tree clean
- If redesign breaks something, restore: `git checkout v0.4-pre-pipeline-rework`
