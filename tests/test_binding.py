"""Tests for the Binding class."""

import pytest

from post_canonical.matching.binding import Binding


class TestBindingCreation:
    """Tests for binding construction."""

    def test_create_empty(self) -> None:
        """Empty binding can be created with empty() factory."""
        binding = Binding.empty()
        assert len(binding) == 0

    def test_create_from_dict(self) -> None:
        """Binding can be created from a dictionary."""
        binding = Binding({"x": "A", "y": "B"})
        assert binding["x"] == "A"
        assert binding["y"] == "B"

    def test_create_from_none(self) -> None:
        """Binding with None creates empty binding."""
        binding = Binding(None)
        assert len(binding) == 0

    def test_create_from_pairs(self) -> None:
        """Binding.from_pairs creates from tuples."""
        binding = Binding.from_pairs(("x", "A"), ("y", "B"))
        assert binding["x"] == "A"
        assert binding["y"] == "B"


class TestBindingAccess:
    """Tests for accessing binding values."""

    def test_getitem(self) -> None:
        """Access values with [] operator."""
        binding = Binding({"x": "A"})
        assert binding["x"] == "A"

    def test_getitem_missing_raises(self) -> None:
        """Accessing missing key raises KeyError."""
        binding = Binding({"x": "A"})
        with pytest.raises(KeyError):
            _ = binding["y"]

    def test_contains(self) -> None:
        """The 'in' operator works for checking presence."""
        binding = Binding({"x": "A"})
        assert "x" in binding
        assert "y" not in binding

    def test_len(self) -> None:
        """len() returns number of bindings."""
        assert len(Binding.empty()) == 0
        assert len(Binding({"x": "A"})) == 1
        assert len(Binding({"x": "A", "y": "B"})) == 2

    def test_iteration(self) -> None:
        """Iteration yields variable names."""
        binding = Binding({"x": "A", "y": "B"})
        names = list(binding)
        assert "x" in names
        assert "y" in names

    def test_to_dict(self) -> None:
        """to_dict() converts to regular dictionary."""
        binding = Binding({"x": "A", "y": "B"})
        d = binding.to_dict()
        assert d == {"x": "A", "y": "B"}
        assert isinstance(d, dict)


class TestBindingMerge:
    """Tests for binding merge operation."""

    def test_merge_disjoint(self) -> None:
        """Merging disjoint bindings combines them."""
        b1 = Binding({"x": "A"})
        b2 = Binding({"y": "B"})
        merged = b1.merge(b2)
        assert merged is not None
        assert merged["x"] == "A"
        assert merged["y"] == "B"

    def test_merge_same_value(self) -> None:
        """Merging bindings with same value for same var succeeds."""
        b1 = Binding({"x": "A"})
        b2 = Binding({"x": "A"})
        merged = b1.merge(b2)
        assert merged is not None
        assert merged["x"] == "A"

    def test_merge_conflict_returns_none(self) -> None:
        """Merging bindings with conflicting values returns None."""
        b1 = Binding({"x": "A"})
        b2 = Binding({"x": "B"})
        merged = b1.merge(b2)
        assert merged is None

    def test_merge_with_empty(self) -> None:
        """Merging with empty binding returns equivalent binding."""
        b1 = Binding({"x": "A"})
        b2 = Binding.empty()
        merged = b1.merge(b2)
        assert merged is not None
        assert merged["x"] == "A"
        assert len(merged) == 1

    def test_merge_preserves_immutability(self) -> None:
        """Original bindings are not modified by merge."""
        b1 = Binding({"x": "A"})
        b2 = Binding({"y": "B"})
        merged = b1.merge(b2)
        assert len(b1) == 1  # Original unchanged
        assert len(b2) == 1  # Original unchanged
        assert merged is not None
        assert len(merged) == 2


