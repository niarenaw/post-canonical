"""Tests for the Alphabet class."""

import pytest

from post_canonical import Alphabet


class TestAlphabetCreation:
    """Tests for alphabet construction."""

    def test_create_from_string(self) -> None:
        """Alphabet can be created from a string of characters."""
        alphabet = Alphabet("abc")
        assert "a" in alphabet
        assert "b" in alphabet
        assert "c" in alphabet
        assert len(alphabet) == 3

    def test_create_from_set(self) -> None:
        """Alphabet can be created from a set of characters."""
        alphabet = Alphabet({"x", "y", "z"})
        assert "x" in alphabet
        assert "y" in alphabet
        assert "z" in alphabet

    def test_create_from_frozenset(self) -> None:
        """Alphabet can be created from a frozenset."""
        alphabet = Alphabet(frozenset({"1", "2", "3"}))
        assert "1" in alphabet
        assert "2" in alphabet
        assert len(alphabet) == 3

    def test_duplicate_characters_deduplicated(self) -> None:
        """Duplicate characters in input are deduplicated."""
        alphabet = Alphabet("aabbcc")
        assert len(alphabet) == 3

    def test_empty_alphabet_raises(self) -> None:
        """Creating an empty alphabet raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Alphabet("")

    def test_multi_character_symbol_raises(self) -> None:
        """Symbols must be single characters."""
        with pytest.raises(ValueError, match="single characters"):
            Alphabet({"ab", "cd"})

    def test_immutability(self) -> None:
        """Alphabet is immutable (frozen dataclass)."""
        alphabet = Alphabet("abc")
        with pytest.raises(AttributeError):
            alphabet.symbols = frozenset("xyz")  # type: ignore


class TestAlphabetMethods:
    """Tests for alphabet methods."""

    def test_contains(self) -> None:
        """The 'in' operator works correctly."""
        alphabet = Alphabet("MIU")
        assert "M" in alphabet
        assert "I" in alphabet
        assert "U" in alphabet
        assert "X" not in alphabet

    def test_iteration_is_sorted(self) -> None:
        """Iteration yields symbols in sorted order."""
        alphabet = Alphabet("CBA")
        assert list(alphabet) == ["A", "B", "C"]

    def test_len(self) -> None:
        """Length returns number of unique symbols."""
        assert len(Alphabet("abc")) == 3
        assert len(Alphabet("aaa")) == 1

    def test_str_representation(self) -> None:
        """String representation shows sorted symbols."""
        alphabet = Alphabet("CBA")
        assert str(alphabet) == "{A, B, C}"

    def test_repr(self) -> None:
        """Repr includes the type name."""
        alphabet = Alphabet("01")
        assert "Alphabet" in repr(alphabet)


class TestAlphabetUnion:
    """Tests for alphabet union operation."""

    def test_union_combines_symbols(self) -> None:
        """Union creates alphabet with symbols from both."""
        a1 = Alphabet("AB")
        a2 = Alphabet("CD")
        combined = a1.union(a2)
        assert "A" in combined
        assert "B" in combined
        assert "C" in combined
        assert "D" in combined

    def test_union_handles_overlap(self) -> None:
        """Union correctly handles overlapping symbols."""
        a1 = Alphabet("ABC")
        a2 = Alphabet("BCD")
        combined = a1.union(a2)
        assert len(combined) == 4
        assert set(combined) == {"A", "B", "C", "D"}


class TestAlphabetValidation:
    """Tests for word validation against alphabets."""

    def test_validate_word_returns_empty_for_valid(self) -> None:
        """validate_word returns empty list for valid words."""
        alphabet = Alphabet("MIU")
        assert alphabet.validate_word("MIU") == []
        assert alphabet.validate_word("MIUUU") == []
        assert alphabet.validate_word("") == []  # Empty word is always valid

    def test_validate_word_returns_invalid_chars(self) -> None:
        """validate_word returns list of invalid characters."""
        alphabet = Alphabet("MIU")
        invalid = alphabet.validate_word("MAX")
        assert "A" in invalid
        assert "X" in invalid
        assert "M" not in invalid

    def test_validate_word_detects_invalid_word(self) -> None:
        """validate_word returns non-empty list for invalid words."""
        alphabet = Alphabet("abc")
        assert len(alphabet.validate_word("abd")) > 0  # d not in alphabet
        assert len(alphabet.validate_word("xyz")) > 0  # none in alphabet


class TestAlphabetEdgeCases:
    """Edge case tests for alphabets."""

    def test_single_character_alphabet(self) -> None:
        """Single character alphabets work correctly."""
        alphabet = Alphabet("X")
        assert len(alphabet) == 1
        assert "X" in alphabet
        assert alphabet.validate_word("XXX") == []

    def test_numeric_characters(self) -> None:
        """Numeric character alphabets work correctly."""
        alphabet = Alphabet("0123456789")
        assert len(alphabet) == 10
        assert alphabet.validate_word("123") == []

    def test_special_characters(self) -> None:
        """Special characters can be used in alphabets."""
        alphabet = Alphabet("+-*/")
        assert "+" in alphabet
        assert "-" in alphabet
        assert alphabet.validate_word("+-") == []

    @pytest.mark.parametrize(
        "symbols,expected_len",
        [
            ("01", 2),
            ("abc", 3),
            ("ABCDEFGHIJ", 10),
            ("aAbBcC", 6),
        ],
    )
    def test_various_alphabet_sizes(self, symbols: str, expected_len: int) -> None:
        """Alphabets of various sizes work correctly."""
        alphabet = Alphabet(symbols)
        assert len(alphabet) == expected_len
