"""Tests for the TerminationChecker."""

from post_canonical import (
    Alphabet,
    Pattern,
    PostCanonicalSystem,
    ProductionRule,
    Variable,
)
from post_canonical.presets import BINARY
from post_canonical.query import (
    TerminationCertificate,
    TerminationChecker,
    TerminationStatus,
)


class TestTerminationStatus:
    """Tests for the TerminationStatus enum."""

    def test_three_distinct_outcomes(self) -> None:
        outcomes = {
            TerminationStatus.TERMINATING,
            TerminationStatus.NON_TERMINATING,
            TerminationStatus.UNKNOWN,
        }
        assert len(outcomes) == 3


class TestTerminationCertificate:
    """Tests for the TerminationCertificate dataclass."""

    def test_carries_witness_when_present(self) -> None:
        cert = TerminationCertificate(
            status=TerminationStatus.TERMINATING,
            method="weight_function",
            witness={"a": 2, "b": 1},
            explanation="ok",
        )
        assert cert.witness == {"a": 2, "b": 1}
        assert cert.method == "weight_function"

    def test_unknown_with_no_witness(self) -> None:
        cert = TerminationCertificate(
            status=TerminationStatus.UNKNOWN,
            method="no_certificate",
            witness=None,
            explanation="nothing found",
        )
        assert cert.witness is None


class TestLengthDecreasingCheck:
    """Tests for the strict-length-decrease certificate."""

    def test_pure_shrinking_system_terminates(self) -> None:
        x = Variable.any("x")
        y = Variable.any("y")

        # Every rule strictly removes characters.
        rule = ProductionRule(
            antecedents=[Pattern([x, "AA", y])],
            consequent=Pattern([x, y]),
            name="drop_AA",
        )
        system = PostCanonicalSystem(
            alphabet=Alphabet("AB"),
            axioms=frozenset({"AAB"}),
            rules=frozenset({rule}),
            variables=frozenset({x, y}),
        )

        cert = TerminationChecker(system).check_length_decreasing()
        assert cert.status is TerminationStatus.TERMINATING
        assert cert.method == "length_strict_decrease"

    def test_growing_system_unknown(self, binary_doubler: PostCanonicalSystem) -> None:
        cert = TerminationChecker(binary_doubler).check_length_decreasing()
        assert cert.status is TerminationStatus.UNKNOWN
        assert "double" in cert.explanation


class TestWeightFunctionCheck:
    """Tests for the weight-function certificate."""

    def test_weight_amenable_system_terminates(self) -> None:
        # Rule "A → B" has constant length 1 → 1 but reduces weight when w[A] > w[B].
        rule_a_to_b = ProductionRule(
            antecedents=[Pattern(["A"])],
            consequent=Pattern(["B"]),
            name="A_to_B",
        )
        rule_b_to_b = ProductionRule(
            antecedents=[Pattern(["B", "B"])],
            consequent=Pattern(["B"]),
            name="merge_B",
        )
        system = PostCanonicalSystem(
            alphabet=Alphabet("AB"),
            axioms=frozenset({"A"}),
            rules=frozenset({rule_a_to_b, rule_b_to_b}),
            variables=frozenset(),
        )

        cert = TerminationChecker(system).check_weight_function(max_weight=4)
        assert cert.status is TerminationStatus.TERMINATING
        assert cert.method == "weight_function"
        assert isinstance(cert.witness, dict)
        # The chosen weight must give A a strictly larger weight than B.
        assert cert.witness["A"] > cert.witness["B"]

    def test_growing_rule_short_circuits(self, binary_doubler: PostCanonicalSystem) -> None:
        cert = TerminationChecker(binary_doubler).check_weight_function()
        assert cert.status is TerminationStatus.UNKNOWN
        assert "grows" in cert.explanation


class TestIdentityRuleCheck:
    """Tests for trivial-loop detection via identity rules."""

    def test_identity_rule_flagged(self) -> None:
        x = Variable.any("x")
        rule = ProductionRule(
            antecedents=[Pattern([x])],
            consequent=Pattern([x]),
            name="noop",
        )
        system = PostCanonicalSystem(
            alphabet=BINARY,
            axioms=frozenset({"0"}),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )

        cert = TerminationChecker(system).check_identity_rules()
        assert cert.status is TerminationStatus.NON_TERMINATING
        assert cert.method == "identity_rule"
        assert cert.witness == "noop"

    def test_no_identity_rule_unknown(self, mu_system: PostCanonicalSystem) -> None:
        cert = TerminationChecker(mu_system).check_identity_rules()
        assert cert.status is TerminationStatus.UNKNOWN


class TestCombinedCheck:
    """Tests for the combined check() method."""

    def test_mu_puzzle_unknown(self, mu_system: PostCanonicalSystem) -> None:
        # MU has the doubler rule, so neither length nor weight certificates fit;
        # there is no identity rule, so the combined verdict is UNKNOWN.
        cert = TerminationChecker(mu_system).check()
        assert cert.status is TerminationStatus.UNKNOWN

    def test_binary_doubler_unknown(self, binary_doubler: PostCanonicalSystem) -> None:
        cert = TerminationChecker(binary_doubler).check()
        assert cert.status is TerminationStatus.UNKNOWN

    def test_pure_shrinking_terminates(self) -> None:
        x = Variable.any("x")
        rule = ProductionRule(
            antecedents=[Pattern(["AA", x])],
            consequent=Pattern([x]),
            name="trim",
        )
        system = PostCanonicalSystem(
            alphabet=Alphabet("AB"),
            axioms=frozenset({"AAAA"}),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )
        cert = TerminationChecker(system).check()
        assert cert.status is TerminationStatus.TERMINATING

    def test_identity_rule_dominates(self) -> None:
        # An identity rule plus a shrinking rule still reports NON_TERMINATING:
        # the identity-rule certificate is sound regardless of other rules.
        x = Variable.any("x")
        identity = ProductionRule(
            antecedents=[Pattern([x])],
            consequent=Pattern([x]),
            name="noop",
        )
        shrink = ProductionRule(
            antecedents=[Pattern(["A", x])],
            consequent=Pattern([x]),
            name="drop_A",
        )
        system = PostCanonicalSystem(
            alphabet=Alphabet("AB"),
            axioms=frozenset({"AB"}),
            rules=frozenset({identity, shrink}),
            variables=frozenset({x}),
        )
        cert = TerminationChecker(system).check()
        assert cert.status is TerminationStatus.NON_TERMINATING
        assert cert.witness == "noop"
