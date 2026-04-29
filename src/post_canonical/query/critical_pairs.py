"""Critical-pair detection for Post Canonical Systems.

A *critical pair* arises when two rules can fire on the same word and
produce different reducts. The pair is *joinable* if both reducts can
be reduced (in any number of further steps) to a common word; a
system whose every critical pair is joinable is *locally confluent*,
and (by Newman's lemma) terminating + locally confluent systems are
fully confluent.

This analyzer detects critical pairs *pragmatically* rather than
symbolically: it walks through reachable words from the system and,
for each word, asks the executor which distinct reducts the rules
produce. Each pair of distinct reducts is reported as a critical
pair; joinability is checked by bounded BFS from each reduct, looking
for a shared descendant.

Symbolic critical-pair analysis (overlapping antecedent skeletons,
unifying variable bindings) is not implemented. The pragmatic
approach catches every critical pair that occurs during real
derivations within a depth budget; pairs that arise only on words the
system never reaches in that budget are missed. For most user
systems the budget is enough.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from ..core.rule import ProductionRule
from ..system.derivation import DerivedWord
from ..system.executor import RuleExecutor
from ..system.pcs import PostCanonicalSystem


@dataclass(frozen=True, slots=True)
class CriticalPair:
    """One pair of distinct reducts of the same word.

    ``rule_a`` rewrites ``overlap_word`` to ``reduct_a``;
    ``rule_b`` rewrites it to ``reduct_b``. The two reducts must
    differ. ``joinable`` is ``True`` when both reduce to a common
    descendant within the analyzer's joinability budget;
    ``common_normal_form`` records that descendant when found.
    """

    overlap_word: str
    rule_a: ProductionRule
    rule_b: ProductionRule
    reduct_a: str
    reduct_b: str
    joinable: bool
    common_normal_form: str | None


@dataclass(frozen=True, slots=True)
class ConfluenceReport:
    """Outcome of a confluence sweep.

    ``locally_confluent`` is ``True`` iff every detected critical pair
    is joinable. The flag is sound only for the explored portion of
    the system, since pairs on words outside the budget are not
    inspected; ``notes`` records the budget used so callers can judge
    coverage.
    """

    pairs: tuple[CriticalPair, ...]
    locally_confluent: bool
    notes: str


class CriticalPairAnalyzer:
    """Detect overlapping rules and analyze their joinability.

    The analyzer enumerates reachable words via
    :meth:`PostCanonicalSystem.iterate` up to a depth budget, asks the
    executor for every reduct of each word, and reports any
    word-pair-of-reducts as a critical pair. Joinability is checked
    by a bounded BFS from each reduct.
    """

    def __init__(self, system: PostCanonicalSystem) -> None:
        self.system = system
        self._executor = RuleExecutor(system.alphabet, system.rules)

    def critical_pairs(
        self,
        max_words: int = 200,
        max_join_steps: int = 10,
    ) -> Iterator[CriticalPair]:
        """Yield distinct critical pairs found within the search budget.

        Each yielded pair is canonical: ``rule_a.display_name`` is
        lexicographically <= ``rule_b.display_name``, and pairs whose
        reducts are equal are skipped. Duplicate pairs that arise from
        different overlap words are NOT deduplicated, since each
        overlap is a distinct piece of evidence.
        """
        seen: set[tuple[str, str, str, str, str]] = set()
        for word in self._reachable_words(max_words):
            reducts = self._reducts_per_rule(word)
            yield from self._pairs_from_reducts(word, reducts, seen, max_join_steps)

    def confluence_report(
        self,
        max_words: int = 200,
        max_join_steps: int = 10,
    ) -> ConfluenceReport:
        """Run the analyzer and aggregate into a confluence verdict."""
        pairs = tuple(self.critical_pairs(max_words=max_words, max_join_steps=max_join_steps))
        locally_confluent = all(pair.joinable for pair in pairs)
        notes = (
            f"Inspected up to {max_words} reachable words with joinability budget "
            f"{max_join_steps}. Found {len(pairs)} critical pair(s)."
        )
        if not all(rule.is_single_antecedent for rule in self.system.rules):
            notes += " Multi-antecedent rules are not analyzed."
        return ConfluenceReport(pairs=pairs, locally_confluent=locally_confluent, notes=notes)

    def _reachable_words(self, max_words: int) -> Iterator[str]:
        for index, derived in enumerate(self.system.iterate()):
            if index >= max_words:
                return
            yield derived.word

    def _reducts_per_rule(self, word: str) -> dict[ProductionRule, frozenset[str]]:
        """Return the distinct outputs each single-antecedent rule produces from ``word``."""
        reducts: dict[ProductionRule, set[str]] = {}
        seed = DerivedWord.axiom(word)
        for derived in self._executor.apply_rules_all([seed]):
            if derived.derivation.steps:
                step = derived.derivation.steps[-1]
                if step.rule.is_single_antecedent:
                    reducts.setdefault(step.rule, set()).add(derived.word)
        return {rule: frozenset(outputs) for rule, outputs in reducts.items()}

    def _pairs_from_reducts(
        self,
        word: str,
        reducts: dict[ProductionRule, frozenset[str]],
        seen: set[tuple[str, str, str, str, str]],
        max_join_steps: int,
    ) -> Iterator[CriticalPair]:
        rules = sorted(reducts, key=lambda r: r.display_name)
        for i, rule_a in enumerate(rules):
            for rule_b in rules[i:]:
                for reduct_a in reducts[rule_a]:
                    for reduct_b in reducts[rule_b]:
                        if reduct_a == reduct_b:
                            continue
                        if rule_a is rule_b and reduct_a >= reduct_b:
                            continue
                        key = (word, rule_a.display_name, rule_b.display_name, reduct_a, reduct_b)
                        if key in seen:
                            continue
                        seen.add(key)
                        common = self._find_common_descendant(reduct_a, reduct_b, max_join_steps)
                        yield CriticalPair(
                            overlap_word=word,
                            rule_a=rule_a,
                            rule_b=rule_b,
                            reduct_a=reduct_a,
                            reduct_b=reduct_b,
                            joinable=common is not None,
                            common_normal_form=common,
                        )

    def _find_common_descendant(self, a: str, b: str, max_steps: int) -> str | None:
        """Return a word reachable from both ``a`` and ``b`` within ``max_steps`` BFS layers."""
        if a == b:
            return a

        seen_a = {a}
        seen_b = {b}
        frontier_a = {a}
        frontier_b = {b}
        for _ in range(max_steps):
            if not frontier_a and not frontier_b:
                break
            frontier_a = self._bfs_layer(frontier_a, seen_a)
            if shared := frontier_a & seen_b:
                return min(shared)
            frontier_b = self._bfs_layer(frontier_b, seen_b)
            if shared := frontier_b & seen_a:
                return min(shared)
        return None

    def _bfs_layer(self, frontier: set[str], seen: set[str]) -> set[str]:
        """Apply every single-antecedent rule once to each frontier word."""
        new_layer: set[str] = set()
        if not frontier:
            return new_layer
        seeds = [DerivedWord.axiom(word) for word in frontier]
        for derived in self._executor.apply_rules_all(seeds):
            if derived.word not in seen:
                seen.add(derived.word)
                new_layer.add(derived.word)
        return new_layer
