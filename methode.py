# -*- coding: utf-8 -*-
"""Page « Comprendre les chiffres » : méthode détaillée, avec exemples calculés sur les données."""
import numpy as np
import pandas as pd
import streamlit as st

from donnees import load, nb

com, shapes, flux, car, meta = load()
p = meta.get("params", {})
KM_MAX = p.get("km_max_quotidien", 80)
SMAX = p.get("score_captif_max", 1)
JOURS, CONSO = p.get("jours_travailles", 220), p.get("conso_l_100", 6.5)
PRIX_C, PRIX_R = p.get("prix_crise", 2.37), p.get("prix_reference", 1.70)
DETOUR, VIT = p.get("detour_route", 1.3), p.get("vitesse_voiture_kmh", 55)
PEN = p.get("penalite_acces_tc_min", 10)
FM, FS = p.get("fenetre_matin", ["06:00", "09:30"]), p.get("fenetre_soir", ["16:00", "20:00"])
V3, V2, V1 = p.get("velo_km_3", 3), p.get("velo_km_2", 8), p.get("velo_km_1", 20)
C2, C1 = p.get("covoit_2", 60), p.get("covoit_1", 10)

v = flux[flux["actifs_voiture"] > 0].copy()
if "longue_distance" not in v:
    v["longue_distance"] = v["km_route"] > KM_MAX
V = v["actifs_voiture"].sum()
CAP = v.loc[v["captif"], "actifs_voiture"].sum()
LD = v.loc[v["longue_distance"], "actifs_voiture"].sum()
dep_nom = f"{meta.get('nom', '')} ({meta.get('departement', '')})"


def moy(x, col="km_route"):
    w = x["actifs_voiture"]
    return np.average(x[col], weights=w) if w.sum() > 0 else np.nan


def mediane(x, col="km_route"):
    x = x.sort_values(col)
    if x["actifs_voiture"].sum() == 0:
        return np.nan
    return x.loc[x["actifs_voiture"].cumsum() >= x["actifs_voiture"].sum() / 2, col].iloc[0]


# commune d'exemple par défaut : celle où les longues distances faussaient le plus la moyenne
ecarts = []
for code, x in v[v["score_alternative"] <= SMAX].groupby("orig"):
    if x["actifs_voiture"].sum() < 50:
        continue
    ecarts.append((moy(x) - moy(x[~x["longue_distance"]]), code))
code_defaut = max(ecarts)[1] if ecarts else com.sort_values("actifs", ascending=False)["code"].iloc[0]
liste = com[com["actifs"].fillna(0) >= 50].sort_values("nom")
options = list(liste["code"])
noms = dict(zip(com["code"], com["nom"]))

# ======================================================================
st.title("Comprendre les chiffres")
st.markdown(f"""
Cette page explique, pas à pas, comment chaque chiffre de la carte est calculé pour **{dep_nom}**.
Les exemples sont calculés en direct sur les données affichées.
""")
code_ex = st.selectbox("Commune utilisée pour les exemples", options,
                       index=options.index(code_defaut) if code_defaut in options else 0,
                       format_func=lambda c: noms.get(c, c))
nom_ex = noms.get(code_ex, code_ex)
fx = v[v["orig"] == code_ex]

st.info(f"""**En une phrase** : pour chaque actif qui va travailler en voiture, on regarde s'il existe une autre façon
crédible de faire son trajet domicile-travail (car ou train, vélo, covoiturage). S'il n'y en a pas, il est **captif**.
On compte ensuite les captifs commune par commune, et on les croise avec les revenus.""")

