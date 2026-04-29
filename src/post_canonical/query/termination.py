"""Termination analysis for Post Canonical Systems.

Termination - "does every derivation chain end?" - is undecidable in
general. The checker here returns sound but incomplete certificates: a
``TERMINATING`` verdict is always backed by a witness (a weight function
or a length argument) and is mathematically rigorous; ``NON_TERMINATING``
is only reported for trivially-looping rules; everything else is
``UNKNOWN``.

Three certificates are tried in order, fastest first:

1. **Length strictly decreasing** - every rule application shrinks the
   total word size. Decidable from rule shape alone.
2. **Weight function** - assign each alphabet symbol a positive weight
   so that every rule strictly reduces the weighted symbol total.
   Brute-searched over small weight vectors.
3. **Identity-rule detection** - a single rule whose antecedent equals
   its consequent loops on every match.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from itertools import product

from ..core.rule import ProductionRule
from ..system.pcs import PostCanonicalSystem
from ._rule_analysis import (
    rule_length_bounds,
    variable_multiplicity,
)


class TerminationStatus(StrEnum):
    """Outcome of a termination check."""

    TERMINATING = "terminating"
    NON_TERMINATING = "non_terminating"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TerminationCertificate:
    """Outcome of a termination check, with a witness when one exists.

    ``method`` names the technique that produced the verdict
    (``"length_strict_decrease"``, ``"weight_function"``,
    ``"identity_rule"``, or ``"no_certificate"``); ``witness`` is the
    concrete object the technique produced (the weight vector, the
    looping rule's name, …).
    """

    status: TerminationStatus
    method: str
    witness: Mapping[str, int] | str | None
    explanation: str


class TerminationChecker:
    """Run termination certificates against a Post canonical system.

    Each ``check_*`` method runs a single certificate; ``check()`` runs
    them in increasing order of cost and returns the first definitive
    answer. All checks are sound: ``TERMINATING`` and
    ``NON_TERMINATING`` verdicts are guaranteed correct; ``UNKNOWN`` is
    a true "I don't know," not a false negative.
    """

    def __init__(self, system: PostCanonicalSystem) -> None:
        self.system = system

    def check_length_decreasing(self) -> TerminationCertificate:
        """Verify every rule strictly reduces the total word length.

        This is the cheapest certificate: derivable in linear time from
        rule shape, with no search.
        """
        offending: list[str] = []
        for rule in self.system.rules:
            bounds = rule_length_bounds(rule)
            if not bounds.is_strictly_decreasing:
                offending.append(rule.display_name)

        if not offending:
            return TerminationCertificate(
                status=TerminationStatus.TERMINATING,
                method="length_strict_decrease",
                witness=None,
                explanation=(
                    "Every rule strictly reduces the total word length, so derivations cannot grow without bound."
                ),
            )

        return TerminationCertificate(
            status=TerminationStatus.UNKNOWN,
            method="no_certificate",
            witness=None,
            explanation=(f"Rules without a guaranteed length decrease: {', '.join(sorted(offending))}."),
        )

    def check_weight_function(self, max_weight: int = 5) -> TerminationCertificate:
        """Search for a positive integer weight vector that bounds the system.

        A weight vector ``w`` certifies termination when, for every rule,
        the weighted total of the consequent is strictly less than the
        weighted total of the antecedents over *every* possible binding.
        Search is brute-force over ``[1, max_weight]^|alphabet|``.

        Rules that grow in variable multiplicity (some variable
        appearing more times on the consequent than on the antecedents)
        cannot be bounded by any fixed weight vector, so the search
        skips straight to ``UNKNOWN`` when one is present.
        """
        for rule in self.system.rules:
            if any(m_c > m_a for m_a, m_c in variable_multiplicity(rule).values()):
                return TerminationCertificate(
                    status=TerminationStatus.UNKNOWN,
                    method="no_certificate",
                    witness=None,
                    explanation=(
                        f"Rule '{rule.display_name}' grows a variable's multiplicity, "
                        "so no fixed weight function can dominate its weight delta."
                    ),
                )

        symbols = tuple(self.system.alphabet)
        for weight_tuple in product(range(1, max_weight + 1), repeat=len(symbols)):
            weights = dict(zip(symbols, weight_tuple, strict=True))
            if all(_max_weight_delta(rule, weights) < 0 for rule in self.system.rules):
                return TerminationCertificate(
                    status=TerminationStatus.TERMINATING,
                    method="weight_function",
                    witness=weights,
                    explanation=f"Every rule strictly reduces total symbol weight under {weights}.",
                )

        return TerminationCertificate(
            status=TerminationStatus.UNKNOWN,
            method="no_certificate",
            witness=None,
            explanation=f"No weight function found with weights in [1, {max_weight}].",
        )

    def check_identity_rules(self) -> TerminationCertificate:
        """Flag rules whose consequent is structurally identical to an antecedent.

        Such a rule fires on any matching word and returns the same
        word, so it can be applied indefinitely. This catches trivial
        non-termination; multi-rule cycles are out of scope.
        """
        for rule in self.system.rules:
            if rule.is_single_antecedent and rule.antecedents[0].elements == rule.consequent.elements:
                return TerminationCertificate(
                    status=TerminationStatus.NON_TERMINATING,
                    method="identity_rule",
                    witness=rule.display_name,
                    explanation=(
                        f"Rule '{rule.display_name}' has identical antecedent and consequent, "
                        "so it loops on any matching word."
                    ),
                )

        return TerminationCertificate(
            status=TerminationStatus.UNKNOWN,
            method="no_certificate",
            witness=None,
            explanation="No identity rules detected.",
        )

    def check(self, max_weight: int = 5) -> TerminationCertificate:
        """Try certificates in cost order and return the first definitive verdict.

        Order: identity-rule check (linear), length-decreasing (linear),
        weight-function (brute search, dominant cost). The combined
        result is the strongest verdict any check produced; if all are
        ``UNKNOWN``, the combined explanation aggregates the misses.
        """
        identity = self.check_identity_rules()
        if identity.status is TerminationStatus.NON_TERMINATING:
            return identity

        length = self.check_length_decreasing()
        if length.status is TerminationStatus.TERMINATING:
            return length

        weight = self.check_weight_function(max_weight=max_weight)
        if weight.status is TerminationStatus.TERMINATING:
            return weight

        return TerminationCertificate(
            status=TerminationStatus.UNKNOWN,
            method="no_certificate",
            witness=None,
            explanation=(
                f"No certificate found. Length check: {length.explanation} Weight check: {weight.explanation}"
            ),
        )


def _max_weight_delta(rule: ProductionRule, weights: Mapping[str, int]) -> int:
    """Tight upper bound on ``weight(consequent) - weight(antecedents)``.

    The constant skeleton contributes a fixed delta. Each variable with
    a negative multiplicity coefficient contributes at most
    ``coefficient * v_min * min(weights)``: the binding has to be at
    least ``v_min`` characters, and the smallest possible weight per
    character is ``min(weights)``. Variables with zero coefficient
    cancel; positive coefficients are filtered upstream.
    """
    constant_delta = 0
    for elem in rule.consequent.elements:
        if isinstance(elem, str):
            constant_delta += sum(weights[c] for c in elem)
    for ante in rule.antecedents:
        for elem in ante.elements:
            if isinstance(elem, str):
                constant_delta -= sum(weights[c] for c in elem)

    min_weight = min(weights.values())

    var_contribution = 0
    for name, (m_a, m_c) in variable_multiplicity(rule).items():
        coefficient = m_c - m_a
        if coefficient >= 0:
            continue
        v_min = _min_length(rule, name)
        # coefficient is negative, so coefficient * v_min * min_weight is
        # the most positive (largest) value the variable can contribute.
        var_contribution += coefficient * v_min * min_weight

    return constant_delta + var_contribution


def _min_length(rule: ProductionRule, name: str) -> int:
    """Minimum number of characters a variable's binding must contain."""
    for var in rule.all_variables:
        if var.name == name:
            return var.min_length()
    return 0
