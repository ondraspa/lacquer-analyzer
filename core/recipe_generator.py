import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

NC_HANSEN = (16.2, 14.1, 9.5)
NC_TG_K = 463.0
CUT_TEMP_K = 328.0
ROOM_TEMP_K = 298.0
WLF_C1 = 17.44
WLF_C2 = 51.6

INGREDIENTS: Dict[str, Dict] = {
    "nitrocellulose_30s": dict(role="resin", mw=270.0, density=1.65, tg_k=463.0),
    "dibutyl_phthalate": dict(role="plasticizer", mw=278.3, density=1.045, tg_k=183.0, hansen=(18.2, 8.6, 4.0)),
    "castor_oil": dict(role="plasticizer", mw=933.4, density=0.961, tg_k=223.0, hansen=(16.2, 4.9, 7.2)),
    "dioctyl_phthalate": dict(role="plasticizer", mw=390.6, density=0.986, tg_k=188.0, hansen=(16.6, 9.5, 3.4)),
    "tricresyl_phosphate": dict(role="plasticizer", mw=368.4, density=1.160, tg_k=213.0, hansen=(19.4, 9.5, 5.9)),
    "camphor": dict(role="plasticizer", mw=152.2, density=0.990, tg_k=250.0, hansen=(18.2, 8.1, 5.1)),
    "acetone": dict(role="solvent", mw=58.1, density=0.790, bp_c=56.0, evap=11.6, hansen=(15.5, 10.4, 7.0)),
    "mek": dict(role="solvent", mw=72.1, density=0.805, bp_c=80.0, evap=3.8, hansen=(16.0, 9.0, 5.1)),
    "mibk": dict(role="solvent", mw=100.2, density=0.800, bp_c=116.0, evap=1.4, hansen=(15.3, 6.1, 4.1)),
    "ethyl_acetate": dict(role="solvent", mw=88.1, density=0.902, bp_c=77.0, evap=4.1, hansen=(15.8, 5.3, 7.2)),
    "butyl_acetate": dict(role="solvent", mw=116.2, density=0.882, bp_c=126.0, evap=1.0, hansen=(15.8, 3.7, 6.3)),
    "ethanol": dict(role="solvent", mw=46.1, density=0.789, bp_c=78.0, evap=1.7, hansen=(15.8, 8.8, 19.4)),
    "butanol": dict(role="solvent", mw=74.1, density=0.810, bp_c=117.7, evap=0.44, hansen=(16.0, 5.7, 15.8)),
    "toluene": dict(role="solvent", mw=92.1, density=0.867, bp_c=110.6, evap=1.9, hansen=(18.0, 1.4, 2.0)),
    "xylene": dict(role="solvent", mw=106.2, density=0.864, bp_c=139.0, evap=0.7, hansen=(17.8, 1.0, 3.1)),
    "cellosolve_acetate": dict(role="solvent", mw=132.2, density=0.974, bp_c=156.0, evap=0.22, hansen=(16.2, 5.1, 7.8)),
    "diacetone_alcohol": dict(role="solvent", mw=116.2, density=0.938, bp_c=166.0, evap=0.12, hansen=(15.1, 6.5, 9.9)),
    "butyl_cellosolve": dict(role="solvent", mw=118.2, density=0.902, bp_c=171.0, evap=0.07, hansen=(16.0, 5.1, 12.3)),
}

R_NS_IN_NS = {}
R_SOLVENTS = [
    "acetone", "mek", "mibk", "ethyl_acetate", "butyl_acetate", "ethanol",
    "butanol", "toluene", "xylene", "cellosolve_acetate", "diacetone_alcohol",
    "butyl_cellosolve",
]
R_PLASTICIZERS = [
    "dibutyl_phthalate", "castor_oil", "dioctyl_phthalate",
    "tricresyl_phosphate", "camphor",
]


