# Carte de la dépendance automobile contrainte — prototype

Pour chaque commune d'un département : combien d'actifs vont travailler en voiture **sans alternative crédible** (car ou train direct, vélo / VAE / véli, covoiturage observé), combien sont employés ou ouvriers, et quel est le taux de pauvreté local.

Tout se fait dans le navigateur, sans rien installer sur votre ordinateur.

## Étape 1 — Calculer les données (Google Colab)

1. Ouvrez le notebook directement dans Colab : [![Ouvrir dans Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GabrielPlassat/carte-dependance-auto/blob/main/notebook/carte_dependance_auto.ipynb)
   (si le dépôt est privé : dans Colab, **Fichier → Ouvrir un notebook → GitHub**, cochez « Inclure les dépôts privés », puis choisissez `notebook/carte_dependance_auto.ipynb`).
2. Dans la cellule **Paramètres**, mettez le code du département (`DEP = "24"` par défaut).
3. Menu **Exécution → Tout exécuter**. Comptez 5 à 15 minutes.
4. À la fin, la carte s'affiche dans le notebook et un fichier `resultats_24.zip` se télécharge.

Si un réseau de transport manque, copiez son lien GTFS depuis transport.data.gouv.fr dans `GTFS_URLS_EN_PLUS` et relancez.

## Étape 2 — Publier l'app (GitHub + Streamlit)

1. Dézippez `resultats_24.zip` et déposez `communes.geojson`, `flux.csv`, `carreaux.csv` et `meta.json` dans `data/` (bouton **Add file → Upload files** de GitHub).
2. Sur [share.streamlit.io](https://share.streamlit.io), **New app**, choisissez le dépôt `carte-dependance-auto`, la branche `main` et le fichier `app.py`.

Pour un autre département : relancez le notebook avec un autre `DEP` et remplacez les 4 fichiers de `data/`.

## Contenu du dépôt

| Fichier | Rôle |
|---|---|
| `notebook/carte_dependance_auto.ipynb` | calcul complet, à exécuter dans Colab |
| `app.py` | app Streamlit qui affiche les résultats |
| `requirements.txt` | bibliothèques de l'app |
| `data/` | résultats du notebook (4 fichiers à déposer) |

## Méthode en bref

| Mode | 3 | 2 | 1 | 0 |
|---|---|---|---|---|
| Car / train **direct** (aller 6h–9h30, retour 16h–20h) | ≥ 3 départs, ≤ 1,3 × temps voiture | ≥ 2 départs, ≤ 1,8 × | un aller-retour possible, ≤ 3 × | rien |
| Vélo / VAE / véli | ≤ 3 km | ≤ 8 km | ≤ 20 km | > 20 km |
| Covoiturage (registre de preuve) | — | ≥ 60 trajets/mois | ≥ 10 trajets/mois | moins |

Le score d'un trajet est le meilleur des trois. **Captif** = score 0 ou 1.
**Indice de priorité (0–100)** = 50 % rang du taux de captifs employés/ouvriers + 30 % rang du taux de pauvreté + 20 % rang de la distance des captifs. Les pondérations et tous les seuils se modifient dans la cellule Paramètres du notebook.

## Sources

- Insee, Recensement 2022 — fichier détail Mobilités professionnelles (MOBPRO)
- Insee, Filosofi 2021 — données carroyées 200 m
- transport.data.gouv.fr — horaires GTFS des réseaux
- Registre de preuve de covoiturage (data.gouv.fr)
- geo.api.gouv.fr — communes

## Limites du prototype

- Trajets directs seulement en transport collectif (pas de correspondances).
- Vélo évalué sur la distance seule ; prochaine étape : sécurité de l'itinéraire avec la Base nationale des aménagements cyclables.
- Le covoiturage observé ne couvre que les plateformes connectées au registre.
- Recensement 2022 et revenus 2021 : l'indicateur décrit une structure territoriale, pas des situations individuelles.
