# ========================
# Diretórios
# ========================
DATA_RAW_PATH = "python_pipeline_anac/data/raw"
DATA_PROCESSED_PATH = "python_pipeline_anac/data/processed"
LOG_PATH = "python_pipeline_anac/logs/"
GLOB_PATH = str(DATA_PROCESSED_PATH)

CHUNKSIZE = 50_000  # linhas por batch no INSERT — evita estourar memória

# ========================
# Banco de dados
# ========================
SCHEMA_NAME_RAW = "raw"
TABLE_NAME_RAW = "raw_anac"
PATTERN_CSV = "*.csv"
PATTERN_TXT = "*.txt"
PATTERN_PARQUET = "*.parquet"

ENCODINGS = [
    "utf-8",
    "utf-8-sig",  # UTF-8 com BOM — comum em exports do Excel
    "cp1252",  # Windows-1252 — padrão em sistemas Windows BR
    "iso-8859-1",  # Latin-1 — arquivos legados
    "cp860",  # MS-DOS Portuguese
    "latin-1",
    "utf-16",
    "MacTurkish",
]