@dataclass
class Scores:
    ok: bool
    dry_h: float
    residual_idx: float
    tg_room_c: float
    cut_delta_k: float
    modulus_ratio_cut: float
    crater_idx: float
    hansen_dist: float
    solids_pct: float
    plast_ratio: float
    total: float


def _wb_hansen(fracs: Dict[str, float]) -> Tuple[float, float, float]:
    total = sum(fracs.values())
    h = np.zeros(3)
    for k, v in fracs.items():
        if not v:
            continue
        ing = INGREDIENTS[k]
        if "hansen" not in ing:
            continue
        vol = v / ing["density"]
        h += vol * np.array(ing["hansen"])
    n_vol = sum(fracs[k] / INGREDIENTS[k]["density"] for k in fracs if "hansen" in INGREDIENTS[k])
    if n_vol <= 0:
        return (0.0, 0.0, 0.0)
    return tuple(h / n_vol)


def hansen_distance(fracs: Dict[str, float], target: Tuple[float, float, float] = NC_HANSEN) -> float:
    bd, bp, bh = _wb_hansen(fracs)
    return math.sqrt(4.0 * (bd - target[0]) ** 2 + (bp - target[1]) ** 2 + (bh - target[2]) ** 2)


def evaporation_metrics(fracs: Dict[str, float]) -> Tuple[float, float, float, float]:
    solv = {k: v for k, v in fracs.items() if INGREDIENTS[k]["role"] == "solvent"}
    if not solv:
        return (0.0, 0.0, 1.0, 0.0)
    vol = {k: v / INGREDIENTS[k]["density"] for k, v in solv.items()}
    tot = sum(vol.values())
    eff = sum(vol[k] * INGREDIENTS[k]["evap"] for k in vol) / tot
    fastest = max(INGREDIENTS[k]["evap"] for k in vol)
    slowest = min(INGREDIENTS[k]["evap"] for k in vol)
    slow_mass = sum(v for k, v in solv.items() if INGREDIENTS[k]["evap"] < 0.35)
    slow_frac = slow_mass / max(sum(solv.values()), 1e-9)
    return eff, fastest / max(slowest, 1e-9), slow_frac, solv


def dry_time_h(fracs: Dict[str, float]) -> float:
    eff, _, slow_frac, _ = evaporation_metrics(fracs)
    if eff <= 0:
        return 999.0
    return 12.0 / (eff ** 0.9)


def residual_solvent_index(fracs: Dict[str, float]) -> float:
    _, _, slow_frac, _ = evaporation_metrics(fracs)
    return 100.0 * slow_frac


def fox_tg_k(fracs: Dict[str, float]) -> float:
    solids = {k: v for k, v in fracs.items() if INGREDIENTS[k]["role"] != "solvent"}
    if not solids:
        return 0.0
    m = sum(solids.values())
    inv = sum((v / m) / INGREDIENTS[k]["tg_k"] for k, v in solids.items())
    return 1.0 / inv if inv > 0 else 0.0


def wlf_shift(t_k: float, tg_k: float) -> float:
    d = t_k - tg_k
    if d <= 0:
        return 1e6
    return 10 ** (WLF_C1 * d / (WLF_C2 + d))


