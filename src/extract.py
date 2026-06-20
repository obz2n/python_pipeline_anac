import glob
import logging
from pathlib import Path

import chardet
import pandas as pd
from config import DATA_RAW_DIR, PATTERN_CSV, PATTERN_TXT

# ============================================================
# Logger do módulo
# ============================================================
logger = logging.getLogger(__name__)


# ============================================================
# Extração de dados
# ============================================================
def acessar_dados():
    """Retorna a lista de arquivos que casam com os padrões configurados.

    Observações:
    - Os caminhos retornados são ordenados para reprodutibilidade.
    - Não faz side-effect de configurar logging; apenas registra informações.
    """
    logger.info("Acessando dados em %s", DATA_RAW_DIR)
    arquivos = sorted(
        glob.glob(f"{DATA_RAW_DIR}/{PATTERN_CSV}")
        + glob.glob(f"{DATA_RAW_DIR}/{PATTERN_TXT}")
    )
    logger.info("Arquivos encontrados: %d", len(arquivos))
    if arquivos:
        for a in arquivos:
            try:
                tamanho = Path(a).stat().st_size
            except Exception:
                tamanho = "desconhecido"
            logger.debug("Arquivo: %s (bytes=%s)", a, tamanho)
    else:
        logger.warning("Nenhum arquivo encontrado em %s", DATA_RAW_DIR)

    return arquivos


def detectar_encoding(file_path: str, amostra_bytes: int = 50_000) -> str:
    """
    Detecta o encoding do arquivo usando chardet.
    Lê apenas os primeiros `amostra_bytes` bytes para ser eficiente em arquivos grandes.
    Retorna o encoding detectado ou 'utf-8' como padrão seguro.
    """
    with open(file_path, "rb") as f:
        amostra = f.read(amostra_bytes)

    resultado = chardet.detect(amostra)
    encoding = resultado.get("encoding") or "utf-8"
    confianca = resultado.get("confidence", 0)

    logger.debug(f"  Encoding detectado: '{encoding}' (confiança: {confianca:.0%})")

    # Se confiança baixa, usa cp1252 como padrão seguro para arquivos BR
    if confianca < 0.7:
        logger.debug("Confiança baixa — usando 'cp1252' como fallback seguro")
        return "cp1252"

    return encoding


def separar_chunks(df, chunk_size):
    """Divide um DataFrame em pedaços (chunks) de tamanho chunk_size.

    Retorna uma lista de DataFrames.
    """
    if df is None or df.shape[0] == 0:
        return []
    chunks = [df[i : i + chunk_size] for i in range(0, df.shape[0], chunk_size)]
    return chunks


def extrair_dados(arquivos, chunk_size=1000):
    """Extrai os dados de uma lista de arquivos e retorna a lista de chunks."""
    logger.info(
        "Iniciando extração de %d arquivo(s).", len(arquivos) if arquivos else 0
    )

    if not arquivos:
        logger.error("Nenhum arquivo fornecido para extração.")
        return []

    all_chunks = []
    for arquivo in arquivos:
        logger.info("Processando arquivo: %s", arquivo)
        try:
            df = pd.read_csv(arquivo, encoding="utf-8")

            chunks = separar_chunks(df, chunk_size)
            all_chunks.extend(chunks)
        except Exception as e:
            logger.error("Falha ao processar %s: %s", arquivo, e)

    logger.info("Extração finalizada. Total de chunks gerados: %d", len(all_chunks))
    return all_chunks
