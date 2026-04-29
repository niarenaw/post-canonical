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
    variable_min_lengths,
    variable_multiplicity,
)


class TerminationStatus(StrEnum):
    """Outcome of a termination check."""

    TERMINATING = "terminating"
    NON_TERMINATING = "non_terminating"
    UNKNOWN = "unknown"


class TerminationMethod(StrEnum):
    """Which technique produced a termination certificate."""

    LENGTH_STRICT_DECREASE = "length_strict_decrease"
    WEIGHT_FUNCTION = "weight_function"
    IDENTITY_RULE = "identity_rule"
    NO_CERTIFICATE = "no_certificate"


@dataclass(frozen=True, slots=True)
class TerminationCertificate:
    """Outcome of a termination check, with a witness when one exists.

    ``witness`` is the concrete object the technique produced - the
    weight vector for ``WEIGHT_FUNCTION``, the looping rule's name for
    ``IDENTITY_RULE``, ``None`` for length and no-certificate verdicts.
    """

    status: TerminationStatus
    method: TerminationMethod
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
        """Verify every rule strictly reduces the total word length."""
        offending = [
            rule.display_name for rule in self.system.rules if not rule_length_bounds(rule).is_strictly_decreasing
        ]

        if not offending:
            return TerminationCertificate(
                status=TerminationStatus.TERMINATING,
                method=TerminationMethod.LENGTH_STRICT_DECREASE,
                witness=None,
                explanation=(
                    "Every rule strictly reduces the total word length, so derivations cannot grow without bound."
                ),
            )

        return TerminationCertificate(
            status=TerminationStatus.UNKNOWN,
            method=TerminationMethod.NO_CERTIFICATE,
            witness=None,
            explanation=f"Rules without a guaranteed length decrease: {', '.join(sorted(offending))}.",
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
                    method=TerminationMethod.NO_CERTIFICATE,
                    witness=None,
                    explanation=(
                        f"Rule '{rule.display_name}' grows a variable's multiplicity, "
                        "so no fixed weight function can dominate its weight delta."
                    ),
                )

        rule_summaries = tuple(_RuleWeightSummary.from_rule(rule) for rule in self.system.rules)
        symbols = tuple(self.system.alphabet)

        for weight_tuple in product(range(1, max_weight + 1), repeat=len(symbols)):
            weights = dict(zip(symbols, weight_tuple, strict=True))
            if all(summary.max_weight_delta(weights) < 0 for summary in rule_summaries):
                return TerminationCertificate(
                    status=TerminationStatus.TERMINATING,
                    method=TerminationMethod.WEIGHT_FUNCTION,
                    witness=weights,
                    explanation=f"Every rule strictly reduces total symbol weight under {weights}.",
                )

        return TerminationCertificate(
            status=TerminationStatus.UNKNOWN,
            method=TerminationMethod.NO_CERTIFICATE,
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
                    method=TerminationMethod.IDENTITY_RULE,
                    witness=rule.display_name,
                    explanation=(
                        f"Rule '{rule.display_name}' has identical antecedent and consequent, "
                        "so it loops on any matching word."
                    ),
                )

        return TerminationCertificate(
            status=TerminationStatus.UNKNOWN,
            method=TerminationMethod.NO_CERTIFICATE,
            witness=None,
            explanation="No identity rules detected.",
        )

    def check(self, max_weight: int = 5) -> TerminationCertificate:
        """Try certificates in cost order and return the first definitive verdict."""
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
            method=TerminationMethod.NO_CERTIFICATE,
            witness=None,
            explanation=(
                f"No certificate found. Length check: {length.explanation} Weight check: {weight.explanation}"
            ),
        )


@dataclass(frozen=True, slots=True)
class _RuleWeightSummary:
    """Pre-extracted shape of a rule for weight-delta computation in a tight loop.

    Repeated brute-force over weight vectors hits this summary once per
    iteration; the per-rule data we read - constant character lists and
    the negative-coefficient variable terms - never changes between
    iterations, so we materialise them once when the summary is built.
    """

    consequent_chars: tuple[str, ...]
    antecedent_chars: tuple[str, ...]
    negative_var_terms: tuple[tuple[int, int], ...]
    """Each entry is ``(coefficient, v_min)`` for a negative-coefficient variable."""

    @classmethod
    def from_rule(cls, rule: ProductionRule) -> "_RuleWeightSummary":
        consequent_chars = tuple(c for elem in rule.consequent.elements if isinstance(elem, str) for c in elem)
        antecedent_chars = tuple(
            c for ante in rule.antecedents for elem in ante.elements if isinstance(elem, str) for c in elem
        )
        min_lengths = variable_min_lengths(rule)
        negative_var_terms = tuple(
            (m_c - m_a, min_lengths.get(name, 0))
            for name, (m_a, m_c) in variable_multiplicity(rule).items()
            if m_c < m_a
        )
        return cls(
            consequent_chars=consequent_chars,
            antecedent_chars=antecedent_chars,
            negative_var_terms=negative_var_terms,
        )

    def max_weight_delta(self, weights: Mapping[str, int]) -> int:
        """Tight upper bound on ``weight(consequent) - weight(antecedents)``.

        Constants contribute a fixed delta. Each negative-coefficient
        variable shaves off at most ``coefficient * v_min * min(weights)``
        because its binding must be at least ``v_min`` characters and
        each character carries at least the smallest weight.
        """
        constant_delta = sum(weights[c] for c in self.consequent_chars) - sum(weights[c] for c in self.antecedent_chars)
        if not self.negative_var_terms:
            return constant_delta
        min_weight = min(weights.values())
        var_contribution = sum(coefficient * v_min * min_weight for coefficient, v_min in self.negative_var_terms)
        return constant_delta + var_contribution