def evaluate(fracs: Dict[str, float]) -> Scores:
    solids = sum(v for k, v in fracs.items() if INGREDIENTS[k]["role"] != "solvent")
    total = sum(fracs.values())
    solids_pct = 100.0 * solids / total
    plast = sum(v for k, v in fracs.items() if INGREDIENTS[k]["role"] == "plasticizer")
    plast_ratio = plast / max(solids, 1e-9)
    tg_k = fox_tg_k(fracs)
    tg_c = tg_k - 273.15
    cut_delta = CUT_TEMP_K - tg_k
    mod_room = wlf_shift(ROOM_TEMP_K, tg_k)
    mod_cut = wlf_shift(CUT_TEMP_K, tg_k)
    mod_ratio = mod_cut / max(mod_room, 1e-12)
    eff, spread, slow_frac, _ = evaporation_metrics(fracs)
    crater = math.log1p(spread - 1.0) * (1.0 + 2.0 * slow_frac)
    hd = hansen_distance(fracs)
    dry = dry_time_h(fracs)

    ok = True
    msg_penalty = 0.0
    if not (10.0 <= solids_pct <= 28.0):
        ok = False
        msg_penalty += 50.0
    if not (0.15 <= plast_ratio <= 0.60):
        ok = False
        msg_penalty += 50.0
    if hd > 9.0:
        ok = False
        msg_penalty += 50.0
    if not (0.5 <= dry <= 72.0):
        ok = False
        msg_penalty += 50.0
    if not (5.0 <= cut_delta <= 55.0):
        ok = False
        msg_penalty += 50.0

    d_dry = max(abs(dry - 8.0) - 4.0, 0.0)
    d_res = residual_solvent_index(fracs)
    d_cut = max(abs(cut_delta - 28.0) - 12.0, 0.0)
    d_crat = max(crater - 3.0, 0.0) * 4.0
    d_hd = max(hd - 4.0, 0.0) * 4.0
    d_tg = max(abs(tg_c - 30.0) - 10.0, 0.0)
    total = (msg_penalty
             + 2.0 * d_dry
             + 0.8 * d_res
             + 1.0 * d_cut
             + 6.0 * d_crat
             + 4.0 * d_hd
             + 0.6 * d_tg
             + abs(solids_pct - 18.0) * 0.25)
    return Scores(
        ok=ok, dry_h=dry, residual_idx=d_res, tg_room_c=tg_c,
        cut_delta_k=cut_delta, modulus_ratio_cut=mod_ratio, crater_idx=crater,
        hansen_dist=hd, solids_pct=solids_pct, plast_ratio=plast_ratio, total=total,
    )


def _sample_recipe(rng: random.Random) -> Dict[str, float]:
    solids_pct = rng.uniform(13.0, 25.0)
    plast_ratio = rng.uniform(0.18, 0.52)
    n_plast = rng.choice([1, 1, 2, 2])
    plastis = rng.sample(R_PLASTICIZERS, k=n_plast)
    plast_w = np.array([rng.uniform(0.0, 1.0) for _ in range(n_plast)])
    plast_w = plast_w / plast_w.sum()
    n_solv = rng.choice([3, 3, 4, 4, 5])
    solvs = rng.sample(R_SOLVENTS, k=n_solv)
    solv_w = np.array([rng.uniform(0.0, 1.0) for _ in range(n_solv)])
    solv_w = solv_w / solv_w.sum()
    rem = 100.0 - solids_pct
    out = {"nitrocellulose_30s": solids_pct * (1.0 - plast_ratio)}
    for k, w in zip(plastis, plast_w):
        out[k] = solids_pct * plast_ratio * w
    for k, w in zip(solvs, solv_w):
        out[k] = rem * w
    return out


def _random_search(n: int, rng: random.Random) -> List[Tuple[Dict[str, float], Scores]]:
    out = []
    for _ in range(n):
        f = _sample_recipe(rng)
        s = evaluate(f)
        if s.ok:
            out.append((f, s))
    out.sort(key=lambda t: t[1].total)
    return out


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    keys = sorted(set(a) | set(b))
    va = np.array([a.get(k, 0.0) for k in keys])
    vb = np.array([b.get(k, 0.0) for k in keys])
    na = np.linalg.norm(va)
    nb = np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def generate(n_samples: int = 4000, top_k: int = 5, seed: int = 7) -> List[Tuple[Dict[str, float], Scores]]:
    rng = random.Random(seed)
    ranked = _random_search(n_samples, rng)
    if not ranked:
        return []
    chosen = []
    for cand in ranked:
        if all(_cosine(cand[0], c[0]) < 0.995 for c in chosen):
            chosen.append(cand)
        if len(chosen) >= top_k:
            break
    return chosen