# ----------------------------------------------------------------------
st.header("1. Les données utilisées")
st.markdown(f"""
| Source | Ce qu'on en tire | Millésime |
|---|---|---|
| Insee, recensement : fichier détail « mobilités professionnelles » | commune de résidence, commune de travail, mode de transport, catégorie sociale | 2022 |
| Insee, Filosofi : revenus au carreau de 200 m | nombre de ménages, ménages pauvres, niveau de vie | 2021 |
| transport.data.gouv.fr : horaires GTFS | cars et trains entre communes, un jour de semaine type | à la date du calcul |
| Registre de preuve de covoiturage | trajets covoiturés réellement enregistrés par les plateformes | {meta.get("mois_covoiturage", 0)} mois récents |
| geo.api.gouv.fr | contours, centres et superficies des communes | à la date du calcul |

Réseaux de transport pris en compte : {len(meta.get("gtfs", []))} fichiers GTFS.
""")
with st.expander("Voir la liste des réseaux de transport utilisés"):
    st.write(meta.get("gtfs", []))

# ----------------------------------------------------------------------
st.header("2. Qui est compté")
st.markdown(f"""
- **Actifs** : personnes de 15 ans ou plus ayant un emploi et habitant le département.
- **Automobilistes** : actifs dont le mode de transport *principal* pour aller travailler est « voiture, camion,
  fourgonnette », d'après leur réponse au recensement. Ici : **{nb(V)}** automobilistes sur {nb(flux["actifs"].sum())} actifs
  ({V / flux["actifs"].sum():.0%}).
- **Pondération** : le recensement n'enregistre pas le lieu de travail de tout le monde mais d'un échantillon. Chaque
  réponse représente donc plusieurs personnes : le plus souvent **environ 5**. C'est pourquoi on voit des nombres comme
  « 5,1 personnes » vers une commune : c'est une seule réponse. Une ligne isolée ne doit jamais être lue comme une
  certitude ; seuls les totaux sur plusieurs dizaines de personnes sont solides.
""")

# ----------------------------------------------------------------------
st.header("3. Les distances")
intra = fx[fx["orig"] == fx["dest"]]
st.markdown(f"""
Toutes les distances sont des **kilomètres par trajet, aller simple**, du domicile au lieu de travail.
Pour passer à la journée : × 2. Pour l'année : × 2 × {JOURS} jours travaillés.

Elles sont **estimées, pas mesurées** :
- entre deux communes : distance à vol d'oiseau entre leurs centres × **{DETOUR}** (pour tenir compte des routes) ;
- pour ceux qui travaillent **dans leur propre commune** : 0,4 × √(superficie de la commune), soit la distance moyenne
  entre deux points d'un territoire de cette taille.

Le temps en voiture est déduit de la distance avec une vitesse moyenne de **{VIT} km/h**, plus 3 minutes.
""")
if len(intra):
    st.caption(f"Exemple — {nom_ex} : un trajet interne à la commune est estimé à {nb(intra['km_route'].iloc[0], 1)} km.")

# ----------------------------------------------------------------------
st.header("4. La note d'alternative d'un trajet (0 à 3)")
st.markdown(f"""
Pour chaque trajet (commune de résidence → commune de travail), on note de 0 à 3 trois façons de le faire sans
voiture, et on garde **la meilleure note**.

| Note | Car ou train direct | Vélo, VAE, véli | Covoiturage observé |
|---|---|---|---|
| **3** | au moins 3 départs le matin, un retour le soir, pas plus de 1,3 × le temps en voiture | {V3} km ou moins | — |
| **2** | au moins 2 départs, pas plus de 1,8 × le temps en voiture | {V2} km ou moins | au moins {C2} trajets par mois |
| **1** | au moins un aller-retour possible, pas plus de 3 × le temps en voiture | {V1} km ou moins (VAE ou véli) | au moins {C1} trajets par mois |
| **0** | rien d'utilisable | plus de {V1} km | presque rien |

**0** = aucune alternative · **1** = alternative théorique, peu praticable · **2** = alternative crédible ·
**3** = alternative facile.

**Détails du transport collectif**
- On choisit dans les horaires un mardi ou un jeudi type, le plus chargé de la période.
- Un aller compte s'il **arrive** entre {FM[0]} et {FM[1]} ; un retour compte s'il **part** entre {FS[0]} et {FS[1]}.
- Seules les liaisons **directes** sont comptées (pas de correspondance).
- Au temps à bord, on ajoute **{PEN} minutes** pour rejoindre l'arrêt et attendre.
- Un arrêt est rattaché à la commune dont le centre est le plus proche (à 3 km au plus).

**Covoiturage** : la note est plafonnée à 2, car le registre ne voit que les trajets passés par des plateformes
partenaires ; le covoiturage informel (collègues, voisins) n'y figure pas.
""")
if len(fx):
    autres = fx[fx["dest"] != fx["orig"]]
    ex = (autres if len(autres) else fx).sort_values("actifs_voiture", ascending=False).iloc[0]
    st.caption(
        f"Exemple — trajet {nom_ex} → {ex['dest_nom']} ({nb(ex['actifs_voiture'])} automobilistes, "
        f"{nb(ex['km_route'], 1)} km) : car/train {int(ex['score_tc'])}, vélo {int(ex['score_velo'])}, "
        f"covoiturage {int(ex['score_covoit'])} → note retenue **{int(ex['score_alternative'])}**.")

