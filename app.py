# -*- coding: utf-8 -*-
"""
Carte de la dépendance automobile contrainte — app Streamlit.
Lit les fichiers produits par le notebook Colab, déposés dans le dossier data/.
"""
import streamlit as st

st.set_page_config(page_title="Dépendance automobile contrainte", page_icon="🚗", layout="wide")
pg = st.navigation([
    st.Page("carte.py", title="Carte", icon="🗺️", default=True),
    st.Page("methode.py", title="Comprendre les chiffres", icon="📖"),
])
pg.run()
