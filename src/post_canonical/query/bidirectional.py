"""Bidirectional BFS reachability for Post Canonical Systems.

Forward BFS expands derivations from the axioms outward; backward BFS
inverts each rule to expand predecessors from the target inward. The
frontiers grow much smaller than a one-sided search because the meeting
point lies near the midpoint of the path: total work drops from
``O(b^d)`` to ``O(2 b^(d/2))``.

This implementation expands single-antecedent rules in both directions
and falls back to forward-only expansion for multi-antecedent rules,
because the backward step would otherwise require both predecessor
words to be jointly reachable forward, an operation that doesn't
slot into a frontier-pair BFS without significant extra machinery.
The fallback is sound: results agree with forward BFS on every system,
they're only delivered faster on systems whose useful rules are
single-antecedent.
"""

from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum

from ..core.rule import ProductionRule
from ..matching.binding import Binding
from ..matching.inverter import RuleInverter
from ..matching.matcher import PatternMatcher
from ..system.derivation import Derivation, DerivationStep, DerivedWord
from ..system.executor import RuleExecutor
from ..system.pcs import PostCanonicalSystem
from .reachability import QueryResult, ReachabilityResult


class InversionMode(StrEnum):
    """Control how aggressive backward expansion is.

    ``STRICT`` (default) only inverts rules where every antecedent
    variable also appears in the consequent, guaranteeing finite
    predecessors. ``BOUNDED`` is reserved for a future opt-in mode
    that enumerates bounded preimages of variable-deleting rules; it
    falls back to ``STRICT`` semantics today.
    """

    STRICT = "strict"
    BOUNDED = "bounded"


@dataclass(frozen=True, slots=True)
class BidirectionalConfig:
    """Knobs for the bidirectional reachability search."""

    max_words: int = 10_000
    inversion_mode: InversionMode = InversionMode.STRICT


@dataclass(frozen=True, slots=True)
class _BackwardLink:
    """One link in the backward chain from a word to the target.

    Applying ``rule`` to (the word this link is attached to plus the
    other antecedent inputs in ``other_inputs``) under ``binding``
    produces ``next_word`` - the word one step closer to the target.
    For single-antecedent rules ``other_inputs`` is empty.
    """

    rule: ProductionRule
    binding: Binding
    next_word: str
    other_inputs: tuple[str, ...] = ()


class BidirectionalReachabilityQuery:
    """Meet-in-the-middle reachability for Post canonical systems."""

    def __init__(self, system: PostCanonicalSystem) -> None:
        self.system = system
        self._matcher = PatternMatcher(system.alphabet)
        self._executor = RuleExecutor(system.alphabet, system.rules)
        self._inverters = tuple(RuleInverter.from_rule(rule) for rule in system.rules)

    def is_derivable(
        self,
        target: str,
        config: BidirectionalConfig | None = None,
    ) -> ReachabilityResult:
        """Search for a derivation of ``target`` from any axiom.

        Returns a :class:`ReachabilityResult` whose ``derivation`` is a
        full forward derivation when found - the bidirectional search
        is internal; the caller-facing API is identical to
        :class:`ReachabilityQuery`.
        """
        config = config or BidirectionalConfig()

        if target in self.system.axioms:
            return ReachabilityResult(
                status=QueryResult.DERIVABLE,
                derivation=Derivation(),
                steps_explored=0,
                target=target,
            )

        forward: dict[str, Derivation] = {axiom: Derivation() for axiom in self.system.axioms}
        backward: dict[str, _BackwardLink | None] = {target: None}
        forward_frontier: deque[str] = deque(self.system.axioms)
        backward_frontier: deque[str] = deque([target])

        meeting_word: str | None = None
        words_explored = 0

        while forward_frontier or backward_frontier:
            if words_explored >= config.max_words:
                break

            if not backward_frontier or (forward_frontier and len(forward_frontier) <= len(backward_frontier)):
                meeting_word, words_explored = self._expand_forward(
                    forward=forward,
                    backward=backward,
                    frontier=forward_frontier,
                    words_explored=words_explored,
                    max_words=config.max_words,
                )
            else:
                meeting_word, words_explored = self._expand_backward(
                    forward=forward,
                    backward=backward,
                    frontier=backward_frontier,
                    words_explored=words_explored,
                    max_words=config.max_words,
                )

            if meeting_word is not None:
                derivation = self._reconstruct(meeting_word, forward, backward)
                return ReachabilityResult(
                    status=QueryResult.DERIVABLE,
                    derivation=derivation,
                    steps_explored=words_explored,
                    target=target,
                )

        return ReachabilityResult(
            status=QueryResult.NOT_FOUND,
            derivation=None,
            steps_explored=words_explored,
            target=target,
        )

    def _expand_forward(
        self,
        forward: dict[str, Derivation],
        backward: dict[str, _BackwardLink | None],
        frontier: deque[str],
        words_explored: int,
        max_words: int,
    ) -> tuple[str | None, int]:
        if not frontier:
            return None, words_explored

        word = frontier.popleft()
        derivation = forward[word]

        for derived in self._executor.apply_rules_all([DerivedWord(word, derivation)]):
            words_explored += 1
            new_word = derived.word
            if new_word in forward:
                continue
            forward[new_word] = derived.derivation
            if new_word in backward:
                return new_word, words_explored
            frontier.append(new_word)
            if words_explored >= max_words:
                return None, words_explored

        return None, words_explored

    def _expand_backward(
        self,
        forward: dict[str, Derivation],
        backward: dict[str, _BackwardLink | None],
        frontier: deque[str],
        words_explored: int,
        max_words: int,
    ) -> tuple[str | None, int]:
        if not frontier:
            return None, words_explored

        word = frontier.popleft()

        for inverter in self._inverters:
            if not inverter.is_clean or not inverter.rule.is_single_antecedent:
                continue
            for inversion in inverter.invert(word, self._matcher):
                words_explored += 1
                predecessor = inversion.predecessors[0]
                if predecessor in backward:
                    continue
                backward[predecessor] = _BackwardLink(
                    rule=inverter.rule,
                    binding=inversion.binding,
                    next_word=word,
                )
                if predecessor in forward:
                    return predecessor, words_explored
                frontier.append(predecessor)
                if words_explored >= max_words:
                    return None, words_explored

        return None, words_explored

    def _reconstruct(
        self,
        meeting_word: str,
        forward: dict[str, Derivation],
        backward: dict[str, _BackwardLink | None],
    ) -> Derivation:
        steps = list(forward[meeting_word].steps)
        steps.extend(self._walk_backward(meeting_word, backward))
        return Derivation(steps)

    @staticmethod
    def _walk_backward(
        start: str,
        backward: dict[str, _BackwardLink | None],
    ) -> Iterator[DerivationStep]:
        word = start
        link = backward.get(word)
        while link is not None:
            yield DerivationStep(
                inputs=(word, *link.other_inputs),
                rule=link.rule,
                binding=link.binding,
                output=link.next_word,
            )
            word = link.next_word
            link = backward.get(word)
