"""Alphabet definition for Post Canonical Systems."""

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Alphabet:
    """Immutable set of symbols forming an alphabet.

    An alphabet defines the valid symbols that can appear in words
    of a Post Canonical System. Variables are explicitly declared
    separately and are not part of the alphabet.
    """

    symbols: frozenset[str]

    def __init__(self, symbols: str | frozenset[str] | set[str]) -> None:
        if isinstance(symbols, str):
            symbol_set = frozenset(symbols)
        else:
            symbol_set = frozenset(symbols)

        # Validate: each symbol must be a single character
        for s in symbol_set:
            if len(s) != 1:
                raise ValueError(f"Alphabet symbols must be single characters, got: '{s}'")

        if not symbol_set:
            raise ValueError("Alphabet cannot be empty")

        object.__setattr__(self, "symbols", symbol_set)

    def __contains__(self, item: str) -> bool:
        return item in self.symbols

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self.symbols))

    def __len__(self) -> int:
        return len(self.symbols)

    def __str__(self) -> str:
        return "{" + ", ".join(sorted(self.symbols)) + "}"

    def __repr__(self) -> str:
        return f"Alphabet({self})"

    def union(self, other: "Alphabet") -> "Alphabet":
        """Return a new alphabet containing symbols from both."""
        return Alphabet(self.symbols | other.symbols)

    def validate_word(self, word: str) -> list[str]:
        """Return list of invalid characters in word (empty if valid)."""
        return [c for c in word if c not in self.symbols]
