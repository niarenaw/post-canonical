"""Tests for the RuleExecutor class."""

from post_canonical import (
    Alphabet,
    ExecutionConfig,
    ExecutionMode,
    Pattern,
    ProductionRule,
    Variable,
)
from post_canonical.presets.alphabets import BINARY, MIU
from post_canonical.system.derivation import DerivedWord
from post_canonical.system.executor import RuleExecutor


class TestExecutorCreation:
    """Tests for executor construction."""

    def test_create_with_defaults(self) -> None:
        """Executor can be created with default config."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]))
        executor = RuleExecutor(BINARY, frozenset({rule}))
        assert executor.config.mode == ExecutionMode.DETERMINISTIC

    def test_create_with_config(self) -> None:
        """Executor can be created with custom config."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]))
        config = ExecutionConfig(mode=ExecutionMode.NON_DETERMINISTIC)
        executor = RuleExecutor(BINARY, frozenset({rule}), config)
        assert executor.config.mode == ExecutionMode.NON_DETERMINISTIC


class TestExecutorDeterministicMode:
    """Tests for deterministic execution mode."""

    def test_deterministic_returns_first_match(self) -> None:
        """Deterministic mode returns only the first match."""
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern([x])],
            Pattern([x, x]),
            name="double",
        )
        config = ExecutionConfig(mode=ExecutionMode.DETERMINISTIC)
        executor = RuleExecutor(BINARY, frozenset({rule}), config)

        words = frozenset({DerivedWord.axiom("01")})
        results = list(executor.apply_rules(words))

        # Should get exactly one result in deterministic mode
        assert len(results) == 1
        assert results[0].word == "0101"

    def test_deterministic_respects_priority(self) -> None:
        """Higher priority rules are applied first."""
        x = Variable.any("x")
        rule_low = ProductionRule(
            [Pattern([x])],
            Pattern(["0", x]),
            priority=1,
            name="prepend_0",
        )
        rule_high = ProductionRule(
            [Pattern([x])],
            Pattern(["1", x]),
            priority=2,
            name="prepend_1",
        )
        config = ExecutionConfig(mode=ExecutionMode.DETERMINISTIC)
        executor = RuleExecutor(BINARY, frozenset({rule_low, rule_high}), config)

        words = frozenset({DerivedWord.axiom("X")})
        # Need to use an alphabet that includes X for this test
        executor = RuleExecutor(
            Alphabet("01X"),
            frozenset({rule_low, rule_high}),
            config,
        )
        results = list(executor.apply_rules(words))

        # Higher priority rule_high (priority=2) should be applied
        assert len(results) == 1
        assert results[0].word == "1X"


class TestExecutorNonDeterministicMode:
    """Tests for non-deterministic execution mode."""

    def test_non_deterministic_returns_all_matches(self) -> None:
        """Non-deterministic mode returns all possible matches."""
        x = Variable.any("x")
        y = Variable.any("y")
        rule = ProductionRule(
            [Pattern([x, "I", y])],
            Pattern([x, "U", y]),
            name="I_to_U",
        )
        config = ExecutionConfig(mode=ExecutionMode.NON_DETERMINISTIC)
        executor = RuleExecutor(MIU, frozenset({rule}), config)

        # Word with multiple I's should produce multiple results
        words = frozenset({DerivedWord.axiom("MII")})
        results = list(executor.apply_rules(words))

        # Should find both possible I replacements
        result_words = {r.word for r in results}
        assert "MUI" in result_words
        assert "MIU" in result_words

    def test_non_deterministic_multiple_rules(self) -> None:
        """Multiple rules can all be applied."""
        x = Variable.any("x")
        rule1 = ProductionRule(
            [Pattern([x])],
            Pattern(["0", x]),
            name="prepend_0",
        )
        rule2 = ProductionRule(
            [Pattern([x])],
            Pattern(["1", x]),
            name="prepend_1",
        )
        config = ExecutionConfig(mode=ExecutionMode.NON_DETERMINISTIC)
        executor = RuleExecutor(BINARY, frozenset({rule1, rule2}), config)

        words = frozenset({DerivedWord.axiom("")})
        results = list(executor.apply_rules(words))

        result_words = {r.word for r in results}
        assert "0" in result_words
        assert "1" in result_words

    def test_max_results_limits_output(self) -> None:
        """max_results config limits number of results."""
        x = Variable.any("x")
        y = Variable.any("y")
        rule = ProductionRule(
            [Pattern([x, y])],
            Pattern([y, x]),
            name="swap",
        )
        config = ExecutionConfig(
            mode=ExecutionMode.NON_DETERMINISTIC,
            max_results=2,
        )
        executor = RuleExecutor(BINARY, frozenset({rule}), config)

        # "0000" has many possible splits, but we limit to 2
        words = frozenset({DerivedWord.axiom("0000")})
        results = list(executor.apply_rules(words))

        assert len(results) <= 2


