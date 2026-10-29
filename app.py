# -*- coding: utf-8 -*-
"""
Carte de la dépendance automobile contrainte — app Streamlit.
Lit les fichiers produits par le notebook Colab, déposés dans le dossier data/.
"""
import json
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

DATA = Path(__file__).parent / "data"
st.set_page_config(page_title="Dépendance automobile contrainte", page_icon="🚗", layout="wide")


# ---------------------------------------------------------------- chargement
@st.cache_data
def load():
    gj = json.load(open(DATA / "communes.geojson", encoding="utf-8"))
    meta = json.load(open(DATA / "meta.json", encoding="utf-8")) if (DATA / "meta.json").exists() else {}
    rows, polys = [], []
    for feat in gj["features"]:
        p = feat["properties"]
        rows.append(p)
        geom = feat["geometry"]
        parts = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for poly in parts:
            polys.append({"code": p["code"], "contour": poly[0]})
    com = pd.DataFrame(rows)
    shapes = pd.DataFrame(polys)
    flux = pd.read_csv(DATA / "flux.csv", dtype={"orig": str, "dest": str})
    car = pd.read_csv(DATA / "carreaux.csv") if (DATA / "carreaux.csv").exists() else None
    return com, shapes, flux, car, meta


if not (DATA / "communes.geojson").exists():
    st.error("Aucune donnée trouvée. Exécutez le notebook Colab puis déposez le contenu du zip "
             "`resultats_XX.zip` dans le dossier `data/` de ce dépôt.")
    st.stop()

com, shapes, flux, car, meta = load()

INDIC = {
    "Indice de priorité (0–100)": ("indice_priorite", 1, ""),
    "Actifs captifs employés ou ouvriers (% des actifs)": ("part_captifs_modestes", 100, " %"),
    "Actifs captifs (% des actifs)": ("part_captifs", 100, " %"),
    "Ménages pauvres (%)": ("taux_pauvrete", 100, " %"),
    "Surcoût carburant de crise par captif (€/an)": ("surcout_moyen_par_captif", 1, " €"),
    "Distance d'un trajet des captifs (km, aller simple)": ("km_route_moyen_captifs", 1, " km"),
    "Navetteurs longue distance (> 80 km)": ("navetteurs_longue_distance", 1, ""),
    "Score moyen d'alternative (0–3, inversé)": ("score_alt_moyen", 1, ""),
}

# ---------------------------------------------------------------- barre latérale
with st.sidebar:
    st.header("Affichage")
    choix = st.selectbox("Indicateur sur la carte", list(INDIC))
    col, mult, unit = INDIC[choix]
    min_actifs = st.slider("Masquer les communes de moins de … actifs", 0, 500, 50, step=10)
    voir_carreaux = st.checkbox("Afficher la pauvreté au carreau de 200 m", value=False)
    st.divider()
    st.caption(f"Département **{meta.get('nom', '')} ({meta.get('departement', '')})** — "
               f"calcul du {meta.get('genere_le', '?')}")

# ---------------------------------------------------------------- chiffres clés
st.title(f"Dépendance automobile contrainte — {meta.get('nom', '')}")
st.caption("Actifs qui vont travailler en voiture sans alternative crédible (transport collectif direct, "
           "vélo / VAE / véli, covoiturage observé). Prototype — ordres de grandeur, pas une liste d'ayants droit.")

tot = flux["actifs"].sum()
voit = flux["actifs_voiture"].sum()
cap = flux.loc[flux["captif"], "actifs_voiture"].sum()
cap_m = flux.loc[flux["captif"], "actifs_voiture_modestes"].sum()
surcout = (flux.loc[flux["captif"], "surcout_crise_an_par_actif"] * flux.loc[flux["captif"], "actifs_voiture"]).sum()
k = st.columns(5)
k[0].metric("Actifs résidents", f"{tot:,.0f}".replace(",", " "))
k[1].metric("Vont travailler en voiture", f"{voit/tot:.0%}")
k[2].metric("Automobilistes captifs", f"{cap:,.0f}".replace(",", " "), f"{cap/voit:.0%} des automobilistes",
            delta_color="off")
k[3].metric("dont employés ou ouvriers", f"{cap_m:,.0f}".replace(",", " "))
k[4].metric("Surcoût carburant de crise", f"{surcout/1e6:,.1f} M€/an".replace(".", ","))

