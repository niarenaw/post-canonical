"""Variable bindings for pattern matching."""

from collections.abc import Iterator, Mapping
from collections.abc import Mapping as MappingABC
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class Binding(MappingABC[str, str]):
    """Immutable mapping from variable names to matched string values.

    Supports merging and conflict detection. Used during pattern matching
    to track what each variable has been bound to.
    """

    _data: tuple[tuple[str, str], ...]

    def __init__(self, data: Mapping[str, str] | None = None) -> None:
        if data is None:
            data = {}
        object.__setattr__(self, "_data", tuple(sorted(data.items())))

    def __getitem__(self, key: str) -> str:
        for k, v in self._data:
            if k == key:
                return v
        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        return any(k == key for k, _ in self._data)

    def __iter__(self) -> Iterator[str]:
        return (k for k, _ in self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __str__(self) -> str:
        pairs = ", ".join(f"${k}={v!r}" for k, v in self._data)
        return "{" + pairs + "}"

    def __repr__(self) -> str:
        return f"Binding({dict(self._data)})"

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
                return None  # Conflict: same variable, different values
            merged[k] = v
        return Binding(merged)

    def extend(self, name: str, value: str) -> "Binding | None":
        """Add a binding. Returns None if there's a conflict."""
        return self.merge(Binding({name: value}))

    @classmethod
    def empty(cls) -> Self:
        """Create an empty binding."""
        return cls({})

    @classmethod
    def from_pairs(cls, *pairs: tuple[str, str]) -> Self:
        """Create a binding from variable-value pairs."""
        return cls(dict(pairs))
