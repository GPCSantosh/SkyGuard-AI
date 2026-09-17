"""Programmatic migration runner and database schema initializers for SkyGuard AI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

from backend.app.core.config import get_project_root, get_settings
from backend.app.core.logging import get_logger
from backend.app.db.models import Base

logger = get_logger("db_migrations")


def get_alembic_config(database_url: Optional[str] = None) -> Config:
    """Create configured Alembic Config object pointing to the repository alembic.ini."""
    root_dir = get_project_root()
    ini_path = root_dir / "alembic.ini"
    
    if not ini_path.exists():
        raise FileNotFoundError(f"alembic.ini not found at expected path: {ini_path}")

    cfg = Config(str(ini_path))
    db_url = database_url or get_settings().database_url
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.set_main_option("script_location", str(root_dir / "alembic"))
    return cfg


def run_db_migrations(database_url: Optional[str] = None) -> None:
    """Run all pending Alembic migrations up to head."""
    cfg = get_alembic_config(database_url)
    try:
        command.upgrade(cfg, "head")
        logger.info("Successfully executed database migrations to 'head'.")
    except Exception as e:
        logger.error("Alembic migration failed: %s", str(e), exc_info=True)
        raise


def init_db_schema(engine: Engine) -> None:
    """Initialize database schema directly using SQLAlchemy metadata (used for tests and memory DBs)."""
    Base.metadata.create_all(bind=engine)
    logger.info("Initialized schema via SQLAlchemy metadata create_all.")
