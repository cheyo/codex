from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from local_file_database import LocalFileDatabase


def test_record_and_fetch_roundtrip(tmp_path):
    db_path = tmp_path / "records.db"
    database = LocalFileDatabase(db_path)

    first_id = database.record({"temperature": 21.5, "unit": "C"})
    second_timestamp = datetime(2020, 1, 1, tzinfo=timezone.utc)
    second_id = database.record({"humidity": 0.58}, created_at=second_timestamp)

    records = database.fetch_records()
    assert [record["id"] for record in records] == [first_id, second_id]
    assert records[0]["data"] == {"temperature": 21.5, "unit": "C"}
    assert records[1]["created_at"].startswith("2020-01-01T00:00:00+00:00")

    assert db_path.exists(), "database file should be created on disk"


def test_fetch_with_limit_and_offset(tmp_path):
    database = LocalFileDatabase(tmp_path / "db.sqlite")

    for index in range(5):
        database.record({"index": index})

    limited = database.fetch_records(limit=2)
    assert len(limited) == 2
    assert [record["data"]["index"] for record in limited] == [0, 1]

    paged = database.fetch_records(limit=2, offset=2)
    assert len(paged) == 2
    assert [record["data"]["index"] for record in paged] == [2, 3]

    descending = database.fetch_records(descending=True)
    assert [record["data"]["index"] for record in descending] == [4, 3, 2, 1, 0]


def test_clear_and_count(tmp_path):
    database = LocalFileDatabase(tmp_path / "storage.sqlite")

    database.record({"value": 1})
    database.record({"value": 2})

    assert database.count() == 2

    database.clear()
    assert database.count() == 0
    assert database.fetch_records() == []


def test_record_requires_mapping(tmp_path):
    database = LocalFileDatabase(tmp_path / "db.sqlite")

    with pytest.raises(TypeError):
        database.record([("key", "value")])  # type: ignore[arg-type]


def test_custom_json_serialisation(tmp_path):
    database = LocalFileDatabase(tmp_path / "custom.sqlite")

    timestamp = datetime(2023, 3, 8, tzinfo=timezone.utc)
    payload_path = Path("/tmp/data.txt")

    record_id = database.record({
        "timestamp": timestamp,
        "path": payload_path,
    })

    [record] = database.fetch_records()
    assert record["id"] == record_id
    assert record["data"]["timestamp"] == timestamp.isoformat()
    assert record["data"]["path"] == str(payload_path)
