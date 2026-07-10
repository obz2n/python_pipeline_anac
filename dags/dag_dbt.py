"""
dag_dbt.py
----------
DAG de transformação dbt orquestrada via Astronomer Cosmos.

O Cosmos converte automaticamente cada modelo dbt em uma task Airflow,
respeitando o grafo de dependências do dbt (ref / source).

Fluxo gerado automaticamente pelo Cosmos:
    seed_aeroportos
        └── silver_voos
                ├── gold_pontualidade
                ├── gold_volume_periodo
                └── gold_ranking_rotas_atrasadas

Schedule: primeiro dia do mês às 08:00 (2h após dag_ingestao).
Também disparada automaticamente via TriggerDagRunOperator da dag_ingestao.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.empty import EmptyOperator

from cosmos import DbtTaskGroup, ProjectConfig, ProfileConfig, ExecutionConfig
from cosmos.profiles import PostgresUserPasswordProfileMapping
from cosmos.constants import ExecutionMode

# -- Caminhos (devem bater com os volumes do docker-compose) --
DBT_PROJECT_DIR  = Path(os.getenv("DBT_PROJECT_DIR",  "/opt/airflow/dbt"))
DBT_PROFILES_DIR = Path(os.getenv("DBT_PROFILES_DIR", "/opt/airflow/dbt"))

# -- Configurações padrão de cada task --
DEFAULT_ARGS = {
    "owner":            "anac_pipeline",
    "depends_on_past":  False,
    "retries":          1,
    "retry_delay":      timedelta(minutes=10),
    "email_on_failure": False,
}


# ── Configuração do Cosmos ─────────────────────────────────────────

project_config = ProjectConfig(
    dbt_project_path=DBT_PROJECT_DIR,
)

profile_config = ProfileConfig(
    profile_name="anac_pipeline",
    target_name="prod",
    profile_mapping=PostgresUserPasswordProfileMapping(
        conn_id="postgres_anac",   # Connection cadastrada no Airflow (Admin → Connections)
        profile_args={
            "schema": "bronze",    # schema de entrada — onde o source raw.voos está
        },
    ),
)

execution_config = ExecutionConfig(
    execution_mode=ExecutionMode.LOCAL,   # roda dbt no mesmo processo do Airflow
    dbt_executable_path=os.getenv("DBT_EXECUTABLE", "/usr/local/bin/dbt"),
)


# ── Definição da DAG ──────────────────────────────────────────────

with DAG(
    dag_id="dag_dbt_anac",
    description="Transformações dbt: bronze → silver → gold (Astronomer Cosmos)",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule="0 8 1 * *",   # primeiro dia do mês às 08:00 (2h após a ingestão)
    catchup=False,
    max_active_runs=1,
    tags=["anac", "dbt", "silver", "gold"],
) as dag:

    inicio = EmptyOperator(task_id="inicio")

    # O Cosmos gera automaticamente uma task por modelo dbt,
    # na ordem correta de dependências definida pelos ref() e source()
    dbt_group = DbtTaskGroup(
        group_id="dbt_anac",
        project_config=project_config,
        profile_config=profile_config,
        execution_config=execution_config,
        operator_args={
            "install_deps": True,   # roda `dbt deps` antes do primeiro modelo
        },
        default_args={
            "retries": 1,
        },
    )

    fim = EmptyOperator(task_id="fim")

    # ── Dependências ──────────────────────────────────────────────
    inicio >> dbt_group >> fim
