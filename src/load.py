import os
from pathlib import Path

import duckdb
import sqlalchemy
from config import CHUNKSIZE, DATA_PROCESSED_PATH, SCHEMA_NAME_RAW, TABLE_NAME_RAW
from dotenv import load_dotenv
from loguru import logger

# ============================================================
# Carregamento de variáveis de ambiente
# ============================================================
# Procurar .env na raiz do projeto (pai do diretório src/)
env_path = Path(__file__).parent.parent / ".env"

if not env_path.exists():
    logger.warning(f"Arquivo .env não encontrado em {env_path}")

# Carregar variáveis de ambiente do arquivo .env
load_dotenv(dotenv_path=env_path)

logger.debug(f"Carregando variáveis de ambiente de: {env_path}")

USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
DATABASE = os.getenv("DATABASE")

# Log de debug
logger.debug(f"USER={USER}, HOST={HOST}, PORT={PORT}, DATABASE={DATABASE}")


# ============================================================
# Carregamento de dados
# ============================================================


def criar_engine() -> sqlalchemy.Engine:
    """
    Cria o engine SQLAlchemy com pool configurado para carga em batch.

    Parâmetros:
    - pool_size=2: suficiente para uma conexão de INSERT e outra para checagem
    - max_overflow=0: evita conexões extras (não precisa paralelismo pesado)
    - pool_pre_ping=True: descarta conexões mortas automaticamente

    Retorna:
    - sqlalchemy.Engine configurado e pronto para uso

    Lança:
    - ValueError se PASSWORD não estiver configurado
    """
    if not PASSWORD:
        logger.error("Variável PASSWORD não configurada em .env")
        raise ValueError("PASSWORD deve ser definido em .env")

    # Construir URL de conexão
    host_port = f"{HOST}:{PORT}" if PORT else HOST
    connection_string = f"mysql+pymysql://{USER}:{PASSWORD}@{host_port}/{DATABASE}"
    logger.info(f"Conectando ao banco de dados: {USER}@{HOST}:{PORT}/{DATABASE}")

    try:
        engine = sqlalchemy.create_engine(
            connection_string,
            pool_size=2,
            max_overflow=0,
            pool_pre_ping=True,
        )
        # Testar a conexão
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
            logger.info("✓ Conexão com banco de dados estabelecida com sucesso")
        return engine
    except Exception as e:
        logger.error(f"✗ Erro ao conectar ao banco de dados ({HOST}:{PORT}): {e}")
        logger.error(
            f"  Verifique: USER={USER}, HOST={HOST}, PORT={PORT}, DATABASE={DATABASE}"
        )
        raise


def criar_schema_se_nao_existe(engine: sqlalchemy.Engine, schema: str) -> None:
    """
    Cria o schema no banco de dados se não existir.
    """
    try:
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text(f"CREATE SCHEMA IF NOT EXISTS `{schema}`"))
            conn.commit()
            logger.info(f"✓ Schema '{schema}' criado/verificado com sucesso")
    except Exception as e:
        logger.error(f"✗ Erro ao criar schema '{schema}': {e}")
        raise


