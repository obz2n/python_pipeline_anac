import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import DATA_PROCESSED_PATH, DATA_RAW_PATH, LOG_PATH
from extract import carregar_parquet_duckdb, processar_arquivos_txt

# ============================================================
# Configuração de logging centralizada
# ============================================================
pasta_logs = LOG_PATH
arquivo_logs = pasta_logs / "anac.log"
pasta_logs.mkdir(parents=True, exist_ok=True)

# Handler de arquivo rotativo (max 5MB por arquivo, mantendo 3 backups)
file_handler = RotatingFileHandler(
    filename=str(arquivo_logs),
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
file_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(file_formatter)

# Handler de console para facilitar desenvolvimento
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s - %(message)s", datefmt="%H:%M:%S"
)
console_handler.setFormatter(console_formatter)

# Logger root configuration
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
# Remover handlers duplicados se já existirem (evita logs duplicados em execuções interativas)
for h in list(root_logger.handlers):
    root_logger.removeHandler(h)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)


# ============================================================
# Funções auxiliares
# ============================================================
def carregar_parquets(diretorio: Path) -> list[Path]:
    """Retorna uma lista de arquivos Parquet no diretório especificado."""
    if not diretorio.exists():
        logger.warning(f"Diretório não existe: {diretorio}")
        return []

    arquivos = list(diretorio.glob("*.parquet"))
    logger.info(f"Encontrados {len(arquivos)} arquivo(s) Parquet em {diretorio.name}")
    return arquivos


# ============================================================
# Pipeline
# ============================================================
def main():
    logger.info("=" * 60)
    logger.info("Iniciando execução do pipeline ANAC.")
    logger.info("=" * 60)

    try:
        # --------------------------------------------------------
        # Etapa 1: Extração e conversão para Parquet
        # --------------------------------------------------------
        logger.info("Etapa 1: Extração de dados (txt -> parquet)")
        txt_files = list(DATA_RAW_PATH.glob("*.txt"))

        if not txt_files:
            logger.warning(f"Nenhum arquivo .txt encontrado em {str(DATA_RAW_PATH)}")
            logger.info("Pipeline concluído sem dados para processar.")
        else:
            logger.info(
                f"Encontrados {len(txt_files)} arquivo(s) .txt em {str(DATA_RAW_PATH)}"
            )
            stats = processar_arquivos_txt(txt_files)
            logger.info(f"Etapa 1 concluída. Resultados: {stats}")

            # --------------------------------------------------------
            # Etapa 2: Carregamento de Parquets com DuckDB
            # --------------------------------------------------------
            logger.info("Etapa 2: Carregamento de Parquets com DuckDB")
            parquet_files = carregar_parquets(DATA_PROCESSED_PATH)

            if parquet_files:
                logger.info(f"Carregando {len(parquet_files)} Parquet(s) com DuckDB...")
                for parquet_file in parquet_files[
                    :3
                ]:  # Limita a 3 arquivos como exemplo
                    relacao = carregar_parquet_duckdb(parquet_file)
                    if relacao:
                        logger.debug(f"  ✓ {parquet_file.name} carregado com sucesso")
            else:
                logger.warning("Nenhum arquivo Parquet para carregar.")

            # --------------------------------------------------------
            # Etapa 3: Carregamento em banco de dados (placeholder)
            # --------------------------------------------------------
            logger.info(
                "Etapa 3: Carregamento de dados em banco de dados (placeholder)"
            )
            logger.info("  TODO: implementar carregamento em banco de dados")

            logger.info("=" * 60)
            logger.info("Pipeline concluído com sucesso.")
            logger.info("=" * 60)

    except Exception as e:
        logger.exception("Erro durante a execução do pipeline:")
        raise
    finally:
        logger.info("Finalizando execução do pipeline.")


if __name__ == "__main__":
    main()
