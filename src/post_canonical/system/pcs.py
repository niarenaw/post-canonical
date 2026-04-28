"""Main Post Canonical System class."""

from collections.abc import Iterator
from dataclasses import dataclass

from ..core.alphabet import Alphabet
from ..core.errors import ValidationError, format_set
from ..core.rule import ProductionRule
from ..core.variable import Variable
from .derivation import DerivedWord
from .executor import ExecutionConfig, ExecutionMode, RuleExecutor


@dataclass(frozen=True, slots=True)
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
            raise ValidationError(
                "Word contains characters not in the alphabet",
                context={
                    "word": word,
                    "invalid_characters": format_set(set(invalid)),
                    "alphabet": str(self.alphabet),
                },
            )

    def _validate_rule(self, rule: ProductionRule) -> None:
        """Validate rule patterns against alphabet and variables."""
        for var in rule.all_variables:
            if var not in self.variables:
                raise ValidationError(
                    "Rule references an undeclared variable",
                    context={
                        "rule": rule.display_name,
                        "variable": var.name,
                        "declared": format_set(v.name for v in self.variables),
                    },
                    hint="Add the variable via SystemBuilder.var() or check spelling.",
                )

        for ante in rule.antecedents:
            errors = ante.validate_against_alphabet(self.alphabet)
            if errors:
                raise ValidationError(
                    "Antecedent uses characters not in the alphabet",
                    context=self._pattern_error_context(rule, "antecedent", ante, errors),
                )

        errors = rule.consequent.validate_against_alphabet(self.alphabet)
        if errors:
            raise ValidationError(
                "Consequent uses characters not in the alphabet",
                context=self._pattern_error_context(rule, "consequent", rule.consequent, errors),
            )

    def _pattern_error_context(
        self,
        rule: ProductionRule,
        role: str,
        pattern: object,
        errors: list[str],
    ) -> dict[str, str]:
        """Build the structured error context for a pattern-vs-alphabet failure."""
        return {
            "rule": rule.display_name,
            role: str(pattern),
            "issues": "; ".join(errors),
            "alphabet": str(self.alphabet),
        }

    # === Generation ===

    def generate(
        self,
        max_steps: int = 10,
        mode: ExecutionMode = ExecutionMode.NON_DETERMINISTIC,
    ) -> tuple[DerivedWord, ...]:
        """Generate all derivable words up to ``max_steps``.

        Returns ``DerivedWord`` objects (each carrying its derivation
        history) ordered first by word length, then lexicographically.
        Uses breadth-first exploration.

        Args:
            max_steps: Maximum number of derivation rounds. Defaults to 10
                so that systems with explosive growth (or accidental infinite
                loops) terminate quickly. Raise it for deeper exploration,
                or use ``iterate()`` for unbounded lazy traversal.
            mode: Execution mode (DETERMINISTIC or NON_DETERMINISTIC)

        Returns:
            Ordered tuple of all derived words with their derivations.
            The order is deterministic: ``(len(word), word)``.
        """
        config = ExecutionConfig(mode=mode)
        executor = RuleExecutor(self.alphabet, self.rules, config)

        # Initialize with axioms
        current: list[DerivedWord] = [DerivedWord.axiom(w) for w in self.axioms]
        all_words: dict[str, DerivedWord] = {dw.word: dw for dw in current}

        for _ in range(max_steps):
            new_words: list[DerivedWord] = []

            for derived in executor.apply_rules_all(current):
                if derived.word not in all_words:
                    new_words.append(derived)
                    all_words[derived.word] = derived

            if not new_words:
                break  # Fixed point reached

            current = new_words

        return tuple(sorted(all_words.values(), key=lambda dw: (len(dw.word), dw.word)))

    def generate_words(
        self,
        max_steps: int = 10,
        mode: ExecutionMode = ExecutionMode.NON_DETERMINISTIC,
    ) -> tuple[str, ...]:
        """Generate all derivable words (without derivation info).

        Returns word strings in the same deterministic order as
        :meth:`generate`: by length, then lexicographic.
        """
        return tuple(dw.word for dw in self.generate(max_steps, mode))

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

            for derived in executor.apply_rules_all(frontier):
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
        for rule in sorted(self.rules, key=lambda r: r.sort_key):
            lines.append(f"  {rule}")
        return "\n".join(lines)
