#!/usr/bin/env python

from __future__ import annotations
import datetime
import io


import os
import pathlib
import functools
import sqlite3
import tempfile
from typing import Any, ClassVar

import pydbhub.dbhub as dbhub
import upath

API_KEY = os.getenv("DBHUB_API_KEY")

DEFAULT_BACKUP_PATH = upath.UPath(
    's3://aind-scratch-data/ben.hardcastle/db-backups'
)

class SqliteDBHub:
    """Base class for sqlite database on dbhub.io.

    """
    schema_string_or_path: ClassVar[str | upath.UPath]
    """Schema as a string, or path to .sql file containing schema."""
    db_name: ClassVar[str]
    
    db_owner: ClassVar[str] = "svc_neuropix"
    backup_path: ClassVar[upath.UPath] = DEFAULT_BACKUP_PATH
    
    @functools.cached_property
    def schema(self) -> str:
        _path = upath.UPath(self.schema_string_or_path)
        if _path.is_file():
            return _path.read_text()
        return str(self.schema_string_or_path)
            
    @functools.cached_property
    def connection(self) -> dbhub.Dbhub:
        return dbhub.Dbhub(API_KEY, db_name=self.db_name, db_owner=self.db_owner)

    @property
    def url(self) -> str:
        return f"https://dbhub.io/{self.db_owner}/{self.db_name}"
    
    def __init__(self) -> None:
        try:
            self.test()
        except LookupError:
            self.upload()
            
    def test(self) -> None:
        """Test connection to dbhub and existence of db."""
        response = self.connection.Databases(live=True) # raises if API key is invalid
        if response[1] and isinstance(response[1], dict):
            raise AssertionError(response[1].get("error", "Unknown error"))
        if self.db_name not in response[0]:
            raise LookupError(f"Database {self.db_name} not found on dbhub.io (only checking live databases for {self.db_owner})")
    
    def backup(self) -> None:
        """Backup database to s3. Requires write permissions."""
        timestamp = datetime.datetime.now().isoformat()
        self.backup_path.mkdir(parents=True, exist_ok=True)
        backup_file = self.backup_path / f"{self.db_name}.{timestamp}"
        backup_file.write_bytes(self.connection.Download()[0]) # type: ignore
        
        
    def upload(self) -> None:
        """Create from schema and upload as a live database to dbhub.io."""
        temp: str = tempfile.mkstemp()[1]
        db = sqlite3.connect(temp)
        db.executescript(self.schema)
        db.commit()
        info = dbhub.UploadInformation(
            live=True,
            public=True,
        )
        self.connection.Upload(db_name=self.db_name, info=info, db_bytes=pathlib.Path(temp).read_bytes()) # type: ignore

    def create(self) -> None:
        self.execute(self.schema)
    
    def query(self, query: str) -> list[dict[str, Any]] | None:
        response = self.connection.Query(query)
        if response[1] and isinstance(response[1], dict):
            raise LookupError(response[1].get("error", "Unknown error"))
        return self.connection.Query(query)[0]

    def execute(self, query: str) -> None:
        response = self.connection.Execute(query)
        if response[1] and isinstance(response[1], dict):
            raise RuntimeError(response[1].get("error", "Unknown error"))
    
    def insert(self, table: str, *rows: dict[str, Any]) -> None:
        
        if not all(v.keys() == rows[0].keys() for v in rows):
            raise ValueError("All rows must have the same keys (column names)")
        statement = (
            f"INSERT INTO {table} ({', '.join(rows[0].keys())}) VALUES "
        )
        for row in rows:
            statement += f"\n\t({', '.join(repr(_) for _ in row.values())}),"
        statement = statement[:-1] + ";"
        
        self.execute(statement)


class TestDB(SqliteDBHub):
    """Test database on dbhub.io.
    
    >>> db = TestDB()
    >>> db.execute("DROP TABLE IF EXISTS test;")
    >>> db.create()
    >>> db.insert("test", {'id': 1, 'name': 'one'}, {'id': 2, 'name': 'two'})
    >>> db.query("SELECT * FROM test;")
    [{'id': 1, 'name': 'one'}, {'id': 2, 'name': 'two'}]
    >>> _ = db.execute("DROP TABLE test;")
    """
    db_name = "test.db"
    schema_string_or_path = "CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT);"
    
    
class NWBSqliteDBHub(SqliteDBHub):
    db_name = "nwb.db"
    schema_string_or_path = upath.UPath(__file__).parent / "nwb.sql"


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
