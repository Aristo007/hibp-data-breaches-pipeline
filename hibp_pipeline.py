"""
Pipeline d'analyse des fuites de données publiques (HIBP)
Semaine 1 : script d'ingestion + premières analyses

Ce script :
1. Récupère la liste des breaches depuis l'API HIBP
2. Les sauvegarde en local (breaches.json)
3. Affiche 3 analyses : plus gros breach, évolution par année, types de données volées
"""

import requests
import json
from collections import Counter

BREACHES_FILE = "breaches.json"


def telecharger_breaches():
    """Va chercher la liste complète des breaches sur l'API HIBP (endpoint public)."""
    url = "https://haveibeenpwned.com/api/v3/breaches"
    headers = {"User-Agent": "Projet-Groupe10-Test"}

    response = requests.get(url, headers=headers)
    response.raise_for_status()  # arrête le script si la requête échoue

    breaches = response.json()
    print(f"[OK] {len(breaches)} breaches téléchargés depuis l'API.")
    return breaches


def sauvegarder(breaches):
    """Sauvegarde la liste des breaches dans un fichier JSON local."""
    with open(BREACHES_FILE, "w", encoding="utf-8") as f:
        json.dump(breaches, f, ensure_ascii=False, indent=2)
    print(f"[OK] Sauvegardé dans {BREACHES_FILE}")


def charger():
    """Recharge les breaches depuis le fichier local (pas besoin de re-télécharger)."""
    with open(BREACHES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def analyse_plus_gros_breach(breaches):
    """Affiche le breach avec le plus de comptes compromis + le total cumulé."""
    plus_gros = max(breaches, key=lambda b: b["PwnCount"])
    total = sum(b["PwnCount"] for b in breaches)

    print("\n--- Plus gros breach ---")
    print("Nom :", plus_gros["Name"])
    print("Comptes touchés :", f"{plus_gros['PwnCount']:,}")
    print("Date :", plus_gros["BreachDate"])
    print("Total cumulé (tous breaches) :", f"{total:,}")


def analyse_par_annee(breaches):
    """Compte le nombre de breaches par année."""
    annees = [b["BreachDate"][:4] for b in breaches]
    compteur = Counter(annees)

    print("\n--- Nombre de breaches par année ---")
    for annee in sorted(compteur):
        print(f"{annee} : {compteur[annee]} breaches")


def analyse_types_donnees(breaches, top_n=15):
    """Compte quels types de données sont les plus souvent volés."""
    compteur = Counter()
    for b in breaches:
        compteur.update(b["DataClasses"])

    print(f"\n--- Top {top_n} des types de données volées ---")
    for type_donnee, nombre in compteur.most_common(top_n):
        print(f"{type_donnee} : {nombre} breaches")


if __name__ == "__main__":
    breaches = telecharger_breaches()
    sauvegarder(breaches)

    # Ou, si le fichier existe déjà et qu'on veut juste ré-analyser sans re-télécharger :
    # breaches = charger()

    analyse_plus_gros_breach(breaches)
    analyse_par_annee(breaches)
    analyse_types_donnees(breaches)