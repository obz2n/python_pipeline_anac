"""
dag_dbt.py
----------
DAG de transformação dbt via Astronomer Cosmos.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from cosmos import DbtTaskGroup, ProjectConfig, ProfileConfig, ExecutionConfig, RenderConfig
from cosmos.profiles import PostgresUserPasswordProfileMapping
from cosmos.constants import ExecutionMode, LoadMode

DBT_PROJECT_DIR = Path(os.getenv("DBT_PROJECT_DIR", "/opt/airflow/dbt"))
DBT_MANIFEST    = DBT_PROJECT_DIR / "target" / "manifest.json"
DBT_VENV_DIR    = Path("/opt/airflow/dbt-venv")   # virtualenv persistente

DBT_PY_REQUIREMENTS = [
    "dbt-core==1.9.8",
    "dbt-postgres==1.9.1",
]

DEFAULT_ARGS = {
    "owner":            "anac_pipeline",
    "depends_on_past":  False,
    "retries":          1,
    "retry_delay":      timedelta(minutes=10),
    "email_on_failure": False,
}

project_config = ProjectConfig(
    dbt_project_path=DBT_PROJECT_DIR,
    manifest_path=DBT_MANIFEST,
)

profile_config = ProfileConfig(
    profile_name="anac_pipeline",
    target_name="prod",
    profile_mapping=PostgresUserPasswordProfileMapping(
        conn_id="postgres_anac",
        profile_args={"schema": "bronze"},
    ),
)

execution_config = ExecutionConfig(
    execution_mode=ExecutionMode.VIRTUALENV,
    dbt_executable_path=str(DBT_VENV_DIR / "bin" / "dbt"),  # caminho explícito no venv
)

render_config = RenderConfig(
    load_method=LoadMode.DBT_MANIFEST,
)

with DAG(
    dag_id="dag_dbt_anac",
    description="Transformações dbt: bronze → silver → gold (Cosmos VIRTUALENV)",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule="0 8 1 * *",
    catchup=False,
    max_active_runs=1,
    tags=["anac", "dbt", "silver", "gold"],
) as dag:

    inicio = EmptyOperator(task_id="inicio")

    # Cria o virtualenv com dbt na primeira execução (ou se não existir)
    # Roda antes do DbtTaskGroup para garantir que o executável existe
    criar_venv = BashOperator(
        task_id="criar_venv_dbt",
        bash_command=f"""
            if [ ! -f "{DBT_VENV_DIR}/bin/dbt" ]; then
                echo "Criando virtualenv dbt em {DBT_VENV_DIR}..."
                python -m venv {DBT_VENV_DIR}
                {DBT_VENV_DIR}/bin/pip install --quiet \
                    dbt-core==1.9.8 \
                    dbt-postgres==1.9.1
                echo "Virtualenv criado com sucesso."
            else
                echo "Virtualenv dbt já existe — pulando instalação."
            fi
            {DBT_VENV_DIR}/bin/dbt --version
        """,
    )

    dbt_group = DbtTaskGroup(
        group_id="dbt_anac",
        project_config=project_config,
        profile_config=profile_config,
        execution_config=execution_config,
        render_config=render_config,
        operator_args={
            "py_requirements": DBT_PY_REQUIREMENTS,
            "install_deps":    True,
        },
        default_args={"retries": 1},
    )

    fim = EmptyOperator(task_id="fim")

    inicio >> criar_venv >> dbt_group >> fim
