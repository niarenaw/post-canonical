"""Derivation tracking for Post Canonical Systems."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

from ..core.rule import ProductionRule
from ..matching.binding import Binding


@dataclass(frozen=True, slots=True)
class DerivationStep:
    """A single step in a derivation.

    Records what words were input, what rule was applied,
    what binding was used, and what word was produced.
    """

    inputs: tuple[str, ...]  # Input words (one per antecedent)
    rule: ProductionRule  # Rule that was applied
    binding: Binding  # Variable binding used
    output: str  # Resulting word

    def __str__(self) -> str:
        inputs_str = ", ".join(f"'{w}'" for w in self.inputs)
        rule_name = self.rule.name or "rule"
        return f"{inputs_str} --[{rule_name}]--> '{self.output}'"

    def __repr__(self) -> str:
        return f"DerivationStep({self})"


@dataclass(frozen=True, slots=True)
class Derivation:
    """Complete derivation from axioms to a word.

    Immutable chain of derivation steps. Each step shows how one word
    was derived from previous words using a specific rule and binding.
    """

    steps: tuple[DerivationStep, ...]

    def __init__(self, steps: Sequence[DerivationStep] = ()) -> None:
        object.__setattr__(self, "steps", tuple(steps))

    @property
    def final_word(self) -> str | None:
        """The final derived word, or None if empty."""
        return self.steps[-1].output if self.steps else None

    @property
    def length(self) -> int:
        """Number of derivation steps."""
        return len(self.steps)

    @property
    def is_axiom(self) -> bool:
        """True if this derivation has no steps (word is an axiom)."""
        return len(self.steps) == 0

    def extend(self, step: DerivationStep) -> "Derivation":
        """Return new Derivation with added step."""
        return Derivation((*self.steps, step))

    def rules_used(self) -> list[str]:
        """Return list of rule names used in this derivation."""
        return [step.rule.name or f"rule_{i}" for i, step in enumerate(self.steps)]

    def __str__(self) -> str:
        if not self.steps:
            return "(axiom)"
        return " => ".join(str(step) for step in self.steps)

    def __repr__(self) -> str:
        return f"Derivation({len(self.steps)} steps)"

    def to_trace(self) -> str:
        """Return a multi-line trace of the derivation."""
        if not self.steps:
            return "  (axiom - no derivation steps)"

        lines = []
        for i, step in enumerate(self.steps, 1):
            rule_name = step.rule.name or "rule"
            lines.append(f"  {i}. {step.inputs} --[{rule_name}]--> {step.output}")
            lines.append(f"     bindings: {step.binding}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class DerivedWord:
    """A word along with how it was derived.

    Combines the word itself with its complete derivation history,
    allowing proof inspection and verification.
    """

    word: str
    derivation: Derivation

    def __str__(self) -> str:
        return f"'{self.word}' ({self.derivation.length} steps)"

    def __repr__(self) -> str:
        return f"DerivedWord({self.word!r}, {self.derivation!r})"

    @property
    def is_axiom(self) -> bool:
        """True if this word is an axiom (no derivation needed)."""
        return self.derivation.is_axiom

    @classmethod
    def axiom(cls, word: str) -> Self:
        """Create a DerivedWord that is an axiom (no derivation needed)."""
        return cls(word=word, derivation=Derivation())

    def trace(self) -> str:
        """Return a human-readable trace of how this word was derived."""
        lines = [f"Word: '{self.word}'"]
        if self.is_axiom:
            lines.append("  (axiom)")
        else:
            lines.append(f"Derivation ({self.derivation.length} steps):")
            lines.append(self.derivation.to_trace())
        return "\n".join(lines)
