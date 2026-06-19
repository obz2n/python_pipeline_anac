import glob
import logging

import chardet
import pandas as pd
from config import DATA_RAW_DIR, PATTERN_CSV, PATTERN_TXT

# ============================================================
# Configuração de logging
# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Iniciando extração de dados...")

# ============================================================
# Extração de dados
# ============================================================


def acessar_dados():
    logger.info("Acessando dados...")
    arquivos = glob.glob(f"{DATA_RAW_DIR}/{PATTERN_CSV}") + glob.glob(
        f"{DATA_RAW_DIR}/{PATTERN_TXT}"
    )
    logger.info(f"Arquivos encontrados: {arquivos}")
    print(f"Quantidade de arquivos: {len(arquivos)}")
    return arquivos


def separar_chunks(df, chunk_size):
    chunks = [df[i : i + chunk_size] for i in range(0, df.shape[0], chunk_size)]
    return chunks


def extrair_dados(arquivos, chunk_size):
    logger.info("Extraindo dados...")
    df = pd.DataFrame()
    for arquivo in arquivos:
        logger.info(f"Extraindo dados do arquivo: {arquivo}")
        with open(arquivo, "rb") as f:
            resultado = chardet.detect(f.read())
        logger.info(f"Codificação detectada: {resultado['encoding']}")
        df = pd.read_csv(arquivo, encoding=resultado["encoding"])
        logger.info(f"Dados extraídos: {df.head()}")
        chunks = separar_chunks(df, chunk_size)
        return chunks
    else:
        logger.error("Nenhum arquivo encontrado.")
        return None
