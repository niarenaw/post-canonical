"""Main Post Canonical System class."""

from collections.abc import Iterator
from dataclasses import dataclass

from ..core.alphabet import Alphabet
from ..core.rule import ProductionRule
from ..core.variable import Variable
from .derivation import DerivedWord
from .executor import ExecutionConfig, ExecutionMode, RuleExecutor


@dataclass(frozen=True)
class PostCanonicalSystem:
    """A Post Canonical System with full derivation tracking.

    A Post Canonical System consists of:
    - An alphabet of symbols
    - A set of explicitly declared variables
    - A set of axioms (initial words)
    - A set of production rules

    The system can generate all words derivable from the axioms
    by repeatedly applying the production rules.

    This implementation is immutable: all operations return new
    instances or iterators.
    """

    alphabet: Alphabet
    axioms: frozenset[str]
    rules: frozenset[ProductionRule]
    variables: frozenset[Variable]

    def __post_init__(self) -> None:
        # Validate axioms
        for axiom in self.axioms:
            self._validate_word(axiom)

        # Validate rules
        for rule in self.rules:
            self._validate_rule(rule)

    def _validate_word(self, word: str) -> None:
        """Ensure word uses only alphabet symbols."""
        invalid = self.alphabet.validate_word(word)
        if invalid:
            raise ValueError(f"Word '{word}' contains invalid characters: {invalid}")

    def _validate_rule(self, rule: ProductionRule) -> None:
        """Validate rule patterns against alphabet and variables."""
        # Check all variables in rule are declared
        for var in rule.all_variables:
            if var not in self.variables:
                raise ValueError(f"Undeclared variable in rule: {var}")

        # Validate constant parts of patterns
        for ante in rule.antecedents:
            errors = ante.validate_against_alphabet(self.alphabet)
            if errors:
                raise ValueError(f"Invalid antecedent in rule '{rule.name}': {errors}")

        errors = rule.consequent.validate_against_alphabet(self.alphabet)
        if errors:
            raise ValueError(f"Invalid consequent in rule '{rule.name}': {errors}")

    # === Generation ===

    def generate(
        self,
        max_steps: int = 10,
        mode: ExecutionMode = ExecutionMode.NON_DETERMINISTIC,
    ) -> frozenset[DerivedWord]:
        """Generate all derivable words up to max_steps.

        Returns DerivedWord objects that include derivation history.
        Uses breadth-first exploration.

        Args:
            max_steps: Maximum number of derivation rounds
            mode: Execution mode (DETERMINISTIC or NON_DETERMINISTIC)

        Returns:
            Frozen set of all derived words with their derivations
        """
        config = ExecutionConfig(mode=mode)
        executor = RuleExecutor(self.alphabet, self.rules, config)

        # Initialize with axioms
        current: frozenset[DerivedWord] = frozenset(DerivedWord.axiom(w) for w in self.axioms)
        all_words: dict[str, DerivedWord] = {dw.word: dw for dw in current}

        for _ in range(max_steps):
            new_words: list[DerivedWord] = []

            for derived in executor.apply_rules_all(current):
                if derived.word not in all_words:
                    new_words.append(derived)
                    all_words[derived.word] = derived

            if not new_words:
                break  # Fixed point reached

            current = frozenset(new_words)

        return frozenset(all_words.values())

    def generate_words(
        self,
        max_steps: int = 10,
        mode: ExecutionMode = ExecutionMode.NON_DETERMINISTIC,
    ) -> frozenset[str]:
        """Generate all derivable words (without derivation info).

        Convenience method that returns just the word strings.
        """
        return frozenset(dw.word for dw in self.generate(max_steps, mode))

    # === Iteration ===

    def iterate(
        self,
        mode: ExecutionMode = ExecutionMode.NON_DETERMINISTIC,
    ) -> Iterator[DerivedWord]:
        """Iterate derivations lazily (potentially infinite).

        Yields derived words as they are discovered.
        Uses breadth-first exploration.

        Args:
            mode: Execution mode

        Yields:
            DerivedWord objects in order of discovery
        """
        config = ExecutionConfig(mode=mode)
        executor = RuleExecutor(self.alphabet, self.rules, config)

        seen: set[str] = set()
        frontier = [DerivedWord.axiom(w) for w in self.axioms]

        for dw in frontier:
            if dw.word not in seen:
                seen.add(dw.word)
                yield dw

        while frontier:
            next_frontier: list[DerivedWord] = []

            for derived in executor.apply_rules_all(frozenset(frontier)):
                if derived.word not in seen:
                    seen.add(derived.word)
                    yield derived
                    next_frontier.append(derived)

            frontier = next_frontier

    # === Utilities ===

    def __str__(self) -> str:
        return (
            f"PostCanonicalSystem(\n"
            f"  alphabet={self.alphabet},\n"
            f"  axioms={set(self.axioms)},\n"
            f"  variables={{{', '.join(str(v) for v in self.variables)}}},\n"
            f"  rules=[{len(self.rules)} rules]\n"
            f")"
        )

    def describe(self) -> str:
        """Return a detailed description of the system."""
        lines = [
            "Post Canonical System",
            "=" * 40,
            f"Alphabet: {self.alphabet}",
            f"Variables: {', '.join(str(v) for v in sorted(self.variables, key=lambda v: v.name))}",
            f"Axioms: {', '.join(sorted(self.axioms))}",
            "",
            "Rules:",
        ]
        for rule in sorted(self.rules, key=lambda r: (-r.priority, r.name or "")):
            lines.append(f"  {rule}")
        return "\n".join(lines)
