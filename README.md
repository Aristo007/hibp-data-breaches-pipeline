# Pipeline d'analyse des fuites de données publiques — Have I Been Pwned

**Groupe 10 — Projet Master 1**

Pipeline d'ingestion, transformation et analyse des fuites de données publiques (data breaches), construit à partir de l'API [Have I Been Pwned (HIBP)](https://haveibeenpwned.com/API/v3). Le pipeline est orchestré par Apache Airflow (Docker), stocke les données sur AWS S3, et alimente un dashboard Power BI.

## Objectif

Analyser les fuites de données publiques pour dégager des tendances : évolution du nombre de fuites dans le temps, volume de comptes compromis, types de données les plus fréquemment volés, et répartition par secteur d'activité.

## Architecture

```
API HIBP  --->  Airflow (Docker)  --->  AWS S3  --->  Power BI
                 ingestion,             stockage       dashboard
                 transformation,        par date        interactif
                 chargement

                      |
                      v
                   GitHub
              (code versionné)
```

Le DAG Airflow exécute trois tâches séquentielles :
1. **Ingestion** — téléchargement des breaches depuis l'endpoint public `/breaches` de l'API HIBP (aucune clé API requise)
2. **Transformation** — génération de deux fichiers CSV (breaches, types de données volées) prêts pour Power BI
3. **Chargement** — envoi des fichiers CSV vers un bucket S3, organisés par date d'ingestion (`breaches/{date}/`)

Le pipeline inclut une gestion d'erreurs (retries automatiques, timeout, messages d'erreur explicites) et bascule automatiquement en mode simulation si les identifiants AWS ne sont pas configurés.

## Stack technique

| Outil | Rôle |
|---|---|
| Python (`requests`, `boto3`) | Ingestion API et envoi S3 |
| Apache Airflow (via Docker Compose) | Orchestration du pipeline |
| AWS S3 | Stockage des données, organisées par date |
| Power BI Desktop | Dashboard et visualisations |
| GitHub | Versionnement du code |

## Structure du dépôt

```
.
├── src/
│   └── hibp_pipeline.py       # Script d'ingestion et d'analyse en local (hors Airflow)
├── dags/
│   └── hibp_dag.py            # DAG Airflow (3 tâches)
├── config/
│   ├── docker-compose.yaml    # Configuration Airflow (officielle Apache)
│   └── .env.example           # Modèle de variables d'environnement (AWS, etc.)
├── powerbi/
│   └── Groupe10.pbix          # Dashboard Power BI
├── reports/
│   ├── rapport_groupe10.docx      # Rapport de projet détaillé
│   └── soutenance_groupe10.pptx   # Support de présentation
├── export_breaches.csv        # Export de données pour Power BI
├── export_dataclasses.csv     # Export de données pour Power BI
├── architecture_pipeline_hibp.png
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation et exécution

### Prérequis

- Python 3.10+
- Docker Desktop
- Un compte AWS avec un bucket S3 et des identifiants IAM (Access Key + Secret Key)
- Power BI Desktop (Windows)

### 1. Cloner le dépôt

```bash
git clone https://github.com/Aristo007/hibp-data-breaches-pipeline.git
cd hibp-data-breaches-pipeline
```

### 2. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

### 3. Configurer les variables d'environnement

Copie `config/.env.example` vers un fichier `.env` à la racine du projet (non versionné) et renseigne tes propres identifiants :

```
AIRFLOW_UID=50000
_PIP_ADDITIONAL_REQUIREMENTS=boto3
AWS_ACCESS_KEY_ID=ta_clé_d_accès
AWS_SECRET_ACCESS_KEY=ta_clé_secrète
S3_BUCKET_NAME=nom_du_bucket
AWS_REGION=eu-north-1
```

> Si ces variables AWS ne sont pas définies, la tâche de chargement bascule automatiquement en mode simulation (aucune erreur, juste un message dans les logs).

### 4. Lancer Airflow

Le fichier `docker-compose.yaml` se trouve dans `config/` — lance les commandes depuis la racine du projet en le référençant :

```bash
docker compose -f config/docker-compose.yaml up airflow-init
docker compose -f config/docker-compose.yaml up -d
```

L'interface est accessible sur [http://localhost:8080](http://localhost:8080) (identifiants par défaut : `airflow` / `airflow`).

### 5. Activer et déclencher le DAG

Dans l'interface Airflow, active le DAG `hibp_pipeline`, puis déclenche une exécution manuelle. Les 3 tâches (ingestion, transformation, chargement) s'exécutent séquentiellement.

### 6. Exécution locale (sans Airflow, optionnel)

Pour tester rapidement en dehors d'Airflow :

```bash
python src/hibp_pipeline.py
```

Génère `breaches.json`, `export_breaches.csv` et `export_dataclasses.csv` en local.

### 7. Dashboard Power BI

Ouvrir `powerbi/Groupe10.pbix` dans Power BI Desktop. Les données peuvent être actualisées depuis les CSV locaux ou directement depuis le bucket S3.

## Rapports et documentation

- Le rapport de projet détaillé se trouve dans `reports/rapport_groupe10.docx`
- Le support de présentation se trouve dans `reports/soutenance_groupe10.pptx`

## Analyses réalisées

- Évolution du nombre de fuites de données par année
- Volume total de comptes compromis, tous breaches confondus
- Classement des types de données les plus fréquemment volés (emails, mots de passe, etc.)
- Répartition du volume de comptes compromis par secteur d'activité (classification manuelle progressive, avec une catégorie dédiée pour les compilations de données non attribuables à un site source unique)

## Limites connues

- L'API HIBP ne fournit pas de champ "secteur d'activité" — la classification est construite manuellement, en priorisant les breaches à fort volume. Une part significative des données reste "non classée" ou relève de compilations sans site source identifiable (stealer logs, combolists).
- Les données 2026 ne couvrent qu'une partie de l'année en cours au moment de l'analyse.

## Auteur

TCHA-TCHESSI — Master 1, Groupe 10
