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
    ways a pattern can match a word. To keep the inner loop allocation-free,
    bindings are tracked in a mutable scratch dict and frozen into an
    immutable :class:`Binding` only at the moment of yielding a successful
    match.
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
        elements = pattern.elements
        suffix_min = self._compute_suffix_min_lengths(elements)

        scratch: dict[str, str] = dict(initial_binding) if initial_binding is not None else {}

        yield from self._match_elements(
            elements=elements,
            suffix_min=suffix_min,
            elem_idx=0,
            word=word,
            pos=0,
            scratch=scratch,
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

        ``suffix_min[i]`` is the minimum length needed to match ``elements[i:]``.
        This avoids recomputing the sum on every backtracking node and lets
        the matcher prune branches that cannot possibly fit the remaining word.
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
        scratch: dict[str, str],
    ) -> Iterator[Binding]:
        """Recursive matching with backtracking.

        Uses an index into the elements tuple rather than slicing, to avoid
        allocating intermediate tuples on each recursive call. Variable
        bindings live in a mutable ``scratch`` dict that is mutated on the
        way down and reverted on the way back up; only successful matches
        pay the cost of constructing an immutable :class:`Binding`.

        Core algorithm:

        1. If no more elements, succeed if we consumed the entire word.
        2. If the remaining word cannot fit the remaining minimum length, prune.
        3. Constant element: must match exactly via :meth:`str.startswith`.
        4. Variable element: either reuse the existing binding (consistency
           check) or try every feasible length within the variable's kind.
        """
        if elem_idx >= len(elements):
            if pos == len(word):
                yield Binding(scratch)
            return

        # Length-feasibility prune: if what remains in `word` cannot fit
        # the remaining minimum-length sum, no extension can succeed.
        if len(word) - pos < suffix_min[elem_idx]:
            return

        elem = elements[elem_idx]
        next_idx = elem_idx + 1

        if isinstance(elem, str):
            if word.startswith(elem, pos):
                yield from self._match_elements(elements, suffix_min, next_idx, word, pos + len(elem), scratch)
            return

        if isinstance(elem, Variable):
            bound = scratch.get(elem.name)
            if bound is not None:
                if word.startswith(bound, pos):
                    yield from self._match_elements(elements, suffix_min, next_idx, word, pos + len(bound), scratch)
                return

            min_len = elem.min_length()
            if elem.kind == VariableKind.SINGLE:
                max_len = 1
            else:
                max_len = len(word) - pos - suffix_min[next_idx]
                if max_len < min_len:
                    return

            name = elem.name
            for length in range(min_len, max_len + 1):
                scratch[name] = word[pos : pos + length]
                yield from self._match_elements(elements, suffix_min, next_idx, word, pos + length, scratch)
            # Pop the variable on the way out so siblings see a clean scratch.
            scratch.pop(name, None)
