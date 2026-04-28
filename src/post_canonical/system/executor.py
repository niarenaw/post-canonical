"""Rule execution engine for Post Canonical Systems."""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum

from ..core.alphabet import Alphabet
from ..core.rule import ProductionRule
from ..matching.binding import Binding
from ..matching.matcher import PatternMatcher
from ..matching.unifier import MultiPatternUnifier
from .derivation import Derivation, DerivationStep, DerivedWord


class ExecutionMode(StrEnum):
    """How to handle multiple possible rule applications."""

    DETERMINISTIC = "deterministic"  # First match only (by priority, then order)
    NON_DETERMINISTIC = "non_deterministic"  # All matches (for exploration)


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    """Configuration for rule execution."""

    mode: ExecutionMode = ExecutionMode.DETERMINISTIC
    max_results: int | None = None  # Limit results in non-deterministic mode


class RuleExecutor:
    """Executes production rules against words.

    Handles both single-antecedent and multi-antecedent rules,
    tracks derivations, and respects execution mode configuration.
    """

    def __init__(
        self,
        alphabet: Alphabet,
        rules: frozenset[ProductionRule],
        config: ExecutionConfig | None = None,
    ) -> None:
        self.alphabet = alphabet
        self.rules = rules
        self.config = config or ExecutionConfig()
        self.matcher = PatternMatcher(alphabet)
        self.unifier = MultiPatternUnifier(self.matcher)

        self._sorted_rules = sorted(rules, key=lambda r: r.sort_key)

    def apply_rules(
        self,
        words: Sequence[DerivedWord],
    ) -> Iterator[DerivedWord]:
        """Apply all applicable rules to produce new derived words.

        In DETERMINISTIC mode: yields first successful application per input
        In NON_DETERMINISTIC mode: yields all possible applications

        Args:
            words: Set of currently available derived words

        Yields:
            New DerivedWord objects with updated derivations
        """
        results_count = 0

        for rule in self._sorted_rules:
            for derived in self._apply_rule(rule, words):
                yield derived
                results_count += 1

                if self.config.mode == ExecutionMode.DETERMINISTIC:
                    return

                if self.config.max_results and results_count >= self.config.max_results:
                    return

    def apply_rules_all(
        self,
        words: Sequence[DerivedWord],
    ) -> Iterator[DerivedWord]:
        """Apply all rules and yield all possible results.

        Ignores execution mode and always yields all possibilities.
        Useful for exhaustive exploration.
        """
        for rule in self._sorted_rules:
            if rule.is_single_antecedent:
                yield from self._apply_single_antecedent(rule, words)
            else:
                yield from self._apply_multi_antecedent(rule, words)

    def _apply_rule(
        self,
        rule: ProductionRule,
        words: Sequence[DerivedWord],
    ) -> Iterator[DerivedWord]:
        """Apply a single rule, respecting execution mode for early return."""
        source = self._apply_single_antecedent if rule.is_single_antecedent else self._apply_multi_antecedent
        for derived in source(rule, words):
            yield derived
            if self.config.mode == ExecutionMode.DETERMINISTIC:
                return

    def _create_derivation_step(
        self,
        inputs: tuple[str, ...],
        rule: ProductionRule,
        binding: Binding,
    ) -> tuple[DerivationStep, str]:
        """Create a derivation step and compute the result word.

        Returns the step and the resulting word as a tuple, since both are
        needed by callers and the result computation is tightly coupled.
        """
        result = rule.consequent.substitute(binding)
        step = DerivationStep(
            inputs=inputs,
            rule=rule,
            binding=binding,
            output=result,
        )
        return step, result

    def _apply_single_antecedent(
        self,
        rule: ProductionRule,
        words: Sequence[DerivedWord],
    ) -> Iterator[DerivedWord]:
        """Apply rule with single antecedent, yielding all matches."""
        pattern = rule.antecedents[0]

        for derived_word in words:
            for binding in self.matcher.match(pattern, derived_word.word):
                step, result = self._create_derivation_step(
                    inputs=(derived_word.word,),
                    rule=rule,
                    binding=binding,
                )
                new_derivation = derived_word.derivation.extend(step)
                yield DerivedWord(result, new_derivation)

    def _apply_multi_antecedent(
        self,
        rule: ProductionRule,
        words: Sequence[DerivedWord],
    ) -> Iterator[DerivedWord]:
        """Apply rule with multiple antecedents, yielding all matches."""
        word_map = {dw.word: dw for dw in words}
        raw_words = list(word_map.keys())

        for word_combo, binding in self.unifier.unify_any_combination(rule.antecedents, raw_words):
            step, result = self._create_derivation_step(
                inputs=word_combo,
                rule=rule,
                binding=binding,
            )

            input_derived = tuple(word_map[w] for w in word_combo)
            combined = self._merge_derivations(input_derived)
            new_derivation = combined.extend(step)
            yield DerivedWord(result, new_derivation)

    def _merge_derivations(
        self,
        derived_words: tuple[DerivedWord, ...],
    ) -> Derivation:
        """Merge multiple derivations (for multi-antecedent rules)."""
        all_steps: list[DerivationStep] = []
        for dw in derived_words:
            all_steps.extend(dw.derivation.steps)
        return Derivation(tuple(all_steps))
