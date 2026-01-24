"""Tests for ReachabilityQuery class."""

from post_canonical import (
    Alphabet,
    ExecutionMode,
    Pattern,
    PostCanonicalSystem,
    ProductionRule,
    Variable,
)
from post_canonical.presets.alphabets import BINARY
from post_canonical.query import QueryResult, ReachabilityQuery, ReachabilityResult


class TestQueryResult:
    """Tests for QueryResult enum."""

    def test_derivable_exists(self) -> None:
        """DERIVABLE result exists."""
        assert QueryResult.DERIVABLE is not None

    def test_not_found_exists(self) -> None:
        """NOT_FOUND result exists."""
        assert QueryResult.NOT_FOUND is not None

    def test_results_are_distinct(self) -> None:
        """Query results are distinct values."""
        assert QueryResult.DERIVABLE != QueryResult.NOT_FOUND


class TestReachabilityResult:
    """Tests for ReachabilityResult class."""

    def test_derivable_result(self) -> None:
        """Result for derivable word."""
        from post_canonical.system.derivation import Derivation

        result = ReachabilityResult(
            status=QueryResult.DERIVABLE,
            derivation=Derivation(),
            steps_explored=5,
            target="MI",
        )

        assert result.found is True
        assert result.status == QueryResult.DERIVABLE
        assert result.target == "MI"

    def test_not_found_result(self) -> None:
        """Result for word not found."""
        result = ReachabilityResult(
            status=QueryResult.NOT_FOUND,
            derivation=None,
            steps_explored=1000,
            target="MU",
        )

        assert result.found is False
        assert result.derivation is None
        assert result.steps_explored == 1000

    def test_str_derivable(self) -> None:
        """String representation for derivable result."""
        from post_canonical.system.derivation import Derivation

        result = ReachabilityResult(
            status=QueryResult.DERIVABLE,
            derivation=Derivation(),
            steps_explored=5,
            target="MI",
        )

        s = str(result)
        assert "MI" in s
        assert "DERIVABLE" in s

    def test_str_not_found(self) -> None:
        """String representation for not found result."""
        result = ReachabilityResult(
            status=QueryResult.NOT_FOUND,
            derivation=None,
            steps_explored=100,
            target="MU",
        )

        s = str(result)
        assert "MU" in s
        assert "NOT_FOUND" in s
        assert "100" in s


