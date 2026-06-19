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


def separar_chunks(df, chunk_size):
    """Divide um DataFrame em pedaços (chunks) de tamanho chunk_size.

    Retorna uma lista de DataFrames.
    """
    if df is None or df.shape[0] == 0:
        return []
    chunks = [df[i : i + chunk_size] for i in range(0, df.shape[0], chunk_size)]
    return chunks


def tentar_ler_csv(path, encodings):
    """Tenta ler um CSV usando várias codificações em fallback.

    Retorna o DataFrame lido ou levanta a última exceção se todas falharem.
    """
    last_exc = None
    for enc in encodings:
        try:
            logger.debug("Tentando ler %s com encoding=%s", path, enc)
            df = pd.read_csv(path, encoding=enc)
            return df
        except Exception as e:
            logger.debug("Falha ao ler %s com encoding=%s: %s", path, enc, e)
            last_exc = e
    # Se chegou aqui, re-raise para o chamador lidar
    raise last_exc


def extrair_dados(arquivos, chunk_size=1000):
    """Extrai os dados de uma lista de arquivos e retorna a lista de chunks.

    Para cada arquivo tenta detectar a codificação com chardet e faz fallback
    para encodings comuns se a leitura falhar.
    """
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
            # Detect encoding
            with open(arquivo, "rb") as f:
                raw = f.read()
            resultado = chardet.detect(raw)
            enc = resultado.get("encoding")
            logger.info(
                "Codificação detectada para %s: %s (confiança=%.2f)",
                arquivo,
                enc,
                resultado.get("confidence", 0.0),
            )

            # Lista de encodings para tentar: detectada primeiro, depois fallbacks
            tried_encodings = [enc] if enc else []
            for fallback in ("utf-8", "latin1", "cp1252"):
                if fallback not in tried_encodings:
                    tried_encodings.append(fallback)

            df = tentar_ler_csv(arquivo, tried_encodings)

            logger.info(
                "Dados lidos de %s: %d linhas, %d colunas",
                arquivo,
                df.shape[0],
                df.shape[1],
            )
            logger.debug("Colunas: %s", df.columns.tolist())

            chunks = separar_chunks(df, chunk_size)
            logger.info(
                "Gerados %d chunk(s) a partir de %s (chunk_size=%d)",
                len(chunks),
                arquivo,
                chunk_size,
            )
            all_chunks.extend(chunks)
        except Exception:
            logger.exception("Erro ao processar o arquivo: %s", arquivo)
            # Continua para o próximo arquivo em vez de falhar todo o pipeline
            continue

    logger.info("Extração finalizada. Total de chunks gerados: %d", len(all_chunks))
    return all_chunks
