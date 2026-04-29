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
