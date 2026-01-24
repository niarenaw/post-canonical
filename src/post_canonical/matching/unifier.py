"""Multi-pattern unification for rules with multiple antecedents."""

from collections.abc import Iterator, Sequence
from itertools import permutations

from ..core.pattern import Pattern
from .binding import Binding
from .matcher import PatternMatcher


class MultiPatternUnifier:
    """Unifies multiple patterns against multiple words.

    Used for rules with multiple antecedents. Each pattern must match
    one word, and all patterns must agree on variable bindings.
    """

    def __init__(self, matcher: PatternMatcher) -> None:
        self.matcher = matcher

    def unify(
        self,
        patterns: Sequence[Pattern],
        words: Sequence[str],
    ) -> Iterator[Binding]:
        """Find all bindings that satisfy all patterns against corresponding words.

        Each pattern[i] must match words[i]. Bindings must be consistent
        across all patterns (same variable = same value).

        Args:
            patterns: Sequence of patterns (one per antecedent)
            words: Sequence of words to match against

        Yields:
            All valid unified bindings
        """
        if len(patterns) != len(words):
            return

        if not patterns:
            yield Binding.empty()
            return

        yield from self._unify_recursive(
            patterns=patterns,
            words=words,
            index=0,
            binding=Binding.empty(),
        )

    def _unify_recursive(
        self,
        patterns: Sequence[Pattern],
        words: Sequence[str],
        index: int,
        binding: Binding,
    ) -> Iterator[Binding]:
        """Recursively unify patterns with accumulated binding."""
        if index >= len(patterns):
            yield binding
            return

        pattern = patterns[index]
        word = words[index]

        # Match this pattern, respecting existing bindings
        for local_binding in self.matcher.match(pattern, word, binding):
            # Recurse with merged binding
            yield from self._unify_recursive(patterns, words, index + 1, local_binding)

    def unify_any_combination(
        self,
        patterns: Sequence[Pattern],
        available_words: Sequence[str],
    ) -> Iterator[tuple[tuple[str, ...], Binding]]:
        """Find all word combinations and bindings that satisfy patterns.

        Tries all permutations of available words to find matches.
        Returns both the word combination used and the binding.

        Args:
            patterns: Sequence of patterns to match
            available_words: Pool of words to draw from

        Yields:
            Tuples of (words_used, binding) for each valid match
        """
        n = len(patterns)
        if n > len(available_words):
            return

        for word_combo in permutations(available_words, n):
            for binding in self.unify(patterns, word_combo):
                yield (word_combo, binding)
