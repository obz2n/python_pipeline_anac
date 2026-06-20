import logging
from pathlib import Path

import chardet
import duckdb
import pandas as pd
from config import DATA_PROCESSED_PATH, ENCODINGS

# ============================================================
# Logger do módulo
# ============================================================
logger = logging.getLogger(__name__)


# ============================================================
# Extração de dados
# ============================================================
def detectar_encoding(file_path: Path, amostra_bytes: int = 50_000) -> str:
    """
    Detecta o encoding do arquivo usando chardet.
    Lê apenas os primeiros `amostra_bytes` bytes para ser eficiente em arquivos grandes.
    Retorna o encoding detectado ou 'cp1252' como padrão seguro para BR.
    """
    try:
        with open(file_path, "rb") as f:
            amostra = f.read(amostra_bytes)

        resultado = chardet.detect(amostra)
        encoding = resultado.get("encoding") or "utf-8"
        confianca = resultado.get("confidence", 0)

        logger.info(f"  Encoding detectado: '{encoding}' (confiança: {confianca:.0%})")

        # Se confiança baixa, usa cp1252 como padrão seguro para arquivos BR
        if confianca < 0.7:
            logger.debug("  Confiança baixa — usando 'cp1252' como fallback seguro")
            return "cp1252"

        return encoding
    except Exception as e:
        logger.warning(
            f"  Erro ao detectar encoding: {e}. Usando 'cp1252' como padrão."
        )
        return "cp1252"


def ler_arquivo_txt(file_path: Path) -> pd.DataFrame | None:
    """
    Lê um arquivo .txt da ANAC (CSV separado por ';').
    Tenta primeiro com chardet, depois percorre ENCODINGS.
    Retorna o DataFrame ou None em caso de falha total.
    """
    logger.info(f"Lendo: {file_path.name}")

    # Tentativa 1: encoding detectado automaticamente
    encoding_detectado = detectar_encoding(file_path)
    try:
        df = pd.read_csv(
            file_path, sep=";", encoding=encoding_detectado, low_memory=False
        )
        logger.info(
            f"  Lido com sucesso ({len(df):,} linhas, {len(df.columns)} colunas)"
        )
        return df
    except UnicodeDecodeError:
        logger.debug(
            f"  UnicodeDecodeError com '{encoding_detectado}' — percorrendo fallbacks..."
        )
    except Exception as e:
        logger.debug(f"  Erro ao ler com '{encoding_detectado}': {e}")

    # Tentativa 2: percorrer lista de fallback
    for encoding in ENCODINGS:
        if encoding == encoding_detectado:
            continue  # já tentou
        try:
            df = pd.read_csv(file_path, sep=";", encoding=encoding, low_memory=False)
            logger.info(
                f"  Lido com sucesso usando fallback '{encoding}' ({len(df):,} linhas)"
            )
            return df
        except UnicodeDecodeError:
            logger.debug(f"  UnicodeDecodeError com '{encoding}'")
            continue
        except Exception as e:
            logger.debug(f"  Erro inesperado com '{encoding}': {e}")
            continue

    # Se chegou aqui, falhou com todos os encodings
    logger.error(
        f"  Falha: não foi possível ler '{file_path.name}' com nenhum encoding testado"
    )
    return None


def processar_arquivos_txt(txt_files: list[Path] | list[str]) -> dict:
    """
    Orquestra a leitura de todos os .txt e a conversão para .parquet.
    Arquivos com falha são registrados e ignorados sem interromper o processo.
    Usa DuckDB para salvar em formato Parquet (mais eficiente para arquivos grandes).

    Retorna um dicionário com estatísticas: {'sucessos': int, 'falhas': int, 'falhos': list}
    """
    DATA_PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

    total = len(txt_files)
    sucessos = 0
    falhas = []

    logger.info(f"Iniciando processamento de {total} arquivo(s)...")

    for i, file in enumerate(txt_files, start=1):
        file_path = Path(file) if isinstance(file, str) else file
        logger.info(f"[{i}/{total}] Processando: {file_path.name}")

        df = ler_arquivo_txt(file_path)

        if df is None:
            falhas.append(file_path.name)
            logger.warning(f"  IGNORADO: '{file_path.name}' — não foi possível ler")
            continue

        # Salvar como Parquet usando DuckDB
        parquet_name = file_path.stem + ".parquet"
        parquet_path = DATA_PROCESSED_PATH / parquet_name

        try:
            # Converter DataFrame pandas para DuckDB e salvar como Parquet
            duckdb.from_df(df).write_parquet(str(parquet_path))
            logger.info(f"  Salvo em: {parquet_path.name}")
            sucessos += 1
        except Exception as e:
            logger.error(f"  Erro ao salvar parquet '{parquet_name}': {e}")
            falhas.append(file_path.name)

    # Resumo final
    logger.info("Processamento concluído.")
    logger.info(f"  Sucessos: {sucessos}/{total}")
    logger.info(f"  Falhas:   {len(falhas)}/{total}")
    if falhas:
        logger.warning("Arquivos com falha:")
        for nome in falhas:
            logger.warning(f"    - {nome}")

    return {
        "sucessos": sucessos,
        "falhas": len(falhas),
        "falhos": falhas,
    }


def carregar_parquet_duckdb(parquet_path: Path) -> duckdb.DuckDBPyRelation | None:
    """
    Carrega um arquivo Parquet usando DuckDB.
    Retorna uma relação DuckDB para consultas eficientes.
    Útil para análises e transformações sem carregar tudo na memória.
    """
    try:
        logger.info(f"Carregando Parquet com DuckDB: {parquet_path.name}")
        relacao = duckdb.read_parquet(str(parquet_path))
        logger.info(
            f"  Carregado: {relacao.shape[0]:,} linhas, {len(relacao.columns)} colunas"
        )
        return relacao
    except Exception as e:
        logger.error(f"Erro ao carregar {parquet_path.name}: {e}")
        return None
