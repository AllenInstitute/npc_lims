from __future__ import annotations

from collections.abc import Iterable
from typing import ClassVar, Protocol

from typing_extensions import Self


class SupportsDB(Protocol):
    table: ClassVar[str]

    @property
    def db(self) -> dict[str, str | int | float | None]: ...


class SupportsFromDB(Protocol):
    table: ClassVar[str]

    @classmethod
    def from_db(cls, row: dict[str, str | int | float | None]) -> Self: ...


class RecordDB(Protocol):
    def add_records(
        self, records: Iterable[SupportsDB], **kwargs: str | int | float | None
    ) -> None: ...

    def get_records(
        self,
        cls: type[SupportsFromDB],
        **kwargs: str | int | float | None,
    ) -> tuple[SupportsFromDB, ...]: ...

    def delete_records(
        self, *rows: SupportsDB, **kwargs: str | int | float | None
    ) -> None: ...


class SupportsNWB(Protocol):
    @property
    def nwb(self) -> dict[str, str | int | float | None]: ...


class SupportsToNWB(Protocol):
    def to_nwb(self, nwb) -> None: ...
