"""
Groupe 10 - Consolidation des exports S3 avec DuckDB
Interroge directement tous les fichiers CSV déposés par le DAG Airflow sur S3,
sans les télécharger manuellement ni les fusionner à la main.
"""

import duckdb
import os

# Récupère les identifiants AWS depuis les variables d'environnement
# (les mêmes que celles utilisées par le DAG, dans le fichier .env)
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "eu-north-1")
BUCKET = os.environ.get("S3_BUCKET_NAME", "hibp-groupe10-2026")

con = duckdb.connect()

# Installe et charge l'extension httpfs, nécessaire pour lire depuis S3
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")

# Configure les identifiants AWS pour cette session DuckDB
con.execute(f"""
    CREATE SECRET (
        TYPE s3,
        KEY_ID '{AWS_ACCESS_KEY_ID}',
        SECRET '{AWS_SECRET_ACCESS_KEY}',
        REGION '{AWS_REGION}'
    );
""")

print(f"[OK] Connexion à s3://{BUCKET}/breaches/ configurée.\n")

# --- Requête 1 : consolider TOUS les export_breaches.csv, quelle que soit la date ---
query_breaches = f"""
    SELECT *
    FROM read_csv_auto('s3://{BUCKET}/breaches/*/export_breaches.csv', filename=true)
"""
df_breaches = con.execute(query_breaches).df()
print(f"[Consolidation] {len(df_breaches)} lignes récupérées depuis toutes les dates d'ingestion disponibles.")
print(f"[Consolidation] Dates d'ingestion distinctes trouvées : {df_breaches['filename'].nunique()}\n")

# --- Requête 2 : exemple d'analyse directement en SQL, sans Pandas ---
query_top_secteurs = f"""
    SELECT
        Secteur,
        SUM(PwnCount) AS total_comptes,
        COUNT(*) AS nb_breaches
    FROM read_csv_auto('s3://{BUCKET}/breaches/*/export_breaches.csv')
    GROUP BY Secteur
    ORDER BY total_comptes DESC
"""
print("[Analyse SQL] Comptes compromis par secteur, tous jours d'ingestion confondus :\n")
print(con.execute(query_top_secteurs).df().to_string(index=False))

con.close()