from collections.abc import Collection
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Alphabet:
    """Represents a finite alphabet for use in Post Canonical Systems."""

    symbols: frozenset[str] = field(default_factory=frozenset)

    def __init__(self, symbols: Collection[str]):
        """Initialize an alphabet with a set of symbols.

        Args:
            symbols: A set or iterable of strings representing the alphabet symbols
        """
        # Convert to frozenset and make immutable
        object.__setattr__(self, "symbols", frozenset(symbols))

    def __contains__(self, symbol: str) -> bool:
        """Check if a symbol is in the alphabet."""
        return symbol in self.symbols

    def __iter__(self):
        """Iterate over the alphabet symbols."""
        return iter(self.symbols)

    def __len__(self) -> int:
        """Get the size of the alphabet."""
        return len(self.symbols)

    def __str__(self) -> str:
        """String representation of the alphabet."""
        return f"Alphabet({sorted(self.symbols)})"

    def __repr__(self) -> str:
        """Detailed string representation of the alphabet."""
        return f"Alphabet(symbols={sorted(self.symbols)})"


# Common predefined alphabets
ENGLISH_LOWERCASE = Alphabet("abcdefghijklmnopqrstuvwxyz")
ENGLISH_UPPERCASE = Alphabet("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
ENGLISH_ALPHABET = Alphabet("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
DIGITS = Alphabet("0123456789")
BINARY = Alphabet("01")
HEXADECIMAL = Alphabet("0123456789ABCDEF")
BOOLEAN = Alphabet("TF")
BRACKETS = Alphabet("[](){}")
MU_PUZZLE = Alphabet("MIU")  # Alphabet for the MU puzzle