# ---------------------------------------------------------------- carte
d = com.copy()
d["valeur"] = d[col] * mult
if col == "score_alt_moyen":           # plus le score est faible, plus c'est grave
    d["valeur_coul"] = 3 - d["valeur"]
else:
    d["valeur_coul"] = d["valeur"]
d.loc[d["actifs"].fillna(0) < min_actifs, "valeur_coul"] = None
lo, hi = d["valeur_coul"].quantile(0.02), d["valeur_coul"].quantile(0.98)

RAMP = [(255, 247, 214), (254, 217, 118), (253, 141, 60), (227, 26, 28), (128, 0, 38)]


def couleur(v):
    if pd.isna(v) or hi == lo:
        return [220, 220, 220, 90]
    t = min(max((v - lo) / (hi - lo), 0), 1) * (len(RAMP) - 1)
    i = min(int(t), len(RAMP) - 2); f = t - i
    c = [round(RAMP[i][j] + (RAMP[i + 1][j] - RAMP[i][j]) * f) for j in range(3)]
    return c + [190]


d["fill"] = d["valeur_coul"].apply(couleur)
d["valeur_txt"] = d["valeur"].map(lambda v: "n.d." if pd.isna(v) else f"{v:,.1f}{unit}".replace(",", " "))
for c, m in [("part_captifs", 100), ("part_captifs_modestes", 100), ("taux_pauvrete", 100)]:
    d[c + "_txt"] = (d[c] * m).map(lambda v: "n.d." if pd.isna(v) else f"{v:.1f} %")
d["actifs_txt"] = d["actifs"].map(lambda v: "n.d." if pd.isna(v) else f"{v:,.0f}".replace(",", " "))
poly = shapes.merge(d, on="code", how="left")

layers = [pdk.Layer("PolygonLayer", poly, get_polygon="contour", get_fill_color="fill",
                    get_line_color=[90, 90, 90, 120], line_width_min_pixels=0.5, pickable=True,
                    auto_highlight=True)]
if voir_carreaux and car is not None:
    cc = car.dropna(subset=["taux_pauvrete"]).copy()
    cc["r"] = (cc["taux_pauvrete"].clip(0, 0.5) / 0.5 * 255).round()
    layers.append(pdk.Layer("ScatterplotLayer", cc, get_position=["lon", "lat"], get_radius=90,
                            get_fill_color="[30, 60, 160, r]", pickable=False))

centre = [float(car["lon"].mean()), float(car["lat"].mean())] if car is not None else [2.5, 46.5]
st.pydeck_chart(pdk.Deck(
    layers=layers, map_style=None,
    initial_view_state=pdk.ViewState(longitude=centre[0], latitude=centre[1], zoom=8.3),
    tooltip={"html": "<b>{nom}</b><br/>" + choix + " : <b>{valeur_txt}</b><br/>"
                     "Actifs : {actifs_txt}<br/>Captifs : {part_captifs_txt}<br/>"
                     "Captifs employés/ouvriers : {part_captifs_modestes_txt}<br/>"
                     "Ménages pauvres : {taux_pauvrete_txt}",
             "style": {"fontSize": "13px"}}), height=560)
st.caption(f"Couleur : du clair (faible) au rouge foncé (élevé). Communes de moins de {min_actifs} actifs en gris.")

# ---------------------------------------------------------------- tableaux
g, dr = st.columns([1, 1])
with g:
    st.subheader("Communes prioritaires")
    t = com[com["actifs"].fillna(0) >= min_actifs].sort_values("indice_priorite", ascending=False).head(20)
    st.dataframe(pd.DataFrame({
        "Commune": t["nom"],
        "Actifs": t["actifs"].round(0),
        "Captifs": t["captifs"].round(0),
        "dont empl./ouvr.": t["captifs_modestes"].round(0),
        "% ménages pauvres": (t["taux_pauvrete"] * 100).round(1),
        "km / trajet (aller)": t["km_route_moyen_captifs"].round(0),
        "Indice": t["indice_priorite"],
    }), hide_index=True, width="stretch")

