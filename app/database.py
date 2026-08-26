"""Small MariaDB connection layer for FarmPi."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Sequence

import pymysql
from pymysql.cursors import DictCursor


class DatabaseUnavailable(RuntimeError):
    """Raised when FarmPi cannot use its configured MariaDB database."""


@dataclass(frozen=True)
class DatabaseSettings:
    """MariaDB connection settings loaded from the service environment."""

    host: str
    port: int
    name: str
    user: str
    password: str
    connect_timeout: int = 3

    @classmethod
    def from_environment(cls) -> "DatabaseSettings":
        password = os.getenv("FARMPI_DB_PASSWORD", "")
        if not password:
            raise DatabaseUnavailable(
                "FARMPI_DB_PASSWORD is not configured. Run scripts/setup-database."
            )

        try:
            port = int(os.getenv("FARMPI_DB_PORT", "3306"))
        except ValueError as exc:
            raise DatabaseUnavailable("FARMPI_DB_PORT is invalid.") from exc

        return cls(
            host=os.getenv("FARMPI_DB_HOST", "127.0.0.1"),
            port=port,
            name=os.getenv("FARMPI_DB_NAME", "farmpi"),
            user=os.getenv("FARMPI_DB_USER", "farmpi"),
            password=password,
        )


def _connect() -> pymysql.connections.Connection:
    settings = DatabaseSettings.from_environment()

    try:
        return pymysql.connect(
            host=settings.host,
            port=settings.port,
            user=settings.user,
            password=settings.password,
            database=settings.name,
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=True,
            connect_timeout=settings.connect_timeout,
            read_timeout=5,
            write_timeout=5,
        )
    except pymysql.MySQLError as exc:
        raise DatabaseUnavailable("Unable to connect to the FarmPi MariaDB database.") from exc


def fetch_all(sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    """Run a read-only query and return all rows as dictionaries."""
    connection = _connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())
    except pymysql.MySQLError as exc:
        raise DatabaseUnavailable("FarmPi database query failed.") from exc
    finally:
        connection.close()


def ping_database() -> bool:
    """Return True when MariaDB is reachable and the FarmPi database can be selected."""
    connection = _connect()
    try:
        connection.ping(reconnect=False)
        return True
    except pymysql.MySQLError as exc:
        raise DatabaseUnavailable("FarmPi database health check failed.") from exc
    finally:
        connection.close()
