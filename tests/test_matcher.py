"""Tests for the PatternMatcher class."""

import pytest

from post_canonical import Alphabet, Pattern, Variable
from post_canonical.matching.binding import Binding
from post_canonical.matching.matcher import PatternMatcher


class TestMatcherBasics:
    """Basic pattern matching tests."""

    def test_constant_match(self, binary_alphabet: Alphabet) -> None:
        """Constant pattern matches exact string."""
        matcher = PatternMatcher(binary_alphabet)
        pattern = Pattern(["01"])
        binding = matcher.match_first(pattern, "01")
        assert binding is not None
        assert len(binding) == 0  # No variables to bind

    def test_constant_no_match(self, binary_alphabet: Alphabet) -> None:
        """Constant pattern fails on different string."""
        matcher = PatternMatcher(binary_alphabet)
        pattern = Pattern(["01"])
        binding = matcher.match_first(pattern, "10")
        assert binding is None

    def test_single_variable_any(self, binary_alphabet: Alphabet) -> None:
        """ANY variable matches the entire word."""
        matcher = PatternMatcher(binary_alphabet)
        x = Variable.any("x")
        pattern = Pattern([x])
        binding = matcher.match_first(pattern, "0110")
        assert binding is not None
        assert binding["x"] == "0110"

    def test_single_variable_any_empty(self, binary_alphabet: Alphabet) -> None:
        """ANY variable can match empty string."""
        matcher = PatternMatcher(binary_alphabet)
        x = Variable.any("x")
        pattern = Pattern([x])
        binding = matcher.match_first(pattern, "")
        assert binding is not None
        assert binding["x"] == ""

    def test_single_variable_non_empty(self, binary_alphabet: Alphabet) -> None:
        """NON_EMPTY variable matches at least one char."""
        matcher = PatternMatcher(binary_alphabet)
        y = Variable.non_empty("y")
        pattern = Pattern([y])
        binding = matcher.match_first(pattern, "01")
        assert binding is not None
        assert binding["y"] == "01"

    def test_single_variable_non_empty_no_match_empty(self, binary_alphabet: Alphabet) -> None:
        """NON_EMPTY variable fails on empty string."""
        matcher = PatternMatcher(binary_alphabet)
        y = Variable.non_empty("y")
        pattern = Pattern([y])
        binding = matcher.match_first(pattern, "")
        assert binding is None

    def test_single_variable_single(self, binary_alphabet: Alphabet) -> None:
        """SINGLE variable matches exactly one char."""
        matcher = PatternMatcher(binary_alphabet)
        z = Variable.single("z")
        pattern = Pattern([z])
        binding = matcher.match_first(pattern, "0")
        assert binding is not None
        assert binding["z"] == "0"

    def test_single_variable_single_no_match_multiple(self, binary_alphabet: Alphabet) -> None:
        """SINGLE variable fails on multiple chars."""
        matcher = PatternMatcher(binary_alphabet)
        z = Variable.single("z")
        pattern = Pattern([z])
        binding = matcher.match_first(pattern, "01")
        assert binding is None


class TestMatcherWithConstants:
    """Tests for patterns mixing variables and constants."""

    def test_prefix_constant(self, miu_alphabet: Alphabet) -> None:
        """Pattern with prefix constant."""
        matcher = PatternMatcher(miu_alphabet)
        x = Variable.any("x")
        pattern = Pattern(["M", x])  # M${x}
        binding = matcher.match_first(pattern, "MIU")
        assert binding is not None
        assert binding["x"] == "IU"

    def test_suffix_constant(self, miu_alphabet: Alphabet) -> None:
        """Pattern with suffix constant."""
        matcher = PatternMatcher(miu_alphabet)
        x = Variable.any("x")
        pattern = Pattern([x, "I"])  # ${x}I
        binding = matcher.match_first(pattern, "MUI")
        assert binding is not None
        assert binding["x"] == "MU"

    def test_infix_constant(self, miu_alphabet: Alphabet) -> None:
        """Pattern with constant in the middle."""
        matcher = PatternMatcher(miu_alphabet)
        x = Variable.any("x")
        y = Variable.any("y")
        pattern = Pattern([x, "U", y])  # ${x}U${y}
        binding = matcher.match_first(pattern, "MIUI")
        assert binding is not None
        # First match should have x="" since we try min length first
        assert "U" not in binding["x"] or "U" not in binding["y"]

    def test_multiple_constants(self, miu_alphabet: Alphabet) -> None:
        """Pattern with multiple constants."""
        matcher = PatternMatcher(miu_alphabet)
        x = Variable.any("x")
        pattern = Pattern(["M", x, "U"])  # M${x}U
        binding = matcher.match_first(pattern, "MIU")
        assert binding is not None
        assert binding["x"] == "I"

    def test_constant_not_found(self, miu_alphabet: Alphabet) -> None:
        """Pattern fails when constant not in word."""
        matcher = PatternMatcher(miu_alphabet)
        x = Variable.any("x")
        pattern = Pattern(["M", x, "U"])  # M${x}U
        binding = matcher.match_first(pattern, "MII")
        assert binding is None