# ----------------------------------------------------------------------
st.header("5. Les automobilistes captifs")
rep = v.groupby("score_alternative")["actifs_voiture"].sum() / V
st.markdown(f"""
Un automobiliste est **captif** si :
1. la note d'alternative de son trajet vaut **0 ou 1**,
2. **et** son trajet fait au plus **{KM_MAX} km** (voir section 6).

Dans {dep_nom} : **{nb(CAP)}** captifs sur {nb(V)} automobilistes, soit **{CAP / V:.0%} des automobilistes**.
C'est le chiffre affiché sur la carte sous « Automobilistes captifs ».
""")
st.table(pd.DataFrame({
    "Note du trajet": ["0 — aucune alternative", "1 — alternative théorique", "2 — alternative crédible",
                       "3 — alternative facile"],
    "Part des automobilistes": [f"{rep.get(i, 0):.0%}" for i in range(4)],
}))
st.markdown(f"""
Les notes 0 et 1 font {rep.get(0, 0) + rep.get(1, 0):.0%} ; on arrive à {CAP / V:.0%} parce qu'on retire les
navetteurs longue distance ({LD / V:.1%} des automobilistes), qui ont presque tous la note 0 mais ne font pas ce
trajet chaque jour.

À noter : la note 3 ne vient presque jamais du car ou du train ; elle correspond surtout à des gens qui travaillent
dans leur commune, à quelques kilomètres.
""")

# ----------------------------------------------------------------------
st.header(f"6. Les navetteurs longue distance (plus de {KM_MAX} km)")
st.markdown(f"""
Le recensement enregistre le lieu de travail **déclaré**, même très lointain : Paris, Bordeaux, voire l'outre-mer.
Ces personnes ne font évidemment pas l'aller-retour en voiture chaque jour : télétravail, logement sur place en
semaine, ou adresse du siège de l'employeur.

Les compter comme captifs fausse tout : une seule réponse à 600 km, pesant 5 personnes, suffit à faire exploser la
distance moyenne d'une petite commune et à gonfler le surcoût carburant. Au-delà de **{KM_MAX} km par trajet**, ces
actifs sont donc **comptés à part** (indicateur « Navetteurs longue distance ») et **exclus** des captifs, de la
distance moyenne et du surcoût. Dans {dep_nom}, ils sont **{nb(LD)}**.
""")
fc = fx[fx["score_alternative"] <= SMAX]
if len(fc):
    st.markdown(f"**Exemple — {nom_ex}**")
    loin = fc[fc["longue_distance"]].sort_values("km_route", ascending=False)
    a, b = st.columns(2)
    a.metric("Distance moyenne, longues distances incluses", f"{nb(moy(fc))} km")
    b.metric(f"Distance moyenne, sans les plus de {KM_MAX} km", f"{nb(moy(fc[~fc['longue_distance']]))} km")
    st.markdown(f"""
La **médiane** (la distance qui partage les automobilistes en deux moitiés) n'est pas sensible aux cas extrêmes :
même en gardant les longues distances, elle vaut **{nb(mediane(fc))} km**. Elle confirme que la moyenne corrigée
décrit bien la commune.
""")
    if len(loin):
        st.dataframe(pd.DataFrame({"Lieu de travail déclaré": loin["dest_nom"],
                                   "Personnes": loin["actifs_voiture"].round(1),
                                   "km par trajet": loin["km_route"].round(0)}),
                     hide_index=True, width="stretch")

