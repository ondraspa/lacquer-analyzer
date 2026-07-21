"""Pigment reference database — search by C.I. name, trade name, or chemical class."""

from typing import Dict, List, Optional, Any

PIGMENTS: List[Dict[str, Any]] = [
    # ============================================================
    # VIOLET PIGMENTS
    # ============================================================
    {
        "ci_name": "Pigment Violet 23",
        "ci_number": "51319",
        "common_names": ["PV 23", "Carbazole Violet", "Dioxazine Violet"],
        "trade_names": [
            "T67", "Violet T67", "PV23", "Hostaperm Violet RL",
            "Hostaperm Violet RL-NF", "Irgazin Violet D 4070",
            "CINIC PV23", "Violet 23", "Sunfast Violet 23",
            "Fastogen Super Violet", "Sanyo Violet",
            "Heliogen Violet", "Lionogen Violet",
        ],
        "chemical_class": "dioxazine",
        "formula": "C34H22Cl2N4O2",
        "mw": 589.47,
        "cas": "6358-30-1",
        "density_gcm3": 1.40,
        "oil_absorption": 40,
        "ph_range": "4.0–9.0",
        "heat_stability_c": 200,
        "lightfastness": "excellent",
        "weatherfastness": "good",
        "applications": ["automotive", "industrial coatings", "lacquer", "printing ink"],
        "notes": "Quinoxalinedione structure. Most important violet in coatings. High tinting strength.",
    },
    {
        "ci_name": "Pigment Violet 19",
        "ci_number": "73900",
        "common_names": ["PV 19", "Quinacridone Violet", "Gamma Violet"],
        "trade_names": [
            "PV19", "Quinacridone Violet", "Hostaperm Red E5B 02",
            "Cinquasia Red B-PT", "Cinquasia Violet R",
        ],
        "chemical_class": "quinacridone",
        "formula": "C20H12N2O2",
        "mw": 312.32,
        "cas": "1047-16-1",
        "density_gcm3": 1.47,
        "heat_stability_c": 180,
        "lightfastness": "excellent",
        "weatherfastness": "excellent",
        "applications": ["automotive", "industrial coatings", "lacquer", "artists colors"],
        "notes": "Gamma crystal phase. Excellent durability. High cost.",
    },
    {
        "ci_name": "Pigment Violet 37",
        "ci_number": "51345",
        "common_names": ["PV 37", "Dioxazine Violet"],
        "trade_names": ["PV37", "Fastogen Super Violet B"],
        "chemical_class": "dioxazine",
        "formula": "C36H26Cl2N4O2",
        "mw": 617.52,
        "cas": "17741-63-8",
        "density_gcm3": 1.35,
        "lightfastness": "excellent",
        "applications": ["coatings", "plastics"],
        "notes": "Bluer shade than PV 23. Good heat stability.",
    },
    # ============================================================
    # BLUE PIGMENTS
    # ============================================================
    {
        "ci_name": "Pigment Blue 15:3",
        "ci_number": "74160",
        "common_names": ["PB 15:3", "Phthalo Blue", "Copper Phthalocyanine Blue"],
        "trade_names": [
            "Heliogen Blue L 7101 F", "Heliogen Blue L 6901 F",
            "Sunfast Blue 15:3", "Lionol Blue FG-7330",
            "Fastogen Blue FGA", "CINIC PB15:3",
        ],
        "chemical_class": "phthalocyanine",
        "formula": "C32H16CuN8",
        "mw": 576.07,
        "cas": "147-14-8",
        "density_gcm3": 1.60,
        "oil_absorption": 38,
        "ph_range": "3.0–10.0",
        "heat_stability_c": 220,
        "lightfastness": "excellent",
        "weatherfastness": "excellent",
        "applications": ["automotive", "industrial coatings", "lacquer", "printing ink"],
        "notes": "Copper phthalocyanine, beta crystal form. Most widely used organic blue in coatings.",
    },
    {
        "ci_name": "Pigment Blue 15:1",
        "ci_number": "74160",
        "common_names": ["PB 15:1", "Phthalo Blue Alpha"],
        "trade_names": ["Heliogen Blue K 6902 F", "Sunfast Blue 15:1"],
        "chemical_class": "phthalocyanine",
        "formula": "C32H16CuN8",
        "mw": 576.07,
        "cas": "147-14-8",
        "density_gcm3": 1.55,
        "lightfastness": "excellent",
        "applications": ["coatings", "plastics"],
        "notes": "Alpha crystal form, redder shade than 15:3.",
    },
    {
        "ci_name": "Pigment Blue 29",
        "ci_number": "77007",
        "common_names": ["PB 29", "Ultramarine Blue", "Ultramarine"],
        "trade_names": ["Ultramarine Blue 5080", "Nubifarm PB29"],
        "chemical_class": "inorganic / aluminosilicate",
        "formula": "Na6-8Al6Si6O24S2-4",
        "mw": 862.58,
        "cas": "57455-37-5",
        "density_gcm3": 2.35,
        "heat_stability_c": 350,
        "lightfastness": "excellent",
        "acid_resistance": "poor",
        "applications": ["industrial coatings", "lacquer", "artists colors"],
        "notes": "Natural mineral (lapis lazuli) or synthetic. Poor acid resistance limits use.",
    },
    # ============================================================
    # RED PIGMENTS
    # ============================================================
    {
        "ci_name": "Pigment Red 254",
        "ci_number": "56110",
        "common_names": ["PR 254", "DPP Red", "Pyrrole Red"],
        "trade_names": [
            "Irgazin DPP Red BTR", "Cromophtal DPP Red",
            "Sunfast Red 254", "CINIC PR254",
        ],
        "chemical_class": "diketopyrrolopyrrole (DPP)",
        "formula": "C18H10Cl2N2O2",
        "mw": 357.19,
        "cas": "84632-65-7",
        "density_gcm3": 1.57,
        "oil_absorption": 41,
        "heat_stability_c": 240,
        "lightfastness": "excellent",
        "weatherfastness": "excellent",
        "applications": ["automotive", "industrial coatings", "lacquer"],
        "notes": "High-performance red. Excellent opacity and durability.",
    },
    {
        "ci_name": "Pigment Red 170",
        "ci_number": "12475",
        "common_names": ["PR 170", "Naphthol Red"],
        "trade_names": ["Permanent Red F5RK", "Naphthol Red F5RK", "Sunfast Red 170"],
        "chemical_class": "naphthol AS",
        "formula": "C26H22N4O4",
        "mw": 454.48,
        "cas": "2786-76-7",
        "density_gcm3": 1.38,
        "heat_stability_c": 180,
        "lightfastness": "good",
        "weatherfastness": "fair",
        "applications": ["industrial coatings", "printing ink", "lacquer"],
        "notes": "Medium-cost red. Good for general industrial use.",
    },
    {
        "ci_name": "Pigment Red 112",
        "ci_number": "12370",
        "common_names": ["PR 112", "Naphthol Red"],
        "trade_names": ["Permanent Red FGR"],
        "chemical_class": "naphthol AS",
        "formula": "C19H13Cl4N3O4",
        "mw": 489.14,
        "cas": "6535-46-2",
        "density_gcm3": 1.47,
        "lightfastness": "good",
        "applications": ["lacquer", "printing ink"],
        "notes": "Naphthol AS red with high tinting strength.",
    },
    {
        "ci_name": "Pigment Red 48:1",
        "ci_number": "15865:1",
        "common_names": ["PR 48:1", "Lake Red 2B Ba"],
        "trade_names": ["Permanent Red 2B"],
        "chemical_class": "monoazo (Ba lake)",
        "formula": "C18H11BaClN2O6S",
        "mw": 628.24,
        "cas": "7585-41-3",
        "density_gcm3": 1.68,
        "lightfastness": "fair",
        "applications": ["printing ink", "lacquer"],
        "notes": "Barium lake of monoazo. Good brightness, limited weatherfastness.",
    },
    {
        "ci_name": "Pigment Red 57:1",
        "ci_number": "15850:1",
        "common_names": ["PR 57:1", "Lithol Rubine 4B", "Rubine Red"],
        "trade_names": ["Lithol Rubine 4B", "Rubine Red", "Sunfast Red 57:1"],
        "chemical_class": "monoazo (Ca lake)",
        "formula": "C18H12CaN2O6S",
        "mw": 424.44,
        "cas": "5281-04-9",
        "density_gcm3": 1.60,
        "lightfastness": "fair",
        "applications": ["printing ink", "lacquer"],
        "notes": "Calcium lake of monoazo. Bluish red. Common in packaging inks.",
    },
    # ============================================================
    # YELLOW PIGMENTS
    # ============================================================
    {
        "ci_name": "Pigment Yellow 83",
        "ci_number": "21108",
        "common_names": ["PY 83", "Diarylide Yellow"],
        "trade_names": [
            "Permanent Yellow HR", "Sunbrite Yellow 83",
            "CINIC PY83",
        ],
        "chemical_class": "diarylide",
        "formula": "C36H32Cl4N6O8",
        "mw": 818.49,
        "cas": "5567-15-7",
        "density_gcm3": 1.38,
        "oil_absorption": 46,
        "heat_stability_c": 180,
        "lightfastness": "good",
        "applications": ["industrial coatings", "printing ink", "lacquer"],
        "notes": "High strength diarylide yellow. Good general purpose.",
    },
    {
        "ci_name": "Pigment Yellow 151",
        "ci_number": "13980",
        "common_names": ["PY 151", "Benzimidazolone Yellow H4G"],
        "trade_names": [
            "Hostaperm Yellow H4G", "Permanent Yellow H4G",
        ],
        "chemical_class": "benzimidazolone",
        "formula": "C18H15N5O5",
        "mw": 381.34,
        "cas": "31837-42-0",
        "density_gcm3": 1.54,
        "heat_stability_c": 200,
        "lightfastness": "excellent",
        "weatherfastness": "good",
        "applications": ["automotive", "industrial coatings", "lacquer"],
        "notes": "Greenish yellow. High performance. Excellent heat stability.",
    },
    {
        "ci_name": "Pigment Yellow 74",
        "ci_number": "11741",
        "common_names": ["PY 74", "Hansa Yellow"],
        "trade_names": ["Hansa Yellow 5GX", "Sunbrite Yellow 74"],
        "chemical_class": "monoazo",
        "formula": "C18H18N4O6",
        "mw": 386.36,
        "cas": "6358-31-2",
        "density_gcm3": 1.30,
        "lightfastness": "good",
        "applications": ["lacquer", "printing ink"],
        "notes": "Hansa type. Greenish yellow. Moderate bleed resistance.",
    },
    {
        "ci_name": "Pigment Yellow 109",
        "ci_number": "56284",
        "common_names": ["PY 109", "Isoindolinone Yellow"],
        "trade_names": ["Irgazin Yellow 2GLTE"],
        "chemical_class": "isoindolinone",
        "formula": "C22H8Cl8N2O2",
        "mw": 639.96,
        "cas": "127438-84-0",
        "density_gcm3": 1.75,
        "heat_stability_c": 260,
        "lightfastness": "excellent",
        "weatherfastness": "excellent",
        "applications": ["automotive", "industrial coatings"],
        "notes": "High-performance greenish yellow. Very high heat stability.",
    },
    {
        "ci_name": "Pigment Yellow 42",
        "ci_number": "77492",
        "common_names": ["PY 42", "Yellow Iron Oxide"],
        "trade_names": ["Bayferrox 920", "Bayferrox 3910", "Mapico Yellow"],
        "chemical_class": "inorganic / iron oxide",
        "formula": "Fe2O3·H2O",
        "mw": 177.69,
        "cas": "51274-00-1",
        "density_gcm3": 3.90,
        "heat_stability_c": 300,
        "lightfastness": "excellent",
        "weatherfastness": "excellent",
        "applications": ["coatings", "lacquer", "primers"],
        "notes": "Synthetic yellow iron oxyhydroxide. Goethite structure. Opaque, very durable.",
    },
    # ============================================================
    # WHITE PIGMENTS
    # ============================================================
    {
        "ci_name": "Pigment White 6",
        "ci_number": "77891",
        "common_names": ["PW 6", "Titanium Dioxide", "TiO2"],
        "trade_names": [
            "Kronos 2300", "Ti-Pure R-706", "Ti-Pure R-902+",
            "Tronox CR-828", "Hombitan R 611",
        ],
        "chemical_class": "inorganic / titanium dioxide",
        "formula": "TiO2",
        "mw": 79.87,
        "cas": "13463-67-7",
        "density_gcm3": 4.00,
        "oil_absorption": 18,
        "ph_range": "6.5–8.5",
        "heat_stability_c": 400,
        "lightfastness": "excellent",
        "weatherfastness": "excellent",
        "applications": ["all coatings", "lacquer", "automotive", "architectural"],
        "notes": "Rutile crystal form. Most important white pigment. High refractive index.",
    },
    # ============================================================
    # BLACK PIGMENTS
    # ============================================================
    {
        "ci_name": "Pigment Black 7",
        "ci_number": "77266",
        "common_names": ["PBk 7", "Carbon Black"],
        "trade_names": [
            "Carbon Black FW-200", "Printex 200", "Mogul L",
            "Raven 14", "Black Pearls 700",
        ],
        "chemical_class": "inorganic / carbon",
        "formula": "C",
        "mw": 12.01,
        "cas": "1333-86-4",
        "density_gcm3": 1.80,
        "oil_absorption": 120,
        "lightfastness": "excellent",
        "weatherfastness": "excellent",
        "applications": ["all coatings", "lacquer", "automotive"],
        "notes": "Furnace black grade. High tinting strength. Jetness depends on particle size.",
    },
    {
        "ci_name": "Pigment Black 11",
        "ci_number": "77499",
        "common_names": ["PBk 11", "Black Iron Oxide", "Magnetite"],
        "trade_names": ["Bayferrox 318", "Bayferrox 330", "Mapico Black"],
        "chemical_class": "inorganic / iron oxide",
        "formula": "Fe3O4",
        "mw": 231.53,
        "cas": "1317-61-9",
        "density_gcm3": 4.80,
        "heat_stability_c": 350,
        "lightfastness": "excellent",
        "weatherfastness": "excellent",
        "applications": ["primers", "industrial coatings", "lacquer"],
        "notes": "Synthetic magnetite. Opaque, low oil absorption. Very durable.",
    },
    # ============================================================
    # GREEN PIGMENTS
    # ============================================================
    {
        "ci_name": "Pigment Green 7",
        "ci_number": "74260",
        "common_names": ["PG 7", "Phthalo Green", "Chlorinated Phthalo"],
        "trade_names": [
            "Heliogen Green L 8730", "Sunfast Green 7",
            "Lionol Green 6Y-501", "CINIC PG7",
        ],
        "chemical_class": "phthalocyanine",
        "formula": "C32Cl16CuN8",
        "mw": 1127.16,
        "cas": "1328-53-6",
        "density_gcm3": 2.00,
        "oil_absorption": 35,
        "heat_stability_c": 220,
        "lightfastness": "excellent",
        "weatherfastness": "excellent",
        "applications": ["automotive", "industrial coatings", "lacquer"],
        "notes": "Chlorinated copper phthalocyanine. Blue shade green. High durability.",
    },
    {
        "ci_name": "Pigment Green 36",
        "ci_number": "74265",
        "common_names": ["PG 36", "Phthalo Green Y", "Brilliant Green"],
        "trade_names": ["Heliogen Green L 9361", "Sunfast Green 36"],
        "chemical_class": "phthalocyanine",
        "formula": "C32Br8Cl8CuN8",
        "mw": 1635.59,
        "cas": "14302-13-7",
        "density_gcm3": 2.20,
        "heat_stability_c": 220,
        "lightfastness": "excellent",
        "applications": ["automotive", "coatings", "lacquer"],
        "notes": "Brominated/chlorinated copper phthalocyanine. Yellow shade green.",
    },
    # ============================================================
    # ORANGE PIGMENTS
    # ============================================================
    {
        "ci_name": "Pigment Orange 73",
        "ci_number": "561170",
        "common_names": ["PO 73", "DPP Orange"],
        "trade_names": ["Irgazin DPP Orange RA", "Cromophtal DPP Orange"],
        "chemical_class": "diketopyrrolopyrrole (DPP)",
        "formula": "C20H10Cl2N2O2",
        "mw": 381.21,
        "cas": "84632-59-7",
        "density_gcm3": 1.53,
        "heat_stability_c": 220,
        "lightfastness": "excellent",
        "weatherfastness": "excellent",
        "applications": ["automotive", "coatings"],
        "notes": "DPP orange. High performance, excellent opacity.",
    },
    {
        "ci_name": "Pigment Orange 34",
        "ci_number": "21115",
        "common_names": ["PO 34", "Diarylide Orange"],
        "trade_names": ["Permanent Orange RL"],
        "chemical_class": "diarylide",
        "formula": "C32H26Cl4N6O6",
        "mw": 748.40,
        "cas": "15793-73-4",
        "density_gcm3": 1.35,
        "lightfastness": "fair",
        "applications": ["lacquer", "printing ink"],
        "notes": "Diarylide orange. Good strength, moderate durability.",
    },
    # ============================================================
    # EFFECT PIGMENTS (not C.I. classified)
    # ============================================================
    {
        "ci_name": None,
        "ci_number": None,
        "common_names": ["Aluminum Powder", "Aluminum Flake"],
        "trade_names": ["Stapa Metallux", "Alu-Sperse", "Alpaste"],
        "chemical_class": "metallic effect",
        "formula": "Al",
        "mw": 26.98,
        "cas": "7429-90-5",
        "density_gcm3": 2.70,
        "lightfastness": "excellent",
        "applications": ["automotive metallic", "industrial coatings", "lacquer"],
        "notes": "Leafing or non-leafing grades. Particle size controls sparkle.",
    },
    {
        "ci_name": None,
        "ci_number": None,
        "common_names": ["Mica", "Pearlescent Pigment"],
        "trade_names": ["Iriodin 100", "Mearlin", "Afflair"],
        "chemical_class": "effect / mica-coated TiO2",
        "formula": "KAl2(AlSi3O10)(OH)2",
        "mw": 398.31,
        "cas": "12001-26-2",
        "density_gcm3": 3.00,
        "lightfastness": "excellent",
        "applications": ["automotive", "lacquer", "cosmetic coatings"],
        "notes": "TiO2-coated mica platelets. Interference colors via thin-film optics.",
    },
]


