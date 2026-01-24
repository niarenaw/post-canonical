"""Tests for JSON serialization (PCSJsonCodec)."""

import json
import tempfile
from pathlib import Path

import pytest

from post_canonical import (
    Alphabet,
    Pattern,
    PCSJsonCodec,
    PostCanonicalSystem,
    ProductionRule,
    Variable,
    VariableKind,
)
from post_canonical.presets.alphabets import BINARY, MIU


class TestCodecEncode:
    """Tests for encoding PCS to JSON."""

    def test_encode_basic_system(self) -> None:
        """Basic system encodes to valid JSON."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]), name="double")

        pcs = PostCanonicalSystem(
            alphabet=BINARY,
            axioms=frozenset({"0"}),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )

        codec = PCSJsonCodec()
        json_str = codec.encode(pcs)

        # Should be valid JSON
        data = json.loads(json_str)
        assert "version" in data
        assert "alphabet" in data
        assert "variables" in data
        assert "axioms" in data
        assert "rules" in data

    def test_encode_alphabet(self) -> None:
        """Alphabet is encoded as sorted list."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x]))

        pcs = PostCanonicalSystem(
            alphabet=Alphabet("CBA"),
            axioms=frozenset({"A"}),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )

        codec = PCSJsonCodec()
        data = json.loads(codec.encode(pcs))

        assert data["alphabet"] == ["A", "B", "C"]

    def test_encode_variables(self) -> None:
        """Variables are encoded with name and kind."""
        x = Variable.any("x")
        y = Variable.non_empty("y")
        z = Variable.single("z")
        rule = ProductionRule([Pattern([x, y, z])], Pattern([x]))

        pcs = PostCanonicalSystem(
            alphabet=BINARY,
            axioms=frozenset({"01"}),
            rules=frozenset({rule}),
            variables=frozenset({x, y, z}),
        )

        codec = PCSJsonCodec()
        data = json.loads(codec.encode(pcs))

        var_dict = {v["name"]: v["kind"] for v in data["variables"]}
        assert var_dict["x"] == "ANY"
        assert var_dict["y"] == "NON_EMPTY"
        assert var_dict["z"] == "SINGLE"

    def test_encode_rules(self) -> None:
        """Rules are encoded with patterns as strings."""
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern([x, "I"])],
            Pattern([x, "I", "U"]),
            name="add_U",
            priority=5,
        )

        pcs = PostCanonicalSystem(
            alphabet=MIU,
            axioms=frozenset({"MI"}),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )

        codec = PCSJsonCodec()
        data = json.loads(codec.encode(pcs))

        assert len(data["rules"]) == 1
        rule_data = data["rules"][0]
        assert rule_data["name"] == "add_U"
        assert rule_data["priority"] == 5
        assert "${x}I" in rule_data["antecedents"]
        assert rule_data["consequent"] == "${x}IU"

    def test_encode_multi_antecedent_rule(self) -> None:
        """Multi-antecedent rules are encoded correctly."""
        x = Variable.any("x")
        y = Variable.any("y")
        rule = ProductionRule(
            [Pattern([x]), Pattern([y])],
            Pattern([x, y]),
            name="concat",
        )

        pcs = PostCanonicalSystem(
            alphabet=BINARY,
            axioms=frozenset({"0", "1"}),
            rules=frozenset({rule}),
            variables=frozenset({x, y}),
        )

        codec = PCSJsonCodec()
        data = json.loads(codec.encode(pcs))

        rule_data = data["rules"][0]
        assert len(rule_data["antecedents"]) == 2