def carregar_parquets_unificado(
    engine: sqlalchemy.Engine,
    schema: str = SCHEMA_NAME_RAW,
    table: str = TABLE_NAME_RAW,
) -> dict[str, int]:
    """
    Carrega todos os arquivos Parquet em uma ÚNICA tabela unificada usando DuckDB.

    Processo (otimizado para memória com streaming direto):
    1. Para cada Parquet individual:
       a. DuckDB lê o arquivo (lazy loading)
       b. Itera em chunks (50k linhas por vez)
       c. Insere diretamente no MySQL (sem consolidação prévia)
    2. Adiciona coluna source_file para rastrear origem
    3. Usa INSERT em batch para maximizar performance

    Benefício: Nunca carrega mais de 50k linhas em memória, evita picos > 8GB

    Parâmetros:
    - engine: SQLAlchemy Engine configurado
    - schema: nome do schema (padrão: 'raw')
    - table: nome da tabela unificada (padrão: 'raw_anac')

    Retorna:
    - dict com estatísticas: {'total_linhas': int, 'arquivos': int, 'falhas': int}
    """
    data_path = Path(DATA_PROCESSED_PATH)

    if not data_path.exists():
        logger.error(f"Diretório não existe: {data_path}")
        return {"total_linhas": 0, "arquivos": 0, "falhas": 0}

    parquet_files = sorted(data_path.glob("*.parquet"))

    if not parquet_files:
        logger.warning("Nenhum arquivo Parquet encontrado")
        return {"total_linhas": 0, "arquivos": 0, "falhas": 0}

    logger.info(
        f"Carregando {len(parquet_files)} arquivo(s) Parquet em {schema}.{table} (streaming otimizado)..."
    )

    # Criar schema se não existir
    criar_schema_se_nao_existe(engine, schema)

    falhas = 0
    total_linhas_inseridas = 0
    chunk_size = CHUNKSIZE
    table_name = f"{schema}.{table}"

    # -----------------------------------------------------------------------
    # Processar cada Parquet individualmente (streaming direto para MySQL)
    # -----------------------------------------------------------------------
    logger.info("Iniciando carregamento streaming (sem consolidação em memória)...")

    for file_idx, file_path in enumerate(parquet_files, start=1):
        try:
            logger.info(f"  [{file_idx}/{len(parquet_files)}] {file_path.name}")

            # Criar DuckDB para ESTE arquivo apenas (será descartado após)
            db = duckdb.connect(":memory:")
            file_str = str(file_path)

            try:
                # Contar linhas no arquivo para logging
                count_result = db.execute(
                    f"SELECT COUNT(*) as cnt FROM read_parquet('{file_str}')"
                ).fetchone()
                file_row_count = count_result[0] if count_result else 0
                logger.debug(f"    Total de linhas no arquivo: {file_row_count:,}")

                # Iterar em chunks e inserir no MySQL
                batch_num = 1
                offset = 0
                linhas_arquivo = 0

                while True:
                    try:
                        # Buscar chunk do arquivo via DuckDB
                        chunk_df = db.execute(
                            f"SELECT *, '{file_path.name}' as source_file "
                            f"FROM read_parquet('{file_str}') "
                            f"LIMIT {chunk_size} OFFSET {offset}"
                        ).df()

                        if len(chunk_df) == 0:
                            break

                        # Inserir chunk no MySQL com transação explícita
                        logger.debug(
                            f"      Batch {batch_num}: inserindo {len(chunk_df):,} linhas..."
                        )

                        # Usar begin() para transação explícita
                        with engine.begin() as conn:
                            chunk_df.to_sql(
                                table,
                                conn,
                                schema=schema,
                                if_exists="append",
                                index=False,
                                method=None,  # Sem method específico, usa padrão (mais seguro)
                            )

                        linhas_arquivo += len(chunk_df)
                        total_linhas_inseridas += len(chunk_df)
                        offset += chunk_size
                        batch_num += 1

                    except Exception as chunk_error:
                        logger.error(
                            f"      ✗ Erro ao processar batch {batch_num}: {chunk_error}"
                        )
                        # Log do erro mas continua com próximo batch
                        logger.warning(f"      ⚠️  Continuando com próximo batch...")
                        offset += chunk_size
                        batch_num += 1

                logger.debug(
                    f"    ✓ {file_path.name} inserido ({linhas_arquivo:,} linhas)"
                )

            finally:
                # Fechar conexão DuckDB deste arquivo (liberar memória)
                db.close()

        except Exception as e:
            logger.error(f"  ✗ Erro ao processar {file_path.name}: {e}")
            falhas += 1
            continue

    if falhas == len(parquet_files):
        logger.error("Nenhum arquivo Parquet foi processado com sucesso")
        return {"total_linhas": 0, "arquivos": 0, "falhas": falhas}

    # Resumo final
    logger.info("=" * 70)
    logger.info("Carregamento unificado concluído!")
    logger.info(
        f"  Arquivos processados : {len(parquet_files) - falhas}/{len(parquet_files)}"
    )
    logger.info(f"  Total de linhas      : {total_linhas_inseridas:,}")
    logger.info(f"  Falhas               : {falhas}")
    logger.info(f"  Tabela de destino    : {table_name}")
    logger.info(f"  Chunk size           : {chunk_size:,} linhas/batch")
    logger.info("=" * 70)

    return {
        "total_linhas": total_linhas_inseridas,
        "arquivos": len(parquet_files) - falhas,
        "falhas": falhas,
    }


def contar_registros(
    engine: sqlalchemy.Engine,
    schema: str = SCHEMA_NAME_RAW,
    table: str = TABLE_NAME_RAW,
) -> int:
    """
    Conta o número de registros na tabela unificada.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                sqlalchemy.text(f"SELECT COUNT(*) as count FROM `{schema}`.`{table}`")
            )
            count = result.scalar()
            logger.info(f"Total de registros em {schema}.{table}: {count:,}")
            return count
    except Exception as e:
        logger.warning(f"Não foi possível contar registros: {e}")
        return 0
