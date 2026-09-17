"""Database engine, session management, connection pooling, and health observability."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import time
from typing import Any, Dict, Generator, Optional
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger("db_session")


class DatabaseHealthMetrics:
    """Tracks operational database connection and query metrics."""

    def __init__(self) -> None:
        self.connected: bool = False
        self.last_check_utc: Optional[str] = None
        self.reads_total: int = 0
        self.writes_total: int = 0
        self.write_failures: int = 0
        self.read_failures: int = 0
        self.transaction_failures: int = 0
        self.total_read_latency_ms: float = 0.0
        self.total_write_latency_ms: float = 0.0
        self.mean_read_latency_ms: float = 0.0
        self.mean_write_latency_ms: float = 0.0
        self.last_error: Optional[str] = None

    def record_read(self, latency_ms: float, success: bool = True, error: Optional[str] = None) -> None:
        self.reads_total += 1
        if success:
            self.total_read_latency_ms += latency_ms
            self.mean_read_latency_ms = round(self.total_read_latency_ms / max(1, self.reads_total - self.read_failures), 2)
        else:
            self.read_failures += 1
            self.last_error = error

    def record_write(self, latency_ms: float, success: bool = True, error: Optional[str] = None) -> None:
        self.writes_total += 1
        if success:
            self.total_write_latency_ms += latency_ms
            self.mean_write_latency_ms = round(self.total_write_latency_ms / max(1, self.writes_total - self.write_failures), 2)
        else:
            self.write_failures += 1
            self.transaction_failures += 1
            self.last_error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "last_check_utc": self.last_check_utc,
            "reads_total": self.reads_total,
            "writes_total": self.writes_total,
            "write_failures": self.write_failures,
            "read_failures": self.read_failures,
            "transaction_failures": self.transaction_failures,
            "mean_read_latency_ms": self.mean_read_latency_ms,
            "mean_write_latency_ms": self.mean_write_latency_ms,
            "last_error": self.last_error,
        }


def _sqlite_on_connect(dbapi_con, con_record) -> None:
    """Enable WAL mode and foreign key enforcement on SQLite."""
    cursor = dbapi_con.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.close()


def create_skyguard_engine(database_url: Optional[str] = None) -> Engine:
    """Create configured SQLAlchemy Engine supporting PostgreSQL and SQLite."""
    settings = get_settings()
    url = database_url or settings.database_url

    if url.startswith("sqlite"):
        # Ensure parent directory exists for file-based SQLite
        if not url.startswith("sqlite:///:memory:") and "///" in url:
            db_path_str = url.split("///")[-1]
            db_path = Path(db_path_str)
            db_path.parent.mkdir(parents=True, exist_ok=True)

        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
        event.listen(engine, "connect", _sqlite_on_connect)
        return engine

    # PostgreSQL / Other Relational Targets
    engine = create_engine(
        url,
        pool_size=settings.storage.pool_size,
        max_overflow=settings.storage.max_overflow,
        pool_timeout=settings.storage.pool_timeout_seconds,
        pool_pre_ping=True,
        echo=False,
    )
    return engine


class DatabaseSessionManager:
    """Manages database connection pool, sessions, and operational metrics."""

    def __init__(self, database_url: Optional[str] = None, engine: Optional[Engine] = None) -> None:
        self.database_url = database_url or get_settings().database_url
        self.engine = engine or create_skyguard_engine(self.database_url)
        self.session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False,
        )
        self.metrics = DatabaseHealthMetrics()
        self.check_connection()

    def check_connection(self) -> bool:
        """Verify database connectivity with a lightweight probe."""
        t0 = time.perf_counter()
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.metrics.connected = True
            self.metrics.last_check_utc = datetime.now(timezone.utc).isoformat()
            self.metrics.last_error = None
            return True
        except Exception as e:
            self.metrics.connected = False
            self.metrics.last_check_utc = datetime.now(timezone.utc).isoformat()
            self.metrics.last_error = str(e)
            logger.error("Database connection check failed: %s", str(e))
            return False

    def check_health(self) -> Dict[str, Any]:
        """Verify database connectivity and return health report dictionary."""
        is_conn = self.check_connection()
        return {
            "status": "healthy" if is_conn else "unreachable",
            "dialect": self.engine.dialect.name,
            "connected": is_conn,
            "metrics": self.metrics.to_dict(),
        }

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provide a transactional database session context."""
        sess: Session = self.session_factory()
        t_start = time.perf_counter()
        try:
            yield sess
            sess.commit()
            latency = (time.perf_counter() - t_start) * 1000.0
            self.metrics.record_write(latency, success=True)
        except Exception as e:
            sess.rollback()
            latency = (time.perf_counter() - t_start) * 1000.0
            self.metrics.record_write(latency, success=False, error=str(e))
            logger.error("Database transaction rolled back due to error: %s", str(e))
            raise
        finally:
            sess.close()

    def close(self) -> None:
        """Dispose of the engine connection pool."""
        self.engine.dispose()
        self.metrics.connected = False


_session_manager: Optional[DatabaseSessionManager] = None


def get_session_manager(database_url: Optional[str] = None, force_recreate: bool = False) -> DatabaseSessionManager:
    """Get or create singleton DatabaseSessionManager."""
    global _session_manager
    if _session_manager is None or force_recreate:
        _session_manager = DatabaseSessionManager(database_url=database_url)
    return _session_manager
