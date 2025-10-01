# codex

This repository provides a lightweight helper for persisting structured data to
an on-disk SQLite database.  The :class:`LocalFileDatabase` utility handles
initialising the database file, inserting JSON-serialised payloads, fetching
records, and clearing stored entries.

## Quick start

```python
from local_file_database import LocalFileDatabase

# create (or connect to) the local SQLite database
storage = LocalFileDatabase("measurements.sqlite")

# store some structured data
storage.record({"temperature": 21.5, "unit": "C"})

# retrieve all stored rows
for record in storage.fetch_records():
    print(record)
```

Run the automated test-suite with:

```bash
pytest
```
