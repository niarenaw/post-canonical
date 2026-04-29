"""Tests for the InvariantAnalyzer."""

from post_canonical import (
    Alphabet,
    Pattern,
    PostCanonicalSystem,
    ProductionRule,
    Variable,
)
from post_canonical.query import (
    InvariantAnalyzer,
    InvariantReport,
    LinearInvariant,
    ResidueInvariant,
)


class TestLinearInvariant:
    """Tests for the LinearInvariant dataclass."""

    def test_evaluate_exact(self) -> None:
        inv = LinearInvariant(
            coefficients={"a": 1, "b": -1},
            modulus=None,
            constant_value=0,
        )
        assert inv.evaluate("ab") == 0
        assert inv.evaluate("aab") == 1
        assert inv.evaluate("abb") == -1

    def test_evaluate_modular(self) -> None:
        inv = LinearInvariant(
            coefficients={"a": 1},
            modulus=3,
            constant_value=2,
        )
        assert inv.evaluate("aa") == 2
        assert inv.evaluate("aaaaa") == 2
        assert inv.evaluate("aaa") == 0

    def test_admits_uses_constant_value(self) -> None:
        inv = LinearInvariant(
            coefficients={"a": 1, "b": -1},
            modulus=None,
            constant_value=0,
        )
        assert inv.admits("ab")
        assert not inv.admits("aab")


class TestResidueInvariant:
    """Tests for the ResidueInvariant dataclass."""

    def test_residue_of_word(self) -> None:
        inv = ResidueInvariant(
            modulus=3,
            alphabet_order=("I", "M", "U"),
            reachable_residues=frozenset({(1, 1, 0), (2, 1, 1)}),
            full_space_size=27,
        )
        assert inv.residue_of("MI") == (1, 1, 0)
        assert inv.residue_of("MIIIIU") == (4 % 3, 1, 1)

    def test_admits_membership(self) -> None:
        inv = ResidueInvariant(
            modulus=2,
            alphabet_order=("0", "1"),
            reachable_residues=frozenset({(0, 0), (1, 0)}),
            full_space_size=4,
        )
        assert inv.admits("00")
        assert inv.admits("0")
        assert not inv.admits("1")
        assert not inv.admits("01")


class TestInvariantReport:
    """Tests for the InvariantReport dataclass and is_complete property."""

    def test_complete_when_no_excluded_rules(self) -> None:
        report = InvariantReport(linear=(), residue=(), excluded_rules=(), notes="")
        assert report.is_complete

    def test_incomplete_when_excluded_rules(self) -> None:
        report = InvariantReport(linear=(), residue=(), excluded_rules=("rule_a",), notes="")
        assert not report.is_complete


class TestMUPuzzleInvariant:
    """The headline test: capturing the famous MU-puzzle I-count-mod-3 invariant."""

    def test_mu_residue_invariant_at_modulus_3(self, mu_system: PostCanonicalSystem) -> None:
        analyzer = InvariantAnalyzer(mu_system)
        report = analyzer.discover()

        residue_at_3 = next((inv for inv in report.residue if inv.modulus == 3), None)
        assert residue_at_3 is not None, "Expected residue invariant at modulus 3 for MU puzzle"
        assert len(residue_at_3.reachable_residues) < residue_at_3.full_space_size

    def test_prove_unreachable_for_mu(self, mu_system: PostCanonicalSystem) -> None:
        analyzer = InvariantAnalyzer(mu_system)
        invariant = analyzer.prove_unreachable("MU")
        assert invariant is not None
        assert isinstance(invariant, ResidueInvariant)
        assert not invariant.admits("MU")

    def test_axiom_remains_admissible(self, mu_system: PostCanonicalSystem) -> None:
        analyzer = InvariantAnalyzer(mu_system)
        report = analyzer.discover()
        for inv in report.residue:
            assert inv.admits("MI"), "Every invariant must admit the axiom"

    def test_known_reachable_words_admitted(self, mu_system: PostCanonicalSystem) -> None:
        # MIU and MII are reachable in one step from MI; an invariant that excludes
        # them would be unsound.
        analyzer = InvariantAnalyzer(mu_system)
        report = analyzer.discover()
        for inv in report.residue:
            assert inv.admits("MIU")
            assert inv.admits("MII")

    def test_report_is_complete(self, mu_system: PostCanonicalSystem) -> None:
        analyzer = InvariantAnalyzer(mu_system)
        report = analyzer.discover()
        assert report.is_complete


