"""Multi-pattern unification for rules with multiple antecedents."""

from collections.abc import Iterator, Sequence

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

        Tries every assignment of distinct word slots to antecedent slots,
        but prunes assignments where a word is shorter than its assigned
        antecedent's minimum match length. Antecedents are explored in
        order of descending minimum length, so the most constrained
        slots fail fast and prune the search tree early.

        Args:
            patterns: Sequence of patterns to match
            available_words: Pool of words to draw from

        Yields:
            Tuples of (words_used, binding) for each valid match. The
            ``words_used`` tuple is in the original antecedent order.
        """
        n = len(patterns)
        if n == 0 or n > len(available_words):
            return

        words = tuple(available_words)
        # Pre-compute length floors so we don't pay them per node.
        pattern_min = tuple(p.min_match_length() for p in patterns)
        word_lengths = tuple(len(w) for w in words)

        # Per-antecedent candidate index lists, restricted to words long
        # enough to potentially match. If any antecedent has zero candidates
        # the whole search is empty.
        candidates: list[list[int]] = []
        for required in pattern_min:
            slot_candidates = [i for i, length in enumerate(word_lengths) if length >= required]
            if not slot_candidates:
                return
            candidates.append(slot_candidates)

        # Walk antecedents in descending order of min length so the
        # most-constrained slot prunes the search tree first.
        order = sorted(range(n), key=lambda i: pattern_min[i], reverse=True)

        used: set[int] = set()
        chosen: list[int] = [-1] * n  # index per antecedent

        def walk(depth: int) -> Iterator[tuple[tuple[str, ...], Binding]]:
            if depth == n:
                ordered = tuple(words[chosen[i]] for i in range(n))
                ordered_patterns = tuple(patterns[i] for i in range(n))
                for binding in self.unify(ordered_patterns, ordered):
                    yield (ordered, binding)
                return

            slot = order[depth]
            for word_idx in candidates[slot]:
                if word_idx in used:
                    continue
                used.add(word_idx)
                chosen[slot] = word_idx
                yield from walk(depth + 1)
                used.remove(word_idx)
                chosen[slot] = -1

        yield from walk(0)
