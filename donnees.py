# -*- coding: utf-8 -*-
"""Chargement des données partagé par les pages de l'app."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "data"


# ---------------------------------------------------------------- chargement
def load():
    if not (DATA / "communes.geojson").exists():
        st.error("Aucune donnée trouvée. Exécutez le notebook Colab puis déposez le contenu du zip "
                 "`resultats_XX.zip` dans le dossier `data/` de ce dépôt.")
        st.stop()
    return _load()


@st.cache_data
def _load():
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





def nb(x, dec=0):
    """Nombre au format français : 62 240 ; 0,93."""
    if pd.isna(x):
        return "n.d."
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")
