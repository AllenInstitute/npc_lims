from typing import ClassVar, Iterable, Protocol, Type
from typing_extensions import Self

import npc_session

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
    def add_records(self, records: Iterable[SupportsToDB]) -> None:
        ...
    
    def get_records(
        self, 
        cls: Type[SupportsFromDB],
        session: str | npc_session.SessionRecord | None = None,
        subject: str | npc_session.SubjectRecord | None = None,
        ) -> tuple[SupportsFromDB, ...]:
        ...