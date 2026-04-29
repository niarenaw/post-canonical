"""Invariant discovery for Post Canonical Systems.

The analyzer reports two kinds of invariants:

- **Linear invariants** ``f(w) = sum(c[s] * count_s(w))`` that are
  preserved exactly by every rule application. These are sound only
  when every rule is *closed* (each variable appears the same number of
  times on both sides), because non-closed rules introduce binding-
  dependent terms that no fixed coefficient vector can dominate.
- **Residue invariants** capturing the set of reachable residue tuples
  in ``(Z/k)^|alphabet|``. This is the multiplicative case that catches
  the famous MU-puzzle ``I-count mod 3`` invariant: the doubler rule
  ``Mx -> Mxx`` is not closed, but it is *affine* in residues - it
  multiplies the I-count by 2 - so a finite-state BFS over residue
  tuples finds the reachable subset and proves any target outside it
  unreachable.

Both certificates are sound in the standard sense: a discovered
invariant is guaranteed to hold; ``prove_unreachable`` only returns an
invariant when it conclusively rules the target out. When some rules
are too unstructured for either analysis (multi-variable rules with
mixed multiplicities), they appear in :attr:`InvariantReport.excluded_rules`
and the report explains that no sound conclusions can be drawn.
"""

from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import product

from ..core.rule import ProductionRule
from ..system.pcs import PostCanonicalSystem
from ._rule_analysis import (
    AffineTransition,
    affine_transition,
    is_closed_rule,
    rule_constant_delta,
)


@dataclass(frozen=True, slots=True)
class LinearInvariant:
    """A linear function of symbol counts that is constant across reachable words.

    ``coefficients`` map alphabet symbols to integers; ``f(w) = sum(c[s]
    * count_s(w))`` evaluates to ``constant_value`` for every reachable
    word. When ``modulus is None`` the invariant is exact; otherwise
    ``f(w) mod modulus == constant_value``.
    """

    coefficients: dict[str, int]
    modulus: int | None
    constant_value: int

    def evaluate(self, word: str) -> int:
        """Compute ``f(word)``, reducing modulo ``self.modulus`` when set."""
        value = sum(self.coefficients.get(symbol, 0) * count for symbol, count in Counter(word).items())
        if self.modulus is not None:
            return value % self.modulus
        return value

    def admits(self, word: str) -> bool:
        """True when the word's value matches the invariant's constant value."""
        return self.evaluate(word) == self.constant_value


@dataclass(frozen=True, slots=True)
class ResidueInvariant:
    """The set of reachable residue tuples modulo ``k`` over the alphabet.

    A residue invariant is informative when the reachable set is a
    *strict* subset of ``(Z/k)^|alphabet|``: targets whose residue
    tuple is missing cannot be derived. For the MU puzzle at ``k=3``
    the reachable set excludes any residue with ``count_I mod 3 == 0``,
    so target ``MU`` (residue ``(0, 1, 1)`` over ``('I', 'M', 'U')``)
    is provably unreachable.
    """

    modulus: int
    alphabet_order: tuple[str, ...]
    reachable_residues: frozenset[tuple[int, ...]]
    full_space_size: int

    def residue_of(self, word: str) -> tuple[int, ...]:
        """Compute the residue tuple of ``word`` under this invariant's ordering."""
        counts = Counter(word)
        return tuple(counts[symbol] % self.modulus for symbol in self.alphabet_order)

    def admits(self, word: str) -> bool:
        """True when ``word``'s residue is among the reachable tuples."""
        return self.residue_of(word) in self.reachable_residues


@dataclass(frozen=True, slots=True)
class InvariantReport:
    """Outcome of running invariant discovery against a system."""

    linear: tuple[LinearInvariant, ...]
    residue: tuple[ResidueInvariant, ...]
    excluded_rules: tuple[str, ...]
    notes: str

    @property
    def is_complete(self) -> bool:
        """True when every rule was analyzable; reports apply to the full system."""
        return not self.excluded_rules


