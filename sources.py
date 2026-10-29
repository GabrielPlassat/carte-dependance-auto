# -*- coding: utf-8 -*-
"""Page « Données sources » : provenance, contenu et usage de chaque jeu de données."""
import pandas as pd
import streamlit as st

from donnees import load, nb

com, shapes, flux, car, meta = load()
dep_nom = f"{meta.get('nom', '')} ({meta.get('departement', '')})"
gtfs = meta.get("gtfs", [])

st.title("Données sources")
st.markdown(f"""
Le calcul n'utilise **que des données publiques et ouvertes**, téléchargées automatiquement par le notebook Colab.
Cette page détaille, pour chacune, d'où elle vient, ce qu'on en garde et à quoi elle sert.
Calcul affiché : **{dep_nom}**, réalisé le {meta.get("genere_le", "?")}.
""")

# ----------------------------------------------------------------------
st.header("Vue d'ensemble")
st.graphviz_chart("""
digraph {
  rankdir=LR; bgcolor="transparent";
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, color="#999999"];
  edge [color="#888888", fontsize=9, fontname="Helvetica"];
  subgraph cluster_src { label="Sources ouvertes"; fontname="Helvetica"; fontsize=12; color="#cccccc";
    mob [label="Insee MOBPRO 2022\\nqui travaille où, avec quel mode", fillcolor="#fde7c8"];
    fil [label="Insee Filosofi 2021\\nrevenus au carreau 200 m", fillcolor="#fde7c8"];
    gtf [label="Horaires GTFS\\ncars et trains", fillcolor="#d7e8f7"];
    rpc [label="Registre de preuve\\nde covoiturage", fillcolor="#d7e8f7"];
    geo [label="geo.api.gouv.fr\\ncommunes", fillcolor="#e3e3e3"];
  }
  flx [label="Trajets domicile-travail\\n(commune → commune)", fillcolor="#ffffff"];
  sco [label="Note d'alternative\\n0 à 3 par trajet", fillcolor="#ffffff"];
  cap [label="Captifs par commune\\nkm, surcoût", fillcolor="#ffffff"];
  ind [label="Indice de priorité\\n0 à 100", fillcolor="#f6c6c6"];
  mob -> flx; geo -> flx [label="distances"];
  flx -> sco; gtf -> sco [label="car / train"]; rpc -> sco [label="covoiturage"];
  sco -> cap; cap -> ind; fil -> ind [label="pauvreté"]; geo -> fil [label="rattachement"];
}
""")

st.table(pd.DataFrame([
    ["Insee — recensement, mobilités professionnelles", "2022", "commune de résidence et de travail, mode, catégorie sociale"],
    ["Insee — Filosofi, carreaux de 200 m", "2021", "ménages pauvres, niveau de vie"],
    ["transport.data.gouv.fr — horaires GTFS", "horaires en cours", "liaisons directes en car et en train"],
    ["Registre de preuve de covoiturage", f"{meta.get('mois_covoiturage', 0)} mois récents", "trajets covoiturés observés"],
    ["geo.api.gouv.fr — découpage communal", "en cours", "contours, centres, superficies"],
], columns=["Source", "Millésime", "Apport principal"]))


def fiche(titre, lien, producteur, licence, fichier, variables, traitement, usage, limites):
    st.subheader(titre)
    a, b = st.columns([1, 2])
    with a:
        st.markdown(f"""
**Producteur** : {producteur}
**Licence** : {licence}
**Fichier** : {fichier}
[Page officielle de la source]({lien})
""")
    with b:
        st.markdown("**Variables utilisées**")
        st.dataframe(pd.DataFrame(variables, columns=["Variable", "Contenu", "Usage dans le calcul"]),
                     hide_index=True, width="stretch")
    st.markdown(f"**Ce que fait le calcul** \n{traitement}")
    st.markdown(f"**Ce que ça alimente** : {usage}")
    st.markdown(f"**Limites** : {limites}")
    st.divider()


st.header("Fiches par source")

