"""Roundtrip tests for core/formula_store.py.

Run: python3 tests/test_formula_store.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.formula_store import FormulaStore  # noqa: E402


def _sample_formula(name="Test Laca"):
    return {
        "id": "TEST-1",
        "name": name,
        "target_viscosity_mpas": 600,
        "target_solids_pct": 18,
        "application": "curtain_coater",
        "coater": "burkle",
        "notes": "test",
        "metadata": {"best_for": "33⅓ RPM"},
        "components": [
            {"id": "RES-002", "name": "Nitrocelulosa", "concentration_pct": 18.0},
            {"id": "SOL-012", "name": "Acetato de Butilo", "concentration_pct": 42.0},
        ],
    }


def test_create_and_list():
    with tempfile.TemporaryDirectory() as tmp:
        store = FormulaStore(tmp)
        ref = store.create_formula("Mi Laca!", _sample_formula())
        assert ref.id == "mi_laca"
        assert ref.name == "Mi Laca!"
        assert ref.version == 1
        assert store.formula_exists("mi_laca")
        refs = store.list_formulas()
        assert len(refs) == 1
        assert refs[0].id == "mi_laca"


def test_duplicate_name_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        store = FormulaStore(tmp)
        store.create_formula("Laca", _sample_formula())
        try:
            store.create_formula("laca!", _sample_formula())
            raise AssertionError("expected ValueError")
        except ValueError:
            pass


def test_save_and_commit():
    with tempfile.TemporaryDirectory() as tmp:
        store = FormulaStore(tmp)
        store.create_formula("Laca", _sample_formula())
        data = store.get_formula("laca")
        data["components"][0]["concentration_pct"] = 20.0
        store.save_formula("laca", data)
        assert len(store.list_versions("laca")) == 1
        store.save_formula("laca", data, change_reason="Mas nitro")
        versions = store.list_versions("laca")
        assert len(versions) == 2
        assert versions[-1].reason == "Mas nitro"
        assert versions[-1].diff["changed"][0]["to"] == 20.0
        assert store.get_formula_meta("laca")["version"] == 2


def test_version_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        store = FormulaStore(tmp)
        store.create_formula("Laca", _sample_formula())
        v1 = store.get_version("laca", 1)
        assert v1["components"][0]["concentration_pct"] == 18.0
        assert "_meta" not in v1
        assert store.get_version("laca", 99) is None


def test_restore():
    with tempfile.TemporaryDirectory() as tmp:
        store = FormulaStore(tmp)
        store.create_formula("Laca", _sample_formula())
        data = store.get_formula("laca")
        data["components"][0]["concentration_pct"] = 25.0
        store.save_formula("laca", data, change_reason="cambio")
        assert store.get_formula("laca")["components"][0]["concentration_pct"] == 25.0
        store.restore_version("laca", 1, reason="volver")
        versions = store.list_versions("laca")
        assert len(versions) == 3
        assert versions[-1].reason == "Restore checkpoint"
        assert store.get_formula("laca")["components"][0]["concentration_pct"] == 18.0
        assert store.get_formula("laca")["name"] == "Laca"
        assert any(e["action"] == "restore" and e["reason"] == "volver"
                   for e in store.get_log())


def test_images():
    with tempfile.TemporaryDirectory() as tmp:
        store = FormulaStore(tmp)
        store.create_formula("Laca", _sample_formula())
        path = store.save_snapshot_image("laca", 1, b"\x89PNG\r\n\x1a\nfakedata")
        assert path.endswith(".png")
        assert store.get_snapshot_images("laca", 1) == [path]
        assert store.get_snapshot_images("laca", 2) == []
        assert store.get_thumbnail("laca") == path
        store.delete_snapshot_image("laca", 1, os.path.basename(path))
        assert store.get_snapshot_images("laca", 1) == []


def test_favorite_tags():
    with tempfile.TemporaryDirectory() as tmp:
        store = FormulaStore(tmp)
        store.create_formula("Laca", _sample_formula(),
                             description="desc", tags=["solvente"])
        store.set_favorite("laca", True)
        meta = store.get_formula_meta("laca")
        assert meta["favorite"] is True
        assert meta["description"] == "desc"
        assert meta["tags"] == ["solvente"]


def test_rename():
    with tempfile.TemporaryDirectory() as tmp:
        store = FormulaStore(tmp)
        store.create_formula("Old Name", _sample_formula())
        ref = store.rename_formula("old_name", "New Name")
        assert ref.id == "new_name"
        assert store.get_formula("new_name")["name"] == "New Name"
        assert not store.formula_exists("old_name")
        assert len(store.list_versions("new_name")) == 1


def test_delete():
    with tempfile.TemporaryDirectory() as tmp:
        store = FormulaStore(tmp)
        store.create_formula("Laca", _sample_formula())
        store.delete_formula("laca")
        assert not store.formula_exists("laca")
        assert store.list_formulas() == []
        try:
            store.delete_formula("laca")
            raise AssertionError("expected ValueError")
        except ValueError:
            pass


def test_persistence_across_instances():
    with tempfile.TemporaryDirectory() as tmp:
        store = FormulaStore(tmp)
        store.create_formula("Laca", _sample_formula())
        store.save_formula("laca", store.get_formula("laca"),
                           change_reason="v2 razon")
        store.save_snapshot_image("laca", 2, b"\x89PNG data")
        store2 = FormulaStore(tmp)
        assert len(store2.list_formulas()) == 1
        assert store2.get_formula_meta("laca")["version"] == 2
        assert len(store2.list_versions("laca")) == 2
        assert store2.list_versions("laca")[-1].reason == "v2 razon"
        assert store2.get_snapshot_images("laca", 2)
        log = store2.get_log()
        assert any(e["action"] == "commit" and e["version"] == 2 for e in log)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  PASS {t.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    main()
