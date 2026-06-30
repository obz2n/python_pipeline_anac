import os
from pathlib import Path

import duckdb
import sqlalchemy
from config import CHUNKSIZE, DATA_PROCESSED_PATH, SCHEMA_NAME_BRONZE, TABLE_NAME_BRONZE
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

# Usar DB_USER em vez de USER para evitar conflito com variável de sistema
DB_USER = os.getenv("DB_USER") or os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
DATABASE = os.getenv("DATABASE")
SCHEMA = os.getenv("SCHEMA")
DB_DIALECT = os.getenv("DB_DIALECT", "mysql").lower()

# Log de debug
logger.debug(
    f"DB_USER={DB_USER}, HOST={HOST}, PORT={PORT}, DATABASE={DATABASE}, SCHEMA={SCHEMA}, DB_DIALECT={DB_DIALECT}"
)


# ============================================================
# Carregamento de dados
# ============================================================


def criar_engine() -> sqlalchemy.Engine:
    """
    Cria o engine SQLAlchemy com pool configurado para carga em batch.

    Suporta MySQL/MariaDB e PostgreSQL. Usa sqlalchemy.engine.URL.create()
    para escapar corretamente username/password com caracteres especiais (ex: '@', '!').

    Variáveis de ambiente:
    - USER, PASSWORD, HOST, PORT, DATABASE
    - DB_DIALECT (opcional): 'mysql' (padrão) ou 'postgresql'
    - SCHEMA (opcional): schema padrão a ser usado

    Retorna:
    - sqlalchemy.Engine configurado e pronto para uso

    Lança:
    - ValueError se PASSWORD não estiver configurado
    """
    if not PASSWORD:
        logger.error("Variável PASSWORD não configurada em .env")
        raise ValueError("PASSWORD deve ser definido em .env")

    # Detectar driver baseado em DB_DIALECT
    if DB_DIALECT in ("postgres", "postgresql"):
        drivername = "postgresql+psycopg2"
    else:
        drivername = "mysql+pymysql"

    # Validar e limpar DATABASE (remover '/schema' se presente)
    db_name = DATABASE
    if db_name and "/" in db_name:
        logger.warning(
            "DATABASE contém '/' (ex: 'postgres/bronze'). "
            "Use somente o nome do banco. Schema deve estar em SCHEMA no .env."
        )
        db_name = db_name.split("/")[0]

    port_int = int(PORT) if PORT else None

    logger.info(
        f"Conectando ao banco de dados: {DB_USER}@{HOST}:{PORT}/{db_name} "
        f"(driver={drivername})"
    )

    try:
        # URL.create() escapa automáticamente username/password
        url = sqlalchemy.engine.URL.create(
            drivername=drivername,
            username=DB_USER,
            password=PASSWORD,
            host=HOST,
            port=port_int,
            database=db_name,
        )

        engine = sqlalchemy.create_engine(
            url,
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
            f"  Verifique: DB_USER={DB_USER}, HOST={HOST}, PORT={PORT}, DATABASE={DATABASE}"
        )
        raise


