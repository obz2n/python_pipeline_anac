import sys
from pathlib import Path

from config import DATA_PROCESSED_PATH, DATA_RAW_PATH, LOG_PATH
from extract import carregar_parquet_duckdb, processar_arquivos_txt
from load import carregar_parquets_unificado, contar_registros, criar_engine
from loguru import logger

# ============================================================
# Configuração de logging centralizado com loguru
# ============================================================
log_path = Path(LOG_PATH)
log_path.mkdir(parents=True, exist_ok=True)
log_file = log_path / "anac.log"

# Remover handler padrão (stderr)
logger.remove()

# Adicionar handler de arquivo (persistente)
logger.add(
    str(log_file),
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="5 MB",  # Rotaciona quando atingir 5MB
    retention=3,  # Mantém 3 backups
    encoding="utf-8",
)

# Adicionar handler de console (colorido)
logger.add(
    sys.stdout,
    format="<level>{time:HH:mm:ss}</level> | <level>{level: <8}</level> | {message}",
    level="INFO",
    colorize=True,
)

logger.info("Sistema de logging inicializado")


# ============================================================
# Funções auxiliares
# ============================================================
def carregar_parquets(diretorio: Path | str) -> list[Path]:
    """Retorna uma lista de arquivos Parquet no diretório especificado."""
    dir_path = Path(diretorio)

    if not dir_path.exists():
        logger.warning(f"Diretório não existe: {dir_path}")
        return []

    arquivos = sorted(dir_path.glob("*.parquet"))
    logger.info(f"Encontrados {len(arquivos)} arquivo(s) Parquet em {dir_path.name}")
    return arquivos


# ============================================================
# Pipeline
# ============================================================
def main():
    logger.info("=" * 70)
    logger.info("INICIANDO EXECUÇÃO DO PIPELINE ANAC")
    logger.info("=" * 70)

    try:
        # ================================================================
        # Etapa 1: Extração e conversão para Parquet
        # ================================================================
        logger.info("Etapa 1: Extração de dados (txt -> parquet)")
        logger.info("-" * 70)

        data_raw = Path(DATA_RAW_PATH)
        txt_files = sorted(data_raw.glob("*.txt"))

        if not txt_files:
            logger.warning(f"Nenhum arquivo .txt encontrado em {str(data_raw)}")
            logger.info("Pipeline interrompido: sem dados para processar.")
            return

        logger.info(f"Encontrados {len(txt_files)} arquivo(s) .txt")
        stats_extract = processar_arquivos_txt(txt_files)

        if stats_extract["sucessos"] == 0:
            logger.error("Nenhum arquivo foi processado com sucesso na Etapa 1.")
            logger.warning("Pipeline interrompido: nenhum Parquet gerado.")
            return

        logger.info(
            f"✓ Etapa 1 concluída: {stats_extract['sucessos']} sucessos, {stats_extract['falhas']} falhas"
        )

        # ================================================================
        # Etapa 2: Validação de Parquets com DuckDB
        # ================================================================
        logger.info("")
        logger.info("Etapa 2: Validação de Parquets com DuckDB")
        logger.info("-" * 70)

        parquet_files = carregar_parquets(DATA_PROCESSED_PATH)

        if not parquet_files:
            logger.error("Nenhum arquivo Parquet encontrado após Etapa 1.")
            logger.warning("Pipeline interrompido: sem Parquets para validar.")
            return

        logger.info(
            f"Carregando {len(parquet_files)} Parquet(s) com DuckDB para validação..."
        )

        parquets_validos = 0
        for parquet_file in parquet_files:
            relacao = carregar_parquet_duckdb(parquet_file)
            if relacao:
                parquets_validos += 1

        if parquets_validos == 0:
            logger.error("Nenhum Parquet foi carregado com sucesso.")
            logger.warning("Pipeline interrompido: Parquets inválidos.")
            return

        logger.info(
            f"✓ Etapa 2 concluída: {parquets_validos}/{len(parquet_files)} Parquets válidos"
        )

        # ================================================================
        # Etapa 3: Carregamento em banco de dados
        # ================================================================
        logger.info("")
        logger.info("Etapa 3: Carregamento de dados em banco de dados")
        logger.info("-" * 70)

        try:
            engine = criar_engine()
            logger.info("Engine SQLAlchemy criado com sucesso")

            stats_load = carregar_parquets_unificado(engine)

            if stats_load["arquivos"] == 0:
                logger.error("Nenhum arquivo Parquet foi carregado no banco de dados.")
            else:
                total_registros = contar_registros(engine)
                logger.info(
                    f"✓ Etapa 3 concluída: {stats_load['arquivos']} Parquets carregados, {stats_load['total_linhas']:,} linhas, {total_registros:,} registros no BD"
                )

        except ValueError as e:
            logger.warning(f"Etapa 3 pulada: {e}")
            logger.info(
                "Configure as variáveis de ambiente em .env para habilitar o carregamento."
            )
            stats_load = None
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {e}")
            logger.warning("Etapa 3 foi interrompida, mas Etapas 1 e 2 completadas.")
            stats_load = None

        # ================================================================
        # Resumo final
        # ================================================================
        logger.info("")
        logger.info("=" * 70)
        logger.info("PIPELINE CONCLUÍDO COM SUCESSO")
        logger.info("=" * 70)
        logger.info(f"Etapa 1 (Extração)  : {stats_extract['sucessos']} sucessos")
        logger.info(f"Etapa 2 (Validação) : {parquets_validos} Parquets válidos")
        if stats_load is not None and stats_load["arquivos"] > 0:
            logger.info(
                f"Etapa 3 (Carregamento): {stats_load['total_linhas']:,} linhas em raw.raw_anac"
            )

    except Exception as e:
        logger.exception("ERRO FATAL NO PIPELINE:")
        raise
    finally:
        logger.info("=" * 70)
        logger.info("Finalizando pipeline...")
        logger.info("=" * 70)


if __name__ == "__main__":
    main()