class PigmentDatabase:
    """Search pigments by C.I. name, trade name, chemical class, or application."""

    def __init__(self):
        self._by_ci_name: Dict[str, dict] = {}
        self._by_ci_number: Dict[str, dict] = {}
        self._by_trade_name: Dict[str, dict] = {}
        self._by_common_name: Dict[str, dict] = {}
        self._all: List[dict] = []
        self._build_index()

    def _build_index(self):
        for p in PIGMENTS:
            self._all.append(p)
            if p["ci_name"]:
                self._by_ci_name[p["ci_name"].lower()] = p
            if p["ci_number"]:
                self._by_ci_number[p["ci_number"]] = p
            for name in p["trade_names"]:
                self._by_trade_name[name.strip().lower()] = p
            for name in p["common_names"]:
                self._by_common_name[name.strip().lower()] = p

    def search(self, query: str) -> List[dict]:
        """Search across all name fields. Case-insensitive. Returns matching pigments."""
        q = query.strip().lower()
        if not q:
            return []

        seen = set()
        results = []

        for source in (self._by_trade_name, self._by_common_name, self._by_ci_name, self._by_ci_number):
            for key, pigment in source.items():
                if q in key or key in q:
                    pid = id(pigment)
                    if pid not in seen:
                        seen.add(pid)
                        results.append(pigment)

        # Also search chemical class
        for p in self._all:
            chem = (p.get("chemical_class") or "").lower()
            if q in chem:
                if id(p) not in seen:
                    seen.add(id(p))
                    results.append(p)

        return results

    def resolve_trade_name(self, trade_name: str) -> Optional[dict]:
        """Look up a specific trade name like 'T67' and return the pigment data."""
        return self._by_trade_name.get(trade_name.strip().lower())

    def get_by_ci_name(self, ci_name: str) -> Optional[dict]:
        return self._by_ci_name.get(ci_name.strip().lower())

    def get_by_ci_number(self, ci_number: str) -> Optional[dict]:
        return self._by_ci_number.get(ci_number.strip())

    def all_pigments(self) -> List[dict]:
        return list(self._all)

    def format_row(self, p: dict) -> str:
        ci = p["ci_name"] or "—"
        num = p["ci_number"] or "—"
        cls = p.get("chemical_class", "?")
        density = p.get("density_gcm3", "?")
        app = ", ".join(p.get("applications", [])[:3])
        name = (p["common_names"] or [p["ci_name"] or "?"])[0]
        return f"{ci:32s} {num:8s}  {cls:22s}  {str(density):6s} g/cm³  {app}"

    def summary(self, p: dict) -> str:
        lines = [
            f"  C.I. Name:      {p['ci_name'] or '—'}",
            f"  C.I. Number:    {p['ci_number'] or '—'}",
            f"  Common Names:   {', '.join(p['common_names'])}",
            f"  Trade Names:    {', '.join(p['trade_names'][:5])}",
            f"  Chemical Class: {p.get('chemical_class', '?')}",
            f"  Formula:        {p.get('formula', '?')}",
            f"  CAS#:           {p.get('cas', '?')}",
            f"  Density:        {p.get('density_gcm3', '?')} g/cm³",
            f"  Oil Absorption: {p.get('oil_absorption', '?')} g/100g",
            f"  Heat Stability: {p.get('heat_stability_c', '?')} °C",
            f"  Lightfastness:  {p.get('lightfastness', '?')}",
            f"  Applications:   {', '.join(p.get('applications', []))}",
        ]
        return "\n".join(lines) + f"\n  Notes: {p.get('notes', '')}"


DB = PigmentDatabase()
