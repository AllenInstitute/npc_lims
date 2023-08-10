"""
Protocols (interfaces) that define the required methods for jobs and
job-queues, and types for static analysis (mypy).
"""
from __future__ import annotations

import abc
import datetime
import typing
from typing import Mapping, Protocol, TypeVar, Union

from typing_extensions import TypeAlias

import npc_session


JobArgs: TypeAlias = Union[str, int, float, None]
"""Types of value that can be stored - mainly for compatibility with redis/sqlite3 types."""

JobKwargs: TypeAlias = Mapping[str, JobArgs]
"""Key:value pairs of job attributes.
For a job stored in sqlite, these would correspond to column-name:value pairs.
"""

JobT = TypeVar("JobT", bound="Job")
"""TypeVar with upper-bound `Job`."""

JobQueueT = TypeVar("JobQueueT", bound="JobQueue")
"""TypeVar with upper-bound `JobQueue`."""


@typing.runtime_checkable
class Job(Protocol):
    """Base class for jobs. The only required attribute is `session`, to
    match a job with a session. All other fields can be set to None."""

    def __init__(self, session: npc_lims.SessionRecord, **kwargs: JobArgs) -> None:
        """Create a new job."""

    @property
    @abc.abstractmethod
    def session(self) -> str | npc_lims.SessionRecord:
        """Session folder name, from which we can make an `np_session.Session` instance.

        - each job must have a Session
        - each queue can only have one job per session (session is unique)
        """

    @property
    @abc.abstractmethod
    def priority(self) -> None | int:
        """
        Priority level for this job.
        Processed in descending order (then ordered by `added`).
        """

    @property
    @abc.abstractmethod
    def added(self) -> None | datetime.datetime:
        """
        When the job was added to the queue.
        Jobs processed in ascending order (after ordering by `priority`).
        """

    @property
    @abc.abstractmethod
    def started(self) -> None | datetime.datetime:
        """Whether the job has started (can also represent time)."""

    @property
    @abc.abstractmethod
    def hostname(self) -> None | str:
        """The hostname of the machine that is currently processing this
        session.

        Can also be set to choose a specific machine to process the job.
        """

    @property
    @abc.abstractmethod
    def finished(self) -> None | datetime.datetime:
        """Whether the session has been verified as finished (can also
        represent time).
        """

    @property
    @abc.abstractmethod
    def error(self) -> None | str:
        """Error message, if the job errored."""


@typing.runtime_checkable
class JobQueue(Protocol):
    """Base class for job queues.

    Implementations should subclass `collections.abc.MutableMapping`
    to get methods like items, keys, get, setdefault, etc.
    """

    @abc.abstractmethod
    def __setitem__(self, key: npc_lims.SessionRecord, value: Job) -> None:
        """Add a job to the queue."""

    @abc.abstractmethod
    def __getitem__(self, key: npc_lims.SessionRecord) -> Job:
        """Get a job from the queue."""

    @abc.abstractmethod
    def __delitem__(self, key: npc_lims.SessionRecord) -> None:
        """Remove a job from the queue."""

    @abc.abstractmethod
    def __contains__(self, key: npc_lims.SessionRecord) -> bool:
        """Whether the session is in the queue."""

    @abc.abstractmethod
    def __len__(self) -> int:
        """Number of jobs in the queue."""

    @abc.abstractmethod
    def __iter__(self) -> Job:
        """Iterate over all jobs in the queue."""

    @abc.abstractmethod
    def __next__(self) -> Job:
        """Get the next job to process.
        Sorted by priority (desc), then date added (asc).
        """

    @abc.abstractmethod
    def update(self, key: npc_lims.SessionRecord, **kwargs: JobArgs) -> None:
        """Update the fields on an existing entry."""