class TestCodecDecode:
    """Tests for decoding JSON to PCS."""

    def test_decode_basic_system(self) -> None:
        """Basic JSON decodes to valid system."""
        json_str = """
        {
            "version": "1.0",
            "alphabet": ["0", "1"],
            "variables": [{"name": "x", "kind": "ANY"}],
            "axioms": ["0"],
            "rules": [
                {
                    "name": "double",
                    "priority": 0,
                    "antecedents": ["${x}"],
                    "consequent": "${x}${x}"
                }
            ]
        }
        """

        codec = PCSJsonCodec()
        pcs = codec.decode(json_str)

        assert "0" in pcs.alphabet
        assert "1" in pcs.alphabet
        assert "0" in pcs.axioms
        assert len(pcs.rules) == 1

    def test_decode_variable_kinds(self) -> None:
        """All variable kinds are decoded correctly."""
        json_str = """
        {
            "version": "1.0",
            "alphabet": ["A"],
            "variables": [
                {"name": "x", "kind": "ANY"},
                {"name": "y", "kind": "NON_EMPTY"},
                {"name": "z", "kind": "SINGLE"}
            ],
            "axioms": ["A"],
            "rules": [
                {
                    "antecedents": ["${x}${y}${z}"],
                    "consequent": "${x}"
                }
            ]
        }
        """

        codec = PCSJsonCodec()
        pcs = codec.decode(json_str)

        var_dict = {v.name: v.kind for v in pcs.variables}
        assert var_dict["x"] == VariableKind.ANY
        assert var_dict["y"] == VariableKind.NON_EMPTY
        assert var_dict["z"] == VariableKind.SINGLE

    def test_decode_missing_version_uses_default(self) -> None:
        """Missing version defaults to 1.0."""
        json_str = """
        {
            "alphabet": ["A"],
            "variables": [],
            "axioms": ["A"],
            "rules": []
        }
        """

        codec = PCSJsonCodec()
        pcs = codec.decode(json_str)  # Should not raise

        assert "A" in pcs.axioms

    def test_decode_invalid_version_raises(self) -> None:
        """Invalid version raises ValueError."""
        json_str = """
        {
            "version": "99.0",
            "alphabet": ["A"],
            "variables": [],
            "axioms": ["A"],
            "rules": []
        }
        """

        codec = PCSJsonCodec()
        with pytest.raises(ValueError, match="Unsupported version"):
            codec.decode(json_str)

    def test_decode_missing_field_raises(self) -> None:
        """Missing required field raises an error."""
        json_str = """
        {
            "version": "1.0",
            "alphabet": ["A"],
            "axioms": ["A"],
            "rules": []
        }
        """

        codec = PCSJsonCodec()
        # The codec raises KeyError when accessing missing 'variables' field
        with pytest.raises(KeyError):
            codec.decode(json_str)

    def test_decode_invalid_variable_kind_raises(self) -> None:
        """Invalid variable kind raises KeyError (enum lookup fails)."""
        json_str = """
        {
            "version": "1.0",
            "alphabet": ["A"],
            "variables": [{"name": "x", "kind": "INVALID"}],
            "axioms": ["A"],
            "rules": []
        }
        """

        codec = PCSJsonCodec()
        with pytest.raises(KeyError):
            codec.decode(json_str)

    def test_decode_missing_variable_name_raises(self) -> None:
        """Variable without name raises KeyError."""
        json_str = """
        {
            "version": "1.0",
            "alphabet": ["A"],
            "variables": [{"kind": "ANY"}],
            "axioms": ["A"],
            "rules": []
        }
        """

        codec = PCSJsonCodec()
        with pytest.raises(KeyError):
            codec.decode(json_str)

    def test_decode_missing_variable_kind_raises(self) -> None:
        """Variable without kind raises KeyError."""
        json_str = """
        {
            "version": "1.0",
            "alphabet": ["A"],
            "variables": [{"name": "x"}],
            "axioms": ["A"],
            "rules": []
        }
        """

        codec = PCSJsonCodec()
        with pytest.raises(KeyError):
            codec.decode(json_str)