def criar_schema_se_nao_existe(engine: sqlalchemy.Engine, schema: str) -> None:
    """
    Cria o schema no banco de dados se não existir.
    Compatível com MySQL, MariaDB e PostgreSQL.

    Parâmetros:
    - engine: SQLAlchemy Engine configurado
    - schema: nome do schema a criar
    """
    try:
        with engine.begin() as conn:
            if DB_DIALECT in ("postgres", "postgresql"):
                # PostgreSQL: usar aspas duplas para identificadores
                conn.execute(sqlalchemy.text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            else:
                # MySQL/MariaDB: usar backticks
                conn.execute(sqlalchemy.text(f"CREATE SCHEMA IF NOT EXISTS `{schema}`"))
            logger.info(f"✓ Schema '{schema}' criado/verificado com sucesso")
    except Exception as e:
        logger.error(f"✗ Erro ao criar schema '{schema}': {e}")
        raise


def inserir_chunk_no_banco(
    engine: sqlalchemy.Engine,
    chunk_df,
    schema: str,
    table: str,
    batch_num: int,
) -> int:
    """
    Insere um chunk de dados no banco de dados.
    Compatível com MySQL, MariaDB e PostgreSQL.

    Parâmetros:
    - engine: SQLAlchemy Engine configurado
    - chunk_df: DataFrame com os dados a inserir
    - schema: nome do schema
    - table: nome da tabela
    - batch_num: número do batch (para logging)

    Retorna:
    - int: número de linhas inseridas
    """
    linhas_chunk = len(chunk_df)
    logger.debug(f"      Batch {batch_num}: inserindo {linhas_chunk:,} linhas...")

    with engine.begin() as conn:
        chunk_df.to_sql(
            table, conn, schema=schema, if_exists="append", index=False, method=None
        )
    return linhas_chunk


def obter_contagem_linhas(db, file_path: str) -> int:
    """
    Obtém a contagem de linhas de um arquivo Parquet via DuckDB.

    Parâmetros:
    - db: conexão DuckDB
    - file_path: caminho completo do arquivo

    Retorna:
    - int: número de linhas no arquivo
    """
    try:
        result = db.execute(
            f"SELECT COUNT(*) as cnt FROM read_parquet('{file_path}')"
        ).fetchone()
        return result[0] if result else 0
    except Exception as e:
        logger.debug(f"Erro ao contar linhas: {e}")
        return 0


def ler_chunks_duckdb(db, file_name: str, file_path: str, chunk_size: int):
    """
    Generator que lê chunks do arquivo Parquet via DuckDB.

    Parâmetros:
    - db: conexão DuckDB
    - file_name: nome do arquivo (para coluna source_file)
    - file_path: caminho completo do arquivo
    - chunk_size: tamanho de cada chunk em linhas

    Yields:
    - DataFrame com até chunk_size linhas
    """
    offset = 0
    while True:
        chunk_df = db.execute(
            f"SELECT *, '{file_name}' as source_file "
            f"FROM read_parquet('{file_path}') "
            f"LIMIT {chunk_size} OFFSET {offset}"
        ).df()

        if chunk_df.empty:
            break

        yield chunk_df
        offset += chunk_size


def processar_arquivo_parquet(
    engine: sqlalchemy.Engine,
    file_path: Path,
    file_idx: int,
    total_arquivos: int,
    schema: str,
    table: str,
    chunk_size: int,
) -> tuple[int, bool]:
    """
    Processa um único arquivo Parquet em chunks e o insere no banco.

    Parâmetros:
    - engine: SQLAlchemy Engine configurado
    - file_path: caminho do arquivo Parquet
    - file_idx: índice do arquivo (para logging)
    - total_arquivos: total de arquivos (para logging)
    - schema: nome do schema
    - table: nome da tabela
    - chunk_size: tamanho de cada chunk

    Retorna:
    - tuple: (total_linhas_arquivo, sucesso_bool)
    """
    logger.info(f"  [{file_idx}/{total_arquivos}] {file_path.name}")
    db = duckdb.connect(":memory:")
    file_str = str(file_path)
    linhas_arquivo = 0

    try:
        # Log contagem de linhas do arquivo
        total_linhas_arquivo = obter_contagem_linhas(db, file_str)
        logger.debug(f"    Total de linhas no arquivo: {total_linhas_arquivo:,}")

        # Processar chunks
        for batch_num, chunk_df in enumerate(
            ler_chunks_duckdb(db, file_path.name, file_str, chunk_size), start=1
        ):
            try:
                linhas_inseridas = inserir_chunk_no_banco(
                    engine, chunk_df, schema, table, batch_num
                )
                linhas_arquivo += linhas_inseridas
            except Exception as chunk_error:
                logger.error(
                    f"      ✗ Erro ao processar batch {batch_num}: {chunk_error}"
                )
                logger.warning(f"      ⚠️  Pulando batch {batch_num}")

        logger.debug(f"    ✓ {file_path.name} inserido ({linhas_arquivo:,} linhas)")
        return linhas_arquivo, True

    except Exception as e:
        logger.error(f"  ✗ Erro ao processar {file_path.name}: {e}")
        logger.debug(f"  Stack trace:", exc_info=True)
        return 0, False
    finally:
        db.close()


def carregar_parquets_unificado(
    engine: sqlalchemy.Engine,
    schema: str = SCHEMA_NAME_BRONZE,
    table: str = TABLE_NAME_BRONZE,
) -> dict[str, int]:
    """
    Carrega todos os arquivos Parquet em uma Única tabela unificada usando DuckDB.

    Processo (otimizado para memória com streaming direto):
    1. Para cada Parquet individual:
       a. DuckDB lê o arquivo (lazy loading)
       b. Itera em chunks (50k linhas por vez) via generator
       c. Insere diretamente no banco de dados (sem consolidação prévia)
    2. Adiciona coluna source_file para rastrear origem
    3. Usa INSERT em batch para maximizar performance

    Compatível com MySQL, MariaDB e PostgreSQL.

    Benefício: Nunca carrega mais de 50k linhas em memória, evita picos > 8GB

    Parâmetros:
    - engine: SQLAlchemy Engine configurado
    - schema: nome do schema (padrão: 'bronze')
    - table: nome da tabela unificada (padrão: 'bronze_anac')

    Retorna:
    - dict com estatísticas: {'total_linhas': int, 'arquivos': int, 'falhas': int}
    """
    # Validar diretório de dados
    data_path = Path(DATA_PROCESSED_PATH)
    if not data_path.exists():
        logger.error(f"Diretório não existe: {data_path}")
        return {"total_linhas": 0, "arquivos": 0, "falhas": 0}

    # Buscar arquivos Parquet
    parquet_files = sorted(data_path.glob("*.parquet"))
    if not parquet_files:
        logger.warning("Nenhum arquivo Parquet encontrado")
        return {"total_linhas": 0, "arquivos": 0, "falhas": 0}

    # Inicializar
    logger.info(
        f"Carregando {len(parquet_files)} arquivo(s) Parquet em {schema}.{table} (streaming otimizado)..."
    )
    criar_schema_se_nao_existe(engine, schema)

    chunk_size = CHUNKSIZE
    table_name = f"{schema}.{table}"
    total_linhas_inseridas = 0
    arquivos_sucesso = 0

    logger.info("Iniciando carregamento streaming (sem consolidação em memória)...")

    # Processar cada arquivo
    for file_idx, file_path in enumerate(parquet_files, start=1):
        linhas_arquivo, sucesso = processar_arquivo_parquet(
            engine, file_path, file_idx, len(parquet_files), schema, table, chunk_size
        )

        if sucesso:
            total_linhas_inseridas += linhas_arquivo
            arquivos_sucesso += 1

    # Resumo final
    falhas = len(parquet_files) - arquivos_sucesso

    if arquivos_sucesso == 0:
        logger.error("Nenhum arquivo Parquet foi processado com sucesso")
        return {"total_linhas": 0, "arquivos": 0, "falhas": falhas}

    logger.info("=" * 70)
    logger.info("Carregamento unificado concluído!")
    logger.info(f"  Arquivos processados : {arquivos_sucesso}/{len(parquet_files)}")
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
    schema: str = SCHEMA_NAME_BRONZE,
    table: str = TABLE_NAME_BRONZE,
) -> int:
    """
    Conta o número de registros na tabela unificada.
    Compatível com MySQL, MariaDB e PostgreSQL.
    """
    try:
        with engine.connect() as conn:
            if DB_DIALECT in ("postgres", "postgresql"):
                # PostgreSQL: usar aspas duplas
                query = f'SELECT COUNT(*) as count FROM "{schema}"."{table}"'
            else:
                # MySQL/MariaDB: usar backticks
                query = f"SELECT COUNT(*) as count FROM `{schema}`.`{table}`"

            result = conn.execute(sqlalchemy.text(query))
            count = result.scalar()
            logger.info(f"Total de registros em {schema}.{table}: {count:,}")
            return count
    except Exception as e:
        logger.warning(f"Não foi possível contar registros: {e}")
        return 0
