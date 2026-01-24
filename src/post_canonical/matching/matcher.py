"""Core pattern matching algorithm with backtracking."""

from collections.abc import Iterator, Sequence

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

        yield from self._match_elements(
            elements=pattern.elements,
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

    def _match_elements(
        self,
        elements: Sequence[PatternElement],
        word: str,
        pos: int,
        binding: Binding,
    ) -> Iterator[Binding]:
        """Recursive matching with backtracking.

        Core algorithm:
        1. If no more elements, succeed if we consumed entire word
        2. If element is constant, must match exactly
        3. If element is variable:
           a. If already bound, must match bound value
           b. If unbound, try all possible lengths (backtracking)
        """
        # Base case: no more elements
        if not elements:
            if pos == len(word):
                yield binding
            return

        elem = elements[0]
        rest = elements[1:]

        if isinstance(elem, str):
            # Constant: must match exactly
            end_pos = pos + len(elem)
            if end_pos <= len(word) and word[pos:end_pos] == elem:
                yield from self._match_elements(rest, word, end_pos, binding)

        elif isinstance(elem, Variable):
            # Variable: check if already bound
            if elem.name in binding:
                # Already bound: must match bound value
                bound_value = binding[elem.name]
                end_pos = pos + len(bound_value)
                if end_pos <= len(word) and word[pos:end_pos] == bound_value:
                    yield from self._match_elements(rest, word, end_pos, binding)
            else:
                # Unbound: try all possible lengths
                min_len, max_len = self._var_length_bounds(elem, word, pos, rest)

                for length in range(min_len, max_len + 1):
                    value = word[pos : pos + length]
                    new_binding = binding.extend(elem.name, value)
                    if new_binding is not None:  # No conflict
                        yield from self._match_elements(rest, word, pos + length, new_binding)

    def _var_length_bounds(
        self,
        var: Variable,
        word: str,
        pos: int,
        remaining_elements: Sequence[PatternElement],
    ) -> tuple[int, int]:
        """Compute min/max length a variable can match."""
        # Minimum based on variable kind
        match var.kind:
            case VariableKind.ANY:
                min_len = 0
            case VariableKind.NON_EMPTY:
                min_len = 1
            case VariableKind.SINGLE:
                return (1, 1)  # Exactly one

        # Maximum: remaining word minus minimum for remaining elements
        remaining_min = self._min_length_for_elements(remaining_elements)
        max_len = len(word) - pos - remaining_min

        return (min_len, max(min_len, max_len))

    def _min_length_for_elements(
        self,
        elements: Sequence[PatternElement],
    ) -> int:
        """Compute minimum length needed to match remaining elements."""
        total = 0
        for elem in elements:
            if isinstance(elem, str):
                total += len(elem)
            elif isinstance(elem, Variable):
                total += elem.min_length()
        return total
