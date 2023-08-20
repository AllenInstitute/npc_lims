#!/usr/bin/env python

from __future__ import annotations

import abc
import datetime
import functools
import os
import pathlib
import sqlite3
import tempfile
from collections.abc import Iterable
from typing import Any, ClassVar

import pydbhub.dbhub as pydbhub
import upath

import npc_lims.metadata.types as types

DBHUB_API_KEY = os.getenv("DBHUB_API_KEY")

DEFAULT_BACKUP_PATH = upath.UPath("s3://aind-scratch-data/ben.hardcastle/db-backups")


class SqliteRecordDB:
    """Base class for sqlite database storing records."""

    db_name: ClassVar[str]

    schema_string_or_path: ClassVar[str | upath.UPath] = (
        upath.UPath(__file__).parent / "nwb.sql"
    )
    """Schema as a string, or path to .sql file containing schema."""

    backup_path: ClassVar[upath.UPath] = DEFAULT_BACKUP_PATH

    def __init__(self, *args, **kwargs) -> None:
        pass

    @abc.abstractmethod
    def create(self) -> None:
        ...

    @abc.abstractmethod
    def query(self, query: str) -> tuple[dict[str, Any], ...] | None:
        ...

    @abc.abstractmethod
    def execute(self, query: str) -> None:
        ...

    @property
    @abc.abstractmethod
    def serialized(self) -> bytes:
        ...

    @functools.cached_property
    def schema(self) -> str:
        _path = upath.UPath(self.schema_string_or_path)
        if _path.is_file():
            return _path.read_text()
        return str(self.schema_string_or_path)

    def backup(self) -> None:
        """Backup database to s3. Requires write permissions."""
        timestamp = datetime.datetime.now().isoformat()
        self.backup_path.mkdir(parents=True, exist_ok=True)
        backup_file = self.backup_path / f"{self.db_name}.{timestamp}"
        backup_file.write_bytes(self.serialized)

    def insert(self, table: str, *rows: dict[str, Any]) -> None:
        if not all(v.keys() == rows[0].keys() for v in rows):
            raise ValueError("All rows must have the same keys (column names)")
        statement = f"INSERT INTO {table} ({', '.join(rows[0].keys())}) VALUES "
        for row in rows:
            statement += f"\n\t({', '.join(repr(_) if _ is not None else 'NULL' for _ in row.values())}),"
        statement = statement[:-1] + " ON CONFLICT DO NOTHING;"

        self.execute(statement)

    def add_records(
        self, *rows: types.SupportsDB, **kwargs: str | int | float | None
    ) -> None:
        table = rows[0].table
        self.insert(table, *(row.db for row in rows))

    def get_records(
        self,
        cls: type[types.SupportsFromDB],
        **kwargs: str | int | float | None,
    ) -> tuple[types.SupportsFromDB, ...]:
        table = cls.table
        query = f"SELECT * FROM {table!r}"
        extra = []
        for k, v in kwargs.items():
            extra += [f"{k} = {repr(v)}"] if v is not None else [f"{k} IS NULL"]
        if extra:
            query += f" WHERE ({' AND '.join(extra)})"

        rows = self.query(query)
        if not rows:
            return ()
        instances = []
        for row in rows:
            instances.append(cls.from_db(row))
        return tuple(instances)

    def delete_records(
        self, *rows: types.SupportsDB, **kwargs: str | int | float | None
    ) -> None:
        table = rows[0].table
        statement = f"DELETE FROM {table} WHERE EXISTS (SELECT * FROM {table} WHERE "
        for row in rows:
            statement += f"\n\t({' AND '.join(f'{k} = {repr(v)}' for k, v in row.db.items() if v)}) OR"
        statement = statement[:-3] + ");"
        self.execute(statement)


class SqliteLocalDB(SqliteRecordDB):
    backup_path = DEFAULT_BACKUP_PATH / "local"

    def __init__(self, *args, **kwargs) -> None:
        self.connection = sqlite3.connect(self.path)

        def dict_factory(cursor, row):
            fields = [column[0] for column in cursor.description]
            return dict(zip(fields, row))

        self.connection.row_factory = dict_factory
        self.cursor = self.connection.cursor()

    @property
    @abc.abstractmethod
    def path(self) -> pathlib.Path | upath.UPath:
        raise NotImplementedError

    def create(self) -> None:
        self.execute(self.schema)

    def query(self, query: str) -> tuple[dict[str, Any], ...] | None:
        return tuple(self.cursor.execute(query).fetchall())

    def execute(self, query: str) -> None:
        self.cursor.execute(query)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()


