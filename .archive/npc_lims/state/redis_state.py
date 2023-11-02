"""
Redis connection for persisting session state.
"""
from __future__ import annotations

import collections.abc
import contextlib
import logging
import os
from collections.abc import Iterator
from typing import ClassVar, Union

import redis
from typing_extensions import TypeAlias

logger = logging.getLogger(__name__)

# AcceptedType will be coerced to RedisType before being stored in Redis
RedisType: TypeAlias = Union[str, int, float]
"""Can be stored in Redis directly, or returned from Redis."""

AcceptedType: TypeAlias = Union[RedisType, bool, None]
"""Can be stored in Redis after using `encode(value: AcceptedType)`."""


class State(collections.abc.MutableMapping):
    """Get and set session state in Redis via a dict interface.

    - dict interface provides `keys`, `get`, `setdefault`, `pop`, etc.
    - accepted value types are str, int, float, bool, None

    >>> test_id = 0
    >>> state = State(test_id)
    >>> state['test'] = 1.0
    >>> state['test']
    1.0
    >>> state['test'] = 'test'
    >>> state['test']
    'test'
    >>> all('test' in _ for _ in (state, state.keys(), state.values()))
    True
    >>> state.setdefault('test', True)
    'test'
    >>> state.pop('test')
    'test'
    >>> del state['test']
    >>> state.get('test') is None
    True
    """

    db: ClassVar[redis.Redis]

    def __init__(self, id: int | str) -> None:
        self.name = str(id)
        try:
            _ = self.db
        except AttributeError:
            self.__class__.connect()

    def __repr__(self) -> str:
        return self.data.__repr__()

    @classmethod
    def connect(cls) -> None:
        cls.db = redis.Redis(
            host="redis-11357.c1.us-west-2-2.ec2.cloud.redislabs.com",
            port=11357,
            password=os.environ["REDIS_DEFAULT_USER_PASSWORD"],
        )
        if cls.db.ping():
            logger.debug("Connected to Redis database: %s", cls.db)
        else:
            logger.error("Failed to connect to Redis database")

    @property
    def data(self) -> dict[str, AcceptedType]:
        return {k.decode(): decode(v) for k, v in self.db.hgetall(self.name).items()}

    def __getitem__(self, key: str) -> AcceptedType:
        _ = decode(self.db.hget(self.name, key))
        if _ is None:
            raise KeyError(f"{key!r} not found in Redis db entry {self!r}")
        return _

    def __setitem__(self, key: str, value: AcceptedType) -> None:
        self.db.hset(self.name, key, encode(value))

    def __delitem__(self, key: str) -> None:
        self.db.hdel(self.name, key)

    def __iter__(self) -> Iterator[str]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)


def encode(value: AcceptedType) -> RedisType:
    """Redis can't store bools: convert to something compatible before entering."""
    if isinstance(value, bool) or value is None:
        return str(value)
    if isinstance(value, (int, str, float)):
        return value
    raise TypeError(f"Cannot store {value!r} in Redis")


def decode(value: bytes | None) -> AcceptedType:
    """Redis stores everything as bytes: convert back to our original python datatype."""
    if value is None:
        return None
    decoded_value: str = value.decode()
    if decoded_value.isnumeric():
        return int(decoded_value)
    with contextlib.suppress(ValueError):
        return float(decoded_value)
    if decoded_value.capitalize() in (str(_) for _ in (True, False, None)):
        return eval(decoded_value.capitalize())
    return decoded_value


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