class TestMatcherBacktracking:
    """Tests for backtracking with multiple matches."""

    def test_all_matches_generator(self, miu_alphabet: Alphabet) -> None:
        """match() yields all possible bindings."""
        matcher = PatternMatcher(miu_alphabet)
        x = Variable.any("x")
        y = Variable.any("y")
        pattern = Pattern([x, "I", y])  # ${x}I${y}

        matches = list(matcher.match(pattern, "MIIU"))
        # Should find matches at different I positions
        assert len(matches) >= 2

    def test_matches_method(self, binary_alphabet: Alphabet) -> None:
        """matches() returns True/False for match existence."""
        matcher = PatternMatcher(binary_alphabet)
        x = Variable.any("x")
        pattern = Pattern(["0", x, "1"])

        assert matcher.matches(pattern, "01") is True
        assert matcher.matches(pattern, "0111") is True
        assert matcher.matches(pattern, "10") is False

    def test_backtracking_finds_later_match(self, miu_alphabet: Alphabet) -> None:
        """Backtracking explores alternative bindings."""
        matcher = PatternMatcher(miu_alphabet)
        x = Variable.any("x")
        y = Variable.any("y")
        pattern = Pattern([x, "III", y])  # ${x}III${y}

        # "MIIIIU" has III at position 1
        binding = matcher.match_first(pattern, "MIIIIU")
        assert binding is not None
        assert "III" not in binding["x"]
        assert "III" not in binding["y"]


class TestMatcherConsecutiveVariables:
    """Tests for patterns with consecutive variables."""

    def test_two_any_variables(self, binary_alphabet: Alphabet) -> None:
        """Two ANY variables can split word any way."""
        matcher = PatternMatcher(binary_alphabet)
        x = Variable.any("x")
        y = Variable.any("y")
        pattern = Pattern([x, y])  # ${x}${y}

        matches = list(matcher.match(pattern, "01"))
        # All possible splits: ("", "01"), ("0", "1"), ("01", "")
        assert len(matches) == 3
        values = [(b["x"], b["y"]) for b in matches]
        assert ("", "01") in values
        assert ("0", "1") in values
        assert ("01", "") in values

    def test_any_then_non_empty(self, binary_alphabet: Alphabet) -> None:
        """ANY followed by NON_EMPTY restricts splits."""
        matcher = PatternMatcher(binary_alphabet)
        x = Variable.any("x")
        y = Variable.non_empty("y")
        pattern = Pattern([x, y])  # ${x}${y}

        matches = list(matcher.match(pattern, "01"))
        # y must have at least 1 char, so: ("", "01"), ("0", "1")
        assert len(matches) == 2
        values = [(b["x"], b["y"]) for b in matches]
        assert ("", "01") in values
        assert ("0", "1") in values
        assert ("01", "") not in values

    def test_non_empty_then_any(self, binary_alphabet: Alphabet) -> None:
        """NON_EMPTY followed by ANY restricts splits."""
        matcher = PatternMatcher(binary_alphabet)
        x = Variable.non_empty("x")
        y = Variable.any("y")
        pattern = Pattern([x, y])  # ${x}${y}

        matches = list(matcher.match(pattern, "01"))
        assert len(matches) == 2
        values = [(b["x"], b["y"]) for b in matches]
        assert ("0", "1") in values
        assert ("01", "") in values
        assert ("", "01") not in values

    def test_three_consecutive_variables(self, binary_alphabet: Alphabet) -> None:
        """Three consecutive ANY variables."""
        matcher = PatternMatcher(binary_alphabet)
        x = Variable.any("x")
        y = Variable.any("y")
        z = Variable.any("z")
        pattern = Pattern([x, y, z])

        matches = list(matcher.match(pattern, "01"))
        # Number of ways to split 2 chars into 3 parts with empty allowed
        # (0,0,2), (0,1,1), (0,2,0), (1,0,1), (1,1,0), (2,0,0) = 6
        assert len(matches) == 6


