"""Tests for Variable and VariableKind classes."""

import pytest

from post_canonical import Variable, VariableKind


class TestVariableCreation:
    """Tests for variable construction."""

    def test_create_with_default_kind(self) -> None:
        """Variable defaults to ANY kind."""
        var = Variable("x")
        assert var.name == "x"
        assert var.kind == VariableKind.ANY

    def test_create_with_explicit_kind(self) -> None:
        """Variable can be created with explicit kind."""
        var = Variable("y", VariableKind.NON_EMPTY)
        assert var.name == "y"
        assert var.kind == VariableKind.NON_EMPTY

    def test_empty_name_raises(self) -> None:
        """Empty variable name raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Variable("")

    def test_invalid_name_raises(self) -> None:
        """Non-alphanumeric names (except underscore) raise ValueError."""
        with pytest.raises(ValueError, match="alphanumeric"):
            Variable("my-var")
        with pytest.raises(ValueError, match="alphanumeric"):
            Variable("my.var")
        with pytest.raises(ValueError, match="alphanumeric"):
            Variable("my var")

    def test_underscore_in_name_allowed(self) -> None:
        """Underscores are allowed in variable names."""
        var = Variable("my_var")
        assert var.name == "my_var"

    def test_numeric_names_allowed(self) -> None:
        """Pure numeric names are allowed."""
        var = Variable("123")
        assert var.name == "123"


class TestVariableFactoryMethods:
    """Tests for Variable class factory methods."""

    def test_any_creates_any_variable(self) -> None:
        """Variable.any() creates an ANY kind variable."""
        var = Variable.any("x")
        assert var.kind == VariableKind.ANY
        assert var.name == "x"

    def test_non_empty_creates_non_empty_variable(self) -> None:
        """Variable.non_empty() creates a NON_EMPTY kind variable."""
        var = Variable.non_empty("y")
        assert var.kind == VariableKind.NON_EMPTY
        assert var.name == "y"

    def test_single_creates_single_variable(self) -> None:
        """Variable.single() creates a SINGLE kind variable."""
        var = Variable.single("z")
        assert var.kind == VariableKind.SINGLE
        assert var.name == "z"


class TestVariableMatching:
    """Tests for variable matching properties."""

    def test_any_matches_empty(self) -> None:
        """ANY variables can match empty strings."""
        var = Variable.any("x")
        assert var.matches_empty() is True

    def test_non_empty_does_not_match_empty(self) -> None:
        """NON_EMPTY variables cannot match empty strings."""
        var = Variable.non_empty("y")
        assert var.matches_empty() is False

    def test_single_does_not_match_empty(self) -> None:
        """SINGLE variables cannot match empty strings."""
        var = Variable.single("z")
        assert var.matches_empty() is False

    @pytest.mark.parametrize(
        "kind,expected_min",
        [
            (VariableKind.ANY, 0),
            (VariableKind.NON_EMPTY, 1),
            (VariableKind.SINGLE, 1),
        ],
    )
    def test_min_length(self, kind: VariableKind, expected_min: int) -> None:
        """min_length returns correct minimum for each kind."""
        var = Variable("x", kind)
        assert var.min_length() == expected_min

    def test_max_length_for_any(self) -> None:
        """ANY variables can match up to all available characters."""
        var = Variable.any("x")
        assert var.max_length(10) == 10
        assert var.max_length(0) == 0

    def test_max_length_for_non_empty(self) -> None:
        """NON_EMPTY variables can match up to all available characters."""
        var = Variable.non_empty("y")
        assert var.max_length(10) == 10
        assert var.max_length(1) == 1

    def test_max_length_for_single(self) -> None:
        """SINGLE variables always match exactly one character."""
        var = Variable.single("z")
        assert var.max_length(10) == 1
        assert var.max_length(100) == 1


class TestVariableEquality:
    """Tests for variable equality and hashing."""

    def test_equal_variables(self) -> None:
        """Variables with same name and kind are equal."""
        v1 = Variable("x", VariableKind.ANY)
        v2 = Variable("x", VariableKind.ANY)
        assert v1 == v2

    def test_different_names_not_equal(self) -> None:
        """Variables with different names are not equal."""
        v1 = Variable("x", VariableKind.ANY)
        v2 = Variable("y", VariableKind.ANY)
        assert v1 != v2

    def test_different_kinds_not_equal(self) -> None:
        """Variables with different kinds are not equal."""
        v1 = Variable("x", VariableKind.ANY)
        v2 = Variable("x", VariableKind.NON_EMPTY)
        assert v1 != v2

    def test_hashable_for_sets(self) -> None:
        """Variables can be used in sets and dicts."""
        v1 = Variable("x")
        v2 = Variable("y")
        var_set = {v1, v2}
        assert len(var_set) == 2
        assert v1 in var_set

    def test_hash_consistency(self) -> None:
        """Equal variables have equal hashes."""
        v1 = Variable("x", VariableKind.ANY)
        v2 = Variable("x", VariableKind.ANY)
        assert hash(v1) == hash(v2)


class TestVariableRepresentation:
    """Tests for string representations."""

    def test_str_format(self) -> None:
        """String representation uses $name format."""
        var = Variable("x")
        assert str(var) == "$x"

    def test_repr_includes_kind(self) -> None:
        """Repr includes name and kind."""
        var = Variable("x", VariableKind.NON_EMPTY)
        repr_str = repr(var)
        assert "Variable" in repr_str
        assert "x" in repr_str
        assert "NON_EMPTY" in repr_str


class TestVariableImmutability:
    """Tests for variable immutability."""

    def test_variable_is_frozen(self) -> None:
        """Variables are immutable (frozen dataclass)."""
        var = Variable("x")
        with pytest.raises(AttributeError):
            var.name = "y"  # type: ignore
        with pytest.raises(AttributeError):
            var.kind = VariableKind.SINGLE  # type: ignore


class TestVariableKindEnum:
    """Tests for the VariableKind enum."""

    def test_all_kinds_exist(self) -> None:
        """All expected variable kinds exist."""
        assert hasattr(VariableKind, "ANY")
        assert hasattr(VariableKind, "NON_EMPTY")
        assert hasattr(VariableKind, "SINGLE")

    def test_kinds_are_distinct(self) -> None:
        """Each kind is a distinct value."""
        kinds = [VariableKind.ANY, VariableKind.NON_EMPTY, VariableKind.SINGLE]
        assert len(set(kinds)) == 3