class TestExecutorSingleAntecedent:
    """Tests for single-antecedent rules."""

    def test_single_antecedent_basic(self) -> None:
        """Basic single-antecedent rule application."""
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern(["M", x])],
            Pattern(["M", x, x]),
            name="double",
        )
        config = ExecutionConfig(mode=ExecutionMode.NON_DETERMINISTIC)
        executor = RuleExecutor(MIU, frozenset({rule}), config)

        words = frozenset({DerivedWord.axiom("MI")})
        results = list(executor.apply_rules(words))

        assert len(results) == 1
        assert results[0].word == "MII"

    def test_single_antecedent_no_match(self) -> None:
        """Rule that doesn't match produces no results."""
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern(["M", x])],
            Pattern(["M", x, x]),
            name="double",
        )
        config = ExecutionConfig(mode=ExecutionMode.NON_DETERMINISTIC)
        executor = RuleExecutor(MIU, frozenset({rule}), config)

        # "UI" doesn't start with M
        words = frozenset({DerivedWord.axiom("UI")})
        results = list(executor.apply_rules(words))

        assert len(results) == 0


class TestExecutorMultiAntecedent:
    """Tests for multi-antecedent rules (the recently fixed bug area)."""

    def test_multi_antecedent_basic(self) -> None:
        """Basic multi-antecedent rule combines two words."""
        x = Variable.any("x")
        y = Variable.any("y")
        rule = ProductionRule(
            [Pattern([x]), Pattern([y])],
            Pattern([x, y]),
            name="concat",
        )
        config = ExecutionConfig(mode=ExecutionMode.NON_DETERMINISTIC)
        executor = RuleExecutor(BINARY, frozenset({rule}), config)

        words = frozenset(
            {
                DerivedWord.axiom("0"),
                DerivedWord.axiom("1"),
            }
        )
        results = list(executor.apply_rules(words))

        result_words = {r.word for r in results}
        # Should produce permutations of different words (not same word twice)
        assert "01" in result_words
        assert "10" in result_words
        # Note: "00" and "11" would require using the same word for both patterns,
        # which depends on the unifier implementation. The current implementation
        # uses permutations which allows selecting the same word multiple times.

    def test_multi_antecedent_shared_variable(self) -> None:
        """Multi-antecedent rule with same variable in both patterns."""
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern([x, "0"]), Pattern([x, "1"])],
            Pattern([x]),
            name="extract_common",
        )
        config = ExecutionConfig(mode=ExecutionMode.NON_DETERMINISTIC)
        executor = RuleExecutor(BINARY, frozenset({rule}), config)

        words = frozenset(
            {
                DerivedWord.axiom("10"),  # x="1"
                DerivedWord.axiom("11"),  # x="1"
            }
        )
        results = list(executor.apply_rules(words))

        # Should find x="1" as the common prefix
        result_words = {r.word for r in results}
        assert "1" in result_words

    def test_multi_antecedent_needs_distinct_words(self) -> None:
        """Multi-antecedent rule uses permutations which require sufficient words.

        The unifier uses permutations(available_words, n) where n is the number
        of patterns. With only one word, permutations(1, 2) yields nothing since
        we need 2 distinct selections.
        """
        x = Variable.any("x")
        y = Variable.any("y")
        rule = ProductionRule(
            [Pattern([x]), Pattern([y])],
            Pattern([x, y]),
            name="concat",
        )
        config = ExecutionConfig(mode=ExecutionMode.NON_DETERMINISTIC)
        executor = RuleExecutor(BINARY, frozenset({rule}), config)

        # Only one word available - permutations(["0"], 2) yields nothing
        words = frozenset({DerivedWord.axiom("0")})
        results = list(executor.apply_rules(words))

        # With permutations, we need at least 2 words to match 2 patterns
        assert len(results) == 0

    def test_multi_antecedent_three_patterns(self) -> None:
        """Multi-antecedent rule with three patterns needs three distinct words.

        With permutations, a 3-pattern rule needs at least 3 distinct words.
        With only 2 words ("0" and "1"), permutations(2, 3) yields nothing.
        """
        x = Variable.any("x")
        y = Variable.any("y")
        z = Variable.any("z")
        rule = ProductionRule(
            [Pattern([x]), Pattern([y]), Pattern([z])],
            Pattern([x, y, z]),
            name="concat3",
        )
        config = ExecutionConfig(mode=ExecutionMode.NON_DETERMINISTIC)
        executor = RuleExecutor(BINARY, frozenset({rule}), config)

        # Only 2 words, but need 3 for permutations(2, 3)
        words = frozenset(
            {
                DerivedWord.axiom("0"),
                DerivedWord.axiom("1"),
            }
        )
        results = list(executor.apply_rules(words))

        # permutations of 2 items taken 3 at a time is empty
        assert len(results) == 0

    def test_multi_antecedent_three_patterns_with_three_words(self) -> None:
        """Multi-antecedent rule with three patterns and three words."""
        x = Variable.any("x")
        y = Variable.any("y")
        z = Variable.any("z")
        rule = ProductionRule(
            [Pattern([x]), Pattern([y]), Pattern([z])],
            Pattern([x, y, z]),
            name="concat3",
        )
        config = ExecutionConfig(mode=ExecutionMode.NON_DETERMINISTIC)
        executor = RuleExecutor(BINARY, frozenset({rule}), config)

        words = frozenset(
            {
                DerivedWord.axiom("A"),
                DerivedWord.axiom("B"),
                DerivedWord.axiom("C"),
            }
        )
        # Need an alphabet that includes A, B, C
        executor = RuleExecutor(Alphabet("ABC"), frozenset({rule}), config)
        results = list(executor.apply_rules(words))

        # permutations(3, 3) = 3! = 6
        result_words = {r.word for r in results}
        assert len(result_words) == 6
        assert "ABC" in result_words
        assert "ACB" in result_words
        assert "BAC" in result_words
        assert "BCA" in result_words
        assert "CAB" in result_words
        assert "CBA" in result_words