# ----------------------------------------------------------------------
fiche(
    "1. Recensement — mobilités professionnelles (MOBPRO)",
    "https://www.insee.fr/fr/statistiques/8589904",
    "Insee", "Licence Ouverte Etalab",
    "fichier détail national RP 2022, format Parquet (66 Mo, 7,4 millions de lignes)",
    [["COMMUNE", "commune de résidence", "garder les habitants du département"],
     ["DCLT", "commune du lieu de travail", "destination du trajet"],
     ["TRANS", "mode de transport principal pour aller travailler", "repérer les automobilistes (« voiture, camion, fourgonnette »)"],
     ["GS (ou CS1)", "groupe socioprofessionnel", "employés (5) et ouvriers (6) = revenus modestes"],
     ["IPONDI", "poids de la réponse", "nombre de personnes que représente chaque réponse"]],
    """- On garde les actifs habitant le département, puis on additionne les poids par couple
« commune de résidence → commune de travail ».
- On en tire, pour chaque couple : nombre d'actifs, d'automobilistes, et d'automobilistes employés ou ouvriers.
- Contrôle automatique : la part des automobilistes est vérifiée ; si le code « voiture » ne correspondait à
presque personne, le mode majoritaire serait retenu avec un avertissement.""",
    f"tous les comptages d'actifs, d'automobilistes et de captifs. Ici : **{nb(flux['actifs'].sum())}** actifs, "
    f"**{nb(len(flux))}** couples de communes.",
    "le lieu de travail n'est enregistré que pour un échantillon : chaque réponse vaut le plus souvent environ "
    "5 personnes. Le lieu de travail est celui déclaré, ce qui explique les quelques destinations très lointaines "
    "(traitées comme navetteurs longue distance). Le mode est le mode *principal* : un actif qui fait une partie du "
    "trajet en car est compté selon le mode qu'il utilise le plus.",
)

# ----------------------------------------------------------------------
fiche(
    "2. Revenus carroyés (Filosofi)",
    "https://www.insee.fr/fr/statistiques/8735162",
    "Insee, à partir des déclarations fiscales et des prestations sociales", "Licence Ouverte Etalab",
    "carreaux de 200 m, France métropolitaine, revenus 2021, format CSV (87 Mo)",
    [["idcar_200m", "identifiant du carreau, qui contient ses coordonnées", "positionner le carreau sur la carte"],
     ["lcog_geo", "commune(s) du carreau", "présélection des carreaux du département"],
     ["men", "nombre de ménages", "dénominateur du taux de pauvreté"],
     ["men_pauv", "nombre de ménages pauvres", "numérateur du taux de pauvreté"],
     ["ind, ind_snv", "nombre d'habitants, somme des niveaux de vie", "niveau de vie moyen"]],
    """- Le centre de chaque carreau est calculé à partir de son identifiant, puis le carreau est rattaché à la
commune dans laquelle tombe ce centre (selon les contours communaux actuels, ce qui évite les problèmes de
communes fusionnées depuis 2021).
- Par commune : taux de pauvreté = somme des ménages pauvres ÷ somme des ménages.""",
    f"le taux de pauvreté (30 % de l'indice de priorité) et la couche « pauvreté au carreau » de la carte. "
    f"Ici : **{nb(len(car)) if car is not None else 'n.d.'}** carreaux habités.",
    "dans les carreaux de moins de 11 ménages, l'Insee publie des valeurs approchées (secret statistique) : le taux "
    "est moins précis dans les communes très rurales. Les revenus datent de 2021.",
)

# ----------------------------------------------------------------------
fiche(
    "3. Horaires des transports collectifs (GTFS)",
    "https://transport.data.gouv.fr",
    "les autorités organisatrices de la mobilité (région, intercommunalités, SNCF pour les TER), "
    "rassemblées par le Point d'accès national transport.data.gouv.fr",
    "propre à chaque réseau (le plus souvent Licence Ouverte ou ODbL), indiquée sur transport.data.gouv.fr",
    f"{len(gtfs)} fichiers GTFS trouvés automatiquement (réseaux couvrant le département, sa région, ses "
    "intercommunalités, et les TER)",
    [["stops", "arrêts et leurs coordonnées", "rattacher chaque arrêt à une commune"],
     ["trips, calendar, calendar_dates", "courses et jours de circulation", "choisir un mardi ou jeudi type"],
     ["stop_times", "heures de passage à chaque arrêt", "trouver les liaisons directes et leur durée"]],
    """- Chaque arrêt est rattaché à la commune dont le centre est le plus proche (3 km au plus).
- On choisit un mardi ou un jeudi type, le plus chargé de la période couverte.
- Pour chaque couple de communes desservi par une même course : nombre d'allers arrivant le matin, meilleur temps
à bord, nombre de retours partant le soir.""",
    "la note « car ou train » de chaque trajet.",
    "seules les liaisons **directes** sont comptées (pas de correspondance) ; le transport à la demande et les "
    "lignes scolaires ouvertes à tous ne sont vus que s'ils figurent dans les GTFS ; un réseau absent de "
    "transport.data.gouv.fr n'est pas pris en compte.",
)
if gtfs:
    with st.expander(f"Les {len(gtfs)} réseaux utilisés"):
        st.write(pd.DataFrame({"Jeu de données": gtfs}))

