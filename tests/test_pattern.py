"""Tests for the Pattern class."""

import pytest

from post_canonical import Alphabet, Pattern, Variable
from post_canonical.matching.binding import Binding


class TestPatternCreation:
    """Tests for pattern construction."""

    def test_create_from_string_constant(self) -> None:
        """Pattern can be created from a string constant."""
        pattern = Pattern(["abc"])
        assert pattern.elements == ("abc",)

    def test_create_with_variables(self) -> None:
        """Pattern can include variables."""
        x = Variable.any("x")
        pattern = Pattern(["A", x, "B"])
        assert len(pattern.elements) == 3
        assert pattern.elements[1] == x

    def test_empty_pattern(self) -> None:
        """Empty pattern can be created."""
        pattern = Pattern([])
        assert pattern.elements == ()

    def test_normalization_merges_adjacent_strings(self) -> None:
        """Adjacent string constants are merged during normalization."""
        pattern = Pattern(["A", "B", "C"])
        assert pattern.elements == ("ABC",)

    def test_normalization_removes_empty_strings(self) -> None:
        """Empty strings are removed during normalization."""
        x = Variable.any("x")
        pattern = Pattern(["", "A", "", x, ""])
        assert pattern.elements == ("A", x)

    def test_constant_factory_method(self) -> None:
        """Pattern.constant creates a constant-only pattern."""
        pattern = Pattern.constant("hello")
        assert pattern.elements == ("hello",)
        assert len(pattern.variables) == 0


class TestPatternParsing:
    """Tests for pattern parsing from string."""

    def test_parse_constant(self) -> None:
        """Parse a constant-only pattern."""
        pattern = Pattern.parse("ABC", {})
        assert pattern.elements == ("ABC",)

    def test_parse_with_variable(self) -> None:
        """Parse a pattern containing a variable."""
        x = Variable.any("x")
        pattern = Pattern.parse("A${x}B", {"x": x})
        assert len(pattern.elements) == 3
        assert pattern.elements[0] == "A"
        assert pattern.elements[1] == x
        assert pattern.elements[2] == "B"

    def test_parse_multiple_variables(self) -> None:
        """Parse a pattern with multiple variables."""
        x = Variable.any("x")
        y = Variable.any("y")
        pattern = Pattern.parse("${x}M${y}", {"x": x, "y": y})
        assert len(pattern.elements) == 3
        assert pattern.elements[0] == x
        assert pattern.elements[1] == "M"
        assert pattern.elements[2] == y

    def test_parse_consecutive_variables(self) -> None:
        """Parse a pattern with consecutive variables."""
        x = Variable.any("x")
        y = Variable.any("y")
        pattern = Pattern.parse("${x}${y}", {"x": x, "y": y})
        assert len(pattern.elements) == 2
        assert pattern.elements[0] == x
        assert pattern.elements[1] == y

    def test_parse_variable_only(self) -> None:
        """Parse a pattern that is just a variable."""
        x = Variable.any("x")
        pattern = Pattern.parse("${x}", {"x": x})
        assert pattern.elements == (x,)

    def test_parse_unknown_variable_raises(self) -> None:
        """Parsing with unknown variable raises ValueError."""
        with pytest.raises(ValueError, match="Unknown variable"):
            Pattern.parse("${unknown}", {"x": Variable.any("x")})

    def test_parse_unclosed_variable_raises(self) -> None:
        """Unclosed variable syntax raises ValueError."""
        with pytest.raises(ValueError, match="Unclosed"):
            Pattern.parse("${x", {"x": Variable.any("x")})

    def test_parse_missing_brace_raises(self) -> None:
        """Dollar sign without brace raises ValueError."""
        with pytest.raises(ValueError, match="Expected"):
            Pattern.parse("$x", {"x": Variable.any("x")})

    def test_parse_empty_variable_name_raises(self) -> None:
        """Empty variable name raises ValueError."""
        with pytest.raises(ValueError, match="Empty variable name"):
            Pattern.parse("${}", {})


class TestPatternProperties:
    """Tests for pattern properties."""

    def test_variables_property(self) -> None:
        """variables returns frozenset of all variables."""
        x = Variable.any("x")
        y = Variable.non_empty("y")
        pattern = Pattern([x, "A", y, x])  # x appears twice
        assert pattern.variables == frozenset({x, y})

    def test_variable_names_property(self) -> None:
        """variable_names returns frozenset of all variable names."""
        x = Variable.any("x")
        y = Variable.non_empty("y")
        pattern = Pattern([x, "A", y])
        assert pattern.variable_names == frozenset({"x", "y"})

    def test_has_consecutive_variables_true(self) -> None:
        """has_consecutive_variables returns True when variables are adjacent."""
        x = Variable.any("x")
        y = Variable.any("y")
        pattern = Pattern([x, y])
        assert pattern.has_consecutive_variables() is True

    def test_has_consecutive_variables_false(self) -> None:
        """has_consecutive_variables returns False when variables are separated."""
        x = Variable.any("x")
        y = Variable.any("y")
        pattern = Pattern([x, "A", y])
        assert pattern.has_consecutive_variables() is False

    def test_min_match_length_constant_only(self) -> None:
        """min_match_length for constant pattern equals string length."""
        pattern = Pattern(["ABC"])
        assert pattern.min_match_length() == 3

    def test_min_match_length_with_any_variable(self) -> None:
        """ANY variable contributes 0 to minimum length."""
        x = Variable.any("x")
        pattern = Pattern(["A", x, "B"])
        assert pattern.min_match_length() == 2

    def test_min_match_length_with_non_empty_variable(self) -> None:
        """NON_EMPTY variable contributes 1 to minimum length."""
        y = Variable.non_empty("y")
        pattern = Pattern(["A", y, "B"])
        assert pattern.min_match_length() == 3

    def test_min_match_length_with_single_variable(self) -> None:
        """SINGLE variable contributes 1 to minimum length."""
        z = Variable.single("z")
        pattern = Pattern(["A", z, "B"])
        assert pattern.min_match_length() == 3


