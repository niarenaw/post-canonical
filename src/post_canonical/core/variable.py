"""Explicit variable system for Post Canonical Systems."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Self


class VariableKind(Enum):
    """Defines what a variable can match."""

    ANY = auto()  # Matches any string (including empty)
    NON_EMPTY = auto()  # Matches at least one symbol
    SINGLE = auto()  # Matches exactly one symbol


@dataclass(frozen=True, slots=True)
class Variable:
    """Explicitly declared variable for pattern matching.

    Variables are immutable and identified by name.
    Kind determines matching behavior:
    - ANY: matches any string including empty
    - NON_EMPTY: matches at least one character
    - SINGLE: matches exactly one character
    """

    name: str
    kind: VariableKind = VariableKind.ANY

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Variable name cannot be empty")
        if not self.name.replace("_", "").isalnum():
            raise ValueError(f"Variable name must be alphanumeric (with underscores): {self.name}")

    def __str__(self) -> str:
        return f"${self.name}"

    def __repr__(self) -> str:
        return f"Variable({self.name!r}, {self.kind.name})"

    def matches_empty(self) -> bool:
        """Return True if this variable can match an empty string."""
        return self.kind == VariableKind.ANY

    def min_length(self) -> int:
        """Minimum number of characters this variable must match."""
        match self.kind:
            case VariableKind.ANY:
                return 0
            case VariableKind.NON_EMPTY | VariableKind.SINGLE:
                return 1

    def max_length(self, available: int) -> int:
        """Maximum number of characters this variable can match."""
        match self.kind:
            case VariableKind.SINGLE:
                return 1
            case _:
                return available

    @classmethod
    def any(cls, name: str) -> Self:
        """Create a variable that matches any string (including empty)."""
        return cls(name, VariableKind.ANY)

    @classmethod
    def non_empty(cls, name: str) -> Self:
        """Create a variable that matches at least one character."""
        return cls(name, VariableKind.NON_EMPTY)

    @classmethod
    def single(cls, name: str) -> Self:
        """Create a variable that matches exactly one character."""
        return cls(name, VariableKind.SINGLE)