st.markdown("**Le résultat dépend-il du seuil choisi ?** Le calcul refait avec d'autres seuils :")
lignes = []
for K, lib in [(50, "50 km"), (60, "60 km"), (80, "80 km"), (100, "100 km"), (150, "150 km"), (None, "aucun seuil")]:
    c = v[(v["score_alternative"] <= SMAX) & ((v["km_route"] <= K) if K else True)]
    sur = (c["km_route"] * 2 * JOURS * CONSO / 100 * (PRIX_C - PRIX_R) * c["actifs_voiture"]).sum()
    lignes.append({"Seuil": lib + (" (retenu)" if K == KM_MAX else ""), "Captifs": nb(c["actifs_voiture"].sum()),
                   "Distance moyenne par trajet": f"{nb(moy(c), 1)} km", "Surcoût de crise": f"{nb(sur / 1e6, 1)} M€"})
st.table(pd.DataFrame(lignes))
st.caption("Entre 50 et 150 km, les résultats bougent peu : ce qui faussait les chiffres, ce n'était pas le choix du "
           "seuil mais une poignée de lieux de travail à des centaines ou des milliers de kilomètres.")

# ----------------------------------------------------------------------
st.header("7. Le score moyen d'alternative d'une commune")
st.markdown("""
C'est la moyenne des notes (0 à 3) des trajets de tous les automobilistes de la commune, chaque trajet pesant le
nombre de personnes qui le font.
""")
if len(fx):
    r = fx.groupby("score_alternative")["actifs_voiture"].sum()
    st.markdown(f"**Exemple — {nom_ex}** : " + " ; ".join(
        f"{nb(r.get(i, 0))} automobilistes ont un trajet noté {i}" for i in range(4) if r.get(i, 0) > 0)
        + f". Moyenne : **{nb(moy(fx, 'score_alternative'), 2)}**.")
st.markdown(f"""
Médiane des communes de {dep_nom} : **{nb(com["score_alt_moyen"].median(), 2)}**.

Sur la carte, cet indicateur est **inversé** : plus le score est bas, plus la couleur est foncée, pour que le
rouge foncé signale toujours le problème.
""")

# ----------------------------------------------------------------------
st.header("8. Les captifs « employés ou ouvriers »")
st.markdown("""
Le recensement ne donne pas le revenu des personnes, mais leur **catégorie socioprofessionnelle**. On utilise les
**employés** et les **ouvriers** comme indicateur de revenus modestes (variable « groupe socioprofessionnel », codes 5
et 6). Cet indicateur est individuel : il porte sur la personne elle-même, pas sur son quartier. Il inclut notamment
les aides-soignantes, aides à domicile, agents d'entretien, caristes, vendeurs…

« Part des captifs employés ou ouvriers » = captifs employés ou ouvriers ÷ **tous les actifs** de la commune.
""")

# ----------------------------------------------------------------------
st.header("9. La pauvreté (Filosofi)")
st.markdown("""
- **Ménages pauvres** : ménages dont le niveau de vie est inférieur au seuil de pauvreté (60 % du niveau de vie
  médian national), d'après les déclarations fiscales et les prestations sociales de 2021.
- L'Insee publie ces données par **carreaux de 200 m**. Chaque carreau est rattaché à la commune dans laquelle se
  trouve son centre, puis on fait la somme par commune : taux de pauvreté = ménages pauvres ÷ ménages.
- Dans les carreaux de moins de 11 ménages, l'Insee publie des valeurs **approchées** pour protéger le secret
  statistique. Dans les communes très rurales, le taux est donc moins précis.
- L'option « Afficher la pauvreté au carreau de 200 m » montre ces carreaux sur la carte : plus le point est foncé,
  plus la part de ménages pauvres est élevée.
""")

