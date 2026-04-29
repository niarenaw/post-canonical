"""Tests for the CriticalPairAnalyzer."""

import pytest

from post_canonical import (
    Alphabet,
    Pattern,
    PostCanonicalSystem,
    ProductionRule,
    Variable,
)
from post_canonical.query import (
    ConfluenceReport,
    CriticalPair,
    CriticalPairAnalyzer,
)


@pytest.fixture
def trivially_confluent_system() -> PostCanonicalSystem:
    """A system whose rules can never overlap on any reachable word."""
    x = Variable.any("x")
    rule = ProductionRule(
        antecedents=[Pattern([x])],
        consequent=Pattern([x, "0"]),
        name="append_0",
    )
    return PostCanonicalSystem(
        alphabet=Alphabet("01"),
        axioms=frozenset({"1"}),
        rules=frozenset({rule}),
        variables=frozenset({x}),
    )


@pytest.fixture
def joinable_pair_system() -> PostCanonicalSystem:
    """Two rules that overlap and reduce to the same canonical word.

    Both rules eat one ``a``; rule_a then appends ``b`` and rule_b then
    appends ``c``. Reducts diverge by one letter, but a third rule
    consumes both finishing letters back to the same predecessor.
    """
    x = Variable.any("x")
    rules = frozenset(
        {
            ProductionRule(
                antecedents=[Pattern([x, "a"])],
                consequent=Pattern([x, "b"]),
                name="a_to_b",
            ),
            ProductionRule(
                antecedents=[Pattern([x, "a"])],
                consequent=Pattern([x, "c"]),
                name="a_to_c",
            ),
            ProductionRule(
                antecedents=[Pattern([x, "b"])],
                consequent=Pattern([x, "d"]),
                name="b_to_d",
            ),
            ProductionRule(
                antecedents=[Pattern([x, "c"])],
                consequent=Pattern([x, "d"]),
                name="c_to_d",
            ),
        }
    )
    return PostCanonicalSystem(
        alphabet=Alphabet("abcd"),
        axioms=frozenset({"a"}),
        rules=rules,
        variables=frozenset({x}),
    )


@pytest.fixture
def non_joinable_pair_system() -> PostCanonicalSystem:
    """Two rules whose reducts head off in different directions and never meet."""
    x = Variable.any("x")
    rules = frozenset(
        {
            ProductionRule(
                antecedents=[Pattern([x, "a"])],
                consequent=Pattern([x, "b"]),
                name="a_to_b",
            ),
            ProductionRule(
                antecedents=[Pattern([x, "a"])],
                consequent=Pattern([x, "c"]),
                name="a_to_c",
            ),
        }
    )
    return PostCanonicalSystem(
        alphabet=Alphabet("abc"),
        axioms=frozenset({"a"}),
        rules=rules,
        variables=frozenset({x}),
    )


class TestCriticalPair:
    """Tests for the CriticalPair dataclass."""

    def test_carries_all_fields(self) -> None:
        x = Variable.any("x")
        rule = ProductionRule(
            antecedents=[Pattern([x])],
            consequent=Pattern([x, "x"]),
            name="dummy",
        )
        pair = CriticalPair(
            overlap_word="a",
            rule_a=rule,
            rule_b=rule,
            reduct_a="ax",
            reduct_b="ay",
            joinable=False,
            common_normal_form=None,
        )
        assert pair.overlap_word == "a"
        assert pair.joinable is False


class TestConfluenceReport:
    """Tests for ConfluenceReport aggregation."""

    def test_no_pairs_means_locally_confluent(self) -> None:
        report = ConfluenceReport(pairs=(), locally_confluent=True, notes="")
        assert report.locally_confluent

    def test_notes_carry_information(self) -> None:
        report = ConfluenceReport(pairs=(), locally_confluent=True, notes="explored 100 words")
        assert "100" in report.notes


class TestTriviallyConfluent:
    """A single-rule system has no overlaps and so is locally confluent."""

    def test_no_pairs_reported(self, trivially_confluent_system: PostCanonicalSystem) -> None:
        report = CriticalPairAnalyzer(trivially_confluent_system).confluence_report(max_words=20)
        assert report.pairs == ()
        assert report.locally_confluent


class TestJoinablePairs:
    """A confluent system with overlapping rules: every pair must be joinable."""

    def test_joinable_pair_reports_locally_confluent(self, joinable_pair_system: PostCanonicalSystem) -> None:
        report = CriticalPairAnalyzer(joinable_pair_system).confluence_report(max_words=20, max_join_steps=5)
        assert len(report.pairs) >= 1
        assert all(pair.joinable for pair in report.pairs)
        assert report.locally_confluent

    def test_each_pair_has_distinct_reducts(self, joinable_pair_system: PostCanonicalSystem) -> None:
        for pair in CriticalPairAnalyzer(joinable_pair_system).critical_pairs(max_words=20):
            assert pair.reduct_a != pair.reduct_b


class TestNonJoinablePairs:
    """Diverging rules produce critical pairs that don't join within the budget."""

    def test_non_joinable_pair_reported(self, non_joinable_pair_system: PostCanonicalSystem) -> None:
        report = CriticalPairAnalyzer(non_joinable_pair_system).confluence_report(max_words=20, max_join_steps=5)
        assert len(report.pairs) >= 1
        assert any(not pair.joinable for pair in report.pairs)
        assert not report.locally_confluent


class TestMUPuzzle:
    """The MU puzzle's overlapping rules should be detected."""

    def test_pairs_are_yielded(self, mu_system: PostCanonicalSystem) -> None:
        # MU has rules that can fire on the same word in distinct ways
        # (e.g. multiple positions for the III -> U replacement).
        pairs = list(CriticalPairAnalyzer(mu_system).critical_pairs(max_words=30, max_join_steps=4))
        # We don't assert a specific count, just that at least one pair exists
        # since MU's rules are clearly non-trivially overlapping.
        assert len(pairs) >= 1
        for pair in pairs:
            assert pair.reduct_a != pair.reduct_b


class TestMultiAntecedentNote:
    """When a system contains multi-antecedent rules, the report calls it out."""

    def test_multi_antecedent_note_included(self, multi_antecedent_system: PostCanonicalSystem) -> None:
        report = CriticalPairAnalyzer(multi_antecedent_system).confluence_report(max_words=10)
        assert "multi-antecedent" in report.notes.lower()
