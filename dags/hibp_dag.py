"""
DAG Airflow - Groupe 10 - Pipeline HIBP
3 tâches : ingestion -> transformation -> chargement
Version 2 : gestion d'erreurs, retries, préparation S3 réelle (boto3)
"""

from airflow.sdk import dag, task
from datetime import datetime, timezone, timedelta
import json
import csv
import os

DATA_DIR = "/opt/airflow/dags/data"

# Paramètres par défaut appliqués à toutes les tâches du DAG
default_args = {
    "retries": 2,                          # réessaie 2 fois en cas d'échec
    "retry_delay": timedelta(minutes=2),   # attend 2 min entre chaque tentative
    "execution_timeout": timedelta(minutes=5),  # abandonne si une tâche dépasse 5 min
}


@dag(
    dag_id="hibp_pipeline",
    schedule="@daily",
    start_date=datetime(2026, 7, 1),
    catchup=False,
    tags=["groupe10", "hibp"],
    default_args=default_args,
)
def hibp_pipeline():

    @task
    def ingestion():
        """Télécharge les breaches depuis l'API HIBP et les sauvegarde en JSON."""
        import requests

        os.makedirs(DATA_DIR, exist_ok=True)
        url = "https://haveibeenpwned.com/api/v3/breaches"
        headers = {"User-Agent": "Projet-Groupe10-Airflow"}

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise RuntimeError("L'API HIBP n'a pas répondu dans le délai imparti (30s).")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"L'API HIBP a renvoyé une erreur HTTP : {e}")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Impossible de joindre l'API HIBP (problème réseau).")

        breaches = response.json()
        if not breaches:
            raise ValueError("L'API a renvoyé une liste vide, ce qui est inattendu.")

        filepath = os.path.join(DATA_DIR, "breaches.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(breaches, f, ensure_ascii=False, indent=2)

        print(f"[Ingestion] {len(breaches)} breaches téléchargés et sauvegardés.")
        return filepath

    @task
    def transformation(breaches_path: str):
        """Génère les fichiers CSV à partir des breaches téléchargés."""
        try:
            with open(breaches_path, "r", encoding="utf-8") as f:
                breaches = json.load(f)
        except FileNotFoundError:
            raise RuntimeError(f"Fichier introuvable : {breaches_path}. La tâche d'ingestion a-t-elle réussi ?")
        except json.JSONDecodeError:
            raise RuntimeError(f"Le fichier {breaches_path} n'est pas un JSON valide (corrompu ?).")

        breaches_csv = os.path.join(DATA_DIR, "export_breaches.csv")
        with open(breaches_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Domain", "BreachDate", "Year", "PwnCount"])
            for b in breaches:
                writer.writerow([
                    b["Name"], b["Domain"], b["BreachDate"],
                    b["BreachDate"][:4], b["PwnCount"],
                ])

        dataclasses_csv = os.path.join(DATA_DIR, "export_dataclasses.csv")
        with open(dataclasses_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "DataClass"])
            for b in breaches:
                for dc in b["DataClasses"]:
                    writer.writerow([b["Name"], dc])

        print(f"[Transformation] Fichiers CSV générés : {breaches_csv}, {dataclasses_csv}")
        return [breaches_csv, dataclasses_csv]

    @task
    def chargement(csv_paths: list):
        """
        Charge les fichiers vers AWS S3.
        Si les identifiants AWS ne sont pas configurés, bascule automatiquement
        en mode simulation (utile tant que le bucket n'est pas encore prêt).
        """
        aws_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
        bucket_name = os.environ.get("S3_BUCKET_NAME")
        aws_region = os.environ.get("AWS_REGION", "eu-west-3")

        date_ingestion = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if not (aws_key and aws_secret and bucket_name):
            print("[Chargement] Identifiants AWS non configurés -> mode SIMULATION.")
            for path in csv_paths:
                filename = os.path.basename(path)
                print(f"[Chargement][SIMULATION] Aurait envoyé : "
                      f"s3://<bucket>/breaches/{date_ingestion}/{filename}")
            return

        # Mode réel : envoi effectif vers S3
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError

        try:
            s3 = boto3.client(
                "s3",
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
                region_name=aws_region,
            )
            for path in csv_paths:
                filename = os.path.basename(path)
                s3_key = f"breaches/{date_ingestion}/{filename}"
                s3.upload_file(path, bucket_name, s3_key)
                print(f"[Chargement] Envoyé avec succès : s3://{bucket_name}/{s3_key}")

        except NoCredentialsError:
            raise RuntimeError("Identifiants AWS invalides ou manquants.")
        except ClientError as e:
            raise RuntimeError(f"Erreur AWS S3 : {e}")

    breaches_path = ingestion()
    csv_paths = transformation(breaches_path)
    chargement(csv_paths)


hibp_pipeline()