class TestMatcherRepeatedVariables:
    """Tests for patterns with the same variable appearing multiple times."""

    def test_repeated_variable_must_match_same(self, binary_alphabet: Alphabet) -> None:
        """Same variable must have same value everywhere."""
        matcher = PatternMatcher(binary_alphabet)
        x = Variable.any("x")
        pattern = Pattern([x, x])  # ${x}${x}

        # "0101" can be split as "01" + "01"
        binding = matcher.match_first(pattern, "0101")
        assert binding is not None
        assert binding["x"] == "01"

    def test_repeated_variable_no_match(self, binary_alphabet: Alphabet) -> None:
        """Repeated variable fails when halves differ."""
        matcher = PatternMatcher(binary_alphabet)
        x = Variable.any("x")
        pattern = Pattern([x, x])  # ${x}${x}

        # "0110" cannot be split into two equal parts
        binding = matcher.match_first(pattern, "0110")
        assert binding is None

    def test_repeated_variable_with_constant(self, miu_alphabet: Alphabet) -> None:
        """Repeated variable with constant separator."""
        matcher = PatternMatcher(miu_alphabet)
        x = Variable.any("x")
        pattern = Pattern(["M", x, x])  # M${x}${x}

        binding = matcher.match_first(pattern, "MII")
        assert binding is not None
        assert binding["x"] == "I"


class TestMatcherInitialBinding:
    """Tests for matching with pre-existing bindings."""

    def test_initial_binding_respected(self, binary_alphabet: Alphabet) -> None:
        """Initial binding constrains variable values."""
        matcher = PatternMatcher(binary_alphabet)
        x = Variable.any("x")
        pattern = Pattern([x, "1"])  # ${x}1

        initial = Binding({"x": "0"})
        binding = matcher.match_first(pattern, "01", initial)
        assert binding is not None
        assert binding["x"] == "0"

    def test_initial_binding_conflict(self, binary_alphabet: Alphabet) -> None:
        """Conflicting initial binding causes match failure."""
        matcher = PatternMatcher(binary_alphabet)
        x = Variable.any("x")
        pattern = Pattern([x, "1"])  # ${x}1

        # Initial says x="00" but word is "01" so x must be "0"
        initial = Binding({"x": "00"})
        binding = matcher.match_first(pattern, "01", initial)
        assert binding is None


class TestMatcherEdgeCases:
    """Edge case tests for pattern matching."""

    def test_empty_pattern_matches_empty_word(self, binary_alphabet: Alphabet) -> None:
        """Empty pattern matches only empty word."""
        matcher = PatternMatcher(binary_alphabet)
        pattern = Pattern([])
        assert matcher.matches(pattern, "") is True
        assert matcher.matches(pattern, "0") is False

    def test_empty_word_with_any_variable(self, binary_alphabet: Alphabet) -> None:
        """Empty word matches pattern with only ANY variable."""
        matcher = PatternMatcher(binary_alphabet)
        x = Variable.any("x")
        pattern = Pattern([x])
        binding = matcher.match_first(pattern, "")
        assert binding is not None
        assert binding["x"] == ""

    def test_empty_word_with_constant(self, binary_alphabet: Alphabet) -> None:
        """Empty word fails to match constant pattern."""
        matcher = PatternMatcher(binary_alphabet)
        pattern = Pattern(["0"])
        assert matcher.matches(pattern, "") is False

    @pytest.mark.parametrize(
        "word,expected_x",
        [
            ("M", ""),
            ("MI", "I"),
            ("MII", "II"),
            ("MIIIIIIII", "IIIIIIII"),
        ],
    )
    def test_prefix_pattern_various_lengths(self, miu_alphabet: Alphabet, word: str, expected_x: str) -> None:
        """Pattern with prefix works for various word lengths."""
        matcher = PatternMatcher(miu_alphabet)
        x = Variable.any("x")
        pattern = Pattern(["M", x])

        binding = matcher.match_first(pattern, word)
        assert binding is not None
        assert binding["x"] == expected_x
