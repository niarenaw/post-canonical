"""Shared rule introspection used by termination, invariants, and friends.

The helpers in this module tear a :class:`ProductionRule` apart into the
two pieces that downstream analyses care about: the contribution of its
constant symbols and the per-variable multiplicities. Once you know how
many times each variable appears on each side of a rule, you can answer
questions like "is the symbol delta a fixed vector?" and "can the length
ever grow unboundedly under this rule?" without re-walking the patterns.

These helpers deliberately stay free of any dependency on the executor
or the matching engine - they reason about a rule's *shape*, not its
runtime behaviour.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from ..core.pattern import Pattern
from ..core.rule import ProductionRule
from ..core.variable import Variable


def _constant_counter(pattern: Pattern) -> Counter[str]:
    """Symbol counts contributed by the pattern's constant elements only."""
    counter: Counter[str] = Counter()
    for elem in pattern.elements:
        if isinstance(elem, str):
            counter.update(elem)
    return counter


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


def is_closed_rule(rule: ProductionRule) -> bool:
    """True iff every variable appears the same number of times on both sides.

    Closed rules have a fixed symbol-delta vector that does not depend on
    variable bindings. They are the well-behaved case for invariant
    discovery and length analysis.
    """
    return all(m_a == m_c for m_a, m_c in variable_multiplicity(rule).values())


def rule_constant_delta(rule: ProductionRule) -> dict[str, int] | None:
    """Symbol-count delta from constants alone, or ``None`` for non-closed rules.

    For closed rules the returned mapping equals ``count_s(consequent) -
    count_s(antecedent)`` over all alphabet symbols, since variable
    contributions cancel. The returned dict only contains symbols whose
    delta is non-zero.
    """
    if not is_closed_rule(rule):
        return None

    antecedent_constants: Counter[str] = Counter()
    for ante in rule.antecedents:
        antecedent_constants += _constant_counter(ante)
    consequent_constants = _constant_counter(rule.consequent)

    delta: dict[str, int] = {}
    for symbol in set(antecedent_constants) | set(consequent_constants):
        d = consequent_constants[symbol] - antecedent_constants[symbol]
        if d != 0:
            delta[symbol] = d
    return delta


@dataclass(frozen=True, slots=True)
class LengthBounds:
    """Worst- and best-case length change a rule can produce.

    ``max_delta`` is ``None`` when a variable has higher multiplicity on
    the consequent side, since the binding can grow without bound. The
    bounds are computed against the sum of antecedent word lengths, so
    multi-antecedent rules are accommodated naturally.
    """

    min_delta: int | None
    max_delta: int | None

    @property
    def is_strictly_decreasing(self) -> bool:
        """True when every application of the rule shortens the total word size."""
        return self.max_delta is not None and self.max_delta < 0


def _variable_min_length(rule: ProductionRule, name: str) -> int:
    """Return the minimum number of characters a variable's binding must contain."""
    for var in rule.all_variables:
        if var.name == name:
            return var.min_length()
    return 0


def rule_length_bounds(rule: ProductionRule) -> LengthBounds:
    """Compute tight bounds on ``len(consequent) - sum(len(antecedents))``.

    The constant skeleton contributes a fixed delta. Each variable
    contributes ``(m_C - m_A) * |binding|`` to the length change; bounds
    on ``|binding|`` come from the variable kind (``ANY`` permits zero,
    ``NON_EMPTY``/``SINGLE`` force at least one).
    """
    constant_delta = sum(len(elem) for elem in rule.consequent.elements if isinstance(elem, str)) - sum(
        len(elem) for ante in rule.antecedents for elem in ante.elements if isinstance(elem, str)
    )

    min_delta: int | None = constant_delta
    max_delta: int | None = constant_delta

    for name, (m_a, m_c) in variable_multiplicity(rule).items():
        coefficient = m_c - m_a
        if coefficient == 0:
            continue
        v_min = _variable_min_length(rule, name)
        if coefficient > 0:
            # Consequent multiplies the variable; the binding can be
            # arbitrarily long, so the length grows without bound above.
            if min_delta is not None:
                min_delta += coefficient * v_min
            max_delta = None
        else:
            # Consequent uses fewer copies; the longer the binding, the
            # more length is shed, so the lower bound vanishes.
            if max_delta is not None:
                max_delta += coefficient * v_min
            min_delta = None

    return LengthBounds(min_delta=min_delta, max_delta=max_delta)


def is_affine_rule(rule: ProductionRule) -> bool:
    """True when the rule's per-symbol residue transition is affine in the input.

    A rule is affine for residue analysis when the new count of every
    symbol can be written as ``alpha + beta * old_count`` with constant
    ``alpha, beta``. This is satisfied when:

    - The rule is closed (``beta = 1`` for every symbol), or
    - The rule has a single variable with integer multiplicity ratio
      ``m_C / m_A`` (``beta`` is that ratio, applied uniformly to every
      symbol).

    Multi-variable rules with mixed multiplicities don't reduce to a
    per-symbol affine form because the new count depends on individual
    variable contents, which the input word-count alone can't recover.
    """
    if not rule.is_single_antecedent:
        return False
    if is_closed_rule(rule):
        return True

    multiplicities = variable_multiplicity(rule)
    differing = [(m_a, m_c) for m_a, m_c in multiplicities.values() if m_a != m_c]
    if len(differing) != 1:
        return False

    m_a, m_c = differing[0]
    if m_a == 0:
        # Variable appears only on the consequent: there is no "old" content
        # to scale, so the rule isn't expressible as alpha + beta * old.
        return False
    return m_c % m_a == 0


@dataclass(frozen=True, slots=True)
class AffineTransition:
    """Per-symbol affine transition induced by a single rule.

    ``alpha[s]`` and ``beta[s]`` describe the new symbol count under
    application of the rule: ``count_s(new) = alpha[s] + beta[s] *
    count_s(old)``. The mapping covers every alphabet symbol the rule
    touches; symbols absent from both ``alpha`` and ``beta`` are
    untouched (i.e. ``alpha=0, beta=1``).
    """

    alpha: dict[str, int]
    beta: int  # uniform across symbols for the rule shapes we model


def affine_transition(rule: ProductionRule) -> AffineTransition | None:
    """Compute the affine transition for an :func:`is_affine_rule` rule.

    Returns ``None`` for rules that don't satisfy :func:`is_affine_rule`,
    so callers can filter rules without re-running the classification.
    """
    if not is_affine_rule(rule):
        return None

    antecedent_constants: Counter[str] = Counter()
    for ante in rule.antecedents:
        antecedent_constants += _constant_counter(ante)
    consequent_constants = _constant_counter(rule.consequent)

    if is_closed_rule(rule):
        beta = 1
    else:
        # The single variable with differing multiplicity sets the slope.
        multiplicities = variable_multiplicity(rule)
        m_a, m_c = next((m_a, m_c) for m_a, m_c in multiplicities.values() if m_a != m_c)
        beta = m_c // m_a

    # For symbol s with input word w under a single-antecedent rule:
    #   count_s(w)      = ac_const_s + m_a * count_s(binding)
    #   count_s(output) = cc_const_s + m_c * count_s(binding)
    # Solving for count_s(binding) and substituting:
    #   count_s(output) = (cc_const_s - beta * ac_const_s) + beta * count_s(w).
    # When the rule is closed, beta == 1 and this collapses to the constant delta.
    alpha = {
        s: consequent_constants[s] - beta * antecedent_constants[s]
        for s in set(antecedent_constants) | set(consequent_constants)
    }
    return AffineTransition(alpha=alpha, beta=beta)
