from dataclasses import dataclass
from typing import override


@dataclass(frozen=True, slots=True)
class ProductionRule:
    """Represents a production rule in a Post Canonical System."""

    antecedents: tuple[str, ...]  # Tuple of antecedent patterns
    consequent: str  # Consequent pattern

    def __init__(self, antecedents: list[str] | tuple[str, ...], consequent: str):
        """Initialize a production rule.

        Args:
            antecedents: List or tuple of antecedent patterns
            consequent: Consequent pattern
        """
        object.__setattr__(self, "antecedents", tuple(antecedents))
        object.__setattr__(self, "consequent", consequent)

    @override
    def __str__(self) -> str:
        """String representation of the rule."""
        return f"{' '.join(self.antecedents)} → {self.consequent}"
