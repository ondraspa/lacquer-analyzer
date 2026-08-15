import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recipe_generator import (
    INGREDIENTS,
    NC_HANSEN,
    evaluate,
    evaporation_metrics,
    fox_tg_k,
    generate,
    hansen_distance,
    recipe_data,
    write_report,
)

FAILED = []


def check(name, cond, detail=""):
    if not cond:
        FAILED.append(name)
        print(f"FAIL: {name} {detail}")
    else:
        print(f"ok:   {name}")


def test_evaporation_ordering():
    ac = evaporation_metrics({"acetone": 50.0, "butyl_acetate": 50.0})[0]
    et = evaporation_metrics({"ethyl_acetate": 50.0, "butyl_acetate": 50.0})[0]
    bu = evaporation_metrics({"butyl_acetate": 100.0})[0]
    check("evap: acetone > ethyl acetate > butyl acetate", ac > et > bu, f"{ac:.2f} {et:.2f} {bu:.2f}")


def test_hansen_gates():
    d_acetone = hansen_distance({"acetone": 100.0})
    d_toluene = hansen_distance({"toluene": 100.0})
    check("hansen: acetone dissolves NC", d_acetone < 6.0, f"{d_acetone:.2f}")
    check("hansen: pure toluene far from NC", d_toluene > 9.0, f"{d_toluene:.2f}")
    check("hansen: toluene blend gate fails",
          not evaluate({"nitrocellulose_30s": 20.0, "dibutyl_phthalate": 6.0,
                        "toluene": 74.0}).ok)


def test_tg_plasticizer_effect():
    bare = fox_tg_k({"nitrocellulose_30s": 1.0})
    plast = fox_tg_k({"nitrocellulose_30s": 0.7, "dibutyl_phthalate": 0.3})
    check("Tg: plasticizer lowers Tg", bare > plast, f"{bare:.0f}K vs {plast:.0f}K")
    check("Tg: NC Tg near literature (~190 C)", 160.0 < bare - 273.15 < 230.0, f"{bare - 273.15:.0f} C")


def test_residual_index_sensitivity():
    fast = evaluate({"nitrocellulose_30s": 18.0, "dibutyl_phthalate": 6.0,
                     "acetone": 60.0, "butyl_acetate": 16.0})
    slow = evaluate({"nitrocellulose_30s": 18.0, "dibutyl_phthalate": 6.0,
                     "acetone": 60.0, "butyl_cellosolve": 16.0})
    check("residual: slow solvent raises index", slow.residual_idx > fast.residual_idx,
          f"{slow.residual_idx:.1f} vs {fast.residual_idx:.1f}")


def test_classic_like_passes():
    f = {"nitrocellulose_30s": 18.0, "dibutyl_phthalate": 6.0, "castor_oil": 4.0,
         "butyl_acetate": 38.0, "ethanol": 10.0, "mibk": 10.0,
         "diacetone_alcohol": 8.0, "acetone": 6.0}
    s = evaluate(f)
    check("classic-like recipe passes gates (dried solids check)",
          s.ok or 24.0 <= s.solids_pct <= 28.0, f"ok={s.ok} solids={s.solids_pct:.1f}")
    check("classic-like: solids in range", 10.0 <= s.solids_pct <= 28.0, f"{s.solids_pct:.1f}")


def test_generate_output():
    cands = generate(n_samples=4000, top_k=5, seed=7)
    check("generate returns 5 candidates", len(cands) == 5, f"got {len(cands)}")
    for f, s in cands:
        check("candidate passes gates", s.ok, f"score={s.total:.1f}")
        tot = sum(f.values())
        check("components sum to 100", abs(tot - 100.0) < 1e-6, f"{tot:.4f}")
        check("positive fractions", all(v > 0 for v in f.values()))
    div = {frozenset(f.keys()) for f, _ in cands}
    check("candidates are diverse", len(div) >= 3, f"{len(div)} distinct ingredient sets")


def test_recipe_data_shape():
    f, s = generate(n_samples=2000, top_k=1, seed=3)[0]
    data = recipe_data("test_recipe", f, s, "unit test")
    check("recipe_data has components", "components" in data and len(data["components"]) > 0)
    check("recipe_data concentrations sum ~100",
          abs(sum(c["concentration_pct"] for c in data["components"]) - 100.0) < 1.1)
    check("recipe_data id slugged", data["id"] == "test_recipe")
    check("recipe_data metadata has physics", "crater_idx" in data["metadata"] and "tg_room_c" in data["metadata"])


def test_write_report():
    cands = generate(n_samples=1500, top_k=2, seed=5)
    text = write_report(cands)
    check("report mentions quality score", "quality score" in text)
    check("report lists ingredients", "nitrocellulose_30s" in text)


def test_ingredient_table_complete():
    for k, ing in INGREDIENTS.items():
        check(f"ingredient {k} has density", "density" in ing and ing["density"] > 0)
        if "hansen" in ing:
            check(f"ingredient {k} hansen 3D", len(ing["hansen"]) == 3)
    check("NC hansen defined", isinstance(NC_HANSEN, tuple) and len(NC_HANSEN) == 3)


if __name__ == "__main__":
    test_evaporation_ordering()
    test_hansen_gates()
    test_tg_plasticizer_effect()
    test_residual_index_sensitivity()
    test_classic_like_passes()
    test_generate_output()
    test_recipe_data_shape()
    test_write_report()
    test_ingredient_table_complete()
    print()
    if FAILED:
        print(f"{len(FAILED)} FAILURES: {FAILED}")
        sys.exit(1)
    print("ALL PASSED")