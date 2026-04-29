"""Tests for bidirectional BFS reachability."""

import pytest

from post_canonical import (
    Alphabet,
    Pattern,
    PostCanonicalSystem,
    ProductionRule,
    Variable,
)
from post_canonical.matching.inverter import RuleInverter
from post_canonical.query import (
    BidirectionalConfig,
    BidirectionalReachabilityQuery,
    QueryResult,
    ReachabilityQuery,
)


class TestRuleInverter:
    """Tests for the per-rule inversion building block."""

    def test_clean_when_consequent_covers_antecedent_vars(self) -> None:
        x = Variable.any("x")
        rule = ProductionRule(
            antecedents=[Pattern([x, "I"])],
            consequent=Pattern([x, "I", "U"]),
            name="add_U",
        )
        assert RuleInverter.from_rule(rule).is_clean

    def test_not_clean_when_antecedent_has_unbound_var(self) -> None:
        # Hypothetical "deletion" rule where the antecedent has a variable z
        # that doesn't appear in the consequent: predecessors are unbounded.
        x = Variable.any("x")
        z = Variable.any("z")
        rule = ProductionRule(
            antecedents=[Pattern([x, z, x])],
            consequent=Pattern([x]),
            name="collapse",
        )
        assert not RuleInverter.from_rule(rule).is_clean


class TestBidirectionalAgreesWithForward:
    """Bidirectional and forward BFS must agree on derivability for every target."""

    @pytest.mark.parametrize("target", ["MI", "MIU", "MII", "MIIII", "MIUIU"])
    def test_mu_targets(self, mu_system: PostCanonicalSystem, target: str) -> None:
        forward = ReachabilityQuery(mu_system).is_derivable(target, max_words=5000)
        bidirectional = BidirectionalReachabilityQuery(mu_system).is_derivable(target)
        assert forward.found == bidirectional.found

    @pytest.mark.parametrize("target", ["1", "11", "1111", "11111111"])
    def test_doubler_targets(self, binary_doubler: PostCanonicalSystem, target: str) -> None:
        forward = ReachabilityQuery(binary_doubler).is_derivable(target, max_words=200)
        bidirectional = BidirectionalReachabilityQuery(binary_doubler).is_derivable(target)
        assert forward.found == bidirectional.found


class TestBidirectionalDerivationCorrectness:
    """The reconstructed derivation must be a valid forward derivation."""

    def test_derivation_chains_to_target(self, mu_system: PostCanonicalSystem) -> None:
        result = BidirectionalReachabilityQuery(mu_system).is_derivable("MIIII")
        assert result.found
        assert result.derivation is not None
        assert result.derivation.final_word == "MIIII"

    def test_axiom_returns_zero_step_derivation(self, mu_system: PostCanonicalSystem) -> None:
        result = BidirectionalReachabilityQuery(mu_system).is_derivable("MI")
        assert result.found
        assert result.derivation is not None
        assert result.derivation.is_axiom
        assert result.steps_explored == 0

    def test_derivation_steps_are_consistent(self, mu_system: PostCanonicalSystem) -> None:
        # Each step's output must be derivable from its inputs under its rule
        # and binding - this catches bugs in the backward-half reconstruction.
        result = BidirectionalReachabilityQuery(mu_system).is_derivable("MIUIU")
        assert result.found
        derivation = result.derivation
        assert derivation is not None
        for step in derivation.steps:
            expected = step.rule.consequent.substitute(step.binding)
            assert step.output == expected


class TestBidirectionalEfficiency:
    """Meeting in the middle should explore fewer words than one-sided BFS."""

    def test_fewer_steps_on_deep_target(self) -> None:
        # A linear chain x -> 0x -> 00x -> ... where the shortest path has many steps.
        x = Variable.any("x")
        rule = ProductionRule(
            antecedents=[Pattern([x])],
            consequent=Pattern(["0", x]),
            name="prepend",
        )
        system = PostCanonicalSystem(
            alphabet=Alphabet("01"),
            axioms=frozenset({"1"}),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )

        target = "0" * 8 + "1"
        forward = ReachabilityQuery(system).is_derivable(target, max_words=100)
        bidirectional = BidirectionalReachabilityQuery(system).is_derivable(target)

        assert forward.found
        assert bidirectional.found
        assert bidirectional.steps_explored <= forward.steps_explored


class TestNotFoundResults:
    """Search budget exhaustion returns NOT_FOUND with no derivation."""

    def test_unreachable_target_returns_not_found(self, mu_system: PostCanonicalSystem) -> None:
        # MU is famously unreachable; the search exhausts max_words.
        config = BidirectionalConfig(max_words=500)
        result = BidirectionalReachabilityQuery(mu_system).is_derivable("MU", config=config)
        assert not result.found
        assert result.status is QueryResult.NOT_FOUND
        assert result.derivation is None
        assert result.steps_explored > 0

    def test_target_not_in_alphabet_returns_not_found(self, mu_system: PostCanonicalSystem) -> None:
        config = BidirectionalConfig(max_words=200)
        result = BidirectionalReachabilityQuery(mu_system).is_derivable("MIX", config=config)
        assert not result.found


class TestBidirectionalConfig:
    """Tests for the configuration dataclass."""

    def test_defaults(self) -> None:
        config = BidirectionalConfig()
        assert config.max_words == 10_000

    def test_custom_max_words(self) -> None:
        config = BidirectionalConfig(max_words=42)
        assert config.max_words == 42
