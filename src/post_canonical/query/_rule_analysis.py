"""Shared rule introspection used by analysis modules in :mod:`query`.

The helpers here describe a rule's *shape* without depending on the
matcher or the executor: how many times each variable appears on each
side, what symbols the constant skeleton carries, and how those numbers
constrain the change in word length under any binding.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from ..core.pattern import Pattern
from ..core.rule import ProductionRule
from ..core.variable import Variable


def _variable_counter(patterns: Iterable[Pattern]) -> Counter[str]:
    """Multiplicity of each variable name across the given patterns."""
    counter: Counter[str] = Counter()
    for pattern in patterns:
        for elem in pattern.elements:
            if isinstance(elem, Variable):
                counter[elem.name] += 1
    return counter


def variable_multiplicity(rule: ProductionRule) -> dict[str, tuple[int, int]]:
    """Return ``{var_name: (m_antecedent, m_consequent)}`` for every variable.

    The antecedent count sums multiplicities across all antecedent
    patterns; consequent is a single pattern. Variables not appearing on
    a side are recorded with ``0``.
    """
    antecedent_counts = _variable_counter(rule.antecedents)
    consequent_counts = _variable_counter([rule.consequent])
    names = set(antecedent_counts) | set(consequent_counts)
    return {name: (antecedent_counts[name], consequent_counts[name]) for name in names}


def variable_min_lengths(rule: ProductionRule) -> dict[str, int]:
    """Map each variable name in the rule to its kind-imposed minimum length."""
    return {var.name: var.min_length() for var in rule.all_variables}


@dataclass(frozen=True, slots=True)
class LengthBounds:
    """Worst- and best-case length change a rule can produce.

    Each bound is ``None`` when no finite bound exists in that direction:
    ``max_delta is None`` when a variable appears more times on the
    consequent (binding can grow without limit), and ``min_delta is None``
    when it appears more times on the antecedents (binding shed grows
    without limit). The bounds are computed against the sum of antecedent
    word lengths, so multi-antecedent rules are accommodated naturally.
    """

    min_delta: int | None
    max_delta: int | None

    @property
    def is_strictly_decreasing(self) -> bool:
        """True when every application of the rule shortens the total word size."""
        return self.max_delta is not None and self.max_delta < 0


def rule_length_bounds(rule: ProductionRule) -> LengthBounds:
    """Compute tight bounds on ``len(consequent) - sum(len(antecedents))``."""
    constant_delta = sum(len(elem) for elem in rule.consequent.elements if isinstance(elem, str)) - sum(
        len(elem) for ante in rule.antecedents for elem in ante.elements if isinstance(elem, str)
    )

    min_delta: int | None = constant_delta
    max_delta: int | None = constant_delta

    min_lengths = variable_min_lengths(rule)
    for name, (m_a, m_c) in variable_multiplicity(rule).items():
        coefficient = m_c - m_a
        if coefficient == 0:
            continue
        v_min = min_lengths.get(name, 0)
        if coefficient > 0:
            if min_delta is not None:
                min_delta += coefficient * v_min
            max_delta = None
        else:
            if max_delta is not None:
                max_delta += coefficient * v_min
            min_delta = None

    return LengthBounds(min_delta=min_delta, max_delta=max_delta)


def is_closed_rule(rule: ProductionRule) -> bool:
    """True iff every variable appears the same number of times on both sides.

    Closed rules have a fixed symbol-delta vector that does not depend on
    variable bindings, the well-behaved case for invariant discovery.
    """
    return all(m_a == m_c for m_a, m_c in variable_multiplicity(rule).values())


def constant_symbol_counts(pattern: Pattern) -> Counter[str]:
    """Symbol counts contributed by the pattern's constant elements only."""
    counter: Counter[str] = Counter()
    for elem in pattern.elements:
        if isinstance(elem, str):
            counter.update(elem)
    return counter


def antecedent_constants(rule: ProductionRule) -> Counter[str]:
    """Symbol counts from the constant skeleton of every antecedent combined."""
    total: Counter[str] = Counter()
    for ante in rule.antecedents:
        total += constant_symbol_counts(ante)
    return total


def rule_constant_delta(rule: ProductionRule) -> dict[str, int] | None:
    """Symbol delta from constants alone, or ``None`` for non-closed rules.

    For closed rules the variable contributions cancel, so the returned
    mapping equals ``count_s(consequent) - count_s(antecedent_total)``
    over every alphabet symbol the rule touches. Only non-zero entries
    are included.
    """
    if not is_closed_rule(rule):
        return None
    ac = antecedent_constants(rule)
    cc = constant_symbol_counts(rule.consequent)
    return {symbol: d for symbol in ac | cc if (d := cc[symbol] - ac[symbol]) != 0}


@dataclass(frozen=True, slots=True)
class AffineTransition:
    """Per-symbol affine transition induced by a single rule.

    ``alpha`` and ``beta`` describe how each alphabet symbol's count
    changes in the consequent: ``count_s(new) = alpha[s] + beta *
    count_s(old)``. Symbols absent from ``alpha`` are unaffected
    (``alpha=0``); ``beta`` is uniform across symbols since the rule
    shapes we model scale every symbol's contribution by the same
    multiplicity ratio.
    """

    alpha: dict[str, int]
    beta: int


def affine_transition(rule: ProductionRule) -> AffineTransition | None:
    """Compute the rule's per-symbol affine transition, or ``None`` if non-affine.

    A rule is affine when its action on symbol counts can be written as
    ``count_s(new) = alpha[s] + beta * count_s(old)`` with constants
    ``alpha[s]`` and ``beta``. Closed rules satisfy this trivially with
    ``beta = 1``; single-antecedent rules with one variable whose
    consequent multiplicity is an integer multiple of its antecedent
    multiplicity satisfy it with ``beta = m_C / m_A``. Multi-variable
    non-closed rules don't reduce to a per-symbol affine form because
    the new count depends on individual variable contents that the
    word-level count alone can't recover.
    """
    if not rule.is_single_antecedent:
        return None
    if is_closed_rule(rule):
        beta = 1
    else:
        # When the rule has multiple variables, count_s(input) cannot
        # be split back into per-variable contributions, so no
        # per-symbol affine form exists. Restrict the non-closed case
        # to single-variable rules with integer multiplicity ratio.
        multiplicities = variable_multiplicity(rule)
        if len(multiplicities) != 1:
            return None
        m_a, m_c = next(iter(multiplicities.values()))
        if m_a == 0 or m_c % m_a != 0:
            return None
        beta = m_c // m_a

    ac = antecedent_constants(rule)
    cc = constant_symbol_counts(rule.consequent)
    # count_s(input)  = ac[s] + m_a * count_s(binding)
    # count_s(output) = cc[s] + m_c * count_s(binding)
    #                 = (cc[s] - beta * ac[s]) + beta * count_s(input)
    alpha = {s: cc[s] - beta * ac[s] for s in ac | cc}
    return AffineTransition(alpha=alpha, beta=beta)
