"""Pattern representation for Post Canonical Systems."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .variable import Variable

if TYPE_CHECKING:
    from ..matching.binding import Binding
    from .alphabet import Alphabet

# A pattern element is either a string constant or a Variable
type PatternElement = str | Variable


def _normalize_elements(elements: Sequence[PatternElement]) -> list[PatternElement]:
    """Merge consecutive string constants."""
    if not elements:
        return []

    result: list[PatternElement] = []
    current_str: list[str] = []

    for elem in elements:
        if isinstance(elem, str):
            if elem:  # Skip empty strings
                current_str.append(elem)
        else:
            if current_str:
                result.append("".join(current_str))
                current_str = []
            result.append(elem)

    if current_str:
        result.append("".join(current_str))

    return result


@dataclass(frozen=True, slots=True)
class Pattern:
    """Immutable pattern for matching/producing strings.

    A pattern is a sequence of constants (strings) and variables.
    Example: Pattern(["M", Variable("x"), "I"]) represents "M$xI"

    Variables are referenced by name using $ prefix in string representation.
    """

    elements: tuple[PatternElement, ...]

    def __init__(self, elements: Sequence[PatternElement]) -> None:
        normalized = _normalize_elements(elements)
        object.__setattr__(self, "elements", tuple(normalized))

    @property
    def variables(self) -> frozenset[Variable]:
        """Return all unique variables in the pattern.

        Not cached because this property is only accessed during system construction
        and validation, not in hot execution paths. Patterns are typically small, so
        the cost of filtering elements is negligible compared to caching overhead.
        """
        return frozenset(e for e in self.elements if isinstance(e, Variable))

    @property
    def variable_names(self) -> frozenset[str]:
        """Return all unique variable names in the pattern."""
        return frozenset(v.name for v in self.variables)

    def has_consecutive_variables(self) -> bool:
        """Check if pattern has two variables in a row."""
        for i in range(len(self.elements) - 1):
            if isinstance(self.elements[i], Variable) and isinstance(self.elements[i + 1], Variable):
                return True
        return False

    def substitute(self, bindings: "Binding") -> str:
        """Substitute variables with their bound values."""
        result: list[str] = []
        for elem in self.elements:
            if isinstance(elem, Variable):
                if elem.name not in bindings:
                    raise ValueError(f"Unbound variable: {elem.name}")
                result.append(bindings[elem.name])
            else:
                result.append(elem)
        return "".join(result)

    def validate_against_alphabet(self, alphabet: "Alphabet") -> list[str]:
        """Return list of validation errors (empty if valid)."""
        errors: list[str] = []
        for elem in self.elements:
            if isinstance(elem, str):
                for char in elem:
                    if char not in alphabet:
                        errors.append(f"Character '{char}' not in alphabet")
        return errors

    def min_match_length(self) -> int:
        """Minimum length of string this pattern can match."""
        total = 0
        for elem in self.elements:
            if isinstance(elem, str):
                total += len(elem)
            elif isinstance(elem, Variable):
                total += elem.min_length()
        return total

    def __str__(self) -> str:
        parts: list[str] = []
        for elem in self.elements:
            if isinstance(elem, Variable):
                parts.append(f"${{{elem.name}}}")
            else:
                parts.append(elem)
        return "".join(parts)

    def __repr__(self) -> str:
        return f"Pattern({self})"

    @classmethod
    def parse(cls, text: str, variables: dict[str, Variable]) -> "Pattern":
        """Parse a pattern string like 'M${x}${y}I' into a Pattern object.

        Variables are denoted by ${name} syntax for unambiguous parsing.
        """
        elements: list[PatternElement] = []
        i = 0

        while i < len(text):
            if text[i] == "$":
                # Expect ${name} format
                if i + 1 >= len(text) or text[i + 1] != "{":
                    raise ValueError(f"Expected '{{' after '$' at position {i}")
                # Find closing brace
                j = i + 2
                while j < len(text) and text[j] != "}":
                    j += 1
                if j >= len(text):
                    raise ValueError(f"Unclosed variable at position {i}")
                var_name = text[i + 2 : j]
                if not var_name:
                    raise ValueError(f"Empty variable name at position {i}")
                if var_name not in variables:
                    raise ValueError(f"Unknown variable: ${{{var_name}}}")
                elements.append(variables[var_name])
                i = j + 1  # Skip past closing brace
            else:
                # Parse constant
                j = i
                while j < len(text) and text[j] != "$":
                    j += 1
                elements.append(text[i:j])
                i = j

        return cls(elements)

    @classmethod
    def constant(cls, text: str) -> "Pattern":
        """Create a pattern with only constant text (no variables)."""
        return cls([text])