class InvariantAnalyzer:
    """Discover and apply invariants of a Post canonical system."""

    def __init__(self, system: PostCanonicalSystem) -> None:
        self.system = system
        self._cached_report: InvariantReport | None = None

    def discover(self, max_modulus: int = 6, linear_bound: int = 3) -> InvariantReport:
        """Run linear and residue discovery and return the cached report.

        ``max_modulus`` caps the moduli tried for residue analysis;
        ``linear_bound`` bounds the absolute value of integer
        coefficients searched for linear invariants. Both default to
        small values that keep discovery fast on typical 2-5 symbol
        alphabets.
        """
        if self._cached_report is None:
            self._cached_report = self._compute_report(max_modulus=max_modulus, linear_bound=linear_bound)
        return self._cached_report

    def prove_unreachable(self, target: str) -> LinearInvariant | ResidueInvariant | None:
        """Return an invariant that excludes ``target``, or ``None``.

        The check is sound only when the report is complete (no
        excluded rules); otherwise the invariants describe a
        sub-system, not the full one, and ``None`` is returned to
        avoid false positives.
        """
        report = self.discover()
        if not report.is_complete:
            return None

        for inv in report.linear:
            if not inv.admits(target):
                return inv
        for inv in report.residue:
            if not inv.admits(target):
                return inv
        return None

    def _compute_report(self, max_modulus: int, linear_bound: int) -> InvariantReport:
        rules = tuple(self.system.rules)
        transitions: list[AffineTransition] = []
        excluded: list[str] = []
        for rule in rules:
            transition = affine_transition(rule)
            if transition is None:
                excluded.append(rule.display_name)
            else:
                transitions.append(transition)
        excluded_sorted = tuple(sorted(excluded))

        linear = (
            self._discover_linear(rules, linear_bound, max_modulus) if all(is_closed_rule(r) for r in rules) else ()
        )
        residue = self._discover_residue(transitions, max_modulus) if not excluded else ()

        notes = _build_notes(
            excluded=excluded_sorted,
            linear_count=len(linear),
            residue_count=len(residue),
            all_closed=all(is_closed_rule(r) for r in rules),
        )
        return InvariantReport(linear=linear, residue=residue, excluded_rules=excluded_sorted, notes=notes)

    def _discover_linear(
        self,
        rules: Iterable[ProductionRule],
        bound: int,
        max_modulus: int,
    ) -> tuple[LinearInvariant, ...]:
        deltas = [rule_constant_delta(rule) or {} for rule in rules]
        symbols = tuple(self.system.alphabet)
        axioms = tuple(self.system.axioms)
        if not axioms:
            return ()

        results: list[LinearInvariant] = []

        for coeffs in _enumerate_primitive_coefficients(symbols, bound):
            if not all(_dot(coeffs, delta) == 0 for delta in deltas):
                continue
            values = {sum(coeffs[s] * Counter(axiom)[s] for s in symbols) for axiom in axioms}
            if len(values) != 1:
                continue
            results.append(
                LinearInvariant(
                    coefficients=dict(coeffs),
                    modulus=None,
                    constant_value=next(iter(values)),
                )
            )

        for k in range(2, max_modulus + 1):
            for coeffs in _enumerate_residue_coefficients(symbols, k):
                if not all(_dot(coeffs, delta) % k == 0 for delta in deltas):
                    continue
                values = {sum(coeffs[s] * Counter(axiom)[s] for s in symbols) % k for axiom in axioms}
                if len(values) != 1:
                    continue
                if any(
                    inv.modulus is None and _dot(inv.coefficients, coeffs) != 0
                    for inv in results
                    if inv.modulus is None
                ):
                    # The coefficient vector is already explained by an exact
                    # invariant: skip mod-k duplicates of the same direction.
                    continue
                results.append(
                    LinearInvariant(
                        coefficients=dict(coeffs),
                        modulus=k,
                        constant_value=next(iter(values)),
                    )
                )
        return tuple(results)

    def _discover_residue(
        self,
        transitions: list[AffineTransition],
        max_modulus: int,
    ) -> tuple[ResidueInvariant, ...]:
        alphabet_order = tuple(self.system.alphabet)
        results: list[ResidueInvariant] = []

        for k in range(2, max_modulus + 1):
            reachable = _reachable_residues(
                axioms=self.system.axioms,
                transitions=transitions,
                alphabet_order=alphabet_order,
                modulus=k,
            )
            full_size = k ** len(alphabet_order)
            if len(reachable) < full_size:
                results.append(
                    ResidueInvariant(
                        modulus=k,
                        alphabet_order=alphabet_order,
                        reachable_residues=frozenset(reachable),
                        full_space_size=full_size,
                    )
                )
        return tuple(results)


