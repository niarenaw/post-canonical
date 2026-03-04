"""Variable bindings for pattern matching."""

from collections.abc import Iterator
from collections.abc import Mapping as MappingABC
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class Binding(MappingABC[str, str]):
    """Immutable mapping from variable names to matched string values.

    Supports merging and conflict detection. Used during pattern matching
    to track what each variable has been bound to. Maintains both a sorted
    tuple for stable iteration/hashing and a dict for O(1) lookups, since
    this is on the hot path of the backtracking matcher.
    """

    _data: tuple[tuple[str, str], ...]
    _lookup: dict[str, str]

    def __init__(self, data: MappingABC[str, str] | None = None) -> None:
        if data is None:
            data = {}
        sorted_items = tuple(sorted(data.items()))
        object.__setattr__(self, "_data", sorted_items)
        object.__setattr__(self, "_lookup", dict(sorted_items))

    def __getitem__(self, key: str) -> str:
        try:
            return self._lookup[key]
        except KeyError:
            raise KeyError(key) from None

    def __contains__(self, key: object) -> bool:
        return key in self._lookup

    def __iter__(self) -> Iterator[str]:
        return (k for k, _ in self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __str__(self) -> str:
        pairs = ", ".join(f"${k}={v!r}" for k, v in self._data)
        return "{" + pairs + "}"

    def __repr__(self) -> str:
        return f"Binding({dict(self._data)})"

    def __hash__(self) -> int:
        return hash(self._data)

    def to_dict(self) -> dict[str, str]:
        """Convert to a regular dictionary."""
        return dict(self._data)

    def merge(self, other: "Binding") -> "Binding | None":
        """Merge two bindings. Returns None if there's a conflict.

        A conflict occurs when the same variable is bound to different values.
        """
        merged = dict(self._data)
        for k, v in other._data:
            if k in merged and merged[k] != v:
                return None
            merged[k] = v
        return Binding(merged)

    def extend(self, name: str, value: str) -> "Binding | None":
        """Add a single binding. Returns None if there's a conflict.

        Optimized to avoid creating an intermediate Binding object, since
        this is called on every variable-length attempt during backtracking.
        """
        if name in self._lookup:
            return self if self._lookup[name] == value else None
        new_data = dict(self._data)
        new_data[name] = value
        return Binding(new_data)

    @classmethod
    def empty(cls) -> Self:
        """Create an empty binding."""
        return cls({})

    @classmethod
    def from_pairs(cls, *pairs: tuple[str, str]) -> Self:
        """Create a binding from variable-value pairs."""
        return cls(dict(pairs))
