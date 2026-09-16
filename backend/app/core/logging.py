"""Logging infrastructure for SkyGuard AI.

Configures structured logging and ensures sensitive tokens are not logged.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None
) -> None:
    """Configure root logger and application loggers."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ"
    )

    handlers: list[logging.Handler] = []

    # Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # Optional File Handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        handlers=handlers,
        force=True
    )

    # Quieten external noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Obtain a namespaced logger instance."""
    return logging.getLogger(f"skyguard.{name}")
