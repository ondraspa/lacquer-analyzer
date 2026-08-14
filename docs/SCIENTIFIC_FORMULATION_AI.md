# Modern AI / Scientific Approaches for Lacquer-Blank Formulation & Prediction

Status: research synthesis (web searches + free AI providers, Aug 2026)
Goal: predict coater/cutting behavior from composition AND generate de-novo
lacquer recipes matching or beating the classic Neumann-lathe blanks.

---

## 1. Physics models (the foundation, no ML needed)

1. **Solvent evaporation / drying curve** — binary-solvent Raoult–Flory–Huggins
   model plus UNIFAC activity coefficients predicts the evaporation "ladder" of
   the solvent blend during drying at 25–30 °C. Critical because the high-boiler
   (e.g. diacetone alcohol / butyl cellosolve) must stay in the film during
   coating and leave at the end; wrong ratios cause blushing or cratering.
2. **Viscosity of the wet lacquer** — Jouyban–Acree model + Abraham solute
   parameters predicts mixture viscosity with MRD ≈ 17% for binary solvent
   blends (≈ 7% if one mono-solvent experimental value is known). Governs
   coating thickness, flow, and spin-coat uniformity.
3. **Hansen solubility parameters (HSP)** — NC + plasticizer must sit in the
   Hansen sphere of the solvent blend (δd/δp/δh). HSP distance < ~2–3 MPa^1/2 →
   clear, stable film; too far → haziness, blushing, plating failures.
4. **Plasticizer chemistry** — dibutyl phthalate / castor oil soften the NC
   film (lower Tg → chip flow, less cratering at stylus temp). Cutting hardness
   at 40–70 °C is essentially a Tg/tan δ problem: the film must be glassy at
   room temp but plasticized near the stylus temperature.
5. **Mechanical analogies** — when a stylus cuts a lacquer chip, the material
   acts as a viscoelastic solid; chip flow quality correlates with
   strain-rate-dependent yield. Nothing in the KB quantifies it, but the
   Westrex/AES papers (knowledge base, book article list) describe the desired
   cutting feel in engineering terms.

## 2. Physics-informed ML (2024–2026)

1. **GNN + COSMO-RS (SSD / teacher–student distillation)** — semi-supervised
   GNN on the MixSolDB dataset predicts solubility in *multi-component* solvent
   systems; COSMO-RS-derived data corrects error margins and expands the
   chemical space (RSC Digital Discovery 2025). Direct fit: predicting how a
   new solvent pair will dissolve NC + plasticizer without experiments.
2. **Physics-constrained GNNs** — PEGAT enforces Gibbs–Duhem consistency;
   HASolGNN uses LLM-derived molecular features for multi-solvent solubility.
   Both reduce physically impossible predictions (phase split, negative
   activity).
3. **FDS2S / FDA / FG (formulation graph) family** (npj Comput Mater 2025) —
   the most on-target result found: FG treats a formulation as a *graph* of
   ingredients, learns graph-based mixing rules, and predicts formulation
   properties in-domain and out-of-domain. Trained on 30k solvent mixtures;
   active learning 2–3× faster than random sampling. With a few dozen historic
   lacquer recipes, a small FG-style model + active learning is the most
   realistic supervised path.
4. **LLM features + classical models** — use an LLM to convert a recipe text
   into structured descriptors (SMILES via RDKit, HSP via chemprop/PyG) and
   feed those into a small GPR/GP or GNN; combines NLP of old recipes with
   physics-based featurization.

## 3. Optimization / de-novo generation

1. **Bayesian optimization (BO)** — Bgolearn framework (npj Comput Mater 2026):
   GP surrogates, multi-objective (hardness + chip flow + noise + plating
   compatibility), uncertainty quantification, acquisition functions
   (EI/UCB/NEHVI). Reported 40–60% fewer experiments vs random/grid/GA. FABO
   uses adaptive representations. With only dozens of recipes this is THE
   realistic design loop: propose 3–5 candidate recipes per round, workshop
   casts one disc, quality score returns into the surrogate.
2. **Physics-model-based Design of Experiments (MBDoE)** — physics-informed
   parametric models (UNIFAC + Tg mixing rules) can beat black-box GP with as
   few as 5 experiments. Blend section 1 physics into the BO surrogate.
3. **NSGA-II / pymoo** multi-objective screening of generated candidates
   (hardness ↔ chip flow ↔ evaporation window ↔ plating compatibility).
4. **Neuro-symbolic / agentic search** — AI4S-SDS (MCTS + differentiable
   physics engine + LLM agents) discovered a photoresist developer beating the
   commercial benchmark; ToolMol is an evolutionary LLM agent with RDKit-backed
   tool calls and multi-objective GA for de-novo molecules. These are heavier
   but the right pattern if the workshop wants fully automatic new-solvent
   discovery.

## 4. Concrete tooling (from Mistral, cross-checked)

| Need | Library |
|---|---|
| Molecular descriptors / SMILES | RDKit |
| Deep fingerprints | DeepChem |
| GNN property models | chemprop (D-MPNN), pytorch-geometric (MEGNet) |
| Solubility / solvent prediction | COSMO-RS or MixSolDB-based GNN |
| Bayesian optimization | BoTorch (GPyTorch), GPyOpt, Bgolearn |
| Multi-objective search | pymoo (NSGA-II) |
| Active learning | modAL / ALPy, or BoTorch qNEHVI |
| Evaporation / transport simulation | COMSOL (PyCOMSOL) or open UNIFAC code |
| Formulation-as-graph | FG model (npj Comput Mater 2025) |

## 5. Proposed hybrid architecture for this repo

```
historic recipes (KB + formula store)
        │
        ▼
structured ingredients (SMILES/HSP/Tg via RDKit + lookup tables)
        │
        ▼
two parallel surrogates:
  (a) physics: UNIFAC evaporation ladder + Jouyban–Acree viscosity
      + HSP distance + Flory–Fox Tg of the plasticized film
  (b) ML: FG-style formulation graph or GPR on (descriptors → quality)
        │
        ▼
multi-objective BO (BoTorch/pymoo): propose next 3–5 recipes
        │
        ▼
workshop casts one disc per candidate → quality score back into store
        │
        ▼
active-learning loop; after ~20–40 rounds: new recipe ≥ classic blank
```

Key risk: with a few dozen recipes, a purely learned model is underdetermined —
hence the physics surrogate must carry the extrapolation; ML is for ranking and
uncertainty, not for standalone prediction. Feasibility is high: everything
needed (RDKit, scikit-learn GPR, pymoo) is pip-installable and CPU-only.

## 6. AI provider answers (round 5, Aug 2026)

- Perplexity: sign-in wall mid-session (answer lost) — flaky free tier.
- Mistral (full answer, stored in /tmp/opencode/ai_answers/mistral_vibe.txt):
  GNNs (MEGNet/D-MPNN via chemprop), physics-informed PyG + COMSOL for drying,
  BO via GPyOpt/BoTorch for the small-dataset quality map, generative RLMD
  (MolDQN/GraphAF), NSGA-II via pymoo, active learning via modAL/ALPy;
  workflow: RDKit featurize → GNN train → RLMD generate → NSGA-II screen →
  BO validate. This matches the web research (sections 2–4) well.