def recipe_data(name: str, fracs: Dict[str, float], scores: Scores, notes: str) -> Dict:
    comps = []
    for k, v in sorted(fracs.items(), key=lambda t: -t[1]):
        if v <= 0:
            continue
        label = INGREDIENTS[k]["role"]
        comps.append(dict(id=k, name=k, concentration_pct=float(round(v, 2))))
    return dict(
        id=_slug(name),
        name=name,
        target_viscosity_mpas=120.0,
        target_solids_pct=float(round(scores.solids_pct, 1)),
        application="corte de maestres (Neumann)",
        coater="flow/automatic coater",
        notes=notes,
        metadata=dict(
            generated=True,
            dry_h=float(round(scores.dry_h, 1)),
            residual_idx=float(round(scores.residual_idx, 1)),
            tg_room_c=float(round(scores.tg_room_c, 1)),
            cut_delta_k=float(round(scores.cut_delta_k, 1)),
            crater_idx=float(round(scores.crater_idx, 3)),
            hansen_dist=float(round(scores.hansen_dist, 3)),
            quality_score=float(round(scores.total, 2)),
        ),
        components=comps,
    )


def _slug(name: str) -> str:
    out = name.lower().strip().replace(" ", "-")
    out = "".join(c for c in out if c.isalnum() or c in "-_")
    return out or "generated-recipe"


def write_report(candidates: List[Tuple[Dict[str, float], Scores]], dest: Optional[Path] = None) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("LACQUER 360 - generator report (physics kernel only)")
    lines.append("=" * 72)
    for i, (fracs, s) in enumerate(candidates, 1):
        lines.append("")
        lines.append(f"[candidate {i}] quality score {s.total:.2f} (lower = better)")
        for k, v in sorted(fracs.items(), key=lambda t: -t[1]):
            lines.append(f"  {k:<22} {v:6.1f} w%  ({INGREDIENTS[k]['role']})")
        lines.append(f"  solids {s.solids_pct:.1f}% | plasticizer/NC {s.plast_ratio:.2f} "
                     f"| dry ~{s.dry_h:.1f} h | residual idx {s.residual_idx:.1f}")
        lines.append(f"  Tg(room) {s.tg_room_c:.1f} C | T_cut - Tg = {s.cut_delta_k:.1f} K "
                     f"| E'(55C)/E'(25C) {s.modulus_ratio_cut:.2e}")
        lines.append(f"  crater idx {s.crater_idx:.3f} | Hansen dist {s.hansen_dist:.3f} "
                     f"(<9.0 gate)")
    text = "\n".join(lines)
    if dest:
        dest.write_text(text)
    return text


def main(argv: List[str]) -> int:
    n = 4000
    top_k = 5
    store = False
    seed = 7
    out_report = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--n" and i + 1 < len(argv):
            n = int(argv[i + 1]); i += 2
        elif a == "--top" and i + 1 < len(argv):
            top_k = int(argv[i + 1]); i += 2
        elif a == "--seed" and i + 1 < len(argv):
            seed = int(argv[i + 1]); i += 2
        elif a == "--store":
            store = True; i += 1
        elif a == "--report" and i + 1 < len(argv):
            out_report = Path(argv[i + 1]); i += 2
        else:
            i += 1
    cands = generate(n_samples=n, top_k=top_k, seed=seed)
    if not cands:
        print("no valid recipes found - relax gates or raise n")
        return 1
    text = write_report(cands, out_report)
    print(text)
    if store:
        from core.formula_store import FormulaStore
        st = FormulaStore()
        for fracs, s in cands:
            name = f"gen_{int(100 - s.total):03d}_{_slug(fracs['nitrocellulose_30s'])}"
            st.create_formula(name, recipe_data(name, fracs, s, "generated by physics-kernel search"),
                              description="LACQUER 360 generated candidate")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))