class TestPatternSubstitution:
    """Tests for pattern substitution."""

    def test_substitute_single_variable(self) -> None:
        """Substitute a single variable."""
        x = Variable.any("x")
        pattern = Pattern(["A", x, "B"])
        result = pattern.substitute(Binding({"x": "XYZ"}))
        assert result == "AXYZB"

    def test_substitute_multiple_variables(self) -> None:
        """Substitute multiple variables."""
        x = Variable.any("x")
        y = Variable.any("y")
        pattern = Pattern([x, "M", y])
        result = pattern.substitute(Binding({"x": "A", "y": "B"}))
        assert result == "AMB"

    def test_substitute_repeated_variable(self) -> None:
        """Same variable appears multiple times, gets same value."""
        x = Variable.any("x")
        pattern = Pattern([x, x])
        result = pattern.substitute(Binding({"x": "AB"}))
        assert result == "ABAB"

    def test_substitute_empty_value(self) -> None:
        """Variables can be substituted with empty string."""
        x = Variable.any("x")
        pattern = Pattern(["A", x, "B"])
        result = pattern.substitute(Binding({"x": ""}))
        assert result == "AB"

    def test_substitute_unbound_raises(self) -> None:
        """Substitution with unbound variable raises ValueError."""
        x = Variable.any("x")
        y = Variable.any("y")
        pattern = Pattern([x, y])
        with pytest.raises(ValueError, match="Unbound variable"):
            pattern.substitute(Binding({"x": "A"}))  # y is unbound


class TestPatternValidation:
    """Tests for pattern validation against alphabet."""

    def test_validate_valid_pattern(self) -> None:
        """Valid pattern returns empty error list."""
        alphabet = Alphabet("ABC")
        pattern = Pattern(["AB", Variable.any("x"), "C"])
        errors = pattern.validate_against_alphabet(alphabet)
        assert errors == []

    def test_validate_invalid_pattern(self) -> None:
        """Invalid pattern returns list of errors."""
        alphabet = Alphabet("ABC")
        pattern = Pattern(["AXB"])  # X not in alphabet
        errors = pattern.validate_against_alphabet(alphabet)
        assert len(errors) == 1
        assert "X" in errors[0]

    def test_validate_only_checks_constants(self) -> None:
        """Validation only checks constant parts, not variables."""
        alphabet = Alphabet("AB")
        x = Variable.any("x")
        pattern = Pattern([x, "AB", x])  # Variables don't matter
        errors = pattern.validate_against_alphabet(alphabet)
        assert errors == []


class TestPatternRepresentation:
    """Tests for string representations."""

    def test_str_constant_pattern(self) -> None:
        """String representation of constant pattern."""
        pattern = Pattern(["ABC"])
        assert str(pattern) == "ABC"

    def test_str_with_variable(self) -> None:
        """String representation includes ${name} for variables."""
        x = Variable.any("x")
        pattern = Pattern(["A", x, "B"])
        assert str(pattern) == "A${x}B"

    def test_str_multiple_variables(self) -> None:
        """String representation with multiple variables."""
        x = Variable.any("x")
        y = Variable.any("y")
        pattern = Pattern([x, y])
        assert str(pattern) == "${x}${y}"

    def test_repr_includes_pattern(self) -> None:
        """Repr includes Pattern type and content."""
        pattern = Pattern(["ABC"])
        assert "Pattern" in repr(pattern)


class TestPatternEdgeCases:
    """Edge case tests for patterns."""

    def test_pattern_with_all_empty_strings(self) -> None:
        """Pattern with only empty strings normalizes to empty."""
        pattern = Pattern(["", "", ""])
        assert pattern.elements == ()

    def test_pattern_immutability(self) -> None:
        """Pattern is immutable."""
        pattern = Pattern(["ABC"])
        with pytest.raises(AttributeError):
            pattern.elements = ()  # type: ignore

    @pytest.mark.parametrize(
        "text,expected_str",
        [
            ("", ""),
            ("A", "A"),
            ("ABC", "ABC"),
        ],
    )
    def test_constant_patterns(self, text: str, expected_str: str) -> None:
        """Various constant patterns work correctly."""
        pattern = Pattern.constant(text)
        assert str(pattern) == expected_str
