import logging
from pathlib import Path

import dotenv
import pandas as pd
import sqlalchemy
from config import DATA_PROCESSED_PATH

CONNECTION_STRING = dotenv.get_key(".env", "CONNECTION_STRING")

# ============================================================
# Logger do módulo
# ============================================================
logger = logging.getLogger(__name__)


# ============================================================
# Carregamento de dados
# ============================================================


def criar_engine() -> sqlalchemy.Engine:
    """
    Cria o engine SQLAlchemy com pool configurado para carga em batch.
    pool_size=2 é suficiente: uma conexão para INSERT, outra para checagem.
    pool_pre_ping=True descarta conexões mortas automaticamente.
    """
    return sqlalchemy.create_engine(
        CONNECTION_STRING,
        pool_size=2,
        max_overflow=0,
        pool_pre_ping=True,
    )


def carregar_raw(engine: sqlalchemy.Engine):
    """
    Carrega os arquivos parquet para o banco de dados utilizando SQLAlchemy.
    """
    for file_path in DATA_PROCESSED_PATH.glob("*.parquet"):
        df = pd.read_parquet(file_path)
        df.to_sql(file_path.stem, engine, if_exists="replace", index=False)
        logger.info(f"Carregado {file_path.stem} para o banco de dados.")
