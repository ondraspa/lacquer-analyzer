"""UI tests for ui/formula/formula_window.py (offscreen).

Run: QT_QPA_PLATFORM=offscreen python3 tests/test_formula_window.py
"""

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.formula_store import FormulaStore  # noqa: E402
from ui.formula.formula_window import FormulaWindow  # noqa: E402

app = QApplication.instance() or QApplication([])

SAMPLE = {
    "id": "T1",
    "name": "Test Laca",
    "components": [
        {"id": "RES-002", "name": "Nitrocelulosa", "type": "base_resin",
         "concentration_pct": 18.0, "max_concentration_pct": 30.0},
    ],
    "target_viscosity_mpas": 600,
    "target_solids_pct": 18,
}


def _setup():
    tmp = tempfile.mkdtemp()
    store = FormulaStore(tmp)
    ref = store.create_formula("Test Laca", dict(SAMPLE))
    window = FormulaWindow(store=store)
    window._open_formula(ref.id)
    return tmp, store, ref, window


def test_fresh_load_clean():
    _, _, _, window = _setup()
    editor = window._editors[list(window._editors)[0]]
    assert editor.table.rowCount() == 1
    assert not editor.is_dirty()
    assert editor.undo_stack.count() == 0


def test_undo_redo():
    _, _, _, window = _setup()
    editor = window._editors[list(window._editors)[0]]
    editor.name_input.setText("Laca v2")
    editor._push_change()
    assert editor.is_dirty()
    assert editor.undo_stack.count() == 1
    editor.undo_stack.undo()
    assert not editor.is_dirty()
    assert editor.name_input.text() == "Test Laca"
    editor.undo_stack.redo()
    assert editor.name_input.text() == "Laca v2"


def test_add_remove_component_with_undo():
    _, _, _, window = _setup()
    editor = window._editors[list(window._editors)[0]]
    idx = None
    for i in range(editor.ingredient_selector.count()):
        ing = editor.ingredient_selector.itemData(i)
        if ing and ing.id == "RES-002":
            idx = i
            break
    assert idx is not None
    editor.ingredient_selector.setCurrentIndex(idx)
    editor._add_component()
    assert editor.table.rowCount() == 2
    editor.table.selectRow(1)
    editor._remove_component()
    assert editor.table.rowCount() == 1
    editor.undo_stack.undo()
    assert editor.table.rowCount() == 2


def test_restore_roundtrip():
    _, store, ref, window = _setup()
    editor = window._editors[ref.id]
    data = editor.get_data()
    data["components"] = data["components"] + [{
        "id": "SOL-012", "name": "Acetato de Butilo", "type": "active_solvent",
        "concentration_pct": 42.0, "max_concentration_pct": None,
    }]
    editor._apply_data(data)
    editor._push_change()
    assert editor.table.rowCount() == 2
    store.save_formula(ref.id, data)
    store.commit_version(ref.id, "v2 commit", data=data)
    window._refresh_history(ref.id)
    assert window.history_list.count() == 2
    window.history_list.setCurrentRow(1)
    from PySide6.QtCore import Qt
    version = window.history_list.currentItem().data(Qt.UserRole)
    store.restore_version(ref.id, version, "Manual restore")
    editor.load_from_store(store, ref.id)
    assert editor.table.rowCount() == 1
    assert not editor.is_dirty()


def test_snapshot_flow():
    _, store, ref, window = _setup()
    editor = window._editors[ref.id]
    editor.grab().save("/tmp/opencode/fw_capture.png", "PNG")
    with open("/tmp/opencode/fw_capture.png", "rb") as f:
        store.save_snapshot_image(ref.id, 1, f.read())
    window._refresh_snapshots(ref.id)
    assert window.snapshots_list.count() == 1


def test_retranslate_en_es():
    _, _, _, window = _setup()
    from core.translations import translator
    translator.set_language("en")
    assert window.library_group.title() == "Formula Library"
    assert window.history_group.title() == "Version History"
    assert window.snap_group.title() == "Snapshots"
    assert window.new_action.text() == "New Formula"
    assert window.preview_btn.text() == "Preview"
    translator.set_language("es")
    assert window.library_group.title() == "Biblioteca de Fórmulas"


def test_favorite_toggle():
    _, store, ref, window = _setup()
    window.library_list.setCurrentRow(0)
    window._toggle_favorite()
    assert store.list_formulas()[0].favorite


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  PASS {t.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    main()