with dr:
    st.subheader("Zoom sur une commune")
    noms = com.sort_values("indice_priorite", ascending=False)
    sel = st.selectbox("Commune de résidence", noms["nom"] + " (" + noms["code"] + ")")
    code = sel[-6:-1]
    fc = flux[(flux["orig"] == code) & (flux["actifs_voiture"] > 0)].sort_values("actifs_voiture", ascending=False)
    if fc.empty:
        st.info("Pas d'automobilistes recensés pour cette commune.")
    else:
        v, cpt = fc["actifs_voiture"].sum(), fc.loc[fc["captif"], "actifs_voiture"].sum()
        st.markdown(f"**{cpt/v:.0%}** de ses {v:,.0f} automobilistes n'ont pas d'alternative crédible."
                    .replace(",", " "))
        lib = {"tc": "car / train", "velo": "vélo / VAE / véli", "covoit": "covoiturage", "aucune": "aucune"}
        st.dataframe(pd.DataFrame({
            "Lieu de travail": fc["dest_nom"].fillna(fc["dest"]),
            "Automobilistes": fc["actifs_voiture"].round(0),
            "km (aller)": fc["km_route"].round(0),
            "Cars/trains matin": fc["tc_departs_matin"].astype(int),
            "Score (0–3)": fc["score_alternative"],
            "Meilleure alternative": fc["alternative_principale"].map(lib),
            "Captif": [("longue distance" if ld else ("oui" if c else "non")) for c, ld in
                       zip(fc["captif"], fc.get("longue_distance", pd.Series(False, index=fc.index)))],
        }).head(25), hide_index=True, width="stretch")

# ---------------------------------------------------------------- méthode
with st.expander("Méthode, sources et limites"):
    p = meta.get("params", {})
    st.markdown(f"""
**Sources** : {", ".join(meta.get("sources", []))}.
Réseaux de transport utilisés : {len(meta.get("gtfs", []))} fichiers GTFS ; covoiturage : {meta.get("mois_covoiturage", 0)} mois.

**Score d'alternative (0–3) par couple commune de résidence → commune de travail**, meilleur des trois modes :
- *Transport collectif* : liaison **directe** arrivant entre {p.get("fenetre_matin", ["6h", "9h30"])[0]} et {p.get("fenetre_matin", ["", "9h30"])[1]}
  avec un retour entre {p.get("fenetre_soir", ["16h", ""])[0]} et {p.get("fenetre_soir", ["", "20h"])[1]}.
  3 = ≥ 3 départs et temps ≤ 1,3 × voiture ; 2 = ≥ 2 départs et ≤ 1,8 × ; 1 = aller-retour possible et ≤ 3 ×.
- *Vélo / VAE / véli* : 3 si ≤ {p.get("velo_km_3", 3)} km, 2 si ≤ {p.get("velo_km_2", 8)} km, 1 si ≤ {p.get("velo_km_1", 20)} km.
- *Covoiturage* : 2 si ≥ {p.get("covoit_2", 60)} trajets/mois observés dans le registre, 1 si ≥ {p.get("covoit_1", 10)}.

Un automobiliste est **captif** si ce score vaut 0 ou 1 et que son trajet fait au plus {p.get("km_max_quotidien", 80)} km. Au-delà, c'est un **navetteur longue distance** (lieu de travail déclaré lointain : télétravail, logement sur place la semaine…), compté à part et exclu des captifs et du surcoût. Les distances sont des **km par trajet, aller simple**. **Employés ou ouvriers** : catégorie socioprofessionnelle
du recensement (CS 5 et 6), utilisée comme indicateur de revenus modestes.
**Indice de priorité** = 50 % rang du taux de captifs employés/ouvriers + 30 % rang du taux de pauvreté + 20 % rang de la distance des captifs.
**Surcoût de crise** = km × 2 × {p.get("jours_travailles", 220)} jours × {p.get("conso_l_100", 6.5)} L/100 × ({p.get("prix_crise", 2.37)} − {p.get("prix_reference", 1.7)} €/L).

**Limites connues du prototype**
- Pas de correspondances en transport collectif (trajets directs seulement) : l'offre est sous-estimée là où il faut changer.
- Arrêts rattachés à la commune dont le centre est le plus proche ; distances estimées à vol d'oiseau × 1,3.
- Vélo évalué sur la seule distance (pas encore la sécurité de l'itinéraire, prochaine étape : Base nationale des aménagements cyclables).
- Le registre de covoiturage ne couvre que les trajets passés par des plateformes.
- Le recensement 2022 et les revenus 2021 précèdent la crise ; l'indicateur décrit une structure, pas une situation individuelle.
""")