# ----------------------------------------------------------------------
st.header("10. L'indice de priorité (0 à 100)")
st.markdown("""
Il combine trois critères, chacun transformé en **rang** (0 = la commune la moins concernée du département,
100 = la plus concernée) :

| Critère | Poids |
|---|---|
| Part des actifs captifs employés ou ouvriers | 50 % |
| Taux de ménages pauvres | 30 % |
| Distance moyenne d'un trajet des captifs | 20 % |

Un indice de 90 veut dire que la commune est, sur ces critères combinés, plus exposée que 90 % des communes du
département. C'est un **classement relatif**, pas une mesure absolue : il sert à choisir où agir en premier, pas à
comparer deux départements. Les poids sont un choix ; ils se modifient dans le notebook.
""")
row = com[com["code"] == code_ex]
if len(row):
    r0 = row.iloc[0]
    st.caption(f"Exemple — {nom_ex} : {nb(100 * (r0['part_captifs_modestes'] or 0), 1)} % d'actifs captifs employés ou "
               f"ouvriers, {nb(100 * (r0['taux_pauvrete'] or 0), 1)} % de ménages pauvres, "
               f"{nb(r0['km_route_moyen_captifs'])} km par trajet → indice **{nb(r0['indice_priorite'], 1)}**.")

# ----------------------------------------------------------------------
st.header("11. Le surcoût carburant de crise")
st.markdown(f"""
Pour chaque captif : **km par trajet × 2 × {JOURS} jours × {CONSO} L/100 km × ({PRIX_C} − {PRIX_R} €/L)**,
c'est-à-dire le supplément payé sur un an au prix de crise du gazole, par rapport au prix d'avant crise.

Exemple : un trajet de 25 km coûte {nb(25 * 2 * JOURS * CONSO / 100 * (PRIX_C - PRIX_R))} € de plus par an.

Il n'est calculé que pour les captifs (pas pour les navetteurs longue distance), sur la base d'une voiture moyenne.
Dans {dep_nom} : **{nb(com["surcout_crise_total"].sum() / 1e6, 1)} M€ par an**.
""")

# ----------------------------------------------------------------------
st.header("12. Bien lire la carte")
st.markdown("""
- **Nombre ou part ?** Les indicateurs en **%** permettent de comparer les communes entre elles. Les indicateurs en
  **nombre de personnes** (navetteurs longue distance) font toujours ressortir les grandes communes, même à
  proportion égale.
- **Petites communes** : avec quelques réponses au recensement, les chiffres sont instables (une seule réponse peut
  faire basculer un taux). Le curseur « Masquer les communes de moins de … actifs » permet de les écarter.
- **Couleurs** : du clair (faible) au rouge foncé (élevé) ; les valeurs extrêmes (2 % de chaque côté) sont ramenées
  aux bornes pour garder une échelle lisible.
""")

# ----------------------------------------------------------------------
st.header("13. Ce que ces chiffres ne disent pas")
st.markdown("""
- **Ce sont des ordres de grandeur.** Ils servent à comparer les communes et à chiffrer un enjeu, pas à dire
  « telle personne est captive ».
- **Le transport collectif est sous-estimé** là où une correspondance existe, puisque seules les liaisons directes
  sont comptées.
- **Le vélo est évalué sur la distance seule**, sans tenir compte de la sécurité de l'itinéraire ni du relief.
- **Les distances sont estimées** à partir des centres des communes, pas mesurées sur la route.
- **Les données précèdent la crise** : recensement 2022, revenus 2021, horaires actuels.
- **Le covoiturage informel n'est pas vu**, seul celui des plateformes l'est.
""")
st.caption(f"Calcul du {meta.get('genere_le', '?')} — sources : " + ", ".join(meta.get("sources", [])))
