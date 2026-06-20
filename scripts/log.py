import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import LOG_PATH

# ============================================================
# Configuração de logging centralizada
# ============================================================

pasta_logs = Path(LOG_PATH)
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
