"""Tests for the ProductionRule class."""

import pytest

from post_canonical import Pattern, ProductionRule, Variable


class TestRuleCreation:
    """Tests for production rule construction."""

    def test_create_single_antecedent_rule(self) -> None:
        """Rule can be created with single antecedent."""
        x = Variable.any("x")
        antecedent = Pattern([x, "I"])
        consequent = Pattern([x, "I", "U"])
        rule = ProductionRule([antecedent], consequent)

        assert len(rule.antecedents) == 1
        assert rule.antecedents[0] == antecedent
        assert rule.consequent == consequent

    def test_create_multi_antecedent_rule(self) -> None:
        """Rule can be created with multiple antecedents."""
        x = Variable.any("x")
        y = Variable.any("y")
        ante1 = Pattern([x])
        ante2 = Pattern([y])
        consequent = Pattern([x, y])
        rule = ProductionRule([ante1, ante2], consequent)

        assert len(rule.antecedents) == 2
        assert rule.is_single_antecedent is False

    def test_create_with_priority(self) -> None:
        """Rule can be created with priority."""
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern([x])],
            Pattern([x, x]),
            priority=5,
        )
        assert rule.priority == 5

    def test_create_with_name(self) -> None:
        """Rule can be created with name."""
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern([x])],
            Pattern([x, x]),
            name="double",
        )
        assert rule.name == "double"

    def test_default_priority_is_zero(self) -> None:
        """Default priority is 0."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x]))
        assert rule.priority == 0

    def test_default_name_is_none(self) -> None:
        """Default name is None."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x]))
        assert rule.name is None


class TestRuleValidation:
    """Tests for production rule validation."""

    def test_empty_antecedents_raises(self) -> None:
        """Rule with no antecedents raises ValueError."""
        with pytest.raises(ValueError, match="at least one antecedent"):
            ProductionRule([], Pattern(["A"]))

    def test_undefined_variable_in_consequent_raises(self) -> None:
        """Consequent using undefined variable raises ValueError."""
        x = Variable.any("x")
        y = Variable.any("y")  # Not in antecedent

        antecedent = Pattern([x])
        consequent = Pattern([x, y])  # y is undefined

        with pytest.raises(ValueError, match="undefined variables"):
            ProductionRule([antecedent], consequent)

    def test_all_consequent_variables_must_be_in_antecedents(self) -> None:
        """All variables in consequent must appear in some antecedent."""
        x = Variable.any("x")
        y = Variable.any("y")
        z = Variable.any("z")

        # z only in consequent, not in any antecedent
        ante1 = Pattern([x])
        ante2 = Pattern([y])
        consequent = Pattern([x, y, z])

        with pytest.raises(ValueError, match="undefined variables"):
            ProductionRule([ante1, ante2], consequent)


class TestRuleProperties:
    """Tests for production rule properties."""

    def test_is_single_antecedent_true(self) -> None:
        """is_single_antecedent returns True for single antecedent."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]))
        assert rule.is_single_antecedent is True

    def test_is_single_antecedent_false(self) -> None:
        """is_single_antecedent returns False for multiple antecedents."""
        x = Variable.any("x")
        y = Variable.any("y")
        rule = ProductionRule(
            [Pattern([x]), Pattern([y])],
            Pattern([x, y]),
        )
        assert rule.is_single_antecedent is False

    def test_all_variables(self) -> None:
        """all_variables returns all variables from rule."""
        x = Variable.any("x")
        y = Variable.non_empty("y")
        z = Variable.single("z")

        rule = ProductionRule(
            [Pattern([x, y]), Pattern([z])],
            Pattern([x, y, z]),
        )

        assert rule.all_variables == frozenset({x, y, z})

    def test_all_variables_includes_antecedent_only_vars(self) -> None:
        """all_variables includes vars only in antecedents."""
        x = Variable.any("x")
        y = Variable.any("y")

        # y only in antecedent, not in consequent
        rule = ProductionRule(
            [Pattern([x, y])],
            Pattern([x]),
        )

        assert x in rule.all_variables
        assert y in rule.all_variables


class TestRuleRepresentation:
    """Tests for string representations."""

    def test_str_single_antecedent(self) -> None:
        """String representation of single-antecedent rule."""
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern([x, "I"])],
            Pattern([x, "I", "U"]),
        )
        s = str(rule)
        assert "->" in s
        assert "${x}I" in s
        assert "${x}IU" in s

    def test_str_with_name(self) -> None:
        """String representation includes rule name."""
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern([x])],
            Pattern([x, x]),
            name="double",
        )
        s = str(rule)
        assert "[double]" in s

    def test_str_multi_antecedent(self) -> None:
        """String representation of multi-antecedent rule."""
        x = Variable.any("x")
        y = Variable.any("y")
        rule = ProductionRule(
            [Pattern([x]), Pattern([y])],
            Pattern([x, y]),
        )
        s = str(rule)
        # Antecedents should be comma-separated
        assert "${x}" in s
        assert "${y}" in s
        assert "->" in s

    def test_repr(self) -> None:
        """Repr includes ProductionRule type."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x]))
        assert "ProductionRule" in repr(rule)


class TestRuleImmutability:
    """Tests for rule immutability."""

    def test_rule_is_frozen(self) -> None:
        """Rules are immutable (frozen dataclass)."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x]))
        with pytest.raises(AttributeError):
            rule.priority = 10  # type: ignore
        with pytest.raises(AttributeError):
            rule.name = "new_name"  # type: ignore


class TestRuleEdgeCases:
    """Edge case tests for production rules."""

    def test_identity_rule(self) -> None:
        """Rule that produces same as input."""
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern([x])],
            Pattern([x]),
            name="identity",
        )
        assert rule.antecedents[0].elements == rule.consequent.elements

    def test_constant_only_rule(self) -> None:
        """Rule with only constants (no variables)."""
        rule = ProductionRule(
            [Pattern(["A"])],
            Pattern(["B"]),
            name="A_to_B",
        )
        assert len(rule.all_variables) == 0

    def test_consequent_subset_of_antecedent_vars(self) -> None:
        """Consequent can use subset of antecedent variables."""
        x = Variable.any("x")
        y = Variable.any("y")
        # y is in antecedent but not consequent (deletion rule)
        rule = ProductionRule(
            [Pattern([x, y])],
            Pattern([x]),
            name="delete_suffix",
        )
        assert x in rule.all_variables
        assert y in rule.all_variables

    def test_variable_shared_across_antecedents(self) -> None:
        """Same variable can appear in multiple antecedents."""
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern([x, "A"]), Pattern([x, "B"])],
            Pattern([x]),
            name="shared_var",
        )
        assert len(rule.all_variables) == 1
        assert x in rule.all_variables

    @pytest.mark.parametrize("priority", [-10, 0, 1, 100])
    def test_various_priorities(self, priority: int) -> None:
        """Rules work with various priority values."""
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern([x])],
            Pattern([x]),
            priority=priority,
        )
        assert rule.priority == priority
