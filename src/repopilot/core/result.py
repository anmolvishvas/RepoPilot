"""Typed Result monad for explicit and deterministic error handling."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, NoReturn, TypeVar

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")
F = TypeVar("F")


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """Represents a successful computation containing a value."""

    value: T

    @property
    def is_ok(self) -> bool:
        """Return True if this is an Ok instance."""
        return True

    @property
    def is_err(self) -> bool:
        """Return False if this is an Ok instance."""
        return False

    def unwrap(self) -> T:
        """Extract the inner success value."""
        return self.value

    def unwrap_or(self, _default: T) -> T:
        """Return the inner value regardless of the default."""
        return self.value

    def unwrap_err(self) -> NoReturn:
        """Raise ValueError because this result is an Ok variant."""
        raise ValueError(f"Called unwrap_err on an Ok variant: {self.value}")

    def map(self, func: Callable[[T], U]) -> Ok[U]:
        """Apply a transformation function to the inner value."""
        return Ok(func(self.value))

    def map_err(self, _func: object) -> Ok[T]:
        """No-op for Ok variant; returns self."""
        return Ok(self.value)

    def flat_map(self, func: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Apply a monadic bind operation that returns another Result."""
        return func(self.value)


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    """Represents a failed computation containing an error."""

    error: E

    @property
    def is_ok(self) -> bool:
        """Return False if this is an Err instance."""
        return False

    @property
    def is_err(self) -> bool:
        """Return True if this is an Err instance."""
        return True

    def unwrap(self) -> NoReturn:
        """Raise ValueError because this result is an Err variant."""
        raise ValueError(f"Called unwrap on an Err variant: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Return the provided default value."""
        return default

    def unwrap_err(self) -> E:
        """Extract the inner error value."""
        return self.error

    def map(self, _func: object) -> Err[E]:
        """No-op for Err variant; returns self."""
        return Err(self.error)

    def map_err(self, func: Callable[[E], F]) -> Err[F]:
        """Apply a transformation function to the inner error."""
        return Err(func(self.error))

    def flat_map(self, _func: object) -> Err[E]:
        """No-op for Err variant; returns self."""
        return Err(self.error)


Result = Ok[T] | Err[E]


def ok(value: T) -> Ok[T]:
    """Convenience constructor for Ok[T]."""
    return Ok(value)


def err(error: E) -> Err[E]:
    """Convenience constructor for Err[E]."""
    return Err(error)