def _dot(a: dict[str, int], b: dict[str, int]) -> int:
    return sum(a.get(s, 0) * b.get(s, 0) for s in set(a) | set(b))


def _enumerate_primitive_coefficients(symbols: tuple[str, ...], bound: int) -> Iterator[dict[str, int]]:
    """Yield non-trivial integer coefficient vectors with ``|c[s]| <= bound``.

    Vectors with a non-unit gcd are scalar multiples of smaller ones;
    we filter those out so callers see one representative per direction.
    The first non-zero coefficient is forced positive to dedupe sign-
    flipped pairs.
    """
    n = len(symbols)
    for values in product(range(-bound, bound + 1), repeat=n):
        if not any(values):
            continue
        first_nonzero = next(v for v in values if v != 0)
        if first_nonzero < 0:
            continue
        if _gcd_many(abs(v) for v in values if v != 0) != 1:
            continue
        yield dict(zip(symbols, values, strict=True))


def _enumerate_residue_coefficients(symbols: tuple[str, ...], modulus: int) -> Iterator[dict[str, int]]:
    """Yield non-trivial coefficient vectors over ``Z/modulus``.

    The first non-zero coordinate is forced into the smaller half of
    the residue range so we don't double-count ``c`` and ``-c``.
    """
    n = len(symbols)
    for values in product(range(modulus), repeat=n):
        if not any(values):
            continue
        first_nonzero = next(v for v in values if v != 0)
        if first_nonzero > modulus // 2:
            continue
        yield dict(zip(symbols, values, strict=True))


def _gcd_many(values: Iterable[int]) -> int:
    from math import gcd

    result = 0
    for v in values:
        result = gcd(result, v)
    return result or 1


def _reachable_residues(
    axioms: Iterable[str],
    transitions: list[AffineTransition],
    alphabet_order: tuple[str, ...],
    modulus: int,
) -> set[tuple[int, ...]]:
    initial = {tuple(Counter(axiom)[s] % modulus for s in alphabet_order) for axiom in axioms}
    seen = set(initial)
    frontier = list(initial)
    while frontier:
        next_frontier: list[tuple[int, ...]] = []
        for state in frontier:
            for transition in transitions:
                new_state = tuple(
                    (transition.alpha.get(symbol, 0) + transition.beta * state[i]) % modulus
                    for i, symbol in enumerate(alphabet_order)
                )
                if new_state not in seen:
                    seen.add(new_state)
                    next_frontier.append(new_state)
        frontier = next_frontier
    return seen


def _build_notes(
    excluded: tuple[str, ...],
    linear_count: int,
    residue_count: int,
    all_closed: bool,
) -> str:
    parts: list[str] = []
    if excluded:
        parts.append(
            f"Rules excluded from analysis (not affine): {', '.join(excluded)}. "
            "Discovered invariants apply only to the analyzable subsystem."
        )
    elif not all_closed:
        parts.append(
            "System contains non-closed rules; linear-invariant search is "
            "restricted to closed-only systems and was skipped."
        )
    parts.append(f"Found {linear_count} linear invariant(s) and {residue_count} residue invariant(s).")
    return " ".join(parts)
