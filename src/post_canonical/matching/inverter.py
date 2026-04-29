"""Rule inversion for backward search.

Forward execution applies a rule by matching its antecedents against
input words and substituting bindings into the consequent. Backward
execution does the reverse: given a target word that some rule
*could have produced*, recover the predecessor word(s) that fed it.

Rule inversion is clean only when every antecedent variable also
appears in the consequent. When the consequent doesn't see an
antecedent variable - the deletion-style rules in the MU puzzle's
``xUUy -> xy``, for example - the rule has infinite preimages, and
only an opt-in bounded enumeration could recover any of them. We ship
the strict, clean-inverse case and leave bounded enumeration as a
future extension knob.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from ..core.rule import ProductionRule
from .binding import Binding
from .matcher import PatternMatcher


@dataclass(frozen=True, slots=True)
class RuleInversion:
    """The result of inverting a rule against a single target word."""

    predecessors: tuple[str, ...]
    binding: Binding


@dataclass(frozen=True, slots=True)
class RuleInverter:
    """Compute predecessor words for a single production rule.

    A rule is *cleanly invertible* when every antecedent variable also
    appears in the consequent: matching the consequent pattern against
    a target word then provides bindings for all antecedent variables,
    and each antecedent substitutes into a single predecessor word.
    """

    rule: ProductionRule
    is_clean: bool

    @classmethod
    def from_rule(cls, rule: ProductionRule) -> "RuleInverter":
        antecedent_vars: set[str] = set()
        for ante in rule.antecedents:
            antecedent_vars.update(ante.variable_names)
        is_clean = antecedent_vars.issubset(rule.consequent.variable_names)
        return cls(rule=rule, is_clean=is_clean)

    def invert(self, target: str, matcher: PatternMatcher) -> Iterator[RuleInversion]:
        """Yield each binding by which ``self.rule`` could have produced ``target``.

        Each result includes the predecessor word tuple (one word per
        antecedent) and the binding that recovers it, so callers can
        reconstruct a derivation step. When the rule is not cleanly
        invertible, this iterator is empty.
        """
        if not self.is_clean:
            return

        for binding in matcher.match(self.rule.consequent, target):
            predecessors = tuple(ante.substitute(binding) for ante in self.rule.antecedents)
            yield RuleInversion(predecessors=predecessors, binding=binding)