class TestExecutorApplyRulesAll:
    """Tests for apply_rules_all method."""

    def test_apply_rules_all_ignores_mode(self) -> None:
        """apply_rules_all yields all results regardless of mode."""
        x = Variable.any("x")
        y = Variable.any("y")
        rule = ProductionRule(
            [Pattern([x, "I", y])],
            Pattern([x, "U", y]),
            name="I_to_U",
        )
        # Even with DETERMINISTIC, apply_rules_all yields all
        config = ExecutionConfig(mode=ExecutionMode.DETERMINISTIC)
        executor = RuleExecutor(MIU, frozenset({rule}), config)

        words = frozenset({DerivedWord.axiom("MII")})
        results = list(executor.apply_rules_all(words))

        result_words = {r.word for r in results}
        assert "MUI" in result_words
        assert "MIU" in result_words


class TestExecutorDerivationTracking:
    """Tests for derivation tracking in executor."""

    def test_derivation_step_recorded(self) -> None:
        """Each application records a derivation step."""
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern([x])],
            Pattern([x, x]),
            name="double",
        )
        config = ExecutionConfig(mode=ExecutionMode.DETERMINISTIC)
        executor = RuleExecutor(BINARY, frozenset({rule}), config)

        words = frozenset({DerivedWord.axiom("0")})
        results = list(executor.apply_rules(words))

        assert len(results) == 1
        derived = results[0]
        assert derived.derivation.length == 1
        step = derived.derivation.steps[0]
        assert step.rule == rule
        assert step.output == "00"

    def test_multi_antecedent_derivation_tracks_inputs(self) -> None:
        """Multi-antecedent derivation tracks all input words."""
        x = Variable.any("x")
        y = Variable.any("y")
        rule = ProductionRule(
            [Pattern([x]), Pattern([y])],
            Pattern([x, y]),
            name="concat",
        )
        config = ExecutionConfig(mode=ExecutionMode.NON_DETERMINISTIC)
        executor = RuleExecutor(BINARY, frozenset({rule}), config)

        words = frozenset(
            {
                DerivedWord.axiom("0"),
                DerivedWord.axiom("1"),
            }
        )
        results = list(executor.apply_rules(words))

        # Find the result for "01"
        for derived in results:
            if derived.word == "01":
                step = derived.derivation.steps[0]
                assert len(step.inputs) == 2
                assert "0" in step.inputs
                assert "1" in step.inputs
                break


class TestExecutorEdgeCases:
    """Edge case tests for executor."""

    def test_empty_rule_set(self) -> None:
        """Executor with no rules produces no results."""
        config = ExecutionConfig(mode=ExecutionMode.NON_DETERMINISTIC)
        executor = RuleExecutor(BINARY, frozenset(), config)

        words = frozenset({DerivedWord.axiom("0")})
        results = list(executor.apply_rules(words))

        assert len(results) == 0

    def test_empty_word_set(self) -> None:
        """Executor with no words produces no results."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]))
        config = ExecutionConfig(mode=ExecutionMode.NON_DETERMINISTIC)
        executor = RuleExecutor(BINARY, frozenset({rule}), config)

        words: frozenset[DerivedWord] = frozenset()
        results = list(executor.apply_rules(words))

        assert len(results) == 0
