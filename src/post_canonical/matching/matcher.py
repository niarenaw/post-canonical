"""Core pattern matching algorithm with backtracking."""

from collections.abc import Iterator

from ..core.alphabet import Alphabet
from ..core.pattern import Pattern, PatternElement
from ..core.variable import Variable, VariableKind
from .binding import Binding


class PatternMatcher:
    """Pattern matching engine that handles all edge cases.

    Key features:
    - Handles consecutive variables via backtracking
    - Enforces repeated variable consistency
    - Supports different variable kinds (ANY, NON_EMPTY, SINGLE)
    - Yields ALL matches (for non-determinism)

    The algorithm uses recursive backtracking to explore all possible
    ways a pattern can match a word.
    """

    def __init__(self, alphabet: Alphabet) -> None:
        self.alphabet = alphabet

    def match(
        self,
        pattern: Pattern,
        word: str,
        initial_binding: Binding | None = None,
    ) -> Iterator[Binding]:
        """Yield all possible bindings that match pattern to word.

        This is a generator that yields every valid binding,
        allowing for non-deterministic exploration.

        Args:
            pattern: The pattern to match
            word: The string to match against
            initial_binding: Optional pre-existing variable bindings

        Yields:
            Binding objects for each valid match
        """
        if initial_binding is None:
            initial_binding = Binding.empty()

        elements = pattern.elements
        suffix_min = self._compute_suffix_min_lengths(elements)

        yield from self._match_elements(
            elements=elements,
            suffix_min=suffix_min,
            elem_idx=0,
            word=word,
            pos=0,
            binding=initial_binding,
        )

    def match_first(
        self,
        pattern: Pattern,
        word: str,
        initial_binding: Binding | None = None,
    ) -> Binding | None:
        """Return first valid binding, or None if no match."""
        for binding in self.match(pattern, word, initial_binding):
            return binding
        return None

    def matches(
        self,
        pattern: Pattern,
        word: str,
        initial_binding: Binding | None = None,
    ) -> bool:
        """Return True if pattern matches word."""
        return self.match_first(pattern, word, initial_binding) is not None

    @staticmethod
    def _compute_suffix_min_lengths(elements: tuple[PatternElement, ...]) -> list[int]:
        """Precompute minimum match length for each suffix of the elements array.

        suffix_min[i] is the minimum length needed to match elements[i:]. This
        avoids recomputing the sum on every backtracking node.
        """
        n = len(elements)
        suffix_min = [0] * (n + 1)
        for i in range(n - 1, -1, -1):
            elem = elements[i]
            if isinstance(elem, str):
                suffix_min[i] = suffix_min[i + 1] + len(elem)
            else:
                suffix_min[i] = suffix_min[i + 1] + elem.min_length()
        return suffix_min

    def _match_elements(  # noqa: PLR0913
        self,
        elements: tuple[PatternElement, ...],
        suffix_min: list[int],
        elem_idx: int,
        word: str,
        pos: int,
        binding: Binding,
    ) -> Iterator[Binding]:
        """Recursive matching with backtracking.

        Uses an index into the elements tuple rather than slicing, to avoid
        allocating intermediate tuples on each recursive call.

        Core algorithm:
        1. If no more elements, succeed if we consumed entire word
        2. If element is constant, must match exactly
        3. If element is variable:
           a. If already bound, must match bound value
           b. If unbound, try all possible lengths (backtracking)
        """
        if elem_idx >= len(elements):
            if pos == len(word):
                yield binding
            return

        elem = elements[elem_idx]
        next_idx = elem_idx + 1

        if isinstance(elem, str):
            end_pos = pos + len(elem)
            if end_pos <= len(word) and word[pos:end_pos] == elem:
                yield from self._match_elements(elements, suffix_min, next_idx, word, end_pos, binding)

        elif isinstance(elem, Variable):
            if elem.name in binding:
                bound_value = binding[elem.name]
                end_pos = pos + len(bound_value)
                if end_pos <= len(word) and word[pos:end_pos] == bound_value:
                    yield from self._match_elements(elements, suffix_min, next_idx, word, end_pos, binding)
            else:
                min_len = elem.min_length()
                if elem.kind == VariableKind.SINGLE:
                    max_len = 1
                else:
                    max_len = max(min_len, len(word) - pos - suffix_min[next_idx])

                for length in range(min_len, max_len + 1):
                    value = word[pos : pos + length]
                    new_binding = binding.extend(elem.name, value)
                    if new_binding is not None:
                        yield from self._match_elements(elements, suffix_min, next_idx, word, pos + length, new_binding)