class TestCodecRoundTrip:
    """Tests for encode-decode round trips."""

    def test_round_trip_preserves_system(self, mu_system: PostCanonicalSystem) -> None:
        """Encoding then decoding preserves the system."""
        codec = PCSJsonCodec()

        json_str = codec.encode(mu_system)
        restored = codec.decode(json_str)

        # Check alphabet
        assert restored.alphabet.symbols == mu_system.alphabet.symbols

        # Check axioms
        assert restored.axioms == mu_system.axioms

        # Check variables
        original_vars = {v.name: v.kind for v in mu_system.variables}
        restored_vars = {v.name: v.kind for v in restored.variables}
        assert restored_vars == original_vars

        # Check rules
        assert len(restored.rules) == len(mu_system.rules)

    def test_round_trip_multi_antecedent(self, multi_antecedent_system: PostCanonicalSystem) -> None:
        """Multi-antecedent rules survive round trip."""
        codec = PCSJsonCodec()

        json_str = codec.encode(multi_antecedent_system)
        restored = codec.decode(json_str)

        # Find the concat rule
        concat_rules = [r for r in restored.rules if r.name == "concat"]
        assert len(concat_rules) == 1
        assert len(concat_rules[0].antecedents) == 2

    def test_round_trip_generated_words_match(self) -> None:
        """Restored system generates same words."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]), name="double")

        original = PostCanonicalSystem(
            alphabet=BINARY,
            axioms=frozenset({"1"}),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )

        codec = PCSJsonCodec()
        restored = codec.decode(codec.encode(original))

        original_words = original.generate_words(max_steps=3)
        restored_words = restored.generate_words(max_steps=3)

        assert original_words == restored_words


class TestCodecFileOperations:
    """Tests for file save/load operations."""

    def test_save_and_load(self, mu_system: PostCanonicalSystem) -> None:
        """System can be saved to file and loaded back."""
        codec = PCSJsonCodec()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "system.json"

            codec.save(mu_system, str(path))
            assert path.exists()

            loaded = codec.load(str(path))
            assert loaded.axioms == mu_system.axioms

    def test_save_creates_valid_json_file(self, mu_system: PostCanonicalSystem) -> None:
        """Saved file is valid JSON."""
        codec = PCSJsonCodec()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "system.json"
            codec.save(mu_system, str(path))

            # Read and parse as JSON
            with open(path) as f:
                data = json.load(f)

            assert "version" in data
            assert data["version"] == "1.0"


class TestCodecEdgeCases:
    """Edge case tests for serialization."""

    def test_empty_axiom(self) -> None:
        """Empty string axiom survives round trip."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern(["0", x, "0"]))

        original = PostCanonicalSystem(
            alphabet=BINARY,
            axioms=frozenset({""}),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )

        codec = PCSJsonCodec()
        restored = codec.decode(codec.encode(original))

        assert "" in restored.axioms

    def test_system_with_no_rules(self) -> None:
        """System with no rules serializes correctly."""
        original = PostCanonicalSystem(
            alphabet=BINARY,
            axioms=frozenset({"0", "1"}),
            rules=frozenset(),
            variables=frozenset(),
        )

        codec = PCSJsonCodec()
        json_str = codec.encode(original)
        restored = codec.decode(json_str)

        assert len(restored.rules) == 0
        assert restored.axioms == original.axioms

    def test_system_with_no_variables(self) -> None:
        """System with constant-only rules serializes correctly."""
        rule = ProductionRule([Pattern(["A"])], Pattern(["B"]), name="A_to_B")

        original = PostCanonicalSystem(
            alphabet=Alphabet("AB"),
            axioms=frozenset({"A"}),
            rules=frozenset({rule}),
            variables=frozenset(),
        )

        codec = PCSJsonCodec()
        restored = codec.decode(codec.encode(original))

        assert len(restored.variables) == 0
        assert len(restored.rules) == 1

    def test_special_characters_in_alphabet(self) -> None:
        """Special characters in alphabet serialize correctly."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x]))

        original = PostCanonicalSystem(
            alphabet=Alphabet("+-*/"),
            axioms=frozenset({"+"}),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )

        codec = PCSJsonCodec()
        restored = codec.decode(codec.encode(original))

        assert "+" in restored.alphabet
        assert "-" in restored.alphabet
        assert "*" in restored.alphabet
        assert "/" in restored.alphabet

    def test_rule_priority_preserved(self) -> None:
        """Rule priorities survive round trip."""
        x = Variable.any("x")
        rule = ProductionRule(
            [Pattern([x])],
            Pattern([x, x]),
            name="high_priority",
            priority=100,
        )

        original = PostCanonicalSystem(
            alphabet=BINARY,
            axioms=frozenset({"0"}),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )

        codec = PCSJsonCodec()
        restored = codec.decode(codec.encode(original))

        restored_rule = next(iter(restored.rules))
        assert restored_rule.priority == 100


class TestCodecErrorMessages:
    """Tests for error handling in codec."""

    def test_invalid_rule_format_error(self) -> None:
        """Invalid rule format (not an object) raises TypeError."""
        json_str = """
        {
            "version": "1.0",
            "alphabet": ["A"],
            "variables": [],
            "axioms": ["A"],
            "rules": ["not an object"]
        }
        """

        codec = PCSJsonCodec()
        with pytest.raises(TypeError):
            codec.decode(json_str)

    def test_missing_rule_antecedents_error(self) -> None:
        """Missing antecedents in rule raises KeyError."""
        json_str = """
        {
            "version": "1.0",
            "alphabet": ["A"],
            "variables": [],
            "axioms": ["A"],
            "rules": [
                {
                    "name": "bad_rule",
                    "consequent": "A"
                }
            ]
        }
        """

        codec = PCSJsonCodec()
        with pytest.raises(KeyError):
            codec.decode(json_str)

    def test_invalid_pattern_error(self) -> None:
        """Invalid pattern (unknown variable) raises ValueError."""
        json_str = """
        {
            "version": "1.0",
            "alphabet": ["A"],
            "variables": [{"name": "x", "kind": "ANY"}],
            "axioms": ["A"],
            "rules": [
                {
                    "name": "bad_pattern",
                    "antecedents": ["${unknown}"],
                    "consequent": "A"
                }
            ]
        }
        """

        codec = PCSJsonCodec()
        with pytest.raises(ValueError, match="Unknown variable"):
            codec.decode(json_str)
