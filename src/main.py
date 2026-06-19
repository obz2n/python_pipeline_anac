import logging

from config import LOG_PATH
from extraction import acessar_dados, extrair_dados

# ============================================================
# Execução do pipeline
# ============================================================

logging.basicConfig(filename=LOG_PATH, level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# Etapa 1: Extração de dados
# ============================================================
logger.info("Iniciando extração de dados.")
arquivos = acessar_dados()
extrair_dados(arquivos, chunk_size=1000)
logger.info("Extração concluída.")


# ============================================================
# Etapa 2: Carregamento de dados
# ============================================================
logger.info("Iniciando carregamento de dados.")

logger.info("Carregamento concluído.")


# ============================================================
# Execução do pipeline
# ============================================================
if __name__ == "__main__":
    logger.info("Iniciando execução do pipeline.")

    logger.info("Pipeline concluído.")
