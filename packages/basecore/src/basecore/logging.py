"""
Configuração de Logging

Configura logging padrão para a aplicação.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging():
    """
    Configura logging padrão para a aplicação.

    - Nível: INFO em produção, DEBUG em desenvolvimento
    - Formato: Texto simples com contexto
    - Handler: Console e arquivo (rotativo)
    """
    # Cria diretório de logs se não existir
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configura formato
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)d"
    )

    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.INFO)

    # Handler para arquivo (rotativo, max 10MB, mantém 5 backups)
    file_handler = RotatingFileHandler(
        "logs/app.log", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.INFO)

    # Configura logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Configura loggers específicos
    logging.getLogger("app").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)  # Reduz logs de SQL

    return root_logger

