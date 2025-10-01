"""Local file-backed database helper utilities.

This module exposes :class:`LocalFileDatabase`, a thin wrapper over
:mod:`sqlite3` that persists data to a database stored on the local
filesystem.  The goal is to make it straightforward to record arbitrary
Python dictionaries in situations where a lightweight, embedded storage
solution is sufficient.

Example
-------

>>> db = LocalFileDatabase("my-data.db")
>>> db.record({"temperature": 21.5, "unit": "C"})
1
>>> db.fetch_records()
[{'id': 1, 'data': {'temperature': 21.5, 'unit': 'C'}, ... }]

The implementation keeps the schema intentionally small – every record is
stored as JSON alongside its creation timestamp.  The timestamp uses
``datetime.isoformat`` and is normalised to UTC by default.  Consumers can
limit or page through the stored entries using :meth:`fetch_records`.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Union

JsonMapping = Mapping[str, Any]


class LocalFileDatabase:
    """Persist structured data inside a SQLite database stored on disk.

    Parameters
    ----------
    path:
        Filesystem path to the SQLite database file.  Parent directories are
        created automatically if they do not exist yet.
    """

    def __init__(self, path: Union[str, Path] = "data.db") -> None:
        self._path = Path(path).expanduser()
        self._ensure_parent_directory()
        self._initialise()

    @property
    def path(self) -> Path:
        """Return the path of the backing SQLite database file."""

        return self._path

    def record(
        self,
        data: JsonMapping,
        *,
        created_at: Optional[datetime] = None,
    ) -> int:
        """Insert a new record into the database.

        Parameters
        ----------
        data:
            Mapping of JSON-serialisable values that should be persisted.
        created_at:
            Optional timestamp.  When omitted the current UTC timestamp is
            used.

        Returns
        -------
        int
            The numeric identifier of the newly inserted row.
        """

        if not isinstance(data, Mapping):  # type: ignore[arg-type]
            raise TypeError("data must be a mapping")

        payload = json.dumps(data, default=_json_default, ensure_ascii=False)
        timestamp = _normalise_timestamp(created_at)

        with self._connection() as connection:
            cursor = connection.execute(
                "INSERT INTO records (payload, created_at) VALUES (?, ?)",
                (payload, timestamp),
            )
            return int(cursor.lastrowid)

    def fetch_records(
        self,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
        descending: bool = False,
    ) -> List[Dict[str, Any]]:
        """Return stored records as a list of dictionaries.

        Parameters
        ----------
        limit:
            Maximum number of rows to return.  ``None`` returns all rows.
        offset:
            Number of initial rows to skip.  Useful for pagination.
        descending:
            When ``True`` rows are returned in reverse chronological order.
        """

        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative or None")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        order = "DESC" if descending else "ASC"
        query = f"SELECT id, payload, created_at FROM records ORDER BY id {order}"
        parameters: List[Union[int, str]] = []
        if limit is not None or offset:
            limit_value = limit if limit is not None else -1
            query += " LIMIT ? OFFSET ?"
            parameters.extend([limit_value, offset])

        with self._connection() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(query, parameters)
            return [
                {
                    "id": row["id"],
                    "data": json.loads(row["payload"]),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def clear(self) -> None:
        """Delete all stored records from the database."""

        with self._connection() as connection:
            connection.execute("DELETE FROM records")

    def count(self) -> int:
        """Return the total number of stored records."""

        with self._connection() as connection:
            cursor = connection.execute("SELECT COUNT(*) FROM records")
            (count,) = cursor.fetchone()  # type: ignore[misc]
            return int(count)

    def _ensure_parent_directory(self) -> None:
        parent = self._path.resolve().parent
        parent.mkdir(parents=True, exist_ok=True)

    def _initialise(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self._path))
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()


def _json_default(value: Any) -> Any:
    """Best-effort JSON serialization helper.

    ``json.dumps`` calls the ``default`` callback for unsupported objects.
    ``datetime`` instances are serialised using :meth:`datetime.isoformat`,
    :class:`Path` objects use :func:`str`, and everything else is passed through
    unchanged which lets :mod:`json` raise a ``TypeError`` for unsupported
    values.
    """

    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _normalise_timestamp(timestamp: Optional[datetime]) -> str:
    """Return an ISO-8601 timestamp string.

    ``None`` values fall back to the current time in UTC.
    """

    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).isoformat()