class TestBindingExtend:
    """Tests for binding extend operation."""

    def test_extend_new_variable(self) -> None:
        """Extending with new variable adds it."""
        binding = Binding({"x": "A"})
        extended = binding.extend("y", "B")
        assert extended is not None
        assert extended["x"] == "A"
        assert extended["y"] == "B"

    def test_extend_same_value(self) -> None:
        """Extending with same value for existing var succeeds."""
        binding = Binding({"x": "A"})
        extended = binding.extend("x", "A")
        assert extended is not None
        assert extended["x"] == "A"

    def test_extend_conflict_returns_none(self) -> None:
        """Extending with conflicting value returns None."""
        binding = Binding({"x": "A"})
        extended = binding.extend("x", "B")
        assert extended is None

    def test_extend_empty_binding(self) -> None:
        """Extending empty binding creates single binding."""
        binding = Binding.empty()
        extended = binding.extend("x", "A")
        assert extended is not None
        assert extended["x"] == "A"
        assert len(extended) == 1


class TestBindingRepresentation:
    """Tests for string representations."""

    def test_str_empty(self) -> None:
        """String representation of empty binding."""
        binding = Binding.empty()
        assert str(binding) == "{}"

    def test_str_with_values(self) -> None:
        """String representation includes variable=value pairs."""
        binding = Binding({"x": "A"})
        s = str(binding)
        assert "$x=" in s
        assert "'A'" in s

    def test_repr(self) -> None:
        """Repr includes Binding type."""
        binding = Binding({"x": "A"})
        assert "Binding" in repr(binding)


class TestBindingImmutability:
    """Tests for binding immutability."""

    def test_binding_is_frozen(self) -> None:
        """Binding is immutable."""
        binding = Binding({"x": "A"})
        with pytest.raises(AttributeError):
            binding._data = ()  # type: ignore


class TestBindingEdgeCases:
    """Edge case tests for bindings."""

    def test_empty_string_value(self) -> None:
        """Bindings can have empty string values."""
        binding = Binding({"x": ""})
        assert binding["x"] == ""

    def test_long_value(self) -> None:
        """Bindings can have long string values."""
        long_value = "A" * 1000
        binding = Binding({"x": long_value})
        assert binding["x"] == long_value

    def test_multiple_merges(self) -> None:
        """Multiple sequential merges work correctly."""
        b1 = Binding({"a": "1"})
        b2 = Binding({"b": "2"})
        b3 = Binding({"c": "3"})
        merged = b1.merge(b2)
        assert merged is not None
        final = merged.merge(b3)
        assert final is not None
        assert final["a"] == "1"
        assert final["b"] == "2"
        assert final["c"] == "3"

    @pytest.mark.parametrize(
        "var_name,value",
        [
            ("x", "A"),
            ("long_variable_name", "value"),
            ("x1", "123"),
        ],
    )
    def test_various_names_and_values(self, var_name: str, value: str) -> None:
        """Various variable names and values work correctly."""
        binding = Binding({var_name: value})
        assert binding[var_name] == value


class TestBindingMappingProtocol:
    """Tests for Mapping protocol compliance."""

    def test_keys(self) -> None:
        """Binding supports iteration over keys."""
        binding = Binding({"x": "A", "y": "B"})
        keys = list(binding.keys())
        assert set(keys) == {"x", "y"}

    def test_values(self) -> None:
        """Binding supports values() method."""
        binding = Binding({"x": "A", "y": "B"})
        values = list(binding.values())
        assert set(values) == {"A", "B"}

    def test_items(self) -> None:
        """Binding supports items() method."""
        binding = Binding({"x": "A", "y": "B"})
        items = list(binding.items())
        assert set(items) == {("x", "A"), ("y", "B")}

    def test_get_with_default(self) -> None:
        """Binding supports get() with default value."""
        binding = Binding({"x": "A"})
        assert binding.get("x") == "A"
        assert binding.get("y") is None
        assert binding.get("y", "default") == "default"
