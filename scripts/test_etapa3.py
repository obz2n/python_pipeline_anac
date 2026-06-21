#!/usr/bin/env python3
"""
Script para testar especificamente a Etapa 3 (carregamento)
Testa passo a passo para diagnosticar problemas
"""

import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import os

from dotenv import load_dotenv
from loguru import logger

# Configurar logging básico
log_path = Path(__file__).parent / "logs"
log_path.mkdir(exist_ok=True)

logger.remove()
logger.add(
    str(log_path / "test_etapa3.log"),
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="DEBUG",
)
logger.add(sys.stdout, format="<level>{level: <8}</level> | {message}", level="INFO")

# ============================================================
# TESTE 1: Carregar variáveis de ambiente
# ============================================================
logger.info("TESTE 1: Carregando variáveis de ambiente...")
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
DATABASE = os.getenv("DATABASE")

logger.info(f"  USER={USER}, HOST={HOST}, PORT={PORT}, DATABASE={DATABASE}")
if PASSWORD:
    logger.info(f"  PASSWORD={'*' * len(PASSWORD)}")
else:
    logger.error("  PASSWORD não configurado!")

# ============================================================
# TESTE 2: Testar conexão com MySQL
# ============================================================
logger.info("\nTESTE 2: Testando conexão com MySQL...")
try:
    import sqlalchemy
    from sqlalchemy import text

    connection_string = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
    engine = sqlalchemy.create_engine(connection_string, pool_pre_ping=True)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 as test"))
        value = result.scalar()
        logger.info(f"  ✓ Conexão bem-sucedida: SELECT 1 retornou {value}")
except Exception as e:
    logger.error(f"  ✗ Erro na conexão: {e}")
    sys.exit(1)

# ============================================================
# TESTE 3: Testar DuckDB
# ============================================================
logger.info("\nTESTE 3: Testando DuckDB...")
try:
    import duckdb

    db = duckdb.connect(":memory:")
    logger.info(f"  ✓ DuckDB em memória conectado")

    # Teste simples
    result = db.execute("SELECT 1 as test").fetchall()
    logger.info(f"  ✓ Query simples: {result}")

except Exception as e:
    logger.error(f"  ✗ Erro no DuckDB: {e}")
    sys.exit(1)

# ============================================================
# TESTE 4: Verificar Parquets
# ============================================================
logger.info("\nTESTE 4: Verificando arquivos Parquet...")
data_processed = Path(__file__).parent / "data" / "processed"
parquet_files = sorted(data_processed.glob("*.parquet"))
logger.info(f"  Encontrados {len(parquet_files)} arquivo(s) Parquet")
for f in parquet_files[:3]:
    logger.info(f"    - {f.name}")

if not parquet_files:
    logger.error("  ✗ Nenhum arquivo Parquet encontrado!")
    sys.exit(1)

# ============================================================
# TESTE 5: Carregar primeiro Parquet com DuckDB
# ============================================================
logger.info("\nTESTE 5: Carregando primeiro Parquet com DuckDB...")
try:
    first_file = parquet_files[0]
    file_str = str(first_file)
    logger.info(f"  Arquivo: {first_file.name}")

    # Testar sintaxe de read_parquet
    query = f"SELECT COUNT(*) as cnt FROM read_parquet('{file_str}')"
    logger.debug(f"  Query: {query}")

    result = db.execute(query).fetchall()
    logger.info(f"  ✓ Arquivo carregado: {result[0][0]} linhas")

except Exception as e:
    logger.error(f"  ✗ Erro ao carregar Parquet: {e}")
    logger.exception("  Stack trace:")
    sys.exit(1)

# ============================================================
# TESTE 6: Consolidar Parquets com DuckDB
# ============================================================
logger.info("\nTESTE 6: Consolidando Parquets com DuckDB...")
try:
    for i, file_path in enumerate(parquet_files[:3], start=1):
        file_str = str(file_path)
        if i == 1:
            db.execute(
                "CREATE TABLE consolidated_data AS "
                f"SELECT *, '{file_path.name}' as source_file FROM read_parquet('{file_str}')"
            )
            logger.info(f"  [{i}] Tabela criada com {file_path.name}")
        else:
            db.execute(
                "INSERT INTO consolidated_data "
                f"SELECT *, '{file_path.name}' as source_file FROM read_parquet('{file_str}')"
            )
            logger.info(f"  [{i}] {file_path.name} inserido")

    count = db.execute("SELECT COUNT(*) as cnt FROM consolidated_data").fetchone()[0]
    logger.info(f"  ✓ Total consolidado: {count:,} linhas")

except Exception as e:
    logger.error(f"  ✗ Erro ao consolidar: {e}")
    logger.exception("  Stack trace:")
    sys.exit(1)

# ============================================================
# TESTE 7: Inserir dados no MySQL (pequeno teste)
# ============================================================
logger.info("\nTESTE 7: Inserindo dados de teste no MySQL...")
try:
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        conn.commit()
        logger.info("  ✓ Schema 'raw' criado/verificado")

    # Buscar um chunk pequeno
    chunk_df = db.execute("SELECT * FROM consolidated_data LIMIT 100").df()
    logger.info(
        f"  Chunk carregado: {len(chunk_df)} linhas, {len(chunk_df.columns)} colunas"
    )

    # Inserir no MySQL
    chunk_df.to_sql(
        "raw_anac_test",
        engine,
        schema="raw",
        if_exists="replace",
        index=False,
        method="multi",
    )
    logger.info(f"  ✓ {len(chunk_df)} linhas inseridas em raw.raw_anac_test")

    # Verificar
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM raw.raw_anac_test")).scalar()
        logger.info(f"  ✓ Verificação: {count} registros no BD")

except Exception as e:
    logger.error(f"  ✗ Erro ao inserir dados: {e}")
    logger.exception("  Stack trace:")
    sys.exit(1)

logger.info("\n" + "=" * 70)
logger.info("✓ TODOS OS TESTES PASSARAM")
logger.info("=" * 70)