class SqliteDBHub(SqliteRecordDB):
    """Base class for sqlite database on dbhub.io."""

    db_name: ClassVar[str]
    db_owner: ClassVar[str] = "svc_neuropix"
    backup_path: ClassVar[upath.UPath] = DEFAULT_BACKUP_PATH / "dbhub"

    @functools.cached_property
    def connection(self) -> pydbhub.Dbhub:
        return pydbhub.Dbhub(
            DBHUB_API_KEY, db_name=self.db_name, db_owner=self.db_owner
        )

    @property
    def url(self) -> str:
        return f"https://dbhub.io/{self.db_owner}/{self.db_name}"

    def __init__(self, *args, **kwargs) -> None:
        try:
            self.test()
        except LookupError:
            self.upload()

    def test(self) -> None:
        """Test connection to dbhub and existence of db."""
        response = self.connection.Databases(live=True)  # raises if API key is invalid
        if response[1] and isinstance(response[1], dict):
            raise AssertionError(response[1].get("error", "Unknown error"))
        assert response[0] is not None
        if self.db_name not in response[0]:
            raise LookupError(
                f"Database {self.db_name} not found on dbhub.io (only checking live databases for {self.db_owner})"
            )

    @property
    def serialized(self) -> bytes:
        return bytes(self.connection.Download()[0])  # type: ignore[arg-type]

    def upload(self) -> None:
        """Create from schema and upload as a live database to dbhub.io."""
        temp: str = tempfile.mkstemp()[1]
        db = sqlite3.connect(temp)
        db.executescript(self.schema)
        db.commit()
        info = pydbhub.UploadInformation(
            live=True,
            public=True,
        )
        self.connection.Upload(db_name=self.db_name, info=info, db_bytes=pathlib.Path(temp).read_bytes())  # type: ignore[arg-type]

    def create(self) -> None:
        self.execute(self.schema)

    def query(self, query: str) -> tuple[dict[str, Any], ...] | None:
        response = self.connection.Query(query)
        if response[1] and isinstance(response[1], dict):
            raise LookupError(response[1].get("error", "Unknown error"))
        if not response[0]:
            return None
        results: Iterable[dict[str, Any]] = response[0]
        return tuple(results)

    def execute(self, query: str) -> None:
        response = self.connection.Execute(query)
        if response[1] and isinstance(response[1], dict):
            raise RuntimeError(response[1].get("error", "Unknown error"))


class TestDBHub(SqliteDBHub):
    """Test database on dbhub.io.

    >>> db = TestDBHub()
    >>> db.execute("DROP TABLE IF EXISTS test;")
    >>> db.create()
    >>> db.insert("test", {'id': 1, 'name': 'one'}, {'id': 2, 'name': 'two'})
    >>> db.query("SELECT * FROM test;")
    ({'id': 1, 'name': 'one'}, {'id': 2, 'name': 'two'})
    >>> _ = db.execute("DROP TABLE test;")
    """

    db_name = "test.db"
    schema_string_or_path = (
        "CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT);"
    )


class TestLocalDB(SqliteLocalDB):
    """Test database on local file.

    >>> db = TestLocalDB()
    >>> db.execute("DROP TABLE IF EXISTS test;")
    >>> db.create()
    >>> db.insert("test", {'id': 1, 'name': 'one'}, {'id': 2, 'name': 'two'})
    >>> db.query("SELECT * FROM test;")
    ({'id': 1, 'name': 'one'}, {'id': 2, 'name': 'two'})
    >>> _ = db.execute("DROP TABLE test;")
    >>> db.close()
    >>> db.path.unlink()
    """

    db_name = "test.sqlite"
    path = upath.UPath(__file__).parent / db_name
    schema_string_or_path = (
        "CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT);"
    )


class NWBSqliteDBHub(SqliteDBHub):
    db_name = "nwb.db"


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