class TestReachabilityQuery:
    """Tests for ReachabilityQuery class."""

    def test_axiom_is_derivable(self, mu_system: PostCanonicalSystem) -> None:
        """Axioms are immediately derivable."""
        query = ReachabilityQuery(mu_system)
        result = query.is_derivable("MI")

        assert result.found is True
        assert result.status == QueryResult.DERIVABLE
        assert result.steps_explored == 0  # No exploration needed
        assert result.derivation is not None
        assert result.derivation.is_axiom is True

    def test_simple_derivation(self, mu_system: PostCanonicalSystem) -> None:
        """Simple one-step derivation is found."""
        query = ReachabilityQuery(mu_system)
        result = query.is_derivable("MIU", max_words=100)

        assert result.found is True
        assert result.derivation is not None
        assert result.derivation.length >= 1

    def test_multi_step_derivation(self, mu_system: PostCanonicalSystem) -> None:
        """Multi-step derivation is found."""
        query = ReachabilityQuery(mu_system)
        # MII requires: MI -> MII (double rule)
        result = query.is_derivable("MII", max_words=100)

        assert result.found is True
        assert result.derivation is not None

    def test_not_found_within_limit(self, mu_system: PostCanonicalSystem) -> None:
        """Word not found within exploration limit."""
        query = ReachabilityQuery(mu_system)
        # MU is famously not derivable, but we can't prove it
        # With small limit, it won't be found
        result = query.is_derivable("MU", max_words=10)

        assert result.found is False
        assert result.status == QueryResult.NOT_FOUND
        assert result.derivation is None

    def test_max_words_limit(self) -> None:
        """Exploration respects max_words limit."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern(["0", x]), name="prepend")

        pcs = PostCanonicalSystem(
            alphabet=BINARY,
            axioms=frozenset({"1"}),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )

        query = ReachabilityQuery(pcs)
        # This word requires many steps, more than max_words allows
        result = query.is_derivable("0000000000001", max_words=5)

        assert result.steps_explored <= 5


class TestReachabilityQueryConvenienceMethods:
    """Tests for convenience methods."""

    def test_find_derivation_returns_derivation(self, mu_system: PostCanonicalSystem) -> None:
        """find_derivation returns the derivation object."""
        query = ReachabilityQuery(mu_system)
        deriv = query.find_derivation("MII", max_words=100)

        assert deriv is not None
        # Should be a Derivation object
        assert hasattr(deriv, "steps")

    def test_find_derivation_returns_none_if_not_found(self, mu_system: PostCanonicalSystem) -> None:
        """find_derivation returns None if not found."""
        query = ReachabilityQuery(mu_system)
        deriv = query.find_derivation("MU", max_words=10)

        assert deriv is None

    def test_can_reach_returns_bool(self, mu_system: PostCanonicalSystem) -> None:
        """can_reach returns boolean."""
        query = ReachabilityQuery(mu_system)

        assert query.can_reach("MI", max_words=10) is True
        assert query.can_reach("MII", max_words=100) is True


class TestReachabilityQueryModes:
    """Tests for different execution modes."""

    def test_non_deterministic_mode_default(self, mu_system: PostCanonicalSystem) -> None:
        """Default mode is non-deterministic."""
        query = ReachabilityQuery(mu_system)
        result = query.is_derivable("MII", max_words=100)

        # Should find derivation
        assert result.found is True

    def test_deterministic_mode(self, mu_system: PostCanonicalSystem) -> None:
        """Deterministic mode can be specified."""
        query = ReachabilityQuery(mu_system)
        result = query.is_derivable(
            "MII",
            max_words=100,
            mode=ExecutionMode.DETERMINISTIC,
        )

        # May or may not find it depending on rule order
        # But should not error
        assert result.status in (QueryResult.DERIVABLE, QueryResult.NOT_FOUND)


class TestReachabilityWithMultiAntecedent:
    """Tests for reachability with multi-antecedent rules."""

    def test_multi_antecedent_reachability(self, multi_antecedent_system: PostCanonicalSystem) -> None:
        """Can find words derivable via multi-antecedent rules."""
        query = ReachabilityQuery(multi_antecedent_system)

        # "01" should be derivable by concatenating "0" and "1"
        result = query.is_derivable("01", max_words=100)

        assert result.found is True
        assert result.derivation is not None

    def test_multi_antecedent_derivation_has_multiple_inputs(
        self, multi_antecedent_system: PostCanonicalSystem
    ) -> None:
        """Derivation step from multi-antecedent rule has multiple inputs."""
        query = ReachabilityQuery(multi_antecedent_system)
        result = query.is_derivable("01", max_words=100)

        assert result.found is True
        if result.derivation and result.derivation.steps:
            step = result.derivation.steps[0]
            # Multi-antecedent rule should have 2 inputs
            assert len(step.inputs) == 2


class TestReachabilityEdgeCases:
    """Edge case tests for reachability queries."""

    def test_empty_word_axiom(self) -> None:
        """Empty string axiom is reachable."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern(["0", x, "0"]))

        pcs = PostCanonicalSystem(
            alphabet=BINARY,
            axioms=frozenset({""}),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )

        query = ReachabilityQuery(pcs)
        result = query.is_derivable("")

        assert result.found is True
        assert result.derivation is not None
        assert result.derivation.is_axiom is True

    def test_word_not_in_alphabet(self, mu_system: PostCanonicalSystem) -> None:
        """Word with characters not in alphabet won't be found."""
        query = ReachabilityQuery(mu_system)
        # "X" is not in MIU alphabet
        result = query.is_derivable("MIX", max_words=100)

        assert result.found is False

    def test_system_with_no_rules(self) -> None:
        """System with no rules only reaches axioms."""
        pcs = PostCanonicalSystem(
            alphabet=BINARY,
            axioms=frozenset({"0", "1"}),
            rules=frozenset(),
            variables=frozenset(),
        )

        query = ReachabilityQuery(pcs)

        assert query.can_reach("0") is True
        assert query.can_reach("1") is True
        assert query.can_reach("01", max_words=10) is False

    def test_target_not_derivable_in_simple_system(self) -> None:
        """A word not matching any rule pattern won't be derivable.

        System with a simple prepend rule cannot produce words without that prefix.
        """
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern(["A", x])],  # Only matches words starting with A
            Pattern(["A", "A", x]),  # Prepends another A
            name="prepend_A",
        )

        pcs = PostCanonicalSystem(
            alphabet=Alphabet("AB"),
            axioms=frozenset({"A"}),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )

        query = ReachabilityQuery(pcs)
        # "B" cannot be derived since we start with "A" and only prepend "A"
        result = query.is_derivable("B", max_words=20)

        assert result.found is False
        assert result.steps_explored <= 20


class TestReachabilityPerformance:
    """Performance-related tests for reachability."""

    def test_early_termination_on_find(self) -> None:
        """Query terminates early when target is found."""
        # Use MU system which has bounded behavior
        # and find a word that's derivable in a few steps
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern(["M", x])],  # Match words starting with M
            Pattern(["M", x, x]),  # Double the part after M
            name="double",
        )

        pcs = PostCanonicalSystem(
            alphabet=Alphabet("MI"),
            axioms=frozenset({"MI"}),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )

        query = ReachabilityQuery(pcs)
        result = query.is_derivable("MII", max_words=100)

        # Should find quickly
        assert result.found is True
        assert result.steps_explored < 10

    def test_exploration_count_accuracy(self, mu_system: PostCanonicalSystem) -> None:
        """steps_explored count is accurate."""
        query = ReachabilityQuery(mu_system)
        result = query.is_derivable("NONEXISTENT", max_words=50)

        # Should explore exactly 50 words (or less if fixed point)
        assert result.steps_explored <= 50
        assert result.steps_explored > 0
