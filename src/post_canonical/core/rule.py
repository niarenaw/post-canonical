"""Production rules for Post Canonical Systems."""

from collections.abc import Sequence
from dataclasses import dataclass

from .pattern import Pattern
from .variable import Variable


@dataclass(frozen=True, slots=True)
class ProductionRule:
    """A production rule with multiple antecedents and one consequent.

    Antecedents are patterns that must all match (against different words).
    Consequent is the pattern that produces the result.
    Priority determines order of application (higher = first).
    Name is optional but useful for debugging and proof display.

    Example:
        Rule: $xIII$y -> $xU$y
        Meaning: Replace any occurrence of "III" with "U"
    """

    antecedents: tuple[Pattern, ...]
    consequent: Pattern
    priority: int = 0
    name: str | None = None

    def __init__(
        self,
        antecedents: Sequence[Pattern],
        consequent: Pattern,
        priority: int = 0,
        name: str | None = None,
    ) -> None:
        if not antecedents:
            raise ValueError("Rule must have at least one antecedent")

        object.__setattr__(self, "antecedents", tuple(antecedents))
        object.__setattr__(self, "consequent", consequent)
        object.__setattr__(self, "priority", priority)
        object.__setattr__(self, "name", name)

        # Validate: consequent can only use variables from antecedents
        antecedent_vars: set[str] = set()
        for ante in self.antecedents:
            antecedent_vars.update(ante.variable_names)

        consequent_vars = consequent.variable_names
        undefined = consequent_vars - antecedent_vars
        if undefined:
            raise ValueError(f"Consequent uses undefined variables: {undefined}")

    @property
    def all_variables(self) -> frozenset[Variable]:
        """All variables used in this rule."""
        result: set[Variable] = set()
        for ante in self.antecedents:
            result.update(ante.variables)
        result.update(self.consequent.variables)
        return frozenset(result)

    @property
    def is_single_antecedent(self) -> bool:
        """True if rule has exactly one antecedent."""
        return len(self.antecedents) == 1

    @property
    def display_name(self) -> str:
        """Human-readable name, falling back to 'rule' if unnamed."""
        return self.name or "rule"

    @property
    def sort_key(self) -> tuple[int, str]:
        """Canonical sort key: descending priority, then alphabetical name."""
        return (-self.priority, self.name or "")

    @property
    def pattern_str(self) -> str:
        """The rule's pattern string without the name prefix."""
        antes = ", ".join(str(a) for a in self.antecedents)
        return f"{antes} -> {self.consequent}"

    def __str__(self) -> str:
        name_part = f"[{self.name}] " if self.name else ""
        return f"{name_part}{self.pattern_str}"

    def __repr__(self) -> str:
        return f"ProductionRule({self})"
