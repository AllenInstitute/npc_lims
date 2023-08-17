from __future__ import annotations

from collections.abc import Iterable
from typing import Any, ClassVar, Protocol

import npc_session
from typing_extensions import Self


class SupportsToDB(Protocol):
    table: ClassVar[str]

    def to_db(self) -> dict[str, str | int | float | None]:
        ...


class SupportsFromDB(Protocol):
    table: ClassVar[str]

    @classmethod
    def from_db(cls, row: dict[str, str | int | float | None]) -> Self:
        ...


class RecordDB(Protocol):
    def add_records(self, records: Iterable[SupportsToDB], **kwargs: str | int | float | None) -> None:
        ...

    def get_records(
        self,
        cls: type[SupportsFromDB],
        **kwargs: str | int | float | None,
    ) -> tuple[SupportsFromDB, ...]:
        ...

    def delete_records(self, *rows: SupportsToDB, **kwargs: str | int | float | None) -> None:
        ...