# ----------------------------------------------------------------------
fiche(
    "4. Registre de preuve de covoiturage",
    "https://www.data.gouv.fr/datasets/trajets-realises-en-covoiturage-registre-de-preuve-de-covoiturage",
    "Registre de preuve de covoiturage (ministère chargé des transports), données des opérateurs partenaires",
    "Licence Ouverte Etalab",
    f"fichiers mensuels CSV des trajets réalisés, anonymisés ({meta.get('mois_covoiturage', 0)} mois utilisés)",
    [["journey_start_insee", "commune de prise en charge du passager", "origine du trajet covoituré"],
     ["journey_end_insee", "commune de dépose", "destination du trajet covoituré"]],
    """- On garde les trajets qui partent du département ou y arrivent.
- On compte les trajets par paire de communes, dans les deux sens, en moyenne par mois.""",
    "la note « covoiturage » de chaque trajet (plafonnée à 2).",
    "seuls les trajets passés par des plateformes partenaires sont enregistrés ; le covoiturage informel (collègues, "
    "voisins) est invisible. La note sous-estime donc le covoiturage réel.",
)

# ----------------------------------------------------------------------
fiche(
    "5. Découpage communal (geo.api.gouv.fr)",
    "https://geo.api.gouv.fr",
    "Etalab, à partir des référentiels de l'Insee et de l'IGN", "Licence Ouverte Etalab",
    "API publique : centres de toutes les communes de France, contours des communes du département",
    [["code, nom", "code officiel et nom de la commune", "faire le lien entre toutes les sources"],
     ["centre", "point central de la commune", "calculer les distances, rattacher les arrêts"],
     ["surface", "superficie", "distance des trajets internes à une commune"],
     ["contour", "limites de la commune", "dessiner la carte, rattacher les carreaux"]],
    """- Distance entre deux communes : vol d'oiseau entre leurs centres × 1,3.
- Trajet interne à une commune : 0,4 × √(superficie).""",
    "toutes les distances, la carte, et le lien entre les sources.",
    "les distances sont des estimations depuis le centre des communes, pas des distances mesurées sur la route ; "
    "pour une grande commune nouvelle, le centre peut être éloigné de certains hameaux.",
)

# ----------------------------------------------------------------------
st.header("Fichiers produits par le notebook")
st.markdown("""
Le notebook Colab produit quatre fichiers, déposés dans le dossier `data/` du dépôt. Ils sont ouverts et réutilisables
(un tableur suffit pour les fichiers CSV).
""")
st.table(pd.DataFrame([
    ["communes.geojson", f"{nb(len(com))} communes",
     "contour + tous les indicateurs par commune (actifs, captifs, pauvreté, indice…)"],
    ["flux.csv", f"{nb(len(flux))} lignes",
     "un trajet commune → commune par ligne : nombre de personnes, km, notes car/vélo/covoiturage, captif ou non"],
    ["carreaux.csv", f"{nb(len(car)) if car is not None else 'n.d.'} lignes",
     "un carreau de 200 m par ligne : position, ménages, taux de pauvreté"],
    ["meta.json", "—", "date du calcul, paramètres utilisés, liste des réseaux de transport"],
], columns=["Fichier", "Taille", "Contenu"]))

st.header("Reproduire le calcul")
st.markdown("""
Tout le calcul est dans le notebook `notebook/carte_dependance_auto.ipynb` du dépôt GitHub. Il suffit de l'ouvrir dans
Google Colab, de choisir le code du département et de lancer **Exécution → Tout exécuter** : les données sont
retéléchargées depuis les sources officielles et le calcul est refait à l'identique. Les hypothèses (seuils,
vitesse, prix du carburant, poids de l'indice) sont regroupées dans la cellule « Paramètres ».
""")
st.page_link("methode.py", label="Comment les chiffres sont calculés : page « Comprendre les chiffres »", icon="📖")
