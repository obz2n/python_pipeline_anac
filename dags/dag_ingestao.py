"""
dag_ingestao.py
---------------
DAG de ingestão mensal dos arquivos CSV da ANAC.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

SCRIPTS_DIR = os.getenv("SCRIPTS_DIR", "/opt/airflow/scripts")
DATA_DIR    = os.getenv("DATA_PATH",   "/opt/airflow/data")

DEFAULT_ARGS = {
    "owner":            "anac_pipeline",
    "depends_on_past":  False,
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
    "email_on_failure": False,
}


def verificar_arquivo_fn(**context) -> None:
    import glob
    arquivos = glob.glob(os.path.join(DATA_DIR, "*.parquet"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum arquivo .parquet encontrado em '{DATA_DIR}'."
        )
    print(f"Arquivos encontrados: {len(arquivos)}")
    for f in arquivos:
        print(f"  - {os.path.basename(f)}")
    context["ti"].xcom_push(key="parquet_files", value=arquivos)


def executar_extract_fn(**context) -> None:
    import sys
    sys.path.insert(0, SCRIPTS_DIR)
    import importlib
    extract = importlib.import_module("extract")
    extract.processar_arquivos_txt(extract.TXT_FILES)


def executar_load_fn(**context) -> None:
    import sys
    sys.path.insert(0, SCRIPTS_DIR)
    import importlib
    load = importlib.import_module("load")
    load.processar_carga(load.PARQUET_FILES)


with DAG(
    dag_id="dag_ingestao_anac",
    description="Ingestão mensal ANAC: CSV → parquet → PostgreSQL (bronze)",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule="0 6 1 * *",
    catchup=False,
    max_active_runs=1,
    tags=["anac", "ingestao", "bronze"],
) as dag:

    inicio = EmptyOperator(task_id="inicio")

    # CORRIGIDO: variável nomeada igual ao task_id para evitar confusão
    verificar = PythonOperator(
        task_id="verificar_arquivos",
        python_callable=verificar_arquivo_fn,
    )

    extract = PythonOperator(
        task_id="extract",
        python_callable=executar_extract_fn,
        execution_timeout=timedelta(hours=1),
    )

    load = PythonOperator(
        task_id="load",
        python_callable=executar_load_fn,
        execution_timeout=timedelta(hours=2),
    )

    trigger_dbt = TriggerDagRunOperator(
        task_id="trigger_dag_dbt",
        trigger_dag_id="dag_dbt_anac",
        wait_for_completion=False,
        conf={
            "origem": "dag_ingestao_anac",
            "data_execucao": "{{ ds }}",
        },
    )

    fim = EmptyOperator(
        task_id="fim",
        trigger_rule=TriggerRule.ALL_DONE,
    )

    # CORRIGIDO: encadeamento usando os nomes corretos das variáveis
    inicio >> verificar >> extract >> load >> trigger_dbt >> fim