class TestExcludedRules:
    """Multi-variable rules with mixed multiplicities cannot be soundly analyzed."""

    def test_non_affine_rule_excluded(self) -> None:
        # Rule "xy -> xxy" has two variables with different multiplicity ratios.
        x = Variable.any("x")
        y = Variable.any("y")
        rule = ProductionRule(
            antecedents=[Pattern([x, y])],
            consequent=Pattern([x, x, y]),
            name="weird",
        )
        system = PostCanonicalSystem(
            alphabet=Alphabet("ab"),
            axioms=frozenset({"a"}),
            rules=frozenset({rule}),
            variables=frozenset({x, y}),
        )

        analyzer = InvariantAnalyzer(system)
        report = analyzer.discover()
        assert "weird" in report.excluded_rules
        assert not report.is_complete
        assert report.residue == ()

    def test_prove_unreachable_returns_none_for_incomplete_report(self) -> None:
        x = Variable.any("x")
        y = Variable.any("y")
        rule = ProductionRule(
            antecedents=[Pattern([x, y])],
            consequent=Pattern([x, x, y]),
            name="weird",
        )
        system = PostCanonicalSystem(
            alphabet=Alphabet("ab"),
            axioms=frozenset({"a"}),
            rules=frozenset({rule}),
            variables=frozenset({x, y}),
        )

        analyzer = InvariantAnalyzer(system)
        # Even if "bbb" is unreachable in fact, an incomplete report can't prove it.
        assert analyzer.prove_unreachable("bbb") is None


class TestClosedSystemLinearInvariants:
    """Linear invariants are reported only when every rule is closed."""

    def test_palindrome_has_residue_invariants(self, palindrome_generator: PostCanonicalSystem) -> None:
        # x -> 0x0 and x -> 1x1 are both closed; mod-2 residue analysis still
        # excludes the (count_0 odd, count_1 odd) state.
        analyzer = InvariantAnalyzer(palindrome_generator)
        report = analyzer.discover()
        residue_at_2 = next((inv for inv in report.residue if inv.modulus == 2), None)
        assert residue_at_2 is not None
        assert (1, 1) not in residue_at_2.reachable_residues

    def test_simple_conserved_count_system(self) -> None:
        # Single axiom, single rule that swaps one a for one b: count_a + count_b
        # is preserved exactly.
        x = Variable.any("x")
        rule = ProductionRule(
            antecedents=[Pattern(["a", x])],
            consequent=Pattern(["b", x]),
            name="a_to_b",
        )
        system = PostCanonicalSystem(
            alphabet=Alphabet("ab"),
            axioms=frozenset({"a"}),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )

        analyzer = InvariantAnalyzer(system)
        report = analyzer.discover()
        # We expect the invariant c_a = c_b = 1, value = 1.
        match = next(
            (
                inv
                for inv in report.linear
                if inv.modulus is None and inv.coefficients.get("a") == 1 and inv.coefficients.get("b") == 1
            ),
            None,
        )
        assert match is not None
        assert match.constant_value == 1

    def test_doubler_has_no_linear_invariants(self, binary_doubler: PostCanonicalSystem) -> None:
        # The single rule "x -> xx" is not closed; linear search is skipped.
        analyzer = InvariantAnalyzer(binary_doubler)
        report = analyzer.discover()
        assert report.linear == ()
        assert report.residue, "Residue analysis should still run on affine rules"
