"""
dag_ingestao.py
---------------
DAG de ingestão mensal dos arquivos CSV da ANAC.

Fluxo:
    verificar_arquivo → extract → load → notificar_dag_dbt

Schedule: primeiro dia de cada mês às 06:00.
Trigger manual também suportado via UI.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

# -- Caminhos (devem bater com os volumes do docker-compose) --
SCRIPTS_DIR = os.getenv("SCRIPTS_DIR", "/opt/airflow/scripts")
DATA_DIR    = os.getenv("DATA_PATH",   "/opt/airflow/data")

# -- Configurações padrão de cada task --
DEFAULT_ARGS = {
    "owner":            "anac_pipeline",
    "depends_on_past":  False,
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
    "email_on_failure": False,
}


# ── Funções das tasks ──────────────────────────────────────────────

def verificar_arquivo(**context) -> None:
    """
    Verifica se existe pelo menos um arquivo .csv ou .parquet em DATA_DIR.
    Falha a task se a pasta estiver vazia — evita rodar load sem dados.
    """
    import glob
    import logging

    logger = logging.getLogger(__name__)

    # Procura por .csv (input) ou .parquet (se extract já foi rodado)
    csvs = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    parquets = glob.glob(os.path.join(DATA_DIR, "*.parquet"))
    arquivos = csvs + parquets

    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum arquivo .csv ou .parquet encontrado em '{DATA_DIR}'.\n"
            f"Coloque os CSVs da ANAC na pasta e rode o extract manualmente, "
            f"ou verifique o volume montado no docker-compose."
        )

    logger.info(f"Arquivos encontrados: {len(csvs)} CSVs, {len(parquets)} Parquets")
    for f in csvs[:3]:  # mostra apenas os primeiros 3 para não poluir logs
        logger.info(f"  CSV: {os.path.basename(f)}")
    for f in parquets[:3]:
        logger.info(f"  Parquet: {os.path.basename(f)}")

    # Passa a lista para as próximas tasks via XCom
    context["ti"].xcom_push(key="input_files", value=arquivos)


def executar_extract(**context) -> None:
    """
    Chama o extract.py: lê os CSVs da ANAC e converte para .parquet.
    Usa importação direta do módulo para melhor rastreabilidade de erros.
    """
    import sys
    sys.path.insert(0, SCRIPTS_DIR)

    import importlib
    extract = importlib.import_module("extract")
    extract.processar_arquivos_txt(extract.TXT_FILES)


def executar_load(**context) -> None:
    """
    Chama o load.py: carrega os .parquet no schema bronze do PostgreSQL.
    Idempotente — arquivos já carregados são ignorados automaticamente.
    """
    import sys
    sys.path.insert(0, SCRIPTS_DIR)

    import importlib
    load = importlib.import_module("load")
    load.processar_carga(load.PARQUET_FILES)


# ── Definição da DAG ──────────────────────────────────────────────

with DAG(
    dag_id="dag_ingestao_anac",
    description="Ingestão mensal dos microdados de voos da ANAC: CSV → parquet → PostgreSQL (bronze)",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule="0 6 1 * *",   # primeiro dia do mês às 06:00
    catchup=False,           # não reprocessa meses anteriores automaticamente
    max_active_runs=1,       # garante que só uma execução rode por vez
    tags=["anac", "ingestao", "bronze"],
) as dag:

    inicio = EmptyOperator(task_id="inicio")

    verify = PythonOperator(
        task_id="verificar_arquivos",
        python_callable=verificar_arquivo,
        doc_md="""
        Verifica se existem arquivos .csv ou .parquet em DATA_DIR.
        Falha a pipeline antes de tentar carregar dados inexistentes.
        Suporta CSVs originais ou Parquets pré-processados.
        """,
    )

    extract = PythonOperator(
        task_id="extract",
        python_callable=executar_extract,
        doc_md="Lê CSVs da ANAC, detecta encoding e converte para .parquet.",
        execution_timeout=timedelta(hours=1),
    )

    load = PythonOperator(
        task_id="load",
        python_callable=executar_load,
        doc_md="Carrega os .parquet no schema bronze.voos do PostgreSQL (append + idempotente).",
        execution_timeout=timedelta(hours=2),
    )

    # Dispara a dag_dbt logo após a carga, passando o mês de referência via conf
    trigger_dbt = TriggerDagRunOperator(
        task_id="trigger_dag_dbt",
        trigger_dag_id="dag_dbt_anac",
        wait_for_completion=False,   # não bloqueia esta DAG aguardando o dbt terminar
        conf={
            "origem": "dag_ingestao_anac",
            "data_execucao": "{{ ds }}",
        },
        doc_md="Dispara a dag_dbt_anac após carga bem-sucedida.",
    )

    fim = EmptyOperator(
        task_id="fim",
        trigger_rule=TriggerRule.ALL_DONE,
    )

    # ── Dependências ──────────────────────────────────────────────
    inicio >> verificar >> extract >> load >> trigger_dbt >> fim
